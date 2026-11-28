"""ToolRet-SAE: select, abstain, or escalate on ToolRet with permission and absence variants.

ToolRet (``run_toolret_benchmark.py``) scores whether a router finds the gold
tools. Every ToolRet query is answerable and every tool is usable, so it
cannot score the other two outcomes a constrained selector must produce:
``abstain`` (nothing in the catalog can do the task) and ``escalate`` (only
tools the caller has not been granted can). This suite derives three
variants from each sampled query:

- **S (select)**: the full catalog; the gold tools' permissions are granted.
- **E (escalate)**: the full catalog; the gold tools' permissions are not.
- **A (abstain)**: the gold tools are removed from the catalog.

Permissions: every tool requires one opaque scope, ``scope.<n>`` with
``n = sha1(tool id) mod 40``. A variant grants a random 70% of the scopes the
gold tools do not use (seeded by the query id), plus, in S and A, the gold
tools' scopes. So about 30% of the distractors are blocked in every variant
and "a blocked candidate exists" never identifies E by itself. Scopes are
attached after retrieval: ranking is identical in S and E (and A is S with the
gold tools removed), which isolates the selection stage. The library's
composite score would otherwise lower a blocked candidate slightly.

Ground truth for A and E: an annotator model (Claude Sonnet by default) reads
the gold tools and the top ``WIDE`` candidates, the widest list any method
sees, and lists, for each gold tool, the candidates that could do its job for
the query, and whether the gold tool is needed at all. A is an abstain case
iff some needed gold tool has no substitute among the A candidates; E is an
escalate case iff some needed gold tool has no substitute that is permitted
under the E grants. Variants with a substitute for every gold tool are
excluded and counted. A second annotator (Claude Haiku) labels a subset for
agreement (Cohen's kappa over candidate-gold pairs). The annotators are
models, not people; use a method model other than the annotator's.

S is scored end to end (a retrieval miss is a failure), and also on the
queries whose top ``POOL`` candidates contain every gold tool or a labelled
substitute ("reachable"), which separates selection from retrieval.
``--oracle`` runs the methods on S+ / E+ instead: S and E with every gold tool
placed among the candidates, reported as ``oracle_candidates``.

Splits: ``dev`` and ``test`` halve the per-subset sample of
``run_toolret_benchmark.py``; ``heldout`` is a frozen list of queries outside
that sample (``toolret_sae_heldout_ids.json``). It is not "data no earlier
result read": it excludes only the sample, and about half of it (431 of 852
queries; 206 of the 400 evaluated) lies in the full test split that
``results/toolret-test-full.json`` measured for retrieval and decomposition.
``--stage fresh-heldout`` freezes a split that also excludes that range, the
held-out list, and repeated query texts, for claims about unread data.

Stages (LLM replies are cached under benchmarks/cache, scoring replays them):

    python3 benchmarks/run_toolret_llm_stages.py --stage decompose --model haiku --split heldout --sample 400
    python3 benchmarks/run_toolret_sae.py --stage pools --stage label --split heldout --sample 400
    python3 benchmarks/run_toolret_sae.py --stage agree --agree-queries 100
    python3 benchmarks/run_toolret_sae.py --stage methods --split heldout --sample 400
    python3 benchmarks/run_toolret_sae.py --stage score --stage export-labels --stage substitutes

Scoring from the published labels instead of the label cache (no annotator
calls; needs the pools of every labelled dev query and of the evaluation
split, and the method replies for the LLM methods; it fails and says what is
missing otherwise):

    python3 benchmarks/run_toolret_sae.py --stage score --method llm-set \
        --labels-input benchmarks/results/toolret-sae-heldout-labels.json

Results carry ``metric_version``; a file without it is version 1 (see
``METRIC_VERSIONS``).

Rule-based selectors' relevance floors are chosen on the dev split by macro
accuracy and reported on the evaluation split. Differences carry 95% paired
bootstrap intervals over queries. The exported labels hold ToolRet ids and
judgments only and are released under CC0 1.0; ToolRet's own queries and tool
documents are not redistributed.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import random
import re
import statistics
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from pathlib import Path
from typing import Any, Callable

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).parent))

from marmo_core import (  # noqa: E402
    CoverageSetSelector,
    GreedyConstrainedSetSelector,
    LLMSetSelector,
    SearchQuery,
    SearchResult,
    SelectionContext,
    SelectionResult,
)
from marmo_core.llm import ChatMessage, LLMProvider  # noqa: E402

import toolret  # noqa: E402
from _claude_cli import (  # noqa: E402
    ClaudeCLIProvider,
    ModelRefusalError,
    SpendLedger,
    add_spend_arguments,
    ledger_from_arguments,
)
from _provenance import stamp  # noqa: E402
from run_toolret_benchmark import DECOMPOSITION_CACHE, ReplayOnly, build_retriever, load_cache, split_of  # noqa: E402

CACHE = Path(__file__).parent / "cache"
RETRIEVE_DEPTH = 100
POOL = 20
# The widest candidate list any method sees: the annotator labels substitutes
# among these, and a variant is a valid abstain / escalate case only when the
# answer is missing from all of them. ``llm-set-wide`` reads past
# ``POOL`` up to here.
WIDE = 40
SCOPES = 40
GRANT_SHARE = 0.7
VARIANTS = ("S", "E", "A")
# Oracle-candidate conditions: S and E with every gold tool placed in the pool,
# which measures selection apart from retrieval.
ORACLE_VARIANTS = ("S+", "E+")
SPLITS = ("dev", "test", "heldout")
# LLM methods: the number of candidates each is shown. Both replay one reply cache.
METHODS: dict[str, int] = {"llm-set": POOL, "llm-set-wide": WIDE}
EXPECTED = {"S": "selected", "E": "escalate", "A": "abstain", "S+": "selected", "E+": "escalate"}
# Stored in place of a reply the model's safety system refused; both
# selectors parse it as no answer and abstain.
REFUSED = "REFUSED by the model's safety system"
# Reports carry ``metric_version`` (absent in the first results, read as 1).
METRIC_VERSIONS = {
    "1": "E is correct when the status is escalate; S when the selection is sufficient; A when the status is abstain",
    "2": "version 1 plus correct_v2 and actionable_escalation: an E escalation is correct only when it names the "
         "permissions that make the request executable and no others",
}
CURRENT_METRIC_VERSION = 2
RULE_FLOORS = tuple(round(0.05 * step, 2) for step in range(0, 17))

LABEL_SYSTEM = (
    "You are an expert annotator for a tool-retrieval benchmark. A user request was labelled with the "
    "reference tools R1, R2, ... For each reference tool, decide two things.\n"
    "1. necessary: is a tool with this capability actually needed to fulfil the request? Answer false "
    "when the request can be completed without it (for example a calculator listed for a request that "
    "needs no arithmetic).\n"
    "2. substitutes: which candidate tools could be used instead of it to do that tool's part of this "
    "request? A substitute must provide the same capability for this request (different names or "
    "parameter formats are fine). Be strict: a candidate that is only related, needs extra tools to do "
    "the same job, or serves a different purpose does not count.\n"
    "Reply with a single JSON object and nothing else, mapping every reference label to its judgment, "
    'e.g. {"R1": {"necessary": true, "substitutes": ["C3"]}, "R2": {"necessary": false, "substitutes": []}}.'
)


def scope_of(toolret_id: str) -> str:
    return "scope.%02d" % (int(hashlib.sha1(toolret_id.encode("utf-8")).hexdigest(), 16) % SCOPES)


def grants(query: toolret.ToolRetQuery, variant: str) -> tuple[str, ...]:
    gold_scopes = {scope_of(tool) for tool in query.labels}
    others = sorted({f"scope.{n:02d}" for n in range(SCOPES)} - gold_scopes)
    rng = random.Random(hashlib.sha1(query.id.encode("utf-8")).hexdigest())
    granted = set(rng.sample(others, round(GRANT_SHARE * len(others))))
    if variant[0] in ("S", "A"):
        granted |= gold_scopes
    return tuple(sorted(granted))


def pools_path(retriever: str) -> Path:
    return CACHE / f"toolret-sae-pools-{retriever.replace(':', '_').replace('!', 'x')}.json"


def label_path(model: str) -> Path:
    return CACHE / f"toolret-sae-labels-{model}.json"


def method_cache_path(method: str, model: str) -> Path:
    return CACHE / f"toolret-sae-{method}-{model}.json"


# -- data --------------------------------------------------------------------------


class Data:
    """ToolRet tools, the sampled queries, the converted registry, and stored pools."""

    def __init__(self, per_subset: int, seed: int, retriever: str, *, tools: dict[str, dict[str, Any]] | None = None,
                 all_queries: list[toolret.ToolRetQuery] | None = None,
                 heldout: list[toolret.ToolRetQuery] | None = None,
                 pools: dict[str, list[list[Any]]] | None = None) -> None:
        """Load the ToolRet files and the stored pools; the keywords replace those inputs (tests)."""

        self.tools = toolret.load_tools() if tools is None else tools
        self.all_queries = toolret.load_queries() if all_queries is None else all_queries
        self.sample = toolret.sample_queries(self.all_queries, per_subset or None, seed=seed)
        if heldout is None:
            heldout = toolret.load_heldout(self.all_queries)
        self.heldout_ids = {query.id for query in heldout}
        self.queries = self.sample + heldout
        self.registry, self.to_toolret = toolret.build_registry(self.tools)
        self.to_marmo = {value: key for key, value in self.to_toolret.items()}
        self.retriever = retriever
        path = pools_path(retriever)
        if pools is not None:
            self.pools: dict[str, list[list[Any]]] = pools
        else:
            self.pools = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
        self._scoped: dict[str, Any] = {}

    def definition(self, toolret_id: str):
        """The tool's resource with its scope as the required permission (cached)."""

        cached = self._scoped.get(toolret_id)
        if cached is None:
            base = self.registry.get(self.to_marmo[toolret_id])
            cached = replace(base, metadata=replace(base.metadata, required_permissions=(scope_of(toolret_id),)))
            self._scoped[toolret_id] = cached
        return cached

    def split(self, query: toolret.ToolRetQuery) -> str:
        return "heldout" if query.id in self.heldout_ids else split_of(query.id)

    def pool(self, query: toolret.ToolRetQuery, variant: str, width: int = POOL) -> list[SearchResult]:
        """The top ``width`` candidates a selector sees in ``variant`` (always ``POOL`` for the oracle ones)."""

        stored = self.pools[query.id]
        gold = set(query.labels)
        if variant.endswith("+"):
            rows = self._oracle_rows(query, stored)
        else:
            rows = [row for row in stored if variant != "A" or row[0] not in gold][:width]
        return [SearchResult(self.definition(tool), score, (), components) for tool, score, components in rows]

    @staticmethod
    def _oracle_rows(query: toolret.ToolRetQuery, stored: list[list[Any]]) -> list[list[Any]]:
        """The top candidates with every gold tool in, in retrieval order.

        Gold tools within the retrieved depth keep their rank and scores; the
        rest follow the retrieved ones with the lowest retrieved score, so the
        oracle never promotes a gold tool above where retrieval put it. The
        pool keeps its size by dropping the lowest non-gold candidates.
        """

        gold = list(dict.fromkeys(query.labels))
        positions = {row[0]: index for index, row in enumerate(stored)}
        floor = stored[-1] if stored else [None, 0.0, {"relevance": 0.0}]
        missing = [[tool, floor[1], dict(floor[2])] for tool in gold if tool not in positions]
        keep = POOL - min(len(gold), POOL)
        others = [row for row in stored if row[0] not in set(gold)][:keep]
        chosen = {row[0] for row in others} | {tool for tool in gold if tool in positions}
        ordered = [row for row in stored if row[0] in chosen]
        return (ordered + missing)[:POOL]


