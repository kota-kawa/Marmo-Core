"""Real LLM providers implementing the ``LLMProvider`` interface (F-LLM-02).

These reference adapters speak raw HTTP through ``urllib`` instead of vendor
SDKs. They cover the kernel's needs (chat completion + tool calls + usage);
applications that want
streaming, retries, or the full feature surface should wrap the official
vendor SDK behind the same ``LLMProvider`` interface as an optional extra.

Both providers accept a ``transport`` callable ``(url, payload, headers,
timeout) -> dict`` so tests run offline. API keys come from the environment
(``ANTHROPIC_API_KEY`` / ``OPENAI_API_KEY``) unless passed explicitly; keys
are held by the provider and never enter prompts, state, or logs (F-SEC-06) —
error bodies are run through ``redact_credentials`` before they reach an
exception, because providers echo the rejected key back in 401 responses.

Marmo resource ids such as ``tool.files.read-text`` contain dots, which both
the OpenAI and Anthropic tool-name grammars reject (``^[a-zA-Z0-9_-]{1,64}$``).
Every provider therefore runs tool names through a :class:`ToolNameCodec`
on the way out and maps the model's calls back to the original ids on the
way in, so the kernel, audit log, and resource registry only ever see real
resource ids.
"""

from __future__ import annotations

from typing import Any, Callable, Mapping, Sequence
import hashlib
import json
import os
import re

from .environment import (
    load_local_dotenv,
    optional_environment,
    required_environment,
    required_positive_int_environment,
)
from .errors import ProviderHTTPError
from .llm import ChatMessage, LLMProvider, LLMResponse, LLMToolSpec, ToolCall
from .semantic import DEFAULT_OPENAI_BASE_URL, _post_json, with_missing_api_key_hint

ANTHROPIC_VERSION = "2023-06-01"

Transport = Callable[[str, dict, dict, float], dict]

_SAFE_TOOL_NAME_RE = re.compile(r"[^a-zA-Z0-9_-]")
_TOOL_NAME_MAX_LENGTH = 64
_MAX_TOKENS_PARAMETERS = ("max_completion_tokens", "max_tokens")


class ToolNameCodec:
    """Reversible mapping between resource ids and provider-safe tool names.

    Encoding is deterministic (dots and other disallowed characters become
    ``_``; over-long names get a short hash suffix) and collisions between
    distinct ids are resolved with the same hash suffix, so the same
    resource always gets the same wire name within one provider instance.
    """

    def __init__(self) -> None:
        self._original_by_encoded: dict[str, str] = {}
        self._encoded_by_original: dict[str, str] = {}

    def encode(self, name: str) -> str:
        cached = self._encoded_by_original.get(name)
        if cached is not None:
            return cached
        candidate = _SAFE_TOOL_NAME_RE.sub("_", name) or "tool"
        if len(candidate) > _TOOL_NAME_MAX_LENGTH:
            candidate = _with_hash_suffix(candidate, name)
        existing = self._original_by_encoded.get(candidate)
        if existing is not None and existing != name:
            candidate = _with_hash_suffix(candidate, name)
        self._original_by_encoded[candidate] = name
        self._encoded_by_original[name] = candidate
        return candidate

    def decode(self, name: str) -> str:
        return self._original_by_encoded.get(name, name)


def _with_hash_suffix(candidate: str, original: str) -> str:
    digest = hashlib.sha1(original.encode("utf-8")).hexdigest()[:8]
    return f"{candidate[: _TOOL_NAME_MAX_LENGTH - 9]}_{digest}"


