"""Coverage-based set selection: cover each sub-task once, stop when nothing is gained.

The constrained solvers in ``selector.py`` maximize Σ u(i∈S), the summed
scores of the selected units. A sum rewards every additional relevant-looking
member, so it cannot say how many resources a goal needs: two near-duplicate
search tools add twice the utility of one, and the solvers keep adding until
a count limit stops them. On ToolRet, a fixed top-3 averages Set F1 0.12
while gold sets range from one to seven tools.

``CoverageSetSelector`` instead maximizes a facility-location objective over
the goal's facets (the ``facet.<i>`` relevance components that
``DecomposedRetriever`` attaches; without them the goal is one facet scored
by ``relevance``):

    F(S) = Σ_f w_f · max_{i ∈ S} r_f(i)

A member adds value only for the facets it serves better than what is
already selected, so a second tool for an already-covered sub-task adds
nothing, and selection stops when the best feasible unit's marginal gain
falls below ``min_gain``. F is monotone submodular, so greedy selection by
marginal gain is the standard (1 - 1/e)-approximate maximizer under a
cardinality limit. Units, feasibility, and the abstain / escalate outcomes
are the same as for the greedy constrained solver: a candidate is taken
together with its dependency closure inside the pool, and conflicts,
permissions, per-kind limits, ``max_resources``, and ``budget_cost`` are
enforced.
"""

from __future__ import annotations

from collections import defaultdict
from decimal import Decimal
from typing import Mapping

from .decomposition import FACET_PREFIX
from .models import SearchResult, SelectionResult
from .selector import (
    SelectionContext,
    SetSelector,
    _build_units,
    _conflicts,
    _permission_escalation,
    _total_cost,
    _Unit,
)


class CoverageSetSelector(SetSelector):
    """Greedy facility-location selection over the goal's facets.

    ``min_gain`` is the smallest marginal coverage gain worth another unit;
    the first unit is always taken when one is feasible (the relevance
    floors decide whether anything qualifies at all). ``goal_weight``
    weights the full goal's facet (``facet.0``) against the sub-task facets,
    which weigh 1.0 each.
    """

    def __init__(
        self,
        *,
        min_gain: float = 0.1,
        goal_weight: float = 1.0,
        default_context: SelectionContext | None = None,
    ) -> None:
        if min_gain < 0.0:
            raise ValueError("min_gain must be non-negative")
        if goal_weight < 0.0:
            raise ValueError("goal_weight must be non-negative")
        self.min_gain = min_gain
        self.goal_weight = goal_weight
        self.default_context = default_context or SelectionContext()

    def select(
        self, results: list[SearchResult], *, context: SelectionContext | None = None
    ) -> SelectionResult:
        ctx = context or self.default_context
        pool = {result.resource.metadata.id: result for result in results}
        candidates = [
            r
            for r in results
            if r.score >= ctx.min_score and float(r.components.get("relevance", 1.0)) >= ctx.min_relevance
        ]
        if not candidates:
            return SelectionResult((), "no candidate met the minimum score and relevance thresholds", status="abstain")

        notes: list[str] = []
        units, blocked = _build_units(candidates, pool, ctx, notes)
        facets = _facet_keys(candidates)
        weights = [self.goal_weight if key == f"{FACET_PREFIX}0" else 1.0 for key in facets]
        covered = [0.0] * len(facets)
        picked: dict[str, SearchResult] = {}
        counts: dict[str, int] = defaultdict(int)
        total_cost = Decimal(0)
        budget = Decimal(str(ctx.budget_cost)) if ctx.budget_cost is not None else None
        objective = 0.0

        while True:
            best: tuple[float, float, str] | None = None
            best_unit: _Unit | None = None
            for unit in units:
                members = [pool[uid] for uid in unit.ids if uid not in picked]
                if not members:
                    continue
                if not self._fits(members, picked, counts, total_cost, budget, ctx):
                    continue
                gain = sum(
                    weight * max(0.0, max(_facet_value(member, key) for member in members) - current)
                    for key, weight, current in zip(facets, weights, covered)
                )
                # Ties go to the unit with the higher summed score, then id.
                rank = (gain, unit.utility, unit.root)
                if best is None or rank[:2] > best[:2] or (rank[:2] == best[:2] and rank[2] < best[2]):
                    best, best_unit = rank, unit
            if best_unit is None or best is None:
                break
            if picked and best[0] < self.min_gain:
                notes.append(f"{best_unit.root}: marginal coverage gain {best[0]:.3f} < {self.min_gain:g}")
                break
            for uid in best_unit.ids:
                if uid in picked:
                    continue
                member = pool[uid]
                picked[uid] = member
                counts[member.resource.metadata.kind] += 1
                total_cost += _total_cost([member])
            covered = [max(current, *(_facet_value(pool[uid], key) for uid in best_unit.ids)) for key, current in zip(facets, covered)]
            objective += best[0]

        escalation = _permission_escalation(set(picked), units, blocked, pool, ctx, notes)
        if escalation is not None:
            return escalation
        if picked:
            ordered = tuple(sorted(picked.values(), key=lambda r: (-r.score, r.resource.metadata.id)))
            reason = (
                f"coverage selected {len(ordered)} resource(s) over {len(facets)} facet(s) "
                f"(coverage={objective:.3f}, cost={total_cost:g}) with dependency closure, conflict and budget constraints"
            )
            if notes:
                reason += "; skipped: " + "; ".join(notes[:4])
            return SelectionResult(ordered, reason)
        reason = "no feasible set under dependency, conflict, and budget constraints"
        if notes:
            reason += ": " + "; ".join(notes[:4])
        return SelectionResult((), reason, status="abstain")

    @staticmethod
    def _fits(
        members: list[SearchResult],
        picked: Mapping[str, SearchResult],
        counts: Mapping[str, int],
        total_cost: Decimal,
        budget: Decimal | None,
        ctx: SelectionContext,
    ) -> bool:
        if len(picked) + len(members) > ctx.max_resources:
            return False
        if budget is not None and total_cost + _total_cost(members) > budget:
            return False
        extra: dict[str, int] = defaultdict(int)
        for member in members:
            extra[member.resource.metadata.kind] += 1
        for kind, added in extra.items():
            limit = ctx.per_kind_limits.get(kind)
            if limit is not None and counts.get(kind, 0) + added > limit:
                return False
        return not _conflicts(members, picked)


def _facet_keys(results: list[SearchResult]) -> list[str]:
    keys = {key for result in results for key in result.components if key.startswith(FACET_PREFIX)}
    if not keys:
        return ["relevance"]
    return sorted(keys, key=lambda key: int(key[len(FACET_PREFIX):]) if key[len(FACET_PREFIX):].isdigit() else 1 << 30)


def _facet_value(result: SearchResult, key: str) -> float:
    return float(result.components.get(key, 0.0))
