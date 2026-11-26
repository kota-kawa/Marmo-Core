"""Asymmetric embedding models: queries go through embed_queries, resources through embed."""

from __future__ import annotations

import unittest

from marmo_core import (
    HierarchicalRetriever,
    HybridRetriever,
    LexicalRetriever,
    NamespaceGrouping,
    ResourceDefinition,
    ResourceRegistry,
    SearchQuery,
)
from marmo_core.semantic import EmbeddingProvider, HashingEmbeddingProvider, embed_queries


def _registry() -> ResourceRegistry:
    registry = ResourceRegistry()
    for name in ("weather forecast lookup", "currency exchange rates"):
        registry.add(ResourceDefinition.from_mapping({
            "id": "tool.test." + name.split()[0], "kind": "tool", "name": name, "version": "1.0.0",
            "description": name, "capabilities": [], "input_summary": "in", "output_summary": "out",
            "required_permissions": [], "cost_estimate": 0.0, "latency_class": "fast",
            "side_effect": "none", "trust_level": "core", "ref": "tool://x", "tags": [],
        }))
    return registry


class RecordingAsymmetricProvider(EmbeddingProvider):
    def __init__(self) -> None:
        self.inner = HashingEmbeddingProvider(64)
        self.documents: list[str] = []
        self.queries: list[str] = []

    def embed(self, texts):
        self.documents.extend(texts)
        return self.inner.embed(texts)

    def embed_queries(self, texts):
        self.queries.extend(texts)
        return self.inner.embed(["query: " + text for text in texts])


class DuckTypedProvider:
    """A provider written against the original interface: embed only, no ABC."""

    def __init__(self) -> None:
        self.inner = HashingEmbeddingProvider(64)
        self.calls = 0

    def embed(self, texts):
        self.calls += 1
        return self.inner.embed(texts)


class QueryEmbeddingTests(unittest.TestCase):
    def test_default_embed_queries_is_embed(self) -> None:
        provider = HashingEmbeddingProvider(32)
        self.assertEqual(provider.embed_queries(["a b"]), provider.embed(["a b"]))

    def test_hybrid_retriever_embeds_the_goal_as_a_query(self) -> None:
        provider = RecordingAsymmetricProvider()
        HybridRetriever(provider).search(_registry(), SearchQuery(task="weather tomorrow", top_k=2))
        self.assertEqual(provider.queries, ["weather tomorrow"])
        self.assertNotIn("weather tomorrow", provider.documents)
        self.assertTrue(provider.documents)

    def test_hierarchical_routing_embeds_the_goal_as_a_query(self) -> None:
        provider = RecordingAsymmetricProvider()
        retriever = HierarchicalRetriever(LexicalRetriever(), NamespaceGrouping(), route_k=1,
                                          embedding_provider=provider)
        retriever.search(_registry(), SearchQuery(task="weather tomorrow", top_k=2))
        self.assertEqual(provider.queries, ["weather tomorrow"])
        self.assertNotIn("weather tomorrow", provider.documents)

    def test_providers_without_embed_queries_still_work(self) -> None:
        provider = DuckTypedProvider()
        results = HybridRetriever(provider).search(_registry(), SearchQuery(task="weather tomorrow", top_k=2))
        self.assertTrue(results)
        self.assertEqual(embed_queries(provider, ["x"]), provider.inner.embed(["x"]))


if __name__ == "__main__":
    unittest.main()
