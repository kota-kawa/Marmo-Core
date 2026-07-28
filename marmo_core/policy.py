"""Policy Gateway primitives for activation and execution checks."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping

from .errors import MarmoError
from .models import SIDE_EFFECTS, TRUST_LEVELS, ResourceDefinition
from .safety import SafetyFinding, SafetyInspector
from .security import (
    CORE_ISOLATION_LEVELS,
    ISOLATION_LEVELS,
    isolation_level,
    isolation_satisfies,
)


POLICY_VERDICTS = ("allow", "deny", "escalate")
POLICY_GATES = ("activation", "execution", "output")

DEFAULT_ALLOWED_TRUST_LEVELS = ("core", "verified", "community")
DEFAULT_ALLOWED_SIDE_EFFECTS = SIDE_EFFECTS
DEFAULT_ESCALATE_SIDE_EFFECTS = ("write", "external", "irreversible")


@dataclass(frozen=True)
class PolicyContext:
    """Runtime policy inputs that are external to a resource definition."""

    granted_permissions: tuple[str, ...] = ()
    max_cost: float | None = None
    allowed_trust_levels: tuple[str, ...] = DEFAULT_ALLOWED_TRUST_LEVELS
    allowed_side_effects: tuple[str, ...] = DEFAULT_ALLOWED_SIDE_EFFECTS
    escalate_side_effects: tuple[str, ...] = DEFAULT_ESCALATE_SIDE_EFFECTS
    human_approved: bool = False
    approved_resources: tuple[str, ...] = ()
    approved_operations: tuple[str, ...] = ()
    allowed_external_hosts: tuple[str, ...] = ()
    blocked_external_hosts: tuple[str, ...] = ()
    minimum_isolation_level: str = "L0"
    available_isolation_levels: tuple[str, ...] = CORE_ISOLATION_LEVELS
    untrusted_content_sources: tuple[str, ...] = ()
    prompt_injection_findings: tuple[str, ...] = ()
    dry_run: bool = False
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def approves(self, resource_id: str, identity: str) -> bool:
        """True when a human has cleared this resource's escalation-class risk.

        ``human_approved`` clears everything at once; ``approved_resources``
        scopes the approval to what the person was actually shown, which is
        what the HITL Broker records (4.12).
        """

        return self.human_approved or identity in self.approved_resources or resource_id in self.approved_resources


@dataclass(frozen=True)
class PolicyDecision:
    """Policy Gateway verdict for a single resource at a specific gate."""

    verdict: str
    reason: str
    gate: str
    resource_id: str
    resource_version: str
    required_permissions: tuple[str, ...]
    granted_permissions: tuple[str, ...]
    missing_permissions: tuple[str, ...]
    trust_level: str
    side_effect: str
    cost_estimate: float
    dry_run: bool
    reasons: tuple[str, ...]
    risk_findings: tuple[dict[str, str], ...] = ()
    approval_token: str = ""
    isolation_level: str = ""
    required_isolation_level: str = ""

    @property
    def allowed(self) -> bool:
        return self.verdict == "allow"

    @property
    def denied(self) -> bool:
        return self.verdict == "deny"

    @property
    def escalated(self) -> bool:
        return self.verdict == "escalate"

    def to_dict(self) -> dict[str, Any]:
        return {
            "verdict": self.verdict,
            "reason": self.reason,
            "gate": self.gate,
            "resource_id": self.resource_id,
            "resource_version": self.resource_version,
            "required_permissions": list(self.required_permissions),
            "granted_permissions": list(self.granted_permissions),
            "missing_permissions": list(self.missing_permissions),
            "trust_level": self.trust_level,
            "side_effect": self.side_effect,
            "cost_estimate": self.cost_estimate,
            "dry_run": self.dry_run,
            "reasons": list(self.reasons),
            "risk_findings": [dict(item) for item in self.risk_findings],
            "approval_token": self.approval_token,
            "isolation_level": self.isolation_level,
            "required_isolation_level": self.required_isolation_level,
        }


@dataclass(frozen=True)
class PolicyRejectedError(MarmoError):
    """Raised when a mandatory gate returns deny or escalate (F-GATE-01)."""

    decision: PolicyDecision | None = None


class PolicyGateway:
    """Evaluate resource use against a conservative default policy."""

    def __init__(self, safety: SafetyInspector | None = None) -> None:
        self.safety = safety or SafetyInspector()

    def evaluate(
        self,
        resource: ResourceDefinition,
        context: PolicyContext | None = None,
        *,
        gate: str = "activation",
        arguments: Mapping[str, Any] | None = None,
    ) -> PolicyDecision:
        if gate not in POLICY_GATES:
            raise ValueError(f"gate must be one of: {', '.join(POLICY_GATES)}")
        context = context or PolicyContext()
        _validate_context(context)

        metadata = resource.metadata
        granted = set(context.granted_permissions)
        missing_permissions = tuple(sorted(set(metadata.required_permissions) - granted))

        deny_reasons: list[str] = []
        escalate_reasons: list[str] = []
        allow_reasons: list[str] = []
        risk_findings: tuple[SafetyFinding, ...] = ()
        approval_token = ""
        declared_isolation = isolation_level(resource.extras) if metadata.kind == "tool" else ""

        if missing_permissions:
            deny_reasons.append("missing required permissions: " + ", ".join(missing_permissions))
        elif metadata.required_permissions:
            allow_reasons.append("required permissions are granted")
        else:
            allow_reasons.append("resource requires no permissions")

        if context.max_cost is not None and metadata.cost_estimate > context.max_cost:
            deny_reasons.append(
                f"cost_estimate {metadata.cost_estimate:g} exceeds max_cost {context.max_cost:g}"
            )
        elif context.max_cost is not None:
            allow_reasons.append(f"cost_estimate {metadata.cost_estimate:g} is within max_cost")
        else:
            allow_reasons.append("no cost ceiling was configured")

        if metadata.trust_level not in context.allowed_trust_levels:
            deny_reasons.append(f"trust_level {metadata.trust_level} is not allowed")
        else:
            allow_reasons.append(f"trust_level {metadata.trust_level} is allowed")

        if metadata.kind == "tool":
            required_isolation = context.minimum_isolation_level
            if declared_isolation not in context.available_isolation_levels:
                deny_reasons.append(
                    f"isolation_level {declared_isolation} is not available in this runtime"
                )
            elif not isolation_satisfies(declared_isolation, required_isolation):
                deny_reasons.append(
                    f"isolation_level {declared_isolation} does not satisfy required {required_isolation}"
                )
            else:
                allow_reasons.append(
                    f"isolation_level {declared_isolation} satisfies required {required_isolation}"
                )

        approved = context.approves(metadata.id, metadata.identity)
        if metadata.side_effect not in context.allowed_side_effects:
            deny_reasons.append(f"side_effect {metadata.side_effect} is not allowed")
        elif metadata.side_effect in context.escalate_side_effects and context.dry_run:
            allow_reasons.append(
                f"side_effect {metadata.side_effect} would require human approval outside dry_run"
            )
        elif metadata.side_effect in context.escalate_side_effects and not approved:
            escalate_reasons.append(f"side_effect {metadata.side_effect} requires human approval")
        elif metadata.side_effect in context.escalate_side_effects:
            allow_reasons.append(f"side_effect {metadata.side_effect} was human-approved")
        else:
            allow_reasons.append(f"side_effect {metadata.side_effect} is allowed")

        if context.dry_run:
            allow_reasons.append("dry_run is enabled; tool handlers will not be invoked")

        if gate == "execution" and arguments is not None:
            findings: list[SafetyFinding] = list(
                self.safety.inspect(
                    resource,
                    arguments,
                    allowed_external_hosts=context.allowed_external_hosts,
                    blocked_external_hosts=context.blocked_external_hosts,
                )
            )
            if context.untrusted_content_sources and metadata.side_effect in (
                "write",
                "external",
                "irreversible",
            ):
                findings.append(
                    SafetyFinding(
                        "trust_boundary.untrusted_side_effect",
                        "escalate",
                        "a side-effecting operation was proposed after the model consumed untrusted content",
                    )
                )
                for code in context.prompt_injection_findings:
                    findings.append(
                        SafetyFinding(
                            code,
                            "escalate",
                            "a prior untrusted input matched this prompt-injection rule",
                        )
                    )
            unique_findings = {finding.code: finding for finding in findings}
            risk_findings = tuple(unique_findings[code] for code in sorted(unique_findings))
            if risk_findings:
                approval_token = self.safety.approval_token(resource, arguments, risk_findings)
            for finding in risk_findings:
                explanation = f"safety rule {finding.code}: {finding.message}"
                if finding.verdict == "deny":
                    deny_reasons.append(explanation)
                elif context.dry_run:
                    allow_reasons.append(explanation + "; would require approval outside dry_run")
                elif approval_token in context.approved_operations:
                    allow_reasons.append(explanation + "; exact operation was human-approved")
                else:
                    escalate_reasons.append(explanation + "; exact operation requires human approval")

        if deny_reasons:
            verdict = "deny"
            reasons = tuple(deny_reasons + allow_reasons)
        elif escalate_reasons:
            verdict = "escalate"
            reasons = tuple(escalate_reasons + allow_reasons)
        else:
            verdict = "allow"
            reasons = tuple(allow_reasons)

        reason = "; ".join(reasons)
        return PolicyDecision(
            verdict=verdict,
            reason=reason,
            gate=gate,
            resource_id=metadata.id,
            resource_version=metadata.version,
            required_permissions=metadata.required_permissions,
            granted_permissions=context.granted_permissions,
            missing_permissions=missing_permissions,
            trust_level=metadata.trust_level,
            side_effect=metadata.side_effect,
            cost_estimate=metadata.cost_estimate,
            dry_run=context.dry_run,
            reasons=reasons,
            risk_findings=tuple(finding.to_dict() for finding in risk_findings),
            approval_token=approval_token,
            isolation_level=declared_isolation,
            required_isolation_level=(
                context.minimum_isolation_level if metadata.kind == "tool" else ""
            ),
        )


def _validate_context(context: PolicyContext) -> None:
    if context.max_cost is not None and context.max_cost < 0:
        raise ValueError("max_cost must be non-negative")
    invalid_trust = set(context.allowed_trust_levels) - set(TRUST_LEVELS)
    if invalid_trust:
        raise ValueError(f"invalid allowed trust_level: {', '.join(sorted(invalid_trust))}")
    invalid_side_effects = set(context.allowed_side_effects) - set(SIDE_EFFECTS)
    if invalid_side_effects:
        raise ValueError(f"invalid allowed side_effect: {', '.join(sorted(invalid_side_effects))}")
    invalid_escalations = set(context.escalate_side_effects) - set(SIDE_EFFECTS)
    if invalid_escalations:
        raise ValueError(f"invalid escalation side_effect: {', '.join(sorted(invalid_escalations))}")
    if context.minimum_isolation_level not in ISOLATION_LEVELS:
        raise ValueError(
            f"minimum_isolation_level must be one of: {', '.join(ISOLATION_LEVELS)}"
        )
    invalid_isolation = set(context.available_isolation_levels) - set(ISOLATION_LEVELS)
    if invalid_isolation:
        raise ValueError(
            "invalid available isolation_level: " + ", ".join(sorted(invalid_isolation))
        )
    for label, hosts in (
        ("allowed_external_hosts", context.allowed_external_hosts),
        ("blocked_external_hosts", context.blocked_external_hosts),
    ):
        invalid_hosts = [host for host in hosts if not host.strip() or "://" in host or "/" in host]
        if invalid_hosts:
            raise ValueError(f"{label} entries must be hostnames, not URLs: {', '.join(invalid_hosts)}")
