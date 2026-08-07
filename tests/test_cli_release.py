from __future__ import annotations

from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
import json
import os
import tempfile
import unittest

from marmo_core.cli import main


ROOT = Path(__file__).resolve().parents[1]


def _resource(resource_id: str = "memory.test.default") -> dict:
    return {
        "id": resource_id,
        "kind": "memory",
        "name": "Default resource",
        "version": "1.0.0",
        "description": "A resource used to verify deterministic CLI discovery behavior.",
        "capabilities": ["CLI testing"],
        "input_summary": "A CLI request.",
        "output_summary": "A deterministic result.",
        "required_permissions": [],
        "cost_estimate": 0.0,
        "latency_class": "fast",
        "side_effect": "none",
        "trust_level": "core",
        "ref": "memory://test/default",
        "tags": ["test"],
    }


class CliReleaseBehaviorTests(unittest.TestCase):
    def run_cli(self, *args: str) -> tuple[int, object]:
        output = StringIO()
        with redirect_stdout(output):
            status = main(list(args))
        return status, json.loads(output.getvalue())

    def test_no_default_resources_disables_working_directory_discovery(self) -> None:
        previous = Path.cwd()
        with tempfile.TemporaryDirectory() as temp_dir:
            resources = Path(temp_dir) / "resources"
            resources.mkdir()
            (resources / "resource.json").write_text(json.dumps(_resource()), encoding="utf-8")
            try:
                os.chdir(temp_dir)
                default_status, default_payload = self.run_cli("list", "--format", "json")
                isolated_status, isolated_payload = self.run_cli(
                    "list", "--no-default-resources", "--format", "json"
                )
            finally:
                os.chdir(previous)

        self.assertEqual(default_status, 0)
        self.assertEqual([item["id"] for item in default_payload], ["memory.test.default"])
        self.assertEqual(isolated_status, 0)
        self.assertEqual(isolated_payload, [])

    def test_strict_run_rejects_a_requested_tool_that_was_not_evaluated(self) -> None:
        status, payload = self.run_cli(
            "run",
            "--task",
            "finish without a tool",
            "--no-default-resources",
            "--strict",
            "--tool-args",
            '{"tool.missing": {}}',
            "--format",
            "json",
        )

        self.assertEqual(status, 1)
        self.assertEqual(payload["status"], "completed")
        self.assertEqual(
            payload["strict_violations"],
            ["requested tool was not evaluated: tool.missing"],
        )

    def test_non_strict_run_preserves_recovery_compatible_exit_status(self) -> None:
        status, payload = self.run_cli(
            "run",
            "--task",
            "finish without a tool",
            "--no-default-resources",
            "--tool-args",
            '{"tool.missing": {}}',
            "--format",
            "json",
        )

        self.assertEqual(status, 0)
        self.assertEqual(payload["status"], "completed")
        self.assertNotIn("strict_violations", payload)

    def test_strict_connector_dry_run_is_independent_of_default_resources(self) -> None:
        status, payload = self.run_cli(
            "run",
            "--task",
            "read the README text file",
            "--no-default-resources",
            "--strict",
            "--dry-run",
            "--connector-file-root",
            str(ROOT),
            "--granted-permission",
            "connector.file.read",
            "--minimum-isolation-level",
            "L2",
            "--tool-args",
            '{"connector.file.read_text": {"path": "README.md"}}',
            "--format",
            "json",
        )

        self.assertEqual(status, 0)
        self.assertEqual(payload["strict_violations"], [])
        self.assertEqual(
            [(item["tool_id"], item["status"]) for item in payload["tool_results"]],
            [("connector.file.read_text", "dry_run")],
        )


if __name__ == "__main__":
    unittest.main()
