"""Real LLM providers implementing the ``LLMProvider`` interface (F-LLM-02).

Marmo-Core's core stays dependency-free, so these reference adapters speak
raw HTTP through ``urllib`` instead of vendor SDKs. They cover the kernel's
needs (chat completion + tool calls + usage); applications that want
streaming, retries, or the full feature surface should wrap the official
vendor SDK behind the same ``LLMProvider`` interface as an optional extra.

Both providers accept a ``transport`` callable ``(url, payload, headers,
timeout) -> dict`` so tests run offline. API keys come from the environment
(``ANTHROPIC_API_KEY`` / ``OPENAI_API_KEY``) unless passed explicitly; keys
are held by the provider and never enter prompts, state, or logs (F-SEC-06).
"""

from __future__ import annotations

from typing import Any, Callable, Mapping, Sequence
import json
import os

from .llm import ChatMessage, LLMProvider, LLMResponse, LLMToolSpec, ToolCall
from .semantic import _post_json

ANTHROPIC_VERSION = "2023-06-01"
DEFAULT_ANTHROPIC_MODEL = "claude-opus-4-8"
DEFAULT_OPENAI_MODEL = "gpt-4o-mini"

Transport = Callable[[str, dict, dict, float], dict]


class AnthropicLLMProvider(LLMProvider):
    """Claude via the Anthropic Messages API (raw HTTP, zero-dependency)."""

    def __init__(
        self,
        model: str = DEFAULT_ANTHROPIC_MODEL,
        *,
        api_key: str | None = None,
        base_url: str = "https://api.anthropic.com",
        max_tokens: int = 4096,
        timeout: float = 120.0,
        transport: Transport | None = None,
    ) -> None:
        self.model = model
        self.api_key = api_key if api_key is not None else os.environ.get("ANTHROPIC_API_KEY", "")
        self.base_url = base_url.rstrip("/")
        self.max_tokens = max_tokens
        self.timeout = timeout
        self.transport = transport or _post_json

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
            "messages": _to_anthropic_messages(messages),
        }
        if system_parts:
            payload["system"] = "\n\n".join(part for part in system_parts if part)
        if tools:
            payload["tools"] = [
                {"name": tool.name, "description": tool.description, "input_schema": tool.input_schema}
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
                        name=str(block.get("name", "")),
                        arguments=dict(block.get("input", {}) or {}),
                    )
                )
        stop_reason = str(response.get("stop_reason", "") or "")
        finish_reason = {
            "tool_use": "tool_calls",
            "end_turn": "stop",
            "max_tokens": "length",
        }.get(stop_reason, stop_reason or "stop")
        usage_data = response.get("usage", {}) or {}
        usage = {
            "input_tokens": int(usage_data.get("input_tokens", 0) or 0),
            "output_tokens": int(usage_data.get("output_tokens", 0) or 0),
        }
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
    """

    def __init__(
        self,
        model: str = DEFAULT_OPENAI_MODEL,
        *,
        api_key: str | None = None,
        base_url: str = "https://api.openai.com/v1",
        max_tokens: int = 4096,
        timeout: float = 120.0,
        temperature: float | None = None,
        transport: Transport | None = None,
    ) -> None:
        self.model = model
        self.api_key = api_key if api_key is not None else os.environ.get("OPENAI_API_KEY", "")
        self.base_url = base_url.rstrip("/")
        self.max_tokens = max_tokens
        self.timeout = timeout
        self.temperature = temperature
        self.transport = transport or _post_json

    def complete(self, messages: Sequence[ChatMessage], tools: Sequence[LLMToolSpec] = ()) -> LLMResponse:
        payload = self.build_request(messages, tools)
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        response = self.transport(f"{self.base_url}/chat/completions", payload, headers, self.timeout)
        return self.parse_response(response)

    def build_request(self, messages: Sequence[ChatMessage], tools: Sequence[LLMToolSpec]) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "model": self.model,
            "max_tokens": self.max_tokens,
            "messages": _to_openai_messages(messages),
        }
        if self.temperature is not None:
            payload["temperature"] = self.temperature
        if tools:
            payload["tools"] = [
                {
                    "type": "function",
                    "function": {
                        "name": tool.name,
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
                    name=str(function.get("name", "")),
                    arguments=arguments,
                )
            )
        finish = str(choices[0].get("finish_reason", "stop") or "stop") if choices else "stop"
        usage_data = response.get("usage", {}) or {}
        usage = {
            "input_tokens": int(usage_data.get("prompt_tokens", 0) or 0),
            "output_tokens": int(usage_data.get("completion_tokens", 0) or 0),
        }
        return LLMResponse(
            content=str(message.get("content") or ""),
            tool_calls=tuple(tool_calls),
            finish_reason="tool_calls" if finish == "tool_calls" else finish,
            usage=usage,
        )


def _to_anthropic_messages(messages: Sequence[ChatMessage]) -> list[dict[str, Any]]:
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
                blocks.append({"type": "tool_use", "id": call.id, "name": call.name, "input": call.arguments})
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


def _to_openai_messages(messages: Sequence[ChatMessage]) -> list[dict[str, Any]]:
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
                        "function": {"name": call.name, "arguments": json.dumps(call.arguments)},
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