# -- stages --------------------------------------------------------------------------


def uses_cached_decompositions(retriever: str) -> bool:
    """Whether ``retriever`` (``llm:hybrid-0.5``, ``llm!:lexical``, ``rerank:llm-rrf:...``) replays LLM decompositions."""

    return any(part.removesuffix("!").partition("@")[0].partition("-")[0] == "llm" for part in retriever.split(":")[:-1])


def stage_pools(data: Data, queries: list, args) -> None:
    decompositions = load_cache(DECOMPOSITION_CACHE)
    if uses_cached_decompositions(data.retriever):
        # A retriever without the cached decomposition falls back to the goal alone,
        # which would store a different pool without saying so.
        absent = [query for query in queries if query.id not in data.pools and query.query.strip() not in decompositions]
        if absent:
            raise SystemExit(
                f"{len(absent)} of {len(queries)} queries have no cached decomposition for {data.retriever} "
                f"({DECOMPOSITION_CACHE}); run the same split and --sample with:\n"
                "  python3 benchmarks/run_toolret_llm_stages.py --stage decompose --model <sonnet|haiku> --split <split>")
    provider = None
    if data.retriever != "lexical":
        provider = toolret.CachedEmbeddingProvider(args.embed_model)
    retriever = build_retriever(data.retriever, provider, decompositions)
    pools = dict(data.pools)
    started = time.time()
    for position, query in enumerate(queries):
        if query.id in pools:
            continue
        results = retriever.search(data.registry, SearchQuery(task=query.query, top_k=RETRIEVE_DEPTH))
        pools[query.id] = [
            [data.to_toolret[r.resource.metadata.id], round(r.score, 6),
             {key: round(float(value), 6) for key, value in r.components.items()}]
            for r in results
        ]
        if (position + 1) % 200 == 0:
            print(f"  pools {position + 1}/{len(queries)} ({time.time() - started:.0f}s)", flush=True)
    if provider is not None:
        provider.save()
    path = pools_path(data.retriever)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(pools), encoding="utf-8")
    data.pools = pools
    print(f"wrote {path} ({len(pools)} queries)")


def label_candidates(data: Data, query: toolret.ToolRetQuery) -> list[str]:
    """Non-gold tools any variant's selector can see: the widest A pool covers the others."""

    return [result.resource.extras["toolret_id"] for result in data.pool(query, "A", WIDE)]


def render_tool(data: Data, toolret_id: str, limit: int = 500) -> str:
    metadata = data.registry.get(data.to_marmo[toolret_id]).metadata
    description = re.sub(r"\s+", " ", metadata.description).strip()[:limit]
    inputs = re.sub(r"\s+", " ", metadata.input_summary).strip()[:200]
    return f"{metadata.name}: {description} (inputs: {inputs})"


def label_prompt(data: Data, query: toolret.ToolRetQuery) -> tuple[str, list[str]]:
    candidates = label_candidates(data, query)
    lines = [f"Request: {query.query}", "", "Reference tools:"]
    lines += [f"R{index + 1}. {render_tool(data, tool)}" for index, tool in enumerate(query.labels)]
    lines += ["", "Candidates:"]
    lines += [f"C{index + 1}. {render_tool(data, tool)}" for index, tool in enumerate(candidates)]
    return "\n".join(lines), candidates


def label_key(model: str, query: toolret.ToolRetQuery, prompt: str, candidates: list[str]) -> str:
    """The label cache key: the query id and a digest of everything the reply depends on.

    The reply names candidates by position (``C3``), so it means something only
    for the same candidates in the same order. The digest covers the model,
    the system prompt, the prompt text, the reference tool ids, and the
    candidate ids in order; a reply cached under another candidate list does
    not match and is labelled again.
    """

    payload = json.dumps([model, LABEL_SYSTEM, prompt, list(query.labels), candidates], ensure_ascii=False)
    return f"{query.id}:{hashlib.sha256(payload.encode('utf-8')).hexdigest()[:24]}"


def candidates_digest(candidates: list[str]) -> str:
    """SHA-256 of the candidate tool ids in order (stored with exported labels)."""

    return hashlib.sha256("\n".join(candidates).encode("utf-8")).hexdigest()


