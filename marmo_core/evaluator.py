"""Execution Evaluator: closing the feedback loop (4.11 F-LOG-08 → 4.1 F-REG-05).

Layers 1 and 2 are static: they score a candidate from what its metadata
*claims*. §15.4 (第3層: 適応) asks the opposite question — what did actually
happen when we picked this resource — and both adaptive routes (案F's case
reuse, 案D's bandit over u(i, q)) need that signal before they can be
evaluated at all. This module is that missing link:

    Kernel run → AuditLog (F-LOG-03) → ExecutionOutcome → ResourceStats
    → retrieval score component ``success`` → next routing decision

``ExecutionEvaluator`` aggregates outcomes per resource and writes the
result back onto the registry as ``ResourceStats`` (F-REG-05), the field the
retriever already mixes into its composite score. Nothing here is
LLM-backed or model-backed: it is counting, and it stays zero-dependency.

Two deliberate design points, both of which the §15.4 experiments depend on:

- **Shrinkage, not raw ratios.** One failed run should not drive a
  resource's ``success_rate`` to 0.0 and bury it forever. Observations are
  smoothed toward ``prior_success_rate`` with ``prior_weight`` pseudo-counts
  (a Beta(α, β) posterior mean), which is also the exact quantity 案D's
  Thompson sampling will sample from rather than average.
- **Set-level credit assignment is unsolved here.** A task activates a set;
  the outcome is observed for the *set*. This evaluator attributes the task
  outcome, latency, and cost to every participating member. That is the
  honest baseline (and enough to move ranking), but a member that was
  irrelevant to a success is credited for it — per-member attribution is
  precisely what 案D has to improve on, and is recorded as a limitation
  rather than papered over.
"""

from __future__ import annotations

from dataclasses import dataclass, replace as dataclass_replace
from datetime import datetime, timezone
from typing import Any, Iterable, Sequence

from .audit import AuditLog, AuditRecord
from .models import ResourceStats, parse_resource_ref
from .registry import ResourceRegistry


@dataclass(frozen=True)
class ExecutionOutcome:
    """What one completed task tells us about the resources it used."""

    task: str
    resource_ids: tuple[str, ...]
    success: bool
    latency_ms: float = 0.0
    cost: float = 0.0
    trace_id: str = ""
    timestamp: str = ""
    detail: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "task": self.task,
            "resource_ids": list(self.resource_ids),
            "success": self.success,
            "latency_ms": round(self.latency_ms, 3),
            "cost": round(self.cost, 6),
            "trace_id": self.trace_id,
            "timestamp": self.timestamp,
            "detail": self.detail,
        }


@dataclass
class _Tally:
    attempts: int = 0
    successes: int = 0
    latency_total: float = 0.0
    cost_total: float = 0.0
    last_used_at: str = ""


