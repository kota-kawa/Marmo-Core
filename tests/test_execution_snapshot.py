from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from marmo_core import (
    HitlResponse,
    HitlRequest,
    HitlPolicy,
    InMemoryStateStore,
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
            self.assertIn("activated context memory.test.context", result.detail)
            self.assertEqual(executed, [])

    def test_activation_pause_pins_already_loaded_file_content(self) -> None:
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
                    "description": "Reference context",
                    "capabilities": ["context"],
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
            tool = _external_tool()

            class FixedRetriever(Retriever):
                def search(self, registry, query):
                    return [
                        SearchResult(memory, 1.0, (), {"relevance": 1.0}),
                        SearchResult(tool, 0.9, (), {"relevance": 0.9}),
                    ]

            class FixedSelector(SetSelector):
                @property
                def default_limits(self):
                    return {"memory": 1, "skill": 1, "tool": 1, "agent": 1}

                def select(self, results, *, context=None):
                    return SelectionResult(tuple(results), "fixed test selection")

            registry = ResourceRegistry()
            registry.add(memory)
            registry.add(tool)
            executed: list[str] = []
            kernel = Kernel(
                registry,
                MockLLMProvider(tool_arguments={"tool.test.add": {"a": 2, "b": 3}}),
                retriever=FixedRetriever(),
                selector=FixedSelector(),
                tool_implementations={"tool.test.add": lambda a, b: executed.append("ran")},
                policy_context=PolicyContext(),
                hitl=PendingHitlBroker(),
            )

            paused = kernel.run_goal("Use the context and calculator")

            self.assertTrue(paused.paused, paused.detail)
            self.assertEqual(paused.hitl.stage, "activation")
            snapshot = kernel.get_state(paused.task_id)["snapshot"]
            self.assertIn("memory.test.context@1.0.0", snapshot["activation_fingerprints"])
            memory_file.write_text("Changed while waiting for approval", encoding="utf-8")

            result = kernel.resume(paused.task_id, HitlResponse(kind="approve"))

            self.assertEqual(result.status, "failed")
            self.assertIn("activated context memory.test.context", result.detail)
            self.assertEqual(executed, [])

    def test_legacy_activation_resume_without_snapshot_fails_closed(self) -> None:
        store = InMemoryStateStore()
        state = store.create("Add two numbers with the calculator")
        request = HitlRequest.create(
            task_id=state.task_id,
            stage="activation",
            operation="activate tool.test.add@1.0.0",
            impact="side_effect=external",
            resource="tool.test.add@1.0.0",
        )
        store.append(
            state.task_id,
            "paused",
            {"request": request.to_dict(), "detail": "legacy activation approval"},
        )
        store.append(state.task_id, "resumed", {"approvals": ["tool.test.add@1.0.0"]})

        registry = ResourceRegistry()
        registry.add(_external_tool())
        retriever = CountingRetriever()
        retriever.fail = True
        selector = CountingSelector()
        selector.fail = True
        kernel = self._kernel(
            registry,
            retriever,
            selector,
            state_store=store,
        )

        result = kernel.run(state.task_id)

        self.assertEqual(result.status, "failed")
        self.assertIn("earlier execution snapshot was not saved", result.detail)
        self.assertEqual(retriever.calls, 0)
        self.assertEqual(selector.calls, 0)
