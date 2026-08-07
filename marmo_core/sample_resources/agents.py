"""Deterministic, offline implementations for the bundled Agent samples.

These handlers are intentionally small and synchronous so they can run through
Marmo's guarded AgentRuntime without API credentials. Production applications
can replace them with LLM-backed or service-backed callables while preserving
the same Agent Card contracts.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from statistics import fmean
from typing import Any
import re


def code_reviewer(goal: str, diff: str = "") -> dict[str, Any]:
    """Return evidence-based static review findings for a supplied diff."""

    task = _required_goal(goal)
    evidence = diff or task
    findings: list[dict[str, str]] = []
    checks = (
        (r"\bTODO\b|\bFIXME\b", "medium", "unfinished-work", "Unresolved TODO or FIXME marker."),
        (r"except\s*:\s*", "high", "broad-except", "Bare exception handler can hide failures."),
        (r"shell\s*=\s*True", "high", "shell-injection", "Shell execution needs strict input control."),
        (r"(?:api[_-]?key|password|secret)\s*=\s*['\"][^'\"]+", "critical", "embedded-secret", "Possible embedded credential."),
    )
    for pattern, severity, code, message in checks:
        if re.search(pattern, evidence, flags=re.IGNORECASE):
            findings.append({"severity": severity, "code": code, "message": message})
    return {
        "summary": f"Reviewed change request: {task}",
        "findings": findings,
        "verdict": "changes-requested" if findings else "no-static-findings",
        "checklist": ["correctness", "failure modes", "compatibility", "tests"],
    }


def security_reviewer(goal: str, context: str = "") -> dict[str, Any]:
    """Identify common trust-boundary and dangerous-operation signals."""

    task = _required_goal(goal)
    evidence = f"{task}\n{context}".casefold()
    findings: list[dict[str, str]] = []
    signals = (
        (("eval(", "exec("), "critical", "dynamic-code", "Dynamic code execution needs isolation."),
        (("password", "api key", "secret"), "high", "secret-handling", "Confirm secrets are referenced and redacted."),
        (("http://",), "high", "cleartext-network", "Use authenticated HTTPS for external traffic."),
        (("delete", "overwrite", "drop table"), "high", "destructive-action", "Require explicit scope and approval."),
        (("webhook", "external", "upload"), "medium", "data-egress", "Constrain destination and outbound data."),
    )
    for needles, severity, code, message in signals:
        if any(needle in evidence for needle in needles):
            findings.append({"severity": severity, "code": code, "message": message})
    return {
        "scope": task,
        "findings": findings,
        "risk": _highest_severity(findings),
        "controls": ["least privilege", "input validation", "secret redaction", "audit logging"],
    }


def test_planner(goal: str, changed_files: Sequence[str] = ()) -> dict[str, Any]:
    """Create a compact behavior-focused verification plan."""

    task = _required_goal(goal)
    files = [str(path) for path in changed_files]
    return {
        "goal": task,
        "changed_files": files,
        "test_cases": [
            {"priority": "P0", "case": "Primary user-visible success path"},
            {"priority": "P0", "case": "Invalid or missing required input"},
            {"priority": "P1", "case": "Boundary values and empty collections"},
            {"priority": "P1", "case": "Regression for the reported failure"},
        ],
        "commands": ["python3 -m unittest discover -s tests", "python3 -m ruff check ."],
    }


def docs_writer(goal: str, audience: str = "developers") -> dict[str, Any]:
    """Draft a concise documentation outline and starter text."""

    task = _required_goal(goal)
    target = audience.strip() or "developers"
    return {
        "title": task.rstrip("."),
        "audience": target,
        "outline": ["Outcome", "Prerequisites", "Usage", "Failure modes", "Verification"],
        "draft": (
            f"This guide explains {task}. It is written for {target}. "
            "Start with the smallest runnable example, then document configuration and failure behavior."
        ),
    }


def incident_triager(goal: str, symptoms: str = "") -> dict[str, Any]:
    """Estimate incident severity and return reversible next actions."""

    task = _required_goal(goal)
    evidence = f"{task} {symptoms}".casefold()
    if any(term in evidence for term in ("complete outage", "all users", "data loss", "payments down")):
        severity = "SEV-1"
    elif any(term in evidence for term in ("partial outage", "many users", "5xx", "unavailable")):
        severity = "SEV-2"
    elif any(term in evidence for term in ("slow", "degraded", "intermittent")):
        severity = "SEV-3"
    else:
        severity = "UNCONFIRMED"
    return {
        "incident": task,
        "severity": severity,
        "next_actions": [
            "Confirm user impact and start time",
            "Assign an incident owner",
            "Preserve logs and recent-change evidence",
            "Choose the smallest reversible containment action",
        ],
        "missing_evidence": ["affected users", "error rate", "recent deployments"],
    }


def data_analyst(goal: str, records: Sequence[Any] = ()) -> dict[str, Any]:
    """Summarize numeric fields from supplied JSON-compatible records."""

    task = _required_goal(goal)
    numeric: dict[str, list[float]] = {}
    for record in records:
        if isinstance(record, Mapping):
            for key, value in record.items():
                if isinstance(value, (int, float)) and not isinstance(value, bool):
                    numeric.setdefault(str(key), []).append(float(value))
        elif isinstance(record, (int, float)) and not isinstance(record, bool):
            numeric.setdefault("value", []).append(float(record))
    summaries = {
        key: {
            "count": len(values),
            "min": min(values),
            "max": max(values),
            "mean": fmean(values),
        }
        for key, values in sorted(numeric.items())
    }
    return {
        "question": task,
        "record_count": len(records),
        "numeric_summary": summaries,
        "limitations": [] if records else ["No records were supplied; no metrics were calculated."],
    }


def api_designer(goal: str, method: str = "GET", path: str = "/resource") -> dict[str, Any]:
    """Produce a small HTTP contract skeleton with compatibility notes."""

    task = _required_goal(goal)
    normalized_method = method.upper()
    if normalized_method not in {"GET", "POST", "PUT", "PATCH", "DELETE"}:
        raise ValueError("method must be GET, POST, PUT, PATCH, or DELETE")
    if not path.startswith("/"):
        raise ValueError("path must start with '/'")
    return {
        "goal": task,
        "operation": {"method": normalized_method, "path": path},
        "request_schema": {"type": "object", "additionalProperties": False},
        "responses": {
            "success": {"status": 200 if normalized_method == "GET" else 201},
            "invalid": {"status": 400, "code": "invalid_request"},
            "conflict": {"status": 409, "code": "conflict"},
        },
        "compatibility": "Prefer additive schema changes; version incompatible contracts.",
    }


def release_manager(goal: str, checks: Mapping[str, Any] | None = None) -> dict[str, Any]:
    """Assess supplied release checks without publishing or deploying."""

    task = _required_goal(goal)
    supplied = dict(checks or {})
    blockers = [name for name, status in supplied.items() if status not in (True, "pass", "passed")]
    if not supplied:
        blockers = ["tests", "static-analysis", "package-build", "rollback-plan"]
    return {
        "release": task,
        "ready": not blockers,
        "blockers": blockers,
        "rollout": ["record current version", "deploy canary", "monitor error signals", "expand rollout"],
        "rollback_trigger": "Error rate or critical business metric exceeds the agreed threshold.",
    }


def support_specialist(goal: str, customer_message: str = "") -> dict[str, Any]:
    """Draft, but never send, an empathetic customer response."""

    task = _required_goal(goal)
    message = customer_message.strip()
    acknowledgement = "Thanks for reporting this. I understand the impact this is having."
    if message:
        acknowledgement = "Thanks for the details. I understand this issue is disrupting your work."
    return {
        "goal": task,
        "draft": (
            f"{acknowledgement} We are checking the verified system state now. "
            "Our next update will include what we found and the next concrete action."
        ),
        "internal_questions": ["When did this start?", "Which workflow is affected?", "Can it be reproduced?"],
        "sent": False,
    }


def research_assistant(goal: str, sources: Sequence[Any] = ()) -> dict[str, Any]:
    """Create a source-bounded evidence table without external retrieval."""

    task = _required_goal(goal)
    evidence: list[dict[str, str]] = []
    for index, source in enumerate(sources, start=1):
        if isinstance(source, Mapping):
            title = str(source.get("title") or f"Source {index}")
            content = str(source.get("content") or source.get("text") or "")
        else:
            title = f"Source {index}"
            content = str(source)
        evidence.append({"source": title, "excerpt": _first_sentence(content)})
    return {
        "question": task,
        "source_count": len(evidence),
        "evidence": evidence,
        "synthesis": (
            "No sources were supplied; external claims cannot be supported."
            if not evidence
            else "The evidence table contains the source-bounded statements available for synthesis."
        ),
        "open_questions": [] if evidence else ["Which authoritative sources should be included?"],
    }


def _required_goal(goal: str) -> str:
    if not isinstance(goal, str) or not goal.strip():
        raise ValueError("goal must be a non-empty string")
    return goal.strip()


def _highest_severity(findings: Sequence[Mapping[str, str]]) -> str:
    order = {"critical": 4, "high": 3, "medium": 2, "low": 1}
    if not findings:
        return "none-detected"
    return max((item.get("severity", "low") for item in findings), key=lambda item: order.get(item, 0))


def _first_sentence(content: str) -> str:
    normalized = " ".join(content.split())
    if not normalized:
        return ""
    match = re.search(r".+?[.!?](?:\s|$)", normalized)
    return (match.group(0) if match else normalized)[:240]