class ExecutionEvaluator:
    """Aggregates execution outcomes into per-resource ``ResourceStats``.

    ``prior_weight`` pseudo-observations at ``prior_success_rate`` smooth the
    success ratio; with the default 2.0 / 0.5 a single failure moves a fresh
    resource to 0.33 rather than 0.0, so one bad run costs it rank without
    removing it from consideration.
    """

    def __init__(self, *, prior_weight: float = 2.0, prior_success_rate: float = 0.5) -> None:
        if prior_weight < 0:
            raise ValueError("prior_weight must be non-negative")
        if not 0.0 <= prior_success_rate <= 1.0:
            raise ValueError("prior_success_rate must be between 0.0 and 1.0")
        self.prior_weight = prior_weight
        self.prior_success_rate = prior_success_rate
        self._tallies: dict[str, _Tally] = {}
        self.outcomes: list[ExecutionOutcome] = []

    # -- ingestion -------------------------------------------------------------

    def observe(self, outcome: ExecutionOutcome) -> None:
        self.outcomes.append(outcome)
        timestamp = outcome.timestamp or _utc_now()
        for resource_id in outcome.resource_ids:
            tally = self._tallies.setdefault(resource_id, _Tally())
            tally.attempts += 1
            tally.successes += int(outcome.success)
            tally.latency_total += max(outcome.latency_ms, 0.0)
            tally.cost_total += max(outcome.cost, 0.0)
            tally.last_used_at = timestamp

    def observe_task(
        self,
        task: str,
        resource_ids: Iterable[str],
        *,
        success: bool,
        latency_ms: float = 0.0,
        cost: float = 0.0,
        trace_id: str = "",
        detail: str = "",
    ) -> ExecutionOutcome:
        outcome = ExecutionOutcome(
            task=task,
            resource_ids=tuple(resource_ids),
            success=success,
            latency_ms=latency_ms,
            cost=cost,
            trace_id=trace_id,
            timestamp=_utc_now(),
            detail=detail,
        )
        self.observe(outcome)
        return outcome

    def ingest_audit(self, audit_log: AuditLog | Sequence[AuditRecord]) -> list[ExecutionOutcome]:
        """Replay a kernel audit log into outcomes and observe them."""

        outcomes = outcomes_from_audit(audit_log)
        for outcome in outcomes:
            self.observe(outcome)
        return outcomes

    # -- readout ---------------------------------------------------------------

    def attempts(self, resource_id: str) -> int:
        tally = self._tallies.get(resource_id)
        return tally.attempts if tally else 0

    def stats_for(self, resource_id: str) -> ResourceStats | None:
        tally = self._tallies.get(resource_id)
        if tally is None or tally.attempts == 0:
            return None
        smoothed = (tally.successes + self.prior_weight * self.prior_success_rate) / (
            tally.attempts + self.prior_weight
        )
        return ResourceStats(
            success_rate=round(min(1.0, max(0.0, smoothed)), 6),
            average_latency_ms=round(tally.latency_total / tally.attempts, 3),
            average_cost=round(tally.cost_total / tally.attempts, 6),
            last_used_at=tally.last_used_at or None,
            usage_count=tally.attempts,
        )

    def snapshot(self) -> dict[str, ResourceStats]:
        return {
            resource_id: stats
            for resource_id in sorted(self._tallies)
            if (stats := self.stats_for(resource_id)) is not None
        }

    def reset(self) -> None:
        self._tallies.clear()
        self.outcomes.clear()

    # -- feedback --------------------------------------------------------------

    def apply(self, registry: ResourceRegistry) -> int:
        """Write observed stats onto the registry (F-REG-05). Returns updates.

        Every replacement bumps ``registry.revision``, so retrieval indexes
        and hierarchy groupings rebuild on the next search — necessary,
        because the composite score changed.
        """

        updated = 0
        for definition in registry.all():
            stats = self.stats_for(definition.metadata.id)
            if stats is None or stats == definition.metadata.stats:
                continue
            registry.replace(
                dataclass_replace(
                    definition, metadata=dataclass_replace(definition.metadata, stats=stats)
                )
            )
            updated += 1
        return updated

    def report(self) -> dict[str, Any]:
        return {
            "observations": len(self.outcomes),
            "resources_observed": len(self._tallies),
            "success_rate": (
                round(sum(1 for o in self.outcomes if o.success) / len(self.outcomes), 4)
                if self.outcomes
                else 0.0
            ),
            "stats": {rid: stats.to_dict() for rid, stats in self.snapshot().items()},
        }


def outcomes_from_audit(audit_log: AuditLog | Sequence[AuditRecord]) -> list[ExecutionOutcome]:
    """Reconstruct per-task outcomes from a hash-chained kernel audit log.

    The kernel writes one ``retrieve`` record (which set was selected) and
    one terminal ``task`` record (how it ended) per trace id; ``execute``
    records carry per-tool timings. Traces without both anchors are skipped
    rather than guessed at — an incomplete trace is not evidence.
    """

    records = audit_log.records if isinstance(audit_log, AuditLog) else list(audit_log)
    by_trace: dict[str, dict[str, Any]] = {}
    for record in records:
        bucket = by_trace.setdefault(
            record.trace_id, {"selected": None, "task": None, "goal": "", "latency_ms": 0.0, "timestamp": ""}
        )
        payload = record.payload
        if record.kind == "retrieve":
            if payload.get("selection_status") == "selected":
                bucket["selected"] = [
                    parse_resource_ref(str(identity))[0] for identity in payload.get("selected", [])
                ]
            bucket["goal"] = str(payload.get("task", "")) or bucket["goal"]
        elif record.kind == "execute":
            elapsed = payload.get("elapsed_ms")
            if isinstance(elapsed, (int, float)):
                bucket["latency_ms"] += float(elapsed)
        elif record.kind == "task":
            bucket["task"] = payload
            bucket["goal"] = str(payload.get("goal", "")) or bucket["goal"]
            bucket["timestamp"] = record.timestamp

    outcomes: list[ExecutionOutcome] = []
    for trace_id, bucket in by_trace.items():
        if bucket["selected"] is None or bucket["task"] is None:
            continue
        status = str(bucket["task"].get("status", ""))
        outcomes.append(
            ExecutionOutcome(
                task=bucket["goal"],
                resource_ids=tuple(bucket["selected"]),
                success=status == "completed",
                latency_ms=float(bucket["latency_ms"]),
                trace_id=trace_id,
                timestamp=str(bucket["timestamp"]),
                detail=status,
            )
        )
    return outcomes


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")
