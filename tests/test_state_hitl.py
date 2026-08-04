from __future__ import annotations

from pathlib import Path
import json
import os
import subprocess
import sys
import tempfile
import time
import unittest

from marmo_core import (
    AutoApproveHitlBroker,
    CallbackHitlBroker,
    GreedyConstrainedSetSelector,
    HitlError,
    HitlPolicy,
    HitlRequest,
    HitlResponse,
    InMemoryStateStore,
    JsonFileStateStore,
    Kernel,
    LLMResponse,
    MockLLMProvider,
    PendingHitlBroker,
    PolicyContext,
    ResourceDefinition,
    ResourceRegistry,
    SQLiteStateStore,
    StateConflictError,
    TaskNotFoundError,
    ToolCall,
)


ROOT = Path(__file__).resolve().parents[1]


def _base_fields(resource_id: str, kind: str, **overrides) -> dict:
    data = {
        "id": resource_id,
        "kind": kind,
        "name": resource_id,
        "version": "1.0.0",
        "description": f"{kind} resource for state tests: add numbers with a calculator",
        "capabilities": ["calculator", "addition"],
        "input_summary": "numbers",
        "output_summary": "sum",
        "required_permissions": [],
        "cost_estimate": 0.0,
        "latency_class": "fast",
        "side_effect": "none",
        "trust_level": "core",
        "ref": f"{kind}://test/{resource_id}",
        "tags": ["math", "calculator"],
    }
    data.update(overrides)
    return data


def _tool_definition(resource_id: str = "tool.test.add", **overrides) -> dict:
    data = _base_fields(resource_id, "tool", **overrides)
    data.setdefault(
        "input_schema",
        {
            "type": "object",
            "required": ["a", "b"],
            "properties": {"a": {"type": "number"}, "b": {"type": "number"}},
        },
    )
    return data


def _build_registry(*entries: dict) -> ResourceRegistry:
    registry = ResourceRegistry()
    for entry in entries:
        registry.add(ResourceDefinition.from_mapping(entry))
    return registry


class _Counter:
    """Tool handler that records how many times it actually ran."""

    def __init__(self) -> None:
        self.calls = 0

    def __call__(self, a: float, b: float) -> dict:
        self.calls += 1
        return {"sum": a + b}


class StateStoreContract:
    """Shared behaviour every backend must satisfy (F-STATE-05)."""

    def make_store(self):  # pragma: no cover - overridden
        raise NotImplementedError

    def test_create_and_load_roundtrip(self) -> None:
        store = self.make_store()
        state = store.create("summarize the changelog", session_id="s1")

        loaded = store.load(state.task_id)
        self.assertEqual(loaded.goal, "summarize the changelog")
        self.assertEqual(loaded.status, "submitted")
        self.assertEqual(loaded.session_id, "s1")
        self.assertEqual(loaded.version, 1)

    def test_unknown_task_is_educational(self) -> None:
        store = self.make_store()
        with self.assertRaises(TaskNotFoundError) as ctx:
            store.load("does-not-exist")
        self.assertIn("submit a goal first", str(ctx.exception))

    def test_events_rebuild_any_past_point(self) -> None:
        store = self.make_store()
        state = store.create("goal")
        store.append(state.task_id, "variable", {"key": "step", "value": 1})
        at_two = store.load(state.task_id).version
        store.append(state.task_id, "variable", {"key": "step", "value": 2})

        self.assertEqual(store.load(state.task_id).variables["step"], 2)
        self.assertEqual(store.replay(state.task_id, until_seq=at_two).variables["step"], 1)

    def test_optimistic_locking_rejects_a_stale_write(self) -> None:
        store = self.make_store()
        state = store.create("goal")
        store.append(state.task_id, "variable", {"key": "a", "value": 1})

        with self.assertRaises(StateConflictError) as ctx:
            store.append(state.task_id, "variable", {"key": "b", "value": 2}, expected_version=state.version)
        self.assertIn("reload the state", str(ctx.exception))

    def test_checkpoint_and_rollback(self) -> None:
        store = self.make_store()
        state = store.create("goal")
        store.append(state.task_id, "variable", {"key": "keep", "value": "yes"})
        store.checkpoint(state.task_id, "before-risky")
        store.append(state.task_id, "variable", {"key": "risky", "value": "oops"})

        rolled = store.rollback(state.task_id, "before-risky")

        self.assertEqual(rolled.variables, {"keep": "yes"})
        self.assertNotIn("risky", rolled.variables)
        # The log stays append-only: the discarded event is still replayable.
        self.assertTrue(any(event.kind == "rollback" for event in store.events(state.task_id)))
        self.assertGreater(rolled.version, 4)

    def test_rollback_to_unknown_checkpoint_lists_options(self) -> None:
        store = self.make_store()
        state = store.create("goal")
        store.checkpoint(state.task_id, "known")

        with self.assertRaises(ValueError) as ctx:
            store.rollback(state.task_id, "typo")
        self.assertIn("known", str(ctx.exception))

    def test_short_and_long_term_state_are_separate(self) -> None:
        store = self.make_store()
        first = store.create("first task", session_id="session-a")
        store.append(first.task_id, "variable", {"key": "draft", "value": "task-scoped"})
        store.remember("session-a", "user_timezone", "Asia/Tokyo")

        second = store.create("second task", session_id="session-a")

        self.assertEqual(store.load(second.task_id).variables, {})
        self.assertEqual(store.recall("session-a", "user_timezone"), "Asia/Tokyo")
        store.forget("session-a", "user_timezone")
        self.assertIsNone(store.recall("session-a", "user_timezone"))

    def test_list_tasks_filters_by_status(self) -> None:
        store = self.make_store()
        done = store.create("done")
        store.append(done.task_id, "status", {"status": "completed"})
        store.create("open")

        self.assertEqual([state.goal for state in store.list_tasks(status="completed")], ["done"])
        self.assertEqual(len(store.list_tasks()), 2)

    def test_resource_and_operation_approvals_are_stored_separately(self) -> None:
        store = self.make_store()
        state = store.create("approve one exact operation")

        resumed = store.append(
            state.task_id,
            "resumed",
            {
                "approvals": ["tool.test.shell@1.0.0"],
                "operation_approvals": ["operation:abc123"],
            },
        )

        self.assertEqual(resumed.approvals, ("tool.test.shell@1.0.0",))
        self.assertEqual(resumed.operation_approvals, ("operation:abc123",))


