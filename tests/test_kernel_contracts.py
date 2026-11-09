from __future__ import annotations

import unittest
from dataclasses import replace

from marmo_core import (
    BoundTool, ContextCompiler, GreedyConstrainedSetSelector, HitlResponse,
    Kernel, MockLLMProvider, ResourceDefinition, ResourceRegistry, SearchResult,
)
from marmo_core.retriever import Retriever


def definition(rid, kind, **extra):
    data = dict(id=rid, kind=kind, name=rid, version="1.0.0", description="operation procedure",
                capabilities=[], input_summary="in", output_summary="out", required_permissions=[],
                cost_estimate=0.0, latency_class="fast", side_effect="none", trust_level="core",
                ref=f"{kind}://{rid}", tags=[])
    data.update(extra)
    return ResourceDefinition.from_mapping(data)


class FixedRetriever(Retriever):
    budget_aware = True

    def __init__(self, results):
        self.results = results

    def search(self, registry, query):
        return self.results


class CheckingSelector(GreedyConstrainedSetSelector):
    requires_contract_verification = True

    def __init__(self):
        super().__init__()
        self.validated_tasks = []

    def validate_selection(self, results, *, context, compiled=None):
        self.validated_tasks.append(context.task)
        ids = {r.resource.id for r in results}
        valid = "tool.operation" in ids and all(
            set(r.resource.metadata.dependencies) <= ids for r in results
        )
        return valid, "required operation and its procedure must reach the model"


class KernelContractTests(unittest.TestCase):
    def build(self, *, small_budget=False, unsafe_compiler=False, trust="core", side_effect="none"):
        skill = definition("skill.procedure", "skill", instructions="required instructions " * 500,
                           trust_level=trust)
        tool = definition("tool.operation", "tool", dependencies=[skill.id], side_effect=side_effect,
                          input_schema={"type": "object", "properties": {}})
        registry = ResourceRegistry()
        registry.extend([skill, tool])
        results = [SearchResult(tool, 0.9, (), {"relevance": 0.9}),
                   SearchResult(skill, 0.4, (), {"relevance": 0.4})]
        llm = MockLLMProvider()
        calls = []
        selector = CheckingSelector()
        budget = None
        if small_budget:
            bound = BoundTool(tool, tool.extras["input_schema"], {}, lambda: None)
            budget = max(
                ContextCompiler().compile("Do the operation", tools=[bound]).estimated_tokens,
                ContextCompiler().compile("Do the operation").estimated_tokens,
            ) + 5
        kernel = Kernel(registry, llm, retriever=FixedRetriever(results), selector=selector,
                        compiler=ContextCompiler() if unsafe_compiler else None,
                        context_token_budget=budget,
                        tool_implementations={tool.id: lambda: calls.append(True)})
        return kernel, llm, calls, selector

    def test_dependency_omission_stops_before_model_even_with_custom_legacy_compiler(self):
        kernel, llm, calls, _ = self.build(small_budget=True, unsafe_compiler=True)
        result = kernel.run_goal("Do the operation")
        self.assertEqual(result.status, "failed", result.detail)
        self.assertIn("compiled selection contract failed", result.detail)
        self.assertEqual(llm.requests, [])
        self.assertEqual(calls, [])

    def test_default_compiler_preserves_dependency_units(self):
        kernel, llm, calls, _ = self.build(small_budget=True)
        result = kernel.run_goal("Do the operation")
        self.assertEqual(result.status, "failed", result.detail)
        compiled = next(r.payload for r in kernel.audit_log.records if r.kind == "compile")
        self.assertEqual(compiled["resource_ids"], [])
        self.assertEqual(llm.requests, [])
        self.assertEqual(calls, [])

    def test_activation_failure_invalidates_parent_before_model(self):
        kernel, llm, calls, _ = self.build(trust="untrusted")
        result = kernel.run_goal("Do the operation")
        self.assertEqual(result.status, "failed", result.detail)
        self.assertEqual(llm.requests, [])
        self.assertEqual(calls, [])

    def test_custom_compiler_cannot_rewrite_content_under_same_ids(self):
        class RewritingCompiler(ContextCompiler):
            def compile(self, *args, **kwargs):
                compiled = super().compile(*args, **kwargs)
                messages = tuple(replace(message, content="rewritten content")
                                 for message in compiled.messages)
                return replace(compiled, messages=messages)
        kernel, llm, calls, _ = self.build()
        kernel.compiler = RewritingCompiler()
        result = kernel.run_goal("Do the operation")
        self.assertEqual(result.status, "failed", result.detail)
        self.assertIn("payload differs", result.detail)
        self.assertEqual(llm.requests, [])
        self.assertEqual(calls, [])

    def test_complete_compiled_set_can_execute(self):
        kernel, llm, calls, selector = self.build()
        result = kernel.run_goal("Do the operation")
        self.assertEqual(result.status, "completed", result.detail)
        self.assertEqual(calls, [True])
        self.assertTrue(llm.requests)
        self.assertEqual(selector.validated_tasks, ["Do the operation"])

    def test_resume_validates_frozen_selection_with_task_context(self):
        kernel, _, calls, selector = self.build(side_effect="write")
        paused = kernel.run_goal("Do the operation")
        self.assertTrue(paused.paused, paused.detail)
        resumed = kernel.resume(paused.task_id, HitlResponse(kind="approve"))
        self.assertEqual(resumed.status, "completed", resumed.detail)
        self.assertEqual(calls, [True])
        self.assertEqual(selector.validated_tasks, ["Do the operation"])


