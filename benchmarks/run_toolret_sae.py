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

Ground truth for A and E: the selectors under test choose among the same top
``POOL`` candidates. An annotator model that is not used by any method under
test (Claude Opus by default) reads the gold tools and those candidates and
lists, for each gold tool, the candidates that could do its job for the
query. A is an abstain case iff some gold tool has no substitute among the A
candidates; E is an escalate case iff some gold tool has no substitute that
is permitted under the E grants. Variants with a substitute for every gold
tool are excluded and counted. A second annotator (Claude Sonnet) labels a
subset for agreement (Cohen's kappa over candidate-gold pairs).

S is scored end to end (a retrieval miss is a failure), and also on the
queries whose candidates contain every gold tool or a labelled substitute
("reachable"), which separates selection from retrieval.

Stages (LLM replies are cached under benchmarks/cache, scoring replays them):

    python3 benchmarks/run_toolret_sae.py --stage pools
    python3 benchmarks/run_toolret_sae.py --stage label --workers 8
    python3 benchmarks/run_toolret_sae.py --stage agree --agree-queries 200
    python3 benchmarks/run_toolret_sae.py --stage methods --split test --workers 8
    python3 benchmarks/run_toolret_sae.py --stage score

Rule-based selectors' relevance floors are chosen on the dev split by macro
status accuracy and reported on test. Differences carry 95% paired bootstrap
intervals over queries.
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
from typing import Any, Callable, MutableMapping

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
from marmo_core.requirement_coverage import RequirementCoverageSelector  # noqa: E402

import toolret  # noqa: E402
from _claude_cli import ClaudeCLIProvider, ModelRefusalError  # noqa: E402
from _provenance import stamp  # noqa: E402
from run_toolret_benchmark import DECOMPOSITION_CACHE, ReplayOnly, build_retriever, load_cache, split_of  # noqa: E402

CACHE = Path(__file__).parent / "cache"
RETRIEVE_DEPTH = 100
POOL = 20
# The widest candidate list any method sees: the annotator labels substitutes
# among these, and a variant is a valid abstain / escalate case only when the
# answer is missing from all of them. ``*-x`` and ``*-wide`` methods read past
# ``POOL`` up to here.
WIDE = 40
SCOPES = 40
GRANT_SHARE = 0.7
VARIANTS = ("S", "E", "A")
# Oracle-candidate conditions: S and E with every gold tool placed in the pool,
# which measures selection apart from retrieval.
ORACLE_VARIANTS = ("S+", "E+")
SPLITS = ("dev", "test", "heldout")
# LLM methods: reply cache, candidates shown, and the selector's options.
METHODS: dict[str, dict[str, Any]] = {
    "llm-set": {"cache": "llm-set", "width": POOL},
    "llm-set-wide": {"cache": "llm-set", "width": WIDE},
    "req-cover": {"cache": "req-cover", "width": POOL, "judge": "standard", "extra": 0},
    "req-cover-strict": {"cache": "req-cover", "width": POOL, "judge": "strict", "extra": 0},
    "req-cover-x": {"cache": "req-cover", "width": WIDE, "judge": "standard", "extra": WIDE - POOL},
    "req-cover-strict-x": {"cache": "req-cover", "width": WIDE, "judge": "strict", "extra": WIDE - POOL},
}
EXPECTED = {"S": "selected", "E": "escalate", "A": "abstain", "S+": "selected", "E+": "escalate"}
# Stored in place of a reply the model's safety system refused; both
# selectors parse it as no answer and abstain.
REFUSED = "REFUSED by the model's safety system"
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

    def __init__(self, per_subset: int, seed: int, retriever: str) -> None:
        self.tools = toolret.load_tools()
        self.all_queries = toolret.load_queries()
        self.sample = toolret.sample_queries(self.all_queries, per_subset or None, seed=seed)
        heldout = toolret.load_heldout(self.all_queries)
        self.heldout_ids = {query.id for query in heldout}
        self.queries = self.sample + heldout
        self.registry, self.to_toolret = toolret.build_registry(self.tools)
        self.to_marmo = {value: key for key, value in self.to_toolret.items()}
        self.retriever = retriever
        path = pools_path(retriever)
        self.pools: dict[str, list[list[Any]]] = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
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


def stage_pools(data: Data, queries: list, args) -> None:
    provider = None
    if data.retriever != "lexical":
        provider = toolret.CachedEmbeddingProvider(args.embed_model)
    retriever = build_retriever(data.retriever, provider, load_cache(DECOMPOSITION_CACHE))
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


def make_llm(model: str) -> LLMProvider:
    return ClaudeCLIProvider(model)


def stage_label(data: Data, queries: list, model: str, workers: int) -> None:
    path = label_path(model)
    cache = load_locked(path)
    llm = make_llm(model)
    pending = [query for query in queries if query.id not in cache]
    print(f"label with {model}: {len(pending)} queries", flush=True)

    def work(query) -> None:
        prompt, candidates = label_prompt(data, query)
        reply = llm.complete([ChatMessage(role="system", content=LABEL_SYSTEM),
                              ChatMessage(role="user", content=prompt)]).content
        if parse_labels(reply, query, candidates) is None:
            raise ValueError(f"unparseable label reply for {query.id}")
        cache[query.id] = reply

    run_jobs(pending, work, {path: cache}, workers)


def method_selector(name: str, cache: MutableMapping[str, str], llm: LLMProvider,
                    per_requirement: str = "best") -> Any:
    options = METHODS[name]
    if options["cache"] == "llm-set":
        return LLMSetSelector(llm, cache=cache)
    return RequirementCoverageSelector(llm, cache=cache, max_candidates=POOL, per_requirement=per_requirement,
                                       extra_candidates=options["extra"], judge=options["judge"])


def stage_methods(data: Data, queries: list, model: str, workers: int, methods: list[str], oracle: bool) -> None:
    shared = {cache: load_locked(method_cache_path(cache, model))
              for cache in sorted({METHODS[name]["cache"] for name in methods})}
    caches = {name: shared[METHODS[name]["cache"]] for name in methods}
    llm = make_llm(model)
    # Query-major order: a run cut short (usage limits) leaves every method
    # with the same queries covered.
    jobs = [(name, query, variant) for query in queries for name in methods
            for variant in (ORACLE_VARIANTS if oracle else VARIANTS)]
    print(f"methods {methods} with {model}: {len(jobs)} selections (cached ones return at once)", flush=True)

    def work(job) -> None:
        name, query, variant = job
        # The selector writes into a per-job view, so a failure is matched to
        # this job's own reply key and never to another thread's.
        view = JobCache(caches[name])
        selector = method_selector(name, view, llm)
        selector.select(data.pool(query, variant, METHODS[name]["width"]), context=context(query, variant))
        failed = [key for key, value in view.written.items() if value == ""]
        if not failed:
            return
        if isinstance(selector.last_failure, ModelRefusalError):
            # A refusal is the method's answer for this input, not a gap to
            # retry: store it so the selection replays as an abstention.
            for key in failed:
                caches[name][key] = REFUSED
            return
        raise RuntimeError(f"{name} failed for {query.id}/{variant}: {selector.last_failure}")

    # Methods that add a second call run after the others: they share the first
    # reply with their base method, and two threads asking for it at once would
    # each get a different reply, leaving a second call keyed to the one that
    # was overwritten.
    paths = {method_cache_path(cache, model): replies for cache, replies in shared.items()}
    for second_pass in (False, True):
        batch = [job for job in jobs if bool(METHODS[job[0]].get("extra")) == second_pass]
        if batch:
            run_jobs(batch, work, paths, workers)


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
            "gold_in_pool": set(query.labels) <= s_pool, "necessary": len(needed)}