class InMemoryStateStoreTests(StateStoreContract, unittest.TestCase):
    def make_store(self):
        return InMemoryStateStore()


class JsonFileStateStoreTests(StateStoreContract, unittest.TestCase):
    def setUp(self) -> None:
        self._temp = tempfile.TemporaryDirectory()
        self.addCleanup(self._temp.cleanup)

    def make_store(self):
        return JsonFileStateStore(Path(self._temp.name) / "state")

    def test_state_survives_a_new_store_instance(self) -> None:
        root = Path(self._temp.name) / "durable"
        state = JsonFileStateStore(root).create("goal")
        JsonFileStateStore(root).append(state.task_id, "variable", {"key": "a", "value": 1})

        reopened = JsonFileStateStore(root).load(state.task_id)

        self.assertEqual(reopened.variables, {"a": 1})


class SQLiteStateStoreTests(StateStoreContract, unittest.TestCase):
    def setUp(self) -> None:
        self._temp = tempfile.TemporaryDirectory()
        self.addCleanup(self._temp.cleanup)
        self._index = 0

    def make_store(self):
        self._index += 1
        store = SQLiteStateStore(Path(self._temp.name) / f"state-{self._index}.db")
        self.addCleanup(store.close)
        return store

    def test_state_survives_a_new_connection(self) -> None:
        path = Path(self._temp.name) / "durable.db"
        first = SQLiteStateStore(path)
        state = first.create("goal")
        first.append(state.task_id, "variable", {"key": "a", "value": 1})
        first.close()

        second = SQLiteStateStore(path)
        self.addCleanup(second.close)

        self.assertEqual(second.load(state.task_id).variables, {"a": 1})


