"""ToolRet: a public, large-scale tool-retrieval benchmark, adapted to Marmo-Core.

ToolRet (Shi et al., "Retrieval Models Aren't Tool-Savvy: Benchmarking Tool
Retrieval for Large Language Models", ACL 2025 Findings) pools 35 existing
tool-use datasets into one corpus of 44,453 tools and 7,961 queries. Most
queries from ToolBench, ToolLens, Tool-Be-Honest, ReverseChain, UltraTool and
several others need *several* tools, so the benchmark measures what the
in-repository suites cannot: whether a router finds the complete tool set for
a task in a catalog four orders of magnitude larger than the set itself, with
labels written by other people.

This module downloads the dataset on demand (it is **not** redistributed:
the corpus aggregates sources under different licenses, and the dataset card
states none), converts every tool document into a ``tool`` resource, and
provides the ranking and set metrics. Data lives under
``benchmarks/data/toolret`` (git-ignored). Reading parquet needs ``pyarrow``
(the ``benchmark-toolret`` extra); dense retrieval needs ``fastembed`` (the
``benchmark`` extra).

Conversion keeps every resource's policy metadata identical (same trust,
side effect, latency, cost, permissions), so the composite score orders
resources by text relevance alone and the comparison isolates retrieval.
"""

from __future__ import annotations

import hashlib
import json
import random
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Iterable, Mapping, Sequence
import math

DATA_DIR = Path(__file__).parent / "data" / "toolret"
HF_BASE = "https://huggingface.co/datasets/mangopy"
TOOL_CONFIGS = ("code", "customized", "web")
QUERY_CONFIGS = (
    "apibank", "apigen", "appbench", "autotools-food", "autotools-music", "autotools-weather",
    "craft-math-algebra", "craft-tabmwp", "craft-vqa", "gorilla-huggingface", "gorilla-pytorch",
    "gorilla-tensor", "gpt4tools", "gta", "metatool", "mnms", "restgpt-spotify", "restgpt-tmdb",
    "reversechain", "rotbench", "t-eval-dialog", "t-eval-step", "taskbench-daily",
    "taskbench-huggingface", "taskbench-multimedia", "tool-be-honest", "toolace", "toolalpaca",
    "toolbench-sam", "toolbench", "toolemu", "tooleyes", "toolink", "toollens", "ultratool",
)

_FIELD_LIMIT = 600
_DESCRIPTION_KEYS = ("description", "functionality", "description_for_human", "summary", "func_description")
_NAME_KEYS = ("name", "api_name", "toolkit", "name_for_human")
_INPUT_KEYS = (
    "parameters", "required_parameters", "optional_parameters", "doc_arguments", "inputs",
    "api_arguments", "additional_required_arguments", "optional_arguments", "required",
)
_OUTPUT_KEYS = ("output", "outputs", "responses", "response", "return_data", "result_arguments", "template_response")
_CATEGORY_KEYS = ("category_name", "category", "domain", "framework")


@dataclass(frozen=True)
class ToolRetQuery:
    id: str
    subset: str
    query: str
    instruction: str
    labels: tuple[str, ...]


# Commits of the two dataset repositories at the time this benchmark was built
# (both unchanged since March 2025). ``download`` fetches these unless told
# otherwise, so a rerun reads the same files even if ``main`` moves.
DATASET_REVISIONS = {
    "ToolRet-Tools": "e06c38c75612b6536bd959e08cdd345894aba6a7",
    "ToolRet-Queries": "b8c76ad3349ff17497b6bdb28bb5b8f61a0f6445",
}
MANIFEST = "manifest.json"


@dataclass(frozen=True)
class DataSnapshot:
    """What is in a ToolRet data directory, for a result file to record.

    ``revisions`` maps each dataset repository to the commit its files came
    from, or ``None`` when some file has no recorded origin (data fetched
    before the manifest existed) or the files come from different commits.
    ``files`` maps each parquet path, relative to ``data_dir``, to its SHA-256.
    """

    data_dir: Path
    revisions: dict[str, str | None]
    files: dict[str, str]

    def to_record(self) -> dict[str, Any]:
        digest = hashlib.sha256("\n".join(f"{name} {value}" for name, value in sorted(self.files.items())).encode("utf-8"))
        return {"revisions": dict(self.revisions), "files": dict(sorted(self.files.items())),
                "files_sha256": digest.hexdigest()}


