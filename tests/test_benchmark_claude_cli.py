from __future__ import annotations

import json
import multiprocessing
import stat
import sys
import tempfile
import textwrap
import threading
import unittest
from unittest import mock
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "benchmarks"))

from _claude_cli import (  # noqa: E402
    ISOLATION_FLAGS,
    ClaudeCLIProvider,
    ModelRefusalError,
    SpendLedger,
    SpendLedgerError,
    SpendLimitError,
    check_model,
    worst_case_usd,
)
from marmo_core import ChatMessage  # noqa: E402
from marmo_core.budget import BudgetExceededError  # noqa: E402

# Mimics the CLI's parsing: ``--tools`` consumes every following value that is
# not an option, and ``--`` ends option parsing. It answers in the CLI's JSON
# output format and records its arguments and output-token limit beside itself.
FAKE_CLI = textwrap.dedent(
    """\
    #!{python}
    import json, os, sys
    with open(sys.argv[0] + ".args", "w") as handle:
        json.dump({{"argv": sys.argv[1:], "max_output": os.environ.get("CLAUDE_CODE_MAX_OUTPUT_TOKENS")}}, handle)
    args, positional, index = sys.argv[1:], [], 0
    while index < len(args):
        arg = args[index]
        if arg == "--":
            positional += args[index + 1:]
            break
        if arg == "--tools":
            index += 1
            while index < len(args) and not args[index].startswith("--"):
                index += 1
            continue
        if arg in ("--model", "--system-prompt", "--output-format"):
            index += 2
            continue
        if arg.startswith("-"):
            index += 1
            continue
        positional.append(arg)
        index += 1
    if not positional:
        sys.stderr.write("Input must be provided as a prompt argument")
        sys.exit(1)
    print(json.dumps({{"result": "echo:" + positional[-1], "is_error": False, "total_cost_usd": 0.25}}))
    """
)


def _script(directory: str, body: str) -> str:
    """An executable stand-in for the CLI that counts its runs beside itself and then runs ``body``."""

    path = Path(directory) / "claude"
    path.write_text(f"#!{sys.executable}\nimport json, sys, time\nopen(sys.argv[0] + '.calls', 'a').write('x')\n" + body,
                    encoding="utf-8")
    path.chmod(path.stat().st_mode | stat.S_IXUSR)
    return str(path)


def _reserve_many(path: str, cap: float, amount: float, attempts: int, queue) -> None:
    ledger, admitted = SpendLedger(path, cap), 0
    for _ in range(attempts):
        try:
            ledger.reserve(amount)
            admitted += 1
        except SpendLimitError:
            pass
    queue.put(admitted)


