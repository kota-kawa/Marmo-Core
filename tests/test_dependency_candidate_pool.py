from __future__ import annotations

import unittest

from marmo_core import (
    CandidatePoolLimitError, DependencyExpandedCandidatePool, Kernel,
    GoalAwareSetSelector, MockLLMProvider, PolicyContext, PolicyGateway, Retriever, SearchResult, TaskSpec,
)
from tests.test_candidate_pool import _fields, _ids, _registry, _request


class _Roots(Retriever):
    def __init__(self, *ids: str) -> None:
        self.ids = ids

    def search(self, registry, query):
        return [SearchResult(registry.get(rid), .8, ("root",), {"relevance": .8}) for rid in self.ids]


class DependencyCandidatePoolTests(unittest.TestCase):
    def test_finds_transitive_dependencies_without_rewarding_their_count(self):
        registry = _registry(_fields("a", dependencies=["b"]),
                             _fields("b", dependencies=["c"]),
                             _fields("c", dependencies=["a"]))
        pool = DependencyExpandedCandidatePool()
        results = pool.build(_request(registry, denied=set(), retriever=_Roots("a")))
        self.assertEqual(_ids(results), ["a", "b", "c"])
        self.assertEqual([r.score for r in results], [.8, 0, 0])
        self.assertEqual([r.components["relevance"] for r in results], [.8, 0, 0])
        self.assertEqual(pool.last_added_ids, ("b@1.0.0", "c@1.0.0"))

    def test_discovers_all_context_choices_without_choosing_or_authorizing_them(self):
        contract = {"schema_version": 1, "observed": True, "complete": True,
                    "affordances": [], "context": {"all_of": ["b"], "one_of": [["missing", "c", "d"]]},
                    "call_preconditions": [], "permissions": [], "source_evidence": ["unit fixture"]}
        registry = _registry(_fields("a", routing_contract=contract), _fields("b"),
                             _fields("c", required_permissions=["extra"]), _fields("d"))
        pool = DependencyExpandedCandidatePool()
        request = _request(registry, denied=set(), retriever=_Roots("a"))
        results = pool.build(request)
        self.assertEqual(_ids(results), ["a", "b", "c", "d"])
        self.assertEqual(pool.last_missing_references, ("missing",))
        self.assertEqual(request.granted_permissions, ())
        self.assertTrue(PolicyGateway().evaluate(registry.get("c"), PolicyContext()).denied)

    def test_does_not_expose_denied_disabled_or_ambiguous_dependencies(self):
        registry = _registry(_fields("a", dependencies=["blocked", "disabled", "versioned"]),
                             _fields("blocked"), _fields("disabled"),
                             _fields("versioned"), _fields("versioned", version="2.0.0"))
        registry.disable("disabled")
        pool = DependencyExpandedCandidatePool()
        results = pool.build(_request(registry, denied={"blocked"}, retriever=_Roots("a")))
        self.assertEqual(_ids(results), ["a"])
        self.assertEqual(pool.last_missing_references, ("blocked", "disabled", "versioned"))

    def test_pinned_version_and_duplicate_roots_are_deterministic(self):
        registry = _registry(_fields("a", dependencies=["b@1.0.0"]),
                             _fields("b"), _fields("b", version="2.0.0"))
        pool = DependencyExpandedCandidatePool()
        results = pool.build(_request(registry, denied=set(), retriever=_Roots("a", "a")))
        self.assertEqual([r.resource.identity for r in results], ["a@1.0.0", "b@1.0.0"])

    def test_overflow_is_explicit_and_not_a_successful_truncated_pool(self):
        registry = _registry(_fields("a", dependencies=["b"]), _fields("b"))
        pool = DependencyExpandedCandidatePool(max_candidates=1)
        with self.assertRaisesRegex(CandidatePoolLimitError, "coverage is incomplete"):
            pool.build(_request(registry, denied=set(), retriever=_Roots("a")))
        result = Kernel(registry, MockLLMProvider(), retriever=_Roots("a"),
                        candidate_pool=pool).run_goal("test")
        self.assertEqual(result.status, "failed")
        self.assertIn("max_candidates=1", result.detail)

    def test_overflow_precedes_task_spec_provider_and_execution_model(self):
        registry = _registry(_fields("a", dependencies=["b"]), _fields("b"))
        spec_calls = []

        def resolve(goal):
            spec_calls.append(goal)
            return TaskSpec.from_mapping({})
        llm = MockLLMProvider()
        kernel = Kernel(registry, llm, retriever=_Roots("a"),
                        selector=GoalAwareSetSelector(resolve),
                        candidate_pool=DependencyExpandedCandidatePool(max_candidates=1))
        result = kernel.run_goal("test")
        self.assertEqual(result.status, "failed")
        self.assertEqual(spec_calls, [])
        self.assertFalse(any(record.kind == "llm" for record in kernel.audit_log.records))

    def test_diagnostics_reset_and_invalid_limits_are_rejected(self):
        registry = _registry(_fields("a", dependencies=["missing"]), _fields("b"))
        pool = DependencyExpandedCandidatePool()
        pool.build(_request(registry, denied=set(), retriever=_Roots("a")))
        self.assertEqual(pool.last_missing_references, ("missing",))
        pool.build(_request(registry, denied=set(), retriever=_Roots("b")))
        self.assertEqual(pool.last_missing_references, ())
        self.assertEqual(pool.last_added_ids, ())
        for value in (0, -1, True):
            with self.assertRaises(ValueError):
                DependencyExpandedCandidatePool(max_candidates=value)


if __name__ == "__main__":
    unittest.main()
