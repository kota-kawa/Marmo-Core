"""Selectors given the activation gate's policy leave out what it would deny."""

from __future__ import annotations

import unittest

from marmo_core import (
    BeamSearchSetSelector,
    BranchAndBoundSetSelector,
    CoverageSetSelector,
    GreedyConstrainedSetSelector,
    Kernel,
    MockLLMProvider,
    PolicyContext,
    PolicyGateway,
    RepairingSetSelector,
    ResourceDefinition,
    ResourceRegistry,
    RuleBasedSetSelector,
    SearchResult,
    SelectionContext,
    TopKSetSelector,
)
from marmo_core.policy import static_denials

UNIT_SELECTORS = (
    GreedyConstrainedSetSelector,
    BeamSearchSetSelector,
    BranchAndBoundSetSelector,
    CoverageSetSelector,
)


def _fields(resource_id: str, kind: str = "tool", **overrides) -> dict:
    data = {
        "id": resource_id,
        "kind": kind,
        "name": resource_id,
        "version": "1.0.0",
        "description": "add numbers with a calculator",
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
        data["input_schema"] = {
            "type": "object",
            "required": ["a", "b"],
            "properties": {"a": {"type": "number"}, "b": {"type": "number"}},
        }
    data.update(overrides)
    return data


def _result(score: float, resource_id: str, kind: str = "tool", **overrides) -> SearchResult:
    definition = ResourceDefinition.from_mapping(_fields(resource_id, kind, **overrides))
    return SearchResult(definition, score, (), {"relevance": score})


def _ids(selection) -> set[str]:
    return {item.resource.metadata.id for item in selection.results}


class StaticDenialTests(unittest.TestCase):
    def test_reasons_are_the_gates_own_for_trust_side_effect_and_isolation(self) -> None:
        context = PolicyContext(allowed_side_effects=("none", "read"))
        cases = {
            "trust_level untrusted is not allowed": {"trust_level": "untrusted"},
            "side_effect write is not allowed": {"side_effect": "write"},
            "isolation_level L3 is not available in this runtime": {"isolation_level": "L3"},
        }
        for reason, overrides in cases.items():
            resource = ResourceDefinition.from_mapping(_fields("tool.x", **overrides))
            self.assertEqual(static_denials(resource, context), (reason,))
            self.assertIn(reason, PolicyGateway().evaluate(resource, context).reasons)

    def test_isolation_below_the_required_minimum_is_a_denial(self) -> None:
        resource = ResourceDefinition.from_mapping(_fields("tool.x", isolation_level="L0"))
        context = PolicyContext(minimum_isolation_level="L2")
        self.assertEqual(static_denials(resource, context), ("isolation_level L0 does not satisfy required L2",))

    def test_missing_permissions_and_approval_side_effects_are_not_static(self) -> None:
        resource = ResourceDefinition.from_mapping(
            _fields("tool.x", required_permissions=["net.external"], side_effect="external")
        )
        self.assertEqual(static_denials(resource, PolicyContext()), ())
        self.assertFalse(PolicyGateway().evaluate(resource, PolicyContext()).allowed)


class GateAwareSelectorTests(unittest.TestCase):
    def test_denied_top_candidate_is_not_selected_in_place_of_a_usable_one(self) -> None:
        results = [_result(0.9, "tool.decoy", trust_level="untrusted"), _result(0.6, "tool.gold")]
        limits = SelectionContext(per_kind_limits={"tool": 1})
        aware = SelectionContext(per_kind_limits={"tool": 1}, policy=PolicyContext())
        for selector in (*UNIT_SELECTORS, RuleBasedSetSelector):
            with self.subTest(selector=selector.__name__):
                self.assertEqual(_ids(selector().select(results, context=limits)), {"tool.decoy"})
                selection = selector().select(results, context=aware)
                self.assertEqual(_ids(selection), {"tool.gold"})
                self.assertIn("tool.decoy: the activation gate would deny it", selection.reason)

    def test_denied_candidate_that_also_lacks_permissions_is_not_a_reason_to_escalate(self) -> None:
        results = [
            _result(0.9, "tool.decoy", trust_level="untrusted", required_permissions=["net.external"]),
            _result(0.6, "tool.gold"),
        ]
        for selector in UNIT_SELECTORS:
            with self.subTest(selector=selector.__name__):
                self.assertEqual(selector().select(results, context=SelectionContext()).status, "escalate")
                selection = selector().select(results, context=SelectionContext(policy=PolicyContext()))
                self.assertEqual((selection.status, _ids(selection)), ("selected", {"tool.gold"}))

    def test_a_permission_blocked_candidate_the_gate_would_otherwise_allow_still_escalates(self) -> None:
        results = [_result(0.9, "tool.needs-grant", required_permissions=["net.external"])]
        for selector in UNIT_SELECTORS:
            with self.subTest(selector=selector.__name__):
                selection = selector().select(results, context=SelectionContext(policy=PolicyContext()))
                self.assertEqual(selection.status, "escalate")

    def test_nothing_but_denied_candidates_abstains_and_says_why(self) -> None:
        results = [_result(0.9, "tool.decoy", trust_level="untrusted", required_permissions=["net.external"])]
        for selector in UNIT_SELECTORS:
            with self.subTest(selector=selector.__name__):
                selection = selector().select(results, context=SelectionContext(policy=PolicyContext()))
                self.assertEqual(selection.status, "abstain")
                self.assertIn("trust_level untrusted is not allowed", selection.reason)

    def test_a_denied_dependency_makes_its_dependent_infeasible(self) -> None:
        results = [
            _result(0.9, "tool.main", dependencies=["skill.dep"]),
            _result(0.5, "skill.dep", kind="skill", trust_level="untrusted"),
            _result(0.4, "tool.other"),
        ]
        selection = GreedyConstrainedSetSelector().select(results, context=SelectionContext(policy=PolicyContext()))
        self.assertEqual(_ids(selection), {"tool.other"})
        self.assertIn("tool.main: dependency skill.dep not in candidate pool", selection.reason)


class RepairGateAwareTests(unittest.TestCase):
    def _pool(self) -> list[SearchResult]:
        return [
            _result(0.9, "tool.main", dependencies=["skill.dep"]),
            _result(0.5, "skill.dep", kind="skill", trust_level="untrusted"),
            _result(0.4, "tool.other"),
        ]

    def test_repair_does_not_bring_back_a_denied_dependency(self) -> None:
        aware = SelectionContext(policy=PolicyContext())
        for selector in (RepairingSetSelector(RuleBasedSetSelector()), TopKSetSelector(3, expand_dependencies=True)):
            with self.subTest(selector=type(selector).__name__):
                self.assertIn("skill.dep", _ids(selector.select(self._pool(), context=SelectionContext())))
                selection = selector.select(self._pool(), context=aware)
                self.assertEqual(_ids(selection), {"tool.other"})
                self.assertIn("skill.dep: the activation gate would deny it", selection.reason)

    def test_repair_drops_a_denied_pick_of_a_selector_that_ignores_the_policy(self) -> None:
        pool = [_result(0.9, "tool.decoy", trust_level="untrusted"), _result(0.6, "tool.gold")]
        selection = TopKSetSelector(1).select(pool, context=SelectionContext(policy=PolicyContext()))
        self.assertEqual(_ids(selection), {"tool.gold"})


class KernelGateAwareSelectionTests(unittest.TestCase):
    GOAL = "Add 2 and 3 with the calculator"

    def _offered_tools(self, **kernel_options) -> tuple[set[str], str]:
        registry = ResourceRegistry()
        decoy = _fields(
            "tool.decoy",
            name="Add 2 and 3 with the calculator",
            description=(self.GOAL + " ") * 5,
            trust_level="untrusted",
        )
        for entry in (decoy, _fields("tool.gold")):
            registry.add(ResourceDefinition.from_mapping(entry))
        llm = MockLLMProvider()
        kernel = Kernel(
            registry,
            llm,
            tool_implementations={name: (lambda a, b: {"sum": a + b}) for name in ("tool.decoy", "tool.gold")},
            policy_context=PolicyContext(),
            selector=GreedyConstrainedSetSelector(),
            set_limits={"tool": 1},
            **kernel_options,
        )
        kernel.run_goal(self.GOAL)
        offered = {name for name in ("tool.decoy", "tool.gold") if any(name in str(tool) for tool in llm.requests[0]["tools"])}
        reason = next(r.payload["selection_reason"] for r in kernel.audit_log.records if r.kind == "retrieve")
        return offered, reason

    def test_by_default_the_denied_decoy_takes_the_slot_and_no_tool_reaches_the_model(self) -> None:
        offered, _ = self._offered_tools()
        self.assertEqual(offered, set())

    def test_gate_aware_selection_hands_the_model_the_usable_tool(self) -> None:
        offered, reason = self._offered_tools(gate_aware_selection=True)
        self.assertEqual(offered, {"tool.gold"})
        self.assertIn("tool.decoy: the activation gate would deny it", reason)


if __name__ == "__main__":
    unittest.main()