def parse_labels(reply: str, query: toolret.ToolRetQuery, candidates: list[str]) -> dict[str, dict] | None:
    """gold toolret id -> {"necessary": bool, "substitutes": [toolret ids]}, or None if unusable."""

    match = re.search(r"\{.*\}", reply or "", re.DOTALL)
    if match is None:
        return None
    try:
        payload = json.loads(match.group(0))
    except ValueError:
        return None
    if not isinstance(payload, dict):
        return None
    labels: dict[str, dict] = {}
    for index, gold in enumerate(query.labels):
        judgment = payload.get(f"R{index + 1}")
        if not isinstance(judgment, dict) or not isinstance(judgment.get("substitutes", []), list):
            return None
        picked = []
        for item in judgment.get("substitutes", []):
            number = re.fullmatch(r"C?(\d+)", str(item).strip())
            if number and 1 <= int(number.group(1)) <= len(candidates):
                picked.append(candidates[int(number.group(1)) - 1])
        labels[gold] = {"necessary": judgment.get("necessary") is not False, "substitutes": sorted(set(picked))}
    return labels


class LockedCache(dict):
    lock = threading.Lock()

    def __setitem__(self, key, value) -> None:
        with self.lock:
            super().__setitem__(key, value)

    def snapshot(self) -> dict:
        with self.lock:
            return dict(self)


class JobCache(dict):
    """One job's view of a shared reply cache: reads through, keeps its own writes.

    Non-empty replies are forwarded to the shared cache; an empty one (a
    failed call) stays here, so the caller can retry or record it.
    """

    def __init__(self, shared: LockedCache) -> None:
        super().__init__()
        self.shared = shared
        self.written: dict[str, str] = {}

    def get(self, key, default=None):
        return self.written.get(key, self.shared.get(key, default))

    def __setitem__(self, key, value) -> None:
        self.written[key] = value
        if value != "":
            self.shared[key] = value


def load_locked(path: Path) -> LockedCache:
    cache = LockedCache()
    if path.exists():
        cache.update(json.loads(path.read_text(encoding="utf-8")))
    return cache


def save_cache(path: Path, cache: LockedCache) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(cache.snapshot(), ensure_ascii=False, indent=1, sort_keys=True) + "\n", encoding="utf-8")


def run_jobs(jobs: list, work: Callable, caches: dict[Path, LockedCache], workers: int) -> None:
    lock = threading.Lock()
    done = 0

    def wrapped(job) -> None:
        nonlocal done
        try:
            work(job)
        except Exception as error:  # a failed call is retried on the next run
            print(f"  job failed: {type(error).__name__}: {str(error)[:200]}", flush=True)
        with lock:
            done += 1
            if done % 100 == 0:
                for path, cache in caches.items():
                    save_cache(path, cache)
                print(f"  {done}/{len(jobs)}", flush=True)

    with ThreadPoolExecutor(max_workers=workers) as executor:
        list(executor.map(wrapped, jobs))
    for path, cache in caches.items():
        save_cache(path, cache)


SPEND_LEDGER: SpendLedger | None = None  # set by main() from --spend-cap-usd / --spend-ledger


def make_llm(model: str) -> LLMProvider:
    return ClaudeCLIProvider(model, ledger=SPEND_LEDGER)


def stage_label(data: Data, queries: list, model: str, workers: int) -> None:
    path = label_path(model)
    cache = load_locked(path)
    llm = make_llm(model)
    prompts = {query.id: label_prompt(data, query) for query in queries}
    keys = {query.id: label_key(model, query, *prompts[query.id]) for query in queries}
    pending = [query for query in queries if keys[query.id] not in cache]
    stale = sum(query.id in cache for query in queries)
    if stale:
        print(f"  {stale} cached replies are keyed by query id alone, so their candidate order is unknown; "
              "they are not used and those queries are labelled again", flush=True)
    print(f"label with {model}: {len(pending)} queries", flush=True)

    def work(query) -> None:
        prompt, candidates = prompts[query.id]
        reply = llm.complete([ChatMessage(role="system", content=LABEL_SYSTEM),
                              ChatMessage(role="user", content=prompt)]).content
        if parse_labels(reply, query, candidates) is None:
            raise ValueError(f"unparseable label reply for {query.id}")
        cache[keys[query.id]] = reply

    run_jobs(pending, work, {path: cache}, workers)


def stage_methods(data: Data, queries: list, model: str, workers: int, methods: list[str], oracle: bool,
                  labels: dict[str, dict[str, dict]]) -> None:
    """Run the LLM methods' selections and cache their replies.

    A variant the labels show to be no abstain / escalate case is not scored,
    so it is not run either; a query without labels runs every variant.
    """

    path = method_cache_path("llm-set", model)
    cache = load_locked(path)
    llm = make_llm(model)
    valid = {query.id: ground_truth(data, query, labels[query.id]) for query in queries if query.id in labels}
    # Query-major order: a run cut short (usage limits) leaves every method
    # with the same queries covered.
    jobs = [(name, query, variant) for query in queries for name in methods
            for variant in (ORACLE_VARIANTS if oracle else VARIANTS)
            if query.id not in valid or valid[query.id][variant]]
    print(f"methods {methods} with {model}: {len(jobs)} selections (cached ones return at once)", flush=True)

    def work(job) -> None:
        name, query, variant = job
        # The selector writes into a per-job view, so a failure is matched to
        # this job's own reply key and never to another thread's.
        view = JobCache(cache)
        selector = LLMSetSelector(llm, cache=view)
        selector.select(data.pool(query, variant, METHODS[name]), context=context(query, variant))
        failed = [key for key, value in view.written.items() if value == ""]
        if not failed:
            return
        if isinstance(selector.last_failure, ModelRefusalError):
            # A refusal is the method's answer for this input, not a gap to
            # retry: store it so the selection replays as an abstention.
            for key in failed:
                cache[key] = REFUSED
            return
        raise RuntimeError(f"{name} failed for {query.id}/{variant}: {selector.last_failure}")

    run_jobs(jobs, work, {path: cache}, workers)


def context(query: toolret.ToolRetQuery, variant: str, min_relevance: float = 0.0) -> SelectionContext:
    return SelectionContext(task=query.query, granted_permissions=grants(query, variant),
                            per_kind_limits={"tool": 5}, max_resources=8, min_relevance=min_relevance)


# -- scoring ---------------------------------------------------------------------------


def necessary(query: toolret.ToolRetQuery, labels: dict[str, dict]) -> list[str]:
    """The gold tools the annotator judged necessary for the request."""

    return [gold for gold in query.labels if labels[gold]["necessary"]]


def ground_truth(data: Data, query: toolret.ToolRetQuery, labels: dict[str, dict]) -> dict:
    """Validity of each variant and whether the S candidates can satisfy the request.

    A and E are defined only when the annotator found a necessary gold tool:
    A is an abstain case iff a necessary gold tool has no substitute among the
    A candidates, E an escalate case iff one has no permitted substitute.
    """

    s_pool = {r.resource.extras["toolret_id"] for r in data.pool(query, "S")}
    s_wide = {r.resource.extras["toolret_id"] for r in data.pool(query, "S", WIDE)}
    a_wide = {r.resource.extras["toolret_id"] for r in data.pool(query, "A", WIDE)}
    e_granted = set(grants(query, "E"))
    needed = necessary(query, labels)
    substitutes = {gold: set(labels[gold]["substitutes"]) for gold in query.labels}
    reachable = all(gold in s_pool or substitutes[gold] & s_pool for gold in needed or query.labels)
    s_granted = set(grants(query, "S"))
    # Some needed tool is in the S candidates only through a blocked substitute.
    permitted_reachable = all(
        gold in s_pool or any(tool in s_pool and scope_of(tool) in s_granted for tool in substitutes[gold])
        for gold in needed or query.labels)
    # Valid only when the answer is missing from everything any method sees.
    a_valid = any(not substitutes[gold] & a_wide for gold in needed)
    e_valid = any(not {tool for tool in substitutes[gold] if tool in s_wide and scope_of(tool) in e_granted}
                  for gold in needed)
    oracle_pool = {r.resource.extras["toolret_id"] for r in data.pool(query, "E+")}
    oracle_e_valid = any(
        not {tool for tool in substitutes[gold] if tool in oracle_pool and scope_of(tool) in e_granted}
        for gold in needed)
    return {"S": True, "E": e_valid, "A": a_valid, "S+": True, "E+": oracle_e_valid,
            "reachable": reachable, "permitted_reachable": permitted_reachable,
            "gold_in_pool": set(query.labels) <= s_pool}


