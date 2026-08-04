"""Tests for SetSelector / SelectionResult and the greedy constrained solver."""

from __future__ import annotations

import unittest

from marmo_core import (
    BranchAndBoundSetSelector,
    GreedyConstrainedSetSelector,
    BeamSearchSetSelector,
    ResourceDefinition,
    RuleBasedSetSelector,
    SearchResult,
    SelectionContext,
    SelectionResult,
)


def _resource(resource_id: str, kind: str = "tool", **overrides) -> ResourceDefinition:
    payload = {
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
    payload.update(overrides)
    return ResourceDefinition.from_mapping(payload)


def _result(definition: ResourceDefinition, score: float, relevance: float | None = None) -> SearchResult:
    components = {"relevance": relevance if relevance is not None else score}
    return SearchResult(definition, score, (), components)


class GreedySelectorTests(unittest.TestCase):
    def test_dependency_closure_is_pulled_in(self) -> None:
        skill = _resource("skill.a", kind="skill")
        tool = _resource("tool.a", dependencies=["skill.a"])
        results = [_result(tool, 0.9), _result(skill, 0.4)]
        selection = GreedyConstrainedSetSelector().select(results, context=SelectionContext())
        self.assertEqual(selection.status, "selected")
        self.assertEqual(
            {r.resource.metadata.id for r in selection.results}, {"tool.a", "skill.a"}
        )

    def test_unit_utility_beats_single_high_scorer(self) -> None:
        # The standalone alternative outscores each member of the chain, but
        # the chain's summed utility wins; the conflicting alternative is
        # then excluded.
        skill = _resource("skill.a", kind="skill")
        main = _resource("tool.main", dependencies=["skill.a"], conflicts_with=["tool.alt"])
        agent = _resource("agent.a", kind="agent", dependencies=["tool.main"])
        alt = _resource("tool.alt", conflicts_with=["tool.main"])
        results = [_result(alt, 0.8), _result(agent, 0.7), _result(main, 0.6), _result(skill, 0.5)]
        selection = GreedyConstrainedSetSelector().select(results, context=SelectionContext())
        ids = {r.resource.metadata.id for r in selection.results}
        self.assertIn("agent.a", ids)
        self.assertIn("tool.main", ids)
        self.assertNotIn("tool.alt", ids)

    def test_missing_dependency_makes_candidate_infeasible(self) -> None:
        tool = _resource("tool.a", dependencies=["skill.absent"])
        selection = GreedyConstrainedSetSelector().select(
            [_result(tool, 0.9)], context=SelectionContext()
        )
        self.assertEqual(selection.status, "abstain")
        self.assertIn("skill.absent", selection.reason)

    def test_permission_blocked_candidates_escalate(self) -> None:
        tool = _resource("tool.a", required_permissions=["payments.write"])
        selection = GreedyConstrainedSetSelector().select(
            [_result(tool, 0.9)], context=SelectionContext(granted_permissions=())
        )
        self.assertEqual(selection.status, "escalate")
        self.assertIn("payments.write", selection.reason)

    def test_empty_candidates_abstain(self) -> None:
        selection = GreedyConstrainedSetSelector().select([], context=SelectionContext())
        self.assertEqual(selection.status, "abstain")

    def test_min_relevance_gates_on_relevance_component(self) -> None:
        tool = _resource("tool.a")
        # High composite score but low text relevance → abstain.
        selection = GreedyConstrainedSetSelector().select(
            [_result(tool, 0.6, relevance=0.3)],
            context=SelectionContext(min_relevance=0.5),
        )
        self.assertEqual(selection.status, "abstain")

    def test_budget_cost_is_enforced(self) -> None:
        cheap = _resource("tool.cheap", cost_estimate=1.0)
        pricey = _resource("tool.pricey", cost_estimate=10.0)
        selection = GreedyConstrainedSetSelector().select(
            [_result(pricey, 0.9), _result(cheap, 0.8)],
            context=SelectionContext(budget_cost=5.0, per_kind_limits={"tool": 2}),
        )
        ids = {r.resource.metadata.id for r in selection.results}
        self.assertEqual(ids, {"tool.cheap"})

    def test_per_kind_limits_count_closure_members(self) -> None:
        skill_a = _resource("skill.a", kind="skill")
        skill_b = _resource("skill.b", kind="skill")
        tool = _resource("tool.a", dependencies=["skill.a"])
        results = [_result(tool, 0.9), _result(skill_a, 0.5), _result(skill_b, 0.8)]
        selection = GreedyConstrainedSetSelector().select(
            results, context=SelectionContext(per_kind_limits={"skill": 1, "tool": 1})
        )
        ids = {r.resource.metadata.id for r in selection.results}
        # The tool's closure includes skill.a; skill.b must not exceed the limit.
        self.assertEqual(ids, {"tool.a", "skill.a"})


class RuleBasedCompatibilityTests(unittest.TestCase):
    def test_rule_based_returns_selected_status(self) -> None:
        tool = _resource("tool.a")
        selection = RuleBasedSetSelector().select([_result(tool, 0.9)])
        self.assertIsInstance(selection, SelectionResult)
        self.assertEqual(selection.status, "selected")
        self.assertTrue(selection.selected)

    def test_rule_based_accepts_context_limits(self) -> None:
        tools = [_result(_resource(f"tool.{index}"), 0.9 - index * 0.1) for index in range(3)]
        selection = RuleBasedSetSelector().select(
            tools, context=SelectionContext(per_kind_limits={"tool": 2})
        )
        self.assertEqual(len(selection.results), 2)


class BeamSearchSelectorTests(unittest.TestCase):
    def test_beam_search_avoids_local_optima(self) -> None:
        unit_a = _resource("tool.a", cost_estimate=6.0)
        unit_b = _resource("tool.b", cost_estimate=5.0)
        unit_c = _resource("tool.c", cost_estimate=5.0)
        results = [_result(unit_a, 0.9), _result(unit_b, 0.8), _result(unit_c, 0.8)]
        ctx = SelectionContext(budget_cost=10.0, max_resources=5)
        
        greedy_res = GreedyConstrainedSetSelector().select(results, context=ctx)
        beam_res = BeamSearchSetSelector(beam_width=5).select(results, context=ctx)
        
        self.assertEqual({r.resource.metadata.id for r in greedy_res.results}, {"tool.a"})
        self.assertEqual({r.resource.metadata.id for r in beam_res.results}, {"tool.b", "tool.c"})


class BranchAndBoundSelectorTests(unittest.TestCase):
    def test_finds_optimum_where_greedy_is_myopic(self) -> None:
        # Same setup as the beam test: greedy grabs tool.a (0.9) and blows
        # the budget; the optimum is {tool.b, tool.c} (0.8 + 0.8).
        unit_a = _resource("tool.a", cost_estimate=6.0)
        unit_b = _resource("tool.b", cost_estimate=5.0)
        unit_c = _resource("tool.c", cost_estimate=5.0)
        results = [_result(unit_a, 0.9), _result(unit_b, 0.8), _result(unit_c, 0.8)]
        ctx = SelectionContext(budget_cost=10.0, max_resources=5)
        selection = BranchAndBoundSetSelector().select(results, context=ctx)
        self.assertEqual(
            {r.resource.metadata.id for r in selection.results}, {"tool.b", "tool.c"}
        )
        self.assertIn("proven optimal", selection.reason)

    def test_beats_narrow_beam(self) -> None:
        # A width-1 beam commits to the highest-utility unit and cannot
        # recover; exhaustive search finds the conflicting pair that sums
        # higher.
        big = _resource("tool.big", conflicts_with=["tool.x", "tool.y"])
        x = _resource("tool.x", conflicts_with=["tool.big"])
        y = _resource("tool.y", conflicts_with=["tool.big"])
        results = [_result(big, 0.9), _result(x, 0.6), _result(y, 0.6)]
        ctx = SelectionContext(per_kind_limits={"tool": 2})
        beam = BeamSearchSetSelector(beam_width=1).select(results, context=ctx)
        bnb = BranchAndBoundSetSelector().select(results, context=ctx)
        self.assertEqual({r.resource.metadata.id for r in beam.results}, {"tool.big"})
        self.assertEqual(
            {r.resource.metadata.id for r in bnb.results}, {"tool.x", "tool.y"}
        )

    def test_dependency_closure_and_shared_members(self) -> None:
        # Two tools share one skill dependency; union semantics counts the
        # skill once, so both tools fit under max_resources=3.
        skill = _resource("skill.shared", kind="skill")
        tool_a = _resource("tool.a", dependencies=["skill.shared"])
        tool_b = _resource("tool.b", dependencies=["skill.shared"])
        results = [_result(tool_a, 0.9), _result(tool_b, 0.8), _result(skill, 0.4)]
        ctx = SelectionContext(max_resources=3, per_kind_limits={"tool": 2, "skill": 1})
        selection = BranchAndBoundSetSelector().select(results, context=ctx)
        self.assertEqual(
            {r.resource.metadata.id for r in selection.results},
            {"tool.a", "tool.b", "skill.shared"},
        )

    def test_permission_blocked_candidates_escalate(self) -> None:
        tool = _resource("tool.a", required_permissions=["payments.write"])
        selection = BranchAndBoundSetSelector().select(
            [_result(tool, 0.9)], context=SelectionContext(granted_permissions=())
        )
        self.assertEqual(selection.status, "escalate")
        self.assertIn("payments.write", selection.reason)

    def test_missing_dependency_abstains(self) -> None:
        tool = _resource("tool.a", dependencies=["skill.absent"])
        selection = BranchAndBoundSetSelector().select(
            [_result(tool, 0.9)], context=SelectionContext()
        )
        self.assertEqual(selection.status, "abstain")
        self.assertIn("skill.absent", selection.reason)

    def test_node_budget_reports_truncation(self) -> None:
        results = [
            _result(_resource(f"tool.{index}"), 0.5 + index * 0.001) for index in range(12)
        ]
        ctx = SelectionContext(max_resources=12, per_kind_limits={"tool": 12})
        selection = BranchAndBoundSetSelector(max_nodes=5).select(results, context=ctx)
        self.assertEqual(selection.status, "selected")
        self.assertIn("node budget reached", selection.reason)

    def test_never_worse_than_greedy_or_beam(self) -> None:
        # Σu of the exact solver must dominate both approximations on a
        # randomized constraint-heavy pool.
        import random

        rng = random.Random(7)
        for trial in range(20):
            pool: list[ResourceDefinition] = []
            ids = [f"tool.{i}" for i in range(8)]
            for i, rid in enumerate(ids):
                deps = [ids[j] for j in range(i) if rng.random() < 0.2]
                conflicts = [ids[j] for j in range(8) if j != i and rng.random() < 0.15]
                pool.append(
                    _resource(rid, dependencies=deps, conflicts_with=conflicts,
                              cost_estimate=rng.uniform(0.0, 5.0))
                )
            results = [_result(d, rng.uniform(0.3, 1.0)) for d in pool]
            scores = {d.metadata.id: r.score for d, r in zip(pool, results)}
            ctx = SelectionContext(
                budget_cost=8.0, max_resources=5, per_kind_limits={"tool": 5}
            )

            def utility(selection) -> float:
                return sum(scores[r.resource.metadata.id] for r in selection.results)

            bnb = BranchAndBoundSetSelector().select(results, context=ctx)
            greedy = GreedyConstrainedSetSelector().select(results, context=ctx)
            beam = BeamSearchSetSelector(beam_width=5).select(results, context=ctx)
            self.assertGreaterEqual(utility(bnb) + 1e-9, utility(greedy), f"trial {trial}")
            self.assertGreaterEqual(utility(bnb) + 1e-9, utility(beam), f"trial {trial}")


if __name__ == "__main__":
    unittest.main()
