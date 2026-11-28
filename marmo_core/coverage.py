"""Coverage-based set selection: cover each sub-task once, stop when nothing is gained.

The constrained solvers in ``selector.py`` maximize Σ u(i∈S), the summed
scores of the selected units. A sum rewards every additional relevant-looking
member, so it cannot say how many resources a goal needs: two near-duplicate
search tools add twice the utility of one, and the solvers keep adding until
a count limit stops them. On ToolRet, a fixed top-3 over BM25 averages Set
F1 0.12 while gold sets range from one to seven tools.

``CoverageSetSelector`` instead maximizes a facility-location objective over
the goal's facets (the ``facet.<i>`` relevance components that
``DecomposedRetriever`` attaches; without them the goal is one facet scored
by ``relevance``):

    F(S) = Σ_k Σ_f w_f · max_{i ∈ S, kind(i) = k} r_f(i)

counted per resource kind k, because the kinds play different parts (a
Memory is context, a Skill a procedure, a Tool an action) and one does not
make another redundant. A member adds value only for the facets it serves
better than what of its kind is already selected, so a second tool for an
already-covered sub-task adds nothing, and selection stops when the best
feasible unit's marginal gain falls below ``min_gain``. F is monotone
submodular, so greedy selection by marginal gain is the standard
(1 - 1/e)-approximate maximizer under a cardinality limit alone; the
guarantee does not cover the conflict, budget, and stopping rules.

Measured on ToolRet (``benchmarks/README.md``), the gain over the top result
of a plain search comes from the decomposed ranking itself. Whether coverage
selection adds to the top result of the decomposed ranking depends on the
model that decomposes: on all 3,920 test queries it added +0.012 Set F1 with
Claude Sonnet decompositions and nothing with Claude Haiku 5.5 ones (-0.003,
within noise), which split more queries into sub-tasks. ``LLMSetSelector``
chose better sets than any rule on the sample.

Units, feasibility, and the abstain / escalate outcomes are the same as for
the greedy constrained solver: a candidate is taken
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
    _candidate_pool,
    _conflicts,
    _gate_admissible,
    _no_candidates,
    _permission_escalation,
    _score_order,
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

    Escalation uses the greedy solver's rule unchanged: a permission-blocked
    unit escalates when its summed score beats every selected unit's, which
    compares composite scores rather than coverage gains.

    Without ``facet.<i>`` components there is one facet per kind, so it takes
    the best unit of each kind whose relevance clears ``min_gain``.

    Coverage drops near-duplicates by design. When the caller would rather
    hand a model several near-equivalent resources (three endpoints of the
    same API, say), ``include_within`` also keeps, after the coverage pass,
    every candidate whose relevance is at least that fraction of the
    top-ranked candidate's, in rank order, as long as its unit fits the same
    constraints. The top-ranked candidate is the first one past the score
    and relevance floors, whether or not it could be selected itself;
    permission-blocked units are never added this way.
    """

    def __init__(
        self,
        *,
        min_gain: float = 0.1,
        goal_weight: float = 1.0,
        include_within: float | None = None,
        default_context: SelectionContext | None = None,
    ) -> None:
        if min_gain < 0.0:
            raise ValueError("min_gain must be non-negative")
        if goal_weight < 0.0:
            raise ValueError("goal_weight must be non-negative")
        if include_within is not None and not 0.0 < include_within <= 1.0:
            raise ValueError("include_within must be in (0, 1]")
        self.min_gain = min_gain
        self.goal_weight = goal_weight
        self.include_within = include_within
        self.default_context = default_context or SelectionContext()

    def select(
        self, results: list[SearchResult], *, context: SelectionContext | None = None
    ) -> SelectionResult:
        ctx = context or self.default_context
        results, notes = _gate_admissible(results, ctx)
        pool = _candidate_pool(results)
        candidates = [
            r
            for r in results
            if r.score >= ctx.min_score and float(r.components.get("relevance", 1.0)) >= ctx.min_relevance
        ]
        if not candidates:
            return _no_candidates(notes)

        units, blocked = _build_units(candidates, pool, ctx, notes)
        facets = _facet_keys(candidates)
        weights = [self.goal_weight if key == f"{FACET_PREFIX}0" else 1.0 for key in facets]
        # Coverage is counted per kind: a Tool that serves a sub-task does not
        # make the Skill that explains it, or the Memory that holds its context,
        # redundant.
        covered: dict[tuple[str, int], float] = defaultdict(float)
        picked: dict[str, SearchResult] = {}
        counts: dict[str, int] = defaultdict(int)
        total_cost = Decimal(0)
        budget = Decimal(str(ctx.budget_cost)) if ctx.budget_cost is not None else None
        objective = 0.0

        unfit: dict[str, str] = {}
        while True:
            best: tuple[float, float, str] | None = None
            best_unit: _Unit | None = None
            for unit in units:
                members = [pool[uid] for uid in unit.ids if uid not in picked]
                if not members:
                    continue
                misfit = self._misfit(members, picked, counts, total_cost, budget, ctx)
                if misfit is not None:
                    unfit[unit.root] = misfit
                    continue
                unfit.pop(unit.root, None)
                gain = _gain(members, facets, weights, covered)
                # Ties go to the unit with the higher summed score, then id.
                rank = (gain, unit.utility, unit.root)
                if best is None or rank[:2] > best[:2] or (rank[:2] == best[:2] and rank[2] < best[2]):
                    best, best_unit = rank, unit
            if best_unit is None or best is None:
                break
            if picked and best[0] < self.min_gain:
                unfit[best_unit.root] = f"marginal coverage gain {best[0]:.3f} < {self.min_gain:g}"
                break
            for uid in best_unit.ids:
                if uid in picked:
                    continue
                member = pool[uid]
                picked[uid] = member
                counts[member.resource.metadata.kind] += 1
                total_cost += _total_cost([member])
            for uid in best_unit.ids:
                kind = pool[uid].resource.metadata.kind
                for index, key in enumerate(facets):
                    covered[kind, index] = max(covered[kind, index], _facet_value(pool[uid], key))
            objective += best[0]

        # A missing relevance component counts as 1.0 here as in the floors above.
        top_relevance = float(candidates[0].components.get("relevance", 1.0))
        if self.include_within is not None and picked and top_relevance > 0.0:
            floor = self.include_within * top_relevance
            by_root = {unit.root: unit for unit in units}
            key_of = {member.resource.identity: key for key, member in pool.items()}
            for candidate in candidates:
                near = by_root.get(key_of[candidate.resource.identity])
                if near is None or float(candidate.components.get("relevance", 1.0)) < floor:
                    continue
                added = [uid for uid in near.ids if uid not in picked]
                members = [pool[uid] for uid in added]
                if not members:
                    continue
                misfit = self._misfit(members, picked, counts, total_cost, budget, ctx)
                if misfit is not None:
                    unfit.setdefault(near.root, misfit)
                    continue
                for uid, member in zip(added, members):
                    picked[uid] = member
                    counts[member.resource.metadata.kind] += 1
                    total_cost += _total_cost([member])
                unfit.pop(near.root, None)

        notes.extend(f"{root}: {reason}" for root, reason in unfit.items() if root not in picked)
        escalation = _permission_escalation(set(picked), units, blocked, pool, ctx, notes)
        if escalation is not None:
            return escalation
        if picked:
            ordered = tuple(sorted(picked.values(), key=_score_order))
            reason = (
                f"coverage selected {len(ordered)} resource(s) over {len(facets)} facet(s) "
                f"(coverage={objective:.3f}, cost={total_cost:g}) with dependency closure, conflict and budget constraints"
            )
            if notes:
                reason += "; skipped: " + _first_notes(notes)
            return SelectionResult(ordered, reason)
        reason = "no feasible set under dependency, conflict, and budget constraints"
        if notes:
            reason += ": " + _first_notes(notes)
        return SelectionResult((), reason, status="abstain")

    @staticmethod
    def _misfit(
        members: list[SearchResult],
        picked: Mapping[str, SearchResult],
        counts: Mapping[str, int],
        total_cost: Decimal,
        budget: Decimal | None,
        ctx: SelectionContext,
    ) -> str | None:
        """Why ``members`` cannot join the selection, or None when they can."""

        if _conflicts(members, picked):
            return "conflicts with an already selected resource"
        if len(picked) + len(members) > ctx.max_resources:
            return f"would exceed max_resources={ctx.max_resources}"
        if budget is not None and total_cost + _total_cost(members) > budget:
            return f"would exceed budget_cost={ctx.budget_cost}"
        extra: dict[str, int] = defaultdict(int)
        for member in members:
            extra[member.resource.metadata.kind] += 1
        for kind, added in extra.items():
            limit = ctx.per_kind_limits.get(kind)
            if limit is not None and counts.get(kind, 0) + added > limit:
                return f"per-kind limit for {kind} reached"
        return None


