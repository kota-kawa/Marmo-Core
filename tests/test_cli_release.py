from __future__ import annotations

from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
import json
import os
import shlex
import tempfile
import unittest

from marmo_core import Kernel, MockLLMProvider, ResourceRegistry
from marmo_core.cli import (
    _RESUME_FORWARDED_OPTIONS,
    _audit_log_preserved,
    build_parser,
    main,
    resume_command,
)


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


class ResumeHintTests(unittest.TestCase):
    """The printed resume command must reproduce the run's authorization."""

    def _run_args(self, *extra: str) -> object:
        return build_parser().parse_args(
            ["run", "--task", "write a file", "--state-dir", "/tmp/state", *extra]
        )

    def test_the_hint_repeats_the_flags_the_run_was_authorized_with(self) -> None:
        args = self._run_args(
            "--llm",
            "openai",
            "--granted-permission",
            "fs.write",
            "--granted-permission",
            "fs.read",
            "--allow-side-effect",
            "write",
            "--escalate-side-effect",
            "write",
            "resources",
        )

        command = resume_command(args, "abc123")

        for fragment in (
            "--granted-permission fs.write",
            "--granted-permission fs.read",
            "--allow-side-effect write",
            "--escalate-side-effect write",
            "--llm openai",
            "--state-dir /tmp/state",
            "--approve",
        ):
            self.assertIn(fragment, command)

    def test_the_hint_round_trips_through_the_parser(self) -> None:
        args = self._run_args(
            "--llm",
            "anthropic",
            "--retriever",
            "hyde",
            "--granted-permission",
            "fs.read",
            "--allow-side-effect",
            "read",
            "--top-k",
            "12",
            "--max-tool-calls",
            "9",
            "--planner",
            "rule",
            "--strict",
            "resources",
        )

        resumed = build_parser().parse_args(shlex.split(resume_command(args, "abc123"))[1:])

        self.assertEqual(resumed.task_id, "abc123")
        self.assertTrue(resumed.approve)
        for dest in (
            "llm",
            "retriever",
            "granted_permission",
            "allow_side_effect",
            "top_k",
            "max_tool_calls",
            "planner",
            "strict",
            "paths",
        ):
            self.assertEqual(getattr(resumed, dest), getattr(args, dest), dest)

    def test_a_plain_run_produces_a_short_hint(self) -> None:
        command = resume_command(self._run_args(), "abc123")

        self.assertEqual(command, "marmo resume --task-id abc123 --state-dir /tmp/state --approve")

    def test_every_option_shared_with_run_is_forwarded(self) -> None:
        # Guards against an option being added to both commands and quietly
        # dropped from the hint.
        parser = build_parser()
        subparsers = next(
            action for action in parser._subparsers._group_actions  # type: ignore[union-attr]
        ).choices
        run_dests = {action.dest for action in subparsers["run"]._actions}
        resume_dests = {action.dest for action in subparsers["resume"]._actions}
        forwarded = {dest for dest, _ in _RESUME_FORWARDED_OPTIONS}
        expected = (run_dests & resume_dests) - {"help", "task_id", "state_dir", "paths", "func"}

        self.assertEqual(expected - forwarded, set())


class AuditLogDurabilityTests(unittest.TestCase):
    """A run that raises must still leave its trail on disk."""

    def test_the_audit_log_is_written_when_the_run_raises(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            audit_path = Path(temp_dir) / "audit.jsonl"
            args = build_parser().parse_args(
                ["run", "--task", "anything", "--audit-log", str(audit_path), "--no-default-resources"]
            )
            kernel = Kernel(ResourceRegistry(), MockLLMProvider())
            kernel.audit_log.append("execute", {"tool": "tool.test.write", "status": "success"})

            with self.assertRaises(RuntimeError):
                with _audit_log_preserved(args, kernel):
                    raise RuntimeError("the provider died after a tool already ran")

            records = [json.loads(line) for line in audit_path.read_text(encoding="utf-8").splitlines()]
            self.assertEqual([record["kind"] for record in records], ["execute"])

    def test_nothing_is_written_when_no_audit_log_was_requested(self) -> None:
        args = build_parser().parse_args(["run", "--task", "anything", "--no-default-resources"])
        kernel = Kernel(ResourceRegistry(), MockLLMProvider())

        with self.assertRaises(RuntimeError):
            with _audit_log_preserved(args, kernel):
                raise RuntimeError("boom")


class PauseOutputTests(unittest.TestCase):
    """The hint is only useful if the pause actually prints it."""

    def _paused_run(self, temp_dir: str, *extra: str) -> str:
        resources = Path(temp_dir) / "resources"
        resources.mkdir()
        (resources / "tool.json").write_text(json.dumps(_write_tool()), encoding="utf-8")
        output = StringIO()
        previous = Path.cwd()
        try:
            os.chdir(temp_dir)
            with redirect_stdout(output):
                main(
                    [
                        "run",
                        "--task",
                        "write the report file",
                        "--state-dir",
                        "state",
                        "--granted-permission",
                        "fs.write",
                        "--allow-side-effect",
                        "write",
                        "--tool-args",
                        json.dumps({"tool.test.write": {"path": "r.txt", "api_key": "sk-" + "a" * 40}}),
                        *extra,
                    ]
                )
        finally:
            os.chdir(previous)
        return output.getvalue()

    def test_a_pause_prints_a_resume_command_carrying_the_run_flags(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            printed = self._paused_run(temp_dir)

        hint = next(line for line in printed.splitlines() if "answer with:" in line)
        self.assertIn("--granted-permission fs.write", hint)
        self.assertIn("--allow-side-effect write", hint)
        self.assertIn("--state-dir state", hint)

    def test_the_printed_command_does_not_echo_credentials_from_tool_args(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            printed = self._paused_run(temp_dir)

        self.assertNotIn("sk-" + "a" * 40, printed)
        self.assertIn("[REDACTED]", printed)


def _write_tool() -> dict:
    return {
        "id": "tool.test.write",
        "kind": "tool",
        "name": "Write report",
        "version": "1.0.0",
        "description": "Write the report file to the workspace.",
        "capabilities": ["write the report file"],
        "input_summary": "a path",
        "output_summary": "nothing",
        "required_permissions": ["fs.write"],
        "cost_estimate": 0.0,
        "latency_class": "fast",
        "side_effect": "write",
        "trust_level": "core",
        "ref": "tool://test/write",
        "tags": ["report"],
        "input_schema": {"type": "object", "properties": {"path": {"type": "string"}}},
    }