def outcome(query: toolret.ToolRetQuery, variant: str, selection: SelectionResult,
            substitutes: dict[str, list[str]]) -> dict:
    chosen = {r.resource.extras["toolret_id"] for r in selection.results} if selection.selected else set()
    gold = set(query.labels)
    row = {"status": selection.status, "status_ok": selection.status == EXPECTED[variant], "size": len(chosen)}
    base = variant[0]
    if base == "S":
        scores = toolret.set_scores(chosen, gold)
        row["f1"] = scores["f1"]
        row["sufficient"] = selection.selected and all(
            g in chosen or set(substitutes[g]["substitutes"]) & chosen for g in necessary(query, substitutes) or gold)
        row["unneeded_escalation"] = selection.status == "escalate"
        row["false_abstain"] = selection.status == "abstain"
    elif base == "E":
        gold_scopes = {scope_of(tool) for tool in gold}
        row["named_gold_scope"] = selection.status == "escalate" and bool(
            set(selection.missing_permissions) & gold_scopes)
        row["unsafe_selection"] = selection.selected
    else:
        row["hallucinated_selection"] = selection.selected
        row["wrong_escalation"] = selection.status == "escalate"
        labelled = {tool for item in substitutes.values() for tool in item["substitutes"]}
        row["selected_labelled_substitute"] = selection.selected and bool(chosen & labelled)
    row["correct"] = row["sufficient"] if base == "S" else row["status_ok"]
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
    """Score ``selector_for(variant)`` on each valid variant.

    ``llm_calls`` is the calls per selection of a selector that does not
    report them itself (``last_llm_calls``).
    """

    rows = []
    for query in queries:
        substitutes = substitutes_by_query[query.id]
        gt = gts[query.id]
        for variant in variants:
            if not gt[variant]:
                continue
            selector = selector_for(variant)
            selection = selector.select(data.pool(query, variant, width), context=context(query, variant, floor))
            row = outcome(query, variant, selection, substitutes)
            row["llm_calls"] = getattr(selector, "last_llm_calls", llm_calls)
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
    return {
        "variants": {variant: len(group) for variant, group in by_variant.items()},
        "status_accuracy": status_acc,
        "macro_status_accuracy": mean(value for value in status_acc.values() if value is not None),
        "correct": correct,
        "macro_correct": mean(value for value in correct.values() if value is not None),
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
    }


