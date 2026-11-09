"""The Kernel makes every selected set dependency-closed and conflict-free."""

from __future__ import annotations

import unittest

from marmo_core import (
    Kernel,
    MockLLMProvider,
    PolicyContext,
    ResourceDefinition,
    ResourceRegistry,
    SearchResult,
    SelectionResult,
)
from marmo_core.selector import _enforce_set_constraints

GOAL = "Add 2 and 3 with the calculator"


def _fields(resource_id: str, kind: str, *, related: bool = True, **overrides) -> dict:
    words = "add numbers with a calculator" if related else "unrelated archive of weather notes"
    data = {
        "id": resource_id,
        "kind": kind,
        "name": resource_id,
        "version": "1.0.0",
        "description": f"{kind} resource: {words}",
        "capabilities": ["calculator"] if related else ["weather"],
        "input_summary": "numbers",
        "output_summary": "sum",
        "required_permissions": [],
        "cost_estimate": 0.0,
        "latency_class": "fast",
        "side_effect": "none",
        "trust_level": "core",
        "ref": f"{kind}://test/{resource_id}",
        "tags": ["calculator"] if related else ["weather"],
    }
    if kind == "tool":
        data["input_schema"] = {
            "type": "object",
            "required": ["a", "b"],
            "properties": {"a": {"type": "number"}, "b": {"type": "number"}},
        }
    if kind == "memory":
        data["content"] = f"note from {resource_id}"
    if kind == "skill":
        data["instructions"] = [f"instructions from {resource_id}"]
    data.update(overrides)
    return data


def _kernel(*entries: dict, granted: tuple[str, ...] = ()) -> Kernel:
    registry = ResourceRegistry()
    for entry in entries:
        registry.add(ResourceDefinition.from_mapping(entry))
    implementations = {
        entry["id"]: (lambda a, b: {"sum": a + b}) for entry in entries if entry["kind"] == "tool"
    }
    return Kernel(
        registry,
        MockLLMProvider(),
        tool_implementations=implementations,
        policy_context=PolicyContext(granted_permissions=granted),
    )


def _retrieve_payload(kernel: Kernel) -> dict:
    return next(record.payload for record in kernel.audit_log.records if record.kind == "retrieve")


def _compile_payload(kernel: Kernel) -> dict:
    return next(
        record.payload
        for record in kernel.audit_log.records
        if record.kind == "compile" and "omitted_resource_ids" in record.payload
    )