class HitlPrimitiveTests(unittest.TestCase):
    def _request(self, stage: str = "execution") -> HitlRequest:
        return HitlRequest.create(
            task_id="t1",
            stage=stage,
            operation="execute tool x",
            impact="side_effect=external",
        )

    def test_modify_requires_replacement_arguments(self) -> None:
        with self.assertRaises(ValueError):
            HitlResponse(kind="modify")

    def test_unknown_kind_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            HitlResponse(kind="maybe")

    def test_request_roundtrips_through_dict(self) -> None:
        request = self._request()
        restored = HitlRequest.from_dict(request.to_dict())

        self.assertEqual(restored, request)

    def test_only_listed_approvers_may_approve(self) -> None:
        policy = HitlPolicy(approvers=("alice",))
        broker = PendingHitlBroker(policy)
        request = self._request()

        with self.assertRaises(HitlError) as ctx:
            broker.accept(HitlResponse(kind="approve", responder="mallory"), request)
        self.assertIn("alice", str(ctx.exception))
        # Rejecting and deferring stay open to anyone: they cannot widen risk.
        broker.accept(HitlResponse(kind="reject", responder="mallory"), request)

    def test_response_must_target_the_pending_request(self) -> None:
        broker = PendingHitlBroker()
        request = self._request()

        with self.assertRaises(HitlError) as ctx:
            broker.accept(HitlResponse(kind="approve", request_id="stale"), request)
        self.assertIn("pending", str(ctx.exception))

    def test_bare_response_is_bound_to_the_pending_request(self) -> None:
        broker = PendingHitlBroker()
        request = self._request()

        accepted = broker.accept(HitlResponse(kind="approve"), request)

        self.assertEqual(accepted.request_id, request.request_id)

    def test_modify_only_applies_to_tool_arguments(self) -> None:
        broker = PendingHitlBroker()

        with self.assertRaises(HitlError) as ctx:
            broker.accept(HitlResponse(kind="modify", arguments={"a": 1}), self._request("activation"))
        self.assertIn("stage 'execution'", str(ctx.exception))

    def test_timeout_can_deny_or_stay_pending(self) -> None:
        def slow(request: HitlRequest) -> HitlResponse:
            time.sleep(0.3)
            return HitlResponse(kind="approve", request_id=request.request_id)

        denying = CallbackHitlBroker(slow, HitlPolicy(timeout_seconds=0.05, on_timeout="deny"))
        waiting = CallbackHitlBroker(slow, HitlPolicy(timeout_seconds=0.05, on_timeout="pending"))

        self.assertEqual(denying.request(self._request()).kind, "reject")
        self.assertIsNone(waiting.request(self._request()))

    def test_always_confirm_matches_id_identity_and_side_effect(self) -> None:
        metadata = ResourceDefinition.from_mapping(_tool_definition()).metadata

        self.assertTrue(HitlPolicy(always_confirm_resources=("tool.test.add",)).requires_confirmation(metadata))
        self.assertTrue(
            HitlPolicy(always_confirm_resources=("tool.test.add@1.0.0",)).requires_confirmation(metadata)
        )
        self.assertTrue(HitlPolicy(always_confirm_side_effects=("none",)).requires_confirmation(metadata))
        self.assertFalse(HitlPolicy().requires_confirmation(metadata))


