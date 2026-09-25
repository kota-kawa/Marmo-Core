from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from marmo_core import (
    HitlResponse,
    HitlPolicy,
    JsonFileStateStore,
    Kernel,
    MockLLMProvider,
    PendingHitlBroker,
    PolicyContext,
    ResourceDefinition,
    ResourceRegistry,
    RuleBasedSetSelector,
    SearchQuery,
    SearchResult,
    SelectionResult,
    SetSelector,
)
from marmo_core.retriever import LexicalRetriever, Retriever


def _external_tool(description: str = "Calculator for addition") -> ResourceDefinition:
    return ResourceDefinition.from_mapping(
        {
            "id": "tool.test.add",
            "kind": "tool",
            "name": "Add",
            "version": "1.0.0",
            "description": description,
            "capabilities": ["addition"],
            "input_summary": "two numbers",
            "output_summary": "sum",
            "required_permissions": [],
            "cost_estimate": 0.0,
            "latency_class": "fast",
            "side_effect": "external",
            "trust_level": "core",
            "ref": "tool://test/add",
            "tags": ["test"],
            "input_schema": {
                "type": "object",
                "required": ["a", "b"],
                "properties": {"a": {"type": "number"}, "b": {"type": "number"}},
            },
        }
    )


class CountingRetriever(Retriever):
    def __init__(self) -> None:
        self.inner = LexicalRetriever()
        self.calls = 0
        self.fail = False

    def search(self, registry: ResourceRegistry, query: SearchQuery) -> list[SearchResult]:
        if self.fail:
            raise AssertionError("resumed task reran retrieval")
        self.calls += 1
        return self.inner.search(registry, query)


class CountingSelector(SetSelector):
    def __init__(self) -> None:
        self.inner = RuleBasedSetSelector()
        self.calls = 0
        self.fail = False

    @property
    def default_limits(self):
        return self.inner.default_limits

    def select(self, results, *, context=None) -> SelectionResult:
        if self.fail:
            raise AssertionError("resumed task reran selection")
        self.calls += 1
        return self.inner.select(results, context=context)


class ExecutionSnapshotTests(unittest.TestCase):
    def _kernel(self, registry: ResourceRegistry, retriever, selector, handler=None, state_store=None) -> Kernel:
        return Kernel(
            registry,
            MockLLMProvider(tool_arguments={"tool.test.add": {"a": 2, "b": 3}}),
            retriever=retriever,
            selector=selector,
            tool_implementations={"tool.test.add": handler or (lambda a, b: {"sum": a + b})},
            policy_context=PolicyContext(human_approved=True),
            hitl=PendingHitlBroker(HitlPolicy(always_confirm_resources=("tool.test.add",))),
            state_store=state_store,
        )

    def test_resume_reuses_saved_route_and_selection(self) -> None:
        registry = ResourceRegistry()
        registry.add(_external_tool())
        retriever = CountingRetriever()
        selector = CountingSelector()
        kernel = self._kernel(registry, retriever, selector)

        paused = kernel.run_goal("Add two numbers with the calculator")
        self.assertTrue(paused.paused, paused.detail)
        route_calls = retriever.calls
        selection_calls = selector.calls
        retriever.fail = True
        selector.fail = True

        result = kernel.resume(paused.task_id, HitlResponse(kind="approve"))

        self.assertEqual(result.status, "completed", result.detail)
        self.assertEqual(retriever.calls, route_calls)
        self.assertEqual(selector.calls, selection_calls)
        self.assertEqual(result.tool_results[0].output, {"sum": 5})
        snapshot = kernel.get_state(paused.task_id)["snapshot"]
        self.assertEqual(snapshot["version"], 1)
        self.assertIn("compiled_fingerprint", snapshot)

    def test_fresh_kernel_reuses_snapshot_from_json_state_store(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            registry = ResourceRegistry()
            registry.add(_external_tool())
            retriever = CountingRetriever()
            selector = CountingSelector()
            first = self._kernel(registry, retriever, selector, state_store=JsonFileStateStore(Path(directory)))
            paused = first.run_goal("Add two numbers with the calculator")
            self.assertTrue(paused.paused, paused.detail)

            resumed_retriever = CountingRetriever()
            resumed_retriever.fail = True
            resumed_selector = CountingSelector()
            resumed_selector.fail = True
            second = self._kernel(
                registry,
                resumed_retriever,
                resumed_selector,
                state_store=JsonFileStateStore(Path(directory)),
            )

            result = second.resume(paused.task_id, HitlResponse(kind="approve"))

            self.assertEqual(result.status, "completed", result.detail)
            self.assertEqual(resumed_retriever.calls, 0)
            self.assertEqual(resumed_selector.calls, 0)

    def test_resume_fails_if_selected_resource_changed(self) -> None:
        registry = ResourceRegistry()
        original = _external_tool()
        registry.add(original)
        executed: list[str] = []
        retriever = CountingRetriever()
        selector = CountingSelector()
        kernel = self._kernel(registry, retriever, selector, lambda a, b: executed.append("ran"))

        paused = kernel.run_goal("Add two numbers with the calculator")
        registry.replace(_external_tool("Different handler description"))

        result = kernel.resume(paused.task_id, HitlResponse(kind="approve"))

        self.assertEqual(result.status, "failed")
        self.assertIn("changed", result.detail)
        self.assertEqual(executed, [])

    def test_resume_fails_if_compiled_file_content_changed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            memory_file = root / "memory.txt"
            memory_file.write_text("Original context", encoding="utf-8")
            memory = ResourceDefinition.from_mapping(
                {
                    "id": "memory.test.context",
                    "kind": "memory",
                    "name": "Context",
                    "version": "1.0.0",
                    "description": "Reference context for calculator goals",
                    "capabilities": ["calculator", "addition"],
                    "input_summary": "context",
                    "output_summary": "context",
                    "required_permissions": [],
                    "cost_estimate": 0.0,
                    "latency_class": "fast",
                    "side_effect": "none",
                    "trust_level": "core",
                    "ref": "file:memory.txt",
                    "tags": ["test"],
                },
                source=str(root / "memory.json"),
            )
            registry = ResourceRegistry()
            registry.add(memory)
            registry.add(_external_tool())
            executed: list[str] = []
            kernel = self._kernel(
                registry,
                CountingRetriever(),
                CountingSelector(),
                handler=lambda a, b: executed.append("ran"),
            )

            paused = kernel.run_goal("Add two numbers with the calculator")
            self.assertTrue(paused.paused, paused.detail)
            self.assertIn("compiled_fingerprint", kernel.get_state(paused.task_id)["snapshot"])
            memory_file.write_text("Changed context", encoding="utf-8")

            result = kernel.resume(paused.task_id, HitlResponse(kind="approve"))

            self.assertEqual(result.status, "failed")
            self.assertIn("compiled execution context changed", result.detail)
            self.assertEqual(executed, [])