def _targets() -> list[tuple[str, str, str]]:
    """(dataset repository, path inside it, path under the data directory) for every parquet file."""

    tools = [("ToolRet-Tools", f"{name}/tools-00000-of-00001.parquet", f"tools/{name}.parquet") for name in TOOL_CONFIGS]
    queries = [("ToolRet-Queries", f"{name}/queries-00000-of-00001.parquet", f"queries/{name}.parquet") for name in QUERY_CONFIGS]
    return tools + queries


def resolve_revision(repository: str, revision: str) -> str:
    """The commit SHA a branch, tag, or SHA of ``repository`` names right now."""

    url = f"https://huggingface.co/api/datasets/mangopy/{repository}/revision/{revision}"
    request = urllib.request.Request(url, headers={"User-Agent": "marmo-core-benchmark"})
    with urllib.request.urlopen(request, timeout=60) as response:
        return str(json.loads(response.read())["sha"])


def _read_manifest(data_dir: Path) -> dict[str, dict[str, str]]:
    path = data_dir / MANIFEST
    if not path.exists():
        return {}
    return dict(json.loads(path.read_text(encoding="utf-8")).get("files", {}))


def snapshot(data_dir: Path = DATA_DIR) -> DataSnapshot:
    """Hash the parquet files under ``data_dir`` and read where each came from."""

    recorded = _read_manifest(data_dir)
    files: dict[str, str] = {}
    origins: dict[str, set[str | None]] = {}
    for repository, _, relative in _targets():
        path = data_dir / relative
        if not path.exists():
            continue
        files[relative] = hashlib.sha256(path.read_bytes()).hexdigest()
        entry = recorded.get(relative)
        origins.setdefault(repository, set()).add(entry["revision"] if entry and entry.get("revision") else None)
    revisions = {repository: (next(iter(found)) if len(found) == 1 else None) for repository, found in origins.items()}
    return DataSnapshot(data_dir, revisions, files)


