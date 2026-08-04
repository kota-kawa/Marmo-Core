"""LLM provider abstraction and the zero-dependency deterministic mock."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
import re
from typing import Any, Mapping, Sequence

from .secrets import sanitize_secret_inputs


@dataclass(frozen=True)
class ToolCall:
    """One tool invocation requested by the model."""

    id: str
    name: str
    arguments: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "arguments": sanitize_secret_inputs(self.arguments),
        }


@dataclass(frozen=True)
class ChatMessage:
    """Provider-neutral chat message."""

    role: str  # system / user / assistant / tool
    content: str
    name: str = ""
    tool_calls: tuple[ToolCall, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        data: dict[str, Any] = {"role": self.role, "content": self.content}
        if self.name:
            data["name"] = self.name
        if self.tool_calls:
            data["tool_calls"] = [call.to_dict() for call in self.tool_calls]
        return data


@dataclass(frozen=True)
class LLMToolSpec:
    """Tool definition passed to the model, converted from resource metadata."""

    name: str
    description: str
    input_schema: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {"name": self.name, "description": self.description, "input_schema": self.input_schema}


@dataclass(frozen=True)
class LLMResponse:
    """Provider-neutral completion result."""

    content: str
    tool_calls: tuple[ToolCall, ...] = ()
    finish_reason: str = "stop"
    usage: dict[str, int] = field(default_factory=dict)


class LLMProvider(ABC):
    """Abstract LLM interface (F-LLM-01). The kernel depends only on this."""

    @abstractmethod
    def complete(self, messages: Sequence[ChatMessage], tools: Sequence[LLMToolSpec] = ()) -> LLMResponse:
        """Run one chat completion, optionally with tool definitions."""


class MockLLMProvider(LLMProvider):
    """Deterministic zero-dependency provider for tests, replay, and demos (F-LLM-04).

    Two modes:
    - scripted: return the given responses in order, raising when exhausted.
    - rule-based (default): call the first available tool once, using
      ``tool_arguments`` overrides or defaults derived from the input schema,
      then produce a final answer that echoes the tool output.
    """

    def __init__(
        self,
        *,
        script: Sequence[LLMResponse] | None = None,
        tool_arguments: Mapping[str, Mapping[str, Any]] | None = None,
    ) -> None:
        self.script = list(script or [])
        self.tool_arguments = {name: dict(args) for name, args in (tool_arguments or {}).items()}
        self.requests: list[dict[str, Any]] = []
        self._cursor = 0

    def complete(self, messages: Sequence[ChatMessage], tools: Sequence[LLMToolSpec] = ()) -> LLMResponse:
        self.requests.append(
            {
                "messages": [message.to_dict() for message in messages],
                "tools": [tool.to_dict() for tool in tools],
            }
        )
        if self.script:
            if self._cursor >= len(self.script):
                raise ValueError(
                    "mock LLM script is exhausted; add more scripted responses or raise max_tool_calls"
                )
            response = self.script[self._cursor]
            self._cursor += 1
            return response
        return self._rule_based(messages, tools)

    def _rule_based(self, messages: Sequence[ChatMessage], tools: Sequence[LLMToolSpec]) -> LLMResponse:
        has_tool_result = any(message.role == "tool" for message in messages)
        if tools and not has_tool_result:
            spec = tools[0]
            arguments = self.tool_arguments.get(spec.name)
            if arguments is None:
                arguments = default_arguments(spec.input_schema)
            call = ToolCall(id=f"call-{len(self.requests)}", name=spec.name, arguments=dict(arguments))
            return LLMResponse(
                content="",
                tool_calls=(call,),
                finish_reason="tool_calls",
                usage=_usage(messages, ""),
            )
        last_tool = next((message for message in reversed(messages) if message.role == "tool"), None)
        if last_tool is not None:
            content = f"Task complete. Tool {last_tool.name} returned: {_display_tool_content(last_tool.content)}"
        else:
            goal = next((message.content for message in messages if message.role == "user"), "")
            content = f"Task complete. No tool was required for: {goal}"
        return LLMResponse(content=content, usage=_usage(messages, content))


def _display_tool_content(content: str) -> str:
    """Keep deterministic mock output concise while preserving the LLM boundary."""

    opening = content.find("<untrusted-content")
    if opening < 0:
        return content
    opening_end = content.find(">\n", opening)
    closing = content.rfind("\n</untrusted-content>")
    if opening_end >= 0 and closing > opening_end:
        return content[opening_end + 2 : closing]
    return content


def default_arguments(input_schema: Mapping[str, Any]) -> dict[str, Any]:
    """Build deterministic arguments from a lightweight JSON Schema subset."""

    properties = input_schema.get("properties") if isinstance(input_schema, Mapping) else None
    properties = properties if isinstance(properties, Mapping) else {}
    required = input_schema.get("required") if isinstance(input_schema, Mapping) else None
    required = required if isinstance(required, list) else []
    type_defaults: dict[str, Any] = {
        "string": "",
        "number": 0.0,
        "integer": 0,
        "boolean": False,
        "array": [],
        "object": {},
    }
    arguments: dict[str, Any] = {}
    for name in required:
        prop = properties.get(name)
        prop = prop if isinstance(prop, Mapping) else {}
        if "default" in prop:
            arguments[name] = prop["default"]
        else:
            arguments[name] = type_defaults.get(prop.get("type", "string"), "")
    for name, prop in properties.items():
        if name not in arguments and isinstance(prop, Mapping) and "default" in prop:
            arguments[name] = prop["default"]
    return arguments


def _usage(messages: Sequence[ChatMessage], output: str) -> dict[str, int]:
    input_chars = sum(len(message.content) for message in messages)
    return {
        "input_tokens": max(input_chars // 4, 1),
        "output_tokens": max(len(output) // 4, 1) if output else 0,
    }


def estimate_tokens(text: str) -> int:
    """Cheap token estimate used until a tokenizer extra is installed (F-CTX-07)."""

    return max(len(text) // 4, 1) if text else 0


def tokenize(text: str) -> tuple[str, ...]:
    """Split text into deterministic word and punctuation tokens without extras."""

    return tuple(re.findall(r"\w+|[^\w\s]", text.lower(), flags=re.UNICODE))
