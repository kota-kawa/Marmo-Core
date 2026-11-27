"""MCP gateway: serve a Marmo-Core tool catalog to an MCP client over stdio.

``mcp.py`` consumes MCP servers; this module is the other direction. An MCP
client (an agent host with its own model) connects to one gateway instead of
to every tool, and sees two tools whatever the size of the catalog:

- ``search_tools`` routes a goal: the Kernel's candidate pool restricted to
  Tool resources, set selection, the dependency and conflict check, then
  the activation gate.
  It answers ``selected``, ``abstain``, or ``escalate`` and discloses the
  schemas of the tools that passed.
- ``call_tool`` runs one disclosed tool through ``ToolRuntime``, so the
  execution gate, argument validation, the safety rules, and the timeout
  apply to every call.

The client is outside the trust boundary. The policy context is fixed by
whoever starts the gateway and nothing a client sends changes it; a tool the
session has not been shown cannot be called. There is no human on this
channel, so whatever the gates would escalate is refused with the reason. As
in the Kernel, once a tool result has been handed to the client, a
side-effecting call counts as proposed after untrusted content and needs an
approval the gateway cannot collect (ADR 0016).

Only Tool resources are served. A tool that depends on a Memory, Skill, or
Agent is withheld, because the gateway cannot deliver that dependency.
"""

from __future__ import annotations

from dataclasses import replace
from typing import Any, Callable, Mapping, TextIO
import json
import sys
import uuid

from ._version import __version__
from .activator import BoundTool, ResourceActivator
from .audit import AuditLog
from .candidate_pool import CandidatePoolRequest, KindBalancedCandidatePool
from .errors import ResourceNotFoundError, SecretResolutionError, ToolInputError
from .llm import characters_for_tokens
from .mcp import MCP_PROTOCOL_VERSION
from .models import SearchResult
from .policy import PolicyContext, PolicyGateway, PolicyRejectedError
from .registry import ResourceRegistry
from .retriever import LexicalRetriever, Retriever
from .security import PromptInjectionInspector, label_untrusted_content
from .selector import (
    DEFAULT_SET_LIMITS,
    RuleBasedSetSelector,
    SelectionContext,
    SetSelector,
    _enforce_set_constraints,
    _find_reference,
)
from .tool_runtime import ToolRuntime

SEARCH_TOOL = "search_tools"
CALL_TOOL = "call_tool"

_INSTRUCTIONS = (
    f"Call {SEARCH_TOOL} with what you are trying to do. It returns the tools that fit, with their "
    f"input schemas. Then call {CALL_TOOL} with one returned name and its arguments. Tools that "
    f"{SEARCH_TOOL} has not returned in this session cannot be called."
)

_TOOL_SPECS = [
    {
        "name": SEARCH_TOOL,
        "description": (
            "Find the tools for a goal. Returns status selected, abstain (nothing usable fits), or "
            "escalate (an operator must grant permissions first), the usable tools with their input "
            "schemas, and the tools that were withheld with the reason."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {"goal": {"type": "string", "description": "What you are trying to do."}},
            "required": ["goal"],
            "additionalProperties": False,
        },
    },
    {
        "name": CALL_TOOL,
        "description": f"Run one tool returned by {SEARCH_TOOL}, with arguments matching its input schema.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": f"A tool name returned by {SEARCH_TOOL}."},
                "arguments": {"type": "object", "description": "Arguments for that tool."},
            },
            "required": ["name"],
            "additionalProperties": False,
        },
    },
]

_PARSE_ERROR = -32700
_INVALID_REQUEST = -32600
_METHOD_NOT_FOUND = -32601
_INVALID_PARAMS = -32602