class KernelHitlTests(unittest.TestCase):
    def _kernel(self, registry: ResourceRegistry, handler=None, **kwargs) -> Kernel:
        kwargs.setdefault("tool_implementations", {"tool.test.add": handler or _Counter()})
        kwargs.setdefault("policy_context", PolicyContext(granted_permissions=("math.add",)))
        llm = kwargs.pop("llm", None) or MockLLMProvider(tool_arguments={"tool.test.add": {"a": 2, "b": 3}})
        return Kernel(registry, llm, **kwargs)

    def test_pause_persists_the_request_and_approval_completes_the_task(self) -> None:
        registry = _build_registry(_tool_definition(side_effect="external"))
        kernel = self._kernel(registry)

        paused = kernel.run_goal("Add 2 and 3 with the calculator")

        self.assertTrue(paused.paused)
        self.assertIsNotNone(paused.hitl_request)
        request = kernel.pending_request(paused.task_id)
        self.assertEqual(request.stage, "activation")
        self.assertEqual(request.resource, "tool.test.add@1.0.0")
        self.assertIn("side_effect=external", request.impact)
        self.assertEqual(kernel.get_state(paused.task_id)["status"], "escalated")

        resumed = kernel.resume(paused.task_id, HitlResponse(kind="approve", responder="alice"))

        self.assertEqual(resumed.status, "completed", resumed.detail)
        self.assertEqual(resumed.tool_results[0].output, {"sum": 5})

    def test_approval_is_scoped_to_the_reviewed_resource(self) -> None:
        registry = _build_registry(_tool_definition(side_effect="external"))
        kernel = self._kernel(registry)
        paused = kernel.run_goal("Add 2 and 3 with the calculator")
        kernel.resume(paused.task_id, HitlResponse(kind="approve"))

        state = kernel.get_state(paused.task_id)

        self.assertEqual(state["approvals"], ["tool.test.add@1.0.0"])
        # The blanket flag stays off: only the reviewed resource was cleared.
        self.assertFalse(kernel.policy_context.human_approved)

    def test_rejection_denies_the_task(self) -> None:
        registry = _build_registry(_tool_definition(side_effect="external"))
        kernel = self._kernel(registry)
        paused = kernel.run_goal("Add 2 and 3 with the calculator")

        denied = kernel.resume(
            paused.task_id, HitlResponse(kind="reject", responder="alice", note="not this week")
        )

        self.assertEqual(denied.status, "denied")
        self.assertIn("not this week", denied.detail)
        self.assertTrue(kernel.state_store.load(paused.task_id).terminal)

    def test_defer_leaves_the_task_paused(self) -> None:
        registry = _build_registry(_tool_definition(side_effect="external"))
        kernel = self._kernel(registry)
        paused = kernel.run_goal("Add 2 and 3 with the calculator")

        deferred = kernel.resume(paused.task_id, HitlResponse(kind="defer", responder="alice"))

        self.assertTrue(deferred.paused)
        self.assertIsNotNone(kernel.pending_request(paused.task_id))

    def test_running_a_paused_task_keeps_the_same_pending_request(self) -> None:
        registry = _build_registry(_tool_definition(side_effect="external"))
        kernel = self._kernel(registry)
        paused = kernel.run_goal("Add 2 and 3 with the calculator")
        request_id = kernel.pending_request(paused.task_id).request_id

        again = kernel.run(paused.task_id)

        # Re-offering the pending request keeps the id an operator is holding
        # valid, instead of minting a new one behind their back.
        self.assertTrue(again.paused)
        self.assertEqual(kernel.pending_request(paused.task_id).request_id, request_id)
        kernel.resume(paused.task_id, HitlResponse(kind="approve", request_id=request_id))
        self.assertEqual(kernel.get_state(paused.task_id)["status"], "completed")

    def test_answering_broker_completes_within_one_run(self) -> None:
        registry = _build_registry(_tool_definition(side_effect="external"))
        kernel = self._kernel(registry, hitl=AutoApproveHitlBroker())

        result = kernel.run_goal("Add 2 and 3 with the calculator")

        self.assertEqual(result.status, "completed", result.detail)

    def test_resume_does_not_re_execute_a_tool_that_already_ran(self) -> None:
        safe = _Counter()
        risky = _Counter()
        registry = _build_registry(
            _tool_definition("tool.test.add"),
            _tool_definition("tool.test.publish", side_effect="external"),
        )
        script = [
            LLMResponse(
                content="",
                tool_calls=(
                    ToolCall(id="c1", name="tool.test.add", arguments={"a": 2, "b": 3}),
                    ToolCall(id="c2", name="tool.test.publish", arguments={"a": 1, "b": 1}),
                ),
            ),
            LLMResponse(content="all done"),
        ]
        kernel = self._kernel(
            registry,
            llm=MockLLMProvider(script=script),
            tool_implementations={"tool.test.add": safe, "tool.test.publish": risky},
            hitl=PendingHitlBroker(HitlPolicy(always_confirm_resources=("tool.test.publish",))),
            policy_context=PolicyContext(granted_permissions=("math.add",), human_approved=True),
            set_limits={"tool": 2},
        )

        paused = kernel.run_goal("Add 2 and 3 then publish the result")

        # human_approved clears the gates, but an always-confirm resource
        # still stops for its own review.
        self.assertTrue(paused.paused, paused.detail)
        self.assertEqual(kernel.pending_request(paused.task_id).stage, "execution")
        self.assertEqual(safe.calls, 1)
        self.assertEqual(risky.calls, 0)

        resumed = kernel.resume(paused.task_id, HitlResponse(kind="approve"))

        self.assertEqual(resumed.status, "completed", resumed.detail)
        self.assertEqual(safe.calls, 1, "the already-executed tool must not run a second time")
        self.assertEqual(risky.calls, 1)
        self.assertEqual(len(resumed.tool_results), 2)

    def test_modify_replaces_the_tool_arguments_before_it_runs(self) -> None:
        registry = _build_registry(_tool_definition())
        kernel = self._kernel(
            registry,
            hitl=PendingHitlBroker(HitlPolicy(always_confirm_resources=("tool.test.add",))),
        )
        paused = kernel.run_goal("Add 2 and 3 with the calculator")
        self.assertEqual(kernel.pending_request(paused.task_id).arguments, {"a": 2, "b": 3})

        edited = kernel.resume(paused.task_id, HitlResponse(kind="modify", arguments={"a": 10, "b": 5}))

        self.assertEqual(edited.status, "completed", edited.detail)
        self.assertEqual(edited.tool_results[0].arguments, {"a": 10, "b": 5})
        self.assertEqual(edited.tool_results[0].output, {"sum": 15})

    def test_always_confirm_pauses_a_resource_the_gate_would_allow(self) -> None:
        registry = _build_registry(_tool_definition())
        kernel = self._kernel(
            registry,
            hitl=PendingHitlBroker(HitlPolicy(always_confirm_resources=("tool.test.add",))),
        )

        paused = kernel.run_goal("Add 2 and 3 with the calculator")

        self.assertTrue(paused.paused)
        self.assertIn("always confirms", paused.detail)
        request = kernel.pending_request(paused.task_id)
        self.assertEqual(request.stage, "execution")
        self.assertEqual(request.arguments, {"a": 2, "b": 3})

    def test_selection_escalation_grants_the_missing_permissions(self) -> None:
        registry = _build_registry(_tool_definition(required_permissions=["math.add"]))
        kernel = self._kernel(
            registry,
            policy_context=PolicyContext(),
            selector=GreedyConstrainedSetSelector(),
        )

        paused = kernel.run_goal("Add 2 and 3 with the calculator")

        self.assertTrue(paused.paused, paused.detail)
        request = kernel.pending_request(paused.task_id)
        self.assertEqual(request.stage, "selection")
        self.assertEqual(request.arguments["missing_permissions"], ["math.add"])

        resumed = kernel.resume(paused.task_id, HitlResponse(kind="approve", responder="alice"))

        self.assertEqual(resumed.status, "completed", resumed.detail)
        self.assertEqual(kernel.get_state(paused.task_id)["granted_permissions"], ["math.add"])

    def test_unauthorized_approver_is_refused_at_resume(self) -> None:
        registry = _build_registry(_tool_definition(side_effect="external"))
        kernel = self._kernel(registry, hitl=PendingHitlBroker(HitlPolicy(approvers=("alice",))))
        paused = kernel.run_goal("Add 2 and 3 with the calculator")

        with self.assertRaises(HitlError):
            kernel.resume(paused.task_id, HitlResponse(kind="approve", responder="mallory"))

        self.assertTrue(kernel.state_store.load(paused.task_id).pending is not None)

    def test_resume_without_a_pending_request_is_educational(self) -> None:
        registry = _build_registry(_tool_definition())
        kernel = self._kernel(registry)
        task_id = kernel.submit("Add 2 and 3 with the calculator")

        with self.assertRaises(HitlError) as ctx:
            kernel.resume(task_id, HitlResponse(kind="approve"))
        self.assertIn("not waiting for a human answer", str(ctx.exception))

    def test_cancel_ends_the_task(self) -> None:
        registry = _build_registry(_tool_definition(side_effect="external"))
        kernel = self._kernel(registry)
        paused = kernel.run_goal("Add 2 and 3 with the calculator")

        kernel.cancel(paused.task_id)

        self.assertEqual(kernel.get_state(paused.task_id)["status"], "cancelled")
        self.assertEqual(kernel.run(paused.task_id).status, "cancelled")

    def test_a_paused_task_resumes_in_a_fresh_kernel(self) -> None:
        handler = _Counter()
        registry = _build_registry(_tool_definition(side_effect="external"))
        with tempfile.TemporaryDirectory() as temp_dir:
            store_root = Path(temp_dir) / "state"
            first = self._kernel(registry, handler=handler, state_store=JsonFileStateStore(store_root))
            paused = first.run_goal("Add 2 and 3 with the calculator")
            self.assertTrue(paused.paused)

            # A different process would rebuild everything from disk.
            second = self._kernel(registry, handler=handler, state_store=JsonFileStateStore(store_root))
            resumed = second.resume(paused.task_id, HitlResponse(kind="approve", responder="alice"))

        self.assertEqual(resumed.status, "completed", resumed.detail)
        self.assertEqual(handler.calls, 1)

    def test_audit_log_records_the_request_and_the_response(self) -> None:
        registry = _build_registry(_tool_definition(side_effect="external"))
        kernel = self._kernel(registry)
        paused = kernel.run_goal("Add 2 and 3 with the calculator")
        kernel.resume(paused.task_id, HitlResponse(kind="approve", responder="alice"))

        hitl_records = [record for record in kernel.audit_log.records if record.kind == "hitl"]
        events = [record.payload["event"] for record in hitl_records]

        self.assertIn("requested", events)
        self.assertIn("responded", events)
        responded = next(record for record in hitl_records if record.payload["event"] == "responded")
        self.assertEqual(responded.payload["response"]["responder"], "alice")
        self.assertEqual(kernel.audit_log.verify(), [])

    def test_state_records_steps_and_activated_resources(self) -> None:
        registry = _build_registry(
            _tool_definition(),
            _base_fields("skill.test.arithmetic", "skill", instructions=["Use the calculator tool."]),
        )
        kernel = self._kernel(registry)
        result = kernel.run_goal("Add 2 and 3 with the calculator")

        state = kernel.get_state(result.task_id)

        self.assertEqual(state["status"], "completed")
        self.assertIn("tool.test.add@1.0.0", state["activated"])
        self.assertEqual(len(state["step_results"]), 1)
        self.assertEqual(state["step_results"][0]["output"], {"sum": 5})


