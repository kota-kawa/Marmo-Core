from __future__ import annotations

from itertools import combinations
import unittest

from marmo_core.compiler import CompiledContext
from marmo_core.models import ResourceDefinition, SearchResult
from marmo_core.routing_contracts import (
    AllOf,
    Requirement,
    RequirementExpression,
    ResourceContract,
    TaskSpec,
    TruthValue,
    match_requirement,
)
from marmo_core.selector import SelectionContext
from marmo_core.sufficient_selector import GoalAwareSetSelector, _objective


def _contract(
    affordances: tuple[dict[str, object], ...] = (),
    *,
    context_all_of: tuple[str, ...] = (),
    context_one_of: tuple[tuple[str, ...], ...] = (),
    permissions: tuple[str, ...] = (),
    call_preconditions: tuple[dict[str, object], ...] = (),
    **overrides: object,
) -> dict[str, object]:
    value: dict[str, object] = {
        "schema_version": 1,
        "observed": True,
        "complete": True,
        "affordances": [dict(item) for item in affordances],
        "context": {
            "all_of": list(context_all_of),
            "one_of": [list(group) for group in context_one_of],
        },
        "call_preconditions": [dict(item) for item in call_preconditions],
        "permissions": list(permissions),
        "source_evidence": [{"source": "catalog", "evidence": "checked declaration"}],
    }
    value.update(overrides)
    return value


def _affordance(
    action: str,
    entity_type: str = "document",
    *,
    scope: str = "global",
    mode: str = "effect",
    output_type: str | None = None,
) -> dict[str, str]:
    value = {
        "action": action,
        "entity_type": entity_type,
        "supported_scope": scope,
        "mode": mode,
    }
    if output_type is not None:
        value["output_type"] = output_type
    return value


def _definition(
    resource_id: str,
    *,
    kind: str = "tool",
    version: str = "1.0.0",
    affordances: tuple[dict[str, object], ...] = (),
    dependencies: tuple[str, ...] = (),
    conflicts_with: tuple[str, ...] = (),
    required_permissions: tuple[str, ...] = (),
    contract_permissions: tuple[str, ...] = (),
    cost_estimate: float = 0.0,
    rendered_tokens: int = 1,
    contract: dict[str, object] | None = None,
) -> ResourceDefinition:
    data: dict[str, object] = {
        "id": resource_id,
        "kind": kind,
        "name": resource_id,
        "version": version,
        "description": f"Resource {resource_id}",
        "capabilities": [],
        "input_summary": "input",
        "output_summary": "output",
        "required_permissions": list(required_permissions),
        "cost_estimate": cost_estimate,
        "latency_class": "fast",
        "side_effect": "none",
        "trust_level": "verified",
        "ref": f"{kind}://{resource_id}",
        "tags": [],
        "dependencies": list(dependencies),
        "conflicts_with": list(conflicts_with),
        "routing_contract": contract
        or _contract(affordances, permissions=contract_permissions),
        "rendered_tokens": rendered_tokens,
    }
    return ResourceDefinition.from_mapping(data)


def _result(
    definition: ResourceDefinition,
    score: float = 0.9,
    relevance: float = 0.9,
) -> SearchResult:
    return SearchResult(definition, score, (), {"relevance": relevance})


def _task(*requirements: object, prohibited: tuple[str, ...] = ()) -> TaskSpec:
    return TaskSpec.from_mapping(
        {
            "requirements": {"all_of": list(requirements)},
            "prohibited_operations": list(prohibited),
            "provenance": {"source": "user request", "evidence": "task text"},
        }
    )


def _requirement(
    action: str,
    entity_type: str = "document",
    *,
    scope: str | None = None,
    mode: str = "effect",
    output_type: str | None = None,
) -> dict[str, object]:
    value: dict[str, object] = {
        "action": action,
        "entity_type": entity_type,
        "mode": mode,
        "provenance": {"source": "user request", "evidence": f"{action} {entity_type}"},
    }
    if scope is not None:
        value["target_scope"] = scope
    if output_type is not None:
        value["output_type"] = output_type
    return value


