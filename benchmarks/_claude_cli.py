"""An ``LLMProvider`` backed by the Claude Code CLI (``claude -p``), for benchmarks.

Lets the library's own LLM-assisted components (for example
``LLMQueryDecomposer``) run unchanged against a Claude model in environments
where Claude Code is installed and signed in but no API key is configured.
Each call is one non-interactive ``claude -p`` invocation with tools
disabled and no saved session; the system message becomes the system prompt
and the remaining messages are sent as the prompt text. Benchmark-only: it
spawns a process per call and is not part of the library.

The CLI is started with the user's customizations off (``--safe-mode``,
``--strict-mcp-config``, ``--disable-slash-commands``). Without these it adds
the machine's own MCP servers, skills and memory to every request: on one
workstation that was 117,154 input tokens for a two-word prompt, against 637
with them off. Besides the cost, that text would differ between machines and
enter every benchmark prompt.

Each call reports its list-price cost (``total_cost_usd`` of the CLI's JSON
output). A ``SpendLedger`` adds those up in a file and refuses a call whose
worst case would pass the cap.
"""

from __future__ import annotations

import fcntl
import json
import os
import subprocess
import time
from pathlib import Path
from typing import Sequence

from marmo_core.errors import ProviderError
from marmo_core.llm import ChatMessage, LLMProvider, LLMResponse, LLMToolSpec


class ModelRefusalError(ProviderError):
    """The model's safety system declined the request: retrying returns the same."""


class SpendLimitError(ProviderError):
    """The call was not sent: its worst-case cost would pass the ledger's cap."""


# Benchmarks may call only these model families through the CLI, to keep
# their usage within the subscription's limits. A family alias ("sonnet",
# "haiku") or a full model id of that family is accepted.
ALLOWED_MODEL_FAMILIES = ("sonnet", "haiku")

# List prices in USD per million tokens (input, output), checked 2026-11-28.
# They are used only for the worst case reserved before a call; what a call
# is charged afterwards is the cost the CLI reports.
LIST_PRICES = {"haiku": (0.10, 0.50), "sonnet": (2.00, 10.00)}
MAX_OUTPUT_TOKENS = 4096
# The CLI writes the whole prompt to the one-hour cache (twice the input
# price), and a prompt above 100,000 tokens is billed at a higher tier (five
# times, for Haiku). The CLI's own preamble is well under 2,000 tokens.
CACHE_WRITE_MULTIPLIER = 2.0
LONG_PROMPT_TOKENS = 100_000
LONG_PROMPT_MULTIPLIER = 5.0
PREAMBLE_TOKENS = 2_000
ISOLATION_FLAGS = ("--safe-mode", "--strict-mcp-config", "--disable-slash-commands")


def check_model(model: str) -> str:
    """Return ``model`` if it names an allowed family, else raise ``ValueError``."""

    name = model.strip().lower()
    # Full ids name the family as one dash-separated part, at any position
    # ("claude-haiku-5-5", "claude-3-5-sonnet-20241022").
    if name in ALLOWED_MODEL_FAMILIES or (
        name.startswith("claude-") and any(family in name.split("-") for family in ALLOWED_MODEL_FAMILIES)
    ):
        return model
    raise ValueError(
        f"benchmark Claude CLI calls are limited to {', '.join(ALLOWED_MODEL_FAMILIES)} models; got {model!r}"
    )


def worst_case_usd(model: str, system: str, prompt: str) -> float:
    """An upper bound on one attempt's list-price cost.

    A token is at least one byte, so the byte length bounds the input tokens.
    """

    family = next(family for family in ALLOWED_MODEL_FAMILIES if family in check_model(model).lower().split("-"))
    input_price, output_price = LIST_PRICES[family]
    input_tokens = len(system.encode("utf-8")) + len(prompt.encode("utf-8")) + PREAMBLE_TOKENS
    tier = LONG_PROMPT_MULTIPLIER if input_tokens > LONG_PROMPT_TOKENS else 1.0
    return tier * (input_tokens * input_price * CACHE_WRITE_MULTIPLIER + MAX_OUTPUT_TOKENS * output_price) / 1e6


