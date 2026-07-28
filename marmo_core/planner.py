"""Planner: decompose a goal into an executable step DAG (4.6).

A ``Plan`` is a set of steps plus their dependency edges (F-PLAN-01/02).
Ordering is derived from the edges rather than stored, so the same plan
answers both "what runs next" and "what can run at the same time"
(F-PLAN-05) without a second representation to keep in sync.

Plans are validated before anything executes (F-PLAN-03): unknown resources,
missing permissions, dependency cycles, and edges pointing at steps that do
not exist are all caught up front rather than half way through a run.

Two planners ship, and the interface is swappable (F-PLAN-07):
``RuleBasedPlanner`` is deterministic and zero-dependency (it orders the
activated tools by their declared dependencies), while ``LLMPlanner`` asks a
model for the decomposition and validates the answer before trusting it.
Steps are plain data, so the kernel can persist a plan and resume it
(F-PLAN-06).
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field, replace
from typing import Any, Iterable, Mapping, Sequence
import hashlib
import json
import re

from .llm import ChatMessage, LLMProvider, default_arguments
from .models import ResourceDefinition, ValidationIssue
from .policy import PolicyContext
from .errors import SecretResolutionError
from .secrets import ensure_secret_refs, sanitize_secret_inputs


STEP_STATUSES = ("pending", "running", "completed", "failed", "skipped")

_PLAN_SYSTEM = (
    "You decompose a goal into executable steps for an agent kernel.\n"
    "Reply with JSON only: {\"steps\": [{\"id\": \"s1\", \"description\": \"...\", "
    "\"resource_id\": \"<one of the given tool ids>\", \"arguments\": {...}, "
    "\"expected_output\": \"...\", \"depends_on\": [\"s0\"]}]}\n"
    "Rules:\n"
    "- Use only the tool ids listed. Never invent one.\n"
    "- arguments must satisfy the tool's input schema exactly.\n"
    "- depends_on lists step ids that must finish first. Leave it empty for "
    "steps that can start immediately, so independent work runs in parallel.\n"
    "- Do not add steps that the goal does not require."
)


@dataclass(frozen=True)
class PlanStep:
    """One unit of work and what it needs (F-PLAN-02)."""

    id: str
    description: str
    resource_id: str
    kind: str = "tool"
    arguments: Mapping[str, Any] = field(default_factory=dict)
    expected_output: str = ""
    depends_on: tuple[str, ...] = ()
    status: str = "pending"
    result: Mapping[str, Any] | None = None

    def __post_init__(self) -> None:
        if self.status not in STEP_STATUSES:
            raise ValueError(f"status must be one of: {', '.join(STEP_STATUSES)}")

    @property
    def done(self) -> bool:
        return self.status in ("completed", "skipped")

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "PlanStep":
        depends = data.get("depends_on")
        arguments = data.get("arguments")
        result = data.get("result")
        return cls(
            id=str(data.get("id", "")),
            description=str(data.get("description", "")),
            resource_id=str(data.get("resource_id", "")),
            kind=str(data.get("kind", "tool")),
            arguments=dict(arguments) if isinstance(arguments, Mapping) else {},
            expected_output=str(data.get("expected_output", "")),
            depends_on=tuple(str(item) for item in depends) if isinstance(depends, (list, tuple)) else (),
            status=str(data.get("status", "pending")),
            result=dict(result) if isinstance(result, Mapping) else None,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "description": self.description,
            "resource_id": self.resource_id,
            "kind": self.kind,
            "arguments": sanitize_secret_inputs(self.arguments),
            "expected_output": self.expected_output,
            "depends_on": list(self.depends_on),
            "status": self.status,
            "result": dict(self.result) if self.result else None,
        }


@dataclass(frozen=True)
class Plan:
    """An ordered-by-dependency set of steps (F-PLAN-01)."""

    goal: str
    steps: tuple[PlanStep, ...] = ()
    revision: int = 1

    def step(self, step_id: str) -> PlanStep | None:
        return next((step for step in self.steps if step.id == step_id), None)

    @property
    def complete(self) -> bool:
        return all(step.done for step in self.steps)

    @property
    def failed(self) -> bool:
        return any(step.status == "failed" for step in self.steps)

    def ready(self) -> tuple[PlanStep, ...]:
        """Pending steps whose dependencies are all finished.

        Everything returned here can run at the same time (F-PLAN-05): by
        definition none of them depends on another.
        """

        done = {step.id for step in self.steps if step.done}
        return tuple(
            step
            for step in self.steps
            if step.status == "pending" and set(step.depends_on) <= done
        )

    def blocked(self) -> tuple[PlanStep, ...]:
        """Pending steps that can never run because a dependency did not finish."""

        finished = {step.id for step in self.steps if step.done}
        stalled = {step.id for step in self.steps if step.status == "failed"}
        return tuple(
            step
            for step in self.steps
            if step.status == "pending" and not set(step.depends_on) <= finished
            and (set(step.depends_on) & stalled or not self._reachable(step))
        )

    def _reachable(self, step: PlanStep) -> bool:
        pending = {item.id for item in self.steps if item.status == "pending"}
        done = {item.id for item in self.steps if item.done}
        return all(dep in pending or dep in done for dep in step.depends_on)

    def order(self) -> tuple[tuple[PlanStep, ...], ...]:
        """Group steps into dependency waves; each wave can run in parallel."""

        remaining = {step.id: step for step in self.steps}
        satisfied: set[str] = set()
        waves: list[tuple[PlanStep, ...]] = []
        while remaining:
            wave = tuple(
                step
                for step in remaining.values()
                if set(step.depends_on) <= satisfied
            )
            if not wave:
                raise ValueError("plan contains a dependency cycle")
            waves.append(wave)
            for step in wave:
                satisfied.add(step.id)
                del remaining[step.id]
        return tuple(waves)

    def with_step(self, step: PlanStep) -> "Plan":
        return replace(
            self,
            steps=tuple(step if item.id == step.id else item for item in self.steps),
        )

    def with_status(self, step_id: str, status: str, result: Mapping[str, Any] | None = None) -> "Plan":
        step = self.step(step_id)
        if step is None:
            raise ValueError(f"unknown step id: {step_id}")
        return self.with_step(replace(step, status=status, result=result if result is not None else step.result))

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "Plan":
        steps = data.get("steps")
        return cls(
            goal=str(data.get("goal", "")),
            steps=tuple(PlanStep.from_dict(item) for item in steps) if isinstance(steps, (list, tuple)) else (),
            revision=int(data.get("revision", 1)),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "goal": self.goal,
            "revision": self.revision,
            "steps": [step.to_dict() for step in self.steps],
        }

    def summary(self) -> dict[str, Any]:
        counts: dict[str, int] = {}
        for step in self.steps:
            counts[step.status] = counts.get(step.status, 0) + 1
        return {"goal": self.goal, "revision": self.revision, "steps": len(self.steps), "status_counts": counts}


def validate_plan(
    plan: Plan,
    resources: Mapping[str, ResourceDefinition],
    context: PolicyContext | None = None,
) -> list[ValidationIssue]:
    """Check a plan before anything runs (F-PLAN-03).

    Catches duplicate and unknown step ids, dependency cycles, resources that
    are not in the offered set, and permissions the context does not hold.
    Permission gaps are reported here as well as enforced at the gate; the
    point is to fail before the first side effect, not instead of the gate.
    """

    issues: list[ValidationIssue] = []
    granted = set(context.granted_permissions) if context is not None else set()
    seen: set[str] = set()

    for step in plan.steps:
        path = f"steps.{step.id or '?'}"
        if not step.id:
            issues.append(ValidationIssue("step id must be non-empty", path))
        elif step.id in seen:
            issues.append(ValidationIssue(f"duplicate step id: {step.id}", path))
        seen.add(step.id)
        if not step.resource_id:
            issues.append(ValidationIssue("step must name a resource_id", path))
            continue
        try:
            ensure_secret_refs(step.arguments)
        except SecretResolutionError as exc:
            issues.append(ValidationIssue(str(exc), f"{path}.arguments"))
        definition = resources.get(step.resource_id)
        if definition is None:
            issues.append(
                ValidationIssue(
                    f"unknown resource: {step.resource_id}; it was not selected for this task",
                    path,
                )
            )
            continue
        if context is not None:
            missing = sorted(set(definition.metadata.required_permissions) - granted)
            if missing:
                issues.append(
                    ValidationIssue(
                        f"{step.resource_id} requires permissions that were not granted: "
                        + ", ".join(missing),
                        path,
                    )
                )

    known = {step.id for step in plan.steps}
    for step in plan.steps:
        for dependency in step.depends_on:
            if dependency not in known:
                issues.append(
                    ValidationIssue(f"depends on unknown step: {dependency}", f"steps.{step.id}")
                )
            elif dependency == step.id:
                issues.append(ValidationIssue("step depends on itself", f"steps.{step.id}"))
    try:
        plan.order()
    except ValueError as exc:
        issues.append(ValidationIssue(str(exc), "steps"))
    return issues


class Planner(ABC):
    """Planning interface; implementations are swappable (F-PLAN-07)."""

    @abstractmethod
    def plan(
        self,
        goal: str,
        resources: Sequence[ResourceDefinition],
        *,
        context: PolicyContext | None = None,
    ) -> Plan:
        """Decompose ``goal`` into steps over the offered resources."""

    def replan(
        self,
        plan: Plan,
        resources: Sequence[ResourceDefinition],
        *,
        context: PolicyContext | None = None,
        failure: Mapping[str, Any] | None = None,
    ) -> Plan:
        """Revise a plan after a step failed (F-PLAN-04).

        The default drops the failed step and everything downstream of it,
        keeping completed work. Subclasses can do better with the failure in
        hand; they must not resurrect steps that already ran.
        """

        failed = {step.id for step in plan.steps if step.status == "failed"}
        if not failed:
            return plan
        doomed = set(failed)
        changed = True
        while changed:
            changed = False
            for step in plan.steps:
                if step.id in doomed or step.done:
                    continue
                if set(step.depends_on) & doomed:
                    doomed.add(step.id)
                    changed = True
        kept = tuple(step for step in plan.steps if step.id not in doomed)
        return replace(plan, steps=kept, revision=plan.revision + 1)


class RuleBasedPlanner(Planner):
    """Deterministic, zero-dependency planner.

    Emits one step per offered Tool or Agent, ordered by the ``dependencies`` the
    resources themselves declare, so a callable that needs another runs after it.
    Arguments come from ``step_arguments`` when supplied, otherwise from the
    callable's input-schema defaults -- a rule-based planner cannot invent values,
    and guessing them silently would be worse than a schema-shaped default.
    """

    def __init__(self, *, step_arguments: Mapping[str, Mapping[str, Any]] | None = None) -> None:
        self.step_arguments = {key: dict(value) for key, value in (step_arguments or {}).items()}

    def plan(
        self,
        goal: str,
        resources: Sequence[ResourceDefinition],
        *,
        context: PolicyContext | None = None,
    ) -> Plan:
        callables = [item for item in resources if item.metadata.kind in ("tool", "agent")]
        offered = {item.metadata.id for item in callables}
        step_ids = {item.metadata.id: f"s{index + 1}" for index, item in enumerate(callables)}
        steps: list[PlanStep] = []
        for definition in callables:
            metadata = definition.metadata
            schema = definition.extras.get("input_schema")
            if metadata.kind == "agent":
                card = definition.extras.get("agent_card")
                if isinstance(card, Mapping):
                    schema = card.get("input_schema", schema)
            arguments = self.step_arguments.get(metadata.id)
            if arguments is None:
                arguments = default_arguments(schema) if isinstance(schema, Mapping) else {}
            steps.append(
                PlanStep(
                    id=step_ids[metadata.id],
                    description=f"{metadata.name}: {metadata.description}",
                    resource_id=metadata.id,
                    kind=metadata.kind,
                    arguments=dict(arguments),
                    expected_output=metadata.output_summary,
                    # Only declared dependencies that are actually on offer;
                    # an edge to a step that does not exist fails validation.
                    depends_on=tuple(
                        step_ids[dependency]
                        for dependency in metadata.dependencies
                        if dependency in offered and dependency != metadata.id
                    ),
                )
            )
        return Plan(goal=goal, steps=tuple(steps))


class LLMPlanner(Planner):
    """Ask a model for the decomposition, then validate before trusting it.

    Replies are cached by prompt hash, so a repeated run is deterministic and
    costs nothing. A malformed or unusable reply is not patched up: planning
    returns an empty plan and the caller decides, rather than executing a
    decomposition nobody verified.
    """

    def __init__(
        self,
        llm: LLMProvider,
        *,
        cache: dict[str, str] | None = None,
    ) -> None:
        self.llm = llm
        self.cache = cache if cache is not None else {}
        self.failures = 0

    def plan(
        self,
        goal: str,
        resources: Sequence[ResourceDefinition],
        *,
        context: PolicyContext | None = None,
    ) -> Plan:
        tools = [item for item in resources if item.metadata.kind == "tool"]
        if not tools:
            return Plan(goal=goal)
        reply = self._reply(goal, tools)
        if reply is None:
            return Plan(goal=goal)
        offered = {item.metadata.id for item in tools}
        steps = tuple(step for step in reply if step.resource_id in offered)
        return Plan(goal=goal, steps=steps)

    def replan(
        self,
        plan: Plan,
        resources: Sequence[ResourceDefinition],
        *,
        context: PolicyContext | None = None,
        failure: Mapping[str, Any] | None = None,
    ) -> Plan:
        """Re-plan the unfinished remainder, keeping completed steps intact."""

        completed = tuple(step for step in plan.steps if step.done)
        remaining_goal = plan.goal
        if failure:
            remaining_goal = (
                f"{plan.goal}\n\nA previous attempt failed: "
                f"{failure.get('message', '')} (resource {failure.get('resource', '')}). "
                "Plan the remaining work without that resource."
            )
        blocked = {step.resource_id for step in plan.steps if step.status == "failed"}
        usable = [item for item in resources if item.metadata.id not in blocked]
        revised = self.plan(remaining_goal, usable, context=context)
        if not revised.steps:
            return super().replan(plan, resources, context=context, failure=failure)
        done_ids = {step.id for step in completed}
        renamed = tuple(
            replace(step, id=step.id if step.id not in done_ids else f"{step.id}r{plan.revision}")
            for step in revised.steps
        )
        return Plan(goal=plan.goal, steps=completed + renamed, revision=plan.revision + 1)

    def _reply(self, goal: str, tools: Sequence[ResourceDefinition]) -> tuple[PlanStep, ...] | None:
        prompt = self._prompt(goal, tools)
        key = hashlib.sha256(
            json.dumps([_PLAN_SYSTEM, prompt], ensure_ascii=False).encode("utf-8")
        ).hexdigest()
        cached = self.cache.get(key)
        if cached is None:
            try:
                response = self.llm.complete(
                    [
                        ChatMessage(role="system", content=_PLAN_SYSTEM),
                        ChatMessage(role="user", content=prompt),
                    ]
                )
                cached = response.content
            except Exception:  # noqa: BLE001 - a failed plan is data, not a crash
                self.failures += 1
                cached = ""
            self.cache[key] = cached
        if not cached:
            return None
        return parse_plan_reply(cached)

    def _prompt(self, goal: str, tools: Sequence[ResourceDefinition]) -> str:
        lines = [f"Goal: {goal}", "", "Available tools:"]
        for definition in tools:
            metadata = definition.metadata
            schema = definition.extras.get("input_schema")
            lines.append(
                f"- {metadata.id}: {metadata.description} "
                f"(side_effect={metadata.side_effect}, input_schema="
                f"{json.dumps(schema if isinstance(schema, Mapping) else {}, ensure_ascii=False)})"
            )
        lines.append("")
        lines.append("Reply with the JSON plan.")
        return "\n".join(lines)


def parse_plan_reply(text: str) -> tuple[PlanStep, ...] | None:
    """Pull a step list out of a model reply, or None when unusable."""

    match = re.search(r"\{.*\}", text, re.DOTALL)
    if not match:
        return None
    try:
        parsed = json.loads(match.group(0))
    except json.JSONDecodeError:
        return None
    if not isinstance(parsed, dict):
        return None
    raw_steps = parsed.get("steps")
    if not isinstance(raw_steps, list):
        return None
    steps: list[PlanStep] = []
    for index, item in enumerate(raw_steps):
        if not isinstance(item, Mapping):
            continue
        data = dict(item)
        data.setdefault("id", f"s{index + 1}")
        # A model-supplied status would let a reply mark work as already done.
        data["status"] = "pending"
        data["result"] = None
        try:
            steps.append(PlanStep.from_dict(data))
        except ValueError:
            continue
    return tuple(steps) or None


def resources_by_id(definitions: Iterable[ResourceDefinition]) -> dict[str, ResourceDefinition]:
    return {definition.metadata.id: definition for definition in definitions}