def _selector(
    spec: TaskSpec,
    *,
    strategy: str = "exact",
    token_cost=None,
    max_nodes: int = 100_000,
) -> GoalAwareSetSelector:
    return GoalAwareSetSelector(
        lambda _task: spec,
        strategy=strategy,
        rendered_token_cost=token_cost
        or (lambda results: sum(int(result.resource.extras.get("rendered_tokens", 1)) for result in results)),
        max_nodes=max_nodes,
    )


class RoutingContractMatchingTests(unittest.TestCase):
    def test_unknown_schema_provenance_scope_and_missing_fields_never_match(self) -> None:
        requirement = Requirement.from_mapping(
            {"action": "send", "entity_type": "message", "target_scope": "region/east", "mode": "effect"}
        )
        affordance = _affordance("send", "message", scope="region")

        good = ResourceContract.from_mapping(_contract((affordance,)))
        self.assertEqual(match_requirement(requirement, good, "tool"), TruthValue.TRUE)

        wrong_range = ResourceContract.from_mapping(_contract((_affordance("send", "message", scope="region/west"),)))
        self.assertEqual(match_requirement(requirement, wrong_range, "tool"), TruthValue.FALSE)

        unknown_range = ResourceContract.from_mapping(_contract((_affordance("send", "message", scope=""),)))
        self.assertEqual(match_requirement(requirement, unknown_range, "tool"), TruthValue.UNKNOWN)

        unsupported = ResourceContract.from_mapping(
            _contract((affordance,), schema_version=2)
        )
        self.assertEqual(match_requirement(requirement, unsupported, "tool"), TruthValue.UNKNOWN)

        explicit_null = Requirement.from_mapping(
            {"action": "send", "entity_type": "message", "target_scope": None, "mode": "effect"}
        )
        self.assertEqual(match_requirement(explicit_null, good, "tool"), TruthValue.UNKNOWN)
        unknown_mode = Requirement.from_mapping(
            {"action": "send", "entity_type": "message", "mode": "perform"}
        )
        self.assertEqual(match_requirement(unknown_mode, good, "tool"), TruthValue.UNKNOWN)

        missing_evidence = ResourceContract.from_mapping(
            _contract((affordance,), source_evidence=[])
        )
        self.assertEqual(match_requirement(requirement, missing_evidence, "tool"), TruthValue.UNKNOWN)

    def test_skill_instruction_cannot_satisfy_an_effect_requirement(self) -> None:
        spec = _task(_requirement("send", "message"))
        skill = _result(
            _definition(
                "skill.instructions",
                kind="skill",
                affordances=(_affordance("send", "message"),),
            )
        )
        selection = _selector(spec).select([skill], context=SelectionContext(task="send message"))

        self.assertEqual(selection.status, "abstain")
        self.assertNotEqual(selection.status, "selected")

    def test_malformed_and_child_makes_whole_task_spec_uncertain(self) -> None:
        spec = TaskSpec.from_mapping(
            {"requirements": {"all_of": [_requirement("read"), {"malformed": True}]}}
        )
        self.assertTrue(spec.unknown_items)
        result = _selector(spec).select(
            [_result(_definition("tool.reader", affordances=(_affordance("read"),)))],
            context=SelectionContext(task="read"),
        )
        self.assertEqual(result.status, "abstain")
        self.assertIn("uncertain", result.reason)

    def test_call_preconditions_are_not_assumed_without_runtime_evidence(self) -> None:
        spec = _task(_requirement("read"))
        resource = _result(
            _definition(
                "tool.read",
                affordances=(_affordance("read"),),
                contract=_contract(
                    (_affordance("read"),),
                    call_preconditions=({"action": "authorize", "entity_type": "request"},),
                ),
            )
        )
        selection = _selector(spec).select([resource], context=SelectionContext(task="read"))
        self.assertEqual(selection.status, "abstain")
        self.assertIn("runtime evidence", selection.reason)

    def test_directly_constructed_empty_and_unknown_nodes_remain_unknown(self) -> None:
        resource = _result(_definition("tool.read", affordances=(_affordance("read"),)))
        expressions = (
            AllOf(()),
            AllOf((RequirementExpression(),)),  # type: ignore[arg-type]
        )
        for expression in expressions:
            with self.subTest(expression=expression):
                spec = TaskSpec(expression)
                result = _selector(spec).select(
                    [resource], context=SelectionContext(task="read")
                )
                self.assertEqual(result.status, "abstain")
                self.assertIn("uncertain", result.reason)

    def test_explicit_null_permission_and_closure_fields_are_unknown(self) -> None:
        spec = _task(_requirement("read"))
        for malformed in ("permissions", "context_all_of"):
            with self.subTest(field=malformed):
                raw = _contract((_affordance("read"),))
                if malformed == "permissions":
                    raw["permissions"] = None
                else:
                    raw["context"] = {"all_of": None, "one_of": []}
                resource = _result(
                    _definition("tool.read", affordances=(_affordance("read"),), contract=raw)
                )
                selection = _selector(spec).select(
                    [resource], context=SelectionContext(task="read")
                )
                self.assertEqual(selection.status, "abstain")
                self.assertIn("uncertain", selection.reason)

    def test_task_spec_mapping_round_trip_preserves_expression_provenance_and_unknowns(self) -> None:
        spec = TaskSpec.from_mapping(
            {
                "requirements": {
                    "all_of": [
                        _requirement("create", scope="region/north"),
                        {"one_of": [_requirement("send", output_type="email"), _requirement("send", output_type="portal")]},
                    ]
                },
                "prohibited_operations": ["delete"],
                "unknown_items": ["recipient is unclear"],
                "provenance": [{"source": "request", "evidence": "original prompt"}],
                "vocabulary_version": "ontology-v1",
                "vocabulary_hash": "a" * 64,
            }
        )

        restored = TaskSpec.from_mapping(spec.to_mapping())

        self.assertEqual(restored, spec)

    def test_versioned_vocabulary_binding_must_match(self) -> None:
        spec = TaskSpec.from_mapping(
            {
                "requirements": _requirement("read"),
                "vocabulary_version": "ontology-v1",
                "vocabulary_hash": "a" * 64,
            }
        )
        raw = _contract((_affordance("read"),), vocabulary_version="ontology-v1", vocabulary_hash="b" * 64)
        resource = _result(_definition("tool.read", contract=raw))
        selection = _selector(spec).select([resource], context=SelectionContext(task="read"))
        self.assertEqual(selection.status, "abstain")
        self.assertIn("unknown", selection.reason)


