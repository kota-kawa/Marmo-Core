"""Human-in-the-loop Broker: escalation requests and human responses (4.12).

The kernel raises an escalation, this module turns it into a request a person
can act on (F-HITL-01/02) and carries the answer back. Channels are pluggable
(F-HITL-05): the default never answers on its own, so the task simply stays
paused until an operator supplies a response out of band -- the shape an API
or webhook integration wants. ``ConsoleHitlBroker`` is the CLI channel and
``CallbackHitlBroker`` adapts any callable.

Waiting is bounded: a channel that does not answer within ``timeout_seconds``
falls back to the configured ``on_timeout`` behaviour (F-HITL-06). Who may
approve, and which operations always require a human even when the Policy
Gateway would allow them, is configured on ``HitlPolicy`` (F-HITL-07).
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeoutError
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable, Mapping
import uuid

from .errors import MarmoError
from .models import ResourceMetadata


HITL_STAGES = ("selection", "activation", "execution")
HITL_RESPONSE_KINDS = ("approve", "reject", "modify", "defer")
TIMEOUT_ACTIONS = ("deny", "pending")


class HitlError(MarmoError):
    """Raised when a human response is malformed or unauthorized."""


@dataclass(frozen=True)
class HitlRequest:
    """A confirmation a person is being asked for (F-HITL-02).

    Carries the operation under review, its expected impact, the alternatives
    open to the operator, and the broker's recommended verdict.
    """

    request_id: str
    task_id: str
    stage: str
    operation: str
    impact: str
    alternatives: tuple[str, ...] = ()
    recommendation: str = "reject"
    resource: str = ""
    arguments: dict[str, Any] | None = None
    decision: dict[str, Any] | None = None
    created_at: str = ""

    @classmethod
    def create(
        cls,
        *,
        task_id: str,
        stage: str,
        operation: str,
        impact: str,
        alternatives: tuple[str, ...] = (),
        recommendation: str = "reject",
        resource: str = "",
        arguments: Mapping[str, Any] | None = None,
        decision: Mapping[str, Any] | None = None,
    ) -> "HitlRequest":
        if stage not in HITL_STAGES:
            raise ValueError(f"stage must be one of: {', '.join(HITL_STAGES)}")
        return cls(
            request_id=uuid.uuid4().hex[:16],
            task_id=task_id,
            stage=stage,
            operation=operation,
            impact=impact,
            alternatives=tuple(alternatives),
            recommendation=recommendation,
            resource=resource,
            arguments=dict(arguments) if arguments is not None else None,
            decision=dict(decision) if decision is not None else None,
            created_at=_utc_now(),
        )

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "HitlRequest":
        alternatives = data.get("alternatives")
        arguments = data.get("arguments")
        decision = data.get("decision")
        return cls(
            request_id=str(data.get("request_id", "")),
            task_id=str(data.get("task_id", "")),
            stage=str(data.get("stage", "")),
            operation=str(data.get("operation", "")),
            impact=str(data.get("impact", "")),
            alternatives=tuple(str(item) for item in alternatives) if isinstance(alternatives, (list, tuple)) else (),
            recommendation=str(data.get("recommendation", "reject")),
            resource=str(data.get("resource", "")),
            arguments=dict(arguments) if isinstance(arguments, Mapping) else None,
            decision=dict(decision) if isinstance(decision, Mapping) else None,
            created_at=str(data.get("created_at", "")),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "request_id": self.request_id,
            "task_id": self.task_id,
            "stage": self.stage,
            "operation": self.operation,
            "impact": self.impact,
            "alternatives": list(self.alternatives),
            "recommendation": self.recommendation,
            "resource": self.resource,
            "arguments": self.arguments,
            "decision": self.decision,
            "created_at": self.created_at,
        }

    def describe(self) -> str:
        """Render the request for a text channel (F-DX-04)."""

        lines = [
            f"[{self.stage}] {self.operation}",
            f"  impact: {self.impact}",
            f"  recommendation: {self.recommendation}",
        ]
        if self.resource:
            lines.insert(1, f"  resource: {self.resource}")
        if self.arguments:
            lines.append(f"  arguments: {self.arguments}")
        for alternative in self.alternatives:
            lines.append(f"  alternative: {alternative}")
        return "\n".join(lines)


@dataclass(frozen=True)
class HitlResponse:
    """A human answer: approve / reject / modify / defer (F-HITL-03)."""

    kind: str
    request_id: str = ""
    responder: str = ""
    note: str = ""
    arguments: dict[str, Any] | None = None

    def __post_init__(self) -> None:
        if self.kind not in HITL_RESPONSE_KINDS:
            raise ValueError(f"kind must be one of: {', '.join(HITL_RESPONSE_KINDS)}")
        if self.kind == "modify" and self.arguments is None:
            raise ValueError("a modify response must carry replacement arguments")

    @property
    def approves(self) -> bool:
        """True when execution may proceed (an approval or an edited approval)."""

        return self.kind in ("approve", "modify")

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "HitlResponse":
        arguments = data.get("arguments")
        return cls(
            kind=str(data.get("kind", "")),
            request_id=str(data.get("request_id", "")),
            responder=str(data.get("responder", "")),
            note=str(data.get("note", "")),
            arguments=dict(arguments) if isinstance(arguments, Mapping) else None,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "kind": self.kind,
            "request_id": self.request_id,
            "responder": self.responder,
            "note": self.note,
            "arguments": self.arguments,
        }


@dataclass(frozen=True)
class HitlPolicy:
    """Who may approve, and what always needs a human (F-HITL-07)."""

    approvers: tuple[str, ...] = ()
    always_confirm_resources: tuple[str, ...] = ()
    always_confirm_side_effects: tuple[str, ...] = ()
    timeout_seconds: float | None = None
    on_timeout: str = "pending"
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.on_timeout not in TIMEOUT_ACTIONS:
            raise ValueError(f"on_timeout must be one of: {', '.join(TIMEOUT_ACTIONS)}")
        if self.timeout_seconds is not None and self.timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be positive")

    def requires_confirmation(self, metadata: ResourceMetadata) -> bool:
        """True when this resource must be confirmed even if the gate allows it."""

        return (
            metadata.id in self.always_confirm_resources
            or metadata.identity in self.always_confirm_resources
            or metadata.side_effect in self.always_confirm_side_effects
        )

    def authorize(self, response: HitlResponse) -> None:
        """Raise unless ``response`` comes from a permitted approver."""

        if not self.approvers:
            return
        if response.kind in ("reject", "defer"):
            return
        if response.responder not in self.approvers:
            allowed = ", ".join(self.approvers)
            raise HitlError(
                f"{response.responder or 'anonymous'} may not approve this request; "
                f"respond as one of: {allowed}"
            )


class HitlBroker(ABC):
    """Confirmation channel (F-HITL-05).

    ``request`` returns ``None`` when nobody answered in time; the kernel then
    leaves the task paused and durable so a response can arrive later.
    """

    def __init__(self, policy: HitlPolicy | None = None) -> None:
        self.policy = policy or HitlPolicy()

    def request(self, request: HitlRequest) -> HitlResponse | None:
        timeout = self.policy.timeout_seconds
        if timeout is None:
            response = self._ask(request)
        else:
            executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="marmo-hitl")
            try:
                future = executor.submit(self._ask, request)
                try:
                    response = future.result(timeout=timeout)
                except FutureTimeoutError:
                    return self._on_timeout(request)
            finally:
                executor.shutdown(wait=False)
        if response is None:
            return None
        response = self.accept(response, request)
        return response

    def accept(self, response: HitlResponse, request: HitlRequest | None = None) -> HitlResponse:
        """Validate a response against the policy and bind it to its request."""

        if request is not None and not response.request_id:
            response = HitlResponse(
                kind=response.kind,
                request_id=request.request_id,
                responder=response.responder,
                note=response.note,
                arguments=response.arguments,
            )
        if request is not None and response.request_id != request.request_id:
            raise HitlError(
                f"response targets request {response.request_id!r} but {request.request_id!r} is pending; "
                "reload the pending request and answer that one"
            )
        if response.kind == "modify" and request is not None and request.stage != "execution":
            raise HitlError(
                f"a modify response only applies to tool arguments (stage 'execution'), "
                f"not stage {request.stage!r}; approve or reject instead"
            )
        self.policy.authorize(response)
        return response

    def _on_timeout(self, request: HitlRequest) -> HitlResponse | None:
        if self.policy.on_timeout == "deny":
            return HitlResponse(
                kind="reject",
                request_id=request.request_id,
                note=f"no response within {self.policy.timeout_seconds:g}s; denied by policy",
            )
        return None

    @abstractmethod
    def _ask(self, request: HitlRequest) -> HitlResponse | None:
        """Deliver the request to a human and return their answer, or None."""


class PendingHitlBroker(HitlBroker):
    """Default channel: records the request and never answers by itself.

    The task pauses durably and an operator (CLI, API, webhook) supplies the
    response later through ``Kernel.resume``.
    """

    def __init__(self, policy: HitlPolicy | None = None) -> None:
        super().__init__(policy)
        self.requests: list[HitlRequest] = []

    def _ask(self, request: HitlRequest) -> HitlResponse | None:
        self.requests.append(request)
        return None


class CallbackHitlBroker(HitlBroker):
    """Adapt any callable into a confirmation channel (F-HITL-05)."""

    def __init__(
        self,
        callback: Callable[[HitlRequest], HitlResponse | None],
        policy: HitlPolicy | None = None,
    ) -> None:
        super().__init__(policy)
        self.callback = callback

    def _ask(self, request: HitlRequest) -> HitlResponse | None:
        return self.callback(request)


class ConsoleHitlBroker(HitlBroker):
    """Prompt on the terminal; intended for the CLI and local development."""

    def __init__(self, policy: HitlPolicy | None = None, responder: str = "console") -> None:
        super().__init__(policy)
        self.responder = responder

    def _ask(self, request: HitlRequest) -> HitlResponse | None:
        print(request.describe())
        try:
            answer = input("approve / reject / defer? ").strip().casefold()
        except EOFError:
            return None
        if answer in ("a", "approve", "y", "yes"):
            return HitlResponse(kind="approve", request_id=request.request_id, responder=self.responder)
        if answer in ("r", "reject", "n", "no"):
            return HitlResponse(kind="reject", request_id=request.request_id, responder=self.responder)
        return HitlResponse(kind="defer", request_id=request.request_id, responder=self.responder)


class AutoApproveHitlBroker(HitlBroker):
    """Approve everything. For tests and explicitly trusted automation only."""

    def __init__(self, policy: HitlPolicy | None = None, responder: str = "auto") -> None:
        super().__init__(policy)
        self.responder = responder

    def _ask(self, request: HitlRequest) -> HitlResponse | None:
        return HitlResponse(kind="approve", request_id=request.request_id, responder=self.responder)


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")
