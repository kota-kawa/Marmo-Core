"""Recovery Manager: classify failures and decide what to do next (4.10).

The manager itself is pure policy -- it classifies a failure (F-RECOV-01)
and returns a decision (F-RECOV-02/03/06/07). Carrying that decision out is
the kernel's job, because only the kernel holds the activated resources, the
policy gates, and the state. Keeping the split means the decision table is
testable without running tools.

Retries are bounded by attempt count *and* by a circuit breaker on
consecutive failures, so a resource that fails every time cannot spin
(F-RECOV-07). Backoff is exponential with jitter; the clock and the random
source are injectable so tests stay fast and deterministic.

Compensation (F-RECOV-05) is declared on the resource itself via the
``compensated_by`` extra, naming a tool that undoes it. The kernel runs those
in reverse order when a task fails past recovery -- through the normal gates,
so an undo is never a privilege escape.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Mapping, Sequence
import random
import threading
import time

from .models import ResourceDefinition, ResourceMetadata


FAILURE_KINDS = (
    "transient",
    "permanent",
    "timeout",
    "permission_denied",
    "validation",
    "activation",
    "delegation",
)

RECOVERY_ACTIONS = ("retry", "fallback", "escalate", "fail")

#: Error type names treated as worth retrying. Matched against the leading
#: ``TypeName:`` that ToolRuntime puts in ``ToolResult.error``.
DEFAULT_TRANSIENT_ERRORS = (
    "BrokenPipeError",
    "ConnectionAbortedError",
    "ConnectionError",
    "ConnectionResetError",
    "HTTPError",
    "IOError",
    "OSError",
    "TimeoutError",
    "URLError",
)


@dataclass(frozen=True)
class Failure:
    """One classified failure (F-RECOV-01)."""

    kind: str
    message: str
    resource: str = ""
    stage: str = ""  # activation / execution / delegation
    detail: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.kind not in FAILURE_KINDS:
            raise ValueError(f"kind must be one of: {', '.join(FAILURE_KINDS)}")

    def to_dict(self) -> dict[str, Any]:
        return {
            "kind": self.kind,
            "message": self.message,
            "resource": self.resource,
            "stage": self.stage,
            "detail": dict(self.detail),
        }


@dataclass(frozen=True)
class RecoveryDecision:
    """What the kernel should do about a failure."""

    action: str
    reason: str
    failure: Failure
    backoff_seconds: float = 0.0
    alternative: str = ""

    def __post_init__(self) -> None:
        if self.action not in RECOVERY_ACTIONS:
            raise ValueError(f"action must be one of: {', '.join(RECOVERY_ACTIONS)}")

    def to_dict(self) -> dict[str, Any]:
        return {
            "action": self.action,
            "reason": self.reason,
            "failure": self.failure.to_dict(),
            "backoff_seconds": round(self.backoff_seconds, 4),
            "alternative": self.alternative,
        }


@dataclass(frozen=True)
class RetryPolicy:
    """Attempt limit and exponential backoff with jitter (F-RECOV-02)."""

    max_attempts: int = 3
    initial_backoff_seconds: float = 0.1
    multiplier: float = 2.0
    max_backoff_seconds: float = 5.0
    jitter: float = 0.1
    retry_kinds: tuple[str, ...] = ("transient", "timeout")

    def __post_init__(self) -> None:
        if self.max_attempts < 1:
            raise ValueError("max_attempts must be at least 1")
        if self.initial_backoff_seconds < 0 or self.max_backoff_seconds < 0:
            raise ValueError("backoff seconds must be non-negative")
        if not 0.0 <= self.jitter <= 1.0:
            raise ValueError("jitter must be between 0.0 and 1.0")
        unknown = set(self.retry_kinds) - set(FAILURE_KINDS)
        if unknown:
            raise ValueError(f"unknown retry kind: {', '.join(sorted(unknown))}")

    def allows(self, failure: Failure, attempts: int) -> bool:
        """True when ``failure`` is retryable and attempts remain."""

        return failure.kind in self.retry_kinds and attempts + 1 < self.max_attempts

    def backoff_for(self, attempts: int, rng: random.Random) -> float:
        base = min(
            self.initial_backoff_seconds * (self.multiplier**attempts),
            self.max_backoff_seconds,
        )
        if not self.jitter:
            return base
        return base * (1.0 + rng.uniform(-self.jitter, self.jitter))


class CircuitBreaker:
    """Stop a resource that keeps failing in a row (F-RECOV-07)."""

    def __init__(self, failure_threshold: int = 3) -> None:
        if failure_threshold < 1:
            raise ValueError("failure_threshold must be at least 1")
        self.failure_threshold = failure_threshold
        self._consecutive: dict[str, int] = {}
        # Parallel plan steps can fail at the same time (F-PLAN-05).
        self._lock = threading.Lock()

    def record_failure(self, resource: str) -> int:
        with self._lock:
            count = self._consecutive.get(resource, 0) + 1
            self._consecutive[resource] = count
            return count

    def record_success(self, resource: str) -> None:
        with self._lock:
            self._consecutive.pop(resource, None)

    def is_open(self, resource: str) -> bool:
        """True when ``resource`` has tripped the breaker and must be left alone."""

        return self._consecutive.get(resource, 0) >= self.failure_threshold

    def reset(self, resource: str | None = None) -> None:
        if resource is None:
            self._consecutive.clear()
        else:
            self._consecutive.pop(resource, None)


class RecoveryManager:
    """Decide how to respond to a failure. Swappable like the other engines (5.4)."""

    def __init__(
        self,
        *,
        retry_policy: RetryPolicy | None = None,
        circuit_breaker: CircuitBreaker | None = None,
        transient_errors: Sequence[str] = DEFAULT_TRANSIENT_ERRORS,
        escalate_when_exhausted: bool = True,
        sleep: Callable[[float], None] = time.sleep,
        rng: random.Random | None = None,
    ) -> None:
        self.retry_policy = retry_policy or RetryPolicy()
        self.circuit_breaker = circuit_breaker or CircuitBreaker()
        self.transient_errors = tuple(transient_errors)
        self.escalate_when_exhausted = escalate_when_exhausted
        self._sleep = sleep
        self._rng = rng or random.Random(0)

    # -- classification (F-RECOV-01) ----------------------------------------

    def classify_tool_result(self, result: Any, metadata: ResourceMetadata) -> Failure:
        """Classify a non-successful ``ToolResult``."""

        if result.status == "timeout":
            return Failure(
                kind="timeout",
                message=result.error or "tool timed out",
                resource=metadata.identity,
                stage="execution",
            )
        error = result.error or "tool failed"
        kind = "transient" if self._looks_transient(error) else "permanent"
        return Failure(kind=kind, message=error, resource=metadata.identity, stage="execution")

    def classify_agent_result(self, result: Any, metadata: ResourceMetadata) -> Failure:
        """Classify a failed delegation and preserve timeout retry behavior."""

        if result.status == "timeout":
            return Failure(
                kind="timeout",
                message=result.error or "agent delegation timed out",
                resource=metadata.identity,
                stage="delegation",
            )
        error = result.error or "agent delegation failed"
        kind = "transient" if self._looks_transient(error) else "delegation"
        return Failure(kind=kind, message=error, resource=metadata.identity, stage="delegation")

    def classify_activation(self, definition: ResourceDefinition, error: str) -> Failure:
        """Classify an activation failure so it lands in the audit too (F-ACT-05)."""

        return Failure(
            kind="activation",
            message=error,
            resource=definition.identity,
            stage="activation",
        )

    def classify_denial(self, metadata: ResourceMetadata, reason: str) -> Failure:
        return Failure(
            kind="permission_denied",
            message=reason,
            resource=metadata.identity,
            stage="execution",
        )

    def classify_validation(self, metadata: ResourceMetadata, reason: str) -> Failure:
        return Failure(kind="validation", message=reason, resource=metadata.identity, stage="execution")

    def _looks_transient(self, error: str) -> bool:
        name = error.split(":", 1)[0].strip()
        return name in self.transient_errors

    # -- decision -----------------------------------------------------------

    def decide(
        self,
        failure: Failure,
        *,
        attempts: int = 0,
        alternatives: Sequence[str] = (),
    ) -> RecoveryDecision:
        """Choose retry / fallback / escalate / fail for ``failure``.

        ``attempts`` counts executions already made for this step, so the
        first failure arrives with ``attempts=0``.
        """

        if self.circuit_breaker.is_open(failure.resource):
            return RecoveryDecision(
                action="fail",
                reason=(
                    f"circuit breaker open for {failure.resource} after "
                    f"{self.circuit_breaker.failure_threshold} consecutive failures; "
                    "fix the resource or route around it"
                ),
                failure=failure,
            )
        if failure.kind == "permission_denied":
            return RecoveryDecision(
                action="escalate",
                reason="a human can grant the missing permissions",
                failure=failure,
            )
        if failure.kind == "validation":
            # Re-running identical bad arguments cannot help, and no other
            # tool would accept them either.
            return RecoveryDecision(
                action="fail",
                reason="the arguments do not satisfy the tool input schema; retrying cannot fix that",
                failure=failure,
            )
        if self.retry_policy.allows(failure, attempts):
            return RecoveryDecision(
                action="retry",
                reason=f"{failure.kind} failure, attempt {attempts + 2} of {self.retry_policy.max_attempts}",
                failure=failure,
                backoff_seconds=self.retry_policy.backoff_for(attempts, self._rng),
            )
        if alternatives:
            return RecoveryDecision(
                action="fallback",
                reason=f"retries exhausted; falling back to {alternatives[0]}",
                failure=failure,
                alternative=alternatives[0],
            )
        if self.escalate_when_exhausted:
            return RecoveryDecision(
                action="escalate",
                reason="no retries or alternatives remain; a human can decide whether to continue",
                failure=failure,
            )
        return RecoveryDecision(action="fail", reason="no recovery route remains", failure=failure)

    def wait(self, seconds: float) -> None:
        if seconds > 0:
            self._sleep(seconds)


def compensation_for(definition: ResourceDefinition) -> str:
    """Return the tool id that undoes ``definition``, if it declares one.

    Declared as a ``compensated_by`` extra on the resource. The undo tool is
    called with the same arguments as the original step (F-RECOV-05).
    """

    value = definition.extras.get("compensated_by")
    return value.strip() if isinstance(value, str) and value.strip() else ""


def needs_compensation(metadata: ResourceMetadata) -> bool:
    """True when a completed step left a side effect worth undoing."""

    return metadata.side_effect in ("write", "external", "irreversible")