class GoalAwareSetSelectorTests(unittest.TestCase):
    def test_and_or_requirements_and_range_match_choose_a_satisfying_alternative(self) -> None:
        spec = TaskSpec.from_mapping(
            {
                "requirements": {
                    "all_of": [
                        _requirement("create", "report", scope="region/north"),
                        {
                            "one_of": [
                                _requirement("send", "report", scope="region/north", output_type="email"),
                                _requirement("send", "report", scope="region/north", output_type="portal"),
                            ]
                        },
                    ]
                }
            }
        )
        create = _result(
            _definition(
                "tool.create",
                affordances=(_affordance("create", "report", scope="region"),),
                rendered_tokens=3,
            )
        )
        email = _result(
            _definition(
                "tool.email",
                affordances=(_affordance("send", "report", scope="region", output_type="email"),),
                rendered_tokens=5,
                cost_estimate=0.5,
            )
        )
        portal = _result(
            _definition(
                "tool.portal",
                affordances=(_affordance("send", "report", scope="region", output_type="portal"),),
                rendered_tokens=2,
                cost_estimate=0.1,
            )
        )

        selection = _selector(spec).select(
            [email, portal, create],
            context=SelectionContext(task="create a regional report and send it"),
        )

        self.assertEqual(selection.status, "selected")
        self.assertEqual(
            {item.resource.metadata.id for item in selection.results},
            {"tool.create", "tool.portal"},
        )

    def test_allowed_alternative_prevents_escalation_and_permissions_are_a_union(self) -> None:
        spec = _task(_requirement("send", "message"))
        protected = _result(
            _definition(
                "tool.protected",
                affordances=(_affordance("send", "message"),),
                required_permissions=("message.send",),
                rendered_tokens=1,
            ),
            score=1.0,
            relevance=1.0,
        )
        permitted = _result(
            _definition(
                "tool.permitted",
                affordances=(_affordance("send", "message"),),
                rendered_tokens=1,
            ),
            score=0.4,
            relevance=0.4,
        )
        selector = _selector(spec)
        selection = selector.select(
            [protected, permitted], context=SelectionContext(task="send message")
        )
        self.assertEqual(selection.status, "selected")
        self.assertEqual([item.resource.metadata.id for item in selection.results], ["tool.permitted"])

        only_protected = selector.select(
            [protected], context=SelectionContext(task="send message")
        )
        self.assertEqual(only_protected.status, "escalate")
        self.assertIn("message.send", only_protected.reason)
        self.assertEqual(only_protected.missing_permissions, ("message.send",))

    def test_contract_permissions_are_counted_with_metadata_permissions(self) -> None:
        spec = _task(_requirement("read"))
        resource = _result(
            _definition(
                "tool.reader",
                affordances=(_affordance("read"),),
                required_permissions=("fs.read",),
                contract_permissions=("network.audit",),
            )
        )
        selector = _selector(spec)
        ctx = SelectionContext(task="read", granted_permissions=("fs.read", "network.audit"))
        selected = selector.select([resource], context=ctx)
        self.assertEqual(selected.status, "selected")
        self.assertEqual(_objective(selected.results, selector.rendered_token_cost)[0], 2)

    def test_metadata_dependencies_and_shared_context_dependencies_are_deduplicated(self) -> None:
        spec = _task(_requirement("create"), _requirement("send"))
        shared = _result(
            _definition(
                "skill.shared",
                kind="skill",
                affordances=(_affordance("explain", mode="context"),),
                rendered_tokens=4,
            )
        )
        create = _result(
            _definition(
                "tool.create",
                affordances=(_affordance("create"),),
                dependencies=("skill.shared@1.0.0",),
            )
        )
        send = _result(
            _definition(
                "tool.send",
                affordances=(_affordance("send"),),
                dependencies=("skill.shared@1.0.0",),
            )
        )

        selection = _selector(spec).select(
            [send, shared, create],
            context=SelectionContext(task="create and send", max_resources=3),
        )
        self.assertEqual(selection.status, "selected")
        self.assertEqual(
            {item.resource.metadata.id for item in selection.results},
            {"skill.shared", "tool.create", "tool.send"},
        )
        self.assertTrue(_selector(spec).validate_selection(selection.results, context=SelectionContext(task="create and send", max_resources=3))[0])

    def test_context_one_of_chooses_cheapest_available_dependency(self) -> None:
        spec = _task(_requirement("read"))
        parent = _result(
            _definition(
                "tool.reader",
                affordances=(_affordance("read"),),
                contract=_contract(
                    (_affordance("read"),),
                    context_one_of=(("skill.large", "skill.small"),),
                ),
            )
        )
        large = _result(
            _definition("skill.large", kind="skill", rendered_tokens=10, cost_estimate=0.2)
        )
        small = _result(
            _definition("skill.small", kind="skill", rendered_tokens=2, cost_estimate=0.1)
        )
        selection = _selector(spec).select(
            [parent, large, small], context=SelectionContext(task="read", max_resources=2)
        )
        self.assertEqual(selection.status, "selected")
        self.assertEqual(
            {item.resource.metadata.id for item in selection.results},
            {"tool.reader", "skill.small"},
        )

    def test_context_one_of_can_choose_one_alternative_to_avoid_a_false_cycle(self) -> None:
        spec = _task(_requirement("read"), _requirement("send"))
        reader = _result(
            _definition(
                "tool.reader",
                affordances=(_affordance("read"),),
                contract=_contract(
                    (_affordance("read"),),
                    context_one_of=(("skill.context", "tool.sender"),),
                ),
            )
        )
        sender = _result(
            _definition(
                "tool.sender",
                affordances=(_affordance("send"),),
                dependencies=("tool.reader",),
            )
        )
        context = _result(_definition("skill.context", kind="skill"))

        selection = _selector(spec).select(
            [sender, reader, context], context=SelectionContext(task="read and send")
        )

        self.assertEqual(selection.status, "selected")
        self.assertEqual(
            {item.resource.metadata.id for item in selection.results},
            {"tool.reader", "tool.sender", "skill.context"},
        )

    def test_missing_version_reference_is_uncertain_not_satisfied(self) -> None:
        spec = _task(_requirement("read"))
        reader = _result(
            _definition(
                "tool.reader",
                affordances=(_affordance("read"),),
                dependencies=("skill.rules@2.0.0",),
            )
        )
        older = _result(_definition("skill.rules", kind="skill", version="1.0.0"))
        selection = _selector(spec).select(
            [reader, older], context=SelectionContext(task="read")
        )
        self.assertEqual(selection.status, "abstain")
        self.assertIn("uncertain", selection.reason)

    def test_ambiguous_bare_dependency_reference_is_uncertain(self) -> None:
        spec = _task(_requirement("read"))
        reader = _result(
            _definition(
                "tool.reader",
                affordances=(_affordance("read"),),
                dependencies=("skill.rules",),
            )
        )
        old = _result(_definition("skill.rules", kind="skill", version="1.0.0"))
        new = _result(_definition("skill.rules", kind="skill", version="2.0.0"))
        selection = _selector(spec).select(
            [reader, old, new], context=SelectionContext(task="read")
        )
        self.assertEqual(selection.status, "abstain")
        self.assertIn("uncertain", selection.reason)

    def test_declared_conflict_count_and_cost_budgets_are_hard_constraints(self) -> None:
        spec = _task(_requirement("read"))
        expensive = _result(
            _definition(
                "tool.expensive",
                affordances=(_affordance("read"),),
                cost_estimate=10,
                conflicts_with=("tool.safe",),
                rendered_tokens=1,
            ),
            score=1,
            relevance=1,
        )
        safe = _result(
            _definition(
                "tool.safe",
                affordances=(_affordance("read"),),
                cost_estimate=1,
                rendered_tokens=2,
            ),
            score=0.5,
            relevance=0.5,
        )
        selection = _selector(spec).select(
            [expensive, safe],
            context=SelectionContext(task="read", budget_cost=2, max_resources=1),
        )
        self.assertEqual(selection.status, "selected")
        self.assertEqual(selection.results[0].resource.metadata.id, "tool.safe")

    def test_rendered_context_budget_can_outweigh_permission_minimization(self) -> None:
        spec = _task(_requirement("read"))
        no_permission_but_too_large = _result(
            _definition(
                "tool.large",
                affordances=(_affordance("read"),),
                rendered_tokens=500,
            ),
            relevance=0.9,
        )
        one_granted_permission = _result(
            _definition(
                "tool.compact",
                affordances=(_affordance("read"),),
                required_permissions=("fs.read",),
                rendered_tokens=150,
            ),
            relevance=0.8,
        )
        selection = _selector(spec).select(
            [no_permission_but_too_large, one_granted_permission],
            context=SelectionContext(
                task="read",
                granted_permissions=("fs.read",),
                context_token_budget=200,
            ),
        )
        self.assertEqual(selection.status, "selected")
        self.assertEqual(selection.results[0].resource.metadata.id, "tool.compact")

    def test_low_relevance_dependency_is_retained_but_low_relevance_root_is_not(self) -> None:
        spec = _task(_requirement("read"))
        instructions = _result(
            _definition("skill.instructions", kind="skill", rendered_tokens=3),
            score=0.1,
            relevance=0.1,
        )
        reader = _result(
            _definition(
                "tool.reader",
                affordances=(_affordance("read"),),
                dependencies=("skill.instructions",),
            ),
            score=0.9,
            relevance=0.9,
        )
        selector = _selector(spec)
        context = SelectionContext(task="read", min_relevance=0.5)

        dependent = selector.select([instructions, reader], context=context)
        self.assertEqual(dependent.status, "selected")
        self.assertEqual(
            {item.resource.metadata.id for item in dependent.results},
            {"tool.reader", "skill.instructions"},
        )

        isolated = selector.select([instructions], context=context)
        self.assertEqual(isolated.status, "abstain")

    def test_greedy_does_not_escalate_when_a_feasible_allowed_alternative_exists(self) -> None:
        spec = _task(_requirement("send", "message"))
        protected = _result(
            _definition(
                "tool.a-protected",
                affordances=(_affordance("send", "message"),),
                required_permissions=("send",),
            )
        )
        allowed = _result(
            _definition("tool.b-allowed", affordances=(_affordance("send", "message"),)),
            score=0.5,
            relevance=0.5,
        )
        result = _selector(spec, strategy="greedy").select(
            [protected, allowed], context=SelectionContext(task="send message")
        )
        self.assertEqual(result.status, "selected")
        self.assertEqual(result.results[0].resource.metadata.id, "tool.b-allowed")

    def test_exact_limit_returns_uncertain_without_solution_and_unproven_with_solution(self) -> None:
        impossible = _task(_requirement("archive"))
        one_candidate = _result(
            _definition("tool.read", affordances=(_affordance("read"),))
        )
        none_found = _selector(impossible, max_nodes=1).select(
            [one_candidate], context=SelectionContext(task="archive")
        )
        self.assertEqual(none_found.status, "abstain")
        self.assertIn("uncertain", none_found.reason)

        satisfiable = _task(_requirement("read"))
        one_found = _selector(satisfiable, max_nodes=1).select(
            [one_candidate], context=SelectionContext(task="read")
        )
        self.assertEqual(one_found.status, "selected")
        self.assertIn("optimality unproven", one_found.reason)

    def test_validate_selection_rechecks_compiled_ids_and_trimmed_resources(self) -> None:
        spec = _task(_requirement("read"))
        result = _result(_definition("tool.read", affordances=(_affordance("read"),)))
        selector = _selector(spec)
        context = SelectionContext(task="read")
        complete = CompiledContext(
            system_prompt="",
            messages=(),
            tools=(),
            resource_ids=(result.resource.identity,),
            estimated_tokens=5,
        )
        self.assertTrue(selector.validate_selection([result], context=context, compiled=complete)[0])
        trimmed = CompiledContext(
            system_prompt="",
            messages=(),
            tools=(),
            resource_ids=(result.resource.identity,),
            estimated_tokens=5,
            trimmed_resource_ids=(result.resource.identity,),
        )
        valid, reason = selector.validate_selection([result], context=context, compiled=trimmed)
        self.assertFalse(valid)
        self.assertIn("trimmed", reason)

    def test_frozen_task_spec_skips_provider_until_explicit_resolution(self) -> None:
        spec = _task(_requirement("read"))
        calls: list[str] = []

        def provider(task: str) -> TaskSpec:
            calls.append(task)
            return spec

        selector = GoalAwareSetSelector(provider, strategy="exact")
        resource = _result(_definition("tool.read", affordances=(_affordance("read"),)))
        context = SelectionContext(task="read", task_spec=spec)
        selection = selector.select([resource], context=context)
        valid, _ = selector.validate_selection(selection.results, context=context)

        self.assertEqual(selection.status, "selected")
        self.assertTrue(valid)
        self.assertEqual(calls, [])
        self.assertEqual(selector.resolve_task_spec("fresh task"), spec)
        self.assertEqual(calls, ["fresh task"])

    def test_exact_matches_an_independent_exhaustive_oracle_on_small_cases(self) -> None:
        spec = _task(_requirement("read"))
        candidates = [
            _result(
                _definition(
                    "tool.a-needs-right",
                    affordances=(_affordance("read"),),
                    contract_permissions=("network",),
                    rendered_tokens=1,
                    cost_estimate=0.0,
                ),
                relevance=1.0,
            ),
            _result(
                _definition("tool.b", affordances=(_affordance("read"),), rendered_tokens=3, cost_estimate=0.4),
                relevance=0.7,
            ),
            _result(
                _definition("tool.c", affordances=(_affordance("read"),), rendered_tokens=2, cost_estimate=0.8),
                relevance=0.8,
            ),
            _result(
                _definition("tool.d", affordances=(_affordance("read"),), rendered_tokens=2, cost_estimate=0.2),
                relevance=0.7,
            ),
            _result(
                _definition("tool.e", affordances=(_affordance("read"),), rendered_tokens=2, cost_estimate=0.2),
                relevance=0.9,
            ),
        ]
        context = SelectionContext(
            task="read",
            granted_permissions=("fs.read",),
            budget_cost=1.0,
            max_resources=3,
            per_kind_limits={"tool": 2},
        )
        def token_cost(selected):
            return sum(int(item.resource.extras["rendered_tokens"]) for item in selected)

        selector = _selector(spec, token_cost=token_cost)

        oracle_options = []
        for size in range(len(candidates) + 1):
            for subset in combinations(candidates, size):
                ids = {item.resource.metadata.id for item in subset}
                permissions = set().union(
                    *(
                        set(item.resource.metadata.required_permissions)
                        | set(ResourceContract.from_resource(item.resource).permissions)
                        for item in subset
                    )
                ) if subset else set()
                if permissions - set(context.granted_permissions):
                    continue
                if size > context.max_resources or size > context.per_kind_limits["tool"]:
                    continue
                total_cost = sum(item.resource.metadata.cost_estimate for item in subset)
                if total_cost > context.budget_cost:
                    continue
                if not any(
                    any(
                        affordance.action == "read"
                        for affordance in ResourceContract.from_resource(item.resource).affordances
                    )
                    for item in subset
                ):
                    continue
                token_total = sum(int(item.resource.extras["rendered_tokens"]) for item in subset)
                maximum_relevance = max((item.components["relevance"] for item in subset), default=0.0)
                id_column = tuple(sorted(item.resource.identity.casefold() for item in subset))
                oracle_options.append(
                    ((len(permissions), token_total, total_cost, -maximum_relevance, id_column), ids)
                )
        expected = min(oracle_options)[1]

        actual = selector.select(candidates, context=context)
        self.assertEqual(actual.status, "selected")
        self.assertEqual({item.resource.metadata.id for item in actual.results}, expected)

    def test_partition_and_duplicate_invariance_preserve_coverage_and_prefix_objective(self) -> None:
        spec = _task(_requirement("create"), _requirement("send"))
        unified = _result(
            _definition(
                "tool.z-unified",
                affordances=(_affordance("create"), _affordance("send")),
                rendered_tokens=5,
                cost_estimate=0.4,
            ),
            relevance=0.8,
        )
        create = _result(
            _definition(
                "tool.a-create",
                affordances=(_affordance("create"),),
                rendered_tokens=2,
                cost_estimate=0.2,
            ),
            relevance=0.8,
        )
        send = _result(
            _definition(
                "tool.b-send",
                affordances=(_affordance("send"),),
                rendered_tokens=3,
                cost_estimate=0.2,
            ),
            relevance=0.8,
        )
        def token_cost(selected):
            return sum(int(item.resource.extras["rendered_tokens"]) for item in selected)

        selector = _selector(spec, token_cost=token_cost)
        context = SelectionContext(task="create and send", max_resources=3)
        together = selector.select([unified], context=context)
        split = selector.select([send, create], context=context)
        duplicate = selector.select([unified, unified], context=context)

        self.assertEqual(together.status, "selected")
        self.assertEqual(split.status, "selected")
        self.assertEqual(duplicate.status, "selected")
        self.assertEqual([item.resource.identity for item in duplicate.results], [unified.resource.identity])
        together_objective = _objective(together.results, token_cost)
        split_objective = _objective(split.results, token_cost)
        self.assertEqual(together_objective[:3], split_objective[:3])
        self.assertEqual(together_objective[3], split_objective[3])


if __name__ == "__main__":
    unittest.main()
