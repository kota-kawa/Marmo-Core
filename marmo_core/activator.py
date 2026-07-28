"""Resource Activator: type-specific activation behind the activation gate (4.4).

Every activation passes the Policy Gateway activation gate first (F-GATE-01).
Activation patterns implemented in this phase:

- memory -> retrieve and inject (F-ACT-01)
- skill  -> retrieve and load   (F-ACT-02)
- tool   -> retrieve and bind   (F-ACT-03)
- agent  -> retrieve and bind   (F-ACT-04)
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Mapping
import importlib

from .errors import ActivationError
from .models import ResourceDefinition, ResourceKind, ResourceMetadata
from .policy import PolicyContext, PolicyDecision, PolicyGateway


@dataclass(frozen=True)
class InjectedMemory:
    """Memory content resolved for prompt injection."""

    definition: ResourceDefinition
    content: str

    @property
    def metadata(self) -> ResourceMetadata:
        return self.definition.metadata


@dataclass(frozen=True)
class LoadedSkill:
    """Skill instructions loaded as guidance text."""

    definition: ResourceDefinition
    instructions: str

    @property
    def metadata(self) -> ResourceMetadata:
        return self.definition.metadata


@dataclass(frozen=True)
class BoundTool:
    """Tool bound to an executable handler; the handler never reaches the LLM."""

    definition: ResourceDefinition
    input_schema: dict[str, Any]
    output_schema: dict[str, Any]
    handler: Callable[..., Any]

    @property
    def metadata(self) -> ResourceMetadata:
        return self.definition.metadata


@dataclass(frozen=True)
class BoundAgent:
    """Agent bound as a synchronous tool-style delegate (F-AGENT-01)."""

    definition: ResourceDefinition
    input_schema: dict[str, Any]
    output_schema: dict[str, Any]
    handler: Callable[..., Any]
    delegation_interface: str = "tool_wrap"

    @property
    def metadata(self) -> ResourceMetadata:
        return self.definition.metadata


@dataclass(frozen=True)
class Activation:
    """Outcome of one gated activation attempt."""

    definition: ResourceDefinition
    decision: PolicyDecision
    activated: InjectedMemory | LoadedSkill | BoundTool | BoundAgent | None = None
    error: str | None = None

    @property
    def ok(self) -> bool:
        return self.activated is not None and self.decision.allowed


class ResourceActivator:
    """Activate resources per kind after the mandatory activation gate."""

    def __init__(
        self,
        gateway: PolicyGateway | None = None,
        *,
        tool_implementations: Mapping[str, Callable[..., Any]] | None = None,
        agent_implementations: Mapping[str, Callable[..., Any]] | None = None,
    ) -> None:
        self.gateway = gateway or PolicyGateway()
        self.tool_implementations = dict(tool_implementations or {})
        self.agent_implementations = dict(agent_implementations or {})

    def bind_tool(self, resource_id: str, handler: Callable[..., Any]) -> None:
        self.tool_implementations[resource_id] = handler

    def bind_agent(self, resource_id: str, handler: Callable[..., Any]) -> None:
        self.agent_implementations[resource_id] = handler

    def activate(self, definition: ResourceDefinition, context: PolicyContext | None = None) -> Activation:
        decision = self.gateway.evaluate(definition, context, gate="activation")
        if not decision.allowed:
            return Activation(definition=definition, decision=decision)
        try:
            activated = self._activate_allowed(definition)
        except ActivationError as exc:
            return Activation(definition=definition, decision=decision, error=str(exc))
        return Activation(definition=definition, decision=decision, activated=activated)

    def _activate_allowed(
        self, definition: ResourceDefinition
    ) -> InjectedMemory | LoadedSkill | BoundTool | BoundAgent:
        kind = definition.metadata.kind
        if kind == ResourceKind.MEMORY.value:
            return InjectedMemory(definition=definition, content=self._resolve_memory_content(definition))
        if kind == ResourceKind.SKILL.value:
            return LoadedSkill(definition=definition, instructions=self._resolve_skill_instructions(definition))
        if kind == ResourceKind.TOOL.value:
            return self._bind_tool(definition)
        if kind == ResourceKind.AGENT.value:
            return self._bind_agent(definition)
        raise ActivationError(f"{definition.identity}: unsupported resource kind {kind!r}")

    def _resolve_memory_content(self, definition: ResourceDefinition) -> str:
        content = definition.extras.get("content")
        if isinstance(content, str) and content.strip():
            return content
        if isinstance(content, list) and all(isinstance(item, str) for item in content):
            return "\n".join(content)
        ref = definition.metadata.ref
        if ref.startswith("file:"):
            return _read_ref_file(definition, ref[len("file:"):])
        raise ActivationError(
            f"{definition.identity}: cannot resolve memory content; "
            'add a "content" field to the definition or use a file: ref'
        )

    def _resolve_skill_instructions(self, definition: ResourceDefinition) -> str:
        instructions = definition.extras.get("instructions")
        if isinstance(instructions, str) and instructions.strip():
            return instructions
        if isinstance(instructions, list) and all(isinstance(item, str) for item in instructions):
            return "\n".join(instructions)
        content = definition.extras.get("content")
        if isinstance(content, str) and content.strip():
            return content
        ref = definition.metadata.ref
        if ref.startswith("file:"):
            return _read_ref_file(definition, ref[len("file:"):])
        return definition.metadata.description

    def _bind_tool(self, definition: ResourceDefinition) -> BoundTool:
        metadata = definition.metadata
        handler = self.tool_implementations.get(metadata.id)
        if handler is None:
            handler = _resolve_python_ref(definition)
        if handler is None:
            raise ActivationError(
                f"{definition.identity}: no executable implementation; register one with "
                f'tool_implementations={{"{metadata.id}": callable}} or use a python:module:function ref'
            )
        input_schema = definition.extras.get("input_schema")
        output_schema = definition.extras.get("output_schema")
        return BoundTool(
            definition=definition,
            input_schema=dict(input_schema) if isinstance(input_schema, Mapping) else {},
            output_schema=dict(output_schema) if isinstance(output_schema, Mapping) else {},
            handler=handler,
        )

    def _bind_agent(self, definition: ResourceDefinition) -> BoundAgent:
        metadata = definition.metadata
        card = definition.extras.get("agent_card")
        card = card if isinstance(card, Mapping) else {}
        interface = card.get("delegation_interface", definition.extras.get("delegation_interface", "tool_wrap"))
        if interface != "tool_wrap":
            raise ActivationError(
                f"{definition.identity}: delegation_interface {interface!r} is not available in v2; "
                "use 'tool_wrap' (structured_task is planned for v3)"
            )
        handler = self.agent_implementations.get(metadata.id)
        if handler is None:
            handler = _resolve_python_ref(definition)
        if handler is None:
            raise ActivationError(
                f"{definition.identity}: no executable implementation; register one with "
                f'agent_implementations={{"{metadata.id}": callable}} or use a python:module:function ref'
            )
        input_schema = card.get("input_schema", definition.extras.get("input_schema"))
        output_schema = card.get("output_schema", definition.extras.get("output_schema"))
        if not isinstance(input_schema, Mapping):
            input_schema = {
                "type": "object",
                "required": ["goal"],
                "properties": {"goal": {"type": "string"}},
                "additionalProperties": False,
            }
        return BoundAgent(
            definition=definition,
            input_schema=dict(input_schema),
            output_schema=dict(output_schema) if isinstance(output_schema, Mapping) else {},
            handler=handler,
            delegation_interface=str(interface),
        )


def _resolve_python_ref(definition: ResourceDefinition) -> Callable[..., Any] | None:
    ref = definition.metadata.ref
    if not ref.startswith("python:"):
        return None
    target = ref[len("python:"):]
    if ":" not in target:
        raise ActivationError(
            f"{definition.identity}: python ref must be python:module.path:function, got {ref!r}"
        )
    module_name, _, attribute = target.rpartition(":")
    try:
        module = importlib.import_module(module_name)
    except ImportError as exc:
        raise ActivationError(f"{definition.identity}: cannot import module {module_name!r}: {exc}") from exc
    handler = getattr(module, attribute, None)
    if not callable(handler):
        raise ActivationError(f"{definition.identity}: {target!r} is not a callable")
    return handler


def _read_ref_file(definition: ResourceDefinition, raw_path: str) -> str:
    path = Path(raw_path)
    if not path.is_absolute():
        source = definition.source.split("#", 1)[0]
        base = Path(source).parent if source else Path.cwd()
        path = base / path
    try:
        return path.read_text(encoding="utf-8")
    except OSError as exc:
        raise ActivationError(f"{definition.identity}: cannot read ref file {path}: {exc}") from exc