def _first_notes(notes: list[str], limit: int = 4) -> str:
    text = "; ".join(notes[:limit])
    return text + (f"; and {len(notes) - limit} more" if len(notes) > limit else "")


def _gain(
    members: list[SearchResult], facets: list[str], weights: list[float], covered: Mapping[tuple[str, int], float]
) -> float:
    """Marginal coverage of adding ``members``: per kind and facet, the improvement over what is covered."""

    best: dict[tuple[str, int], float] = {}
    for member in members:
        kind = member.resource.metadata.kind
        for index, key in enumerate(facets):
            value = _facet_value(member, key)
            if value > best.get((kind, index), 0.0):
                best[kind, index] = value
    return sum(weights[index] * max(0.0, value - covered.get((kind, index), 0.0)) for (kind, index), value in best.items())


def _facet_keys(results: list[SearchResult]) -> list[str]:
    keys = {key for result in results for key in result.components if key.startswith(FACET_PREFIX)}
    if not keys:
        return ["relevance"]
    return sorted(keys, key=lambda key: int(key[len(FACET_PREFIX):]) if key[len(FACET_PREFIX):].isdigit() else 1 << 30)


def _facet_value(result: SearchResult, key: str) -> float:
    if key in result.components:
        return float(result.components[key])
    # A result with no ``facet.*`` at all was ranked for the goal alone (its
    # search was not decomposed, e.g. the decomposer failed that time), so its
    # relevance is its goal facet instead of zero next to decomposed results.
    if key == f"{FACET_PREFIX}0" and not any(name.startswith(FACET_PREFIX) for name in result.components):
        return float(result.components.get("relevance", 0.0))
    return 0.0
