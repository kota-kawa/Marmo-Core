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
from typing import Any, Iterable, Sequence
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


def download(data_dir: Path = DATA_DIR, *, force: bool = False) -> Path:
    """Fetch the ToolRet parquet files once into ``data_dir``."""

    targets = [(f"{HF_BASE}/ToolRet-Tools/resolve/main/{name}/tools-00000-of-00001.parquet", data_dir / "tools" / f"{name}.parquet") for name in TOOL_CONFIGS]
    targets += [(f"{HF_BASE}/ToolRet-Queries/resolve/main/{name}/queries-00000-of-00001.parquet", data_dir / "queries" / f"{name}.parquet") for name in QUERY_CONFIGS]
    for url, path in targets:
        if path.exists() and not force:
            continue
        path.parent.mkdir(parents=True, exist_ok=True)
        request = urllib.request.Request(url, headers={"User-Agent": "marmo-core-benchmark"})
        with urllib.request.urlopen(request, timeout=120) as response:
            payload = response.read()
        path.write_bytes(payload)
    return data_dir


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


def select_heldout(queries: Sequence[ToolRetQuery], used: Sequence[ToolRetQuery], target: int) -> list[ToolRetQuery]:
    """About ``target`` queries that are not in ``used``, spread over the subsets.

    A query whose text also appears in ``used`` is left out, as is a repeat of
    a text already taken. Every subset contributes its first queries in SHA-1
    order of the id, up to one cap chosen so the total is closest to
    ``target``; no random state is involved.
    """

    seen = {query.query for query in used}
    used_ids = {query.id for query in used}
    by_subset: dict[str, list[ToolRetQuery]] = {}
    for query in sorted(queries, key=lambda q: hashlib.sha1(q.id.encode("utf-8")).hexdigest()):
        if query.id in used_ids or query.query in seen:
            continue
        seen.add(query.query)
        by_subset.setdefault(query.subset, []).append(query)
    largest = max((len(rows) for rows in by_subset.values()), default=0)
    cap = min(range(largest + 1), key=lambda c: abs(sum(min(len(rows), c) for rows in by_subset.values()) - target))
    return sorted((query for rows in by_subset.values() for query in rows[:cap]), key=lambda q: q.id)


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
