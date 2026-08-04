"""Tests for cross-encoder re-ranking (§15.7 項目4)."""

from __future__ import annotations

import unittest

from marmo_core import (
    CrossEncoderProvider,
    CrossEncoderRerankRetriever,
    LexicalRetriever,
    ResourceDefinition,
    SearchQuery,
)
from marmo_core.registry import ResourceRegistry


def _resource(resource_id: str, kind: str, description: str, **overrides) -> ResourceDefinition:
    payload = {
        "id": resource_id,
        "kind": kind,
        "name": resource_id,
        "version": "1.0.0",
        "description": description,
        "capabilities": [],
        "input_summary": "in",
        "output_summary": "out",
        "required_permissions": [],
        "cost_estimate": 0.0,
        "latency_class": "fast",
        "side_effect": "none",
        "trust_level": "core",
        "ref": f"{kind}://{resource_id}",
        "tags": [],
    }
    payload.update(overrides)
    return ResourceDefinition.from_mapping(payload)


class _KeywordCrossEncoder(CrossEncoderProvider):
    """Deterministic stub: emits a high logit for documents naming ``target``."""

    def __init__(self, target: str) -> None:
        self.target = target
        self.calls: list[tuple[str, int]] = []

    def score(self, query: str, documents):
        self.calls.append((query, len(documents)))
        return [6.0 if self.target in document else -6.0 for document in documents]


class _ConstantCrossEncoder(CrossEncoderProvider):
    def __init__(self, value: float = 0.0) -> None:
        self.value = value

    def score(self, query: str, documents):
        return [self.value] * len(documents)


class _BadCountCrossEncoder(CrossEncoderProvider):
    def score(self, query: str, documents):
        return [1.0]


def _registry() -> ResourceRegistry:
    registry = ResourceRegistry()
    registry.extend(
        [
            _resource(
                "skill.billing.invoices",
                "skill",
                "Procedure for billing runs covering invoices and payment terms.",
            ),
            _resource(
                "skill.billing.dunning",
                "skill",
                "Procedure for billing runs covering dunning letters and collections.",
            ),
            _resource(
                "skill.reporting.summary",
                "skill",
                "Procedure for billing summaries in executive reporting rollups.",
            ),
        ]
    )
    return registry


class CrossEncoderRerankRetrieverTests(unittest.TestCase):
    def setUp(self) -> None:
        self.registry = _registry()

    def test_reranks_pool_to_the_model_preference(self) -> None:
        provider = _KeywordCrossEncoder("dunning")
        retriever = CrossEncoderRerankRetriever(provider, LexicalRetriever())
        results = retriever.search(self.registry, SearchQuery(task="billing runs", top_k=3))
        self.assertEqual(results[0].resource.metadata.id, "skill.billing.dunning")
        self.assertEqual(provider.calls[0][0], "billing runs")

    def test_blended_relevance_is_exposed_in_components(self) -> None:
        retriever = CrossEncoderRerankRetriever(_KeywordCrossEncoder("dunning"), LexicalRetriever())
        results = retriever.search(self.registry, SearchQuery(task="billing runs", top_k=3))
        top = results[0]
        self.assertIn("cross_encoder", top.components)
        self.assertGreater(top.components["cross_encoder"], 0.9)
        self.assertAlmostEqual(top.components["relevance"], top.components["cross_encoder"])
        self.assertTrue(any("cross-encoder relevance" in reason for reason in top.reasons))

    def test_weight_zero_keeps_the_inner_relevance(self) -> None:
        inner = LexicalRetriever()
        query = SearchQuery(task="billing runs", top_k=3)
        baseline = {
            result.resource.metadata.id: result.components["relevance"]
            for result in inner.search(self.registry, query)
        }
        retriever = CrossEncoderRerankRetriever(
            _KeywordCrossEncoder("dunning"), inner, weight=0.0
        )
        for result in retriever.search(self.registry, query):
            self.assertAlmostEqual(
                result.components["relevance"], baseline[result.resource.metadata.id]
            )

    def test_empty_task_bypasses_the_model(self) -> None:
        provider = _KeywordCrossEncoder("dunning")
        retriever = CrossEncoderRerankRetriever(provider, LexicalRetriever())
        retriever.search(self.registry, SearchQuery(top_k=3))
        self.assertEqual(provider.calls, [])

    def test_respects_top_k_and_per_kind_limits(self) -> None:
        retriever = CrossEncoderRerankRetriever(_ConstantCrossEncoder(), LexicalRetriever())
        results = retriever.search(self.registry, SearchQuery(task="billing runs", top_k=2))
        self.assertEqual(len(results), 2)
        limited = retriever.search(
            self.registry,
            SearchQuery(task="billing runs", top_k=5, per_kind_limits={"skill": 1}),
        )
        self.assertEqual(len(limited), 1)

    def test_score_count_mismatch_is_rejected(self) -> None:
        retriever = CrossEncoderRerankRetriever(_BadCountCrossEncoder(), LexicalRetriever())
        with self.assertRaises(ValueError):
            retriever.search(self.registry, SearchQuery(task="billing runs", top_k=3))

    def test_invalid_construction_arguments(self) -> None:
        with self.assertRaises(ValueError):
            CrossEncoderRerankRetriever(_ConstantCrossEncoder(), LexicalRetriever(), weight=1.5)
        with self.assertRaises(ValueError):
            CrossEncoderRerankRetriever(
                _ConstantCrossEncoder(), LexicalRetriever(), temperature=0.0
            )


if __name__ == "__main__":
    unittest.main()
