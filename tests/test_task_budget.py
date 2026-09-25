from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal
from pathlib import Path
import tempfile
import unittest

from marmo_core import (
    BudgetExceededError,
    BudgetLedger,
    BeamSearchSetSelector,
    BranchAndBoundSetSelector,
    GreedyConstrainedSetSelector,
    HydeRetriever,
    InMemoryStateStore,
    JsonFileStateStore,
    Kernel,
    LLMPlanner,
    LLMResponse,
    LLMSetSelector,
    LexicalRetriever,
    MockLLMProvider,
    ModelPrice,
    PolicyContext,
    ProviderError,
    RecoveryManager,
    ResourceDefinition,
    ResourceRegistry,
    RuleBasedSetSelector,
    SearchResult,
    SelectionContext,
    RetryPolicy,
    TaskBudget,
    ToolResult,
)


def _budget(amount: str, *, input_price: str = "0", output_price: str = "0") -> TaskBudget:
    return TaskBudget(
        amount=Decimal(amount),
        currency="USD",
        resource_cost_unit="USD",
        model_price=ModelPrice(
            input_per_million=Decimal(input_price),
            output_per_million=Decimal(output_price),
            max_input_tokens=1000,
            max_output_tokens=1000,
        ),
    )


def _tool(
    resource_id: str, cost: float, *, side_effect: str = "none", compensated_by: str = ""
) -> ResourceDefinition:
    fields = {
            "id": resource_id,
            "kind": "tool",
            "name": resource_id,
            "version": "1.0.0",
            "description": "Add one to a number",
            "capabilities": ["addition"],
            "input_summary": "number",
            "output_summary": "number",
            "required_permissions": [],
            "cost_estimate": cost,
            "latency_class": "fast",
            "side_effect": side_effect,
            "trust_level": "core",
            "ref": "tool://test/add",
            "tags": ["math"],
            "input_schema": {
                "type": "object",
                "required": ["value"],
                "properties": {"value": {"type": "integer"}},
            },
        }
    if compensated_by:
        fields["compensated_by"] = compensated_by
    return ResourceDefinition.from_mapping(fields)


