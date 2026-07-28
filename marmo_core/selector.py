"""Set selection: the SetSelector interface, the rule-based baseline, and the
first constrained solver (§15.3 案H).

Selection is a set problem, not a ranking problem (F-RETR-04): the output
must satisfy dependency closure, conflict exclusion, permission feasibility,
and budgets — and per §15.6 a selector is allowed to *not* pick anything
(``SelectionResult.status`` is ``selected`` / ``abstain`` / ``escalate``).

- ``RuleBasedSetSelector`` is the baseline: top-ranked results per kind,
  no constraint reasoning. It always returns ``selected`` (or an empty
  selected set), matching its v1 behavior.
- ``GreedyConstrainedSetSelector`` is 案H's first solver: score-ordered
  greedy over dependency-closed units with conflict, permission, and budget
  constraints.
- ``BeamSearchSetSelector`` (solver #2) widens the greedy frontier.
- ``BranchAndBoundSetSelector`` (solver #3) proves the Σu optimum by
  exhaustive search with an admissible upper bound, measuring how far the
  approximate solvers sit from the exact objective.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Mapping

from .models import KINDS, SearchResult, SelectionResult


DEFAULT_SET_LIMITS = {
    "memory": 1,
    "skill": 1,
    "tool": 1,
    "agent": 1,
}


@dataclass(frozen=True)
class SelectionContext:
    """Execution-side constraints a selector must respect (§15.3 案H).

    ``granted_permissions`` is the permission set of the calling context;
    with ``enforce_permissions`` on, resources requiring anything outside it
    are infeasible (and can surface as ``escalate``). ``budget_cost`` caps
    the summed ``cost_estimate`` of the selected set. ``task`` carries the
    task statement for selectors that reason over intent (LLM Set Selector);
    constraint-only solvers ignore it.
    """

    task: str = ""
    granted_permissions: tuple[str, ...] = ()
    per_kind_limits: Mapping[str, int] = field(default_factory=dict)
    max_resources: int = 8
    budget_cost: float | None = None
    min_score: float = 0.0
    min_relevance: float = 0.0
    enforce_permissions: bool = True


class SetSelector(ABC):
    """Set selection interface. Implementations are swappable (5.4)."""

    @abstractmethod
    def select(
        self, results: list[SearchResult], *, context: SelectionContext | None = None
    ) -> SelectionResult:
        """Choose a resource set from ranked results, or abstain/escalate."""


class RuleBasedSetSelector(SetSelector):
    """Baseline selector: top-ranked results per kind after active filters.

    Keeps the v1 contract: it never abstains or escalates, and applies no
    dependency/conflict reasoning — that is exactly what 案H solvers are
    measured against.
    """

    def __init__(self, default_limits: Mapping[str, int] | None = None, min_score: float = 0.0) -> None:
        self.default_limits = dict(default_limits or DEFAULT_SET_LIMITS)
        self.min_score = min_score

    def select(
        self,
        results: list[SearchResult],
        limits: Mapping[str, int] | None = None,
        *,
        context: SelectionContext | None = None,
    ) -> SelectionResult:
        effective_limits = dict(self.default_limits)
        if limits:
            effective_limits.update(limits)
        elif context is not None and context.per_kind_limits:
            effective_limits.update(context.per_kind_limits)
        min_score = max(self.min_score, context.min_score if context else 0.0)
        selected: list[SearchResult] = []
        counts: dict[str, int] = defaultdict(int)
        for result in results:
            kind = result.resource.metadata.kind
            if kind not in KINDS:
                continue
            if result.score < min_score:
                continue
            limit = effective_limits.get(kind, 0)
            if counts[kind] >= limit:
                continue
            selected.append(result)
            counts[kind] += 1
        if selected:
            parts = [f"{kind}={counts.get(kind, 0)}/{effective_limits.get(kind, 0)}" for kind in KINDS if effective_limits.get(kind, 0)]
            reason = "selected top-ranked resources per kind after active filters: " + ", ".join(parts)
        else:
            reason = "no resource met the active filters and minimum score"
        return SelectionResult(tuple(selected), reason)


class GreedyConstrainedSetSelector(SetSelector):
    """案H solver #1: constrained greedy over dependency-closed units.

    Each candidate is expanded to its dependency closure *within the
    candidate pool* (a dependency the retriever did not surface makes the
    candidate infeasible — the selector only sees what layer 1 handed it),
    and closures are visited in descending **unit utility** (the summed
    scores of the unit's members, matching the Σ u(i∈S) objective of §15.3)
    rather than per-candidate score: a specialist agent whose closure pulls
    in its tool and skill outranks a cheap standalone alternative, instead
    of being blocked by whichever single resource happened to score first.
    A unit is added when the whole unit is permission-feasible,
    conflict-free against the picked set, and fits the count/per-kind/cost
    budgets.

    Outcome mapping (§15.6): something picked → ``selected``; nothing
    feasible but at least one candidate was blocked *only* by missing
    permissions → ``escalate`` (a human can grant them); otherwise →
    ``abstain``.
    """

    def __init__(self, *, default_context: SelectionContext | None = None) -> None:
        self.default_context = default_context or SelectionContext()

    def select(
        self, results: list[SearchResult], *, context: SelectionContext | None = None
    ) -> SelectionResult:
        ctx = context or self.default_context
        pool = {result.resource.metadata.id: result for result in results}
        # min_score gates on the composite score; min_relevance gates on the
        # text-relevance component alone. The composite mixes cost/trust/
        # latency, so with semantic retrievers even an off-topic resource
        # keeps a sizeable composite score — intent matching needs its own
        # threshold (§15.6 abstain).
        candidates = [
            r
            for r in results
            if r.score >= ctx.min_score
            and float(r.components.get("relevance", 1.0)) >= ctx.min_relevance
        ]
        if not candidates:
            return SelectionResult(
                (), "no candidate met the minimum score and relevance thresholds", status="abstain"
            )

        granted = set(ctx.granted_permissions)
        picked: dict[str, SearchResult] = {}
        counts: dict[str, int] = defaultdict(int)
        total_cost = 0.0
        notes: list[str] = []
        permission_blocked: list[str] = []

        units: list[tuple[float, str, list[str]]] = []
        for candidate in candidates:
            cid = candidate.resource.metadata.id
            unit_ids, missing_dependency = _closure(cid, pool)
            if missing_dependency is not None:
                notes.append(f"{cid}: dependency {missing_dependency} not in candidate pool")
                continue
            utility = sum(pool[uid].score for uid in unit_ids)
            units.append((utility, cid, unit_ids))

        for _, cid, unit_ids in sorted(units, key=lambda item: (-item[0], item[1])):
            if cid in picked:
                continue
            unit = [pool[uid] for uid in unit_ids if uid not in picked]
            if not unit:
                continue
            missing_permissions = set()
            if ctx.enforce_permissions:
                for member in unit:
                    missing_permissions |= set(member.resource.metadata.required_permissions) - granted
            if missing_permissions:
                permission_blocked.append(cid)
                notes.append(f"{cid}: missing permissions {', '.join(sorted(missing_permissions))}")
                continue
            if _conflicts(unit, picked):
                notes.append(f"{cid}: conflicts with an already selected resource")
                continue
            unit_cost = sum(max(m.resource.metadata.cost_estimate, 0.0) for m in unit)
            if len(picked) + len(unit) > ctx.max_resources:
                notes.append(f"{cid}: would exceed max_resources={ctx.max_resources}")
                continue
            if ctx.budget_cost is not None and total_cost + unit_cost > ctx.budget_cost:
                notes.append(f"{cid}: would exceed budget_cost={ctx.budget_cost}")
                continue
            unit_kind_counts: dict[str, int] = defaultdict(int)
            for member in unit:
                unit_kind_counts[member.resource.metadata.kind] += 1
            over_limit_kind = next(
                (
                    kind
                    for kind, extra in unit_kind_counts.items()
                    if ctx.per_kind_limits.get(kind) is not None
                    and counts[kind] + extra > ctx.per_kind_limits[kind]
                ),
                None,
            )
            if over_limit_kind is not None:
                notes.append(f"{cid}: per-kind limit for {over_limit_kind} reached")
                continue
            for kind, extra in unit_kind_counts.items():
                counts[kind] += extra
            for member in unit:
                picked[member.resource.metadata.id] = member
            total_cost += unit_cost

        if picked:
            ordered = tuple(sorted(picked.values(), key=lambda r: (-r.score, r.resource.metadata.id)))
            reason = (
                f"greedy selected {len(ordered)} resource(s) with dependency closure, "
                f"conflict and budget constraints (cost={total_cost:g})"
            )
            if notes:
                reason += "; skipped: " + "; ".join(notes[:4])
            return SelectionResult(ordered, reason)
        if permission_blocked:
            reason = (
                "feasible only with permissions that were not granted: "
                + "; ".join(notes[:4])
                + "; a human can grant them and re-run"
            )
            return SelectionResult((), reason, status="escalate")
        reason = "no feasible set under dependency, conflict, and budget constraints"
        if notes:
            reason += ": " + "; ".join(notes[:4])
        return SelectionResult((), reason, status="abstain")


class BeamSearchSetSelector(SetSelector):
    """案H solver #2: Beam search over dependency-closed units.

    Explores the combinatorics of selecting units (resource + its dependency closure)
    to maximize total set utility within constraints. This avoids local optima
    where the greedy selector might pick an early unit that consumes too much budget
    or conflicts with a better combination of later units.
    """

    def __init__(self, beam_width: int = 5, *, default_context: SelectionContext | None = None) -> None:
        self.beam_width = beam_width
        self.default_context = default_context or SelectionContext()

    def select(
        self, results: list[SearchResult], *, context: SelectionContext | None = None
    ) -> SelectionResult:
        ctx = context or self.default_context
        pool = {result.resource.metadata.id: result for result in results}

        candidates = [
            r
            for r in results
            if r.score >= ctx.min_score
            and float(r.components.get("relevance", 1.0)) >= ctx.min_relevance
        ]
        if not candidates:
            return SelectionResult(
                (), "no candidate met the minimum score and relevance thresholds", status="abstain"
            )

        granted = set(ctx.granted_permissions)
        notes: list[str] = []
        permission_blocked: list[str] = []

        units: list[tuple[float, str, list[str]]] = []
        for candidate in candidates:
            cid = candidate.resource.metadata.id
            unit_ids, missing_dependency = _closure(cid, pool)
            if missing_dependency is not None:
                notes.append(f"{cid}: dependency {missing_dependency} not in candidate pool")
                continue
            utility = sum(pool[uid].score for uid in unit_ids)
            units.append((utility, cid, unit_ids))

        ordered_units = sorted(units, key=lambda item: (-item[0], item[1]))

        # State: picked_ids -> (utility, cost, counts)
        beam: dict[frozenset[str], tuple[float, float, dict[str, int]]] = {
            frozenset(): (0.0, 0.0, defaultdict(int))
        }

        for _, cid, unit_ids in ordered_units:
            next_beam = dict(beam)
            unit_members = [pool[uid] for uid in unit_ids]

            unit_cost = sum(max(m.resource.metadata.cost_estimate, 0.0) for m in unit_members)
            unit_missing_perms = set()
            if ctx.enforce_permissions:
                for m in unit_members:
                    unit_missing_perms |= set(m.resource.metadata.required_permissions) - granted

            if unit_missing_perms:
                permission_blocked.append(cid)
                notes.append(f"{cid}: missing permissions {', '.join(sorted(unit_missing_perms))}")
                continue

            unit_counts: dict[str, int] = defaultdict(int)
            for m in unit_members:
                unit_counts[m.resource.metadata.kind] += 1

            for state_ids, (state_util, state_cost, state_counts) in beam.items():
                if any(uid in state_ids for uid in unit_ids):
                    continue

                if len(state_ids) + len(unit_ids) > ctx.max_resources:
                    continue

                if ctx.budget_cost is not None and state_cost + unit_cost > ctx.budget_cost:
                    continue

                limit_exceeded = False
                for kind, extra in unit_counts.items():
                    if ctx.per_kind_limits.get(kind) is not None:
                        if state_counts[kind] + extra > ctx.per_kind_limits[kind]:
                            limit_exceeded = True
                            break
                if limit_exceeded:
                    continue

                picked_results = {uid: pool[uid] for uid in state_ids}
                if _conflicts(unit_members, picked_results):
                    continue

                new_ids = state_ids | frozenset(unit_ids)
                new_util = state_util + sum(pool[uid].score for uid in unit_ids)
                new_cost = state_cost + unit_cost
                new_counts = state_counts.copy()
                for kind, extra in unit_counts.items():
                    new_counts[kind] += extra

                if new_ids not in next_beam or new_util > next_beam[new_ids][0]:
                    next_beam[new_ids] = (new_util, new_cost, new_counts)

            if len(next_beam) > self.beam_width:
                sorted_states = sorted(next_beam.items(), key=lambda x: (-x[1][0], len(x[0])))
                next_beam = dict(sorted_states[:self.beam_width])
            beam = next_beam

        best_state_ids = None
        best_util = -1.0
        best_cost = 0.0
        for state_ids, (util, cost, _) in beam.items():
            if state_ids and util > best_util:
                best_state_ids = state_ids
                best_util = util
                best_cost = cost

        if best_state_ids:
            picked = [pool[uid] for uid in best_state_ids]
            ordered = tuple(sorted(picked, key=lambda r: (-r.score, r.resource.metadata.id)))
            reason = (
                f"beam search (width={self.beam_width}) selected {len(ordered)} resource(s) with dependency closure, "
                f"conflict and budget constraints (cost={best_cost:g}, utility={best_util:g})"
            )
            if notes:
                reason += "; skipped: " + "; ".join(notes[:4])
            return SelectionResult(ordered, reason)

        if permission_blocked:
            reason = (
                "feasible only with permissions that were not granted: "
                + "; ".join(notes[:4])
                + "; a human can grant them and re-run"
            )
            return SelectionResult((), reason, status="escalate")

        reason = "no feasible set under dependency, conflict, and budget constraints"
        if notes:
            reason += ": " + "; ".join(notes[:4])
        return SelectionResult((), reason, status="abstain")


class BranchAndBoundSetSelector(SetSelector):
    """案H solver #3: exact branch-and-bound over dependency-closed units.

    Depth-first include/exclude search over units (a candidate plus its
    dependency closure; union semantics, so members shared between units are
    counted once — the same family of sets the greedy solver can reach) with
    an admissible upper bound: current utility plus the summed utilities of
    the units not yet branched on. Subtrees that cannot beat the incumbent
    are pruned. Within the node budget the returned set is the exact
    maximizer of Σ u(i∈S) under the dependency-closure, conflict,
    permission, and budget constraints the approximate solvers enforce; the
    reason string records whether optimality was proven or the node budget
    truncated the search. At post-retrieval scale (50–200 candidates, tight
    per-kind limits) the search is small; ``max_nodes`` is a safety valve,
    not an expected limit.
    """

    def __init__(
        self, *, max_nodes: int = 100_000, default_context: SelectionContext | None = None
    ) -> None:
        self.max_nodes = max_nodes
        self.default_context = default_context or SelectionContext()

    def select(
        self, results: list[SearchResult], *, context: SelectionContext | None = None
    ) -> SelectionResult:
        ctx = context or self.default_context
        pool = {result.resource.metadata.id: result for result in results}

        candidates = [
            r
            for r in results
            if r.score >= ctx.min_score
            and float(r.components.get("relevance", 1.0)) >= ctx.min_relevance
        ]
        if not candidates:
            return SelectionResult(
                (), "no candidate met the minimum score and relevance thresholds", status="abstain"
            )

        granted = set(ctx.granted_permissions)
        notes: list[str] = []
        permission_blocked: list[str] = []

        units: list[tuple[float, str, list[str]]] = []
        for candidate in candidates:
            cid = candidate.resource.metadata.id
            unit_ids, missing_dependency = _closure(cid, pool)
            if missing_dependency is not None:
                notes.append(f"{cid}: dependency {missing_dependency} not in candidate pool")
                continue
            missing_permissions = set()
            if ctx.enforce_permissions:
                for uid in unit_ids:
                    missing_permissions |= (
                        set(pool[uid].resource.metadata.required_permissions) - granted
                    )
            if missing_permissions:
                permission_blocked.append(cid)
                notes.append(f"{cid}: missing permissions {', '.join(sorted(missing_permissions))}")
                continue
            utility = sum(pool[uid].score for uid in unit_ids)
            units.append((utility, cid, unit_ids))

        ordered_units = sorted(units, key=lambda item: (-item[0], item[1]))
        # Admissible bound: the utility still reachable from unit i onward can
        # never exceed the summed (full, non-overlap-corrected) utilities of
        # the remaining units.
        suffix_bound = [0.0] * (len(ordered_units) + 1)
        for index in range(len(ordered_units) - 1, -1, -1):
            suffix_bound[index] = suffix_bound[index + 1] + max(ordered_units[index][0], 0.0)

        best_ids: tuple[str, ...] = ()
        best_utility = 0.0
        best_cost = 0.0
        nodes = 0
        truncated = False

        def dfs(
            index: int,
            picked: dict[str, SearchResult],
            counts: dict[str, int],
            cost: float,
            utility: float,
        ) -> None:
            nonlocal best_ids, best_utility, best_cost, nodes, truncated
            if picked and utility > best_utility + 1e-12:
                best_ids = tuple(picked)
                best_utility = utility
                best_cost = cost
            if index == len(ordered_units):
                return
            if truncated or nodes >= self.max_nodes:
                truncated = True
                return
            nodes += 1
            if utility + suffix_bound[index] <= best_utility + 1e-12:
                return
            _, _, unit_ids = ordered_units[index]
            new_ids = [uid for uid in unit_ids if uid not in picked]
            if new_ids:
                new_members = [pool[uid] for uid in new_ids]
                new_cost = sum(max(m.resource.metadata.cost_estimate, 0.0) for m in new_members)
                new_counts: dict[str, int] = defaultdict(int)
                for member in new_members:
                    new_counts[member.resource.metadata.kind] += 1
                feasible = (
                    len(picked) + len(new_ids) <= ctx.max_resources
                    and (ctx.budget_cost is None or cost + new_cost <= ctx.budget_cost)
                    and not any(
                        ctx.per_kind_limits.get(kind) is not None
                        and counts[kind] + extra > ctx.per_kind_limits[kind]
                        for kind, extra in new_counts.items()
                    )
                    and not _conflicts(new_members, picked)
                )
                if feasible:
                    for member in new_members:
                        picked[member.resource.metadata.id] = member
                    for kind, extra in new_counts.items():
                        counts[kind] += extra
                    dfs(index + 1, picked, counts, cost + new_cost, utility + sum(m.score for m in new_members))
                    for member in new_members:
                        del picked[member.resource.metadata.id]
                    for kind, extra in new_counts.items():
                        counts[kind] -= extra
            dfs(index + 1, picked, counts, cost, utility)

        dfs(0, {}, defaultdict(int), 0.0, 0.0)

        if best_ids:
            picked_results = [pool[uid] for uid in best_ids]
            ordered = tuple(sorted(picked_results, key=lambda r: (-r.score, r.resource.metadata.id)))
            proof = "node budget reached, best found" if truncated else "proven optimal"
            reason = (
                f"branch-and-bound selected {len(ordered)} resource(s) over {nodes} node(s), "
                f"{proof} for Σu under dependency closure, conflict and budget constraints "
                f"(cost={best_cost:g}, utility={best_utility:g})"
            )
            if notes:
                reason += "; skipped: " + "; ".join(notes[:4])
            return SelectionResult(ordered, reason)

        if permission_blocked:
            reason = (
                "feasible only with permissions that were not granted: "
                + "; ".join(notes[:4])
                + "; a human can grant them and re-run"
            )
            return SelectionResult((), reason, status="escalate")

        reason = "no feasible set under dependency, conflict, and budget constraints"
        if notes:
            reason += ": " + "; ".join(notes[:4])
        return SelectionResult((), reason, status="abstain")


def _closure(resource_id: str, pool: Mapping[str, SearchResult]) -> tuple[list[str], str | None]:
    """Dependency closure of ``resource_id`` inside the candidate pool.

    Returns (ordered ids, None) or ([], missing_id) when a dependency is not
    in the pool (including transitively).
    """

    ordered: list[str] = []
    seen: set[str] = set()
    stack = [resource_id]
    while stack:
        current = stack.pop()
        if current in seen:
            continue
        seen.add(current)
        result = pool.get(current)
        if result is None:
            return [], current
        ordered.append(current)
        stack.extend(result.resource.metadata.dependencies)
    return ordered, None


def _conflicts(unit: list[SearchResult], picked: Mapping[str, SearchResult]) -> bool:
    """True when the unit conflicts internally or with the picked set."""

    unit_ids = {member.resource.metadata.id for member in unit}
    all_ids = unit_ids | set(picked)
    for member in list(unit) + list(picked.values()):
        for conflict in member.resource.metadata.conflicts_with:
            if conflict in all_ids and conflict != member.resource.metadata.id:
                if member.resource.metadata.id in unit_ids or conflict in unit_ids:
                    return True
    return False
