"""Guarded Agent delegation and pluggable execution backends."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, replace
import math
from typing import Any, Mapping, Sequence

from .activator import BoundAgent, BoundTool
from .errors import MarmoError, ToolInputError
from .hitl import HitlRequest
from .policy import PolicyContext, PolicyRejectedError
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
    child_task_id: str = ""

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
            child_task_id=str(data.get("child_task_id", "")),
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
            "child_task_id": self.child_task_id,
        }


class AgentExecutionBackend(ABC):
    """Pluggable execution strategy for one activated Agent resource."""

    @abstractmethod
    def execute(
        self,
        agent: BoundAgent,
        arguments: Mapping[str, Any],
        context: PolicyContext | None,
        *,
        depth: int,
        cumulative_cost: float,
        delegated_permissions: tuple[str, ...],
        task_id: str,
        invocation_id: str,
    ) -> AgentResult:
        """Run the Agent within the supplied task and delegation boundary."""


class AgentExecutionPendingError(MarmoError):
    """A nested Agent task is paused for a parent task's human approval."""

    def __init__(
        self,
        child_task_id: str,
        request: HitlRequest,
        *,
        tool_results: Sequence[ToolResult] = (),
    ) -> None:
        super().__init__(f"delegated task {child_task_id} is waiting for human approval")
        self.child_task_id = child_task_id
        self.request = request
        self.tool_results = tuple(tool_results)


class ToolWrappedAgentBackend(AgentExecutionBackend):
    """Run a local Agent handler through the guarded ToolRuntime boundary."""

    def __init__(self, tool_runtime: ToolRuntime) -> None:
        self.tool_runtime = tool_runtime

    def execute(
        self,
        agent: BoundAgent,
        arguments: Mapping[str, Any],
        context: PolicyContext | None,
        *,
        depth: int,
        cumulative_cost: float,
        delegated_permissions: tuple[str, ...],
        task_id: str = "",
        invocation_id: str = "",
    ) -> AgentResult:
        if agent.handler is None:
            raise ToolInputError(f"{agent.metadata.identity}: tool_wrap Agent has no handler")
        handler = agent.handler

        def wrapped(**kwargs: Any) -> Any:
            value = handler(**kwargs)
            if isinstance(value, AgentResponse):
                if (
                    not isinstance(value.cost, (int, float))
                    or isinstance(value.cost, bool)
                    or not math.isfinite(value.cost)
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
            handler=(agent.handler if self.tool_runtime.timeout_mode == "process" else wrapped),
        )
        delegated_context = replace(context, granted_permissions=delegated_permissions) if context else None
        result = self.tool_runtime.execute(wrapped_tool, arguments, delegated_context)
        output = result.output
        actual_cost = 0.0 if result.status == "dry_run" else agent.metadata.cost_estimate
        if isinstance(output, Mapping) and output.get("__marmo_agent_response__") is True:
            actual_cost = float(output.get("cost", agent.metadata.cost_estimate))
            output = output.get("output")
        return _agent_result(
            result,
            output=output,
            cost=actual_cost,
            depth=depth,
            delegated_permissions=delegated_permissions,
        )


class AgentRuntime:
    """Dispatch activated Agents through a registered guarded backend."""

    def __init__(
        self,
        tool_runtime: ToolRuntime,
        *,
        max_depth: int = 1,
        max_total_cost: float | None = None,
        backends: Mapping[str, AgentExecutionBackend] | None = None,
    ) -> None:
        if max_depth < 1:
            raise ValueError("max_depth must be at least 1")
        if max_total_cost is not None and (
            not math.isfinite(max_total_cost) or max_total_cost < 0
        ):
            raise ValueError("max_total_cost must be non-negative or None")
        self.tool_runtime = tool_runtime
        self.max_depth = max_depth
        self.max_total_cost = max_total_cost
        self.backends: dict[str, AgentExecutionBackend] = {"tool_wrap": ToolWrappedAgentBackend(tool_runtime)}
        for interface, backend in (backends or {}).items():
            self.register_backend(interface, backend)

    def register_backend(self, delegation_interface: str, backend: AgentExecutionBackend) -> None:
        if not delegation_interface:
            raise ValueError("delegation_interface must not be empty")
        if not isinstance(backend, AgentExecutionBackend):
            raise TypeError("backend must implement AgentExecutionBackend")
        self.backends[delegation_interface] = backend

    def execute(
        self,
        agent: BoundAgent,
        arguments: Mapping[str, Any],
        context: PolicyContext | None = None,
        *,
        depth: int = 1,
        cumulative_cost: float = 0.0,
        delegated_permissions: Sequence[str] | None = None,
        task_id: str = "",
        invocation_id: str = "",
    ) -> AgentResult:
        if depth < 1 or depth > self.max_depth:
            raise ToolInputError(
                f"delegation depth {depth} exceeds max_depth={self.max_depth}; "
                "flatten the delegation chain or raise the explicit limit"
            )
        parent_permissions = set(context.granted_permissions if context else ())
        requested_permissions = tuple(dict.fromkeys(
            agent.metadata.required_permissions if delegated_permissions is None else delegated_permissions
        ))
        excess = set(requested_permissions) - parent_permissions
        if excess:
            raise ToolInputError(
                f"delegated permissions must be a subset of the delegator's permissions; "
                f"not granted: {', '.join(sorted(excess))}"
            )
        if not math.isfinite(cumulative_cost) or cumulative_cost < 0:
            raise ToolInputError("cumulative agent cost must be finite and non-negative")
        estimate = agent.metadata.cost_estimate
        if self.max_total_cost is not None and cumulative_cost + estimate > self.max_total_cost:
            raise ToolInputError(
                f"agent cost estimate would exceed max_total_cost={self.max_total_cost:g}: "
                f"{cumulative_cost:g} + {estimate:g}"
            )

        delegated_context = (
            replace(context, granted_permissions=requested_permissions) if context is not None else None
        )
        decision = self.tool_runtime.gateway.evaluate(
            agent.definition,
            delegated_context,
            gate="execution",
            arguments=arguments,
        )
        if not decision.allowed:
            raise PolicyRejectedError(
                f"execution gate returned {decision.verdict} for {agent.metadata.identity}: {decision.reason}",
                decision,
            )

        backend = self.backends.get(agent.delegation_interface)
        if backend is None:
            raise ToolInputError(
                f"{agent.metadata.identity}: no AgentExecutionBackend is registered for "
                f"delegation_interface={agent.delegation_interface!r}"
            )
        result = backend.execute(
            agent,
            arguments,
            delegated_context,
            depth=depth,
            cumulative_cost=cumulative_cost,
            delegated_permissions=requested_permissions,
            task_id=task_id,
            invocation_id=invocation_id,
        )
        if not isinstance(result, AgentResult):
            raise ToolInputError(
                f"AgentExecutionBackend for {agent.delegation_interface!r} must return AgentResult"
            )
        if result.agent_id != agent.metadata.id or result.agent_version != agent.metadata.version:
            raise ToolInputError("AgentExecutionBackend returned a result for a different Agent")
        if result.delegation_depth != depth:
            raise ToolInputError("AgentExecutionBackend returned an incorrect delegation depth")
        if set(result.delegated_permissions) - set(requested_permissions):
            raise ToolInputError("AgentExecutionBackend reported permissions outside its delegation")
        if not math.isfinite(result.cost) or result.cost < 0:
            raise ToolInputError("AgentExecutionBackend returned a non-finite or negative cost")
        return result


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