class MCPGatewayServer:
    """One MCP session over a tool catalog; see the module docstring.

    ``retriever`` and ``selector`` default to what the Kernel uses
    (``LexicalRetriever``, ``RuleBasedSetSelector``). ``max_tools`` replaces
    the selector's per-search limit on tools. ``gate_aware_selection`` hands
    the selector the policy context, as ``Kernel(gate_aware_selection=True)``
    does. ``max_tool_output_tokens`` caps one tool result (``None`` keeps all).
    """

    def __init__(
        self,
        registry: ResourceRegistry,
        *,
        policy_context: PolicyContext | None = None,
        tool_implementations: Mapping[str, Callable[..., Any]] | None = None,
        gateway: PolicyGateway | None = None,
        retriever: Retriever | None = None,
        selector: SetSelector | None = None,
        audit_log: AuditLog | None = None,
        top_k: int = 8,
        max_tools: int | None = None,
        min_relevance: float = 0.0,
        gate_aware_selection: bool = False,
        timeout_seconds: float = 30.0,
        max_tool_output_tokens: int | None = 8000,
    ) -> None:
        if max_tools is not None and max_tools <= 0:
            raise ValueError("max_tools must be positive or None")
        if max_tool_output_tokens is not None and max_tool_output_tokens <= 0:
            raise ValueError("max_tool_output_tokens must be positive or None")
        self.registry = registry
        self.policy_context = policy_context or PolicyContext()
        self.gateway = gateway or PolicyGateway()
        self.retriever = retriever or LexicalRetriever()
        self.selector = selector or RuleBasedSetSelector()
        self._pool = KindBalancedCandidatePool()
        self.activator = ResourceActivator(self.gateway, tool_implementations=tool_implementations)
        self.tool_runtime = ToolRuntime(self.gateway, timeout_seconds=timeout_seconds)
        self.audit_log = audit_log or AuditLog()
        self.top_k = top_k
        self.max_tools = max_tools
        self.min_relevance = min_relevance
        self.gate_aware_selection = gate_aware_selection
        self.max_tool_output_tokens = max_tool_output_tokens
        self._inspector = PromptInjectionInspector()
        self._trace_id = uuid.uuid4().hex
        self._disclosed: dict[str, BoundTool] = {}
        self._untrusted_sources: list[str] = []
        self._prompt_findings: list[str] = []

    # -- transport ---------------------------------------------------------------

    def serve(self, reader: TextIO | None = None, writer: TextIO | None = None) -> None:
        """Answer newline-delimited JSON-RPC messages until ``reader`` ends."""

        reader = reader or sys.stdin
        writer = writer or sys.stdout
        for line in reader:
            if not line.strip():
                continue
            try:
                message = json.loads(line)
            except json.JSONDecodeError:
                response: dict[str, Any] | None = _error(None, _PARSE_ERROR, "message is not valid JSON")
            else:
                response = self.handle_message(message)
            if response is not None:
                writer.write(json.dumps(response, ensure_ascii=False) + "\n")
                writer.flush()

    def handle_message(self, message: Any) -> dict[str, Any] | None:
        """Answer one decoded JSON-RPC message; ``None`` for a notification."""

        if not isinstance(message, Mapping) or not isinstance(message.get("method"), str):
            request_id = message.get("id") if isinstance(message, Mapping) else None
            if isinstance(message, Mapping) and ("result" in message or "error" in message):
                return None  # a reply to a request this server never sent
            return _error(request_id, _INVALID_REQUEST, "expected a JSON-RPC request object")
        method = message["method"]
        if "id" not in message:
            return None
        request_id = message["id"]
        params = message.get("params")
        params = params if isinstance(params, Mapping) else {}
        if method == "initialize":
            return _result(
                request_id,
                {
                    "protocolVersion": MCP_PROTOCOL_VERSION,
                    "capabilities": {"tools": {}},
                    "serverInfo": {"name": "marmo-core", "version": __version__},
                    "instructions": _INSTRUCTIONS,
                },
            )
        if method == "ping":
            return _result(request_id, {})
        if method == "tools/list":
            return _result(request_id, {"tools": _TOOL_SPECS})
        if method == "tools/call":
            name = params.get("name")
            arguments = params.get("arguments")
            arguments = arguments if isinstance(arguments, Mapping) else {}
            if name == SEARCH_TOOL:
                return _result(request_id, self._search(arguments))
            if name == CALL_TOOL:
                return _result(request_id, self._call(arguments))
            return _error(request_id, _INVALID_PARAMS, f"unknown tool: {name!r}")
        return _error(request_id, _METHOD_NOT_FOUND, f"method not found: {method}")

    # -- the two tools -----------------------------------------------------------

    def _audit(self, kind: str, payload: Mapping[str, Any]) -> None:
        self.audit_log.append(kind, payload, trace_id=self._trace_id)

    def _search(self, arguments: Mapping[str, Any]) -> dict[str, Any]:
        goal = arguments.get("goal")
        if not isinstance(goal, str) or not goal.strip():
            return _tool_text("goal must be a non-empty string", is_error=True)
        context = self.policy_context
        # The Kernel's pool, asked for tools only: a tool the activation gate
        # will not allow keeps a slot only when it is the best match, so the
        # client is told why it is withheld; lower-ranked ones leave their
        # slots to usable tools. Escalation counts as not allowed here, since
        # nobody can approve it during the session.
        limit = self.max_tools or int(
            (getattr(self.selector, "default_limits", None) or DEFAULT_SET_LIMITS).get("tool", 0)
        )
        pool = self._pool.build(
            CandidatePoolRequest(
                goal=goal,
                registry=self.registry,
                retriever=self.retriever,
                granted_permissions=tuple(context.granted_permissions),
                top_k=self.top_k,
                per_kind_limits={"tool": limit},
                min_score=float(getattr(self.selector, "min_score", 0.0) or 0.0),
                is_denied=lambda result: not self.gateway.evaluate(
                    result.resource, context, gate="activation"
                ).allowed,
                min_relevance=self.min_relevance,
            )
        )
        candidates = [result for result in pool if result.resource.metadata.kind == "tool"]
        selection = self.selector.select(
            candidates,
            context=SelectionContext(
                task=goal,
                granted_permissions=tuple(context.granted_permissions),
                per_kind_limits={"tool": self.max_tools} if self.max_tools is not None else {},
                min_relevance=self.min_relevance,
                policy=context if self.gate_aware_selection else None,
            ),
        )
        selection, drops = _enforce_set_constraints(selection, self._dependency_resolver(candidates))
        withheld = [dict(item) for item in drops]
        bound: dict[str, BoundTool] = {}
        if selection.status == "selected":
            for result in selection.results:
                definition = result.resource
                activation = self.activator.activate(definition, context)
                self._audit("policy", activation.decision.to_dict())
                if isinstance(activation.activated, BoundTool) and activation.ok:
                    bound[definition.identity] = activation.activated
                elif activation.decision.escalated:
                    withheld.append(
                        {
                            "resource": definition.identity,
                            "reason": "requires human approval, which this gateway cannot collect: "
                            + activation.decision.reason,
                        }
                    )
                else:
                    withheld.append(
                        {"resource": definition.identity, "reason": activation.error or activation.decision.reason}
                    )
            _withhold_broken_dependents(bound, withheld)
        status = "escalate" if selection.status == "escalate" else "selected" if bound else "abstain"
        self._disclosed.update(bound)
        self._audit(
            "retrieve",
            {
                "task": goal,
                "source": "mcp_gateway",
                "candidates": len(candidates),
                "selection_status": status,
                "selected": list(bound),
                "selection_reason": selection.reason,
                **({"withheld": withheld} if withheld else {}),
            },
        )
        payload: dict[str, Any] = {
            "status": status,
            "reason": selection.reason,
            "tools": [
                {
                    "name": identity,
                    "description": tool.metadata.description,
                    "input_schema": tool.input_schema,
                }
                for identity, tool in bound.items()
            ],
        }
        if withheld:
            payload["withheld"] = withheld
        if selection.status == "escalate":
            granted = set(context.granted_permissions)
            payload["missing_permissions"] = list(selection.missing_permissions) or sorted(
                {
                    permission
                    for result in candidates
                    for permission in result.resource.metadata.required_permissions
                    if permission not in granted
                }
            )
        return _tool_text(json.dumps(payload, ensure_ascii=False))

    def _dependency_resolver(self, pool: list[SearchResult]) -> Callable[[str], SearchResult | str]:
        """Resolve a declared dependency, or say why the gateway cannot deliver it."""

        def resolve(reference: str) -> SearchResult | str:
            found = _find_reference(reference, pool)
            if found is None:
                try:
                    definition = self.registry.get(reference)
                except ResourceNotFoundError as exc:
                    return f"is unavailable: {exc}"
                found = SearchResult(definition, 0.0, ("added as a declared dependency",), {})
            if found.resource.metadata.kind != "tool":
                return f"is a {found.resource.metadata.kind}, and this gateway serves tools only"
            decision = self.gateway.evaluate(found.resource, self.policy_context, gate="activation")
            if not decision.allowed:
                return f"is not allowed at activation: {decision.reason}"
            return found

        return resolve

    def _call(self, arguments: Mapping[str, Any]) -> dict[str, Any]:
        name = arguments.get("name")
        tool = self._disclosed.get(name) if isinstance(name, str) else None
        if tool is None:
            return _tool_text(
                f"no tool named {name!r} has been returned by {SEARCH_TOOL} in this session; "
                f"call {SEARCH_TOOL} first and use a name it returns",
                is_error=True,
            )
        tool_arguments = arguments.get("arguments", {})
        if not isinstance(tool_arguments, Mapping):
            return _tool_text("arguments must be an object", is_error=True)
        identity = tool.metadata.identity
        context = replace(
            self.policy_context,
            untrusted_content_sources=tuple(self._untrusted_sources),
            prompt_injection_findings=tuple(self._prompt_findings),
        )
        try:
            result = self.tool_runtime.execute(tool, tool_arguments, context)
        except PolicyRejectedError as exc:
            if exc.decision is not None:
                self._audit("policy", exc.decision.to_dict())
            if exc.decision is not None and exc.decision.escalated:
                return _tool_text(
                    f"{exc.message}; this needs human approval, which this gateway cannot collect",
                    is_error=True,
                )
            return _tool_text(exc.message, is_error=True)
        except ToolInputError as exc:
            # The resolver's message names the variable backing a secret; that
            # stays in the audit log and out of the client's conversation.
            shown = "a secret reference could not be resolved" if isinstance(exc, SecretResolutionError) else str(exc)
            self._audit("execute", {"tool": identity, "status": "invalid_input", "error": str(exc)})
            return _tool_text(shown, is_error=True)
        self._audit("execute", result.to_dict())
        source = f"tool:{identity}"
        if source not in self._untrusted_sources:
            self._untrusted_sources.append(source)
        findings = self._inspector.inspect(result.output)
        if findings:
            self._prompt_findings.extend(
                finding.code for finding in findings if finding.code not in self._prompt_findings
            )
            self._audit(
                "security",
                {
                    "event": "prompt_injection_detected",
                    "source": source,
                    "trust": "untrusted_content",
                    "findings": [finding.to_dict() for finding in findings],
                },
            )
        budget = self.max_tool_output_tokens
        value = result.output if result.succeeded else {"status": result.status, "error": result.error}
        text = label_untrusted_content(
            value,
            source=source,
            max_characters=None if budget is None else characters_for_tokens(budget),
        )
        return _tool_text(text, is_error=not result.succeeded)


def _withhold_broken_dependents(bound: dict[str, BoundTool], withheld: list[dict[str, str]]) -> None:
    """Withhold tools whose declared dependency did not bind, until none is left.

    The dependency check runs before activation, so a dependency can still
    fail to bind afterwards (no implementation, an approval nobody can give).
    """

    while True:
        delivered = [SearchResult(tool.definition, 0.0, (), {}) for tool in bound.values()]
        broken = next(
            (
                (identity, reference)
                for identity, tool in bound.items()
                for reference in tool.metadata.dependencies
                if _find_reference(reference, delivered) is None
            ),
            None,
        )
        if broken is None:
            return
        identity, reference = broken
        del bound[identity]
        withheld.append({"resource": identity, "reason": f"dependency {reference} was withheld"})


def _tool_text(text: str, *, is_error: bool = False) -> dict[str, Any]:
    return {"content": [{"type": "text", "text": text}], "isError": is_error}


def _result(request_id: Any, result: Mapping[str, Any]) -> dict[str, Any]:
    return {"jsonrpc": "2.0", "id": request_id, "result": dict(result)}


def _error(request_id: Any, code: int, message: str) -> dict[str, Any]:
    return {"jsonrpc": "2.0", "id": request_id, "error": {"code": code, "message": message}}