class TaskBudgetTests(unittest.TestCase):
    def test_default_selection_and_dispatch_respect_remaining_task_cost(self) -> None:
        registry = ResourceRegistry()
        registry.add(_tool("tool.test.first", 4.0))
        registry.add(_tool("tool.test.second", 4.0))
        kernel = Kernel(
            registry,
            MockLLMProvider(tool_arguments={"tool.test.first": {"value": 1}}),
            tool_implementations={
                "tool.test.first": lambda value: {"value": value + 1},
                "tool.test.second": lambda value: {"value": value + 2},
            },
            task_budget=_budget("5"),
        )

        result = kernel.run_goal("Add one")

        self.assertEqual(result.status, "completed", result.detail)
        self.assertEqual(len(result.tool_results), 1)
        self.assertEqual(kernel.budget_status(result.task_id)["spent"], "4.0")
        selected = [record.payload["selected"] for record in kernel.audit_log.records if record.kind == "retrieve"]
        self.assertEqual(len(selected[0]), 1)
        self.assertIn(selected[0][0], {"tool.test.first@1.0.0", "tool.test.second@1.0.0"})

    def test_retry_cannot_start_after_first_attempt_uses_budget(self) -> None:
        registry = ResourceRegistry()
        registry.add(_tool("tool.test.first", 3.0))
        calls = 0

        def flaky(value: int) -> dict[str, int]:
            nonlocal calls
            calls += 1
            raise ConnectionError("temporary")

        kernel = Kernel(
            registry,
            MockLLMProvider(tool_arguments={"tool.test.first": {"value": 1}}),
            tool_implementations={"tool.test.first": flaky},
            task_budget=_budget("5"),
            recovery=RecoveryManager(retry_policy=RetryPolicy(max_attempts=3, initial_backoff_seconds=0)),
        )

        result = kernel.run_goal("Add one")

        self.assertEqual(result.status, "failed")
        self.assertIn("cannot reserve", result.detail)
        self.assertEqual(calls, 1)
        self.assertEqual(len(result.tool_results), 1)
        self.assertEqual(kernel.budget_status(result.task_id)["spent"], "3.0")

    def test_model_reservation_blocks_call_before_dispatch(self) -> None:
        model = MockLLMProvider()
        kernel = Kernel(
            ResourceRegistry(),
            model,
            task_budget=_budget("0.001", input_price="1", output_price="1"),
        )

        result = kernel.run_goal("Answer this")

        self.assertEqual(result.status, "failed")
        self.assertEqual(model.requests, [])
        self.assertEqual(kernel.budget_status(result.task_id)["spent"], "0")

    def test_model_usage_is_settled_at_reported_cost(self) -> None:
        model = MockLLMProvider(
            script=[LLMResponse(content="Done", usage={"input_tokens": 20, "output_tokens": 10})]
        )
        kernel = Kernel(
            ResourceRegistry(),
            model,
            task_budget=_budget("0.01", input_price="1", output_price="1"),
        )

        result = kernel.run_goal("Answer this")

        self.assertEqual(result.status, "completed", result.detail)
        self.assertEqual(kernel.budget_status(result.task_id)["spent"], "0.00003")
        self.assertEqual(kernel.budget_status(result.task_id)["reserved"], "0")

    def test_usage_above_reserved_ceiling_stops_task(self) -> None:
        model = MockLLMProvider(
            script=[LLMResponse(content="Done", usage={"input_tokens": 2000, "output_tokens": 10})]
        )
        kernel = Kernel(
            ResourceRegistry(),
            model,
            task_budget=_budget("0.01", input_price="1", output_price="1"),
        )

        result = kernel.run_goal("Answer this")

        self.assertEqual(result.status, "failed")
        self.assertIn("reported usage above", result.detail)
        self.assertEqual(kernel.budget_status(result.task_id)["spent"], "0.00201")

    def test_reported_output_over_request_cap_fails_even_when_output_is_free(self) -> None:
        policy = TaskBudget(
            amount=Decimal("1"),
            currency="USD",
            resource_cost_unit="USD",
            model_price=ModelPrice(Decimal("0"), Decimal("0"), 1000, 2),
        )
        model = MockLLMProvider(
            script=[LLMResponse(content="Done", usage={"input_tokens": 20, "output_tokens": 5})]
        )
        kernel = Kernel(ResourceRegistry(), model, task_budget=policy)

        result = kernel.run_goal("Answer this")

        self.assertEqual(result.status, "failed")
        self.assertIn("output usage above its configured token ceiling", result.detail)

    def test_provider_exception_settles_the_reservation_at_the_ceiling(self) -> None:
        class FailingProvider(MockLLMProvider):
            def complete_bounded(self, messages, tools=(), *, max_output_tokens):
                raise ProviderError("provider unavailable")

        kernel = Kernel(
            ResourceRegistry(),
            FailingProvider(),
            task_budget=_budget("1", input_price="1", output_price="1"),
        )

        result = kernel.run_goal("Answer this")

        self.assertEqual(result.status, "failed")
        self.assertIn("provider unavailable", result.detail)
        status = kernel.budget_status(result.task_id)
        self.assertEqual(status["spent"], "0.002")
        self.assertEqual(status["reserved"], "0")

    def test_rollback_does_not_refund_spent_budget(self) -> None:
        store = InMemoryStateStore()
        task_id = store.create("Do work").task_id
        ledger = BudgetLedger(store, _budget("5"))
        ledger.attach(task_id)
        checkpoint = store.checkpoint(task_id, "before")
        reservation = ledger.reserve(task_id, "tool", Decimal("3"))
        ledger.settle(task_id, reservation, Decimal("3"))

        store.rollback(task_id, checkpoint.seq)

        self.assertEqual(ledger.status(task_id)["remaining"], "2")

    def test_parallel_reservations_are_atomic(self) -> None:
        store = InMemoryStateStore()
        task_id = store.create("Do work").task_id
        ledger = BudgetLedger(store, _budget("5"))
        ledger.attach(task_id)

        def reserve() -> bool:
            try:
                ledger.reserve(task_id, "parallel tool", Decimal("4"))
            except BudgetExceededError:
                return False
            return True

        with ThreadPoolExecutor(max_workers=2) as pool:
            outcomes = list(pool.map(lambda _: reserve(), range(2)))

        self.assertEqual(sorted(outcomes), [False, True])
        self.assertEqual(ledger.status(task_id)["reserved"], "4")

    def test_compensation_is_blocked_when_no_budget_remains(self) -> None:
        registry = ResourceRegistry()
        registry.add(_tool("tool.test.publish", 1, side_effect="write", compensated_by="tool.test.undo"))
        registry.add(_tool("tool.test.undo", 1, side_effect="write"))
        undo_calls: list[int] = []
        kernel = Kernel(
            registry,
            MockLLMProvider(),
            tool_implementations={"tool.test.undo": lambda value: undo_calls.append(value)},
            task_budget=_budget("1"),
        )
        task_id = kernel.submit("Do work")
        reservation = kernel.budget_ledger.reserve(task_id, "publish", Decimal("1"))
        kernel.budget_ledger.settle(task_id, reservation, Decimal("1"))

        outcome = kernel._compensate(
            task_id,
            [ToolResult("tool.test.publish", "1.0.0", "success", {"value": 1})],
            PolicyContext(allowed_side_effects=("none", "read", "write"), escalate_side_effects=()),
            lambda kind, payload: None,
        )

        self.assertEqual(outcome[0]["status"], "budget_blocked")
        self.assertEqual(undo_calls, [])
        self.assertEqual(kernel.budget_status(task_id)["spent"], "1")

    def test_compensation_is_charged_when_budget_allows_it(self) -> None:
        registry = ResourceRegistry()
        registry.add(_tool("tool.test.publish", 1, side_effect="write", compensated_by="tool.test.undo"))
        registry.add(_tool("tool.test.undo", 1, side_effect="write"))
        undo_calls: list[int] = []
        kernel = Kernel(
            registry,
            MockLLMProvider(),
            tool_implementations={"tool.test.undo": lambda value: undo_calls.append(value)},
            task_budget=_budget("2"),
        )
        task_id = kernel.submit("Do work")
        reservation = kernel.budget_ledger.reserve(task_id, "publish", Decimal("1"))
        kernel.budget_ledger.settle(task_id, reservation, Decimal("1"))

        outcome = kernel._compensate(
            task_id,
            [ToolResult("tool.test.publish", "1.0.0", "success", {"value": 1})],
            PolicyContext(allowed_side_effects=("none", "read", "write"), escalate_side_effects=()),
            lambda kind, payload: None,
        )

        self.assertEqual(outcome[0]["status"], "compensated")
        self.assertEqual(undo_calls, [1])
        self.assertEqual(Decimal(kernel.budget_status(task_id)["spent"]), Decimal("2"))

    def test_budgeted_kernel_does_not_mutate_shared_model_components(self) -> None:
        model = MockLLMProvider()
        retriever = HydeRetriever(model, LexicalRetriever())
        selector = LLMSetSelector(model)
        planner = LLMPlanner(model)

        first = Kernel(
            ResourceRegistry(), model, retriever=retriever, selector=selector, planner=planner,
            task_budget=_budget("1"),
        )
        second = Kernel(ResourceRegistry(), model, retriever=retriever, selector=selector, planner=planner)

        self.assertIs(retriever.llm, model)
        self.assertIs(selector.llm, model)
        self.assertIs(planner.llm, model)
        self.assertIsNot(first.retriever, retriever)
        self.assertIs(second.retriever, retriever)

    def test_builtin_selectors_accept_exact_decimal_cost_sum(self) -> None:
        results = [
            SearchResult(_tool("tool.test.first", 0.1), 1.0, (), {"relevance": 1.0}),
            SearchResult(_tool("tool.test.second", 0.2), 0.9, (), {"relevance": 1.0}),
        ]

        for selector in (
            RuleBasedSetSelector(),
            GreedyConstrainedSetSelector(),
            BeamSearchSetSelector(),
            BranchAndBoundSetSelector(),
        ):
            with self.subTest(selector=type(selector).__name__):
                selected = selector.select(results, context=SelectionContext(budget_cost=0.3))
                self.assertEqual(len(selected.results), 2)

    def test_resume_requires_the_original_budget_policy(self) -> None:
        store = InMemoryStateStore()
        first = Kernel(ResourceRegistry(), MockLLMProvider(), state_store=store, task_budget=_budget("5"))
        task_id = first.submit("Do work")
        with self.assertRaisesRegex(ValueError, "same task_budget"):
            Kernel(ResourceRegistry(), MockLLMProvider(), state_store=store).run(task_id)
        with self.assertRaisesRegex(ValueError, "differs"):
            Kernel(ResourceRegistry(), MockLLMProvider(), state_store=store, task_budget=_budget("6")).run(task_id)

    def test_json_state_store_preserves_charges_for_new_kernel(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)
            policy = _budget("1", input_price="1", output_price="1")
            first = Kernel(
                ResourceRegistry(),
                MockLLMProvider(
                    script=[LLMResponse(content="Done", usage={"input_tokens": 20, "output_tokens": 10})]
                ),
                state_store=JsonFileStateStore(path),
                task_budget=policy,
            )
            task_id = first.run_goal("Answer this").task_id
            second = Kernel(
                ResourceRegistry(), MockLLMProvider(), state_store=JsonFileStateStore(path), task_budget=policy
            )
            self.assertEqual(second.budget_status(task_id)["spent"], "0.00003")