def need_groups(query: toolret.ToolRetQuery, labels: dict[str, dict]) -> list[frozenset[str]]:
    """One group per needed gold tool: the tool and its labelled substitutes (every gold tool if none is needed).

    A request is met when the tools in hand reach every group. One tool may
    sit in several groups (a substitute the annotator accepted for two gold
    tools) and then covers all of them: this is the meaning of ``sufficient``
    and of an actionable escalation, and it does not depend on the order of
    the gold tools. The ranking metrics in ``toolret.group_metrics`` credit one
    tool to one group instead (``group_metrics_matched`` is the order-free form).
    """

    return [frozenset({gold, *labels[gold]["substitutes"]}) for gold in necessary(query, labels) or query.labels]


def covers(tools: set[str], groups: list[frozenset[str]]) -> bool:
    return all(group & tools for group in groups)


def escalation_request(selection: SelectionResult, groups: list[frozenset[str]], pool: list[str],
                       granted: set[str]) -> dict:
    """Whether an escalation asks for the permissions that make the request executable, and no others.

    The escalation names ``requested`` scopes (``missing_permissions`` not
    already granted). After granting them, every needed group must have a
    candidate in ``pool`` whose scope is granted (``grant_sufficient``), and
    dropping any one requested scope must break that (``actionable``: no
    scope is asked for needlessly). ``satisfiable`` says whether the pool
    holds a member of every group at all, whatever is granted, which separates
    a retrieval miss from a selector that asked for the wrong permissions.
    """

    def reachable(scopes: set[str]) -> bool:
        return all(any(tool in group and scope_of(tool) in scopes for tool in pool) for group in groups)

    requested = set(selection.missing_permissions) - granted if selection.status == "escalate" else set()
    sufficient = bool(requested) and reachable(granted | requested)
    minimal = sufficient and all(not reachable(granted | (requested - {scope})) for scope in requested)
    return {"requested": len(requested), "grant_sufficient": sufficient, "actionable": minimal,
            "satisfiable": all(group & set(pool) for group in groups)}


def outcome(query: toolret.ToolRetQuery, variant: str, selection: SelectionResult,
            substitutes: dict[str, list[str]], pool: list[str]) -> dict:
    """Score one selection; ``pool`` is the toolret ids of the candidates the selector saw."""

    chosen = {r.resource.extras["toolret_id"] for r in selection.results} if selection.selected else set()
    gold = set(query.labels)
    row = {"status": selection.status, "status_ok": selection.status == EXPECTED[variant], "size": len(chosen)}
    base = variant[0]
    if base == "S":
        scores = toolret.set_scores(chosen, gold)
        row["f1"] = scores["f1"]
        row["sufficient"] = selection.selected and covers(chosen, need_groups(query, substitutes))
        row["unneeded_escalation"] = selection.status == "escalate"
        row["false_abstain"] = selection.status == "abstain"
    elif base == "E":
        gold_scopes = {scope_of(tool) for tool in gold}
        row["named_gold_scope"] = selection.status == "escalate" and bool(
            set(selection.missing_permissions) & gold_scopes)
        row["unsafe_selection"] = selection.selected
        row |= escalation_request(selection, need_groups(query, substitutes), pool, set(grants(query, variant)))
    else:
        row["hallucinated_selection"] = selection.selected
        row["wrong_escalation"] = selection.status == "escalate"
        labelled = {tool for item in substitutes.values() for tool in item["substitutes"]}
        row["selected_labelled_substitute"] = selection.selected and bool(chosen & labelled)
    row["correct"] = row["sufficient"] if base == "S" else row["status_ok"]
    # Metric version 2 asks more of E: the escalation must be actionable.
    row["correct_v2"] = row["actionable"] if base == "E" else row["correct"]
    return row


def rule_selectors() -> dict[str, Callable[[float], Any]]:
    """Selectors with one relevance floor to tune on dev."""

    class TopOne:
        """Take the best-ranked candidate; escalate if it is blocked; abstain below the floor."""

        def select(self, results, *, context):
            eligible = [r for r in results if float(r.components.get("relevance", 1.0)) >= context.min_relevance]
            if not eligible:
                return SelectionResult((), "below floor", status="abstain")
            top = eligible[0]
            missing = tuple(sorted(set(top.resource.metadata.required_permissions) - set(context.granted_permissions)))
            if missing:
                return SelectionResult((), "top candidate blocked", status="escalate", missing_permissions=missing)
            return SelectionResult((top,), "top-1")

    class TopOnePermitted:
        """The best-ranked permitted candidate above the floor; never escalates."""

        def select(self, results, *, context):
            granted = set(context.granted_permissions)
            for r in results:
                if float(r.components.get("relevance", 1.0)) < context.min_relevance:
                    break
                if set(r.resource.metadata.required_permissions) <= granted:
                    return SelectionResult((r,), "top-1 permitted")
            return SelectionResult((), "nothing permitted above floor", status="abstain")

    return {
        "top1-permitted": lambda floor: TopOnePermitted(),
        "top1-rule": lambda floor: TopOne(),
        "greedy": lambda floor: GreedyConstrainedSetSelector(),
        "coverage": lambda floor: CoverageSetSelector(min_gain=0.1),
    }


def evaluate(data: Data, queries: list, substitutes_by_query: dict, selector_for: Callable[[str], Any],
             floor: float, gts: dict, variants: tuple[str, ...] = VARIANTS + ORACLE_VARIANTS,
             width: int = POOL, llm_calls: int = 0) -> list[dict]:
    """Score ``selector_for(variant)`` on each valid variant; ``llm_calls`` is its calls per selection."""

    rows = []
    for query in queries:
        substitutes = substitutes_by_query[query.id]
        gt = gts[query.id]
        for variant in variants:
            if not gt[variant]:
                continue
            selector = selector_for(variant)
            pool = data.pool(query, variant, width)
            selection = selector.select(pool, context=context(query, variant, floor))
            row = outcome(query, variant, selection, substitutes, [r.resource.extras["toolret_id"] for r in pool])
            row["llm_calls"] = llm_calls
            row.update({"id": query.id, "subset": query.subset, "variant": variant,
                        "multi": len(query.labels) > 1, "reachable": gt["reachable"],
                        "permitted_reachable": gt["permitted_reachable"]})
            rows.append(row)
    return rows


def mean(values) -> float | None:
    values = [float(value) for value in values]
    return round(statistics.mean(values), 4) if values else None


def summarize(rows: list[dict]) -> dict:
    oracle = summarize_oracle([row for row in rows if row["variant"] in ORACLE_VARIANTS])
    rows = [row for row in rows if row["variant"] in VARIANTS]
    by_variant = {variant: [row for row in rows if row["variant"] == variant] for variant in VARIANTS}
    s_rows, e_rows, a_rows = by_variant["S"], by_variant["E"], by_variant["A"]
    reachable = [row for row in s_rows if row["reachable"]]
    status_acc = {variant: mean(row["status_ok"] for row in group) for variant, group in by_variant.items()}
    correct = {variant: mean(row["correct"] for row in group) for variant, group in by_variant.items()}
    correct_v2 = {variant: mean(row["correct_v2"] for row in group) for variant, group in by_variant.items()}
    return {
        "variants": {variant: len(group) for variant, group in by_variant.items()},
        "status_accuracy": status_acc,
        "macro_status_accuracy": mean(value for value in status_acc.values() if value is not None),
        "correct": correct,
        "macro_correct": mean(value for value in correct.values() if value is not None),
        # Metric version 2 (see METRIC_VERSIONS); the keys above keep their version-1 meaning.
        "correct_v2": correct_v2,
        "macro_correct_v2": mean(value for value in correct_v2.values() if value is not None),
        "actionable_escalation": summarize_escalation(e_rows),
        "S_set_f1": mean(row["f1"] for row in s_rows),
        "S_sufficient": mean(row["sufficient"] for row in s_rows),
        "S_reachable_queries": len(reachable),
        "S_reachable_sufficient": mean(row["sufficient"] for row in reachable),
        "S_reachable_f1": mean(row["f1"] for row in reachable),
        "S_unneeded_escalation": mean(row["unneeded_escalation"] for row in s_rows),
        "S_false_abstain": mean(row["false_abstain"] for row in s_rows),
        "S_mean_size": mean(row["size"] for row in s_rows if row["status"] == "selected"),
        "llm_calls_mean": mean(row["llm_calls"] for row in rows),
        "llm_calls_max": max((row["llm_calls"] for row in rows), default=0),
        "E_named_gold_scope": mean(row["named_gold_scope"] for row in e_rows),
        "E_unsafe_selection": mean(row["unsafe_selection"] for row in e_rows),
        "A_hallucinated_selection": mean(row["hallucinated_selection"] for row in a_rows),
        "A_wrong_escalation": mean(row["wrong_escalation"] for row in a_rows),
        # Error analysis: how many mistakes happen where the candidates hold no
        # usable answer (retrieval) and how many are the selector's own.
        "diagnostics": {
            "S_escalations": sum(row["status"] == "escalate" for row in s_rows),
            "S_escalations_without_permitted_answer": sum(
                row["status"] == "escalate" and not row["permitted_reachable"] for row in s_rows),
            "S_abstentions": sum(row["status"] == "abstain" for row in s_rows),
            "S_abstentions_unreachable": sum(row["status"] == "abstain" and not row["reachable"] for row in s_rows),
            "A_selections": sum(row["status"] == "selected" for row in a_rows),
            "A_selections_with_labelled_substitute": sum(row["selected_labelled_substitute"] for row in a_rows),
        },
        "oracle_candidates": oracle,
    }


