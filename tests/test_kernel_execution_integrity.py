"""Interrupted persistence, concurrent execution, cancellation, and plan control."""

from __future__ import annotations

from pathlib import Path
import shutil
import tempfile
import threading
import unittest
from unittest import mock

from marmo_core import (
    AnthropicLLMProvider,
    HitlError,
    HitlPolicy,
    HitlResponse,
    InMemoryStateStore,
    JsonFileStateStore,
    Kernel,
    LLMProvider,
    LLMResponse,
    MockLLMProvider,
    OpenAICompatibleLLMProvider,
    PendingHitlBroker,
    PolicyContext,
    RecoveryManager,
    ResourceDefinition,
    ResourceRegistry,
    RetryPolicy,
    RuleBasedPlanner,
    StateConflictError,
    ToolCall,
)


FIXTURES = Path(__file__).parent / "fixtures" / "compat" / "v0.3.0"
GOAL = "produce the quarterly report"
WAIT = 30  # deadlock guard for synchronization points, never a pass condition


def _tool(resource_id: str, **overrides) -> dict:
    data = {
        "id": resource_id,
        "kind": "tool",
        "name": resource_id,
        "version": "1.0.0",
        "description": "Produce the quarterly report.",
        "capabilities": ["reporting"],
        "input_summary": "name",
        "output_summary": "result object",
        "required_permissions": [],
        "cost_estimate": 0.0,
        "latency_class": "fast",
        "side_effect": "none",
        "trust_level": "core",
        "ref": f"tool://{resource_id}",
        "tags": ["reports", "quarterly"],
        "input_schema": {
            "type": "object",
            "required": ["name"],
            "properties": {"name": {"type": "string", "default": "q3"}},
        },
    }
    data.update(overrides)
    return data


def _registry(*entries: dict) -> ResourceRegistry:
    registry = ResourceRegistry()
    for entry in entries:
        registry.add(ResourceDefinition.from_mapping(entry))
    return registry


class _Handler:
    def __init__(self) -> None:
        self.arguments: list[str] = []

    @property
    def calls(self) -> int:
        return len(self.arguments)

    def __call__(self, name: str) -> dict:
        self.arguments.append(name)
        return {"report": name}


class _ToolThenAnswer(LLMProvider):
    """Ask for one tool call, then answer once a tool result is in the conversation."""

    def __init__(self, tool_id: str = "tool.report") -> None:
        self.tool_id = tool_id
        self.requests = 0

    def complete(self, messages, tools=()):
        self.requests += 1
        if any(message.role == "tool" for message in messages):
            return LLMResponse(content="report ready")
        return LLMResponse(
            content="",
            tool_calls=(ToolCall(id="call-1", name=self.tool_id, arguments={"name": "q3"}),),
            finish_reason="tool_calls",
        )


class _CrashingStore(InMemoryStateStore):
    """Stop the process (raise) at a chosen write, once."""

    def __init__(self) -> None:
        super().__init__()
        self.crash_on = None

    def append(self, task_id, kind, payload=None, *, expected_version=None):
        if self.crash_on is not None and self.crash_on(self, task_id, kind, dict(payload or {})):
            self.crash_on = None
            raise RuntimeError("simulated crash while persisting")
        return super().append(task_id, kind, payload, expected_version=expected_version)

    def has(self, task_id: str, kind: str) -> bool:
        return any(event.kind == kind for event in self.events(task_id))


def _kernel(entries, handlers, llm, **kwargs) -> Kernel:
    kwargs.setdefault("policy_context", PolicyContext())
    kwargs.setdefault("set_limits", {"tool": 4})
    kwargs.setdefault(
        "recovery",
        RecoveryManager(retry_policy=RetryPolicy(initial_backoff_seconds=0.0), sleep=lambda _: None),
    )
    return Kernel(_registry(*entries), llm, tool_implementations=handlers, **kwargs)


