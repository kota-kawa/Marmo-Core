"""Paired 100k flat ANN versus hierarchical retrieval comparison.

Both arms use the same corpus, query set, embeddings, lexical scorer, blend
weight, pool size, and constrained selector. Hash vectors are the quick
algorithmic baseline; --embedding model uses the real benchmark model. ANN is
an optional benchmark dependency and does not enter the runtime package.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from dataclasses import replace
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).parent))

from marmo_core import (  # noqa: E402
    HashingEmbeddingProvider,
    HierarchicalRetriever,
    HybridRetriever,
    LexicalRetriever,
    NamespaceGrouping,
    load_registry,
)
from marmo_core.retriever import RELEVANCE_WEIGHT  # noqa: E402
from marmo_core.models import SearchResult  # noqa: E402
from marmo_core.semantic import _cosine_01  # noqa: E402

from _provenance import stamp  # noqa: E402
from generate_scale_corpus import ensure_scale_corpus  # noqa: E402
from run_scale_benchmark import run_one  # noqa: E402


class FlatAnnHybrid(HybridRetriever):
    """Benchmark-only swap of full cosine scan for USearch nearest neighbors."""

    def __init__(self, provider, *, pool: int = 50, weight: float = 0.9) -> None:
        super().__init__(provider, lexical=LexicalRetriever(), semantic_weight=weight, candidate_pool=pool)
        self._index = None
        self._identities: list[str] = []
        self._vectors = {}
        self.index_seconds = 0.0
        self.index_bytes = 0

    def _ensure_index(self, registry) -> None:
        if self._index is not None:
            return
        try:
            import numpy as np
            from usearch.index import Index
        except ImportError as error:
            raise SystemExit("flat ANN benchmark needs pip install '.[benchmark-ann]'") from error
        start = time.perf_counter()
        self._vectors = self._vectors_for(registry)
        self._identities = list(self._vectors)
        matrix = np.asarray([self._vectors[identity] for identity in self._identities], dtype=np.float32)
        index = Index(ndim=matrix.shape[1], metric="cos", dtype="f32", connectivity=16,
                      expansion_add=128, expansion_search=128)
        index.add(np.arange(len(matrix), dtype=np.uint64), matrix)
        self._index = index
        self.index_seconds = time.perf_counter() - start
        self.index_bytes = index.memory_usage

    def search(self, registry, query):
        if not query.task.strip():
            return self.lexical.search(registry, query)
        self._ensure_index(registry)
        import numpy as np

        widened = replace(query, top_k=max(query.top_k, self.candidate_pool),
                          per_kind_limits={}, min_score=0.0)
        candidates = self.lexical.search(registry, widened)
        query_vector = self._query_vector(query.task)
        assert self._index is not None
        matches = self._index.search(np.asarray(query_vector, dtype=np.float32),
                                     min(self.candidate_pool + len(candidates), len(self._identities)))
        pooled = {result.resource.identity for result in candidates}
        nearest = [self._identities[int(match.key)] for match in matches
                   if self._identities[int(match.key)] not in pooled][:self.candidate_pool]
        candidates += self.lexical.score_semantic_candidates(registry, widened, nearest)
        rescored = []
        for result in candidates:
            semantic = _cosine_01(query_vector, self._vectors[result.resource.identity])
            lexical = float(result.components.get("relevance", 0.0))
            blended = (1.0 - self.semantic_weight) * lexical + self.semantic_weight * semantic
            score = max(0.0, min(1.0, result.score + RELEVANCE_WEIGHT * (blended - lexical)))
            components = dict(result.components)
            components.update(semantic=semantic, relevance=blended)
            rescored.append(SearchResult(result.resource, score,
                                         result.reasons + (f"semantic similarity {semantic:.2f}",), components))
        rescored.sort(key=lambda item: (item.score, item.resource.metadata.trust_level != "untrusted",
                                        item.resource.metadata.id), reverse=True)
        return self.lexical.apply_limits([item for item in rescored if item.score >= query.min_score], query)


def run(*, size: int, embedding: str, pool: int, route_k: int, min_relevance: float,
        model_name: str = "BAAI/bge-small-en-v1.5") -> dict:
    if embedding == "model":
        from run_benchmark import FastembedEmbeddingProvider

        provider = FastembedEmbeddingProvider(model_name)
        model = provider.model_name
    else:
        provider = HashingEmbeddingProvider(dimensions=64)
        model = "hash-64 (non-semantic control)"
    paths = [str(Path(__file__).parent / "corpus/set_corpus.json"), str(ensure_scale_corpus(size))]
    registry = load_registry(paths)
    by_id = {definition.metadata.id: definition for definition in registry.all()}
    scenarios = json.loads((Path(__file__).parent / "set_scenarios.json").read_text(encoding="utf-8"))["scenarios"]
    scenarios += json.loads((Path(__file__).parent / "scale_scenarios.json").read_text(encoding="utf-8"))["scenarios"]
    args = argparse.Namespace(pool=pool, route_k=route_k, min_score=0.45, min_relevance=min_relevance)
    flat = FlatAnnHybrid(provider, pool=pool)
    hierarchical = HierarchicalRetriever(
        HybridRetriever(provider, semantic_weight=0.9, candidate_pool=pool),
        NamespaceGrouping(), route_k=route_k,
    )
    flat_result = run_one("flat-ann", flat, registry, by_id, scenarios, args)
    hierarchical_result = run_one("hier-namespace", hierarchical, registry, by_id, scenarios, args)
    return {
        "corpus_size": len(registry), "scenarios": len(scenarios), "embedding": model,
        "pool": pool, "route_k": route_k, "min_relevance": min_relevance,
        "ann_parameters": {"metric": "cos", "dtype": "f32", "connectivity": 16,
                           "expansion_add": 128, "expansion_search": 128},
        "flat_ann_index_seconds_including_embeddings": round(flat.index_seconds, 3),
        "flat_ann_index_bytes": flat.index_bytes,
        "retrievers": {"flat-ann": flat_result, "hier-namespace": hierarchical_result},
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--size", type=int, default=100_000)
    parser.add_argument("--embedding", choices=("hash", "model"), default="hash")
    parser.add_argument("--model", default="BAAI/bge-small-en-v1.5")
    parser.add_argument("--pool", type=int, default=50)
    parser.add_argument("--route-k", type=int, default=3)
    parser.add_argument("--min-relevance", type=float, default=0.35)
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args()
    report = stamp(run(size=args.size, embedding=args.embedding, pool=args.pool,
                       route_k=args.route_k, min_relevance=args.min_relevance, model_name=args.model))
    output = args.output or Path(__file__).parent / "results" / f"ann-scale-{args.embedding}-{args.size}.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    for name, row in report["retrievers"].items():
        print(f"{name}: recall {row['retrieval_gold_recall']:.3f} Set F1 {row['set_f1']:.3f} "
              f"p50 {row['latency_ms_p50']:.1f}ms p95 {row['latency_ms_p95']:.1f}ms")
    print(f"report written to {output}")


if __name__ == "__main__":
    main()
