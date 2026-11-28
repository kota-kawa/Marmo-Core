from __future__ import annotations

from dataclasses import replace
from itertools import combinations
import random
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
    output_type: str | None = "receipt",
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
    scope: str | None = "global",
    mode: str = "effect",
    output_type: str | None = "receipt",
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
            {"action": "send", "entity_type": "message", "target_scope": "region/east", "output_type": "receipt", "mode": "effect"}
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

    def test_malformed_affordance_invalidates_otherwise_matching_contract(self) -> None:
        spec = _task(_requirement("read"))
        resource = _result(
            _definition(
                "tool.read",
                contract=_contract(
                    (
                        _affordance("read"),
                        {"action": "archive", "entity_type": "document", "supported_scope": "global", "mode": "perform"},
                    )
                ),
            )
        )
        selection = _selector(spec).select(
            [resource], context=SelectionContext(task="read")
        )
        self.assertEqual(selection.status, "abstain")
        self.assertIn("unknown", selection.reason)

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

    def test_context_one_of_search_backtracks_when_first_alternative_leaves_a_low_relevance_root(self) -> None:
        spec = _task(_requirement("read"), _requirement("fetch"))
        parent = _result(
            _definition(
                "tool.reader",
                affordances=(_affordance("read"),),
                contract=_contract(
                    (_affordance("read"),),
                    context_one_of=(("skill.a-primary", "skill.b-fallback"),),
                ),
            )
        )
        primary = _result(
            _definition("skill.a-primary", kind="skill"), score=0.9, relevance=0.9
        )
        fallback = _result(
            _definition(
                "skill.b-fallback",
                affordances=(_affordance("fetch"),),
            ),
            score=0.1,
            relevance=0.1,
        )
        context = SelectionContext(task="read", min_relevance=0.5)

        # Choosing skill.a-primary first would leave skill.b-fallback as an
        # unreferenced, below-threshold root; choosing skill.b-fallback keeps
        # the same three resources valid.
        valid, reason = _selector(spec).validate_selection(
            [parent, primary, fallback], context=context
        )
        self.assertTrue(valid, reason)

        # When no alternative leaves eligible roots the reason names the roots.
        valid, reason = _selector(spec).validate_selection(
            [parent, fallback],
            context=SelectionContext(task="read", min_relevance=0.95),
        )
        self.assertFalse(valid)
        self.assertIn("below the active score or relevance threshold", reason)

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

    def test_context_token_budget_requires_an_explicit_renderer_callback(self) -> None:
        spec = _task(_requirement("read"))
        result = _result(_definition("tool.read", affordances=(_affordance("read"),)))
        selector = GoalAwareSetSelector(lambda _task: spec, strategy="exact")
        context = SelectionContext(task="read", context_token_budget=100)

        selection = selector.select([result], context=context)
        valid, reason = selector.validate_selection([result], context=context)

        self.assertEqual(selection.status, "abstain")
        self.assertIn("explicit rendered_token_cost", selection.reason)
        self.assertFalse(valid)
        self.assertIn("uncertain", reason)

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
        one_found = GoalAwareSetSelector(
            lambda _task: satisfiable, strategy="exact", max_nodes=1
        ).select(
            [one_candidate], context=SelectionContext(task="read")
        )
        self.assertEqual(one_found.status, "selected")
        self.assertIn("optimality unproven", one_found.reason)
        self.assertIn("metadata token proxy", one_found.reason)

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
        self.assertIn("custom rendered_token_cost", actual.reason)

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


    def _six_requirement_pool(self, protected_action: str | None = None) -> tuple[TaskSpec, list[SearchResult]]:
        """Six requirements, three alternatives each, and four distractors: 22 candidates."""

        actions = ("read", "create", "send", "archive", "update", "delete")
        candidates = []
        for action_index, action in enumerate(actions):
            for variant in range(3):
                needs_permission = action == protected_action or (
                    protected_action is None and variant == 0
                )
                candidates.append(
                    _result(
                        _definition(
                            f"tool.{action}-{variant}",
                            affordances=(_affordance(action),),
                            required_permissions=(f"perm.{action}",) if needs_permission else (),
                            rendered_tokens=10 + 3 * variant + action_index,
                            cost_estimate=0.01 * (variant + 1),
                        ),
                        score=0.9 - 0.05 * variant,
                        relevance=0.9 - 0.05 * variant,
                    )
                )
        for index in range(4):
            candidates.append(
                _result(
                    _definition(
                        f"tool.distractor-{index}",
                        affordances=(_affordance("summarize"),),
                        rendered_tokens=8,
                    ),
                    score=0.6,
                    relevance=0.6,
                )
            )
        return _task(*(_requirement(action) for action in actions)), candidates

    def test_exact_proves_the_optimum_for_six_requirements_within_a_small_node_budget(self) -> None:
        spec, candidates = self._six_requirement_pool()
        selection = _selector(spec, max_nodes=2_000).select(
            candidates, context=SelectionContext(task="six steps", max_resources=8)
        )
        self.assertEqual(selection.status, "selected")
        self.assertIn("optimum proven", selection.reason)
        self.assertEqual(
            [item.resource.metadata.id for item in selection.results],
            [
                "tool.archive-1",
                "tool.create-1",
                "tool.delete-1",
                "tool.read-1",
                "tool.send-1",
                "tool.update-1",
            ],
        )

    def test_exact_escalates_when_only_permissions_are_missing_for_six_requirements(self) -> None:
        spec, candidates = self._six_requirement_pool(protected_action="send")
        selection = _selector(spec, max_nodes=2_000).select(
            candidates, context=SelectionContext(task="six steps", max_resources=8)
        )
        self.assertEqual(selection.status, "escalate")
        self.assertEqual(selection.missing_permissions, ("perm.send",))
        self.assertIn("only with additional permissions", selection.reason)

    def test_truncated_exact_search_escalates_without_claiming_permissions_are_the_only_gap(self) -> None:
        # The granted sender is over budget, so no set within the granted
        # permissions exists; the shared dependency keeps the search from
        # ruling that out inside the node budget.
        spec = _task(_requirement("read"), _requirement("send", "message"))
        candidates = [
            _result(_definition("tool.base")),
            *(
                _result(
                    _definition(
                        f"tool.read-{index}",
                        affordances=(_affordance("read"),),
                        dependencies=("tool.base",),
                    )
                )
                for index in range(8)
            ),
            _result(
                _definition(
                    "tool.send-open", affordances=(_affordance("send", "message"),), cost_estimate=5
                )
            ),
            _result(
                _definition(
                    "tool.send-protected",
                    affordances=(_affordance("send", "message"),),
                    required_permissions=("perm.send",),
                    cost_estimate=0.1,
                )
            ),
        ]
        context = SelectionContext(task="read and send", max_resources=12, budget_cost=1)

        truncated = _selector(spec, max_nodes=150).select(candidates, context=context)
        self.assertEqual(truncated.status, "escalate")
        self.assertEqual(truncated.missing_permissions, ("perm.send",))
        self.assertIn("max_nodes=150", truncated.reason)
        self.assertNotIn("only with additional permissions", truncated.reason)

        complete = _selector(spec).select(candidates, context=context)
        self.assertEqual(complete.status, "escalate")
        self.assertEqual(complete.missing_permissions, ("perm.send",))
        self.assertIn("only with additional permissions", complete.reason)

    def test_exact_reason_says_when_a_smaller_permission_request_was_not_ruled_out(self) -> None:
        spec = _task(_requirement("read"), _requirement("send", "message"))
        candidates = [
            _result(_definition("tool.0base")),
            *(
                _result(_definition(f"tool.0x{index}", dependencies=("tool.0base",)))
                for index in range(7)
            ),
            _result(_definition("tool.a-cheap", affordances=(_affordance("read"),), rendered_tokens=9)),
            _result(
                _definition(
                    "tool.a-exp",
                    affordances=(_affordance("read"),),
                    required_permissions=("p1",),
                    rendered_tokens=1,
                )
            ),
            _result(
                _definition(
                    "tool.b",
                    affordances=(_affordance("send", "message"),),
                    required_permissions=("p2",),
                )
            ),
        ]
        context = SelectionContext(task="read and send", max_resources=12)

        truncated = _selector(spec, max_nodes=40).select(candidates, context=context)
        self.assertEqual(truncated.status, "escalate")
        self.assertEqual(truncated.missing_permissions, ("p2",))
        self.assertIn("before it could rule out a smaller permission request", truncated.reason)

        complete = _selector(spec).select(candidates, context=context)
        self.assertEqual(complete.status, "escalate")
        self.assertEqual(complete.missing_permissions, ("p2",))
        self.assertTrue(complete.reason.startswith("a satisfying set exists only with"))

    def test_exact_does_not_pad_the_set_with_a_free_resource_that_satisfies_nothing_new(self) -> None:
        spec = _task(_requirement("read"))
        needed = _result(
            _definition("tool.b-read", affordances=(_affordance("read"),), rendered_tokens=2),
            relevance=0.5,
        )
        free_extra = _result(
            _definition("tool.a-free", affordances=(_affordance("summarize"),), rendered_tokens=0),
            relevance=1.0,
        )
        selection = _selector(spec).select(
            [needed, free_extra], context=SelectionContext(task="read", max_resources=2)
        )
        self.assertEqual(selection.status, "selected")
        self.assertEqual([item.resource.metadata.id for item in selection.results], ["tool.b-read"])

    def test_exact_pruning_matches_exhaustive_enumeration_on_random_pools_with_dependencies(self) -> None:
        def token_cost(selected):
            return sum(int(item.resource.extras["rendered_tokens"]) for item in selected)

        rng = random.Random(103)
        actions = ("read", "create", "send", "archive")
        outcomes: dict[str, int] = {}
        for _case in range(150):
            ids = [f"tool.r{index}" for index in range(rng.randint(1, 7))]
            candidates = []
            for resource_id in ids:
                others = [item for item in ids if item != resource_id]
                dependencies = tuple(rng.sample(others, min(len(others), rng.choice((0, 0, 0, 1, 2)))))
                context_all_of = tuple(rng.sample(others, min(len(others), rng.choice((0, 0, 0, 1)))))
                context_one_of = (
                    (tuple(rng.sample(others, 2)),) if len(others) >= 2 and rng.random() < 0.2 else ()
                )
                conflicts = tuple(rng.sample(others, min(len(others), rng.choice((0, 0, 0, 1)))))
                score = rng.choice((0.9, 0.7, 0.2))
                candidates.append(
                    _result(
                        _definition(
                            resource_id,
                            dependencies=dependencies,
                            conflicts_with=conflicts,
                            required_permissions=tuple(rng.sample(("p1", "p2"), rng.choice((0, 0, 1)))),
                            cost_estimate=rng.choice((0.1, 0.2, 0.5)),
                            rendered_tokens=rng.randint(1, 6),
                            contract=_contract(
                                tuple(
                                    _affordance(action)
                                    for action in rng.sample((*actions, "noop"), rng.randint(0, 2))
                                ),
                                context_all_of=context_all_of,
                                context_one_of=context_one_of,
                            ),
                        ),
                        score=score,
                        relevance=score,
                    )
                )
            spec = _task(*(_requirement(action) for action in rng.sample(actions, rng.randint(1, 2))))
            context = SelectionContext(
                task="random",
                granted_permissions=tuple(rng.sample(("p1", "p2"), rng.randint(0, 2))),
                max_resources=rng.randint(1, 5),
                budget_cost=rng.choice((None, 0.8)),
                min_score=rng.choice((0.0, 0.5)),
            )
            selector = _selector(spec, token_cost=token_cost)

            relaxed_context = replace(context, enforce_permissions=False)
            valid_objectives = []
            satisfiable_with_more_permissions = False
            for size in range(len(candidates) + 1):
                for subset in combinations(candidates, size):
                    if selector.validate_selection(subset, context=context)[0]:
                        valid_objectives.append(_objective(subset, token_cost)[:3])
                    elif selector.validate_selection(subset, context=relaxed_context)[0]:
                        satisfiable_with_more_permissions = True

            selection = selector.select(candidates, context=context)
            outcomes[selection.status] = outcomes.get(selection.status, 0) + 1
            if valid_objectives:
                self.assertEqual(selection.status, "selected")
                self.assertIn("optimum proven", selection.reason)
                self.assertEqual(_objective(selection.results, token_cost)[:3], min(valid_objectives))
            elif satisfiable_with_more_permissions:
                self.assertEqual(selection.status, "escalate")
                self.assertTrue(selection.missing_permissions)
            else:
                self.assertEqual(selection.status, "abstain")
        self.assertGreaterEqual(outcomes.get("selected", 0), 20)
        self.assertGreaterEqual(outcomes.get("escalate", 0), 5)

if __name__ == "__main__":
    unittest.main()