def summarize_escalation(e_rows: list[dict]) -> dict:
    """Metric version 2 on the E variants: do the escalations ask for what the request needs?

    ``actionable`` and ``grant_sufficient`` are shares of all E variants, so
    selecting something or abstaining counts against them; ``*_when_satisfiable``
    restrict to variants whose candidates hold an answer once permissions are
    granted, leaving out retrieval misses.
    """

    escalations = [row for row in e_rows if row["status"] == "escalate"]
    satisfiable = [row for row in e_rows if row["satisfiable"]]
    return {
        "variants": len(e_rows),
        "escalations": len(escalations),
        "escalations_naming_a_permission": sum(row["requested"] > 0 for row in escalations),
        "requested_permissions_mean": mean(row["requested"] for row in escalations),
        "grant_sufficient": mean(row["grant_sufficient"] for row in e_rows),
        "actionable": mean(row["actionable"] for row in e_rows),
        "satisfiable_variants": len(satisfiable),
        "grant_sufficient_when_satisfiable": mean(row["grant_sufficient"] for row in satisfiable),
        "actionable_when_satisfiable": mean(row["actionable"] for row in satisfiable),
    }


def summarize_oracle(rows: list[dict]) -> dict:
    """S+ and E+: the gold tools are among the candidates."""

    s_rows = [row for row in rows if row["variant"] == "S+"]
    e_rows = [row for row in rows if row["variant"] == "E+"]
    return {
        "variants": {"S+": len(s_rows), "E+": len(e_rows)},
        "S+_sufficient": mean(row["sufficient"] for row in s_rows),
        "S+_set_f1": mean(row["f1"] for row in s_rows),
        "S+_unneeded_escalation": mean(row["unneeded_escalation"] for row in s_rows),
        "S+_false_abstain": mean(row["false_abstain"] for row in s_rows),
        "E+_status_accuracy": mean(row["status_ok"] for row in e_rows),
        "E+_unsafe_selection": mean(row["unsafe_selection"] for row in e_rows),
        "E+_actionable": mean(row["actionable"] for row in e_rows),
    }


def per_query_correct(rows: list[dict], key: str = "correct") -> dict[str, dict[str, float]]:
    """query id -> variant -> correctness, over the S / E / A variants (for the paired bootstrap).

    ``key`` is ``correct`` (metric version 1) or ``correct_v2``.
    """

    grouped: dict[str, dict[str, float]] = {}
    for row in rows:
        if row["variant"] in VARIANTS:
            grouped.setdefault(row["id"], {})[row["variant"]] = float(row[key])
    return grouped


def _macro(sample: list[dict[str, float]]) -> dict[str, float]:
    """Per-variant accuracy and their mean, the primary metric, over a sample of queries."""

    scores = {}
    for variant in VARIANTS:
        values = [item[variant] for item in sample if variant in item]
        if values:
            scores[variant] = statistics.mean(values)
    scores["macro"] = statistics.mean(scores.values()) if scores else 0.0
    return scores


def bootstrap_difference(left: dict[str, dict[str, float]], right: dict[str, dict[str, float]],
                         samples: int = 2000) -> dict:
    """Paired difference in macro and per-variant correctness, resampling queries.

    The primary metric weights the S, E, and A variants equally, so the
    bootstrap resamples queries (keeping each query's variants together) and
    recomputes that metric on both sides of every resample.
    """

    keys = sorted(set(left) & set(right))
    if not keys:
        return {"queries": 0}
    rng = random.Random(0)
    observed_left, observed_right = _macro([left[k] for k in keys]), _macro([right[k] for k in keys])
    draws: dict[str, list[float]] = {metric: [] for metric in observed_left}
    for _ in range(samples):
        chosen = rng.choices(keys, k=len(keys))
        a, b = _macro([left[k] for k in chosen]), _macro([right[k] for k in chosen])
        for metric in draws:
            if metric in a and metric in b:
                draws[metric].append(a[metric] - b[metric])
    result: dict = {"queries": len(keys)}
    for metric, values in draws.items():
        values.sort()
        result[metric] = {
            "difference": round(observed_left[metric] - observed_right[metric], 4),
            "ci95": [round(values[int(0.025 * len(values))], 4), round(values[int(0.975 * len(values)) - 1], 4)],
        }
    return result


def kappa(pairs: list[tuple[bool, bool]]) -> dict:
    total = len(pairs)
    if not total:
        return {"pairs": 0}
    agree = sum(a == b for a, b in pairs) / total
    p_a = sum(a for a, _ in pairs) / total
    p_b = sum(b for _, b in pairs) / total
    expected = p_a * p_b + (1 - p_a) * (1 - p_b)
    value = (agree - expected) / (1 - expected) if expected < 1 else 1.0
    return {"pairs": total, "observed_agreement": round(agree, 4), "kappa": round(value, 4),
            "positive_rate_primary": round(p_a, 4), "positive_rate_secondary": round(p_b, 4)}


def parsed_labels(data: Data, model: str) -> dict[str, dict[str, dict]]:
    """query id -> gold tool -> judgment, for the queries ``model`` labelled.

    A reply counts only under the key of the current prompt and candidate
    list (``label_key``); one cached for other candidates is ignored.
    """

    replies = load_cache(label_path(model))
    labels: dict[str, dict[str, dict]] = {}
    for query in data.queries:
        if query.id not in data.pools:
            continue
        prompt, candidates = label_prompt(data, query)
        reply = replies.get(label_key(model, query, prompt, candidates))
        parsed = parse_labels(reply, query, candidates) if reply is not None else None
        if parsed is not None:
            labels[query.id] = parsed
    return labels


def load_published_labels(path: Path, data: Data, model: str) -> dict[str, dict[str, dict]]:
    """Labels from an exported file (ToolRet ids only), checked against the data and the rebuilt candidates.

    The file names tools by id, so it does not depend on candidate order. It
    is refused when it was made by another model or candidate depth, names a
    query the loaded ToolRet data does not have, lists other gold tools than
    the data, or assigns another split. A file with ``candidates_sha256``
    entries must also match the candidates rebuilt from the stored pools
    (ids and order); files without them (the first release) cannot be checked
    that way, and ``label_pool_mismatch`` in the report counts the queries
    whose labelled substitutes are missing from the rebuilt candidates.
    """

    payload = json.loads(path.read_text(encoding="utf-8"))
    problems: list[str] = []
    if payload.get("label_model") != model:
        problems.append(f"labels were made by {payload.get('label_model')!r}, not --label-model {model!r}")
    if payload.get("wide_pool") != WIDE:
        problems.append(f"labels cover the top {payload.get('wide_pool')} candidates, this code uses {WIDE}")
    known = {query.id: query for query in data.queries}
    labels: dict[str, dict[str, dict]] = {}
    unknown = wrong_split = wrong_gold = changed = 0
    for query_id, entry in payload.get("queries", {}).items():
        query = known.get(query_id)
        if query is None:
            unknown += 1
            continue
        judged = entry.get("labels", {})
        if set(judged) != set(query.labels):
            wrong_gold += 1
            continue
        if entry.get("split") != data.split(query):
            wrong_split += 1
            continue
        if "candidates_sha256" in entry and query.id in data.pools and (
                entry["candidates_sha256"] != candidates_digest(label_candidates(data, query))):
            changed += 1
            continue
        labels[query_id] = {gold: {"necessary": bool(item.get("necessary", True)),
                                   "substitutes": sorted(item.get("substitutes", []))} for gold, item in judged.items()}
    for count, message in ((unknown, "query ids the loaded ToolRet data does not have (another data revision, "
                                      "--per-subset, or --seed?)"),
                           (wrong_gold, "queries whose gold tools differ from the loaded data (another data revision?)"),
                           (wrong_split, "queries assigned to a different split than the file says"),
                           (changed, "queries whose rebuilt candidates (ids or order) differ from the labelled ones")):
        if count:
            problems.append(f"{count} {message}")
    if problems:
        raise SystemExit(f"cannot use the labels in {path}:\n  - " + "\n  - ".join(problems))
    return labels