def download(
    data_dir: Path = DATA_DIR, *, force: bool = False, revisions: Mapping[str, str] | None = None
) -> DataSnapshot:
    """Fetch the ToolRet parquet files once into ``data_dir``.

    ``revisions`` maps ``"ToolRet-Tools"`` and ``"ToolRet-Queries"`` to the
    branch, tag, or commit to read; the default is ``DATASET_REVISIONS``
    (pass ``"main"`` for the moving head). The name is resolved to a commit
    first, files are fetched from that commit, and the commit of each file is
    kept in ``data_dir/manifest.json``. A file already present is kept (it was
    fetched earlier, possibly from another commit); ``force=True`` replaces
    every file. The returned snapshot has the commits and file hashes to store
    in a result file.
    """

    wanted = {**DATASET_REVISIONS, **(revisions or {})}
    unknown = set(wanted) - set(DATASET_REVISIONS)
    if unknown:
        raise ValueError(f"unknown ToolRet dataset repositories: {sorted(unknown)}")
    commits: dict[str, str] = {}
    recorded = _read_manifest(data_dir)
    for repository, path_in_repository, relative in _targets():
        target = data_dir / relative
        if target.exists() and not force:
            continue
        if repository not in commits:
            commits[repository] = resolve_revision(repository, wanted[repository])
        url = f"{HF_BASE}/{repository}/resolve/{commits[repository]}/{path_in_repository}"
        target.parent.mkdir(parents=True, exist_ok=True)
        request = urllib.request.Request(url, headers={"User-Agent": "marmo-core-benchmark"})
        with urllib.request.urlopen(request, timeout=120) as response:
            payload = response.read()
        target.write_bytes(payload)
        recorded[relative] = {"repository": repository, "revision": commits[repository]}
        (data_dir / MANIFEST).write_text(json.dumps({"files": recorded}, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    return snapshot(data_dir)


def _read_parquet(path: Path) -> list[dict[str, Any]]:
    try:
        import pyarrow.parquet as pq
    except ImportError as error:  # pragma: no cover - environment dependent
        raise SystemExit("reading ToolRet needs pyarrow: pip install '.[benchmark-toolret]'") from error
    return pq.read_table(path).to_pylist()


def load_tools(data_dir: Path = DATA_DIR) -> dict[str, dict[str, Any]]:
    """Tool id -> parsed documentation (dict, or {"description": text})."""

    tools: dict[str, dict[str, Any]] = {}
    for name in TOOL_CONFIGS:
        for row in _read_parquet(data_dir / "tools" / f"{name}.parquet"):
            try:
                documentation = json.loads(row["documentation"])
            except (TypeError, ValueError):
                documentation = {"description": str(row["documentation"])}
            if not isinstance(documentation, dict):
                documentation = {"description": json.dumps(documentation, ensure_ascii=False)}
            tools[row["id"]] = documentation
    return tools


def load_queries(data_dir: Path = DATA_DIR, subsets: Iterable[str] = QUERY_CONFIGS) -> list[ToolRetQuery]:
    queries: list[ToolRetQuery] = []
    for subset in subsets:
        for row in _read_parquet(data_dir / "queries" / f"{subset}.parquet"):
            labels = row["labels"]
            if isinstance(labels, str):
                labels = json.loads(labels)
            label_ids = tuple(dict.fromkeys(str(label["id"]) for label in labels))
            queries.append(
                ToolRetQuery(
                    id=str(row["id"]),
                    subset=subset,
                    query=str(row["query"]).strip(),
                    instruction=str(row.get("instruction") or "").strip(),
                    labels=label_ids,
                )
            )
    return queries


def sample_queries(queries: Sequence[ToolRetQuery], per_subset: int | None, seed: int = 0) -> list[ToolRetQuery]:
    """At most ``per_subset`` queries from every subset, deterministically."""

    if per_subset is None:
        return list(queries)
    by_subset: dict[str, list[ToolRetQuery]] = {}
    for query in queries:
        by_subset.setdefault(query.subset, []).append(query)
    rng = random.Random(seed)
    sampled: list[ToolRetQuery] = []
    for subset in sorted(by_subset):
        rows = sorted(by_subset[subset], key=lambda q: q.id)
        if len(rows) > per_subset:
            rows = sorted(rng.sample(rows, per_subset), key=lambda q: q.id)
        sampled.extend(rows)
    return sampled


SAE_HELDOUT_IDS = Path(__file__).parent / "toolret_sae_heldout_ids.json"
SAE_FRESH_IDS = Path(__file__).parent / "toolret_sae_fresh_ids.json"


def normalize_text(text: str) -> str:
    """Whitespace-collapsed, case-folded query text, for finding the same request under another id."""

    return " ".join(text.split()).casefold()


def _spread_over_subsets(
    queries: Sequence[ToolRetQuery], used: Sequence[ToolRetQuery], target: int, key: Callable[[ToolRetQuery], str]
) -> list[ToolRetQuery]:
    seen = {key(query) for query in used}
    used_ids = {query.id for query in used}
    by_subset: dict[str, list[ToolRetQuery]] = {}
    for query in sorted(queries, key=lambda q: hashlib.sha1(q.id.encode("utf-8")).hexdigest()):
        if query.id in used_ids or key(query) in seen:
            continue
        seen.add(key(query))
        by_subset.setdefault(query.subset, []).append(query)
    largest = max((len(rows) for rows in by_subset.values()), default=0)
    cap = min(range(largest + 1), key=lambda c: abs(sum(min(len(rows), c) for rows in by_subset.values()) - target))
    return sorted((query for rows in by_subset.values() for query in rows[:cap]), key=lambda q: q.id)


def select_heldout(queries: Sequence[ToolRetQuery], used: Sequence[ToolRetQuery], target: int) -> list[ToolRetQuery]:
    """About ``target`` queries that are not in ``used``, spread over the subsets.

    A query whose text also appears in ``used`` is left out, as is a repeat of
    a text already taken (texts compared as written). Every subset contributes
    its first queries in SHA-1 order of the id, up to one cap chosen so the
    total is closest to ``target``; no random state is involved. This produced
    ``toolret_sae_heldout_ids.json``; its result must not change.
    """

    return _spread_over_subsets(queries, used, target, lambda query: query.query)


def select_fresh_heldout(queries: Sequence[ToolRetQuery], prior: Sequence[ToolRetQuery], target: int) -> list[ToolRetQuery]:
    """Like ``select_heldout``, with ``prior`` meaning every query any earlier evaluation read.

    Texts are compared after ``normalize_text``, so a request that reappears
    under another id, in another case, or with different spacing is also left
    out. Use it to freeze a split for a claim of "data no earlier result used";
    ``select_heldout`` keeps its original rule so the frozen split it made
    stays reproducible.
    """

    return _spread_over_subsets(queries, prior, target, lambda query: normalize_text(query.query))


def prior_overlap(queries: Sequence[ToolRetQuery], prior: Sequence[ToolRetQuery]) -> dict[str, int]:
    """How many of ``queries`` an earlier evaluation already covered.

    ``same_id`` counts ids found in ``prior``; ``same_text_other_id`` counts
    queries whose id is not in ``prior`` but whose normalized text is.
    """

    prior_ids = {query.id for query in prior}
    prior_texts = {normalize_text(query.query) for query in prior}
    same_id = sum(query.id in prior_ids for query in queries)
    same_text = sum(query.id not in prior_ids and normalize_text(query.query) in prior_texts for query in queries)
    return {"queries": len(queries), "same_id": same_id, "same_text_other_id": same_text}


def load_heldout(queries: Sequence[ToolRetQuery], path: Path = SAE_HELDOUT_IDS) -> list[ToolRetQuery]:
    """The held-out queries frozen in ``path`` (empty when it does not exist)."""

    if not path.exists():
        return []
    ids = set(json.loads(path.read_text(encoding="utf-8"))["ids"])
    return sorted((query for query in queries if query.id in ids), key=lambda q: q.id)


# -- conversion ----------------------------------------------------------------


def _flatten(value: Any, budget: int = _FIELD_LIMIT) -> str:
    """Names and descriptions inside a nested parameter/response structure."""

    parts: list[str] = []

    def walk(node: Any, key: str = "") -> None:
        if sum(len(part) for part in parts) > budget:
            return
        if isinstance(node, dict):
            for child_key, child in node.items():
                if child_key in {"type", "in", "default", "required", "enum"} and not isinstance(child, (dict, list)):
                    continue
                parts.append(str(child_key))
                walk(child, str(child_key))
        elif isinstance(node, list):
            for child in node:
                walk(child, key)
        elif node is not None and not isinstance(node, bool):
            text = str(node).strip()
            if text and key not in {"type", "in", "default"}:
                parts.append(text)

    walk(value)
    return " ".join(parts)[:budget]


def tool_resource(tool_id: str, documentation: dict[str, Any]) -> dict[str, Any]:
    """A Marmo ``tool`` resource mapping for one ToolRet tool document."""

    name = next((str(documentation[key]) for key in _NAME_KEYS if documentation.get(key)), tool_id)
    description = next(
        (str(documentation[key]).strip() for key in _DESCRIPTION_KEYS if str(documentation.get(key) or "").strip()),
        "",
    )
    if documentation.get("tools") and isinstance(documentation["tools"], list):
        # ToolEmu toolkits list their member functions.
        description = (description + " " + _flatten(documentation["tools"], 400)).strip()
    if not description:
        description = _flatten(documentation)
    inputs = " ".join(_flatten(documentation[key], 400) for key in _INPUT_KEYS if documentation.get(key))
    outputs = " ".join(_flatten(documentation[key], 300) for key in _OUTPUT_KEYS if documentation.get(key))
    categories = tuple(
        str(documentation[key]).strip()[:80] for key in _CATEGORY_KEYS if isinstance(documentation.get(key), str) and documentation[key].strip()
    )
    digest = hashlib.sha1(tool_id.encode("utf-8")).hexdigest()[:10]
    return {
        "id": f"tool.toolret.{digest}",
        "kind": "tool",
        "name": name[:200],
        "version": "1.0.0",
        "description": description[:_FIELD_LIMIT * 2] or name,
        "capabilities": list(categories),
        "input_summary": inputs or "none",
        "output_summary": outputs or "none",
        "required_permissions": [],
        "cost_estimate": 0.0,
        "latency_class": "fast",
        "side_effect": "read",
        "trust_level": "verified",
        "ref": f"toolret:{digest}",
        "tags": [],
        "toolret_id": tool_id,
    }


# -- metrics ---------------------------------------------------------------------


def ndcg_at_k(ranked: Sequence[str], gold: set[str], k: int) -> float:
    dcg = sum(1.0 / math.log2(rank + 2) for rank, item in enumerate(ranked[:k]) if item in gold)
    ideal = sum(1.0 / math.log2(rank + 2) for rank in range(min(len(gold), k)))
    return dcg / ideal if ideal else 0.0


def recall_at_k(ranked: Sequence[str], gold: set[str], k: int) -> float:
    return len(set(ranked[:k]) & gold) / len(gold) if gold else 0.0


def completeness_at_k(ranked: Sequence[str], gold: set[str], k: int) -> float:
    """1.0 when every gold tool is in the top k (ToolRet's C@k, COLT's COMP@k)."""

    return 1.0 if gold and gold <= set(ranked[:k]) else 0.0


def group_metrics(ranked: Sequence[str], groups: Sequence[set[str]], k: int) -> dict[str, float]:
    """nDCG, recall and completeness at ``k`` when any member of a group satisfies it (metric version 1).

    A group is a gold tool with the tools accepted in its place. Each ranked
    tool is credited to at most one group still unmet (the first in
    ``groups`` order), so a tool that could stand in for two gold tools counts
    once, and the scores stay within [0, 1]. The crediting is greedy, so the
    result depends on the order of ``groups`` and recall can be low: with
    ``ranked = [s, a]`` and groups ``{a, s}``, ``{s}`` it credits ``s`` to the
    first group and scores 0.5, but 1.0 when the groups are listed the other
    way round. Published values use this version;
    ``group_metrics_matched`` removes the order dependence. With one-member
    groups this is ``ndcg_at_k`` / ``recall_at_k`` / ``completeness_at_k``.
    """

    unmet = list(range(len(groups)))
    dcg = 0.0
    for position, tool in enumerate(ranked[:k]):
        hit = next((index for index in unmet if tool in groups[index]), None)
        if hit is not None:
            unmet.remove(hit)
            dcg += 1.0 / math.log2(position + 2)
    ideal = sum(1.0 / math.log2(position + 2) for position in range(min(len(groups), k)))
    met = len(groups) - len(unmet)
    return {
        "ndcg": dcg / ideal if ideal else 0.0,
        "recall": met / len(groups) if groups else 0.0,
        "complete": float(bool(groups) and not unmet),
    }


def group_metrics_matched(ranked: Sequence[str], groups: Sequence[set[str]], k: int) -> dict[str, float]:
    """``group_metrics`` with one tool per group, chosen so the groups' order does not matter (version 2).

    Each group needs its own ranked tool: one substitute that fits two gold
    tools satisfies one of them, as in a ranking where every slot is one tool.
    Walking down the ranking, a tool is credited when the credited tools stay
    assignable to distinct groups (an augmenting path exists), so recall is the
    size of a maximum matching, and which tools are credited depends on the
    ranking only. ``sufficient`` in ``run_toolret_sae.py`` is the other
    meaning: a selected set covers a group when it holds any member, and one
    tool may cover several groups.
    """

    owner: dict[int, int] = {}  # group index -> ranked position credited to it

    def assign(position: int, visited: set[int]) -> bool:
        for index, group in enumerate(groups):
            if ranked[position] in group and index not in visited:
                visited.add(index)
                if index not in owner or assign(owner[index], visited):
                    owner[index] = position
                    return True
        return False

    for position in range(min(k, len(ranked))):
        assign(position, set())
    dcg = sum(1.0 / math.log2(position + 2) for position in set(owner.values()))
    ideal = sum(1.0 / math.log2(position + 2) for position in range(min(len(groups), k)))
    return {
        "ndcg": dcg / ideal if ideal else 0.0,
        "recall": len(owner) / len(groups) if groups else 0.0,
        "complete": float(bool(groups) and len(owner) == len(groups)),
    }


def set_scores(selected: set[str], gold: set[str]) -> dict[str, float]:
    hits = len(selected & gold)
    precision = hits / len(selected) if selected else 0.0
    recall = hits / len(gold) if gold else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return {
        "precision": precision,
        "recall": recall,
        "f1": f1,
        "exact": 1.0 if selected == gold else 0.0,
        "complete": 1.0 if gold <= selected else 0.0,
        "size": float(len(selected)),
    }


# -- embeddings --------------------------------------------------------------------


class CachedEmbeddingProvider:
    """A fastembed model whose vectors persist under ``benchmarks/cache``.

    Embedding 44k tool documents on a CPU takes minutes, and every retriever
    configuration in a run embeds the same texts; the cache is keyed by the
    SHA-1 of the text, so changing the conversion re-embeds only what moved.

    Texts are cut to ``max_chars`` before embedding (the head of a tool
    document carries its name and description; at 512 tokens a CPU embeds
    under two documents a second), and uncached texts are embedded in length
    order so a batch pads to its own longest member.
    """

    def __init__(
        self,
        model: str,
        cache_dir: Path | None = None,
        *,
        threads: int | None = None,
        max_chars: int = 512,
        query_prefix: str = "",
    ) -> None:
        try:
            from fastembed import TextEmbedding
        except ImportError as error:  # pragma: no cover - environment dependent
            raise SystemExit("dense retrieval needs fastembed: pip install '.[benchmark]'") from error
        import numpy

        self._numpy = numpy
        self.model_name = model
        self._model = TextEmbedding(model, threads=threads)
        self.max_chars = max_chars
        # Asymmetric retrieval models expect an instruction on queries only.
        self.query_prefix = query_prefix
        self.checkpoint_every = 2000
        slug = f"{model.replace('/', '__')}-{max_chars}"
        self.cache_dir = cache_dir or Path(__file__).parent / "cache" / "embeddings"
        self._keys_path = self.cache_dir / f"{slug}.keys.json"
        self._vectors_path = self.cache_dir / f"{slug}.npy"
        self._index: dict[str, int] = {}
        self._vectors = None
        if self._keys_path.exists() and self._vectors_path.exists():
            keys = json.loads(self._keys_path.read_text(encoding="utf-8"))
            self._vectors = numpy.load(self._vectors_path)
            self._index = {key: position for position, key in enumerate(keys)}
        self._pending: dict[str, list[float]] = {}

    @staticmethod
    def _key(text: str) -> str:
        return hashlib.sha1(text.encode("utf-8")).hexdigest()

    def embed(self, texts: Sequence[str]) -> list[list[float]]:
        texts = [text[: self.max_chars] for text in texts]
        keys = [self._key(text) for text in texts]
        missing = [(key, text) for key, text in zip(keys, texts) if key not in self._index and key not in self._pending]
        if missing:
            unique = sorted(dict(missing).items(), key=lambda item: len(item[1]))
            vectors = self._model.embed([text for _, text in unique], batch_size=32)
            for position, ((key, _), vector) in enumerate(zip(unique, vectors), start=1):
                self._pending[key] = [float(value) for value in vector]
                # Embedding the corpus takes up to hours on a CPU; persist as it
                # goes so an interrupted run resumes instead of starting over.
                if position % self.checkpoint_every == 0:
                    self.save()
                    print(f"  embedded {position}/{len(unique)} with {self.model_name}", flush=True)
        output = []
        for key in keys:
            if key in self._pending:
                output.append(self._pending[key])
            else:
                assert self._vectors is not None
                output.append(self._vectors[self._index[key]].tolist())
        return output

    def embed_queries(self, texts: Sequence[str]) -> list[list[float]]:
        return self.embed([self.query_prefix + text for text in texts])

    def save(self) -> None:
        if not self._pending:
            return
        numpy = self._numpy
        keys = sorted(self._index, key=self._index.__getitem__) + list(self._pending)
        fresh = numpy.asarray(list(self._pending.values()), dtype=numpy.float32)
        vectors = fresh if self._vectors is None else numpy.concatenate([self._vectors, fresh])
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        numpy.save(self._vectors_path, vectors)
        self._keys_path.write_text(json.dumps(keys), encoding="utf-8")
        self._vectors = vectors
        self._index = {key: position for position, key in enumerate(keys)}
        self._pending = {}


def build_registry(tools: dict[str, dict[str, Any]]):
    """The 44k-tool registry, and Marmo id -> ToolRet id."""

    from marmo_core import ResourceDefinition, ResourceRegistry

    registry = ResourceRegistry()
    to_toolret: dict[str, str] = {}
    for tool_id, documentation in tools.items():
        mapping = tool_resource(tool_id, documentation)
        registry.add(ResourceDefinition.from_mapping(mapping))
        to_toolret[mapping["id"]] = tool_id
    return registry, to_toolret
