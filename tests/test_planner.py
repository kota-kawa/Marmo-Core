from __future__ import annotations

import threading
import time
import unittest

from marmo_core import (
    HitlPolicy,
    HitlResponse,
    Kernel,
    LLMPlanner,
    LLMResponse,
    MockLLMProvider,
    PendingHitlBroker,
    Plan,
    PlanStep,
    PolicyContext,
    RecoveryManager,
    ResourceDefinition,
    ResourceRegistry,
    RetryPolicy,
    RuleBasedPlanner,
    validate_plan,
)
from marmo_core.planner import parse_plan_reply, resources_by_id


def _tool(resource_id: str, description: str, **overrides) -> dict:
    data = {
        "id": resource_id,
        "kind": "tool",
        "name": resource_id,
        "version": "1.0.0",
        "description": description,
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


def _definitions(*entries: dict) -> list[ResourceDefinition]:
    return [ResourceDefinition.from_mapping(entry) for entry in entries]


def _registry(*entries: dict) -> ResourceRegistry:
    registry = ResourceRegistry()
    for entry in entries:
        registry.add(ResourceDefinition.from_mapping(entry))
    return registry


def _step(step_id: str, resource_id: str = "tool.a", depends_on: tuple = (), **kw) -> PlanStep:
    return PlanStep(id=step_id, description=step_id, resource_id=resource_id, depends_on=depends_on, **kw)


class PlanModelTests(unittest.TestCase):
    def test_ready_returns_only_steps_whose_dependencies_finished(self) -> None:
        plan = Plan(
            goal="g",
            steps=(_step("s1"), _step("s2", depends_on=("s1",)), _step("s3")),
        )

        self.assertEqual({step.id for step in plan.ready()}, {"s1", "s3"})

        plan = plan.with_status("s1", "completed")
        self.assertEqual({step.id for step in plan.ready()}, {"s2", "s3"})

    def test_order_groups_independent_steps_into_one_wave(self) -> None:
        plan = Plan(
            goal="g",
            steps=(_step("s1"), _step("s2"), _step("s3", depends_on=("s1", "s2"))),
        )

        waves = plan.order()

        self.assertEqual([{step.id for step in wave} for wave in waves], [{"s1", "s2"}, {"s3"}])

    def test_cycles_are_detected(self) -> None:
        plan = Plan(goal="g", steps=(_step("s1", depends_on=("s2",)), _step("s2", depends_on=("s1",))))

        with self.assertRaises(ValueError):
            plan.order()

    def test_completion_and_failure_flags(self) -> None:
        plan = Plan(goal="g", steps=(_step("s1"), _step("s2")))

        self.assertFalse(plan.complete)
        plan = plan.with_status("s1", "completed").with_status("s2", "failed")
        self.assertFalse(plan.complete)
        self.assertTrue(plan.failed)

    def test_roundtrips_through_dict(self) -> None:
        plan = Plan(goal="g", steps=(_step("s1"), _step("s2", depends_on=("s1",))), revision=3)

        self.assertEqual(Plan.from_dict(plan.to_dict()), plan)

    def test_unknown_step_status_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            PlanStep(id="s", description="d", resource_id="r", status="nonsense")


class PlanValidationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.resources = resources_by_id(_definitions(_tool("tool.a", "Fetch the quarterly report.")))

    def _messages(self, plan: Plan, context: PolicyContext | None = None) -> list[str]:
        return [issue.message for issue in validate_plan(plan, self.resources, context)]

    def test_a_good_plan_has_no_issues(self) -> None:
        plan = Plan(goal="g", steps=(_step("s1"),))

        self.assertEqual(validate_plan(plan, self.resources, PolicyContext()), [])

    def test_unknown_resource_is_reported(self) -> None:
        plan = Plan(goal="g", steps=(_step("s1", resource_id="tool.missing"),))

        self.assertTrue(any("unknown resource" in message for message in self._messages(plan)))

    def test_unknown_dependency_is_reported(self) -> None:
        plan = Plan(goal="g", steps=(_step("s1", depends_on=("nope",)),))

        self.assertTrue(any("unknown step" in message for message in self._messages(plan)))

    def test_duplicate_step_ids_are_reported(self) -> None:
        plan = Plan(goal="g", steps=(_step("s1"), _step("s1")))

        self.assertTrue(any("duplicate step id" in message for message in self._messages(plan)))

    def test_cycle_is_reported_rather_than_raised(self) -> None:
        plan = Plan(goal="g", steps=(_step("s1", depends_on=("s2",)), _step("s2", depends_on=("s1",))))

        self.assertTrue(any("cycle" in message for message in self._messages(plan)))

    def test_missing_permissions_are_caught_before_execution(self) -> None:
        resources = resources_by_id(
            _definitions(_tool("tool.a", "Fetch.", required_permissions=["reports.read"]))
        )
        plan = Plan(goal="g", steps=(_step("s1"),))

        issues = validate_plan(plan, resources, PolicyContext())

        self.assertTrue(any("were not granted" in issue.message for issue in issues))
        self.assertEqual(validate_plan(plan, resources, PolicyContext(granted_permissions=("reports.read",))), [])


class RuleBasedPlannerTests(unittest.TestCase):
    def test_one_step_per_tool_with_schema_defaults(self) -> None:
        definitions = _definitions(_tool("tool.a", "Fetch."), _tool("tool.b", "Publish."))

        plan = RuleBasedPlanner().plan("do the thing", definitions)

        self.assertEqual([step.resource_id for step in plan.steps], ["tool.a", "tool.b"])
        self.assertEqual(plan.steps[0].arguments, {"name": "q3"})
        self.assertEqual([step.depends_on for step in plan.steps], [(), ()])

    def test_declared_dependencies_become_edges(self) -> None:
        definitions = _definitions(
            _tool("tool.a", "Fetch."),
            _tool("tool.b", "Publish.", dependencies=["tool.a"]),
        )

        plan = RuleBasedPlanner().plan("do the thing", definitions)

        self.assertEqual(plan.step("s2").depends_on, ("s1",))
        self.assertEqual([{s.id for s in wave} for wave in plan.order()], [{"s1"}, {"s2"}])

    def test_dependencies_outside_the_offered_set_are_dropped(self) -> None:
        # An edge to a step that does not exist would fail validation, so a
        # dependency nobody selected must not become one.
        definitions = _definitions(_tool("tool.b", "Publish.", dependencies=["tool.elsewhere"]))

        plan = RuleBasedPlanner().plan("do the thing", definitions)

        self.assertEqual(plan.steps[0].depends_on, ())
        self.assertEqual(validate_plan(plan, resources_by_id(definitions), PolicyContext()), [])

    def test_explicit_arguments_win_over_defaults(self) -> None:
        planner = RuleBasedPlanner(step_arguments={"tool.a": {"name": "q4"}})

        plan = planner.plan("do the thing", _definitions(_tool("tool.a", "Fetch.")))

        self.assertEqual(plan.steps[0].arguments, {"name": "q4"})

    def test_non_tool_resources_do_not_become_steps(self) -> None:
        memory = _tool("memory.notes", "Notes.")
        memory["kind"] = "memory"
        definitions = _definitions(_tool("tool.a", "Fetch."), memory)

        plan = RuleBasedPlanner().plan("do the thing", definitions)

        self.assertEqual([step.resource_id for step in plan.steps], ["tool.a"])

    def test_default_replan_drops_the_failure_and_its_dependents(self) -> None:
        plan = Plan(
            goal="g",
            steps=(
                _step("s1", status="completed"),
                _step("s2", status="failed"),
                _step("s3", depends_on=("s2",)),
                _step("s4"),
            ),
        )

        revised = RuleBasedPlanner().replan(plan, [])

        self.assertEqual([step.id for step in revised.steps], ["s1", "s4"])
        self.assertEqual(revised.revision, 2)


class LLMPlannerTests(unittest.TestCase):
    def _planner(self, reply: str) -> LLMPlanner:
        return LLMPlanner(MockLLMProvider(script=[LLMResponse(content=reply)]))

    def test_parses_a_json_plan(self) -> None:
        reply = (
            '{"steps": [{"id": "a", "description": "fetch", "resource_id": "tool.a", '
            '"arguments": {"name": "q3"}}, {"id": "b", "description": "publish", '
            '"resource_id": "tool.b", "depends_on": ["a"]}]}'
        )
        plan = self._planner(reply).plan("goal", _definitions(_tool("tool.a", "Fetch."), _tool("tool.b", "Pub.")))

        self.assertEqual([step.id for step in plan.steps], ["a", "b"])
        self.assertEqual(plan.step("b").depends_on, ("a",))

    def test_steps_naming_tools_that_were_not_offered_are_dropped(self) -> None:
        reply = '{"steps": [{"id": "a", "resource_id": "tool.a"}, {"id": "b", "resource_id": "tool.hallucinated"}]}'

        plan = self._planner(reply).plan("goal", _definitions(_tool("tool.a", "Fetch.")))

        self.assertEqual([step.resource_id for step in plan.steps], ["tool.a"])

    def test_a_reply_cannot_mark_work_as_already_done(self) -> None:
        reply = '{"steps": [{"id": "a", "resource_id": "tool.a", "status": "completed", "result": {"x": 1}}]}'

        plan = self._planner(reply).plan("goal", _definitions(_tool("tool.a", "Fetch.")))

        self.assertEqual(plan.steps[0].status, "pending")
        self.assertIsNone(plan.steps[0].result)

    def test_unusable_replies_produce_an_empty_plan_rather_than_a_guess(self) -> None:
        self.assertEqual(parse_plan_reply("I cannot help with that"), None)
        self.assertEqual(parse_plan_reply('{"nope": 1}'), None)
        self.assertEqual(self._planner("sorry").plan("goal", _definitions(_tool("tool.a", "F."))).steps, ())

    def test_replies_are_cached_so_a_repeat_costs_nothing(self) -> None:
        llm = MockLLMProvider(script=[LLMResponse(content='{"steps": [{"id": "a", "resource_id": "tool.a"}]}')])
        planner = LLMPlanner(llm)
        definitions = _definitions(_tool("tool.a", "Fetch."))

        first = planner.plan("goal", definitions)
        second = planner.plan("goal", definitions)

        self.assertEqual(first, second)
        self.assertEqual(len(llm.requests), 1)

    def test_llm_failure_falls_back_to_dropping_the_failed_branch(self) -> None:
        class _Broken(MockLLMProvider):
            def complete(self, messages, tools=()):
                raise RuntimeError("model down")

        planner = LLMPlanner(_Broken())
        plan = Plan(goal="g", steps=(_step("s1", status="completed"), _step("s2", status="failed")))

        revised = planner.replan(plan, _definitions(_tool("tool.a", "F.")))

        self.assertEqual([step.id for step in revised.steps], ["s1"])


class _Recorder:
    """Tool handler that records call order and can be made slow or broken."""

    def __init__(self, name: str, log: list[str], *, delay: float = 0.0, error: Exception | None = None) -> None:
        self.name = name
        self.log = log
        self.delay = delay
        self.error = error
        self.calls = 0
        self._lock = threading.Lock()

    def __call__(self, name: str) -> dict:
        with self._lock:
            self.calls += 1
        self.log.append(f"start:{self.name}")
        if self.delay:
            time.sleep(self.delay)
        if self.error:
            raise self.error
        self.log.append(f"end:{self.name}")
        return {"tool": self.name, "name": name}


class KernelPlanExecutionTests(unittest.TestCase):
    GOAL = "produce the quarterly report"

    def _kernel(self, entries, implementations, **kwargs) -> Kernel:
        kwargs.setdefault("planner", RuleBasedPlanner())
        kwargs.setdefault("policy_context", PolicyContext())
        kwargs.setdefault("set_limits", {"tool": 4})
        kwargs.setdefault(
            "recovery",
            RecoveryManager(retry_policy=RetryPolicy(initial_backoff_seconds=0.0), sleep=lambda _: None),
        )
        llm = kwargs.pop("llm", None) or MockLLMProvider(script=[LLMResponse(content="report ready")])
        return Kernel(_registry(*entries), llm, tool_implementations=implementations, **kwargs)

    def test_a_plan_runs_every_step_and_is_persisted(self) -> None:
        log: list[str] = []
        entries = [_tool("tool.fetch", "Fetch the quarterly report figures."),
                   _tool("tool.render", "Render the quarterly report document.", dependencies=["tool.fetch"])]
        handlers = {"tool.fetch": _Recorder("fetch", log), "tool.render": _Recorder("render", log)}
        kernel = self._kernel(entries, handlers)

        result = kernel.run_goal(self.GOAL)

        self.assertEqual(result.status, "completed", result.detail)
        self.assertEqual(result.output, "report ready")
        self.assertEqual(len(result.tool_results), 2)
        plan = kernel.get_state(result.task_id)["plan"]
        self.assertEqual([step["status"] for step in plan["steps"]], ["completed", "completed"])

    def test_declared_dependencies_are_respected(self) -> None:
        log: list[str] = []
        entries = [_tool("tool.fetch", "Fetch the quarterly report figures."),
                   _tool("tool.render", "Render the quarterly report document.", dependencies=["tool.fetch"])]
        handlers = {"tool.fetch": _Recorder("fetch", log, delay=0.05), "tool.render": _Recorder("render", log)}
        kernel = self._kernel(entries, handlers)

        kernel.run_goal(self.GOAL)

        self.assertEqual(log, ["start:fetch", "end:fetch", "start:render", "end:render"])

    def test_independent_steps_run_in_parallel(self) -> None:
        log: list[str] = []
        entries = [_tool("tool.fetch", "Fetch the quarterly report figures."),
                   _tool("tool.audit", "Audit the quarterly report figures.")]
        handlers = {
            "tool.fetch": _Recorder("fetch", log, delay=0.1),
            "tool.audit": _Recorder("audit", log, delay=0.1),
        }
        kernel = self._kernel(entries, handlers)

        started = time.perf_counter()
        result = kernel.run_goal(self.GOAL)
        elapsed = time.perf_counter() - started

        self.assertEqual(result.status, "completed", result.detail)
        # Both steps sleep 0.1s; run serially that is >=0.2s.
        self.assertLess(elapsed, 0.19, f"steps did not overlap (took {elapsed:.3f}s)")
        self.assertCountEqual(log[:2], ["start:fetch", "start:audit"])

    def test_parallelism_can_be_switched_off(self) -> None:
        log: list[str] = []
        entries = [_tool("tool.fetch", "Fetch the quarterly report figures."),
                   _tool("tool.audit", "Audit the quarterly report figures.")]
        handlers = {
            "tool.fetch": _Recorder("fetch", log, delay=0.02),
            "tool.audit": _Recorder("audit", log, delay=0.02),
        }
        kernel = self._kernel(entries, handlers, max_parallel_steps=1)

        kernel.run_goal(self.GOAL)

        self.assertEqual(log, ["start:fetch", "end:fetch", "start:audit", "end:audit"])

    def test_dry_run_completes_plan_without_invoking_parallel_handlers(self) -> None:
        log: list[str] = []
        entries = [
            _tool("tool.publish", "Publish the quarterly report.", side_effect="external"),
            _tool("tool.notify", "Notify subscribers.", side_effect="irreversible"),
        ]
        handlers = {
            "tool.publish": _Recorder("publish", log),
            "tool.notify": _Recorder("notify", log),
        }
        kernel = self._kernel(
            entries,
            handlers,
            policy_context=PolicyContext(dry_run=True),
        )

        result = kernel.run_goal(self.GOAL)

        self.assertEqual(result.status, "completed", result.detail)
        self.assertEqual(log, [])
        self.assertEqual([item.status for item in result.tool_results], ["dry_run", "dry_run"])
        plan = kernel.get_state(result.task_id)["plan"]
        self.assertEqual([step["status"] for step in plan["steps"]], ["completed", "completed"])

    def test_write_step_pauses_planned_execution_before_handler(self) -> None:
        log: list[str] = []
        kernel = self._kernel(
            [_tool("tool.persist", "Write and persist the quarterly report.", side_effect="write")],
            {"tool.persist": _Recorder("persist", log)},
        )

        result = kernel.run_goal(self.GOAL)

        self.assertEqual(result.status, "escalated")
        self.assertEqual(log, [])
        self.assertIn("paused for human approval", result.detail)
        self.assertIn("side_effect=write", result.detail)
        self.assertIsNotNone(kernel.pending_request(result.task_id))

    def test_an_invalid_plan_stops_before_anything_runs(self) -> None:
        log: list[str] = []
        handler = _Recorder("fetch", log)

        class _BadPlanner(RuleBasedPlanner):
            def plan(self, goal, resources, *, context=None):
                return Plan(goal=goal, steps=(_step("s1", resource_id="tool.not.selected"),))

        kernel = self._kernel(
            [_tool("tool.fetch", "Fetch the quarterly report figures.")],
            {"tool.fetch": handler},
            planner=_BadPlanner(),
        )

        result = kernel.run_goal(self.GOAL)

        self.assertEqual(result.status, "failed")
        self.assertIn("did not validate", result.detail)
        self.assertIn("unknown resource", result.detail)
        self.assertEqual(handler.calls, 0, "validation must run before any side effect")

    def test_an_empty_plan_is_reported_clearly(self) -> None:
        class _EmptyPlanner(RuleBasedPlanner):
            def plan(self, goal, resources, *, context=None):
                return Plan(goal=goal)

        kernel = self._kernel(
            [_tool("tool.fetch", "Fetch the quarterly report figures.")],
            {"tool.fetch": _Recorder("fetch", [])},
            planner=_EmptyPlanner(),
        )

        result = kernel.run_goal(self.GOAL)

        self.assertEqual(result.status, "failed")
        self.assertIn("no steps", result.detail)

    def test_recovery_fallback_is_preferred_over_re_planning(self) -> None:
        # Both tools share a capability and an input schema, so the stand-in
        # rescues the step and the plan never needs revising.
        log: list[str] = []
        entries = [
            _tool("tool.fetch", "Fetch the quarterly report figures."),
            _tool("tool.mirror", "Fetch the quarterly report figures from the mirror."),
        ]
        handlers = {
            "tool.fetch": _Recorder("fetch", log, error=ValueError("source is empty")),
            "tool.mirror": _Recorder("mirror", log),
        }
        kernel = self._kernel(
            entries,
            handlers,
            max_parallel_steps=1,
            recovery=RecoveryManager(escalate_when_exhausted=False, sleep=lambda _: None),
        )

        result = kernel.run_goal(self.GOAL)

        events = [r.payload.get("event") for r in kernel.audit_log.records if r.kind == "plan"]
        actions = [r.payload.get("action") for r in kernel.audit_log.records if r.kind == "recover"]
        self.assertEqual(result.status, "completed", result.detail)
        self.assertIn("fallback_selected", actions)
        self.assertNotIn("replanned", events)

    def test_an_unrecoverable_step_triggers_a_replan_that_drops_its_dependents(self) -> None:
        log: list[str] = []
        # Disjoint capabilities, so recovery has no stand-in to fall back to
        # and the failure reaches the planner.
        entries = [
            _tool("tool.fetch", "Fetch the quarterly report figures.", capabilities=["fetching"]),
            _tool(
                "tool.render",
                "Render the quarterly report document.",
                capabilities=["rendering"],
                dependencies=["tool.fetch"],
            ),
        ]
        handlers = {
            "tool.fetch": _Recorder("fetch", log, error=ValueError("source is empty")),
            "tool.render": _Recorder("render", log),
        }
        kernel = self._kernel(
            entries,
            handlers,
            recovery=RecoveryManager(escalate_when_exhausted=False, sleep=lambda _: None),
        )

        result = kernel.run_goal(self.GOAL)

        events = [r.payload.get("event") for r in kernel.audit_log.records if r.kind == "plan"]
        recovery_actions = [
            r.payload.get("action") for r in kernel.audit_log.records if r.kind == "recover"
        ]
        self.assertIn("replanned", events)
        self.assertIn("rollback", recovery_actions)
        self.assertIn(
            "rollback",
            [event.kind for event in kernel.state_store.events(result.task_id)],
        )
        # Dropping the failed step removes the step that depended on it, so
        # nothing runs on stale inputs.
        self.assertEqual(handlers["tool.render"].calls, 0)
        self.assertEqual(result.status, "failed")

    def test_work_done_before_an_unrecoverable_failure_is_kept_not_repeated(self) -> None:
        log: list[str] = []
        entries = [
            _tool("tool.fetch", "Fetch the quarterly report figures.", capabilities=["fetching"]),
            _tool("tool.audit", "Audit the quarterly report figures.", capabilities=["auditing"]),
        ]
        handlers = {
            "tool.fetch": _Recorder("fetch", log, error=ValueError("source is empty")),
            "tool.audit": _Recorder("audit", log),
        }
        kernel = self._kernel(
            entries,
            handlers,
            max_parallel_steps=1,
            recovery=RecoveryManager(escalate_when_exhausted=False, sleep=lambda _: None),
        )

        result = kernel.run_goal(self.GOAL)

        # The independent step keeps its completed status across the re-plan,
        # so it is not repeated; the task still fails, because the work the
        # goal asked for was not achieved.
        self.assertEqual(handlers["tool.audit"].calls, 1)
        self.assertEqual(
            [item.tool_id for item in result.tool_results],
            ["tool.audit"],
            "rollback must discard the failed attempt but preserve its completed sibling",
        )
        self.assertEqual(result.status, "failed")
        self.assertIn("re-planning found no usable alternative", result.detail)

    def test_a_plan_step_can_pause_for_approval_and_resume(self) -> None:
        log: list[str] = []
        entries = [_tool("tool.publish", "Publish the quarterly report to the feed.")]
        handler = _Recorder("publish", log)
        kernel = self._kernel(
            entries,
            {"tool.publish": handler},
            hitl=PendingHitlBroker(HitlPolicy(always_confirm_resources=("tool.publish",))),
        )

        paused = kernel.run_goal(self.GOAL)

        self.assertTrue(paused.paused, paused.detail)
        self.assertEqual(handler.calls, 0)

        resumed = kernel.resume(paused.task_id, HitlResponse(kind="approve", responder="alice"))

        self.assertEqual(resumed.status, "completed", resumed.detail)
        self.assertEqual(handler.calls, 1)

    def test_completed_steps_are_not_re_run_after_a_pause(self) -> None:
        log: list[str] = []
        entries = [
            _tool("tool.fetch", "Fetch the quarterly report figures."),
            _tool("tool.publish", "Publish the quarterly report to the feed.",
                  dependencies=["tool.fetch"]),
        ]
        handlers = {"tool.fetch": _Recorder("fetch", log), "tool.publish": _Recorder("publish", log)}
        kernel = self._kernel(
            entries,
            handlers,
            hitl=PendingHitlBroker(HitlPolicy(always_confirm_resources=("tool.publish",))),
        )

        paused = kernel.run_goal(self.GOAL)
        self.assertTrue(paused.paused, paused.detail)
        self.assertEqual(handlers["tool.fetch"].calls, 1)

        kernel.resume(paused.task_id, HitlResponse(kind="approve"))

        self.assertEqual(handlers["tool.fetch"].calls, 1, "a completed step must not run twice")
        self.assertEqual(handlers["tool.publish"].calls, 1)

    def test_plan_steps_still_pass_the_policy_gate(self) -> None:
        log: list[str] = []
        entries = [_tool("tool.fetch", "Fetch the quarterly report figures.",
                         required_permissions=["reports.read"])]
        handler = _Recorder("fetch", log)
        kernel = self._kernel(entries, {"tool.fetch": handler})

        result = kernel.run_goal(self.GOAL)

        # The gate rejects it at activation, so it is never in the plan's
        # resource set and validation reports the gap up front.
        self.assertEqual(result.status, "failed")
        self.assertEqual(handler.calls, 0)

    def test_the_audit_chain_survives_parallel_steps(self) -> None:
        log: list[str] = []
        entries = [
            _tool("tool.fetch", "Fetch the quarterly report figures."),
            _tool("tool.audit", "Audit the quarterly report figures."),
            _tool("tool.review", "Review the quarterly report figures."),
        ]
        handlers = {
            "tool.fetch": _Recorder("fetch", log, delay=0.01),
            "tool.audit": _Recorder("audit", log, delay=0.01),
            "tool.review": _Recorder("review", log, delay=0.01),
        }
        kernel = self._kernel(entries, handlers)

        result = kernel.run_goal(self.GOAL)

        self.assertEqual(result.status, "completed", result.detail)
        self.assertEqual(kernel.audit_log.verify(), [], "concurrent appends broke the hash chain")
        seqs = [event.seq for event in kernel.state_store.events(result.task_id)]
        self.assertEqual(seqs, sorted(set(seqs)), "state event sequence numbers collided")


if __name__ == "__main__":
    unittest.main()