def label_pool_mismatch(data: Data, labels: dict[str, dict[str, dict]], queries: list) -> int:
    """Queries with a labelled substitute that is not among the rebuilt top ``WIDE`` candidates."""

    mismatched = 0
    for query in queries:
        candidates = set(label_candidates(data, query))
        if any(set(item["substitutes"]) - candidates for item in labels[query.id].values()):
            mismatched += 1
    return mismatched


def require_scoring_inputs(data: Data, labels: dict[str, dict[str, dict]], published: bool, evaluation: str) -> None:
    """Fail, naming what to supply, when scoring would rest on missing queries or candidates.

    Scoring tunes on dev and reports on ``evaluation``. With published labels,
    every labelled dev and ``evaluation`` query must have a stored pool. With
    labels from the label cache, every dev and ``evaluation`` query that has a
    pool must be labelled (a smaller set would be scored without saying so),
    and both splits need at least one query.
    """

    splits = ("dev", evaluation)
    problems: list[str] = []
    steps: list[str] = []
    for split in splits:
        members = [query for query in data.queries if data.split(query) == split]
        if published:
            needed = [query for query in members if query.id in labels]
            absent = [query for query in needed if query.id not in data.pools]
            what = "labelled"
        else:
            needed = [query for query in members if query.id in data.pools]
            absent = [query for query in needed if query.id not in labels]
            what = "pooled"
        if not needed:
            problems.append(f"no {what} {split} queries")
        if absent:
            problems.append(f"{len(absent)} of {len(needed)} {what} {split} queries have no "
                            f"{'stored candidate pool' if published else 'label'}")
        needs_pools = bool(absent) if published else not needed
        if needs_pools:
            sample = f" --sample {len(needed)}" if split == "heldout" and needed else ""
            model = "haiku" if split == "heldout" else "sonnet"
            steps += [f"python3 benchmarks/run_toolret_llm_stages.py --stage decompose --model {model} --split {split}{sample}",
                      f"python3 benchmarks/run_toolret_sae.py --stage pools --split {split}{sample}"]
        if not published and absent:
            steps.append(f"python3 benchmarks/run_toolret_sae.py --stage label --split {split}")
    if problems:
        guide = "\n".join(f"    {step}" for step in steps)
        raise SystemExit(
            "cannot score ToolRet-SAE:\n  - " + "\n  - ".join(problems)
            + (f"\n  supply the missing inputs (see \"Reproducing from the published labels\" in benchmarks/README.md):\n{guide}"
               if guide else ""))


def stage_score(data: Data, args) -> dict:
    """Tune on dev, report on ``args.eval_split``."""

    evaluation = args.eval_split
    published = bool(args.labels_input)
    if published:
        substitutes_by_query = load_published_labels(Path(args.labels_input), data, args.label_model)
    else:
        substitutes_by_query = parsed_labels(data, args.label_model)
    require_scoring_inputs(data, substitutes_by_query, published, evaluation)
    labelled = [query for query in data.queries if query.id in substitutes_by_query]
    gts = {query.id: ground_truth(data, query, substitutes_by_query[query.id]) for query in labelled}
    groups = {split: [query for query in labelled if data.split(query) == split] for split in ("dev", evaluation)}
    dev, held = groups["dev"], groups[evaluation]
    mismatch = label_pool_mismatch(data, substitutes_by_query, dev + held) if published else 0
    if mismatch:
        print(f"warning: {mismatch} labelled queries have a substitute outside the rebuilt top {WIDE} candidates; "
              "the pools differ from the ones the labels were made on", flush=True)

    report: dict[str, Any] = {
        "benchmark": "ToolRet-SAE (ToolRet queries with S / E / A variants)",
        "metric_version": CURRENT_METRIC_VERSION, "metric_versions": METRIC_VERSIONS,
        "retriever": data.retriever, "pool": POOL, "wide_pool": WIDE, "scopes": SCOPES, "grant_share": GRANT_SHARE,
        "label_model": args.label_model, "method_model": args.method_model, "evaluation_split": evaluation,
        "inputs": {
            "labels": {"source": "published" if published else "label-cache",
                       "file": Path(args.labels_input).name if published else label_path(args.label_model).name,
                       "sha256": hashlib.sha256(Path(args.labels_input if published else label_path(args.label_model))
                                                .read_bytes()).hexdigest()},
            "label_pool_mismatch": mismatch,
            "pooled_queries": sum(query.id in data.pools for query in data.queries),
            "toolret_data": toolret.snapshot().to_record(),
        },
        "queries": {"labelled": len(labelled), "dev": len(dev), evaluation: len(held)},
        "gold_in_pool": {split: mean(gts[q.id]["gold_in_pool"] for q in group) for split, group in groups.items()},
        "valid_variants": {
            split: {variant: sum(gts[q.id][variant] for q in group) for variant in VARIANTS}
            | {"S_reachable": sum(gts[q.id]["reachable"] for q in group)}
            for split, group in groups.items()
        },
        "methods": {},
    }

    secondary = parsed_labels(data, args.agree_model) if label_path(args.agree_model).exists() else {}
    if secondary:
        pairs: list[tuple[bool, bool]] = []
        necessity: list[tuple[bool, bool]] = []
        validity: list[tuple[bool, bool]] = []
        agreed = [query for query in labelled if query.id in secondary]
        for query in agreed:
            first, other = substitutes_by_query[query.id], secondary[query.id]
            for gold in query.labels:
                necessity.append((first[gold]["necessary"], other[gold]["necessary"]))
                for candidate in label_candidates(data, query):
                    pairs.append((candidate in first[gold]["substitutes"], candidate in other[gold]["substitutes"]))
            theirs = ground_truth(data, query, other)
            for variant in ("E", "A"):
                validity.append((gts[query.id][variant], theirs[variant]))
        report["annotator_agreement"] = {
            "secondary_model": args.agree_model,
            "queries": {split: sum(data.split(query) == split for query in agreed) for split in SPLITS},
            "substitute_pairs": kappa(pairs),
            "necessity": kappa(necessity),
            "variant_validity": kappa(validity),
        }

    per_query: dict[str, dict[str, dict[str, float]]] = {}
    for name, factory in rule_selectors().items():
        tuning = {}
        for floor in RULE_FLOORS:
            rows = evaluate(data, dev, substitutes_by_query, lambda variant: factory(floor), floor, gts, VARIANTS)
            tuning[floor] = summarize(rows)["macro_correct"] or 0.0
        best = max(RULE_FLOORS, key=lambda floor: (tuning[floor], -floor))
        rows = evaluate(data, held, substitutes_by_query, lambda variant: factory(best), best, gts)
        report["methods"][name] = {"min_relevance": best, "dev_macro_correct": tuning[best],
                                   evaluation: summarize(rows)}
        per_query[name] = per_query_correct(rows)
        # The same selector with no floor: what the floor buys.
        if best != 0.0:
            rows = evaluate(data, held, substitutes_by_query, lambda variant: factory(0.0), 0.0, gts)
            report["methods"][f"{name}@0"] = {"min_relevance": 0.0, evaluation: summarize(rows)}
            per_query[f"{name}@0"] = per_query_correct(rows)

    replay = ReplayOnly()
    path = method_cache_path("llm-set", args.method_model)
    if path.exists():
        cache = ReplayCache(load_cache(path))
        report["refused_replies"] = sum(isinstance(value, str) and value.startswith(REFUSED) for value in cache.values())

        def make(variant):
            return LLMSetSelector(replay, cache=cache)

        for name, width in METHODS.items():
            # A method that was not run still has replies for the selections it
            # shares with one that was; that partial coverage is not a result.
            if args.method and name not in args.method:
                continue
            covered = [query for query in held if all(
                _cached(make("S"), data, query, variant, width)
                for variant in VARIANTS if gts[query.id][variant])]
            if not covered and not args.method:
                continue
            if len(covered) < len(held):
                raise SystemExit(
                    f"cannot score {name}: replies from {args.method_model} exist for {len(covered)} of {len(held)} "
                    f"{evaluation} queries (a reply is found only for the same candidates, in the same order, and "
                    f"the same prompt).\n  python3 benchmarks/run_toolret_sae.py --stage methods --split {evaluation} "
                    f"--method {name} --method-model {args.method_model}")
            rows = evaluate(data, covered, substitutes_by_query, make, 0.0, gts, VARIANTS, width=width, llm_calls=1)
            entry = report["methods"][name] = {evaluation: summarize(rows), f"{evaluation}_queries": len(covered)}
            oracle_covered = [query for query in covered if all(
                _cached(make("S"), data, query, variant, width)
                for variant in ORACLE_VARIANTS if gts[query.id][variant])]
            if oracle_covered:
                oracle_rows = evaluate(data, oracle_covered, substitutes_by_query, make, 0.0, gts,
                                       ORACLE_VARIANTS, width=width, llm_calls=1)
                entry[evaluation]["oracle_candidates"] = summarize_oracle(oracle_rows) | {"queries": len(oracle_covered)}
            per_query[name] = per_query_correct(rows)

    if args.method:
        absent = [name for name in args.method if name not in report["methods"]]
        if absent:
            raise SystemExit(
                f"no replies to score for {absent}: {method_cache_path('llm-set', args.method_model)} is missing; "
                f"python3 benchmarks/run_toolret_sae.py --stage methods --split {evaluation} --method {absent[0]} "
                f"--method-model {args.method_model}")

    for reference in args.reference or ["greedy", "llm-set"]:
        if reference in per_query:
            report["paired_vs_" + reference] = {
                name: bootstrap_difference(values, per_query[reference])
                for name, values in per_query.items() if name != reference
            }
    return report


