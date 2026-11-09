"""Tests for SetSelector / SelectionResult and the greedy constrained solver."""

from __future__ import annotations

import unittest

from marmo_core import (
    BranchAndBoundSetSelector,
    GreedyConstrainedSetSelector,
    BeamSearchSetSelector,
    RelevanceUtility,
    RepairingSetSelector,
    ResourceDefinition,
    RuleBasedSetSelector,
    SearchResult,
    SelectionContext,
    SelectionResult,
    SetSelector,
    TopKSetSelector,
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


def _ids(selection: SelectionResult) -> set[str]:
    return {r.resource.metadata.id for r in selection.results}


class TopKSelectorTests(unittest.TestCase):
    def setUp(self) -> None:
        self.skill = _resource("skill.a", kind="skill")
        self.main = _resource("tool.main", dependencies=["skill.a"], conflicts_with=["tool.alt"])
        self.alt = _resource("tool.alt", conflicts_with=["tool.main"])
        self.agent = _resource("agent.a", kind="agent", dependencies=["tool.main"])
        self.results = [
            _result(self.alt, 0.9),
            _result(self.agent, 0.8),
            _result(self.main, 0.7),
            _result(self.skill, 0.3),
        ]

    def test_plain_top_k_takes_the_k_best_regardless_of_kind(self) -> None:
        selection = TopKSetSelector(3).select(self.results, context=SelectionContext())
        self.assertEqual(selection.status, "selected")
        self.assertEqual(_ids(selection), {"tool.alt", "agent.a", "tool.main"})

    def test_plain_top_k_honours_relevance_floor_and_abstains_when_nothing_passes(self) -> None:
        context = SelectionContext(min_relevance=0.75)
        self.assertEqual(_ids(TopKSetSelector(3).select(self.results, context=context)), {"tool.alt", "agent.a"})
        nothing = TopKSetSelector(3).select(self.results, context=SelectionContext(min_relevance=0.95))
        self.assertEqual(nothing.status, "abstain")

    def test_expansion_adds_dependencies_from_the_pool(self) -> None:
        selection = TopKSetSelector(2, expand_dependencies=True).select(self.results, context=SelectionContext())
        self.assertEqual(_ids(selection), {"tool.alt", "agent.a", "tool.main", "skill.a"})

    def test_conflict_dropping_keeps_the_higher_ranked_and_removes_orphaned_dependents(self) -> None:
        selection = TopKSetSelector(2, expand_dependencies=True, drop_conflicts=True).select(
            self.results, context=SelectionContext()
        )
        # tool.alt outranks tool.main, so tool.main goes, and agent.a (which
        # needs tool.main) goes with it; skill.a is no longer anyone's dependency
        # but was pulled in, and stays.
        self.assertEqual(_ids(selection), {"tool.alt", "skill.a"})

    def test_candidate_whose_dependency_is_missing_from_the_pool_is_dropped(self) -> None:
        orphan = _resource("tool.orphan", dependencies=["skill.absent"])
        selection = TopKSetSelector(1, expand_dependencies=True).select(
            [_result(orphan, 0.9), _result(self.skill, 0.2)], context=SelectionContext()
        )
        self.assertEqual(selection.status, "abstain")
        self.assertIn("skill.absent", selection.reason)

    def test_permission_check_escalates_when_a_member_needs_an_ungranted_permission(self) -> None:
        gated = _resource("tool.gated", required_permissions=["pay.write"])
        results = [_result(gated, 0.9)]
        selection = TopKSetSelector(1, check_permissions=True).select(
            results, context=SelectionContext(granted_permissions=("pay.read",))
        )
        self.assertEqual(selection.status, "escalate")
        self.assertIn("pay.write", selection.reason)
        plain = TopKSetSelector(1).select(results, context=SelectionContext(granted_permissions=("pay.read",)))
        self.assertEqual(plain.status, "selected")

    def test_k_must_be_positive(self) -> None:
        with self.assertRaises(ValueError):
            TopKSetSelector(0)


class _FixedSelector(SetSelector):
    def __init__(self, selection: SelectionResult) -> None:
        self.selection = selection

    def select(self, results, *, context=None):
        return self.selection


class RepairingSelectorTests(unittest.TestCase):
    def test_repairs_a_selected_set_with_candidates_from_the_pool(self) -> None:
        skill = _resource("skill.a", kind="skill")
        tool = _resource("tool.a", dependencies=["skill.a"])
        results = [_result(tool, 0.9), _result(skill, 0.4)]
        inner = _FixedSelector(SelectionResult((results[0],), "inner picked the tool"))
        selection = RepairingSetSelector(inner).select(results, context=SelectionContext())
        self.assertEqual(_ids(selection), {"tool.a", "skill.a"})

    def test_abstain_and_escalate_pass_through_unchanged(self) -> None:
        for status in ("abstain", "escalate"):
            inner = _FixedSelector(SelectionResult((), "inner stopped", status=status))
            selection = RepairingSetSelector(inner).select([], context=SelectionContext())
            self.assertEqual(selection.status, status)
            self.assertEqual(selection.reason, "inner stopped")

    def test_escalates_when_the_repaired_set_needs_ungranted_permissions(self) -> None:
        gated = _resource("tool.gated", required_permissions=["pay.write"])
        results = [_result(gated, 0.9)]
        inner = _FixedSelector(SelectionResult(tuple(results), "inner picked it"))
        selection = RepairingSetSelector(inner).select(results, context=SelectionContext())
        self.assertEqual(selection.status, "escalate")


class PermissionEscalationTests(unittest.TestCase):
    """A permission-blocked best match escalates even when a runner-up is feasible."""

    SOLVERS = (
        GreedyConstrainedSetSelector,
        BeamSearchSetSelector,
        BranchAndBoundSetSelector,
    )

    def test_blocked_best_unit_escalates_instead_of_selecting_the_runner_up(self) -> None:
        extract = _resource("tool.pdf-extract", required_permissions=["fs.write"])
        skill = _resource("skill.pdf", kind="skill", dependencies=["tool.pdf-extract"])
        other = _resource("skill.csv", kind="skill")
        results = [_result(skill, 0.73), _result(other, 0.55), _result(extract, 0.46)]
        for solver in self.SOLVERS:
            with self.subTest(solver=solver.__name__):
                selection = solver().select(results, context=SelectionContext())
                self.assertEqual(selection.status, "escalate")
                self.assertEqual(selection.results, ())
                self.assertEqual(selection.missing_permissions, ("fs.write",))
                self.assertIn("skill.pdf", selection.reason)
                self.assertIn("skill.csv", selection.reason)

    def test_blocked_unit_ranked_below_the_set_stays_a_skip(self) -> None:
        best = _resource("tool.read")
        gated = _resource("tool.write", required_permissions=["fs.write"])
        results = [_result(best, 0.9), _result(gated, 0.4)]
        for solver in self.SOLVERS:
            with self.subTest(solver=solver.__name__):
                selection = solver().select(results, context=SelectionContext())
                self.assertEqual(selection.status, "selected")
                self.assertEqual(_ids(selection), {"tool.read"})
                self.assertIn("tool.write: missing permissions fs.write", selection.reason)

    def test_blocked_unit_that_cannot_fit_on_its_own_does_not_escalate(self) -> None:
        alone = _resource("tool.cheap")
        gated = _resource("tool.costly", required_permissions=["fs.write"], cost_estimate=5.0)
        results = [_result(gated, 0.9), _result(alone, 0.5)]
        context = SelectionContext(budget_cost=1.0)
        for solver in self.SOLVERS:
            with self.subTest(solver=solver.__name__):
                selection = solver().select(results, context=context)
                self.assertEqual(selection.status, "selected")
                self.assertEqual(_ids(selection), {"tool.cheap"})


class RelevanceUtilityTests(unittest.TestCase):
    """The opt-in objective u(i) = relevance(i) - cost."""

    SOLVERS = PermissionEscalationTests.SOLVERS

    def _solvers(self, cost: float = 0.3):
        return [solver(utility=RelevanceUtility(cost)) for solver in self.SOLVERS]

    def test_cost_must_be_a_relevance_value(self) -> None:
        for cost in (-0.1, 1.5):
            with self.assertRaises(ValueError):
                RelevanceUtility(cost)

    def test_a_missing_relevance_component_counts_as_zero(self) -> None:
        result = SearchResult(_resource("tool.a"), 0.9, (), {})
        self.assertAlmostEqual(RelevanceUtility(0.2)(result), -0.2)

    def test_off_topic_candidates_abstain_without_a_threshold(self) -> None:
        results = [_result(_resource(f"tool.{index}"), 0.5, relevance=0.2) for index in range(3)]
        for selector in self._solvers():
            with self.subTest(solver=type(selector).__name__):
                selection = selector.select(results, context=SelectionContext())
                self.assertEqual(selection.status, "abstain")
                self.assertEqual(selection.results, ())
            with self.subTest(solver=type(selector).__name__, objective="score"):
                default = type(selector)().select(results, context=SelectionContext())
                self.assertEqual(len(default.results), 3)

    def test_only_resources_worth_their_cost_fill_the_set(self) -> None:
        results = [
            _result(_resource("tool.match"), 0.7, relevance=0.8),
            _result(_resource("tool.weak"), 0.6, relevance=0.25),
            _result(_resource("tool.noise"), 0.6, relevance=0.1),
        ]
        for selector in self._solvers():
            with self.subTest(solver=type(selector).__name__):
                self.assertEqual(_ids(selector.select(results, context=SelectionContext())), {"tool.match"})

    def test_a_low_relevance_dependency_is_kept_when_the_unit_still_pays(self) -> None:
        tool = _resource("tool.helper")
        skill = _resource("skill.main", kind="skill", dependencies=["tool.helper"])
        results = [_result(skill, 0.7, relevance=0.9), _result(tool, 0.5, relevance=0.1)]
        for selector in self._solvers():
            with self.subTest(solver=type(selector).__name__):
                self.assertEqual(
                    _ids(selector.select(results, context=SelectionContext())), {"skill.main", "tool.helper"}
                )

    def test_a_blocked_unit_worth_nothing_does_not_escalate(self) -> None:
        gated = _resource("tool.gated", required_permissions=["pay.write"])
        results = [_result(gated, 0.9, relevance=0.2)]
        for selector in self._solvers():
            with self.subTest(solver=type(selector).__name__):
                self.assertEqual(selector.select(results, context=SelectionContext()).status, "abstain")

    def test_a_unit_whose_dependency_costs_more_than_it_adds_is_left_out(self) -> None:
        # u = relevance - 0.5: unit {a, d} totals 0.25; unit {b, e} has a
        # positive member (b = 0.1) but totals -0.3, so adding it lowers the set.
        a = _resource("skill.a", kind="skill", dependencies=["tool.d"])
        d = _resource("tool.d")
        b = _resource("agent.b", kind="agent", dependencies=["memory.e"])
        e = _resource("memory.e", kind="memory")
        results = [
            _result(a, 0.8, relevance=0.95),
            _result(b, 0.6, relevance=0.6),
            _result(d, 0.4, relevance=0.3),
            _result(e, 0.3, relevance=0.1),
        ]
        for selector in self._solvers(cost=0.5):
            with self.subTest(solver=type(selector).__name__):
                self.assertEqual(_ids(selector.select(results, context=SelectionContext())), {"skill.a", "tool.d"})

    def test_a_unit_with_a_negative_total_alone_abstains(self) -> None:
        b = _resource("agent.b", kind="agent", dependencies=["memory.e"])
        e = _resource("memory.e", kind="memory")
        results = [_result(b, 0.6, relevance=0.6), _result(e, 0.3, relevance=0.1)]
        for selector in self._solvers(cost=0.5):
            with self.subTest(solver=type(selector).__name__):
                selection = selector.select(results, context=SelectionContext())
                self.assertEqual(selection.status, "abstain")
                self.assertEqual(selection.results, ())

    def test_a_blocked_unit_with_a_negative_total_does_not_escalate(self) -> None:
        gated = _resource("agent.gated", kind="agent", dependencies=["memory.e"], required_permissions=["pay.write"])
        e = _resource("memory.e", kind="memory")
        results = [_result(gated, 0.6, relevance=0.6), _result(e, 0.3, relevance=0.1)]
        for selector in self._solvers(cost=0.5):
            with self.subTest(solver=type(selector).__name__):
                self.assertEqual(selector.select(results, context=SelectionContext()).status, "abstain")

    def test_a_shared_negative_dependency_is_counted_once(self) -> None:
        # u = relevance - 0.5: a = 0.5, b = 0.45, d = -0.45. Unit {a, d} totals
        # 0.05 and unit {b, d} totals 0.0, but once {a, d} is taken, b adds
        # 0.45: the optimum is {a, b, d} at 0.5. A bound built from unit totals
        # would prune b; a filter on unit totals would drop it outright.
        # (Beam search never extends a state with an overlapping unit, under
        # any objective, so it is not covered here.)
        shared = _resource("tool.d")
        first = _resource("skill.a", kind="skill", dependencies=["tool.d"])
        second = _resource("agent.b", kind="agent", dependencies=["tool.d"])
        results = [
            _result(first, 0.8, relevance=1.0),
            _result(second, 0.7, relevance=0.95),
            _result(shared, 0.4, relevance=0.05),
        ]
        for solver in (GreedyConstrainedSetSelector, BranchAndBoundSetSelector):
            with self.subTest(solver=solver.__name__):
                selection = solver(utility=RelevanceUtility(0.5)).select(results, context=SelectionContext())
                self.assertEqual(_ids(selection), {"skill.a", "agent.b", "tool.d"})

if __name__ == "__main__":
    unittest.main()
