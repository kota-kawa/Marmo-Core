"""Synchronous, guarded Agent delegation (F-AGENT-01/04/06, F-SEC-08).

The v2 interface deliberately treats an Agent as a wrapped tool.  The actual
call therefore passes through ``ToolRuntime`` and inherits its mandatory
policy gates, argument validation, secret handling, dry-run, and timeout.
This module adds the Agent-specific invariants around that boundary: delegated
permissions can only shrink, delegation depth is bounded, and estimated total
cost is checked before work begins.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Any, Mapping, Sequence

from .activator import BoundAgent, BoundTool
from .errors import ToolInputError
from .policy import PolicyContext
from .tool_runtime import ToolResult, ToolRuntime


@dataclass(frozen=True)
class AgentResponse:
    """Optional handler return envelope for reporting actual delegation cost."""

    output: Any
    cost: float = 0.0


@dataclass(frozen=True)
class AgentResult:
    """Serializable outcome of one Agent delegation (F-AGENT-04)."""

    agent_id: str
    agent_version: str
    status: str
    arguments: dict[str, Any]
    output: Any = None
    error: str | None = None
    elapsed_ms: float = 0.0
    cost: float = 0.0
    delegation_depth: int = 1
    delegated_permissions: tuple[str, ...] = ()
    safety_findings: tuple[dict[str, str], ...] = ()

    @property
    def succeeded(self) -> bool:
        return self.status in ("success", "dry_run")

    @property
    def executed(self) -> bool:
        return self.status == "success"

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "AgentResult":
        arguments = data.get("arguments")
        permissions = data.get("delegated_permissions")
        findings = data.get("safety_findings")
        permissions = permissions if isinstance(permissions, (list, tuple)) else ()
        findings = findings if isinstance(findings, (list, tuple)) else ()
        error = data.get("error")
        return cls(
            agent_id=str(data.get("agent_id", "")),
            agent_version=str(data.get("agent_version", "")),
            status=str(data.get("status", "")),
            arguments=dict(arguments) if isinstance(arguments, Mapping) else {},
            output=data.get("output"),
            error=str(error) if error is not None else None,
            elapsed_ms=float(data.get("elapsed_ms", 0.0)),
            cost=float(data.get("cost", 0.0)),
            delegation_depth=int(data.get("delegation_depth", 1)),
            delegated_permissions=tuple(str(item) for item in permissions),
            safety_findings=tuple(dict(item) for item in findings if isinstance(item, Mapping)),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "agent_id": self.agent_id,
            "agent_version": self.agent_version,
            "status": self.status,
            "arguments": self.arguments,
            "output": self.output,
            "error": self.error,
            "elapsed_ms": round(self.elapsed_ms, 3),
            "cost": self.cost,
            "delegation_depth": self.delegation_depth,
            "delegated_permissions": list(self.delegated_permissions),
            "safety_findings": [dict(item) for item in self.safety_findings],
        }


class AgentRuntime:
    """Execute a tool-wrapped Agent while enforcing delegation limits."""

    def __init__(
        self,
        tool_runtime: ToolRuntime,
        *,
        max_depth: int = 1,
        max_total_cost: float | None = None,
    ) -> None:
        if max_depth < 1:
            raise ValueError("max_depth must be at least 1")
        if max_total_cost is not None and max_total_cost < 0:
            raise ValueError("max_total_cost must be non-negative or None")
        self.tool_runtime = tool_runtime
        self.max_depth = max_depth
        self.max_total_cost = max_total_cost

    def execute(
        self,
        agent: BoundAgent,
        arguments: Mapping[str, Any],
        context: PolicyContext | None = None,
        *,
        depth: int = 1,
        cumulative_cost: float = 0.0,
        delegated_permissions: Sequence[str] | None = None,
    ) -> AgentResult:
        if agent.delegation_interface != "tool_wrap":
            raise ToolInputError(
                f"{agent.metadata.identity}: only delegation_interface='tool_wrap' is supported in v2"
            )
        if depth < 1 or depth > self.max_depth:
            raise ToolInputError(
                f"delegation depth {depth} exceeds max_depth={self.max_depth}; "
                "flatten the delegation chain or raise the explicit limit"
            )
        parent_permissions = set(context.granted_permissions if context else ())
        requested_permissions = tuple(
            dict.fromkeys(delegated_permissions or agent.metadata.required_permissions)
        )
        excess = set(requested_permissions) - parent_permissions
        if excess:
            raise ToolInputError(
                f"delegated permissions must be a subset of the delegator's permissions; "
                f"not granted: {', '.join(sorted(excess))}"
            )
        estimate = agent.metadata.cost_estimate
        if self.max_total_cost is not None and cumulative_cost + estimate > self.max_total_cost:
            raise ToolInputError(
                f"agent cost estimate would exceed max_total_cost={self.max_total_cost:g}: "
                f"{cumulative_cost:g} + {estimate:g}"
            )

        # ToolRuntime owns the mandatory execution boundary. The wrapper only
        # unwraps AgentResponse so arbitrary handler objects never reach state.
        def wrapped(**kwargs: Any) -> Any:
            value = agent.handler(**kwargs)
            if isinstance(value, AgentResponse):
                if (
                    not isinstance(value.cost, (int, float))
                    or isinstance(value.cost, bool)
                    or value.cost < 0
                ):
                    raise ValueError("AgentResponse.cost must be a non-negative number")
                return {
                    "__marmo_agent_response__": True,
                    "output": value.output,
                    "cost": value.cost,
                }
            return value

        wrapped_tool = BoundTool(
            definition=agent.definition,
            input_schema=agent.input_schema,
            output_schema=agent.output_schema,
            handler=wrapped,
        )
        delegated_context = replace(context, granted_permissions=requested_permissions) if context else None
        result = self.tool_runtime.execute(wrapped_tool, arguments, delegated_context)
        output = result.output
        actual_cost = 0.0 if result.status == "dry_run" else estimate
        if isinstance(output, Mapping) and output.get("__marmo_agent_response__") is True:
            actual_cost = float(output.get("cost", estimate))
            output = output.get("output")
        return _agent_result(
            result,
            output=output,
            cost=actual_cost,
            depth=depth,
            delegated_permissions=requested_permissions,
        )


def _agent_result(
    result: ToolResult,
    *,
    output: Any,
    cost: float,
    depth: int,
    delegated_permissions: tuple[str, ...],
) -> AgentResult:
    return AgentResult(
        agent_id=result.tool_id,
        agent_version=result.tool_version,
        status=result.status,
        arguments=result.arguments,
        output=output,
        error=result.error,
        elapsed_ms=result.elapsed_ms,
        cost=cost,
        delegation_depth=depth,
        delegated_permissions=delegated_permissions,
        safety_findings=result.safety_findings,
    )
