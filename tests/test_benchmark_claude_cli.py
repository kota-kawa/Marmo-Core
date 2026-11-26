from __future__ import annotations

import stat
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "benchmarks"))

from _claude_cli import ClaudeCLIProvider, ModelRefusalError, check_model  # noqa: E402
from marmo_core import ChatMessage  # noqa: E402

# Mimics the CLI's parsing: ``--tools`` consumes every following value that is
# not an option, and ``--`` ends option parsing.
FAKE_CLI = textwrap.dedent(
    """\
    #!{python}
    import sys
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
        if arg in ("--model", "--system-prompt"):
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
    print("echo:" + positional[-1])
    """
)


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
                "print(\"API Error: Sonnet's safeguards flagged this message\")\n"
                "sys.exit(1)\n",
                encoding="utf-8",
            )
            path.chmod(path.stat().st_mode | stat.S_IXUSR)
            provider = ClaudeCLIProvider(executable=str(path), attempts=4)
            with self.assertRaises(ModelRefusalError):
                provider.complete([ChatMessage(role="user", content="hello")])
            self.assertEqual((Path(directory) / "claude.calls").read_text(), "x")

    def test_only_sonnet_and_haiku_models_are_accepted(self) -> None:
        for model in ("sonnet", "haiku", "Haiku", "claude-sonnet-5-5", "claude-haiku-5-5"):
            self.assertEqual(check_model(model), model)
        for model in ("opus", "claude-opus-5-5", "fable", "claude-fable-5-2", "", "best"):
            with self.assertRaisesRegex(ValueError, "limited to sonnet, haiku"):
                check_model(model)
        with self.assertRaises(ValueError):
            ClaudeCLIProvider("opus")


if __name__ == "__main__":
    unittest.main()