class InterruptedPersistenceTests(unittest.TestCase):
    def test_a_recorded_result_is_not_produced_again_by_a_new_kernel(self) -> None:
        store = _CrashingStore()
        handler = _Handler()
        entries = [_tool("tool.report")]
        # The result is on record; the frame that moves past the call is not.
        store.crash_on = lambda s, task_id, kind, payload: (
            kind == "frame" and s.has(task_id, "step")
        )
        first = _kernel(entries, {"tool.report": handler}, _ToolThenAnswer(), state_store=store)
        task_id = first.submit(GOAL)
        with self.assertRaises(RuntimeError):
            first.run(task_id)
        self.assertEqual(handler.calls, 1)

        llm = _ToolThenAnswer()
        second = _kernel(entries, {"tool.report": handler}, llm, state_store=store)
        result = second.run(task_id)

        self.assertEqual(result.status, "completed", result.detail)
        self.assertEqual(handler.calls, 1, "the recorded call must not run a second time")
        self.assertEqual(llm.requests, 1, "the model is asked only for the answer")
        self.assertEqual([item.status for item in result.tool_results], ["success"])
        self.assertIn(
            "reuse_recorded_result",
            [record.payload.get("action") for record in second.audit_log.records if record.kind == "recover"],
        )

    def test_a_call_with_no_recorded_result_is_treated_as_unknown(self) -> None:
        store = _CrashingStore()
        handler = _Handler()
        entries = [_tool("tool.report", side_effect="write")]
        # The handler ran; its result never reached the store.
        store.crash_on = lambda s, task_id, kind, payload: kind == "step"
        context = PolicyContext(human_approved=True)
        first = _kernel(
            entries, {"tool.report": handler}, _ToolThenAnswer(), state_store=store, policy_context=context
        )
        task_id = first.submit(GOAL)
        with self.assertRaises(RuntimeError):
            first.run(task_id)
        self.assertEqual(handler.calls, 1)

        second = _kernel(
            entries, {"tool.report": handler}, _ToolThenAnswer(), state_store=store, policy_context=context
        )
        paused = second.run(task_id)

        self.assertTrue(paused.paused, paused.detail)
        self.assertEqual(handler.calls, 1, "an unknown outcome must not be retried automatically")
        self.assertEqual(paused.tool_results[-1].status, "timeout")
        self.assertIn("outcome is unknown", paused.tool_results[-1].error or "")
        self.assertIn("recovery", paused.hitl_request["decision"])

        resumed = second.resume(task_id, HitlResponse(kind="approve", responder="alice"))

        self.assertEqual(resumed.status, "completed", resumed.detail)
        self.assertEqual(handler.calls, 2, "a person authorized exactly one more attempt")

    def test_an_unknown_outcome_fails_the_task_when_escalation_is_off(self) -> None:
        store = _CrashingStore()
        handler = _Handler()
        entries = [_tool("tool.report")]
        store.crash_on = lambda s, task_id, kind, payload: kind == "step"
        recovery = RecoveryManager(escalate_when_exhausted=False, sleep=lambda _: None)
        first = _kernel(entries, {"tool.report": handler}, _ToolThenAnswer(), state_store=store)
        task_id = first.submit(GOAL)
        with self.assertRaises(RuntimeError):
            first.run(task_id)

        second = _kernel(
            entries, {"tool.report": handler}, _ToolThenAnswer(), state_store=store, recovery=recovery
        )
        result = second.run(task_id)

        self.assertEqual(result.status, "failed")
        self.assertEqual(handler.calls, 1)

    def test_a_plan_step_with_a_recorded_result_is_not_run_again(self) -> None:
        store = _CrashingStore()
        handler = _Handler()
        entries = [_tool("tool.report")]
        # The step result is on record; the plan that marks it completed is not.
        store.crash_on = lambda s, task_id, kind, payload: kind == "plan" and s.has(task_id, "step")
        llm = MockLLMProvider(script=[LLMResponse(content="report ready")])
        first = _kernel(entries, {"tool.report": handler}, llm, state_store=store, planner=RuleBasedPlanner())
        task_id = first.submit(GOAL)
        with self.assertRaises(RuntimeError):
            first.run(task_id)
        self.assertEqual(handler.calls, 1)

        second = _kernel(
            entries,
            {"tool.report": handler},
            MockLLMProvider(script=[LLMResponse(content="report ready")]),
            state_store=store,
            planner=RuleBasedPlanner(),
        )
        result = second.run(task_id)

        self.assertEqual(result.status, "completed", result.detail)
        self.assertEqual(handler.calls, 1)

    def test_a_call_id_reused_in_a_later_round_runs_again(self) -> None:
        handler = _Handler()

        def call(name: str) -> LLMResponse:
            return LLMResponse(
                content="",
                tool_calls=(ToolCall(id="call-1", name="tool.report", arguments={"name": name}),),
                finish_reason="tool_calls",
            )

        llm = MockLLMProvider(script=[call("q3"), call("q4"), LLMResponse(content="done")])
        kernel = _kernel([_tool("tool.report")], {"tool.report": handler}, llm)

        result = kernel.run_goal(GOAL)

        self.assertEqual(result.status, "completed", result.detail)
        self.assertEqual(handler.arguments, ["q3", "q4"])

    def test_calls_sharing_an_id_in_one_round_each_run(self) -> None:
        for shared_id in ("", "dup"):
            with self.subTest(call_id=shared_id):
                handler = _Handler()
                llm = MockLLMProvider(
                    script=[
                        LLMResponse(
                            content="",
                            tool_calls=(
                                ToolCall(id=shared_id, name="tool.report", arguments={"name": "q3"}),
                                ToolCall(id=shared_id, name="tool.report", arguments={"name": "q4"}),
                            ),
                            finish_reason="tool_calls",
                        ),
                        LLMResponse(content="done"),
                    ]
                )
                kernel = _kernel([_tool("tool.report")], {"tool.report": handler}, llm)

                result = kernel.run_goal(GOAL)

                self.assertEqual(result.status, "completed", result.detail)
                self.assertEqual(handler.arguments, ["q3", "q4"])
                self.assertEqual([item.arguments["name"] for item in result.tool_results], ["q3", "q4"])

    def test_a_recorded_delegation_is_not_run_again_by_a_new_kernel(self) -> None:
        calls: list[str] = []

        def researcher(question: str) -> dict:
            calls.append(question)
            return {"answer": question}

        agent = {
            **_tool("agent.research"),
            "kind": "agent",
            "ref": "agent://agent.research",
            "agent_card": {
                "delegation_interface": "tool_wrap",
                "callable_name": "delegate_research",
                "input_schema": {
                    "type": "object",
                    "required": ["question"],
                    "properties": {"question": {"type": "string"}},
                },
                "output_schema": {"type": "object"},
            },
        }
        del agent["input_schema"]

        class _DelegateThenAnswer(LLMProvider):
            def complete(self, messages, tools=()):
                if any(message.role == "tool" for message in messages):
                    return LLMResponse(content="research done")
                return LLMResponse(
                    content="",
                    tool_calls=(ToolCall(id="call-1", name="delegate_research", arguments={"question": "why"}),),
                    finish_reason="tool_calls",
                )

        def kernel_on(store) -> Kernel:
            return Kernel(
                _registry(agent),
                _DelegateThenAnswer(),
                agent_implementations={"agent.research": researcher},
                state_store=store,
            )

        store = _CrashingStore()
        store.crash_on = lambda s, task_id, kind, payload: kind == "frame" and s.has(task_id, "step")
        first = kernel_on(store)
        task_id = first.submit(GOAL)
        with self.assertRaises(RuntimeError):
            first.run(task_id)
        self.assertEqual(calls, ["why"])

        result = kernel_on(store).run(task_id)

        self.assertEqual(result.status, "completed", result.detail)
        self.assertEqual(calls, ["why"], "the recorded delegation must not run a second time")
        self.assertEqual(len(result.agent_results), 1)

    def test_a_state_file_written_before_the_call_journal_still_loads(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            shutil.copyfile(FIXTURES / "state.jsonl", Path(directory) / "compat-task.jsonl")
            store = JsonFileStateStore(directory)
            kernel = _kernel([_tool("tool.report")], {}, MockLLMProvider(), state_store=store)

            # A result written the old way carries no call id.
            store.append("compat-task", "step", {"result": {"tool_id": "tool.report", "status": "success"}})

            self.assertEqual(len(store.load("compat-task").step_results), 1)
            self.assertIsNone(kernel._open_call("compat-task", "call-1"))
            store.append("compat-task", "call", {"call_id": "call-new", "phase": "started"})
            self.assertEqual(kernel._open_call("compat-task", "call-new"), {"reservation_id": None, "result": None})


class ConcurrentExecutionTests(unittest.TestCase):
    def test_a_second_kernel_on_the_same_state_directory_stops_before_the_handler(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            entered = threading.Event()
            release = threading.Event()
            calls: list[str] = []

            def handler(name: str) -> dict:
                calls.append(name)
                entered.set()
                release.wait(WAIT)
                return {"report": name}

            entries = [_tool("tool.report")]
            first = _kernel(
                entries, {"tool.report": handler}, _ToolThenAnswer(), state_store=JsonFileStateStore(directory)
            )
            second = _kernel(
                entries, {"tool.report": handler}, _ToolThenAnswer(), state_store=JsonFileStateStore(directory)
            )
            task_id = first.submit(GOAL)
            results: list = []
            runner = threading.Thread(target=lambda: results.append(first.run(task_id)))
            runner.start()
            try:
                self.assertTrue(entered.wait(WAIT))
                with self.assertRaises(StateConflictError):
                    second.run(task_id)
                with self.assertRaises(StateConflictError):
                    second.resume(task_id)
            finally:
                release.set()
                runner.join(WAIT)

            self.assertEqual(len(calls), 1)
            self.assertEqual(results[0].status, "completed", results[0].detail)
            # The right to execute is released with the run.
            self.assertEqual(second.run(task_id).status, "completed")

    def test_cancel_while_waiting_for_the_model_is_not_overwritten(self) -> None:
        entered = threading.Event()
        release = threading.Event()

        class _SlowModel(LLMProvider):
            def complete(self, messages, tools=()):
                entered.set()
                release.wait(WAIT)
                return LLMResponse(content="late answer")

        kernel = _kernel([_tool("tool.report")], {"tool.report": _Handler()}, _SlowModel())
        task_id = kernel.submit(GOAL)
        results: list = []
        runner = threading.Thread(target=lambda: results.append(kernel.run(task_id)))
        runner.start()
        try:
            self.assertTrue(entered.wait(WAIT))
            kernel.cancel(task_id)
        finally:
            release.set()
            runner.join(WAIT)

        self.assertEqual(results[0].status, "cancelled")
        self.assertEqual(kernel.get_state(task_id)["status"], "cancelled")
        self.assertEqual(kernel.get_state(task_id)["output"], "")
        statuses = [
            record.payload["status"] for record in kernel.audit_log.records if record.kind == "task"
        ]
        self.assertEqual(statuses, ["cancelled"])

    def test_a_cancel_that_lands_after_the_last_check_still_stops_the_call(self) -> None:
        handler = _Handler()
        kernel = _kernel([_tool("tool.report")], {"tool.report": handler}, _ToolThenAnswer())
        task_id = kernel.submit(GOAL)

        def cancel_while_reserving(task, metadata):
            # The last step before the call is handed to the runtime.
            kernel.cancel(task)
            return None

        with mock.patch.object(kernel, "_reserve_resource", cancel_while_reserving):
            result = kernel.run(task_id)

        self.assertEqual(result.status, "cancelled")
        self.assertEqual(handler.calls, 0)

    def test_no_call_starts_after_cancel_and_a_late_result_keeps_the_status(self) -> None:
        entered = threading.Event()
        release = threading.Event()
        second = _Handler()

        def first(name: str) -> dict:
            entered.set()
            release.wait(WAIT)
            return {"report": name}

        llm = MockLLMProvider(
            script=[
                LLMResponse(
                    content="",
                    tool_calls=(
                        ToolCall(id="call-1", name="tool.first", arguments={"name": "q3"}),
                        ToolCall(id="call-2", name="tool.second", arguments={"name": "q3"}),
                    ),
                    finish_reason="tool_calls",
                ),
                LLMResponse(content="done"),
            ]
        )
        kernel = _kernel(
            [_tool("tool.first"), _tool("tool.second")], {"tool.first": first, "tool.second": second}, llm
        )
        task_id = kernel.submit(GOAL)
        results: list = []
        runner = threading.Thread(target=lambda: results.append(kernel.run(task_id)))
        runner.start()
        try:
            self.assertTrue(entered.wait(WAIT))
            kernel.cancel(task_id)
        finally:
            release.set()
            runner.join(WAIT)

        self.assertEqual(results[0].status, "cancelled")
        self.assertEqual(second.calls, 0, "no call may start after the cancellation")
        state = kernel.get_state(task_id)
        self.assertEqual(state["status"], "cancelled")
        self.assertEqual(
            [item["tool_id"] for item in state["step_results"]],
            ["tool.first"],
            "the side effect that did happen stays on record",
        )


class _CountingPlanner(RuleBasedPlanner):
    def __init__(self) -> None:
        super().__init__()
        self.replans = 0

    def replan(self, plan, resources, *, context=None, failure=None):
        self.replans += 1
        return super().replan(plan, resources, context=context, failure=failure)


class PlanControlTests(unittest.TestCase):
    def _plan_kernel(self, entries, handlers, **kwargs) -> Kernel:
        kwargs.setdefault("planner", RuleBasedPlanner())
        llm = kwargs.pop("llm", None) or MockLLMProvider(script=[LLMResponse(content="report ready")])
        return _kernel(entries, handlers, llm, **kwargs)

    def test_sequential_plan_stops_at_max_tool_calls(self) -> None:
        handlers = {"tool.fetch": _Handler(), "tool.publish": _Handler()}
        entries = [_tool("tool.fetch"), _tool("tool.publish", dependencies=["tool.fetch"])]
        kernel = self._plan_kernel(entries, handlers, max_tool_calls=1)

        result = kernel.run_goal(GOAL)

        self.assertEqual(result.status, "failed")
        self.assertIn("exceeded max_tool_calls=1", result.detail)
        self.assertEqual(sum(handler.calls for handler in handlers.values()), 1)

    def test_parallel_wave_stops_at_max_tool_calls(self) -> None:
        handlers = {f"tool.{name}": _Handler() for name in ("a", "b", "c")}
        entries = [_tool(resource_id) for resource_id in handlers]
        kernel = self._plan_kernel(entries, handlers, max_tool_calls=2, max_parallel_steps=4)

        result = kernel.run_goal(GOAL)

        self.assertEqual(result.status, "failed")
        self.assertIn("exceeded max_tool_calls=2", result.detail)
        self.assertEqual(sum(handler.calls for handler in handlers.values()), 2)

    def test_the_limit_counts_calls_made_before_a_pause(self) -> None:
        handlers = {"tool.fetch": _Handler(), "tool.publish": _Handler(), "tool.notify": _Handler()}
        entries = [
            _tool("tool.fetch"),
            _tool("tool.publish", dependencies=["tool.fetch"]),
            _tool("tool.notify", dependencies=["tool.publish"]),
        ]
        kernel = self._plan_kernel(
            entries,
            handlers,
            max_tool_calls=2,
            hitl=PendingHitlBroker(HitlPolicy(always_confirm_resources=("tool.publish",))),
        )

        paused = kernel.run_goal(GOAL)
        self.assertTrue(paused.paused, paused.detail)
        result = kernel.resume(paused.task_id, HitlResponse(kind="approve", responder="alice"))

        self.assertEqual(result.status, "failed")
        self.assertIn("exceeded max_tool_calls=2", result.detail)
        self.assertEqual(handlers["tool.notify"].calls, 0)

    def test_a_plan_within_the_limit_still_completes(self) -> None:
        handlers = {"tool.fetch": _Handler(), "tool.publish": _Handler()}
        entries = [_tool("tool.fetch"), _tool("tool.publish", dependencies=["tool.fetch"])]
        kernel = self._plan_kernel(entries, handlers, max_tool_calls=2)

        self.assertEqual(kernel.run_goal(GOAL).status, "completed")

    def test_an_unknown_outcome_is_not_replanned_around(self) -> None:
        release = threading.Event()
        self.addCleanup(release.set)
        later = _Handler()

        def stuck(name: str) -> dict:
            release.wait(WAIT)
            return {"report": name}

        planner = _CountingPlanner()
        entries = [_tool("tool.fetch"), _tool("tool.publish", dependencies=["tool.fetch"])]
        kernel = self._plan_kernel(
            entries,
            {"tool.fetch": stuck, "tool.publish": later},
            planner=planner,
            timeout_seconds=0.05,
            recovery=RecoveryManager(escalate_when_exhausted=False, sleep=lambda _: None),
        )

        result = kernel.run_goal(GOAL)

        self.assertEqual(result.status, "failed")
        self.assertIn("outcome of that step is unknown", result.detail)
        self.assertEqual(planner.replans, 0)
        self.assertEqual(later.calls, 0)


class ParallelUnknownOutcomeTests(unittest.TestCase):
    def test_an_unknown_outcome_stops_replanning_even_when_a_sibling_failed_first(self) -> None:
        release = threading.Event()
        self.addCleanup(release.set)

        def broken(name: str) -> dict:
            raise ValueError("bad input data")

        def stuck(name: str) -> dict:
            release.wait(WAIT)
            return {"report": name}

        # Whichever of the two is first in plan order, the unknown outcome decides.
        for handlers in ({"tool.a": broken, "tool.b": stuck}, {"tool.a": stuck, "tool.b": broken}):
            with self.subTest(stuck=next(name for name, handler in handlers.items() if handler is stuck)):
                planner = _CountingPlanner()
                kernel = _kernel(
                    # Different capabilities, so neither can stand in for the other.
                    [_tool("tool.a", capabilities=["figures"]), _tool("tool.b", capabilities=["charts"])],
                    handlers,
                    MockLLMProvider(script=[LLMResponse(content="report ready")]),
                    planner=planner,
                    timeout_seconds=0.05,
                    recovery=RecoveryManager(escalate_when_exhausted=False, sleep=lambda _: None),
                )

                result = kernel.run_goal(GOAL)

                self.assertEqual(result.status, "failed")
                self.assertIn("outcome of that step is unknown", result.detail)
                self.assertEqual(planner.replans, 0)


class _ReorderedPauseStore(InMemoryStateStore):
    """Write the first plan step's pause first, so the pause stored last is another step's."""

    def __init__(self) -> None:
        super().__init__()
        self.first_resource = ""
        self.first_paused = threading.Event()

    def append(self, task_id, kind, payload=None, *, expected_version=None):
        payload = dict(payload or {})
        if kind == "plan" and not self.first_resource:
            self.first_resource = payload["plan"]["steps"][0]["resource_id"]
        resource = str((payload.get("request") or {}).get("resource", ""))
        is_first = resource.startswith(self.first_resource)
        if kind == "paused" and not is_first:
            self.first_paused.wait(WAIT)
        state = super().append(task_id, kind, payload, expected_version=expected_version)
        if kind == "paused" and is_first:
            self.first_paused.set()
        return state


class PlanApprovalTests(unittest.TestCase):
    def _kernel(self, entries, handlers, confirm, **kwargs) -> Kernel:
        kwargs.setdefault("planner", RuleBasedPlanner())
        kwargs.setdefault("hitl", PendingHitlBroker(HitlPolicy(always_confirm_resources=tuple(confirm))))
        llm = MockLLMProvider(script=[LLMResponse(content="report ready")])
        return _kernel(entries, handlers, llm, **kwargs)

    def test_modified_arguments_are_what_the_resumed_step_runs_with(self) -> None:
        handler = _Handler()
        kernel = self._kernel([_tool("tool.publish")], {"tool.publish": handler}, ["tool.publish"])

        paused = kernel.run_goal(GOAL)
        self.assertEqual(paused.hitl_request["arguments"], {"name": "q3"})
        resumed = kernel.resume(
            paused.task_id,
            HitlResponse(kind="modify", responder="alice", arguments={"name": "reviewed"}),
        )

        self.assertEqual(resumed.status, "completed", resumed.detail)
        self.assertEqual(handler.arguments, ["reviewed"])
        self.assertEqual(resumed.tool_results[-1].arguments, {"name": "reviewed"})
        step = kernel.get_state(paused.task_id)["plan"]["steps"][0]
        self.assertEqual(step["arguments"], {"name": "reviewed"})
        self.assertEqual(step["result"]["arguments"], {"name": "reviewed"})

    def test_the_edit_applies_to_the_paused_step_only(self) -> None:
        handlers = {"tool.fetch": _Handler(), "tool.publish": _Handler()}
        entries = [_tool("tool.fetch"), _tool("tool.publish", dependencies=["tool.fetch"])]
        kernel = self._kernel(entries, handlers, ["tool.publish"])

        paused = kernel.run_goal(GOAL)
        kernel.resume(paused.task_id, HitlResponse(kind="modify", arguments={"name": "reviewed"}))

        self.assertEqual(handlers["tool.fetch"].arguments, ["q3"])
        self.assertEqual(handlers["tool.publish"].arguments, ["reviewed"])

    def test_invalid_modified_arguments_are_an_error_and_leave_the_request_pending(self) -> None:
        handler = _Handler()
        kernel = self._kernel([_tool("tool.publish")], {"tool.publish": handler}, ["tool.publish"])
        paused = kernel.run_goal(GOAL)

        with self.assertRaises(HitlError) as raised:
            kernel.resume(paused.task_id, HitlResponse(kind="modify", arguments={"name": 7}))

        self.assertIn("modified arguments", str(raised.exception))
        self.assertEqual(handler.calls, 0)
        pending = kernel.pending_request(paused.task_id)
        self.assertEqual(pending.request_id, paused.hitl_request["request_id"])
        resumed = kernel.resume(paused.task_id, HitlResponse(kind="modify", arguments={"name": "ok"}))
        self.assertEqual(resumed.status, "completed", resumed.detail)
        self.assertEqual(handler.arguments, ["ok"])

    def test_an_edit_on_a_pause_saved_without_its_step_is_refused(self) -> None:
        handler = _Handler()
        kernel = self._kernel([_tool("tool.publish")], {"tool.publish": handler}, ["tool.publish"])
        paused = kernel.run_goal(GOAL)
        # A pause written before plan steps recorded which step they stopped on.
        state = kernel.state_store.load(paused.task_id)
        frame = {key: value for key, value in state.frame.items() if key != "paused_call"}
        kernel.state_store.append(paused.task_id, "frame", {"frame": frame})

        with self.assertRaises(HitlError):
            kernel.resume(paused.task_id, HitlResponse(kind="modify", arguments={"name": "reviewed"}))

        self.assertEqual(handler.calls, 0)
        resumed = kernel.resume(paused.task_id, HitlResponse(kind="approve"))
        self.assertEqual(resumed.status, "completed", resumed.detail)
        self.assertEqual(handler.arguments, ["q3"])

    def test_the_edit_survives_a_saved_state_and_a_new_kernel(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            handler = _Handler()
            entries = [_tool("tool.publish")]
            first = self._kernel(
                entries, {"tool.publish": handler}, ["tool.publish"], state_store=JsonFileStateStore(directory)
            )
            paused = first.run_goal(GOAL)

            second = self._kernel(
                entries, {"tool.publish": handler}, ["tool.publish"], state_store=JsonFileStateStore(directory)
            )
            resumed = second.resume(
                paused.task_id, HitlResponse(kind="modify", arguments={"name": "reviewed"})
            )

            self.assertEqual(resumed.status, "completed", resumed.detail)
            self.assertEqual(handler.arguments, ["reviewed"])

    def test_parallel_pauses_return_the_request_that_is_stored(self) -> None:
        handlers = {"tool.a": _Handler(), "tool.b": _Handler()}
        entries = [_tool("tool.a"), _tool("tool.b")]
        # The first step's pause is written first, so the one stored last
        # belongs to the other step.
        store = _ReorderedPauseStore()
        kernel = self._kernel(entries, handlers, ["tool.a", "tool.b"], state_store=store)

        paused = kernel.run_goal(GOAL)

        self.assertTrue(paused.paused, paused.detail)
        first_step = kernel.get_state(paused.task_id)["plan"]["steps"][0]
        self.assertTrue(paused.hitl_request["resource"].startswith(first_step["resource_id"]))
        pending = kernel.pending_request(paused.task_id)
        self.assertEqual(pending.request_id, paused.hitl_request["request_id"])
        self.assertEqual(pending.resource, paused.hitl_request["resource"])

        # The other paused step asks again, with its own request, after the first answer.
        again = kernel.resume(
            paused.task_id,
            HitlResponse(kind="approve", request_id=paused.hitl_request["request_id"], responder="alice"),
        )
        self.assertTrue(again.paused, again.detail)
        self.assertNotEqual(again.hitl_request["request_id"], paused.hitl_request["request_id"])
        self.assertNotEqual(again.hitl_request["resource"], paused.hitl_request["resource"])
        self.assertEqual(
            kernel.pending_request(paused.task_id).request_id, again.hitl_request["request_id"]
        )
        self.assertEqual(sum(handler.calls for handler in handlers.values()), 1)

        done = kernel.resume(
            paused.task_id,
            HitlResponse(kind="approve", request_id=again.hitl_request["request_id"], responder="alice"),
        )
        self.assertEqual(done.status, "completed", done.detail)
        self.assertEqual([handler.calls for handler in handlers.values()], [1, 1])

    def test_a_pause_reports_the_sibling_that_finished_and_does_not_rerun_it(self) -> None:
        handlers = {"tool.a": _Handler(), "tool.b": _Handler()}
        entries = [_tool("tool.a"), _tool("tool.b")]
        with tempfile.TemporaryDirectory() as directory:
            first = self._kernel(entries, handlers, ["tool.a"], state_store=JsonFileStateStore(directory))
            paused = first.run_goal(GOAL)

            self.assertTrue(paused.paused, paused.detail)
            self.assertEqual([item.tool_id for item in paused.tool_results], ["tool.b"])
            self.assertEqual(first.get_state(paused.task_id)["frame"]["executed_calls"], 1)

            second = self._kernel(entries, handlers, ["tool.a"], state_store=JsonFileStateStore(directory))
            done = second.resume(paused.task_id, HitlResponse(kind="approve", responder="alice"))

            self.assertEqual(done.status, "completed", done.detail)
            self.assertEqual([handler.calls for handler in handlers.values()], [1, 1])


class ModelResponseTests(unittest.TestCase):
    def test_a_truncated_reply_is_not_a_completion(self) -> None:
        llm = MockLLMProvider(script=[LLMResponse(content="The report says", finish_reason="length")])
        kernel = _kernel([_tool("tool.report")], {"tool.report": _Handler()}, llm)

        result = kernel.run_goal(GOAL)

        self.assertEqual(result.status, "failed")
        self.assertIn("truncated", result.detail)
        self.assertEqual(result.output, "The report says")
        self.assertEqual(kernel.get_state(result.task_id)["status"], "failed")

    def test_a_truncated_tool_request_is_not_dispatched(self) -> None:
        handler = _Handler()
        llm = MockLLMProvider(
            script=[
                LLMResponse(
                    content="",
                    tool_calls=(ToolCall(id="call-1", name="tool.report", arguments={"name": "q"}),),
                    finish_reason="length",
                )
            ]
        )
        kernel = _kernel([_tool("tool.report")], {"tool.report": handler}, llm)

        result = kernel.run_goal(GOAL)

        self.assertEqual(result.status, "failed")
        self.assertEqual(handler.calls, 0)

    def test_normal_tool_requests_and_answers_still_complete(self) -> None:
        handler = _Handler()
        kernel = _kernel([_tool("tool.report")], {"tool.report": handler}, _ToolThenAnswer())

        result = kernel.run_goal(GOAL)

        self.assertEqual(result.status, "completed", result.detail)
        self.assertEqual(handler.calls, 1)

    def test_a_malformed_provider_body_ends_the_task_with_an_audit_record(self) -> None:
        bodies = (
            ["not", "an", "object"],
            {"choices": "oops"},
            {"choices": [{"message": "text instead of an object"}]},
            {"choices": [{"message": {"tool_calls": [{"function": {"arguments": 3}}]}}]},
        )
        for body in bodies:
            with self.subTest(body=body):
                provider = OpenAICompatibleLLMProvider(
                    model="test-model",
                    api_key="test-key",
                    base_url="https://llm.invalid/v1",
                    transport=lambda url, payload, headers, timeout, body=body: body,
                )
                kernel = _kernel([_tool("tool.report")], {"tool.report": _Handler()}, provider)

                result = kernel.run_goal(GOAL)

                self.assertEqual(result.status, "failed")
                self.assertIn("the model provider failed", result.detail)
                self.assertEqual(kernel.get_state(result.task_id)["status"], "failed")
                self.assertTrue(
                    any(
                        record.kind == "llm" and "ProviderError" in str(record.payload.get("error", ""))
                        for record in kernel.audit_log.records
                    )
                )


    def test_tool_arguments_that_are_not_an_object_are_handed_back_for_repair(self) -> None:
        for raw in ("[1]", "null", "5", '"x"'):
            with self.subTest(arguments=raw):
                body = {
                    "choices": [
                        {
                            "finish_reason": "tool_calls",
                            "message": {
                                "tool_calls": [
                                    {"id": "call-1", "function": {"name": "tool.report", "arguments": raw}}
                                ]
                            },
                        }
                    ]
                }
                provider = OpenAICompatibleLLMProvider(
                    model="test-model",
                    api_key="test-key",
                    base_url="https://llm.invalid/v1",
                    transport=lambda url, payload, headers, timeout, body=body: body,
                )
                handler = _Handler()
                kernel = _kernel([_tool("tool.report")], {"tool.report": handler}, provider)

                result = kernel.run_goal(GOAL)

                self.assertEqual(result.status, "failed", result.detail)
                self.assertIn("max_input_repairs", result.detail)
                self.assertEqual(handler.calls, 0)

    def test_a_malformed_anthropic_body_is_a_provider_failure(self) -> None:
        for body in (["not", "an", "object"], {"content": [{"type": "tool_use", "input": [1]}]}):
            with self.subTest(body=body):
                provider = AnthropicLLMProvider(
                    model="m",
                    api_key="k",
                    max_tokens=64,
                    transport=lambda url, payload, headers, timeout, body=body: body,
                )
                kernel = _kernel([_tool("tool.report")], {"tool.report": _Handler()}, provider)

                result = kernel.run_goal(GOAL)

                self.assertEqual(result.status, "failed")
                self.assertIn("the model provider failed", result.detail)


class CatalogCheckTests(unittest.TestCase):
    def test_has_enabled_follows_disable_and_enable(self) -> None:
        registry = ResourceRegistry()
        self.assertFalse(registry.has_enabled())
        registry.add(ResourceDefinition.from_mapping(_tool("tool.report")))
        self.assertTrue(registry.has_enabled())
        registry.disable("tool.report")
        self.assertFalse(registry.has_enabled())
        registry.enable("tool.report")
        self.assertTrue(registry.has_enabled())

    def test_the_kernel_does_not_list_the_catalog_to_see_whether_it_is_empty(self) -> None:
        registry = _registry(_tool("tool.report"))
        kernel = Kernel(registry, _ToolThenAnswer(), tool_implementations={"tool.report": _Handler()})

        with mock.patch.object(registry, "list", wraps=registry.list) as listed:
            result = kernel.run_goal("an unrelated request about gardening")

        self.assertEqual(result.status, "completed", result.detail)
        listed.assert_not_called()


if __name__ == "__main__":
    unittest.main()