def stage_substitutes(data: Data, model: str, output: Path, matching: str = "greedy",
                      labels: dict[str, dict[str, dict]] | None = None) -> None:
    """How much ToolRet's ranking metrics change when a labelled substitute counts as its gold tool.

    Scored on the stored ranking of every labelled query, three ways: the
    gold tools alone (ToolRet's own scoring), each gold tool or one of its
    substitutes, and the same restricted to the gold tools judged necessary.
    Substitutes are labelled among the top ``WIDE`` candidates only, which
    covers the top 10 these metrics read.

    ``matching`` is ``greedy`` (``toolret.group_metrics``, the published
    values) or ``matched`` (``toolret.group_metrics_matched``: one tool per
    group, credited independently of the order of the gold tools). The report
    records it as ``group_matching``; a file without that key is ``greedy``.
    ``labels`` replaces the label cache (published labels); every labelled
    query then needs its stored pool.
    """

    group_metrics = {"greedy": toolret.group_metrics, "matched": toolret.group_metrics_matched}[matching]

    labels = parsed_labels(data, model) if labels is None else labels
    unpooled = [query_id for query_id in labels if query_id not in data.pools]
    if unpooled or not labels:
        raise SystemExit(f"cannot score the substitutes: {len(unpooled) or 'no'} labelled queries have no stored pool; "
                         "run --stage pools for every split the labels cover (see README, ToolRet-SAE)")
    rows = []
    gold_tools = with_substitute = necessary_tools = 0
    for query in data.queries:
        if query.id not in labels:
            continue
        judged = labels[query.id]
        ranked = [row[0] for row in data.pools[query.id]]
        exact = [{gold} for gold in query.labels]
        groups = [{gold} | set(judged[gold]["substitutes"]) for gold in query.labels]
        needed = [group for gold, group in zip(query.labels, groups) if judged[gold]["necessary"]] or groups
        gold_tools += len(query.labels)
        with_substitute += sum(bool(judged[gold]["substitutes"]) for gold in query.labels)
        necessary_tools += sum(judged[gold]["necessary"] for gold in query.labels)
        rows.append({"subset": query.subset, "split": data.split(query), "multi": len(query.labels) > 1,
                     "gold": group_metrics(ranked, exact, 10),
                     "gold_or_substitute": group_metrics(ranked, groups, 10),
                     "necessary_gold_or_substitute": group_metrics(ranked, needed, 10)})

    def averages(selected: list[dict]) -> dict:
        result: dict[str, Any] = {"queries": len(selected)}
        for scoring in ("gold", "gold_or_substitute", "necessary_gold_or_substitute"):
            by_subset: dict[str, list[dict]] = {}
            for row in selected:
                by_subset.setdefault(row["subset"], []).append(row[scoring])
            result[scoring] = {
                f"{metric}@10": {
                    "micro": mean(row[scoring][metric] for row in selected),
                    "macro": mean(statistics.mean(item[metric] for item in items) for items in by_subset.values()),
                }
                for metric in ("ndcg", "recall", "complete")
            }
        return result

    report = {
        "benchmark": "ToolRet ranking metrics with labelled substitutes counted as their gold tool",
        "retriever": data.retriever, "label_model": model, "labelled_within_top": WIDE,
        "group_matching": matching,
        "gold_tools": gold_tools,
        "gold_tools_with_substitute": round(with_substitute / gold_tools, 4) if gold_tools else None,
        "gold_tools_necessary": round(necessary_tools / gold_tools, 4) if gold_tools else None,
        "all": averages(rows),
        "multi_tool": averages([row for row in rows if row["multi"]]),
        "by_split": {split: averages([row for row in rows if row["split"] == split])
                     for split in SPLITS if any(row["split"] == split for row in rows)},
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(stamp(report), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    overall = report["all"]
    print(f"{len(rows)} queries; substitutes for {report['gold_tools_with_substitute']} of gold tools")
    for scoring in ("gold", "gold_or_substitute", "necessary_gold_or_substitute"):
        print(f"  {scoring}: " + " ".join(f"{name} {value['macro']}" for name, value in overall[scoring].items()))
    print(f"wrote {output}")


def stage_heldout(data: Data, target: int) -> None:
    """Freeze the held-out query ids: queries outside the dev / test sample."""

    if toolret.SAE_HELDOUT_IDS.exists():
        raise SystemExit(f"{toolret.SAE_HELDOUT_IDS} already exists; the held-out split is frozen")
    chosen = toolret.select_heldout(data.all_queries, data.sample, target)
    ids = [query.id for query in chosen]
    subsets: dict[str, int] = {}
    for query in chosen:
        subsets[query.subset] = subsets.get(query.subset, 0) + 1
    payload = {
        "description": "ToolRet-SAE held-out split: ToolRet query ids outside the per-subset-60 seed-0 sample",
        "license": "CC0-1.0",
        "count": len(ids), "per_subset": dict(sorted(subsets.items())),
        "sha256": hashlib.sha256("\n".join(ids).encode("utf-8")).hexdigest(), "ids": ids,
    }
    toolret.SAE_HELDOUT_IDS.write_text(json.dumps(payload, indent=1) + "\n", encoding="utf-8")
    print(f"wrote {toolret.SAE_HELDOUT_IDS}: {len(ids)} queries over {len(subsets)} subsets")


def stage_fresh_heldout(data: Data, target: int, output: Path) -> None:
    """Freeze a split of queries no earlier evaluation read, by id or by text.

    Every query in the dev / test sample, in the full test split (the half of
    all queries that ``split_of`` assigns to test, which ``toolret-test-full``
    measured), and in the frozen ToolRet-SAE held-out list is left out, as is
    any query whose normalized text matches one of them. The split is a list
    of ids and does not change the dev / test / held-out splits above.
    """

    if output.exists():
        raise SystemExit(f"{output} already exists; the split is frozen")
    heldout = [query for query in data.queries if query.id in data.heldout_ids]
    prior = data.sample + [query for query in data.all_queries if split_of(query.id) == "test"] + heldout
    chosen = toolret.select_fresh_heldout(data.all_queries, prior, target)
    ids = [query.id for query in chosen]
    subsets: dict[str, int] = {}
    for query in chosen:
        subsets[query.subset] = subsets.get(query.subset, 0) + 1
    payload = {
        "description": "ToolRet query ids outside the per-subset-60 seed-0 sample, the full test split "
                       "(split_of == test), and the ToolRet-SAE held-out list, by id and by normalized text",
        "license": "CC0-1.0",
        "excluded": {"sample": len(data.sample), "full_test": sum(split_of(q.id) == "test" for q in data.all_queries),
                     "sae_heldout": len(heldout), "union_ids": len({query.id for query in prior})},
        "overlap_with_prior": toolret.prior_overlap(chosen, prior),
        "count": len(ids), "per_subset": dict(sorted(subsets.items())),
        "sha256": hashlib.sha256("\n".join(ids).encode("utf-8")).hexdigest(), "ids": ids,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, indent=1) + "\n", encoding="utf-8")
    print(f"wrote {output}: {len(ids)} queries over {len(subsets)} subsets")


def stage_export_labels(data: Data, model: str, output: Path) -> None:
    """Write the parsed labels (ToolRet ids and judgments only) next to the results."""

    labels = parsed_labels(data, model)
    known = {query.id: query for query in data.queries}
    # ``candidates_sha256``: the top-WIDE candidate ids in order, so a scorer can
    # tell labels made on other candidates from these (the first release has none).
    payload = {"license": "CC0-1.0 (the labels; ToolRet's queries and tool documents are not included)",
               "label_model": model, "wide_pool": WIDE,
               "queries": {query_id: {"split": split, "labels": labels[query_id],
                                      "candidates_sha256": candidates_digest(label_candidates(data, known[query_id]))}
                           for query_id, split in sorted((q.id, data.split(q)) for q in data.queries)
                           if query_id in labels}}
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(stamp(payload), indent=1, sort_keys=True) + "\n", encoding="utf-8")
    print(f"wrote {output}: {len(payload['queries'])} queries")


