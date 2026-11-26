"""An ``LLMProvider`` backed by the Claude Code CLI (``claude -p``), for benchmarks.

Lets the library's own LLM-assisted components (for example
``LLMQueryDecomposer``) run unchanged against a Claude model in environments
where Claude Code is installed and signed in but no API key is configured.
Each call is one non-interactive ``claude -p`` invocation with tools
disabled and no saved session; the system message becomes the system prompt
and the remaining messages are sent as the prompt text. Benchmark-only: it
spawns a process per call and is not part of the library.
"""

from __future__ import annotations

import subprocess
import time
from typing import Sequence

from marmo_core.errors import ProviderError
from marmo_core.llm import ChatMessage, LLMProvider, LLMResponse, LLMToolSpec


class ModelRefusalError(ProviderError):
    """The model's safety system declined the request: retrying returns the same."""


# Benchmarks may call only these model families through the CLI, to keep
# their usage within the subscription's limits. A family alias ("sonnet",
# "haiku") or a full model id of that family ("claude-sonnet-...") is accepted.
ALLOWED_MODEL_FAMILIES = ("sonnet", "haiku")


def check_model(model: str) -> str:
    """Return ``model`` if it names an allowed family, else raise ``ValueError``."""

    name = model.strip().lower()
    if name in ALLOWED_MODEL_FAMILIES or any(name.startswith(f"claude-{family}") for family in ALLOWED_MODEL_FAMILIES):
        return model
    raise ValueError(
        f"benchmark Claude CLI calls are limited to {', '.join(ALLOWED_MODEL_FAMILIES)} models; got {model!r}"
    )


class ClaudeCLIProvider(LLMProvider):
    def __init__(
        self, model: str = "sonnet", *, timeout: float = 180.0, executable: str = "claude", attempts: int = 4
    ) -> None:
        self.model = check_model(model)
        self.timeout = timeout
        self.executable = executable
        # The CLI fails transiently under rate limits; a failed call would be
        # cached as a failure by the LLM components, so retry with backoff.
        self.attempts = max(1, attempts)

    def complete(self, messages: Sequence[ChatMessage], tools: Sequence[LLMToolSpec] = ()) -> LLMResponse:
        if tools:
            raise ProviderError("ClaudeCLIProvider does not support tool definitions")
        system = "\n\n".join(message.content for message in messages if message.role == "system")
        prompt = "\n\n".join(message.content for message in messages if message.role != "system")
        command = [self.executable, "-p", "--model", self.model, "--no-session-persistence", "--tools", ""]
        if system:
            command += ["--system-prompt", system]
        # ``--tools`` takes a variadic value list, so a bare prompt after it is
        # read as a tool name; ``--`` ends option parsing (also for prompts that
        # start with a dash).
        command += ["--", prompt]
        problem = ""
        for attempt in range(self.attempts):
            if attempt:
                time.sleep(10 * 2 ** (attempt - 1))
            try:
                completed = subprocess.run(command, capture_output=True, text=True, timeout=self.timeout)
            except (OSError, subprocess.SubprocessError) as error:
                problem = f"claude CLI failed: {error}"
                continue
            if completed.returncode == 0 and completed.stdout.strip():
                return LLMResponse(content=completed.stdout.strip())
            problem = f"claude CLI exited {completed.returncode}: {(completed.stderr or completed.stdout).strip()[:300]}"
            if "safeguards flagged" in problem:
                raise ModelRefusalError(problem)
        raise ProviderError(problem)