class SpendLedger:
    """A dollar cap on CLI calls, kept in a JSON file that processes share.

    ``reserve`` admits a call only if what is already charged, what other
    calls have reserved and this call's worst case stay within the cap.
    ``settle`` replaces the reservation by the reported cost; a call whose
    cost is unknown (it failed or timed out) is charged its reservation.
    """

    def __init__(self, path: str | Path, cap_usd: float) -> None:
        if cap_usd <= 0:
            raise ValueError("the spend cap must be positive")
        self.path = Path(path)
        self.cap_usd = float(cap_usd)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def _update(self, change) -> dict:
        with open(self.path, "a+", encoding="utf-8") as handle:
            fcntl.flock(handle, fcntl.LOCK_EX)
            handle.seek(0)
            text = handle.read()
            state = json.loads(text) if text.strip() else {"charged_usd": 0.0, "reserved_usd": 0.0, "calls": 0,
                                                           "unknown_cost_calls": 0, "refused_calls": 0}
            change(state)
            handle.seek(0)
            handle.truncate()
            handle.write(json.dumps(state, indent=1, sort_keys=True) + "\n")
            handle.flush()
            os.fsync(handle.fileno())
            return state

    def snapshot(self) -> dict:
        return self._update(lambda state: None)

    def reserve(self, amount: float) -> None:
        def change(state: dict) -> None:
            if state["charged_usd"] + state["reserved_usd"] + amount > self.cap_usd + 1e-12:
                state["refused_calls"] += 1
                state["refused"] = True
            else:
                state["reserved_usd"] += amount
                state["refused"] = False

        state = self._update(change)
        if state["refused"]:
            raise SpendLimitError(
                f"CLI spend cap reached: ${state['charged_usd']:.4f} charged and ${state['reserved_usd']:.4f} "
                f"reserved of ${self.cap_usd:.2f}; a further ${amount:.4f} was refused"
            )

    def settle(self, reserved: float, reported: float | None) -> None:
        def change(state: dict) -> None:
            state["reserved_usd"] = max(0.0, state["reserved_usd"] - reserved)
            state["charged_usd"] += reserved if reported is None else reported
            state["calls"] += 1
            state["unknown_cost_calls"] += reported is None

        self._update(change)


class ClaudeCLIProvider(LLMProvider):
    def __init__(
        self,
        model: str = "sonnet",
        *,
        timeout: float = 180.0,
        executable: str = "claude",
        attempts: int = 4,
        ledger: SpendLedger | None = None,
    ) -> None:
        self.model = check_model(model)
        self.timeout = timeout
        self.executable = executable
        # The CLI fails transiently under rate limits; a failed call would be
        # cached as a failure by the LLM components, so retry with backoff.
        self.attempts = max(1, attempts)
        self.ledger = ledger

    def complete(self, messages: Sequence[ChatMessage], tools: Sequence[LLMToolSpec] = ()) -> LLMResponse:
        if tools:
            raise ProviderError("ClaudeCLIProvider does not support tool definitions")
        system = "\n\n".join(message.content for message in messages if message.role == "system")
        prompt = "\n\n".join(message.content for message in messages if message.role != "system")
        command = [self.executable, "-p", "--model", self.model, "--no-session-persistence", *ISOLATION_FLAGS,
                   "--output-format", "json", "--tools", ""]
        if system:
            command += ["--system-prompt", system]
        # ``--tools`` takes a variadic value list, so a bare prompt after it is
        # read as a tool name; ``--`` ends option parsing (also for prompts that
        # start with a dash).
        command += ["--", prompt]
        environment = {**os.environ, "CLAUDE_CODE_MAX_OUTPUT_TOKENS": str(MAX_OUTPUT_TOKENS)}
        worst = worst_case_usd(self.model, system, prompt)
        problem = ""
        for attempt in range(self.attempts):
            if attempt:
                time.sleep(10 * 2 ** (attempt - 1))
            if self.ledger is not None:
                self.ledger.reserve(worst)
            reported: float | None = None
            try:
                try:
                    completed = subprocess.run(
                        command, capture_output=True, text=True, timeout=self.timeout, env=environment
                    )
                except (OSError, subprocess.SubprocessError) as error:
                    problem = f"claude CLI failed: {error}"
                    continue
                reply = _parse(completed.stdout)
                if reply is not None and isinstance(reply.get("total_cost_usd"), (int, float)):
                    reported = float(reply["total_cost_usd"])
                text = str(reply.get("result") or "").strip() if reply is not None else ""
                if completed.returncode == 0 and reply is not None and not reply.get("is_error") and text:
                    return LLMResponse(content=text)
                detail = text or (completed.stderr or completed.stdout).strip()
                problem = f"claude CLI exited {completed.returncode}: {detail[:300]}"
                if "safeguards flagged" in problem:
                    raise ModelRefusalError(problem)
            finally:
                if self.ledger is not None:
                    self.ledger.settle(worst, reported)
        raise ProviderError(problem)


def add_spend_arguments(parser) -> None:
    """Add the two options that put a script's CLI calls under a ``SpendLedger``."""

    parser.add_argument("--spend-cap-usd", type=float,
                        help="refuse a model call whose worst-case list-price cost would pass this total")
    parser.add_argument("--spend-ledger", help="file that adds up the cost of the calls (required with the cap)")


def ledger_from_arguments(parser, args) -> SpendLedger | None:
    if (args.spend_cap_usd is None) != (args.spend_ledger is None):
        parser.error("--spend-cap-usd and --spend-ledger are given together")
    return None if args.spend_cap_usd is None else SpendLedger(args.spend_ledger, args.spend_cap_usd)


def _parse(output: str) -> dict | None:
    try:
        reply = json.loads(output)
    except ValueError:
        return None
    return reply if isinstance(reply, dict) else None
