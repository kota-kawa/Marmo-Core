from __future__ import annotations

from contextlib import redirect_stdout
from io import StringIO
import json
import unittest

from marmo_core import ResourceDefinition, SearchResult, SelectedResourceSet
from marmo_core.formatting import (
    print_json,
    render_inspection,
    render_policy_decision,
    render_resource_table,
    render_search_table,
    render_selected_set,
)
from marmo_core.policy import PolicyContext, PolicyGateway


def _definition() -> ResourceDefinition:
    return ResourceDefinition.from_mapping(
        {
            "id": "tool.files.read",
            "kind": "tool",
            "name": "Read file",
            "version": "1.0.0",
            "description": "Read a UTF-8 file from a confined local workspace.",
            "capabilities": ["file read"],
            "input_summary": "A relative path.",
            "output_summary": "The file contents.",
            "required_permissions": ["fs.read"],
            "cost_estimate": 0.01,
            "latency_class": "fast",
            "side_effect": "read",
            "trust_level": "core",
            "ref": "tool://files/read",
            "tags": ["file", "read"],
            "input_schema": {"type": "object"},
        },
        source="resources/files.json#0",
    )


class FormattingTests(unittest.TestCase):
    def test_json_output_is_machine_readable(self) -> None:
        output = StringIO()
        with redirect_stdout(output):
            print_json({"message": "安全", "ok": True})
        self.assertEqual(json.loads(output.getvalue()), {"message": "安全", "ok": True})

    def test_resource_search_and_selection_rendering(self) -> None:
        definition = _definition()
        result = SearchResult(definition, 0.875, ("matched file read",), {"relevance": 0.9})

        resource_table = render_resource_table([definition])
        search_table = render_search_table([result])
        selected = render_selected_set(SelectedResourceSet((result,), "best per kind"))
        empty = render_selected_set(SelectedResourceSet((), "no safe match", status="abstain"))

        self.assertIn("tool.files.read", resource_table)
        self.assertIn("0.875", search_table)
        self.assertIn("tool: tool.files.read@1.0.0", selected)
        self.assertIn("status: abstain", empty)
        self.assertIn("resources: none", empty)
        self.assertEqual(render_resource_table([]), "(no results)")

    def test_inspection_and_policy_rendering_include_safety_context(self) -> None:
        definition = _definition()
        inspection = render_inspection(definition)
        decision = PolicyGateway().evaluate(
            definition,
            PolicyContext(granted_permissions=("fs.read",), dry_run=True),
            gate="execution",
            arguments={},
        )
        policy = render_policy_decision(decision)

        self.assertIn("input_schema", inspection)
        self.assertIn("source: resources/files.json#0", inspection)
        self.assertIn("allow: tool.files.read@1.0.0", policy)
        self.assertIn("isolation: L0", policy)
        self.assertIn("dry_run: true", policy)


if __name__ == "__main__":
    unittest.main()