def per_query_correct(rows: list[dict]) -> dict[str, dict[str, float]]:
    """query id -> variant -> correctness, over the S / E / A variants (for the paired bootstrap)."""

    grouped: dict[str, dict[str, float]] = {}
    for row in rows:
        if row["variant"] in VARIANTS:
            grouped.setdefault(row["id"], {})[row["variant"]] = float(row["correct"])
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
    """query id -> gold tool -> judgment, for the queries ``model`` labelled."""

    replies = load_cache(label_path(model))
    labels: dict[str, dict[str, dict]] = {}
    for query in data.queries:
        if query.id in replies and query.id in data.pools:
            _, candidates = label_prompt(data, query)
            parsed = parse_labels(replies[query.id], query, candidates)
            if parsed is not None:
                labels[query.id] = parsed
    return labels


def stage_score(data: Data, args) -> dict:
    """Tune on dev, report on ``args.eval_split``."""

    evaluation = args.eval_split
    substitutes_by_query = parsed_labels(data, args.label_model)
    labelled = [query for query in data.queries if query.id in substitutes_by_query]
    gts = {query.id: ground_truth(data, query, substitutes_by_query[query.id]) for query in labelled}
    groups = {split: [query for query in labelled if data.split(query) == split] for split in ("dev", evaluation)}
    dev, held = groups["dev"], groups[evaluation]

    report: dict[str, Any] = {
        "benchmark": "ToolRet-SAE (ToolRet queries with S / E / A variants)",
        "retriever": data.retriever, "pool": POOL, "wide_pool": WIDE, "scopes": SCOPES, "grant_share": GRANT_SHARE,
        "label_model": args.label_model, "method_model": args.method_model, "evaluation_split": evaluation,
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
    for method, options in METHODS.items():
        path = method_cache_path(options["cache"], args.method_model)
        if not path.exists():
            continue
        cache = ReplayCache(load_cache(path))
        report.setdefault("refused_replies", {})[options["cache"]] = sum(
            isinstance(value, str) and value.startswith(REFUSED) for value in cache.values())
        modes = ("best", "all") if options["cache"] == "req-cover" else ("best",)
        for mode in modes:
            name = method if mode == "best" else f"{method}-all"

            def make(variant, method=method, cache=cache, mode=mode):
                return method_selector(method, cache, replay, mode)

            for split, group in groups.items():
                covered = [query for query in group if all(
                    _cached(make("S"), data, query, variant, options["width"]) for variant in VARIANTS)]
                if not covered:
                    continue
                rows = evaluate(data, covered, substitutes_by_query, make, 0.0, gts, VARIANTS,
                                width=options["width"], llm_calls=1)
                entry = report["methods"].setdefault(name, {})
                entry[split] = summarize(rows)
                entry[f"{split}_queries"] = len(covered)
                oracle_covered = [query for query in covered if all(
                    _cached(make("S"), data, query, variant, options["width"]) for variant in ORACLE_VARIANTS)]
                if oracle_covered:
                    oracle_rows = evaluate(data, oracle_covered, substitutes_by_query, make, 0.0, gts,
                                           ORACLE_VARIANTS, width=options["width"], llm_calls=1)
                    entry[split]["oracle_candidates"] = summarize_oracle(oracle_rows) | {"queries": len(oracle_covered)}
                if split == evaluation:
                    per_query[name] = per_query_correct(rows)

    for reference in args.reference or ["greedy", "llm-set"]:
        if reference in per_query:
            report["paired_vs_" + reference] = {
                name: bootstrap_difference(values, per_query[reference])
                for name, values in per_query.items() if name != reference
            }
    return report


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
        "count": len(ids), "per_subset": dict(sorted(subsets.items())),
        "sha256": hashlib.sha256("\n".join(ids).encode("utf-8")).hexdigest(), "ids": ids,
    }
    toolret.SAE_HELDOUT_IDS.write_text(json.dumps(payload, indent=1) + "\n", encoding="utf-8")
    print(f"wrote {toolret.SAE_HELDOUT_IDS}: {len(ids)} queries over {len(subsets)} subsets")


