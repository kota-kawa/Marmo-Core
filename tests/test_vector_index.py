"""Tests for the optional vector indexes behind HybridRetriever."""

from __future__ import annotations

import importlib.util
import unittest

from marmo_core import (
    EmbeddingProvider,
    ExactVectorIndex,
    HashingEmbeddingProvider,
    HNSWVectorIndex,
    HybridRetriever,
    ResourceDefinition,
    ResourceRegistry,
    SearchQuery,
)

HAS_NUMPY = importlib.util.find_spec("numpy") is not None
HAS_USEARCH = importlib.util.find_spec("usearch") is not None

TOPICS = [
    "send monthly invoices to customers",
    "audit the codebase for security vulnerabilities",
    "design a relational database schema",
    "translate the app into Japanese",
    "summarize customer support tickets",
    "deploy a new release with rollback",
    "plan interviews for engineering candidates",
    "review a supplier contract for risks",
    "rebuild the nightly data pipeline",
    "write marketing posts from a long article",
    "track churn and retention of users",
    "write a postmortem after an outage",
]


class _LetterCounts(EmbeddingProvider):
    """Non-negative letter-frequency vectors: cosines are positive and rarely tie."""

    def embed(self, texts):
        return [[float(text.lower().count(letter)) + 0.01 * index for index, letter in enumerate("abcdefghijklmnopqrstuvwxyz")] for text in texts]


def _registry() -> ResourceRegistry:
    registry = ResourceRegistry()
    for index, topic in enumerate(TOPICS):
        registry.add(
            ResourceDefinition.from_mapping(
                {
                    "id": f"tool.t{index:02d}",
                    "kind": "tool",
                    "name": f"Tool {index}",
                    "version": "1.0.0",
                    "description": topic,
                    "capabilities": [],
                    "input_summary": "in",
                    "output_summary": "out",
                    "required_permissions": [],
                    "cost_estimate": 0.0,
                    "latency_class": "fast",
                    "side_effect": "none",
                    "trust_level": "core",
                    "ref": f"tool://t{index}",
                    "tags": [],
                }
            )
        )
    return registry


def _ranking(retriever: HybridRetriever, registry: ResourceRegistry, task: str) -> list[tuple[str, float]]:
    results = retriever.search(registry, SearchQuery(task=task, top_k=12))
    return [(r.resource.metadata.id, round(r.score, 6)) for r in results]


@unittest.skipUnless(HAS_NUMPY, "numpy is not installed")
class ExactVectorIndexTests(unittest.TestCase):
    def test_hybrid_ranking_matches_the_pure_python_path(self) -> None:
        registry = _registry()
        provider = _LetterCounts()
        plain = HybridRetriever(provider, semantic_weight=0.7, candidate_pool=4)
        indexed = HybridRetriever(provider, semantic_weight=0.7, candidate_pool=4, vector_index=ExactVectorIndex)
        for task in ("bill our clients", "find holes attackers could use", "make the app speak Japanese"):
            self.assertEqual(_ranking(plain, registry, task), _ranking(indexed, registry, task), task)

    def test_index_is_rebuilt_only_when_registry_text_changes(self) -> None:
        registry = _registry()
        built: list[int] = []

        class CountingIndex(ExactVectorIndex):
            def build(self, ids, vectors):
                built.append(len(ids))
                super().build(ids, vectors)

        retriever = HybridRetriever(HashingEmbeddingProvider(dimensions=64), vector_index=CountingIndex)
        retriever.search(registry, SearchQuery(task="invoices", top_k=3))
        retriever.search(registry, SearchQuery(task="contracts", top_k=3))
        self.assertEqual(built, [len(TOPICS)])

    def test_nearest_excludes_ids_and_orders_by_similarity(self) -> None:
        index = ExactVectorIndex()
        index.build(["a", "b", "c"], [[1.0, 0.0], [0.8, 0.6], [0.0, 1.0]])
        self.assertEqual([identity for identity, _ in index.nearest([1.0, 0.0], 3)], ["a", "b", "c"])
        self.assertEqual([identity for identity, _ in index.nearest([1.0, 0.0], 2, exclude={"a"})], ["b", "c"])
        self.assertAlmostEqual(index.similarity([1.0, 0.0], ["b"])["b"], 0.8, places=5)


@unittest.skipUnless(HAS_NUMPY and HAS_USEARCH, "numpy or usearch is not installed")
class HNSWVectorIndexTests(unittest.TestCase):
    def test_small_catalog_neighbors_match_exact_search(self) -> None:
        registry = _registry()
        provider = _LetterCounts()
        exact = HybridRetriever(provider, semantic_weight=0.7, candidate_pool=4, vector_index=ExactVectorIndex)
        approximate = HybridRetriever(provider, semantic_weight=0.7, candidate_pool=4, vector_index=HNSWVectorIndex)
        for task in ("bill our clients", "plan hiring interviews"):
            self.assertEqual(
                [identity for identity, _ in _ranking(exact, registry, task)],
                [identity for identity, _ in _ranking(approximate, registry, task)],
                task,
            )


if __name__ == "__main__":
    unittest.main()
