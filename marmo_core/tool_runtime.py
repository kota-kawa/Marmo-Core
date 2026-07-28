"""Tool Runtime: guarded execution of bound tools (4.7).

The execution gate is evaluated inside ``execute`` so it cannot be bypassed
(F-GATE-01). Handler code and credentials stay on this side; only the input
schema and results are exposed to the model (F-TOOL-01).

Dry-run stops at the runtime boundary after policy and schema validation: no
handler is submitted, regardless of the resource's declared side effect. This
is deliberately stronger than trusting metadata to say which handlers are
safe (F-GATE-08).

Timeouts use a worker thread; a timed-out handler is abandoned, not killed.
Hard process isolation is Connector / sandbox work (F-SEC-05, v2+).
"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeoutError
from dataclasses import dataclass
from time import perf_counter
from typing import Any, Mapping

from .activator import BoundTool
from .errors import ToolInputError
from .policy import PolicyContext, PolicyGateway, PolicyRejectedError
from .secrets import (
    SecretResolver,
    ensure_secret_refs,
    is_secret_ref,
    redact_secret_values,
    resolve_secret_refs,
    serialize_secret_refs,
)


@dataclass(frozen=True)
class ToolResult:
    """Outcome of one tool execution (F-TOOL-04)."""

    tool_id: str
    tool_version: str
    status: str  # success / dry_run / error / timeout
    arguments: dict[str, Any]
    output: Any = None
    error: str | None = None
    elapsed_ms: float = 0.0
    safety_findings: tuple[dict[str, str], ...] = ()

    @property
    def succeeded(self) -> bool:
        """Whether the requested step completed without needing recovery."""

        return self.status in ("success", "dry_run")

    @property
    def executed(self) -> bool:
        """Whether the handler actually ran (false for validated dry-runs)."""

        return self.status == "success"

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "ToolResult":
        """Rebuild a result recorded in the State Store (F-STATE-01)."""

        arguments = data.get("arguments")
        error = data.get("error")
        safety_findings = data.get("safety_findings")
        safety_findings = safety_findings if isinstance(safety_findings, (list, tuple)) else ()
        return cls(
            tool_id=str(data.get("tool_id", "")),
            tool_version=str(data.get("tool_version", "")),
            status=str(data.get("status", "")),
            arguments=dict(arguments) if isinstance(arguments, Mapping) else {},
            output=data.get("output"),
            error=str(error) if error is not None else None,
            elapsed_ms=float(data.get("elapsed_ms", 0.0)),
            safety_findings=tuple(dict(item) for item in safety_findings if isinstance(item, Mapping)),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "tool_id": self.tool_id,
            "tool_version": self.tool_version,
            "status": self.status,
            "arguments": self.arguments,
            "output": self.output,
            "error": self.error,
            "elapsed_ms": round(self.elapsed_ms, 3),
            "safety_findings": [dict(item) for item in self.safety_findings],
        }


class ToolRuntime:
    """Execute bound tools with gate check, schema validation, and timeout."""

    def __init__(
        self,
        gateway: PolicyGateway | None = None,
        *,
        timeout_seconds: float = 30.0,
        secret_resolver: SecretResolver | None = None,
    ) -> None:
        if timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be positive")
        self.gateway = gateway or PolicyGateway()
        self.timeout_seconds = timeout_seconds
        self.secret_resolver = secret_resolver

    def execute(
        self,
        tool: BoundTool,
        arguments: Mapping[str, Any],
        context: PolicyContext | None = None,
    ) -> ToolResult:
        stored_arguments = serialize_secret_refs(dict(arguments))
        ensure_secret_refs(stored_arguments)
        preflight = self.gateway.evaluate(tool.definition, context, gate="execution")
        if not preflight.allowed:
            raise PolicyRejectedError(
                f"execution gate returned {preflight.verdict} for {tool.metadata.identity}: {preflight.reason}",
                preflight,
            )
        resolved_arguments, secret_values = resolve_secret_refs(stored_arguments, self.secret_resolver)
        decision = self.gateway.evaluate(
            tool.definition, context, gate="execution", arguments=resolved_arguments
        )
        if not decision.allowed:
            raise PolicyRejectedError(
                f"execution gate returned {decision.verdict} for {tool.metadata.identity}: {decision.reason}",
                decision,
            )
        issues = validate_arguments(tool.input_schema, resolved_arguments)
        if issues:
            raise ToolInputError(
                f"invalid input for {tool.metadata.identity}: "
                + "; ".join(issues)
                + "; fix the arguments to match the tool input_schema"
            )
        metadata = tool.metadata
        if context is not None and context.dry_run:
            return ToolResult(
                tool_id=metadata.id,
                tool_version=metadata.version,
                status="dry_run",
                arguments=stored_arguments,
                output={
                    "dry_run": True,
                    "executed": False,
                    "resource": metadata.identity,
                    "side_effect": metadata.side_effect,
                },
                safety_findings=decision.risk_findings,
            )
        start = perf_counter()
        executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix=f"marmo-tool-{metadata.id}")
        try:
            future = executor.submit(tool.handler, **resolved_arguments)
            try:
                output = future.result(timeout=self.timeout_seconds)
            except FutureTimeoutError:
                return ToolResult(
                    tool_id=metadata.id,
                    tool_version=metadata.version,
                    status="timeout",
                    arguments=stored_arguments,
                    error=f"tool did not finish within {self.timeout_seconds:g}s; "
                    "raise timeout_seconds or make the tool faster",
                    elapsed_ms=(perf_counter() - start) * 1000,
                    safety_findings=decision.risk_findings,
                )
            except Exception as exc:  # noqa: BLE001 - tool failures become data, not crashes
                return ToolResult(
                    tool_id=metadata.id,
                    tool_version=metadata.version,
                    status="error",
                    arguments=stored_arguments,
                    error=redact_secret_values(f"{type(exc).__name__}: {exc}", secret_values),
                    elapsed_ms=(perf_counter() - start) * 1000,
                    safety_findings=decision.risk_findings,
                )
        finally:
            executor.shutdown(wait=False)
        return ToolResult(
            tool_id=metadata.id,
            tool_version=metadata.version,
            status="success",
            arguments=stored_arguments,
            output=redact_secret_values(output, secret_values),
            elapsed_ms=(perf_counter() - start) * 1000,
            safety_findings=decision.risk_findings,
        )


def validate_arguments(schema: Mapping[str, Any], arguments: Mapping[str, Any]) -> list[str]:
    """Validate arguments against the lightweight JSON Schema subset (F-TOOL-02).

    Supported keywords: type, required, properties, enum, minimum, maximum,
    additionalProperties (boolean form).
    """

    issues: list[str] = []
    if not isinstance(schema, Mapping) or not schema:
        return issues
    properties = schema.get("properties")
    properties = properties if isinstance(properties, Mapping) else {}
    required = schema.get("required")
    required = required if isinstance(required, list) else []
    for name in required:
        if name not in arguments:
            issues.append(f"missing required argument: {name}")
    if schema.get("additionalProperties") is False:
        for name in arguments:
            if name not in properties:
                issues.append(f"unknown argument: {name}")
    for name, value in arguments.items():
        prop = properties.get(name)
        if not isinstance(prop, Mapping):
            continue
        # A reference is validated again after ToolRuntime materializes it.
        # Accepting it here lets Planner/Recovery reason about deferred values.
        if is_secret_ref(value):
            continue
        expected = prop.get("type")
        if isinstance(expected, str) and not _matches_type(value, expected):
            issues.append(f"argument {name} must be of type {expected}")
            continue
        enum = prop.get("enum")
        if isinstance(enum, list) and value not in enum:
            issues.append(f"argument {name} must be one of: {enum}")
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            minimum = prop.get("minimum")
            if isinstance(minimum, (int, float)) and value < minimum:
                issues.append(f"argument {name} must be >= {minimum}")
            maximum = prop.get("maximum")
            if isinstance(maximum, (int, float)) and value > maximum:
                issues.append(f"argument {name} must be <= {maximum}")
    return issues


def _matches_type(value: Any, expected: str) -> bool:
    if expected == "string":
        return isinstance(value, str)
    if expected == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if expected == "number":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    if expected == "boolean":
        return isinstance(value, bool)
    if expected == "array":
        return isinstance(value, list)
    if expected == "object":
        return isinstance(value, Mapping)
    if expected == "null":
        return value is None
    return True
