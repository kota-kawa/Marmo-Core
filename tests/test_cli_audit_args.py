"""``--audit-log`` continuity (#62) and ``--tool-args`` / ``--tool-impl`` handling (#82)."""

from __future__ import annotations

from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
from pathlib import Path
import json
import os
import tempfile
import threading
import unittest
from unittest.mock import patch

from marmo_core import AuditLog, Kernel, MockLLMProvider, ResourceRegistry
from marmo_core.cli import _write_audit_log, build_parser, main
from marmo_core.cli_locale import CLIInputError

from tests.test_hitl_cli import TOOL_ARGS, _cli, _external_tool, _printed_command


def _records(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


class _Workspace(unittest.TestCase):
    def setUp(self) -> None:
        self._temp = tempfile.TemporaryDirectory()
        self.addCleanup(self._temp.cleanup)
        self.directory = Path(self._temp.name)
        self._previous = Path.cwd()
        os.chdir(self.directory)
        self.addCleanup(os.chdir, self._previous)
        (self.directory / "tool.json").write_text(json.dumps(_external_tool()), encoding="utf-8")
        self.audit = self.directory / "audit.jsonl"

    def _run(self, *extra: str, task: str = "send a list outside") -> tuple[int, str, str]:
        return _cli("run", "--task", task, "--no-default-resources", "--tool-args", TOOL_ARGS, *extra, "tool.json")


class AuditLogContinuityTests(_Workspace):
    def test_a_second_run_appends_to_the_existing_chain(self) -> None:
        self._run("--audit-log", "audit.jsonl")
        first = _records(self.audit)

        status, stdout, _ = self._run("--audit-log", "audit.jsonl", task="send another list outside")

        second = _records(self.audit)
        self.assertEqual(status, 1, stdout)
        self.assertGreater(len(second), len(first))
        self.assertEqual(second[: len(first)], first)
        self.assertEqual(second[len(first)]["prev_hash"], first[-1]["hash"])
        self.assertEqual(AuditLog.from_jsonl(self.audit).verify(), [])

    def test_a_pause_a_second_run_and_a_resume_leave_every_record_in_one_chain(self) -> None:
        _, stdout, _ = self._run("--audit-log", "audit.jsonl", "--state-dir", "state")
        after_pause = _records(self.audit)
        self._run("--audit-log", "audit.jsonl", "--state-dir", "state2", task="send another list outside")
        after_second_run = _records(self.audit)

        status, _, stderr = _cli(*_printed_command(stdout)[1:])

        final = _records(self.audit)
        self.assertEqual((status, stderr), (0, ""))
        self.assertEqual(final[: len(after_second_run)], after_second_run)
        self.assertEqual(after_second_run[: len(after_pause)], after_pause)
        self.assertGreater(len(final), len(after_second_run))
        self.assertEqual(AuditLog.from_jsonl(self.audit).verify(), [])

    def test_a_broken_chain_is_refused_and_left_untouched(self) -> None:
        self._run("--audit-log", "audit.jsonl")
        lines = self.audit.read_text(encoding="utf-8").splitlines()
        lines[0] = lines[0].replace('"kind": "', '"kind": "x', 1)
        self.audit.write_text("\n".join(lines) + "\n", encoding="utf-8")
        before = self.audit.read_text(encoding="utf-8")

        status, stdout, stderr = self._run("--audit-log", "audit.jsonl")

        self.assertEqual((status, stdout), (2, ""))
        self.assertIn("cannot continue the audit log audit.jsonl", stderr)
        self.assertEqual(self.audit.read_text(encoding="utf-8"), before)

    def test_a_half_written_last_line_is_refused_and_left_untouched(self) -> None:
        self._run("--audit-log", "audit.jsonl")
        with self.audit.open("a", encoding="utf-8") as file:
            file.write('{"trace_id": "interrupted')
        before = self.audit.read_text(encoding="utf-8")

        status, _, stderr = self._run("--audit-log", "audit.jsonl")

        self.assertEqual(status, 2)
        self.assertIn("invalid audit JSONL", stderr)
        self.assertEqual(self.audit.read_text(encoding="utf-8"), before)

    def test_the_diagnostic_for_a_broken_chain_is_translated(self) -> None:
        self.audit.write_text("not json\n", encoding="utf-8")

        status, _, stderr = _cli(
            "run", "--task", "t", "--no-default-resources", "--audit-log", "audit.jsonl", language="ja"
        )

        self.assertEqual(status, 2)
        self.assertIn("監査ログ audit.jsonl の続きを書けません", stderr)

    def test_a_writer_that_lost_a_race_does_not_replace_the_other_writers_records(self) -> None:
        args = build_parser().parse_args(
            ["run", "--task", "t", "--no-default-resources", "--audit-log", str(self.audit)]
        )
        kernel = Kernel(ResourceRegistry(), MockLLMProvider())
        kernel.audit_log.append("run", {"who": "first"})
        theirs = AuditLog()
        theirs.append("run", {"who": "second"})
        theirs.extend_jsonl(self.audit)
        before = self.audit.read_text(encoding="utf-8")

        with self.assertRaises(CLIInputError) as caught:
            _write_audit_log(args, kernel)

        self.assertIn("another writer", str(caught.exception))
        self.assertEqual(self.audit.read_text(encoding="utf-8"), before)

    def test_two_writers_at_once_cannot_fork_the_chain(self) -> None:
        mine, theirs = AuditLog(), AuditLog()
        mine.append("run", {"who": "first"})
        theirs.append("run", {"who": "second"})
        outcome: list[object] = []

        def other_writer() -> None:
            try:
                outcome.append(theirs.extend_jsonl(self.audit))
            except ValueError as exc:
                outcome.append(exc)

        writer = threading.Thread(target=other_writer)
        read_stored_chain = AuditLog.from_jsonl
        started = False

        def read_while_the_other_writer_arrives(path):
            # The other writer shows up after this one read the stored chain
            # and before it appends; it has to wait for the append.
            nonlocal started
            stored = read_stored_chain(path)
            if not started:
                started = True
                writer.start()
                writer.join(0.3)
                self.assertTrue(writer.is_alive(), "the second writer must wait for the first")
            return stored

        with patch.object(AuditLog, "from_jsonl", staticmethod(read_while_the_other_writer_arrives)):
            self.assertEqual(mine.extend_jsonl(self.audit), 1)
            writer.join(30)

        self.assertIsInstance(outcome[0], ValueError)
        self.assertEqual(AuditLog.from_jsonl(self.audit).verify(), [])
        self.assertEqual(len(AuditLog.from_jsonl(self.audit).records), 1)

    def test_writing_twice_adds_nothing_the_second_time(self) -> None:
        log = AuditLog()
        log.append("run", {"n": 1})

        self.assertEqual(log.extend_jsonl(self.audit), 1)
        self.assertEqual(log.extend_jsonl(self.audit), 0)
        log.append("run", {"n": 2})
        self.assertEqual(log.extend_jsonl(self.audit), 1)
        self.assertEqual([record["payload"]["n"] for record in _records(self.audit)], [1, 2])

    def test_a_log_without_a_trailing_newline_is_extended_on_a_new_line(self) -> None:
        log = AuditLog()
        log.append("run", {"n": 1})
        log.extend_jsonl(self.audit)
        self.audit.write_text(self.audit.read_text(encoding="utf-8").rstrip("\n"), encoding="utf-8")
        log.append("run", {"n": 2})

        log.extend_jsonl(self.audit)

        self.assertEqual(AuditLog.from_jsonl(self.audit).verify(), [])
        self.assertEqual(len(_records(self.audit)), 2)


class ToolArgsConditionTests(_Workspace):
    def _json_run(self, llm: str, tool_args: str, *extra: str) -> tuple[int, dict, str]:
        with patch("marmo_core.cli.OpenAICompatibleLLMProvider", lambda: MockLLMProvider()):
            status, stdout, stderr = _cli(
                "run", "--task", "send a list outside", "--no-default-resources", "--llm", llm,
                "--strict", "--format", "json", "--tool-args", tool_args, *extra, "tool.json",
            )
        return status, json.loads(stdout) if stdout else {}, stderr

    def test_tool_args_do_not_change_strict_with_a_real_provider(self) -> None:
        without = self._json_run("openai", "")
        with_args = self._json_run("openai", json.dumps({"tool.other.missing": {"a": 1}}))

        self.assertEqual(without[0], with_args[0])
        self.assertEqual(without[1]["strict_violations"], with_args[1]["strict_violations"])
        self.assertFalse(any("requested tool" in item for item in with_args[1]["strict_violations"]))

    def test_the_mock_model_still_counts_tool_args_under_strict(self) -> None:
        _, payload, _ = self._json_run("mock", json.dumps({"tool.other.missing": {"a": 1}}))

        self.assertIn("requested tool was not evaluated: tool.other.missing", payload["strict_violations"])

    def test_the_rule_planner_counts_tool_args_with_a_real_provider(self) -> None:
        _, payload, _ = self._json_run(
            "openai", json.dumps({"tool.other.missing": {"a": 1}}), "--planner", "rule"
        )

        self.assertIn("requested tool was not evaluated: tool.other.missing", payload["strict_violations"])

    def test_inert_tool_args_are_not_parsed(self) -> None:
        status, _, stderr = self._json_run("openai", "not json")

        self.assertNotEqual(status, 2, stderr)
        self.assertEqual(stderr, "")

    def test_help_states_where_tool_args_are_used(self) -> None:
        for command in ("run", "resume"):
            with self.subTest(command=command):
                stdout = StringIO()
                with redirect_stdout(stdout), self.assertRaises(SystemExit):
                    main([command, "--help"])
                text = " ".join(stdout.getvalue().split())
                self.assertIn("--llm mock", text)
                self.assertIn("--planner rule", text)


class InputDiagnosticTests(_Workspace):
    def test_tool_args_with_non_object_values_exit_2_without_a_traceback(self) -> None:
        for value in ('{"tool.x": null}', '{"tool.x": 3}', '{"tool.x": [1]}', "null", "[]"):
            with self.subTest(value=value):
                status, stdout, stderr = _cli(
                    "run", "--task", "t", "--no-default-resources", "--tool-args", value
                )
                self.assertEqual((status, stdout), (2, ""))
                self.assertEqual(
                    stderr, "error: --tool-args must be a JSON object mapping tool ids to argument objects\n"
                )

    def test_tool_args_type_errors_are_translated(self) -> None:
        status, _, stderr = _cli(
            "run", "--task", "t", "--no-default-resources", "--tool-args", '{"tool.x": null}', language="ja"
        )

        self.assertEqual(status, 2)
        self.assertIn("--tool-args には", stderr)

    def test_an_implementation_module_that_does_not_exist_exits_2(self) -> None:
        for option in ("--tool-impl", "--agent-impl"):
            with self.subTest(option=option):
                status, stdout, stderr = _cli(
                    "run", "--task", "t", "--no-default-resources", option, "tool.x=no_such_module_xyz:fn"
                )
                self.assertEqual((status, stdout), (2, ""))
                self.assertIn("error: cannot load no_such_module_xyz:fn", stderr)
                self.assertIn("ModuleNotFoundError", stderr)

    def test_malformed_implementation_specs_exit_2_with_the_format_hint(self) -> None:
        for value in ("tool.x", "tool.x=os", "tool.x=:fn", "=os:getcwd", "tool.x=.rel:fn", "tool.x=os:"):
            with self.subTest(value=value):
                status, _, stderr = _cli(
                    "run", "--task", "t", "--no-default-resources", "--tool-impl", value
                )
                self.assertEqual(status, 2)
                self.assertIn("tool impl must be ID=MODULE:FUNC", stderr)

    def test_implementation_load_errors_are_translated(self) -> None:
        status, _, stderr = _cli(
            "run", "--task", "t", "--no-default-resources", "--tool-impl", "tool.x=no_such_module_xyz:fn",
            language="ja",
        )

        self.assertEqual(status, 2)
        self.assertIn("no_such_module_xyz:fn を読み込めません", stderr)



class ArgumentOrderTests(unittest.TestCase):
    """Resource paths are accepted wherever they are written, on every supported Python."""

    def _parse(self, *argv: str):
        return build_parser().parse_args(list(argv))

    def test_a_path_after_an_option_that_follows_the_resource_id(self) -> None:
        for command, option in (("inspect", ("--format", "json")), ("policy-check", ("--gate", "execution"))):
            with self.subTest(command=command):
                args = self._parse(command, "tool.x", *option, "resources")

                self.assertEqual(args.resource, "tool.x")
                self.assertEqual(args.paths, ["resources"])

    def test_paths_split_by_options_keep_their_order(self) -> None:
        args = self._parse("run", "one", "--task", "t", "two", "--strict", "three")

        self.assertEqual(args.paths, ["one", "two", "three"])
        self.assertEqual(args.task, "t")
        self.assertTrue(args.strict)

    def test_the_separator_still_marks_paths_that_start_with_a_dash(self) -> None:
        self.assertEqual(self._parse("run", "--task", "t", "--", "-tool.json").paths, ["-tool.json"])
        self.assertEqual(self._parse("run", "one", "--task", "t", "--", "-tool.json").paths, ["one", "-tool.json"])

    def test_unknown_options_and_stray_words_are_still_errors(self) -> None:
        for argv in (
            ("list", "resources", "--bogus"),
            ("list", "resources", "--kind", "tool", "--bogus", "more"),
            ("package", "inspect", "directory", "extra"),
        ):
            with self.subTest(argv=argv):
                stderr = StringIO()
                with self.assertRaises(SystemExit) as raised, redirect_stderr(stderr):
                    self._parse(*argv)

                self.assertEqual(raised.exception.code, 2)
                self.assertIn("unrecognized arguments", stderr.getvalue())

    def test_the_japanese_parser_reports_the_same_error(self) -> None:
        stderr = StringIO()
        with self.assertRaises(SystemExit) as raised, redirect_stderr(stderr):
            build_parser(language="ja").parse_args(["list", "resources", "--bogus"])

        self.assertEqual(raised.exception.code, 2)
        self.assertIn("認識できない引数", stderr.getvalue())

    def test_an_interleaved_command_runs_end_to_end(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "tool.json"
            source.write_text(json.dumps(_external_tool()), encoding="utf-8")
            definition = json.loads(source.read_text(encoding="utf-8"))
            stdout = StringIO()

            with redirect_stdout(stdout):
                code = main(["inspect", definition["id"], "--no-default-resources", str(source), "--format", "json"])

            self.assertEqual(code, 0)
            self.assertEqual(json.loads(stdout.getvalue())["id"], definition["id"])


if __name__ == "__main__":
    unittest.main()