class AnthropicLLMProvider(LLMProvider):
    """Claude via the Anthropic Messages API using raw HTTP."""

    def __init__(
        self,
        model: str | None = None,
        *,
        api_key: str | None = None,
        base_url: str = "https://api.anthropic.com",
        max_tokens: int | None = None,
        timeout: float = 120.0,
        transport: Transport | None = None,
    ) -> None:
        self.model = model if model is not None else required_environment("ANTHROPIC_MODEL")
        if api_key is None:
            load_local_dotenv()
        self.api_key = api_key if api_key is not None else os.environ.get("ANTHROPIC_API_KEY", "")
        self.base_url = base_url.rstrip("/")
        self.max_tokens = (
            max_tokens
            if max_tokens is not None
            else required_positive_int_environment("ANTHROPIC_MAX_TOKENS")
        )
        self.timeout = timeout
        self.transport = transport or _post_json
        self.tool_names = ToolNameCodec()

    def complete(self, messages: Sequence[ChatMessage], tools: Sequence[LLMToolSpec] = ()) -> LLMResponse:
        payload = self.build_request(messages, tools)
        headers = {
            "Content-Type": "application/json",
            "x-api-key": self.api_key,
            "anthropic-version": ANTHROPIC_VERSION,
        }
        response = self.transport(f"{self.base_url}/v1/messages", payload, headers, self.timeout)
        return self.parse_response(response)

    def build_request(self, messages: Sequence[ChatMessage], tools: Sequence[LLMToolSpec]) -> dict[str, Any]:
        system_parts = [message.content for message in messages if message.role == "system"]
        payload: dict[str, Any] = {
            "model": self.model,
            "max_tokens": self.max_tokens,
            "messages": _to_anthropic_messages(messages, self.tool_names.encode),
        }
        if system_parts:
            payload["system"] = "\n\n".join(part for part in system_parts if part)
        if tools:
            payload["tools"] = [
                {
                    "name": self.tool_names.encode(tool.name),
                    "description": tool.description,
                    "input_schema": tool.input_schema,
                }
                for tool in tools
            ]
        return payload

    def parse_response(self, response: Mapping[str, Any]) -> LLMResponse:
        text_parts: list[str] = []
        tool_calls: list[ToolCall] = []
        for block in response.get("content", []) or []:
            if not isinstance(block, Mapping):
                continue
            if block.get("type") == "text":
                text_parts.append(str(block.get("text", "")))
            elif block.get("type") == "tool_use":
                tool_calls.append(
                    ToolCall(
                        id=str(block.get("id", "")),
                        name=self.tool_names.decode(str(block.get("name", ""))),
                        arguments=dict(block.get("input", {}) or {}),
                    )
                )
        stop_reason = str(response.get("stop_reason", "") or "")
        finish_reason = {
            "tool_use": "tool_calls",
            "end_turn": "stop",
            "max_tokens": "length",
        }.get(stop_reason, stop_reason or "stop")
        usage = _parse_usage(response.get("usage"), "input_tokens", "output_tokens")
        return LLMResponse(
            content="".join(text_parts),
            tool_calls=tuple(tool_calls),
            finish_reason=finish_reason,
            usage=usage,
        )


