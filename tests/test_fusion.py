"""Tests for Reciprocal Rank Fusion (RRFRetriever)."""

from __future__ import annotations

import unittest

from marmo_core import (
    ResourceDefinition,
    ResourceRegistry,
    Retriever,
    RRFRetriever,
    SearchQuery,
    SearchResult,
)


def _definition(resource_id: str, kind: str = "tool") -> ResourceDefinition:
    return ResourceDefinition.from_mapping(
        {
            "id": resource_id,
            "kind": kind,
            "name": resource_id,
            "version": "1.0.0",
            "description": f"resource {resource_id}",
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
    )


class _FixedRanking(Retriever):
    def __init__(self, ranking: list[ResourceDefinition], relevance: float) -> None:
        self.ranking = ranking
        self.relevance = relevance
        self.queries: list[SearchQuery] = []

    def search(self, registry, query):
        self.queries.append(query)
        return [
            SearchResult(definition, 1.0 - index * 0.1, (), {"relevance": self.relevance})
            for index, definition in enumerate(self.ranking[: query.top_k])
        ]


class RRFRetrieverTests(unittest.TestCase):
    def setUp(self) -> None:
        self.a, self.b, self.c = _definition("tool.a"), _definition("tool.b"), _definition("skill.c", kind="skill")
        self.registry = ResourceRegistry()

    def test_resource_ranked_well_by_both_lists_wins(self) -> None:
        first = _FixedRanking([self.a, self.b, self.c], relevance=0.7)
        second = _FixedRanking([self.b, self.c, self.a], relevance=0.4)
        results = RRFRetriever(first, second, k=1).search(self.registry, SearchQuery(task="t", top_k=3))
        # k=1: b gets 1/3 + 1/2, a gets 1/2 + 1/4, c gets 1/4 + 1/3.
        self.assertEqual([r.resource.metadata.id for r in results], ["tool.b", "tool.a", "skill.c"])
        self.assertAlmostEqual(results[0].score, (1 / 3 + 1 / 2) / (2 / 2))

    def test_components_come_from_the_first_list_and_rrf_is_exposed(self) -> None:
        first = _FixedRanking([self.a], relevance=0.7)
        second = _FixedRanking([self.c], relevance=0.4)
        results = RRFRetriever(first, second).search(self.registry, SearchQuery(task="t", top_k=5))
        by_id = {r.resource.metadata.id: r for r in results}
        self.assertEqual(by_id["tool.a"].components["relevance"], 0.7)
        self.assertEqual(by_id["skill.c"].components["relevance"], 0.4)
        self.assertIn("rrf", by_id["tool.a"].components)

    def test_inner_retrievers_are_widened_and_caller_limits_apply_after_fusion(self) -> None:
        first = _FixedRanking([self.a, self.b, self.c], relevance=0.7)
        second = _FixedRanking([self.c, self.a, self.b], relevance=0.4)
        query = SearchQuery(task="t", top_k=1, per_kind_limits={"tool": 1})
        results = RRFRetriever(first, second, depth=10).search(self.registry, query)
        self.assertEqual(len(results), 1)
        self.assertEqual(first.queries[0].top_k, 10)
        self.assertEqual(first.queries[0].per_kind_limits, {})

    def test_invalid_parameters_are_rejected(self) -> None:
        retriever = _FixedRanking([], relevance=0.0)
        with self.assertRaises(ValueError):
            RRFRetriever(retriever, retriever, k=0)
        with self.assertRaises(ValueError):
            RRFRetriever(retriever, retriever, depth=0)


if __name__ == "__main__":
    unittest.main()