class ExampleAndCliTests(unittest.TestCase):
    def test_human_in_the_loop_example_runs(self) -> None:
        result = subprocess.run(
            [sys.executable, "examples/human_in_the_loop.py"],
            cwd=ROOT,
            env={**os.environ, "PYTHONPATH": str(ROOT)},
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("status: escalated", result.stdout)
        self.assertIn("status: completed", result.stdout)
        self.assertIn("audit hash chain verified.", result.stdout)

    def _cli(self, *argv: str) -> subprocess.CompletedProcess:
        return subprocess.run(
            [sys.executable, "-m", "marmo_core.cli", *argv],
            cwd=ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )

    def test_cli_pauses_then_resumes_in_a_separate_process(self) -> None:
        resource = _tool_definition(
            "tool.demo.dumps",
            ref="python:json:dumps",
            side_effect="external",
            description="Serialize a list to a JSON string and send it outside.",
            input_schema={
                "type": "object",
                "required": ["obj"],
                "properties": {"obj": {"type": "array"}},
            },
        )
        with tempfile.TemporaryDirectory() as temp_dir:
            resource_path = Path(temp_dir) / "demo_tool.json"
            resource_path.write_text(json.dumps(resource), encoding="utf-8")
            state_dir = str(Path(temp_dir) / "state")
            audit_path = str(Path(temp_dir) / "audit.jsonl")
            tool_args = '{"tool.demo.dumps": {"obj": [1, 2]}}'

            first = self._cli(
                "run", "--task", "send a list outside", str(resource_path),
                "--tool-args", tool_args, "--state-dir", state_dir,
                "--audit-log", audit_path, "--approver", "alice",
            )
            self.assertEqual(first.returncode, 1, first.stderr or first.stdout)
            self.assertIn("status: escalated", first.stdout)
            self.assertIn("awaiting confirmation:", first.stdout)

            listed = self._cli("tasks", "--state-dir", state_dir, "--format", "json")
            self.assertEqual(listed.returncode, 0, listed.stderr)
            tasks = json.loads(listed.stdout)["tasks"]
            self.assertEqual(len(tasks), 1)
            task_id = tasks[0]["task_id"]

            refused = self._cli(
                "resume", "--task-id", task_id, str(resource_path), "--approve",
                "--responder", "mallory", "--tool-args", tool_args,
                "--state-dir", state_dir, "--approver", "alice",
            )
            self.assertEqual(refused.returncode, 2, refused.stdout)
            self.assertIn("may not approve", refused.stderr)

            second = self._cli(
                "resume", "--task-id", task_id, str(resource_path), "--approve",
                "--responder", "alice", "--tool-args", tool_args,
                "--state-dir", state_dir, "--audit-log", audit_path, "--approver", "alice",
            )
            self.assertEqual(second.returncode, 0, second.stderr or second.stdout)
            self.assertIn("status: completed", second.stdout)
            self.assertIn("tool: tool.demo.dumps status=success", second.stdout)

            records = [json.loads(line) for line in Path(audit_path).read_text(encoding="utf-8").splitlines() if line]

        # The chain spans both processes uninterrupted (F-LOG-03/04).
        kinds = [record["kind"] for record in records]
        self.assertIn("hitl", kinds)
        self.assertIn("execute", kinds)
        for previous, current in zip(records, records[1:]):
            self.assertEqual(current["prev_hash"], previous["hash"])


if __name__ == "__main__":
    unittest.main()