class OpenAICompatibleLLMProvider(LLMProvider):
    """Chat completions from any OpenAI-compatible endpoint (raw HTTP).

    Works with OpenAI itself and with local OpenAI-compatible servers
    (vLLM, llama.cpp server, Ollama's ``/v1``), which keeps the fully
    offline / on-prem path open.

    Current OpenAI models reject the legacy ``max_tokens`` parameter in favor
    of ``max_completion_tokens`` while many self-hosted servers only know
    ``max_tokens``. The provider picks ``max_completion_tokens`` for
    ``openai.com`` endpoints and ``max_tokens`` elsewhere, and if the server
    reports the chosen parameter as unsupported it switches once and retries.
    Pass ``max_tokens_parameter`` to pin either name explicitly.

    ``base_url`` falls back to ``OPENAI_BASE_URL`` from the environment or
    ``.env`` (for example ``https://api.groq.com/openai/v1``), then to the
    OpenAI endpoint.
    """

    def __init__(
        self,
        model: str | None = None,
        *,
        api_key: str | None = None,
        base_url: str | None = None,
        max_tokens: int = 4096,
        timeout: float = 120.0,
        temperature: float | None = None,
        reasoning_effort: str | None = None,
        max_tokens_parameter: str | None = None,
        transport: Transport | None = None,
    ) -> None:
        model_from_environment = model is None
        self.model = model if model is not None else required_environment("OPENAI_MODEL")
        if api_key is None or base_url is None:
            load_local_dotenv()
        self.api_key = api_key if api_key is not None else os.environ.get("OPENAI_API_KEY", "")
        if base_url is None:
            base_url = optional_environment("OPENAI_BASE_URL") or DEFAULT_OPENAI_BASE_URL
        self.base_url = base_url.rstrip("/")
        self.max_tokens = max_tokens
        self.timeout = timeout
        self.temperature = temperature
        self.reasoning_effort = (
            optional_environment("OPENAI_REASONING_EFFORT")
            if reasoning_effort is None and model_from_environment
            else reasoning_effort
        )
        if max_tokens_parameter is not None and max_tokens_parameter not in _MAX_TOKENS_PARAMETERS:
            raise ValueError(f"max_tokens_parameter must be one of {_MAX_TOKENS_PARAMETERS}: {max_tokens_parameter}")
        self.max_tokens_parameter = max_tokens_parameter or _default_max_tokens_parameter(self.base_url)
        self.transport = transport or _post_json
        self.tool_names = ToolNameCodec()

    def complete(self, messages: Sequence[ChatMessage], tools: Sequence[LLMToolSpec] = ()) -> LLMResponse:
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        url = f"{self.base_url}/chat/completions"
        payload = self.build_request(messages, tools)
        try:
            response = self._request(url, payload, headers)
        except ProviderHTTPError as exc:
            alternative = _alternative_max_tokens_parameter(exc, self.max_tokens_parameter)
            if alternative is None:
                raise
            self.max_tokens_parameter = alternative
            response = self._request(url, self.build_request(messages, tools), headers)
        return self.parse_response(response)

    def _request(self, url: str, payload: dict[str, Any], headers: dict[str, str]) -> dict:
        try:
            return self.transport(url, payload, headers, self.timeout)
        except ProviderHTTPError as exc:
            # A 401/403 with no key configured is otherwise reported as the
            # server's bare "Invalid API Key", which hides the actual cause.
            raise with_missing_api_key_hint(exc, self.api_key) from None

    def build_request(self, messages: Sequence[ChatMessage], tools: Sequence[LLMToolSpec]) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "model": self.model,
            self.max_tokens_parameter: self.max_tokens,
            "messages": _to_openai_messages(messages, self.tool_names.encode),
        }
        if self.temperature is not None:
            payload["temperature"] = self.temperature
        if self.reasoning_effort is not None:
            payload["reasoning_effort"] = self.reasoning_effort
        if tools:
            payload["tools"] = [
                {
                    "type": "function",
                    "function": {
                        "name": self.tool_names.encode(tool.name),
                        "description": tool.description,
                        "parameters": tool.input_schema,
                    },
                }
                for tool in tools
            ]
        return payload

    def parse_response(self, response: Mapping[str, Any]) -> LLMResponse:
        choices = response.get("choices") or []
        message = choices[0].get("message", {}) if choices else {}
        tool_calls: list[ToolCall] = []
        for call in message.get("tool_calls") or []:
            function = call.get("function", {}) or {}
            raw_arguments = function.get("arguments", "{}")
            try:
                arguments = json.loads(raw_arguments) if isinstance(raw_arguments, str) else dict(raw_arguments)
            except json.JSONDecodeError:
                arguments = {"_raw": raw_arguments}
            tool_calls.append(
                ToolCall(
                    id=str(call.get("id", "")),
                    name=self.tool_names.decode(str(function.get("name", ""))),
                    arguments=arguments,
                )
            )
        finish = str(choices[0].get("finish_reason", "stop") or "stop") if choices else "stop"
        usage = _parse_usage(response.get("usage"), "prompt_tokens", "completion_tokens")
        return LLMResponse(
            content=str(message.get("content") or ""),
            tool_calls=tuple(tool_calls),
            finish_reason="tool_calls" if finish == "tool_calls" else finish,
            usage=usage,
        )


