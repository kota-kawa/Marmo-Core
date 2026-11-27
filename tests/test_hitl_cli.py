"""The resume command ``marmo run`` prints must be parseable and answerable as printed."""

from __future__ import annotations

from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
from pathlib import Path
import json
import os
import shlex
import tempfile
import unittest
from unittest.mock import patch

from marmo_core.cli import build_parser, main, resume_command

TOOL_ARGS = json.dumps({"tool.demo.dumps": {"obj": [1, 2]}})


def _external_tool() -> dict:
    return {
        "id": "tool.demo.dumps",
        "kind": "tool",
        "name": "Send list",
        "version": "1.0.0",
        "description": "Serialize a list to a JSON string and send it outside.",
        "capabilities": ["send a list outside"],
        "input_summary": "a list",
        "output_summary": "JSON text",
        "required_permissions": [],
        "cost_estimate": 0.0,
        "latency_class": "fast",
        "side_effect": "external",
        "trust_level": "core",
        "ref": "python:json:dumps",
        "tags": ["send"],
        "input_schema": {
            "type": "object",
            "required": ["obj"],
            "properties": {"obj": {"type": "array"}},
        },
    }


def _cli(*argv: str, language: str = "en") -> tuple[int, str, str]:
    stdout, stderr = StringIO(), StringIO()
    with patch.dict(os.environ, {"MARMO_CLI_LANGUAGE": language}):
        with redirect_stdout(stdout), redirect_stderr(stderr):
            status = main(list(argv))
    return status, stdout.getvalue(), stderr.getvalue()


def _printed_command(stdout: str) -> list[str]:
    line = next(line for line in stdout.splitlines() if "answer with:" in line)
    return shlex.split(line.split("answer with:", 1)[1])


class _Workspace(unittest.TestCase):
    def setUp(self) -> None:
        self._temp = tempfile.TemporaryDirectory()
        self.addCleanup(self._temp.cleanup)
        self.directory = Path(self._temp.name)
        self._previous = Path.cwd()
        os.chdir(self.directory)
        self.addCleanup(os.chdir, self._previous)

    def _write_resource(self, name: str) -> None:
        (self.directory / name).write_text(json.dumps(_external_tool()), encoding="utf-8")

    def _pause(self, *extra: str) -> tuple[int, str, str]:
        return _cli(
            "run", "--task", "send a list outside", "--no-default-resources",
            "--tool-args", TOOL_ARGS, "--state-dir", "state", *extra,
        )


class ResumeHintApproverTests(_Workspace):
    def test_the_hint_names_the_responder_when_one_approver_is_required(self) -> None:
        self._write_resource("tool.json")
        status, stdout, _ = self._pause("--approver", "alice", "tool.json")
        self.assertEqual(status, 1)

        command = _printed_command(stdout)

        self.assertEqual(command[command.index("--responder") + 1], "alice")

    def test_the_printed_hint_approves_the_task_without_edits(self) -> None:
        self._write_resource("tool.json")
        _, stdout, _ = self._pause("--approver", "alice", "tool.json")

        status, resumed, stderr = _cli(*_printed_command(stdout)[1:])

        self.assertEqual((status, stderr), (0, ""))
        self.assertIn("status: completed", resumed)

    def test_several_approvers_leave_a_placeholder_the_person_must_replace(self) -> None:
        args = build_parser().parse_args(
            ["run", "--task", "t", "--state-dir", "s", "--approver", "alice", "--approver", "bob"]
        )

        command = shlex.split(resume_command(args, "abc"))

        self.assertEqual(command[command.index("--responder") + 1], "<APPROVER>")

    def test_no_responder_is_added_without_approvers(self) -> None:
        args = build_parser().parse_args(["run", "--task", "t", "--state-dir", "s"])

        self.assertNotIn("--responder", resume_command(args, "abc"))


class ResumeHintPathTests(_Workspace):
    def test_a_path_starting_with_a_dash_keeps_the_separator(self) -> None:
        args = build_parser().parse_args(
            ["run", "--task", "t", "--state-dir", "s", "--no-default-resources", "--", "-tool.json", "res"]
        )

        command = shlex.split(resume_command(args, "abc"))
        resumed = build_parser().parse_args(command[1:])

        self.assertEqual(command[-3:], ["--", "-tool.json", "res"])
        self.assertEqual(resumed.paths, ["-tool.json", "res"])

    def test_the_hint_for_a_dash_prefixed_resource_file_resumes_the_task(self) -> None:
        self._write_resource("-tool.json")
        _, stdout, _ = self._pause("--", "-tool.json")

        status, resumed, stderr = _cli(*_printed_command(stdout)[1:])

        self.assertEqual((status, stderr), (0, ""))
        self.assertIn("status: completed", resumed)

    def test_ordinary_paths_get_no_separator(self) -> None:
        args = build_parser().parse_args(["run", "--task", "t", "--state-dir", "s", "resources"])

        self.assertNotIn("--", shlex.split(resume_command(args, "abc")))


class EmptyModifyTests(_Workspace):
    def test_an_empty_modify_is_refused_and_the_task_stays_paused(self) -> None:
        self._write_resource("tool.json")
        _, stdout, _ = self._pause("tool.json")
        task_id = _printed_command(stdout)[3]

        for value in ("", "  "):
            with self.subTest(value=value):
                status, out, stderr = _cli(
                    "resume", "--task-id", task_id, "--state-dir", "state", "--no-default-resources",
                    "--tool-args", TOOL_ARGS, "--modify", value, "tool.json",
                )
                self.assertEqual((status, out), (2, ""))
                self.assertIn("--modify must not be empty", stderr)

        _, tasks, _ = _cli("tasks", "--state-dir", "state", "--format", "json")
        self.assertEqual(json.loads(tasks)["tasks"][0]["status"], "escalated")

    def test_the_empty_modify_diagnostic_is_translated(self) -> None:
        status, _, stderr = _cli(
            "resume", "--task-id", "x", "--state-dir", "state", "--no-default-resources",
            "--modify", "", language="ja",
        )

        self.assertEqual(status, 2)
        self.assertIn("--modify には", stderr)


if __name__ == "__main__":
    unittest.main()
