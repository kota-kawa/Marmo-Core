"""Task-aware set selection with explicit, evidence-backed contracts.

The selector treats unknown declarations as uncertainty.  A successful result
means that the selected candidate set satisfies the parsed TaskSpec and the
known hard constraints; it does not assert that a declaration describes the
outside world correctly.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from decimal import Decimal, InvalidOperation
from math import isfinite
from typing import Callable, Iterable, Mapping, Sequence, TYPE_CHECKING
import unicodedata

from .models import SearchResult, SelectionResult
from .routing_contracts import (
    AllOf,
    OneOf,
    Requirement,
    RequirementExpressionValue,
    ResourceContract,
    TaskSpec,
    TruthValue,
    evaluate_expression,
    match_requirement,
)
from .selector import SelectionContext, SetSelector

if TYPE_CHECKING:
    from .compiler import CompiledContext


TaskSpecProvider = Callable[[str], TaskSpec]
RenderedTokenCost = Callable[[tuple[SearchResult, ...]], int | float]


@dataclass(frozen=True)
class _Assessment:
    state: str
    reason: str
    objective: tuple[object, ...] | None = None
    missing_permissions: frozenset[str] = frozenset()


class GoalAwareSetSelector(SetSelector):
    """Choose a set that satisfies a TaskSpec and its resource contracts.

    ``greedy`` repeatedly adds the dependency-closed unit with the largest
    requirement-progress per rendered-token increase. ``exact`` enumerates
    candidate subsets up to ``max_nodes`` and returns the best set under the
    fixed lexicographic objective. A truncated exact search never labels an
    unproven result optimal. The default token callback is a metadata proxy;
    callers should supply the compiler's renderer for a meaningful context
    budget, and the Kernel still validates the actual compiled payload.
    """

    requires_contract_verification = True
    budget_aware = True

    def __init__(
        self,
        task_spec_provider: TaskSpecProvider,
        strategy: str = "greedy",
        rendered_token_cost: RenderedTokenCost | None = None,
        max_nodes: int = 100_000,
    ) -> None:
        if strategy not in {"greedy", "exact"}:
            raise ValueError("strategy must be 'greedy' or 'exact'")
        if max_nodes < 1:
            raise ValueError("max_nodes must be at least 1")
        self.task_spec_provider = task_spec_provider
        self.strategy = strategy
        self._has_custom_rendered_token_cost = rendered_token_cost is not None
        self.rendered_token_cost = (
            rendered_token_cost
            if rendered_token_cost is not None
            else _default_rendered_token_cost
        )
        self.max_nodes = max_nodes

    def select(
        self, results: list[SearchResult], *, context: SelectionContext | None = None
    ) -> SelectionResult:
        ctx = context or SelectionContext()
        if (
            getattr(ctx, "context_token_budget", None) is not None
            and not self._has_custom_rendered_token_cost
        ):
            return _uncertain(
                "context_token_budget requires an explicit rendered_token_cost callback; "
                "the default metadata estimate cannot verify the budget"
            )
        spec = self._context_task_spec(ctx)
        if not isinstance(spec, TaskSpec):
            return _uncertain("TaskSpec provider did not return a TaskSpec")
        if spec.expression is None or spec.unknown_items:
            detail = "; ".join(spec.unknown_items) or "TaskSpec has no requirement expression"
            return _uncertain(f"TaskSpec is incomplete: {detail}")

        pool = _candidate_pool(results)
        root_ids = _eligible_ids(pool, ctx)
        if not root_ids:
            return SelectionResult((), "no candidate met the active score and relevance thresholds", "abstain")

        if self.strategy == "greedy":
            current = self._greedy(
                pool, spec, ctx, root_ids=root_ids, enforce_permissions=ctx.enforce_permissions
            )
            if current is not None:
                return self._selected(current, "greedy")
            if ctx.enforce_permissions:
                relaxed = self._greedy(pool, spec, ctx, root_ids=root_ids, enforce_permissions=False)
                if relaxed is not None:
                    missing = _permission_union(relaxed) - set(ctx.granted_permissions)
                    if missing:
                        return SelectionResult(
                            (),
                            "a satisfying set exists only with additional permissions: "
                            + ", ".join(sorted(missing)),
                            "escalate",
                            missing_permissions=tuple(sorted(missing)),
                        )
            return _uncertain("greedy search could not establish a satisfying, feasible set")

        return self._exact(pool, spec, ctx, root_ids)

    def validate_selection(
        self,
        results: Sequence[SearchResult],
        *,
        context: SelectionContext = SelectionContext(),
        compiled: CompiledContext | None = None,
    ) -> tuple[bool, str]:
        """Recheck the final set and, when supplied, its compiled resource IDs."""

        if context.context_token_budget is not None and not self._has_custom_rendered_token_cost:
            return (
                False,
                "uncertain: context_token_budget requires an explicit rendered_token_cost callback",
            )
        spec = self._context_task_spec(context)
        if not isinstance(spec, TaskSpec):
            return False, "TaskSpec provider did not return a TaskSpec"
        if spec.expression is None or spec.unknown_items:
            return False, "TaskSpec is incomplete or uncertain"
        pool = _candidate_pool(list(results))
        if len(pool) != len(results):
            return False, "selection contains duplicate or ineligible resource identities"
        assessment = self._assess(tuple(pool.values()), spec, context)
        if assessment.state != "valid":
            return False, assessment.reason
        if compiled is not None:
            selected_ids = {item.resource.identity for item in pool.values()}
            compiled_ids = set(compiled.resource_ids) - set(compiled.trimmed_resource_ids)
            trimmed_selected = selected_ids & set(compiled.trimmed_resource_ids)
            if trimmed_selected:
                return False, "compiled context trimmed selected resource(s): " + ", ".join(sorted(trimmed_selected))
            if compiled_ids != selected_ids:
                missing = sorted(selected_ids - compiled_ids)
                extra = sorted(compiled_ids - selected_ids)
                details = []
                if missing:
                    details.append("missing from compiled context: " + ", ".join(missing))
                if extra:
                    details.append("unexpected compiled resources: " + ", ".join(extra))
                return False, "; ".join(details)
        return True, assessment.reason

    def _get_task_spec(self, task: str) -> TaskSpec | None:
        try:
            return self.resolve_task_spec(task)
        except Exception:
            return None

    def resolve_task_spec(self, task: str) -> TaskSpec:
        """Resolve a TaskSpec once so a caller can freeze it into task state."""

        spec = self.task_spec_provider(task)
        if not isinstance(spec, TaskSpec):
            raise ValueError("TaskSpec provider did not return a TaskSpec")
        return spec

    def _context_task_spec(self, context: SelectionContext) -> TaskSpec | None:
        fixed_spec = getattr(context, "task_spec", None)
        if fixed_spec is not None:
            return fixed_spec if isinstance(fixed_spec, TaskSpec) else None
        return self._get_task_spec(context.task)

    def _selected(self, results: tuple[SearchResult, ...], strategy: str) -> SelectionResult:
        reason = (
            f"goal-aware {strategy} selected {len(results)} resource(s); "
            "requirements and declared constraints verified"
        )
        return SelectionResult(results, reason)

    def _greedy(
        self,
        pool: Mapping[str, SearchResult],
        spec: TaskSpec,
        context: SelectionContext,
        *,
        root_ids: set[str],
        enforce_permissions: bool,
    ) -> tuple[SearchResult, ...] | None:
        effective = context if context.enforce_permissions == enforce_permissions else replace(
            context, enforce_permissions=enforce_permissions
        )
        selected: set[str] = set()
        closure_budget = [0]
        for _ in range(len(pool) + 1):
            current = tuple(pool[identity] for identity in sorted(selected, key=_identity_key))
            assessment = self._assess(current, spec, effective, reference_pool=pool)
            if assessment.state == "valid":
                return _ordered(current)

            baseline = _expression_progress(spec.expression, current)
            best: tuple[float, tuple[object, ...], frozenset[str]] | None = None
            for identity in sorted(root_ids, key=_identity_key):
                if identity in selected:
                    continue
                options = _closure_options(identity, pool, closure_budget, self.max_nodes)
                for option in options:
                    added = option - selected
                    if not added:
                        continue
                    combined = selected | set(option)
                    combined_results = _ordered(pool[item] for item in combined)
                    progress = _expression_progress(spec.expression, combined_results)
                    increase = progress - baseline
                    if increase <= 1e-12:
                        continue
                    if _partial_constraints(combined_results, effective, enforce_permissions):
                        continue
                    token_limit = getattr(effective, "context_token_budget", None)
                    if token_limit is not None:
                        rendered = _rendered_token_cost(self.rendered_token_cost, combined_results)
                        if rendered is None or rendered > token_limit:
                            continue
                    token_delta = _token_delta(
                        self.rendered_token_cost,
                        current,
                        combined_results,
                    )
                    if token_delta is None:
                        continue
                    ratio = increase / max(float(token_delta), 1.0)
                    objective = _objective(
                        combined_results, self.rendered_token_cost
                    )
                    if objective is None:
                        continue
                    candidate = (ratio, objective, frozenset(combined))
                    if best is None or ratio > best[0] + 1e-12 or (
                        abs(ratio - best[0]) <= 1e-12 and objective < best[1]
                    ):
                        best = candidate
            if best is None:
                return None
            selected = set(best[2])
        return None

    def _exact(
        self,
        pool: Mapping[str, SearchResult],
        spec: TaskSpec,
        context: SelectionContext,
        root_ids: set[str],
    ) -> SelectionResult:
        identities = tuple(sorted(pool, key=_identity_key))
        effective = context
        greedy_seed = self._greedy(
            pool, spec, context, root_ids=root_ids, enforce_permissions=context.enforce_permissions
        )
        best: tuple[SearchResult, ...] | None = greedy_seed
        best_objective = _objective(greedy_seed, self.rendered_token_cost) if greedy_seed else None
        relaxed_best: tuple[SearchResult, ...] | None = None
        relaxed_objective: tuple[object, ...] | None = None
        if context.enforce_permissions:
            relaxed_best = self._greedy(pool, spec, context, root_ids=root_ids, enforce_permissions=False)
            relaxed_objective = _objective(relaxed_best, self.rendered_token_cost) if relaxed_best else None
        nodes = 0
        truncated = False
        unknown_seen = False
        unknown_reasons: set[str] = set()

        def visit(index: int, chosen: tuple[SearchResult, ...]) -> None:
            nonlocal best, best_objective, relaxed_best, relaxed_objective, nodes, truncated, unknown_seen
            if truncated:
                return
            if nodes >= self.max_nodes:
                truncated = True
                return
            nodes += 1

            assessed = self._assess(chosen, spec, effective, reference_pool=pool)
            if assessed.state == "valid" and assessed.objective is not None:
                if best_objective is None or assessed.objective < best_objective:
                    best, best_objective = chosen, assessed.objective
            elif assessed.state == "unknown":
                unknown_seen = True
                unknown_reasons.add(assessed.reason)

            if context.enforce_permissions:
                relaxed_context = replace(context, enforce_permissions=False)
                relaxed = self._assess(chosen, spec, relaxed_context, reference_pool=pool)
                if relaxed.state == "valid" and relaxed.objective is not None:
                    if relaxed_objective is None or relaxed.objective < relaxed_objective:
                        relaxed_best, relaxed_objective = chosen, relaxed.objective
                elif relaxed.state == "unknown":
                    unknown_seen = True
                    unknown_reasons.add(relaxed.reason)

            if index >= len(identities):
                return

            identity = identities[index]
            included = _ordered((*chosen, pool[identity]))
            if _unknown_declaration(pool[identity], spec):
                unknown_seen = True
                unknown_reasons.add(
                    f"{identity}: contract is incomplete or requires runtime precondition evidence"
                )
            if not _partial_constraints(included, context, check_permissions=False):
                visit(index + 1, included)
            visit(index + 1, chosen)

        visit(0, ())

        if best is not None:
            objective_scope = (
                "custom rendered_token_cost"
                if self._has_custom_rendered_token_cost
                else "metadata token proxy"
            )
            status = (
                f"node budget reached; best feasible set found, optimality unproven for configured objective ({objective_scope})"
                if truncated
                else f"optimum proven for configured objective ({objective_scope})"
            )
            return SelectionResult(
                _ordered(best),
                f"goal-aware exact selected {len(best)} resource(s) after {nodes} node(s); {status}",
            )
        if truncated:
            return _uncertain(
                f"exact search reached max_nodes={self.max_nodes} without a feasible set; feasibility is uncertain"
            )
        if context.enforce_permissions and relaxed_best is not None:
            missing = _permission_union(relaxed_best) - set(context.granted_permissions)
            if missing:
                return SelectionResult(
                    (),
                    "a satisfying set exists only with additional permissions: "
                    + ", ".join(sorted(missing)),
                    "escalate",
                    missing_permissions=tuple(sorted(missing)),
                )
        if unknown_seen:
            details = "; ".join(sorted(unknown_reasons)[:3])
            return _uncertain(
                "no verified feasible set was found; an incomplete or unknown contract affected the decision"
                + (f": {details}" if details else "")
            )
        return SelectionResult((), "no candidate set satisfies the TaskSpec and hard constraints", "abstain")

    def _assess(
        self,
        results: Sequence[SearchResult],
        spec: TaskSpec,
        context: SelectionContext,
        *,
        reference_pool: Mapping[str, SearchResult] | None = None,
    ) -> _Assessment:
        ordered = _ordered(results)
        identities = [item.resource.identity for item in ordered]
        if len(identities) != len(set(identities)):
            return _Assessment("invalid", "selection contains duplicate resource identities")
        if spec.expression is None or spec.unknown_items:
            return _Assessment("unknown", "TaskSpec is incomplete or uncertain")

        permission_union: set[str] = set()
        total_cost = Decimal(0)
        counts: dict[str, int] = {}
        contracts: dict[str, ResourceContract] = {}
        graph: dict[str, set[str]] = {identity: set() for identity in identities}
        for result in ordered:
            metadata = result.resource.metadata
            contract = ResourceContract.from_resource(result.resource)
            contracts[metadata.identity] = contract
            if not contract.observed or not contract.complete or not contract.source_evidence or contract.unknown_items:
                detail = "; ".join(contract.unknown_items) or "contract is unobserved, incomplete, or lacks source evidence"
                return _Assessment("unknown", f"{metadata.identity}: {detail}")
            vocabulary_state = _vocabulary_binding(spec, contract)
            if vocabulary_state is not None:
                return _Assessment("unknown", f"{metadata.identity}: {vocabulary_state}")
            if contract.call_preconditions:
                return _Assessment(
                    "unknown",
                    f"{metadata.identity}: call_preconditions require runtime evidence unavailable to the selector",
                )
            try:
                cost = Decimal(str(metadata.cost_estimate))
            except (InvalidOperation, ValueError):
                return _Assessment("unknown", f"{metadata.identity}: cost_estimate is invalid")
            if not cost.is_finite() or cost < 0:
                return _Assessment("unknown", f"{metadata.identity}: cost_estimate must be finite and non-negative")
            total_cost += cost
            counts[metadata.kind] = counts.get(metadata.kind, 0) + 1
            permission_union.update(metadata.required_permissions)
            permission_union.update(contract.permissions)
            if _has_prohibited_affordance(contract, spec.prohibited_operations):
                return _Assessment("invalid", f"{metadata.identity} declares a prohibited operation")

        if len(ordered) > context.max_resources:
            return _Assessment("invalid", f"selection exceeds max_resources={context.max_resources}")
        for kind, limit in context.per_kind_limits.items():
            if counts.get(kind, 0) > limit:
                return _Assessment("invalid", f"selection exceeds per-kind limit for {kind}={limit}")
        if context.budget_cost is not None:
            try:
                budget = Decimal(str(context.budget_cost))
            except (InvalidOperation, ValueError):
                return _Assessment("unknown", "budget_cost is invalid")
            if not budget.is_finite() or budget < 0:
                return _Assessment("unknown", "budget_cost must be finite and non-negative")
            if total_cost > budget:
                return _Assessment("invalid", f"selection cost {total_cost} exceeds budget_cost={budget}")

        missing_permissions = permission_union - set(context.granted_permissions)
        if context.enforce_permissions and missing_permissions:
            return _Assessment(
                "invalid",
                "selection requires ungranted permissions: " + ", ".join(sorted(missing_permissions)),
                missing_permissions=frozenset(missing_permissions),
            )

        pool = {item.resource.identity: item for item in ordered}
        all_candidates_by_id = _versions_by_id(
            reference_pool.values() if reference_pool is not None else ordered
        )
        one_of_groups: list[tuple[str, tuple[str, ...]]] = []
        for result in ordered:
            identity = result.resource.identity
            metadata = result.resource.metadata
            contract = contracts[identity]
            required_refs = (*metadata.dependencies, *contract.context_all_of)
            for ref in required_refs:
                resolved, reason = _resolve_reference(ref, all_candidates_by_id)
                if resolved is None:
                    return _Assessment("unknown", f"{identity}: {reason}")
                if resolved not in pool:
                    return _Assessment("invalid", f"{identity} requires unselected resource {resolved}")
                graph[identity].add(resolved)
            for alternatives in contract.context_one_of:
                selected_alternatives: list[str] = []
                unresolved: list[str] = []
                for ref in alternatives:
                    resolved, reason = _resolve_reference(ref, all_candidates_by_id)
                    if resolved is None:
                        unresolved.append(reason)
                    elif resolved in pool:
                        selected_alternatives.append(resolved)
                if not selected_alternatives:
                    if unresolved:
                        return _Assessment("unknown", f"{identity}: context one_of cannot be resolved: {'; '.join(unresolved)}")
                    return _Assessment("invalid", f"{identity} requires one context alternative from {alternatives!r}")
                one_of_groups.append((identity, tuple(sorted(set(selected_alternatives), key=_identity_key))))

        if _has_cycle(graph):
            return _Assessment("invalid", "selection contains a dependency or context cycle")
        selected_graph, truncated = _choose_context_alternatives(graph, one_of_groups, self.max_nodes)
        if truncated:
            return _Assessment("unknown", "context one_of validation reached its search limit")
        if selected_graph is None:
            return _Assessment("invalid", "context one_of alternatives create a dependency cycle")
        graph = selected_graph

        dependencies = {child for children in graph.values() for child in children}
        roots = set(graph) - dependencies
        ineligible_roots = sorted(
            (
                identity
                for identity in roots
                if not _is_eligible(pool[identity], context)
            ),
            key=_identity_key,
        )
        if ineligible_roots:
            return _Assessment(
                "invalid",
                "selected root resource(s) are below the active score or relevance threshold: "
                + ", ".join(ineligible_roots),
            )

        conflict = _first_conflict(ordered)
        if conflict:
            return _Assessment("invalid", conflict)

        def match_one(requirement: Requirement) -> TruthValue:
            return _match_selected(requirement, ordered, contracts)

        requirement_state = evaluate_expression(spec.expression, match_one)
        if requirement_state is TruthValue.UNKNOWN:
            return _Assessment("unknown", "TaskSpec requirements are unknown against the selected contracts")
        if requirement_state is TruthValue.FALSE:
            return _Assessment("invalid", "selected set does not satisfy every required TaskSpec branch")

        objective = _objective(ordered, self.rendered_token_cost)
        if objective is None:
            return _Assessment("unknown", "rendered token cost or relevance is invalid")
        token_limit = getattr(context, "context_token_budget", None)
        if token_limit is not None:
            if not isinstance(token_limit, int) or isinstance(token_limit, bool) or token_limit < 0:
                return _Assessment("unknown", "context_token_budget must be a non-negative integer")
            rendered_cost = _rendered_token_cost(self.rendered_token_cost, ordered)
            if rendered_cost is None:
                return _Assessment("unknown", "rendered token cost is invalid")
            if rendered_cost > token_limit:
                return _Assessment(
                    "invalid",
                    f"rendered context cost {rendered_cost} exceeds context_token_budget={token_limit}",
                )
        return _Assessment("valid", "selected set satisfies the TaskSpec and declared constraints", objective)


def _candidate_pool(results: Sequence[SearchResult]) -> dict[str, SearchResult]:
    grouped: dict[str, list[SearchResult]] = {}
    for result in results:
        grouped.setdefault(result.resource.identity, []).append(result)
    pool: dict[str, SearchResult] = {}
    for identity, duplicates in grouped.items():
        pool[identity] = max(
            duplicates,
            key=lambda item: (
                _safe_score(item.score),
                _relevance(item),
                tuple(sorted(item.components.items())),
                item.reasons,
            ),
        )
    return dict(sorted(pool.items(), key=lambda item: _identity_key(item[0])))


def _eligible_ids(pool: Mapping[str, SearchResult], context: SelectionContext) -> set[str]:
    return {
        identity
        for identity, result in pool.items()
        if _is_eligible(result, context)
    }


def _is_eligible(result: SearchResult, context: SelectionContext) -> bool:
    return (
        isfinite(result.score)
        and result.score >= context.min_score
        and _relevance(result) >= context.min_relevance
    )


def _match_selected(
    requirement: Requirement,
    results: Sequence[SearchResult],
    contracts: Mapping[str, ResourceContract],
) -> TruthValue:
    values = [
        match_requirement(
            requirement,
            contracts[result.resource.identity],
            result.resource.metadata.kind,
        )
        for result in results
    ]
    if TruthValue.TRUE in values:
        return TruthValue.TRUE
    if TruthValue.UNKNOWN in values:
        return TruthValue.UNKNOWN
    return TruthValue.FALSE


def _expression_progress(
    expression: RequirementExpressionValue | None,
    results: Sequence[SearchResult],
) -> float:
    contracts = {
        result.resource.identity: ResourceContract.from_resource(result.resource)
        for result in results
    }

    def progress(node: RequirementExpressionValue | None) -> tuple[float, float]:
        if node is None:
            return 0.0, 1.0
        if isinstance(node, Requirement):
            state = _match_selected(node, results, contracts)
            return (1.0 if state is TruthValue.TRUE else 0.0), 1.0
        if not isinstance(node, (AllOf, OneOf)):
            return 0.0, 1.0
        child_progress = [progress(child) for child in node.children]
        if not child_progress:
            return 0.0, 1.0
        if isinstance(node, AllOf):
            return sum(done for done, _ in child_progress), sum(total for _, total in child_progress)
        return max(done / total for done, total in child_progress), 1.0

    achieved, total = progress(expression)
    return achieved / total if total else 0.0


def _closure_options(
    root: str,
    pool: Mapping[str, SearchResult],
    node_counter: list[int],
    max_nodes: int,
) -> tuple[frozenset[str], ...]:
    versions = _versions_by_id(pool.values())
    memo: dict[tuple[str, frozenset[str]], tuple[frozenset[str], ...]] = {}

    def expand(
        identity: str,
        included: frozenset[str],
        visiting: frozenset[str],
    ) -> tuple[frozenset[str], ...]:
        if identity in visiting:
            return ()
        if identity in included:
            return (included,)
        key = (identity, included)
        if key in memo:
            return memo[key]
        node_counter[0] += 1
        if node_counter[0] > max_nodes:
            return ()
        result = pool.get(identity)
        if result is None:
            return ()
        contract = ResourceContract.from_resource(result.resource)
        if not contract.observed or not contract.complete or not contract.source_evidence or contract.unknown_items:
            return ()
        current = included | {identity}
        next_visiting = visiting | {identity}
        states: tuple[frozenset[str], ...] = (frozenset(current),)
        all_refs = (*result.resource.metadata.dependencies, *contract.context_all_of)
        for ref in all_refs:
            resolved, _ = _resolve_reference(ref, versions)
            if resolved is None:
                memo[key] = ()
                return ()
            next_states: list[frozenset[str]] = []
            for state in states:
                next_states.extend(expand(resolved, state, next_visiting))
            states = _unique_sets(next_states)
            if not states:
                memo[key] = ()
                return ()

        for group in contract.context_one_of:
            next_states = []
            for state in states:
                group_options: list[frozenset[str]] = []
                for ref in group:
                    resolved, _ = _resolve_reference(ref, versions)
                    if resolved is not None:
                        group_options.extend(expand(resolved, state, next_visiting))
                next_states.extend(group_options)
            states = _unique_sets(next_states)
            if not states:
                memo[key] = ()
                return ()
        memo[key] = states
        return states

    return expand(root, frozenset(), frozenset())


def _partial_constraints(
    results: Sequence[SearchResult],
    context: SelectionContext,
    check_permissions: bool,
) -> bool:
    """Return whether a partial set is irreparably infeasible."""

    if len(results) > context.max_resources:
        return True
    counts: dict[str, int] = {}
    cost = Decimal(0)
    for result in results:
        metadata = result.resource.metadata
        counts[metadata.kind] = counts.get(metadata.kind, 0) + 1
        try:
            item_cost = Decimal(str(metadata.cost_estimate))
        except (InvalidOperation, ValueError):
            return True
        if not item_cost.is_finite() or item_cost < 0:
            return True
        cost += item_cost
        contract = ResourceContract.from_resource(result.resource)
        if not contract.observed or not contract.complete or not contract.source_evidence or contract.unknown_items:
            return True
    if any(counts.get(kind, 0) > limit for kind, limit in context.per_kind_limits.items()):
        return True
    if context.budget_cost is not None:
        try:
            budget = Decimal(str(context.budget_cost))
        except (InvalidOperation, ValueError):
            return True
        if not budget.is_finite() or cost > budget:
            return True
    if check_permissions and context.enforce_permissions:
        required = _permission_union(results)
        if required - set(context.granted_permissions):
            return True
    return _first_conflict(results) is not None


def _unknown_declaration(result: SearchResult, spec: TaskSpec) -> bool:
    contract = ResourceContract.from_resource(result.resource)
    return (
        not contract.observed
        or not contract.complete
        or not contract.source_evidence
        or bool(contract.unknown_items)
        or bool(contract.call_preconditions)
        or _vocabulary_binding(spec, contract) is not None
    )


def _objective(
    results: Sequence[SearchResult] | None,
    token_cost: RenderedTokenCost,
) -> tuple[object, ...] | None:
    if results is None:
        return None
    ordered = _ordered(results)
    permissions = _permission_union(ordered)
    try:
        rendered = token_cost(ordered)
        rendered_decimal = Decimal(str(rendered))
    except Exception:
        return None
    if not rendered_decimal.is_finite() or rendered_decimal < 0:
        return None
    total_cost = Decimal(0)
    relevance_values: list[float] = []
    for result in ordered:
        try:
            item_cost = Decimal(str(result.resource.metadata.cost_estimate))
        except (InvalidOperation, ValueError):
            return None
        relevance = _relevance(result)
        if not item_cost.is_finite() or item_cost < 0 or not isfinite(relevance):
            return None
        total_cost += item_cost
        relevance_values.append(relevance)
    max_relevance = max(relevance_values, default=0.0)
    normalized_ids = tuple(_normalize_identity(item.resource.identity) for item in ordered)
    return (len(permissions), rendered_decimal, total_cost, -max_relevance, normalized_ids)


def _rendered_token_cost(
    token_cost: RenderedTokenCost,
    results: Sequence[SearchResult],
) -> Decimal | None:
    try:
        value = Decimal(str(token_cost(_ordered(results))))
    except Exception:
        return None
    if not value.is_finite() or value < 0:
        return None
    return value


def _token_delta(
    token_cost: RenderedTokenCost,
    before: Sequence[SearchResult],
    after: Sequence[SearchResult],
) -> Decimal | None:
    after_cost = _rendered_token_cost(token_cost, after)
    before_cost = _rendered_token_cost(token_cost, before)
    if after_cost is None or before_cost is None:
        return None
    delta = after_cost - before_cost
    if not delta.is_finite():
        return None
    return max(delta, Decimal(0))


def _vocabulary_binding(spec: TaskSpec, contract: ResourceContract) -> str | None:
    task_binding = (spec.vocabulary_version, spec.vocabulary_hash)
    resource_binding = (contract.vocabulary_version, contract.vocabulary_hash)
    if task_binding == (None, None) and resource_binding == (None, None):
        return None
    if None in task_binding or None in resource_binding:
        return "versioned vocabulary binding is incomplete"
    if task_binding != resource_binding:
        return "TaskSpec and resource vocabulary version/hash do not match"
    return None


def _permission_union(results: Iterable[SearchResult]) -> set[str]:
    permissions: set[str] = set()
    for result in results:
        permissions.update(result.resource.metadata.required_permissions)
        permissions.update(ResourceContract.from_resource(result.resource).permissions)
    return permissions


def _versions_by_id(results: Iterable[SearchResult]) -> dict[str, list[str]]:
    by_id: dict[str, list[str]] = {}
    for result in results:
        metadata = result.resource.metadata
        by_id.setdefault(metadata.id, []).append(metadata.identity)
    return {key: sorted(values, key=_identity_key) for key, values in by_id.items()}


def _resolve_reference(
    reference: str,
    by_id: Mapping[str, Sequence[str]],
) -> tuple[str | None, str]:
    if not isinstance(reference, str) or not reference.strip():
        return None, "resource reference is empty or malformed"
    ref = reference.strip()
    if "@" in ref:
        resource_id, version = ref.rsplit("@", 1)
        for identity in by_id.get(resource_id, ()):
            if identity.rsplit("@", 1)[-1] == version:
                return identity, ""
        return None, f"referenced version {ref} is missing from the candidate pool"
    matches = by_id.get(ref, ())
    if len(matches) == 1:
        return matches[0], ""
    if not matches:
        return None, f"referenced resource {ref} is missing from the candidate pool"
    return None, f"reference {ref} is ambiguous across versions"


def _first_conflict(results: Sequence[SearchResult]) -> str | None:
    for index, left in enumerate(results):
        left_meta = left.resource.metadata
        for right in results[index + 1 :]:
            right_meta = right.resource.metadata
            if any(_conflict_ref_matches(ref, right_meta.id, right_meta.identity) for ref in left_meta.conflicts_with):
                return f"{left_meta.identity} conflicts with {right_meta.identity}"
            if any(_conflict_ref_matches(ref, left_meta.id, left_meta.identity) for ref in right_meta.conflicts_with):
                return f"{right_meta.identity} conflicts with {left_meta.identity}"
    return None


def _conflict_ref_matches(reference: str, resource_id: str, identity: str) -> bool:
    if "@" in reference:
        return reference == identity
    return reference == resource_id


def _has_cycle(graph: Mapping[str, set[str]]) -> bool:
    visited: set[str] = set()
    visiting: set[str] = set()

    def visit(identity: str) -> bool:
        if identity in visiting:
            return True
        if identity in visited:
            return False
        visiting.add(identity)
        for child in graph.get(identity, ()):
            if child in graph and visit(child):
                return True
        visiting.remove(identity)
        visited.add(identity)
        return False

    return any(visit(identity) for identity in graph)


def _choose_context_alternatives(
    base_graph: Mapping[str, set[str]],
    groups: Sequence[tuple[str, tuple[str, ...]]],
    max_nodes: int,
) -> tuple[dict[str, set[str]] | None, bool]:
    """Choose one selected alternative per group without creating a cycle."""

    graph = {identity: set(children) for identity, children in base_graph.items()}
    explored = 0
    truncated = False

    def visit(index: int) -> dict[str, set[str]] | None:
        nonlocal explored, truncated
        if explored >= max_nodes:
            truncated = True
            return None
        explored += 1
        if index == len(groups):
            return {identity: set(children) for identity, children in graph.items()}
        parent, alternatives = groups[index]
        for alternative in alternatives:
            already_present = alternative in graph[parent]
            graph[parent].add(alternative)
            if not _has_cycle(graph):
                result = visit(index + 1)
                if result is not None:
                    return result
            if not already_present:
                graph[parent].discard(alternative)
            if truncated:
                return None
        return None

    return visit(0), truncated


def _has_prohibited_affordance(contract: ResourceContract, prohibited: Sequence[str]) -> bool:
    blocked = {item.strip().casefold() for item in prohibited if item.strip()}
    return any(
        affordance.action is not None and affordance.action.casefold() in blocked
        for affordance in contract.affordances
    )


def _unique_sets(values: Iterable[frozenset[str]]) -> tuple[frozenset[str], ...]:
    unique = set(values)
    return tuple(sorted(unique, key=lambda value: tuple(sorted(value, key=_identity_key))))


def _ordered(results: Iterable[SearchResult]) -> tuple[SearchResult, ...]:
    return tuple(sorted(results, key=lambda item: _identity_key(item.resource.identity)))


def _identity_key(identity: str) -> tuple[str, str]:
    return _normalize_identity(identity), identity


def _normalize_identity(identity: str) -> str:
    return unicodedata.normalize("NFKC", identity).strip().casefold()


def _safe_score(value: float) -> float:
    return value if isfinite(value) else float("-inf")


def _relevance(result: SearchResult) -> float:
    try:
        value = float(result.components.get("relevance", result.score))
    except (TypeError, ValueError):
        return float("-inf")
    return value if isfinite(value) else float("-inf")


def _default_rendered_token_cost(results: tuple[SearchResult, ...]) -> int:
    """A deterministic fallback cost for callers without a compiler callback."""

    return sum(len(result.resource.metadata.search_text().split()) for result in results)


def _uncertain(reason: str) -> SelectionResult:
    return SelectionResult((), f"uncertain: {reason}", "abstain")