def _parse_usage(data: Any, input_key: str, output_key: str) -> dict[str, int]:
    if not isinstance(data, Mapping):
        return {}
    input_raw = data.get(input_key)
    output_raw = data.get(output_key)
    if input_raw is None or output_raw is None or isinstance(input_raw, bool) or isinstance(output_raw, bool):
        return {}
    try:
        input_tokens = int(input_raw)
        output_tokens = int(output_raw)
    except (TypeError, ValueError, OverflowError):
        return {}
    if input_tokens < 0 or output_tokens < 0:
        return {}
    return {"input_tokens": input_tokens, "output_tokens": output_tokens}


def _default_max_tokens_parameter(base_url: str) -> str:
    host = re.sub(r"^[a-z]+://", "", base_url.lower()).split("/", 1)[0].split(":", 1)[0]
    return "max_completion_tokens" if host == "openai.com" or host.endswith(".openai.com") else "max_tokens"


def _alternative_max_tokens_parameter(exc: ProviderHTTPError, current: str) -> str | None:
    """Return the other max-tokens parameter name when the server rejected the current one."""

    if exc.status != 400:
        return None
    parameter = ""
    try:
        error = json.loads(exc.body).get("error", {})
        parameter = str(error.get("param") or "")
        message = str(error.get("message") or "")
    except (TypeError, ValueError, AttributeError):
        message = exc.body
    if parameter != current and current not in message:
        return None
    return next(candidate for candidate in _MAX_TOKENS_PARAMETERS if candidate != current)


def _to_anthropic_messages(
    messages: Sequence[ChatMessage], encode: Callable[[str], str] = lambda name: name
) -> list[dict[str, Any]]:
    """Map provider-neutral messages to Anthropic content blocks.

    ``ChatMessage`` carries no tool-call id on tool results, so ids are
    reconstructed by matching each tool result (in order) against the pending
    tool calls of the preceding assistant turn.
    """

    converted: list[dict[str, Any]] = []
    pending_calls: list[ToolCall] = []
    for message in messages:
        if message.role == "system":
            continue  # hoisted to the top-level system parameter
        if message.role == "assistant":
            blocks: list[dict[str, Any]] = []
            if message.content:
                blocks.append({"type": "text", "text": message.content})
            for call in message.tool_calls:
                blocks.append(
                    {"type": "tool_use", "id": call.id, "name": encode(call.name), "input": call.arguments}
                )
            pending_calls = list(message.tool_calls)
            converted.append({"role": "assistant", "content": blocks or [{"type": "text", "text": ""}]})
        elif message.role == "tool":
            call_id = _match_pending_call(pending_calls, message.name)
            converted.append(
                {
                    "role": "user",
                    "content": [
                        {"type": "tool_result", "tool_use_id": call_id, "content": message.content}
                    ],
                }
            )
        else:
            converted.append({"role": "user", "content": message.content})
    return converted


def _to_openai_messages(
    messages: Sequence[ChatMessage], encode: Callable[[str], str] = lambda name: name
) -> list[dict[str, Any]]:
    converted: list[dict[str, Any]] = []
    pending_calls: list[ToolCall] = []
    for message in messages:
        if message.role == "assistant":
            entry: dict[str, Any] = {"role": "assistant", "content": message.content or None}
            if message.tool_calls:
                entry["tool_calls"] = [
                    {
                        "id": call.id,
                        "type": "function",
                        "function": {"name": encode(call.name), "arguments": json.dumps(call.arguments)},
                    }
                    for call in message.tool_calls
                ]
                pending_calls = list(message.tool_calls)
            converted.append(entry)
        elif message.role == "tool":
            call_id = _match_pending_call(pending_calls, message.name)
            converted.append(
                {"role": "tool", "tool_call_id": call_id, "content": message.content}
            )
        else:
            converted.append({"role": message.role, "content": message.content})
    return converted


def _match_pending_call(pending_calls: list[ToolCall], tool_name: str) -> str:
    for index, call in enumerate(pending_calls):
        if call.name == tool_name or not tool_name:
            return pending_calls.pop(index).id
    return pending_calls.pop(0).id if pending_calls else "call-unknown"