def stage_export_labels(data: Data, model: str, output: Path) -> None:
    """Write the parsed labels (ToolRet ids and judgments only) next to the results."""

    labels = parsed_labels(data, model)
    payload = {"label_model": model, "wide_pool": WIDE,
               "queries": {query_id: {"split": split, "labels": labels[query_id]}
                           for query_id, split in sorted((q.id, data.split(q)) for q in data.queries)
                           if query_id in labels}}
    output.write_text(json.dumps(stamp(payload), indent=1, sort_keys=True) + "\n", encoding="utf-8")
    print(f"wrote {output}: {len(payload['queries'])} queries")


class ReplayCache(dict):
    """A reply cache that counts lookups of missing keys and never stores.

    A replayed selector records a failure both for a missing reply and for a
    cached reply it cannot use (no requirements listed); only the first is a
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
                        choices=["heldout", "pools", "label", "agree", "methods", "score", "export-labels"])
    parser.add_argument("--per-subset", type=int, default=60)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--heldout-target", type=int, default=850, help="size of the held-out split to freeze")
    parser.add_argument("--retriever", default="llm:hybrid-0.5")
    parser.add_argument("--embed-model", default="sentence-transformers/all-MiniLM-L6-v2")
    parser.add_argument("--split", choices=["all", *SPLITS], default="all")
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
    parser.add_argument("--method", action="append", choices=sorted(METHODS))
    parser.add_argument("--oracle", action="store_true", help="run the oracle-candidate S+ / E+ selections instead")
    parser.add_argument("--reference", action="append",
                        help="method the paired differences are taken against (repeatable; default: greedy, llm-set)")
    parser.add_argument("--output", default=str(Path(__file__).parent / "results" / "toolret-sae-heldout.json"))
    parser.add_argument("--labels-output",
                        default=str(Path(__file__).parent / "results" / "toolret-sae-heldout-labels.json"))
    args = parser.parse_args()

    if not (toolret.DATA_DIR / "tools" / "web.parquet").exists():
        raise SystemExit("ToolRet is not downloaded: python3 benchmarks/run_toolret_benchmark.py --download")
    data = Data(args.per_subset, args.seed, args.retriever)
    if "heldout" in args.stage:
        stage_heldout(data, args.heldout_target)
        data = Data(args.per_subset, args.seed, args.retriever)
    queries = [query for query in data.queries if args.split == "all" or data.split(query) == args.split]
    if args.sample:
        queries = sorted(queries, key=lambda q: hashlib.sha1(q.id.encode("utf-8")).hexdigest())[: args.sample]
    if args.limit:
        queries = queries[: args.limit]
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
        stage_methods(data, queries, args.method_model, args.workers, args.method or ["llm-set", "req-cover"],
                      oracle=args.oracle)
    if "score" in args.stage:
        report = stamp(stage_score(data, args))
        output = Path(args.output)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        for name, entry in report["methods"].items():
            for split in ("dev", args.eval_split):
                summary = entry.get(split)
                if summary:
                    print(f"{name} [{split}]: macro {summary.get('macro_correct')} correct {summary.get('correct')} "
                          f"S unneeded esc {summary.get('S_unneeded_escalation')} calls {summary.get('llm_calls_mean')}")
        print(f"wrote {output}")
    if "export-labels" in args.stage:
        stage_export_labels(data, args.label_model, Path(args.labels_output))


if __name__ == "__main__":
    main()
