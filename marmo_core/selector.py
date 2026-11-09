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
- ``TopKSetSelector`` is the global Top-K baseline; its optional
  post-processing (add dependencies, drop conflicts, escalate on missing
  permissions) is the "rank, then repair" alternative to the integrated
  solvers. ``RepairingSetSelector`` applies the same repair to any other
  selector's output.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections import defaultdict
from decimal import Decimal
from dataclasses import dataclass, field
from typing import Callable, Iterable, Mapping

from .models import KINDS, SearchResult, SelectionResult
from .routing_contracts import TaskSpec


# One Memory, Skill, and Agent keep the compiled context small, but real goals
# routinely need more than one Tool (list files, then read one), so the model
# gets a few tools to choose from; each one still passes the Policy Gateway.
DEFAULT_SET_LIMITS = {
    "memory": 1,
    "skill": 1,
    "tool": 3,
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
    task_spec: TaskSpec | None = None
    context_token_budget: int | None = None


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

    It does honour both floors in ``SelectionContext``: ``min_score`` on the
    composite score and ``min_relevance`` on the text-relevance component.
    The relevance floor used to be read by every solver *except* this one,
    which is the selector the Kernel uses by default — so the one gate that
    can keep an unrelated resource out of the model's context did nothing in
    the default configuration. Both default to 0.0: with the relevance
    component now absolute a floor is finally meaningful, but on the bundled
    1,000-skill corpus a value high enough to reject every off-topic goal
    also rejects real matches, so the number belongs to the deployment, not
    to the library.
    """

    def __init__(
        self,
        default_limits: Mapping[str, int] | None = None,
        min_score: float = 0.0,
        min_relevance: float = 0.0,
    ) -> None:
        self.default_limits = dict(default_limits or DEFAULT_SET_LIMITS)
        self.min_score = min_score
        self.min_relevance = min_relevance

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
        min_relevance = max(self.min_relevance, context.min_relevance if context else 0.0)
        selected: list[SearchResult] = []
        counts: dict[str, int] = defaultdict(int)
        total_cost = Decimal(0)
        budget = Decimal(str(context.budget_cost)) if context and context.budget_cost is not None else None
        for result in results:
            kind = result.resource.metadata.kind
            if kind not in KINDS:
                continue
            if result.score < min_score:
                continue
            if float(result.components.get("relevance", 1.0)) < min_relevance:
                continue
            limit = effective_limits.get(kind, 0)
            if counts[kind] >= limit:
                continue
            cost = _resource_cost(result)
            if budget is not None and total_cost + cost > budget:
                continue
            selected.append(result)
            counts[kind] += 1
            total_cost += cost
        if selected:
            parts = [f"{kind}={counts.get(kind, 0)}/{effective_limits.get(kind, 0)}" for kind in KINDS if effective_limits.get(kind, 0)]
            reason = "selected top-ranked resources per kind after active filters: " + ", ".join(parts)
        else:
            reason = "no resource met the active filters, minimum score, and minimum relevance"
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

    Outcome mapping (§15.6), shared by the beam and branch-and-bound
    solvers: a unit blocked *only* by missing permissions escalates when
    nothing else is feasible, or when its utility beats every unit in the
    feasible set and it fits the budgets on its own (a human can grant the
    permissions); otherwise something picked → ``selected``, nothing picked
    → ``abstain``.
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

        picked: dict[str, SearchResult] = {}
        counts: dict[str, int] = defaultdict(int)
        total_cost = Decimal(0)
        budget = Decimal(str(ctx.budget_cost)) if ctx.budget_cost is not None else None
        notes: list[str] = []
        units, blocked = _build_units(candidates, pool, ctx, notes)

        for unit_entry in units:
            cid = unit_entry.root
            if cid in picked:
                continue
            unit = [pool[uid] for uid in unit_entry.ids if uid not in picked]
            if not unit:
                continue
            if _conflicts(unit, picked):
                notes.append(f"{cid}: conflicts with an already selected resource")
                continue
            unit_cost = _total_cost(unit)
            if len(picked) + len(unit) > ctx.max_resources:
                notes.append(f"{cid}: would exceed max_resources={ctx.max_resources}")
                continue
            if budget is not None and total_cost + unit_cost > budget:
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

        escalation = _permission_escalation(set(picked), units, blocked, pool, ctx, notes)
        if escalation is not None:
            return escalation
        if picked:
            ordered = tuple(sorted(picked.values(), key=lambda r: (-r.score, r.resource.metadata.id)))
            reason = (
                f"greedy selected {len(ordered)} resource(s) with dependency closure, "
                f"conflict and budget constraints (cost={total_cost:g})"
            )
            if notes:
                reason += "; skipped: " + "; ".join(notes[:4])
            return SelectionResult(ordered, reason)
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

        notes: list[str] = []
        units, blocked = _build_units(candidates, pool, ctx, notes)

        # State: picked_ids -> (utility, cost, counts)
        beam: dict[frozenset[str], tuple[float, Decimal, dict[str, int]]] = {
            frozenset(): (0.0, Decimal(0), defaultdict(int))
        }
        budget = Decimal(str(ctx.budget_cost)) if ctx.budget_cost is not None else None

        for unit_entry in units:
            unit_ids = unit_entry.ids
            next_beam = dict(beam)
            unit_members = [pool[uid] for uid in unit_ids]
            unit_cost = _total_cost(unit_members)

            unit_counts: dict[str, int] = defaultdict(int)
            for m in unit_members:
                unit_counts[m.resource.metadata.kind] += 1

            for state_ids, (state_util, state_cost, state_counts) in beam.items():
                if any(uid in state_ids for uid in unit_ids):
                    continue

                if len(state_ids) + len(unit_ids) > ctx.max_resources:
                    continue

                if budget is not None and state_cost + unit_cost > budget:
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
        best_cost = Decimal(0)
        for state_ids, (util, cost, _) in beam.items():
            if state_ids and util > best_util:
                best_state_ids = state_ids
                best_util = util
                best_cost = cost

        escalation = _permission_escalation(set(best_state_ids or ()), units, blocked, pool, ctx, notes)
        if escalation is not None:
            return escalation
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

        notes: list[str] = []
        ordered_units, blocked = _build_units(candidates, pool, ctx, notes)
        # Admissible bound: the utility still reachable from unit i onward can
        # never exceed the summed (full, non-overlap-corrected) utilities of
        # the remaining units.
        suffix_bound = [0.0] * (len(ordered_units) + 1)
        for index in range(len(ordered_units) - 1, -1, -1):
            suffix_bound[index] = suffix_bound[index + 1] + max(ordered_units[index].utility, 0.0)

        best_ids: tuple[str, ...] = ()
        best_utility = 0.0
        best_cost = Decimal(0)
        budget = Decimal(str(ctx.budget_cost)) if ctx.budget_cost is not None else None
        nodes = 0
        truncated = False

        def dfs(
            index: int,
            picked: dict[str, SearchResult],
            counts: dict[str, int],
            cost: Decimal,
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
            unit_ids = ordered_units[index].ids
            new_ids = [uid for uid in unit_ids if uid not in picked]
            if new_ids:
                new_members = [pool[uid] for uid in new_ids]
                new_cost = _total_cost(new_members)
                new_counts: dict[str, int] = defaultdict(int)
                for member in new_members:
                    new_counts[member.resource.metadata.kind] += 1
                feasible = (
                    len(picked) + len(new_ids) <= ctx.max_resources
                    and (budget is None or cost + new_cost <= budget)
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

        dfs(0, {}, defaultdict(int), Decimal(0), 0.0)

        escalation = _permission_escalation(set(best_ids), ordered_units, blocked, pool, ctx, notes)
        if escalation is not None:
            return escalation
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

        reason = "no feasible set under dependency, conflict, and budget constraints"
        if notes:
            reason += ": " + "; ".join(notes[:4])
        return SelectionResult((), reason, status="abstain")


class TopKSetSelector(SetSelector):
    """Global Top-K baseline with optional constraint post-processing.

    Takes the ``k`` highest-ranked candidates that pass the context's score
    and relevance floors, regardless of kind. With every post-processing
    switch off it is the plain Top-K baseline: it never escalates, and it
    abstains only when no candidate passes the floors.

    The switches turn it into the simplest constraint-aware alternative to
    the integrated solvers — rank first, then repair:

    - ``expand_dependencies`` adds each picked candidate's dependency closure
      from the candidate pool; a candidate whose closure is not in the pool
      is dropped.
    - ``drop_conflicts`` walks the set in score order and drops any member
      that conflicts with a member already kept; when ``expand_dependencies``
      is also on, members whose dependencies were dropped go too.
    - ``check_permissions`` escalates when a remaining member needs a
      permission the context did not grant.

    The repair is the same one ``RepairingSetSelector`` applies to any other
    selector's output.
    """

    def __init__(
        self,
        k: int,
        *,
        expand_dependencies: bool = False,
        drop_conflicts: bool = False,
        check_permissions: bool = False,
    ) -> None:
        if k < 1:
            raise ValueError("k must be at least 1")
        self.k = k
        self.expand_dependencies = expand_dependencies
        self.drop_conflicts = drop_conflicts
        self.check_permissions = check_permissions

    def select(
        self, results: list[SearchResult], *, context: SelectionContext | None = None
    ) -> SelectionResult:
        ctx = context or SelectionContext()
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
        picked = candidates[: self.k]
        return _repair_selection(
            picked,
            results,
            ctx,
            expand_dependencies=self.expand_dependencies,
            drop_conflicts=self.drop_conflicts,
            check_permissions=self.check_permissions,
            label=f"top-{self.k}",
        )


class RepairingSetSelector(SetSelector):
    """Apply the ``TopKSetSelector`` post-processing to another selector's set.

    Only a ``selected`` outcome with at least one resource is repaired;
    abstain and escalate pass through unchanged. The repair can only use
    candidates from the pool the wrapped selector was given.
    """

    def __init__(
        self,
        inner: SetSelector,
        *,
        expand_dependencies: bool = True,
        drop_conflicts: bool = True,
        check_permissions: bool = True,
    ) -> None:
        self.inner = inner
        self.expand_dependencies = expand_dependencies
        self.drop_conflicts = drop_conflicts
        self.check_permissions = check_permissions

    def select(
        self, results: list[SearchResult], *, context: SelectionContext | None = None
    ) -> SelectionResult:
        ctx = context or SelectionContext()
        selection = self.inner.select(results, context=ctx)
        if selection.status != "selected" or not selection.results:
            return selection
        return _repair_selection(
            list(selection.results),
            results,
            ctx,
            expand_dependencies=self.expand_dependencies,
            drop_conflicts=self.drop_conflicts,
            check_permissions=self.check_permissions,
            label="repaired selection",
        )


def _repair_selection(
    picked: list[SearchResult],
    pool_results: list[SearchResult],
    ctx: SelectionContext,
    *,
    expand_dependencies: bool,
    drop_conflicts: bool,
    check_permissions: bool,
    label: str,
) -> SelectionResult:
    """Dependency expansion, conflict dropping, and the permission check, in that order."""

    pool = {result.resource.metadata.id: result for result in pool_results}
    for result in picked:
        pool.setdefault(result.resource.metadata.id, result)
    notes: list[str] = []
    kept: dict[str, SearchResult] = {}
    for result in picked:
        rid = result.resource.metadata.id
        if not expand_dependencies:
            kept.setdefault(rid, result)
            continue
        unit_ids, missing = _closure(rid, pool)
        if missing is not None:
            notes.append(f"{rid}: dependency {missing} not in candidate pool")
            continue
        for uid in unit_ids:
            kept.setdefault(uid, pool[uid])

    if drop_conflicts:
        survivors: dict[str, SearchResult] = {}
        for result in sorted(kept.values(), key=lambda r: (-r.score, r.resource.metadata.id)):
            if _conflicts([result], survivors):
                notes.append(f"{result.resource.metadata.id}: conflicts with a higher-ranked member")
                continue
            survivors[result.resource.metadata.id] = result
        kept = survivors
        if expand_dependencies:
            changed = True
            while changed:
                changed = False
                for rid, result in list(kept.items()):
                    if any(dependency not in kept for dependency in result.resource.metadata.dependencies):
                        del kept[rid]
                        notes.append(f"{rid}: a dependency was dropped")
                        changed = True

    if not kept:
        reason = f"{label}: nothing left after post-processing"
        if notes:
            reason += ": " + "; ".join(notes[:4])
        return SelectionResult((), reason, status="abstain")

    if check_permissions and ctx.enforce_permissions:
        granted = set(ctx.granted_permissions)
        missing_permissions = sorted(
            {
                permission
                for result in kept.values()
                for permission in result.resource.metadata.required_permissions
                if permission not in granted
            }
        )
        if missing_permissions:
            return SelectionResult(
                (),
                f"{label} needs permissions that were not granted: "
                + ", ".join(missing_permissions)
                + "; a human can grant them and re-run",
                status="escalate",
            )

    ordered = tuple(sorted(kept.values(), key=lambda r: (-r.score, r.resource.metadata.id)))
    reason = f"{label}: {len(ordered)} resource(s)"
    if notes:
        reason += "; post-processing: " + "; ".join(notes[:4])
    return SelectionResult(ordered, reason)


@dataclass(frozen=True)
class _Unit:
    """A candidate plus its dependency closure inside the candidate pool."""

    utility: float
    root: str
    ids: tuple[str, ...]
    missing_permissions: frozenset[str] = frozenset()


def _build_units(
    candidates: list[SearchResult],
    pool: Mapping[str, SearchResult],
    ctx: SelectionContext,
    notes: list[str],
) -> tuple[list[_Unit], list[_Unit]]:
    """Split candidates into permission-feasible and permission-blocked units.

    Both lists are in descending unit utility. A candidate whose closure
    leaves the pool is in neither and is recorded in ``notes``.
    """

    granted = set(ctx.granted_permissions)
    units: list[_Unit] = []
    blocked: list[_Unit] = []
    for candidate in candidates:
        cid = candidate.resource.metadata.id
        unit_ids, missing_dependency = _closure(cid, pool)
        if missing_dependency is not None:
            notes.append(f"{cid}: dependency {missing_dependency} not in candidate pool")
            continue
        missing_permissions: set[str] = set()
        if ctx.enforce_permissions:
            for uid in unit_ids:
                missing_permissions |= set(pool[uid].resource.metadata.required_permissions) - granted
        utility = sum(pool[uid].score for uid in unit_ids)
        unit = _Unit(utility, cid, tuple(unit_ids), frozenset(missing_permissions))
        if missing_permissions:
            notes.append(f"{cid}: missing permissions {', '.join(sorted(missing_permissions))}")
            blocked.append(unit)
        else:
            units.append(unit)
    return sorted(units, key=_unit_order), sorted(blocked, key=_unit_order)


def _unit_order(unit: _Unit) -> tuple[float, str]:
    return (-unit.utility, unit.root)


def _permission_escalation(
    picked_ids: set[str],
    units: list[_Unit],
    blocked: list[_Unit],
    pool: Mapping[str, SearchResult],
    ctx: SelectionContext,
    notes: list[str],
) -> SelectionResult | None:
    """Escalate when missing permissions keep out the best unit (§15.6).

    With nothing feasible, any permission-blocked unit escalates. With a
    feasible set, a blocked unit escalates only when its utility beats every
    unit inside that set and it would fit the budgets on its own: the best
    match needs a grant, so selecting the runner-up instead would report a
    worse set as a clean success. A blocked unit that merely ranks below the
    picked ones stays a skipped note.
    """

    if not blocked:
        return None
    if not picked_ids:
        reason = (
            "feasible only with permissions that were not granted: "
            + "; ".join(notes[:4])
            + "; a human can grant them and re-run"
        )
        return SelectionResult((), reason, status="escalate")
    best_picked = max((unit.utility for unit in units if set(unit.ids) <= picked_ids), default=0.0)
    for unit in blocked:
        if unit.utility <= best_picked:
            return None
        if not _fits_alone(unit, pool, ctx):
            continue
        missing = tuple(sorted(unit.missing_permissions))
        reason = (
            f"{unit.root} outranks the feasible set (utility {unit.utility:g} > {best_picked:g}) "
            f"but needs permissions that were not granted: {', '.join(missing)}; "
            f"without them the set would be {', '.join(sorted(picked_ids))}; "
            "a human can grant them and re-run"
        )
        return SelectionResult((), reason, status="escalate", missing_permissions=missing)
    return None


def _fits_alone(unit: _Unit, pool: Mapping[str, SearchResult], ctx: SelectionContext) -> bool:
    """Could ``unit`` be selected on its own once its permissions are granted?"""

    members = [pool[uid] for uid in unit.ids]
    if len(members) > ctx.max_resources:
        return False
    if ctx.budget_cost is not None and _total_cost(members) > Decimal(str(ctx.budget_cost)):
        return False
    kind_counts: dict[str, int] = defaultdict(int)
    for member in members:
        kind_counts[member.resource.metadata.kind] += 1
    if any(
        ctx.per_kind_limits.get(kind) is not None and count > ctx.per_kind_limits[kind]
        for kind, count in kind_counts.items()
    ):
        return False
    return not _conflicts(members, {})


def _enforce_set_constraints(
    selection: SelectionResult,
    resolve: Callable[[str], SearchResult | str],
) -> tuple[SelectionResult, tuple[dict[str, str], ...]]:
    """Make a selected set dependency-closed and conflict-free (F-RETR-04).

    Not every selector reasons about dependencies and conflicts: the
    rule-based default and the LLM selector do not, so the Kernel applies
    this to every ``selected`` outcome. Members are visited in descending
    score. Each is kept together with its transitive dependencies, found
    first among the members already kept and otherwise through ``resolve``,
    which returns the dependency as a ``SearchResult`` or a short reason it
    is unavailable. A member is dropped, never silently, when a dependency
    is unavailable or when its unit conflicts with what is already kept.

    Returns the repaired selection and the dropped members as
    ``{"resource": identity, "reason": ...}``. A set that loses every member
    becomes ``abstain``; abstain and escalate pass through unchanged.
    """

    if selection.status != "selected" or not selection.results:
        return selection, ()
    selected_identities = {result.resource.identity for result in selection.results}
    kept: dict[str, SearchResult] = {}
    dropped: list[dict[str, str]] = []
    added: list[str] = []
    for member in sorted(selection.results, key=lambda r: (-r.score, r.resource.identity)):
        if member.resource.identity in kept:
            continue
        unit, problem = _dependency_unit(member, kept, resolve)
        if problem is None and _conflicts(unit, {r.resource.metadata.id: r for r in kept.values()}):
            problem = "conflicts with a higher-ranked member of the set"
        if problem is not None:
            dropped.append({"resource": member.resource.identity, "reason": problem})
            continue
        for result in unit:
            identity = result.resource.identity
            if identity not in kept:
                kept[identity] = result
                if identity not in selected_identities:
                    added.append(identity)

    if not added and not dropped:
        return selection, ()
    notes = []
    if added:
        notes.append("added dependencies " + ", ".join(added))
    notes.extend(f"dropped {item['resource']} ({item['reason']})" for item in dropped)
    reason = f"{selection.reason}; constraint check: " + "; ".join(notes)
    if not kept:
        return SelectionResult((), reason, status="abstain"), tuple(dropped)
    ordered = tuple(sorted(kept.values(), key=lambda r: (-r.score, r.resource.identity)))
    return SelectionResult(ordered, reason, missing_permissions=selection.missing_permissions), tuple(dropped)


def _dependency_unit(
    member: SearchResult,
    kept: Mapping[str, SearchResult],
    resolve: Callable[[str], SearchResult | str],
) -> tuple[list[SearchResult], str | None]:
    """``member`` plus the transitive dependencies ``kept`` does not already hold."""

    unit = [member]
    stack = list(member.resource.metadata.dependencies)
    while stack:
        reference = stack.pop()
        if _find_reference(reference, kept.values()) or _find_reference(reference, unit):
            continue
        resolved = resolve(reference)
        if isinstance(resolved, str):
            return [], f"dependency {reference} {resolved}"
        if any(result.resource.identity == resolved.resource.identity for result in unit):
            continue
        unit.append(resolved)
        stack.extend(resolved.resource.metadata.dependencies)
    return unit, None


def _find_reference(reference: str, results: Iterable[SearchResult]) -> SearchResult | None:
    """The result a dependency reference names: ``id@version`` exactly, a bare ``id`` by id."""

    for result in results:
        metadata = result.resource.metadata
        if reference == (result.resource.identity if "@" in reference else metadata.id):
            return result
    return None


def _resource_cost(result: SearchResult) -> Decimal:
    return Decimal(str(max(result.resource.metadata.cost_estimate, 0.0)))


def _total_cost(results: Iterable[SearchResult]) -> Decimal:
    return sum((_resource_cost(result) for result in results), Decimal(0))


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