class ReplayCache(dict):
    """A reply cache that counts lookups of missing keys and never stores.

    A replayed selector records a failure both for a missing reply and for a
    cached reply it cannot use (unparseable); only the first is a
    gap in the stage, the second is the method's own output and is scored.
    """

    def __init__(self, data: dict) -> None:
        super().__init__(data)
        self.misses = 0

    def get(self, key, default=None):
        if key not in self:
            self.misses += 1
        return super().get(key, default)

    def __setitem__(self, key, value) -> None:
        return None


def _cached(selector, data: Data, query, variant: str, width: int = POOL) -> bool:
    """Whether the replayed selector has a cached reply for this selection."""

    before = selector.cache.misses
    selector.select(data.pool(query, variant, width), context=context(query, variant))
    return selector.cache.misses == before


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--stage", action="append", required=True,
                        choices=["heldout", "fresh-heldout", "pools", "label", "agree", "methods", "score", "export-labels",
                                 "substitutes"])
    parser.add_argument("--per-subset", type=int, default=60)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--heldout-target", type=int, default=850,
                        help="size of the held-out split (heldout stage) or the fresh split (fresh-heldout stage) to freeze")
    parser.add_argument("--fresh-output", default=str(toolret.SAE_FRESH_IDS),
                        help="fresh-heldout stage: where to write the frozen ids (refuses to overwrite)")
    parser.add_argument("--labels-input",
                        help="score stage: published labels (results/toolret-sae-heldout-labels.json) to score with "
                             "instead of the label cache; needs only the stored candidate pools")
    parser.add_argument("--retriever", default="llm:hybrid-0.5")
    parser.add_argument("--embed-model", default="sentence-transformers/all-MiniLM-L6-v2")
    parser.add_argument("--split", choices=["all", *SPLITS],
                        help="queries the pools, label and methods stages work on; required for them, so "
                             "the held-out split is never processed by default")
    parser.add_argument("--eval-split", choices=["test", "heldout"], default="heldout",
                        help="the split the score and agree stages report on")
    parser.add_argument("--limit", type=int, default=0, help="first N queries of the split (0 = all)")
    parser.add_argument("--sample", type=int, default=0,
                        help="N queries of the split in SHA-1 order of the id, across subsets (0 = all)")
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--label-model", default="sonnet")
    parser.add_argument("--agree-model", default="haiku")
    parser.add_argument("--agree-queries", type=int, default=200)
    parser.add_argument("--method-model", default="haiku")
    parser.add_argument("--method", action="append", choices=sorted(METHODS),
                        help="methods stage: the methods to run; score stage: the LLM methods reported on "
                             "the evaluation split (default: every method with cached replies)")
    parser.add_argument("--oracle", action="store_true", help="run the oracle-candidate S+ / E+ selections instead")
    parser.add_argument("--reference", action="append",
                        help="method the paired differences are taken against (repeatable; default: greedy, llm-set)")
    parser.add_argument("--output", default=str(Path(__file__).parent / "results" / "toolret-sae-heldout.json"))
    parser.add_argument("--labels-output",
                        default=str(Path(__file__).parent / "results" / "toolret-sae-heldout-labels.json"))
    parser.add_argument("--substitute-matching", choices=["greedy", "matched"], default="greedy",
                        help="substitutes stage: how a ranked tool is credited to a gold tool's group; greedy "
                             "reproduces the published values, matched does not depend on the gold tools' order")
    parser.add_argument("--substitutes-output",
                        default=str(Path(__file__).parent / "results" / "toolret-substitutes.json"))
    add_spend_arguments(parser)
    args = parser.parse_args()
    global SPEND_LEDGER
    SPEND_LEDGER = ledger_from_arguments(parser, args)

    if not (toolret.DATA_DIR / "tools" / "web.parquet").exists():
        raise SystemExit("ToolRet is not downloaded: python3 benchmarks/run_toolret_benchmark.py --download")
    data = Data(args.per_subset, args.seed, args.retriever)
    if "heldout" in args.stage:
        stage_heldout(data, args.heldout_target)
        data = Data(args.per_subset, args.seed, args.retriever)
    queries = [query for query in data.queries if args.split == "all" or data.split(query) == args.split]
    if args.split is None and {"pools", "label", "methods"} & set(args.stage):
        parser.error("--split is required for the pools, label and methods stages")
    if args.sample:
        queries = sorted(queries, key=lambda q: hashlib.sha1(q.id.encode("utf-8")).hexdigest())[: args.sample]
    if args.limit:
        queries = queries[: args.limit]
    if "fresh-heldout" in args.stage:
        stage_fresh_heldout(data, args.heldout_target, Path(args.fresh_output))
    if "pools" in args.stage:
        stage_pools(data, queries, args)
    queries = [query for query in queries if query.id in data.pools]
    if "label" in args.stage:
        stage_label(data, queries, args.label_model, args.workers)
    if "agree" in args.stage:
        pool = sorted((q for q in data.queries if data.split(q) == args.eval_split and q.id in data.pools),
                      key=lambda q: q.id)
        rng = random.Random(1)
        stage_label(data, rng.sample(pool, min(args.agree_queries, len(pool))), args.agree_model, args.workers)
    if "methods" in args.stage:
        stage_methods(data, queries, args.method_model, args.workers, args.method or ["llm-set"],
                      oracle=args.oracle, labels=parsed_labels(data, args.label_model))
    if "score" in args.stage:
        report = stamp(stage_score(data, args))
        output = Path(args.output)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        for name, entry in report["methods"].items():
            summary = entry[args.eval_split]
            print(f"{name}: macro {summary.get('macro_correct')} correct {summary.get('correct')} "
                  f"S unneeded esc {summary.get('S_unneeded_escalation')} calls {summary.get('llm_calls_mean')}")
        print(f"wrote {output}")
    if "substitutes" in args.stage:
        published = load_published_labels(Path(args.labels_input), data, args.label_model) if args.labels_input else None
        stage_substitutes(data, args.label_model, Path(args.substitutes_output), args.substitute_matching, published)
    if "export-labels" in args.stage:
        stage_export_labels(data, args.label_model, Path(args.labels_output))


if __name__ == "__main__":
    main()