class KernelSetConstraintTests(unittest.TestCase):
    def test_a_dependency_the_selector_left_out_is_added_from_the_registry(self) -> None:
        kernel = _kernel(
            _fields("skill.test.sum", "skill", dependencies=["memory.test.archive"]),
            _fields("memory.test.style", "memory"),
            _fields("memory.test.archive", "memory", related=False),
        )

        result = kernel.run_goal(GOAL)

        self.assertEqual(result.status, "completed", result.detail)
        retrieve = _retrieve_payload(kernel)
        self.assertIn("memory.test.archive@1.0.0", retrieve["selected"])
        self.assertIn("added dependencies memory.test.archive@1.0.0", retrieve["selection_reason"])
        self.assertIn("memory.test.archive@1.0.0", kernel.get_state(result.task_id)["activated"])
        self.assertEqual(result.skipped_resources, ())

    def test_the_lower_ranked_side_of_a_conflict_is_dropped_and_reported(self) -> None:
        kernel = _kernel(
            _fields("tool.test.add", "tool", conflicts_with=["tool.test.legacy"]),
            _fields(
                "tool.test.legacy",
                "tool",
                description="tool resource: add numbers",
                capabilities=[],
                tags=[],
            ),
        )

        result = kernel.run_goal(GOAL)

        retrieve = _retrieve_payload(kernel)
        self.assertEqual(retrieve["selected"], ["tool.test.add@1.0.0"])
        self.assertEqual(
            [item["resource"] for item in result.skipped_resources], ["tool.test.legacy@1.0.0"]
        )
        self.assertIn("conflicts", result.skipped_resources[0]["reason"])
        self.assertEqual(retrieve["constraint_drops"], list(result.skipped_resources))

    def test_a_resource_with_an_unregistered_dependency_is_dropped(self) -> None:
        kernel = _kernel(
            _fields("tool.test.add", "tool"),
            _fields("skill.test.sum", "skill", dependencies=["tool.test.absent"]),
        )

        result = kernel.run_goal(GOAL)

        self.assertNotIn("skill.test.sum@1.0.0", _retrieve_payload(kernel)["selected"])
        dropped = {item["resource"]: item["reason"] for item in result.skipped_resources}
        self.assertIn("tool.test.absent", dropped["skill.test.sum@1.0.0"])

    def test_a_resource_whose_dependency_the_gate_denies_is_dropped(self) -> None:
        kernel = _kernel(
            _fields("skill.test.sum", "skill", dependencies=["tool.test.pay"]),
            _fields("tool.test.add", "tool"),
            _fields("tool.test.pay", "tool", related=False, required_permissions=["pay.write"]),
        )

        result = kernel.run_goal(GOAL)

        self.assertNotIn("skill.test.sum@1.0.0", _retrieve_payload(kernel)["selected"])
        dropped = {item["resource"]: item["reason"] for item in result.skipped_resources}
        self.assertIn("denied at activation", dropped["skill.test.sum@1.0.0"])

    def test_a_dependent_whose_dependency_fails_to_activate_is_kept_out_of_the_context(self) -> None:
        kernel = _kernel(
            _fields("skill.test.sum", "skill", dependencies=["memory.test.archive"]),
            _fields("memory.test.archive", "memory", related=False, content=None),
        )

        result = kernel.run_goal(GOAL)

        self.assertIn("memory.test.archive@1.0.0", [item["resource"] for item in result.skipped_resources])
        compiled = _compile_payload(kernel)
        self.assertNotIn("skill.test.sum@1.0.0", compiled["resource_ids"])


class EnforceSetConstraintsTests(unittest.TestCase):
    def _result(self, entry: dict, score: float) -> SearchResult:
        return SearchResult(ResourceDefinition.from_mapping(entry), score, (), {"relevance": score})

    def test_a_set_that_loses_every_member_abstains(self) -> None:
        member = self._result(_fields("skill.test.sum", "skill", dependencies=["tool.test.absent"]), 0.9)
        selection, dropped = _enforce_set_constraints(
            SelectionResult((member,), "picked"), lambda reference: "is unavailable"
        )
        self.assertEqual(selection.status, "abstain")
        self.assertEqual(selection.results, ())
        self.assertEqual([item["resource"] for item in dropped], ["skill.test.sum@1.0.0"])

    def test_versioned_and_cyclic_dependencies_resolve_once(self) -> None:
        first = self._result(_fields("tool.test.a", "tool", dependencies=["tool.test.b@1.0.0"]), 0.9)
        second = self._result(_fields("tool.test.b", "tool", dependencies=["tool.test.a"]), 0.4)
        lookups: list[str] = []

        def resolve(reference: str) -> SearchResult | str:
            lookups.append(reference)
            return second

        selection, dropped = _enforce_set_constraints(SelectionResult((first,), "picked"), resolve)
        self.assertEqual(
            [result.resource.identity for result in selection.results], ["tool.test.a@1.0.0", "tool.test.b@1.0.0"]
        )
        self.assertEqual(dropped, ())
        self.assertEqual(lookups, ["tool.test.b@1.0.0"])

    def test_abstain_and_escalate_pass_through(self) -> None:
        for status in ("abstain", "escalate"):
            original = SelectionResult((), "stopped", status=status)
            self.assertIs(_enforce_set_constraints(original, lambda reference: "unused")[0], original)


if __name__ == "__main__":
    unittest.main()