class SpendLedgerTests(unittest.TestCase):
    def test_threads_and_processes_together_never_reserve_past_the_cap(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = str(Path(directory) / "ledger.json")
            queue = multiprocessing.get_context("spawn").Queue()
            workers = [multiprocessing.get_context("spawn").Process(target=_reserve_many, args=(path, 1.0, 0.1, 8, queue))
                       for _ in range(2)]
            threads = [threading.Thread(target=_reserve_many, args=(path, 1.0, 0.1, 8, queue)) for _ in range(4)]
            for runner in workers + threads:
                runner.start()
            for runner in workers + threads:
                runner.join()
            admitted = sum(queue.get() for _ in workers + threads)
            state = SpendLedger(path, 1.0).snapshot()
        self.assertEqual(admitted, 10)  # 48 attempts of 0.10 against a cap of 1.00
        self.assertAlmostEqual(state["reserved_usd"], 1.0)
        self.assertEqual(state["refused_calls"], 38)

    def test_an_empty_or_damaged_ledger_is_not_read_as_nothing_spent(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            for content in ("", "{", '{"charged_usd": NaN, "reserved_usd": 0, "calls": 0, "unknown_cost_calls": 0, '
                                     '"refused_calls": 0, "underestimated_calls": 0}'):
                path = Path(directory) / "ledger.json"
                path.write_text(content, encoding="utf-8")
                with self.assertRaises(SpendLedgerError):
                    SpendLedger(path, 1.0).reserve(0.1)
                self.assertEqual(path.read_text(encoding="utf-8"), content, "the damaged file is left for inspection")

    def test_a_cost_above_its_reservation_is_charged_and_counted(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            ledger = SpendLedger(Path(directory) / "ledger.json", 1.0)
            ledger.reserve(0.1)
            ledger.settle(0.1, 0.4)
            state = ledger.snapshot()
        self.assertEqual((state["charged_usd"], state["reserved_usd"], state["underestimated_calls"]), (0.4, 0.0, 1))
        self.assertNotIn("outcome", state)

    def test_a_refused_call_is_a_budget_error_that_llm_components_re_raise(self) -> None:
        self.assertTrue(issubclass(SpendLimitError, BudgetExceededError))


class ClaudeCLIProviderTests(unittest.TestCase):
    def fake_cli(self, directory: str) -> str:
        path = Path(directory) / "claude"
        path.write_text(FAKE_CLI.format(python=sys.executable), encoding="utf-8")
        path.chmod(path.stat().st_mode | stat.S_IXUSR)
        return str(path)

    def test_prompt_is_not_consumed_by_the_tools_option(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            provider = ClaudeCLIProvider(executable=self.fake_cli(directory), attempts=1)
            reply = provider.complete([ChatMessage(role="user", content="Reply OK")])
        self.assertEqual(reply.content, "echo:Reply OK")

    def test_prompt_starting_with_a_dash_is_sent_as_the_prompt(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            provider = ClaudeCLIProvider(executable=self.fake_cli(directory), attempts=1)
            reply = provider.complete([
                ChatMessage(role="system", content="Be terse."),
                ChatMessage(role="user", content="- list item"),
            ])
        self.assertEqual(reply.content, "echo:- list item")

    def test_safety_refusal_is_raised_at_once_instead_of_retried(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "claude"
            path.write_text(
                f"#!{sys.executable}\n"
                "import sys\n"
                "open(sys.argv[0] + '.calls', 'a').write('x')\n"
                "import json\n"
                "print(json.dumps({'result': \"API Error: Sonnet's safeguards flagged this message\", 'is_error': True}))\n"
                "sys.exit(1)\n",
                encoding="utf-8",
            )
            path.chmod(path.stat().st_mode | stat.S_IXUSR)
            provider = ClaudeCLIProvider(executable=str(path), attempts=4)
            with self.assertRaises(ModelRefusalError):
                provider.complete([ChatMessage(role="user", content="hello")])
            self.assertEqual((Path(directory) / "claude.calls").read_text(), "x")

    def test_user_customizations_are_switched_off_and_output_is_bounded(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            executable = self.fake_cli(directory)
            ClaudeCLIProvider(executable=executable, attempts=1).complete([ChatMessage(role="user", content="hi")])
            seen = json.loads(Path(executable + ".args").read_text())
        for flag in ISOLATION_FLAGS:
            self.assertIn(flag, seen["argv"])
        self.assertEqual(seen["argv"][seen["argv"].index("--output-format") + 1], "json")
        self.assertEqual(seen["max_output"], "4096")

    def test_ledger_charges_the_reported_cost_and_refuses_past_the_cap(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            ledger = SpendLedger(Path(directory) / "ledger.json", cap_usd=0.30)
            provider = ClaudeCLIProvider("haiku", executable=self.fake_cli(directory), attempts=1, ledger=ledger)
            provider.complete([ChatMessage(role="user", content="first")])
            state = ledger.snapshot()
            self.assertEqual((state["calls"], state["charged_usd"], state["reserved_usd"]), (1, 0.25, 0.0))
            # 0.25 is charged; the next call's worst case no longer fits under 0.30.
            Path(directory, "claude.args").unlink()
            with self.assertRaises(SpendLimitError):
                provider.complete([ChatMessage(role="user", content="x" * 400_000)])
            self.assertFalse(Path(directory, "claude.args").exists(), "a refused call must not start the CLI")
            self.assertEqual(ledger.snapshot()["refused_calls"], 1)

    def test_a_failed_call_is_charged_its_reservation(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "claude"
            path.write_text(f"#!{sys.executable}\nimport sys\nsys.exit(1)\n", encoding="utf-8")
            path.chmod(path.stat().st_mode | stat.S_IXUSR)
            ledger = SpendLedger(Path(directory) / "ledger.json", cap_usd=1.0)
            provider = ClaudeCLIProvider("haiku", executable=str(path), attempts=1, ledger=ledger)
            with self.assertRaises(Exception):
                provider.complete([ChatMessage(role="user", content="hello")])
            state = ledger.snapshot()
        self.assertEqual(state["unknown_cost_calls"], 1)
        self.assertAlmostEqual(state["charged_usd"], worst_case_usd("haiku", "", "hello"))
        self.assertEqual(state["reserved_usd"], 0.0)

    def test_every_attempt_is_reserved_and_settled(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            executable = _script(directory, "sys.exit(1)\n")
            ledger = SpendLedger(Path(directory) / "ledger.json", cap_usd=1.0)
            provider = ClaudeCLIProvider("haiku", executable=executable, attempts=2, ledger=ledger)
            with mock.patch("_claude_cli.time.sleep"), self.assertRaises(Exception):
                provider.complete([ChatMessage(role="user", content="hello")])
            state = ledger.snapshot()
            self.assertEqual(Path(executable + ".calls").read_text(), "xx")
        self.assertEqual((state["calls"], state["unknown_cost_calls"], state["reserved_usd"]), (2, 2, 0.0))
        self.assertAlmostEqual(state["charged_usd"], 2 * worst_case_usd("haiku", "", "hello"))

    def test_a_timeout_and_a_refusal_release_their_reservations(self) -> None:
        for body, timeout, error in (("time.sleep(5)\n", 0.2, Exception),
                                     ("print(json.dumps({'result': 'safeguards flagged this', 'is_error': True, "
                                      "'total_cost_usd': 0.01}))\nsys.exit(1)\n", 30.0, ModelRefusalError)):
            with tempfile.TemporaryDirectory() as directory:
                ledger = SpendLedger(Path(directory) / "ledger.json", cap_usd=1.0)
                provider = ClaudeCLIProvider("haiku", executable=_script(directory, body), attempts=1, ledger=ledger,
                                             timeout=timeout)
                with self.assertRaises(error):
                    provider.complete([ChatMessage(role="user", content="hello")])
                state = ledger.snapshot()
            self.assertEqual((state["calls"], state["reserved_usd"]), (1, 0.0))
            self.assertGreater(state["charged_usd"], 0.0)

    def test_an_error_reply_with_exit_code_zero_is_a_failure(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            executable = _script(directory, "print(json.dumps({'result': 'overloaded', 'is_error': True}))\n")
            with self.assertRaisesRegex(Exception, "overloaded"):
                ClaudeCLIProvider(executable=executable, attempts=1).complete([ChatMessage(role="user", content="hi")])

    def test_a_cost_that_is_not_a_finite_non_negative_number_is_charged_as_unknown(self) -> None:
        for cost in ("NaN", "-1", "true", '"0.1"'):
            with tempfile.TemporaryDirectory() as directory:
                executable = _script(directory, "print('{\"result\": \"ok\", \"is_error\": false, "
                                                f"\"total_cost_usd\": {cost.replace(chr(34), chr(92) + chr(34))}}}')\n")
                ledger = SpendLedger(Path(directory) / "ledger.json", cap_usd=1.0)
                ClaudeCLIProvider("haiku", executable=executable, attempts=1, ledger=ledger).complete(
                    [ChatMessage(role="user", content="hello")])
                state = ledger.snapshot()
            self.assertEqual(state["unknown_cost_calls"], 1, cost)
            self.assertAlmostEqual(state["charged_usd"], worst_case_usd("haiku", "", "hello"))

    def test_worst_case_bounds_tokens_by_bytes_and_applies_the_long_prompt_tier(self) -> None:
        short = worst_case_usd("claude-haiku-5-5", "s" * 1_000, "p" * 7_000)
        self.assertAlmostEqual(short, (10_000 * 0.10 * 2 + 4096 * 0.50) / 1e6)
        long = worst_case_usd("haiku", "", "p" * 200_000)
        self.assertAlmostEqual(long, 5 * (202_000 * 0.10 * 2 + 4096 * 0.50) / 1e6)
        self.assertGreater(worst_case_usd("sonnet", "", "hello"), worst_case_usd("haiku", "", "hello"))

    def test_only_sonnet_and_haiku_models_are_accepted(self) -> None:
        for model in ("sonnet", "haiku", "Haiku", "claude-sonnet-5-5", "claude-haiku-5-5", "claude-3-5-sonnet-20241022"):
            self.assertEqual(check_model(model), model)
        for model in ("opus", "claude-opus-5-5", "fable", "claude-fable-5-2", "claude-sonnetx", "", "best"):
            with self.assertRaisesRegex(ValueError, "limited to sonnet, haiku"):
                check_model(model)
        with self.assertRaises(ValueError):
            ClaudeCLIProvider("opus")


if __name__ == "__main__":
    unittest.main()