class GoalAwareKernelTests(unittest.TestCase):
    def test_resume_does_not_charge_selected_resource_estimates_twice(self):
        from decimal import Decimal
        from marmo_core import (
            GoalAwareSetSelector, HitlPolicy, LLMResponse, ModelPrice,
            PendingHitlBroker, TaskBudget, TaskSpec, ToolCall,
        )
        evidence = [{"source": "fixture", "evidence": "declared operation"}]
        registry = ResourceRegistry()
        results = []
        for action in ("read", "send"):
            contract = {"schema_version": 1, "observed": True, "complete": True,
                        "context": {}, "permissions": [], "call_preconditions": [],
                        "source_evidence": evidence, "affordances": [{
                            "action": action, "entity_type": "message", "supported_scope": "workspace",
                            "output_type": "receipt", "mode": "effect", "provenance": evidence}]}
            tool = definition(f"tool.{action}", "tool", cost_estimate=.4,
                              routing_contract=contract,
                              input_schema={"type": "object", "properties": {}})
            registry.add(tool)
            results.append(SearchResult(tool, .9, (), {"relevance": .9}))
        spec = TaskSpec.from_mapping({"requirements": [{
            "action": action, "entity_type": "message", "target_scope": "workspace",
            "output_type": "receipt", "mode": "effect"} for action in ("read", "send")]})
        llm = MockLLMProvider(script=[
            LLMResponse(content="", tool_calls=(ToolCall("first", "tool.read", {}), ToolCall("second", "tool.send", {}))),
            LLMResponse(content="done"),
        ])
        calls = []
        kernel = Kernel(
            registry, llm, retriever=FixedRetriever(results),
            selector=GoalAwareSetSelector(lambda _: spec, strategy="exact"),
            tool_implementations={"tool.read": lambda: calls.append("read"),
                                  "tool.send": lambda: calls.append("send")},
            hitl=PendingHitlBroker(HitlPolicy(always_confirm_resources=("tool.send",))),
            task_budget=TaskBudget(amount=Decimal("0.9"), currency="USD", resource_cost_unit="USD",
                model_price=ModelPrice(Decimal(0), Decimal(0), 4096, 1024)),
        )
        paused = kernel.run_goal("read and send")
        self.assertTrue(paused.paused, paused.detail)
        self.assertEqual(calls, ["read"])
        self.assertEqual(Decimal(kernel.budget_status(paused.task_id)["remaining"]), Decimal("0.5"))
        resumed = kernel.resume(paused.task_id, HitlResponse(kind="approve"))
        self.assertEqual(resumed.status, "completed", resumed.detail)
        self.assertEqual(calls, ["read", "send"])
        self.assertEqual(Decimal(kernel.budget_status(resumed.task_id)["spent"]), Decimal("0.8"))

    def test_task_spec_extraction_failure_stops_before_model(self):
        from marmo_core import GoalAwareSetSelector
        def unavailable(goal):
            raise RuntimeError("provider unavailable")
        llm = MockLLMProvider()
        kernel = Kernel(ResourceRegistry(), llm, selector=GoalAwareSetSelector(unavailable))
        result = kernel.run_goal("send the message")
        self.assertEqual(result.status, "failed")
        self.assertIn("TaskSpec extraction failed", result.detail)
        self.assertEqual(llm.requests, [])

    def test_permission_needed_for_final_effect_is_not_hidden_by_support_skill(self):
        from marmo_core.routing_contracts import TaskSpec
        from marmo_core.sufficient_selector import GoalAwareSetSelector
        evidence = [{"source": "fixture", "evidence": "declared operation"}]
        def contract(action, mode):
            return {"schema_version": 1, "observed": True, "complete": True,
                    "context": {}, "permissions": [], "call_preconditions": [],
                        "source_evidence": evidence, "affordances": [{
                        "action": action, "entity_type": "message", "supported_scope": "workspace",
                        "output_type": "receipt", "mode": mode, "provenance": evidence}]}
        skill = definition("skill.procedure", "skill", instructions="how to send",
                           routing_contract=contract("send", "context"))
        tool = definition("tool.operation", "tool", dependencies=[skill.id],
                          required_permissions=["mail.send"],
                          routing_contract=contract("send", "effect"),
                          input_schema={"type": "object", "properties": {}})
        registry = ResourceRegistry()
        registry.extend([skill, tool])
        spec = TaskSpec.from_mapping({"requirements": [{
            "action": "send", "entity_type": "message", "target_scope": "workspace",
            "output_type": "receipt", "mode": "effect"}]})
        extractions = []
        def provider(goal):
            extractions.append(goal)
            if len(extractions) > 1:
                raise AssertionError("TaskSpec must not be re-extracted")
            return spec
        selector = GoalAwareSetSelector(provider, strategy="exact")
        read_tool = definition("tool.read", "tool", routing_contract=contract("read", "effect"),
                               input_schema={"type": "object", "properties": {}})
        registry.add(read_tool)
        results = [SearchResult(read_tool, 1.0, (), {"relevance": 1.0}),
                   SearchResult(tool, .9, (), {"relevance": .9}),
                   SearchResult(skill, .4, (), {"relevance": .4})]
        llm = MockLLMProvider()
        kernel = Kernel(registry, llm, selector=selector, retriever=FixedRetriever(results),
                        tool_implementations={tool.id: lambda: "sent"})
        result = kernel.run_goal("send the message")
        self.assertTrue(result.paused, result.detail)
        self.assertIn("selection escalated", result.detail)
        self.assertEqual(llm.requests, [])
        self.assertEqual(result.hitl.arguments["missing_permissions"], ["mail.send"])
        resumed = kernel.resume(result.task_id, HitlResponse(kind="approve"))
        self.assertEqual(resumed.status, "completed", resumed.detail)
        self.assertEqual(extractions, ["send the message"])
        self.assertIn("routing_task_spec", kernel.get_state(result.task_id)["snapshot"])


if __name__ == "__main__":
    unittest.main()
