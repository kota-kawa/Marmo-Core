"""Candidate pools: the Kernel's pool construction as a replaceable component."""

from __future__ import annotations

import unittest

from marmo_core import (
    CandidatePool,
    CandidatePoolRequest,
    Kernel,
    KindBalancedCandidatePool,
    LexicalRetriever,
    MockLLMProvider,
    PolicyContext,
    PolicyGateway,
    ResourceDefinition,
    ResourceRegistry,
    Retriever,
    RetrieverCandidatePool,
    RuleBasedSetSelector,
    SearchQuery,
    SearchResult,
)

GOAL = "Add 2 and 3 with the calculator"


def _fields(resource_id: str, kind: str = "tool", **overrides) -> dict:
    data = {
        "id": resource_id,
        "kind": kind,
        "name": resource_id,
        "version": "1.0.0",
        "description": f"{kind} resource: add numbers with a calculator",
        "capabilities": ["calculator"],
        "input_summary": "numbers",
        "output_summary": "sum",
        "required_permissions": [],
        "cost_estimate": 0.0,
        "latency_class": "fast",
        "side_effect": "none",
        "trust_level": "core",
        "ref": f"{kind}://test/{resource_id}",
        "tags": ["calculator"],
    }
    if kind == "tool":
        data["input_schema"] = {"type": "object", "properties": {}}
    if kind == "skill":
        data["instructions"] = ["use the calculator"]
    data.update(overrides)
    return data


def _registry(*entries: dict) -> ResourceRegistry:
    registry = ResourceRegistry()
    for entry in entries:
        registry.add(ResourceDefinition.from_mapping(entry))
    return registry


def _request(registry: ResourceRegistry, *, denied: set[str], **overrides) -> CandidatePoolRequest:
    values = dict(
        goal=GOAL,
        registry=registry,
        retriever=LexicalRetriever(),
        granted_permissions=(),
        top_k=8,
        per_kind_limits={"tool": 3},
        min_score=0.0,
        is_denied=lambda result: result.resource.metadata.id in denied,
    )
    values.update(overrides)
    return CandidatePoolRequest(**values)


def _ids(results: list[SearchResult]) -> list[str]:
    return [result.resource.metadata.id for result in results]


class CandidatePoolTests(unittest.TestCase):
    def setUp(self) -> None:
        self.registry = _registry(
            _fields("tool.test.add"),
            _fields("tool.test.pay", description="tool resource: add numbers and pay"),
            _fields("tool.test.sum", description="tool resource: add numbers"),
        )

    def test_retriever_pool_returns_the_ranking_unchanged(self) -> None:
        request = _request(self.registry, denied={"tool.test.add", "tool.test.pay"})
        ranking = LexicalRetriever().search(self.registry, SearchQuery(task=GOAL, top_k=8))
        self.assertEqual(_ids(RetrieverCandidatePool().build(request)), _ids(ranking))

    def test_kind_balanced_pool_keeps_only_the_best_denied_match_of_a_kind(self) -> None:
        ranking = _ids(RetrieverCandidatePool().build(_request(self.registry, denied=set())))
        best, *rest = ranking
        pool = KindBalancedCandidatePool().build(_request(self.registry, denied=set(ranking)))
        self.assertEqual(_ids(pool), [best])
        pool = KindBalancedCandidatePool().build(
            _request(self.registry, denied=set(ranking), keep_best_denied_of_kind=False)
        )
        self.assertEqual(_ids(pool), [])
        self.assertEqual(len(rest), 2)


class _FixedRanking(Retriever):
    """A retriever with a fixed ranking: a weak Tool in the first search, a strong one for a Tool-only search."""

    def __init__(self, registry: ResourceRegistry) -> None:
        self.registry = registry
        self.queries: list[SearchQuery] = []

    def search(self, registry: ResourceRegistry, query: SearchQuery) -> list[SearchResult]:
        self.queries.append(query)
        if query.kinds == ("tool",):
            rows = [("tool.test.strong", 0.8)]
        else:
            rows = [("tool.test.weak", 0.2), ("skill.test.note", 0.7)]
        return [
            SearchResult(registry.get(identity), score, (), {"relevance": score})
            for identity, score in rows
        ]


class WeakCandidatesDoNotFillTheSlotsTests(unittest.TestCase):
    """A candidate the selector drops for its score must not count as filling its kind."""

    def setUp(self) -> None:
        self.registry = _registry(
            _fields("tool.test.weak"),
            _fields("tool.test.strong"),
            _fields("skill.test.note", "skill"),
        )

    def test_the_pool_tops_up_a_kind_whose_only_match_is_under_the_score_floor(self) -> None:
        retriever = _FixedRanking(self.registry)
        request = _request(
            self.registry, denied=set(), retriever=retriever, per_kind_limits={"tool": 1, "skill": 1}, min_score=0.5
        )
        pool = KindBalancedCandidatePool().build(request)

        self.assertIn("tool.test.strong", _ids(pool))
        self.assertEqual([query.kinds for query in retriever.queries], [(), ("tool",)])

    def test_a_match_over_the_floor_still_fills_its_kind_without_a_top_up(self) -> None:
        retriever = _FixedRanking(self.registry)
        request = _request(
            self.registry, denied=set(), retriever=retriever, per_kind_limits={"tool": 1, "skill": 1}, min_score=0.1
        )
        pool = KindBalancedCandidatePool().build(request)

        self.assertEqual(_ids(pool), ["tool.test.weak", "skill.test.note"])
        self.assertEqual(len(retriever.queries), 1)

    def test_the_default_kernel_offers_the_selector_the_strong_tool(self) -> None:
        retriever = _FixedRanking(self.registry)
        kernel = Kernel(
            self.registry,
            MockLLMProvider(),
            retriever=retriever,
            selector=RuleBasedSetSelector(min_score=0.5),
            set_limits={"tool": 1},
            tool_implementations={"tool.test.strong": lambda: {}, "tool.test.weak": lambda: {}},
            policy_context=PolicyContext(),
            gateway=PolicyGateway(),
        )
        kernel.run_goal(GOAL)

        retrieve = next(record.payload for record in kernel.audit_log.records if record.kind == "retrieve")
        self.assertIn("tool.test.strong@1.0.0", retrieve["selected"])
        self.assertNotIn("tool.test.weak@1.0.0", retrieve["selected"])


class KernelCandidatePoolTests(unittest.TestCase):
    def test_the_kernel_hands_selection_the_configured_pool(self) -> None:
        registry = _registry(_fields("tool.test.add"), _fields("skill.test.sum", "skill"))
        requests: list[CandidatePoolRequest] = []

        class RecordingPool(CandidatePool):
            def build(self, request: CandidatePoolRequest) -> list[SearchResult]:
                requests.append(request)
                return [
                    result
                    for result in RetrieverCandidatePool().build(request)
                    if result.resource.kind == "skill"
                ]

        kernel = Kernel(
            registry,
            MockLLMProvider(),
            candidate_pool=RecordingPool(),
            tool_implementations={"tool.test.add": lambda: {}},
            policy_context=PolicyContext(),
            gateway=PolicyGateway(),
        )
        result = kernel.run_goal(GOAL)

        self.assertEqual(len(requests), 1)
        self.assertEqual(requests[0].goal, GOAL)
        self.assertEqual(requests[0].per_kind_limits["tool"], 3)
        retrieve = next(record.payload for record in kernel.audit_log.records if record.kind == "retrieve")
        self.assertEqual(retrieve["selected"], ["skill.test.sum@1.0.0"])
        self.assertEqual(result.tool_results, ())


if __name__ == "__main__":
    unittest.main()
