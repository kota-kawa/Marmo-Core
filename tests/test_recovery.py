from __future__ import annotations

import random
import unittest

from marmo_core import (
    AutoApproveHitlBroker,
    CircuitBreaker,
    Failure,
    HitlResponse,
    Kernel,
    LLMResponse,
    MockLLMProvider,
    PolicyContext,
    RecoveryManager,
    ResourceDefinition,
    ResourceRegistry,
    RetryPolicy,
    ToolCall,
    ToolResult,
    compensation_for,
)


def _base_fields(resource_id: str, kind: str, **overrides) -> dict:
    data = {
        "id": resource_id,
        "kind": kind,
        "name": resource_id,
        "version": "1.0.0",
        "description": f"{kind} resource for recovery tests: fetch a report from the feed",
        "capabilities": ["reporting", "fetch"],
        "input_summary": "report name",
        "output_summary": "report body",
        "required_permissions": [],
        "cost_estimate": 0.0,
        "latency_class": "fast",
        "side_effect": "none",
        "trust_level": "core",
        "ref": f"{kind}://test/{resource_id}",
        "tags": ["reporting", "feed"],
    }
    data.update(overrides)
    return data


def _tool(resource_id: str = "tool.test.fetch", **overrides) -> dict:
    data = _base_fields(resource_id, "tool", **overrides)
    data.setdefault(
        "input_schema",
        {
            "type": "object",
            "required": ["name"],
            "properties": {"name": {"type": "string"}},
        },
    )
    return data


def _registry(*entries: dict) -> ResourceRegistry:
    registry = ResourceRegistry()
    for entry in entries:
        registry.add(ResourceDefinition.from_mapping(entry))
    return registry


def _result(status: str, error: str | None = None) -> ToolResult:
    return ToolResult(
        tool_id="tool.test.fetch",
        tool_version="1.0.0",
        status=status,
        arguments={"name": "q3"},
        error=error,
    )


class _Flaky:
    """Fails the first ``failures`` calls, then succeeds."""

    def __init__(self, failures: int, error: Exception | None = None) -> None:
        self.failures = failures
        self.calls = 0
        self.error = error or ConnectionError("feed unreachable")

    def __call__(self, name: str) -> dict:
        self.calls += 1
        if self.calls <= self.failures:
            raise self.error
        return {"report": name}


class ClassificationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.manager = RecoveryManager()
        self.metadata = ResourceDefinition.from_mapping(_tool()).metadata

    def test_timeout_is_its_own_class(self) -> None:
        failure = self.manager.classify_tool_result(_result("timeout", "took too long"), self.metadata)

        self.assertEqual(failure.kind, "timeout")
        self.assertEqual(failure.resource, "tool.test.fetch@1.0.0")

    def test_network_errors_are_transient(self) -> None:
        failure = self.manager.classify_tool_result(
            _result("error", "ConnectionError: feed unreachable"), self.metadata
        )

        self.assertEqual(failure.kind, "transient")

    def test_other_errors_are_permanent(self) -> None:
        failure = self.manager.classify_tool_result(
            _result("error", "ValueError: bad report name"), self.metadata
        )

        self.assertEqual(failure.kind, "permanent")

    def test_transient_error_list_is_configurable(self) -> None:
        manager = RecoveryManager(transient_errors=("RateLimited",))

        self.assertEqual(
            manager.classify_tool_result(_result("error", "RateLimited: slow down"), self.metadata).kind,
            "transient",
        )
        self.assertEqual(
            manager.classify_tool_result(_result("error", "ConnectionError: x"), self.metadata).kind,
            "permanent",
        )

    def test_unknown_failure_kind_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            Failure(kind="weird", message="x")


class RetryPolicyTests(unittest.TestCase):
    def test_backoff_grows_exponentially_and_is_capped(self) -> None:
        policy = RetryPolicy(initial_backoff_seconds=1.0, multiplier=2.0, max_backoff_seconds=5.0, jitter=0.0)
        rng = random.Random(0)

        delays = [policy.backoff_for(attempt, rng) for attempt in range(5)]

        self.assertEqual(delays, [1.0, 2.0, 4.0, 5.0, 5.0])

    def test_jitter_stays_within_the_configured_band(self) -> None:
        policy = RetryPolicy(initial_backoff_seconds=1.0, jitter=0.1)
        rng = random.Random(1)

        for _ in range(50):
            delay = policy.backoff_for(0, rng)
            self.assertGreaterEqual(delay, 0.9)
            self.assertLessEqual(delay, 1.1)

    def test_only_listed_kinds_are_retryable(self) -> None:
        policy = RetryPolicy(max_attempts=3)

        self.assertTrue(policy.allows(Failure(kind="transient", message="x"), attempts=0))
        self.assertTrue(policy.allows(Failure(kind="timeout", message="x"), attempts=1))
        self.assertFalse(policy.allows(Failure(kind="transient", message="x"), attempts=2))
        self.assertFalse(policy.allows(Failure(kind="permanent", message="x"), attempts=0))

    def test_invalid_policies_are_rejected(self) -> None:
        with self.assertRaises(ValueError):
            RetryPolicy(max_attempts=0)
        with self.assertRaises(ValueError):
            RetryPolicy(jitter=2.0)
        with self.assertRaises(ValueError):
            RetryPolicy(retry_kinds=("nonsense",))


class CircuitBreakerTests(unittest.TestCase):
    def test_opens_after_consecutive_failures_and_success_resets(self) -> None:
        breaker = CircuitBreaker(failure_threshold=2)

        breaker.record_failure("a")
        self.assertFalse(breaker.is_open("a"))
        breaker.record_failure("a")
        self.assertTrue(breaker.is_open("a"))

        breaker.record_success("a")
        self.assertFalse(breaker.is_open("a"))

    def test_counters_are_per_resource(self) -> None:
        breaker = CircuitBreaker(failure_threshold=2)
        breaker.record_failure("a")
        breaker.record_failure("b")

        self.assertFalse(breaker.is_open("a"))
        self.assertFalse(breaker.is_open("b"))


class DecisionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.manager = RecoveryManager(sleep=lambda _: None)

    def test_transient_failure_retries_with_backoff(self) -> None:
        decision = self.manager.decide(Failure(kind="transient", message="x", resource="r"), attempts=0)

        self.assertEqual(decision.action, "retry")
        self.assertGreater(decision.backoff_seconds, 0.0)

    def test_exhausted_retries_prefer_a_fallback(self) -> None:
        decision = self.manager.decide(
            Failure(kind="transient", message="x", resource="r"), attempts=5, alternatives=("tool.other",)
        )

        self.assertEqual(decision.action, "fallback")
        self.assertEqual(decision.alternative, "tool.other")

    def test_permission_denied_goes_straight_to_a_human(self) -> None:
        decision = self.manager.decide(Failure(kind="permission_denied", message="x", resource="r"))

        self.assertEqual(decision.action, "escalate")

    def test_validation_failure_fails_fast(self) -> None:
        # Identical bad arguments cannot succeed on a retry or on any stand-in.
        decision = self.manager.decide(
            Failure(kind="validation", message="x", resource="r"), alternatives=("tool.other",)
        )

        self.assertEqual(decision.action, "fail")

    def test_open_circuit_overrides_everything(self) -> None:
        manager = RecoveryManager(circuit_breaker=CircuitBreaker(failure_threshold=1))
        manager.circuit_breaker.record_failure("r")

        decision = manager.decide(
            Failure(kind="transient", message="x", resource="r"), alternatives=("tool.other",)
        )

        self.assertEqual(decision.action, "fail")
        self.assertIn("circuit breaker open", decision.reason)

    def test_escalation_can_be_turned_off(self) -> None:
        manager = RecoveryManager(escalate_when_exhausted=False)

        decision = manager.decide(Failure(kind="permanent", message="x", resource="r"))

        self.assertEqual(decision.action, "fail")


class KernelRecoveryTests(unittest.TestCase):
    def _kernel(self, registry: ResourceRegistry, handler, **kwargs) -> Kernel:
        kwargs.setdefault("tool_implementations", {"tool.test.fetch": handler})
        kwargs.setdefault("policy_context", PolicyContext())
        kwargs.setdefault(
            "recovery",
            RecoveryManager(retry_policy=RetryPolicy(initial_backoff_seconds=0.0), sleep=lambda _: None),
        )
        llm = kwargs.pop("llm", None) or MockLLMProvider(tool_arguments={"tool.test.fetch": {"name": "q3"}})
        return Kernel(registry, llm, **kwargs)

    def test_transient_failure_is_retried_until_it_succeeds(self) -> None:
        handler = _Flaky(failures=2)
        kernel = self._kernel(_registry(_tool()), handler)

        result = kernel.run_goal("fetch the q3 report from the feed")

        self.assertEqual(result.status, "completed", result.detail)
        self.assertEqual(handler.calls, 3)
        # Every attempt is recorded, not just the one that worked.
        self.assertEqual([r.status for r in result.tool_results], ["error", "error", "success"])
        actions = [
            record.payload.get("action")
            for record in kernel.audit_log.records
            if record.kind == "recover"
        ]
        self.assertEqual(actions.count("retry"), 2)

    def test_dry_run_never_enters_retry_or_fallback(self) -> None:
        handler = _Flaky(failures=99)
        kernel = self._kernel(
            _registry(_tool()),
            handler,
            policy_context=PolicyContext(dry_run=True),
        )

        result = kernel.run_goal("fetch the q3 report from the feed")

        self.assertEqual(result.status, "completed", result.detail)
        self.assertEqual(handler.calls, 0)
        self.assertEqual([item.status for item in result.tool_results], ["dry_run"])
        self.assertFalse(any(record.kind == "recover" for record in kernel.audit_log.records))

    def test_retries_stop_at_the_attempt_limit(self) -> None:
        handler = _Flaky(failures=99)
        kernel = self._kernel(
            _registry(_tool()),
            handler,
            recovery=RecoveryManager(
                retry_policy=RetryPolicy(max_attempts=2, initial_backoff_seconds=0.0),
                escalate_when_exhausted=False,
                sleep=lambda _: None,
            ),
        )

        result = kernel.run_goal("fetch the q3 report from the feed")

        self.assertEqual(result.status, "failed")
        self.assertEqual(handler.calls, 2)
        self.assertIn("transient failure", result.detail)

    def test_permanent_failure_is_not_retried(self) -> None:
        handler = _Flaky(failures=99, error=ValueError("no such report"))
        kernel = self._kernel(
            _registry(_tool()),
            handler,
            recovery=RecoveryManager(escalate_when_exhausted=False, sleep=lambda _: None),
        )

        result = kernel.run_goal("fetch the q3 report from the feed")

        self.assertEqual(result.status, "failed")
        self.assertEqual(handler.calls, 1)

    # The goal wording makes the primary tool win retrieval, so `set_limits`
    # alone decides whether the stand-in is already activated (cheap path) or
    # has to be found by re-searching the registry.
    GOAL = "fetch the q3 report from the primary feed"
    PRIMARY = dict(description="Fetch the q3 report from the primary feed.")
    STANDBY = dict(description="Mirror service serving reporting fetch requests.")

    def _fallback_kernel(self, standby_calls: list[str], *, set_limits: dict) -> Kernel:
        broken = _Flaky(failures=99, error=ValueError("primary feed is gone"))

        def standby(name: str) -> dict:
            standby_calls.append(name)
            return {"report": name, "via": "standby"}

        script = [
            LLMResponse(
                content="",
                tool_calls=(ToolCall(id="c1", name="tool.test.fetch", arguments={"name": "q3"}),),
            ),
            LLMResponse(content="done"),
        ]
        return self._kernel(
            _registry(_tool("tool.test.fetch", **self.PRIMARY), _tool("tool.test.fetch-standby", **self.STANDBY)),
            broken,
            llm=MockLLMProvider(script=script),
            tool_implementations={"tool.test.fetch": broken, "tool.test.fetch-standby": standby},
            recovery=RecoveryManager(escalate_when_exhausted=False, sleep=lambda _: None),
            set_limits=set_limits,
        )

    def _assert_fell_back(self, kernel: Kernel, result, standby_calls: list[str]) -> None:
        self.assertEqual(result.status, "completed", result.detail)
        self.assertEqual(standby_calls, ["q3"])
        self.assertEqual(result.tool_results[-1].tool_id, "tool.test.fetch-standby")
        selected = [
            record.payload
            for record in kernel.audit_log.records
            if record.kind == "recover" and record.payload.get("action") == "fallback_selected"
        ]
        self.assertEqual(len(selected), 1)
        self.assertEqual(selected[0]["to"], "tool.test.fetch-standby@1.0.0")

    def test_fallback_uses_an_already_activated_tool(self) -> None:
        standby_calls: list[str] = []
        kernel = self._fallback_kernel(standby_calls, set_limits={"tool": 2})

        self._assert_fell_back(kernel, kernel.run_goal(self.GOAL), standby_calls)

    def test_fallback_re_searches_the_registry_when_nothing_activated_fits(self) -> None:
        standby_calls: list[str] = []
        # Only the primary is activated, so the stand-in must come from a
        # fresh retrieval and be activated through the gate on the way in.
        kernel = self._fallback_kernel(standby_calls, set_limits={"tool": 1})
        result = kernel.run_goal(self.GOAL)

        self._assert_fell_back(kernel, result, standby_calls)
        activated = kernel.get_state(result.task_id)["activated"]
        self.assertNotIn("tool.test.fetch-standby@1.0.0", activated, "it was not in the original set")

    def test_a_stand_in_that_cannot_take_the_arguments_is_not_used(self) -> None:
        broken = _Flaky(failures=99, error=ValueError("gone"))
        registry = _registry(
            _tool("tool.test.fetch", **self.PRIMARY),
            _tool(
                "tool.test.fetch-other",
                description="Mirror service serving reporting fetch requests.",
                input_schema={
                    "type": "object",
                    "required": ["report_id"],
                    "properties": {"report_id": {"type": "integer"}},
                },
            ),
        )
        kernel = self._kernel(
            registry,
            broken,
            recovery=RecoveryManager(escalate_when_exhausted=False, sleep=lambda _: None),
            set_limits={"tool": 1},
        )

        result = kernel.run_goal(self.GOAL)

        self.assertEqual(result.status, "failed")
        self.assertNotIn("fetch-other", result.detail)

    def test_unrecoverable_failure_escalates_to_a_human(self) -> None:
        handler = _Flaky(failures=99, error=ValueError("no such report"))
        kernel = self._kernel(_registry(_tool()), handler)

        result = kernel.run_goal("fetch the q3 report from the feed")

        self.assertTrue(result.paused, result.detail)
        request = kernel.pending_request(result.task_id)
        self.assertIn("retry or abandon", request.operation)
        self.assertIn("recovery", request.decision)

    def test_approving_a_recovery_escalation_grants_a_fresh_retry_budget(self) -> None:
        handler = _Flaky(failures=1, error=ValueError("transient in disguise"))
        kernel = self._kernel(_registry(_tool()), handler)
        paused = kernel.run_goal("fetch the q3 report from the feed")
        self.assertTrue(paused.paused)

        resumed = kernel.resume(paused.task_id, HitlResponse(kind="approve", responder="alice"))

        self.assertEqual(resumed.status, "completed", resumed.detail)
        self.assertEqual(handler.calls, 2)

    def test_rejecting_a_recovery_escalation_ends_the_task(self) -> None:
        handler = _Flaky(failures=99, error=ValueError("no such report"))
        kernel = self._kernel(_registry(_tool()), handler)
        paused = kernel.run_goal("fetch the q3 report from the feed")

        denied = kernel.resume(paused.task_id, HitlResponse(kind="reject", responder="alice"))

        self.assertEqual(denied.status, "denied")

    def test_circuit_breaker_stops_a_resource_that_always_fails(self) -> None:
        handler = _Flaky(failures=99)
        kernel = self._kernel(
            _registry(_tool()),
            handler,
            hitl=AutoApproveHitlBroker(),
            recovery=RecoveryManager(
                retry_policy=RetryPolicy(max_attempts=2, initial_backoff_seconds=0.0),
                circuit_breaker=CircuitBreaker(failure_threshold=3),
                sleep=lambda _: None,
            ),
        )

        result = kernel.run_goal("fetch the q3 report from the feed")

        # Auto-approval would otherwise retry forever; the breaker ends it.
        self.assertEqual(result.status, "failed")
        self.assertIn("circuit breaker open", result.detail)

    def test_a_checkpoint_is_taken_before_every_tool_call(self) -> None:
        kernel = self._kernel(_registry(_tool()), lambda name: {"report": name})
        result = kernel.run_goal("fetch the q3 report from the feed")

        labels = [checkpoint["label"] for checkpoint in kernel.checkpoints(result.task_id)]

        self.assertTrue(any(label.startswith("before:") for label in labels), labels)


class CompensationTests(unittest.TestCase):
    def test_compensation_target_is_read_from_the_resource(self) -> None:
        declared = ResourceDefinition.from_mapping(_tool(compensated_by="tool.test.undo"))
        plain = ResourceDefinition.from_mapping(_tool())

        self.assertEqual(compensation_for(declared), "tool.test.undo")
        self.assertEqual(compensation_for(plain), "")

    def _saga_registry(self, **publish_overrides) -> ResourceRegistry:
        return _registry(
            _tool(
                "tool.test.publish",
                description="Publish the quarterly report to the external feed.",
                side_effect="external",
                **publish_overrides,
            ),
            _tool(
                "tool.test.retract",
                description="Retract a published quarterly report from the external feed.",
                side_effect="external",
            ),
            _tool(
                "tool.test.notify",
                description="Notify subscribers that the quarterly report is live.",
                side_effect="external",
                capabilities=["notification"],
            ),
        )

    def _saga_kernel(self, registry, published, retracted, notify_error):
        def publish(name: str) -> dict:
            published.append(name)
            return {"published": name}

        def retract(name: str) -> dict:
            retracted.append(name)
            return {"retracted": name}

        def notify(name: str) -> dict:
            raise notify_error

        script = [
            LLMResponse(
                content="",
                tool_calls=(
                    ToolCall(id="c1", name="tool.test.publish", arguments={"name": "q3"}),
                    ToolCall(id="c2", name="tool.test.notify", arguments={"name": "q3"}),
                ),
            ),
            LLMResponse(content="done"),
        ]
        return Kernel(
            registry,
            MockLLMProvider(script=script),
            policy_context=PolicyContext(human_approved=True),
            tool_implementations={
                "tool.test.publish": publish,
                "tool.test.retract": retract,
                "tool.test.notify": notify,
            },
            recovery=RecoveryManager(escalate_when_exhausted=False, sleep=lambda _: None),
            set_limits={"tool": 3},
        )

    def test_a_failed_saga_undoes_the_completed_side_effect(self) -> None:
        published: list[str] = []
        retracted: list[str] = []
        registry = self._saga_registry(compensated_by="tool.test.retract")
        kernel = self._saga_kernel(registry, published, retracted, ValueError("subscriber list is down"))

        result = kernel.run_goal("publish the q3 report and notify subscribers")

        self.assertEqual(result.status, "failed")
        self.assertEqual(published, ["q3"])
        self.assertEqual(retracted, ["q3"], "the completed publish must be rolled back")
        self.assertIn("compensated: tool.test.publish", result.detail)

    def test_a_side_effect_without_a_declared_undo_is_reported_not_hidden(self) -> None:
        published: list[str] = []
        retracted: list[str] = []
        registry = self._saga_registry()
        kernel = self._saga_kernel(registry, published, retracted, ValueError("subscriber list is down"))

        result = kernel.run_goal("publish the q3 report and notify subscribers")

        self.assertEqual(result.status, "failed")
        self.assertEqual(published, ["q3"])
        self.assertEqual(retracted, [])
        self.assertIn("NOT undone: tool.test.publish", result.detail)

    def test_compensation_can_be_switched_off(self) -> None:
        published: list[str] = []
        retracted: list[str] = []
        registry = self._saga_registry(compensated_by="tool.test.retract")
        kernel = self._saga_kernel(registry, published, retracted, ValueError("down"))
        kernel.compensate_on_failure = False

        kernel.run_goal("publish the q3 report and notify subscribers")

        self.assertEqual(retracted, [])

    def test_dry_run_results_are_not_compensated_after_later_validation_failure(self) -> None:
        published: list[str] = []
        retracted: list[str] = []
        notified: list[str] = []
        registry = self._saga_registry(compensated_by="tool.test.retract")

        def publish(name: str) -> dict:
            published.append(name)
            return {"published": name}

        def retract(name: str) -> dict:
            retracted.append(name)
            return {"retracted": name}

        def notify(name: str) -> dict:
            notified.append(name)
            return {"notified": name}

        script = [
            LLMResponse(
                content="",
                tool_calls=(
                    ToolCall(id="c1", name="tool.test.publish", arguments={"name": "q3"}),
                    ToolCall(id="c2", name="tool.test.notify", arguments={}),
                ),
            )
        ]
        kernel = Kernel(
            registry,
            MockLLMProvider(script=script),
            policy_context=PolicyContext(dry_run=True),
            tool_implementations={
                "tool.test.publish": publish,
                "tool.test.retract": retract,
                "tool.test.notify": notify,
            },
            recovery=RecoveryManager(escalate_when_exhausted=False, sleep=lambda _: None),
            set_limits={"tool": 3},
        )

        result = kernel.run_goal("publish the q3 report and notify subscribers")

        self.assertEqual(result.status, "failed")
        self.assertEqual(published, [])
        self.assertEqual(notified, [])
        self.assertEqual(retracted, [])
        self.assertNotIn("compensated:", result.detail)
        self.assertNotIn("NOT undone:", result.detail)

    def test_compensation_still_passes_the_policy_gate(self) -> None:
        published: list[str] = []
        retracted: list[str] = []
        registry = _registry(
            _tool(
                "tool.test.publish",
                description="Publish the quarterly report to the external feed.",
                side_effect="external",
                compensated_by="tool.test.retract",
            ),
            _tool(
                "tool.test.retract",
                description="Retract a published quarterly report from the external feed.",
                side_effect="external",
                required_permissions=["reports.retract"],
            ),
            _tool(
                "tool.test.notify",
                description="Notify subscribers that the quarterly report is live.",
                side_effect="external",
                capabilities=["notification"],
            ),
        )
        kernel = self._saga_kernel(registry, published, retracted, ValueError("down"))

        result = kernel.run_goal("publish the q3 report and notify subscribers")

        # The undo needs a permission the task never held, so it is refused
        # and reported rather than run as a privileged escape hatch.
        self.assertEqual(retracted, [])
        self.assertIn("NOT undone: tool.test.publish", result.detail)


if __name__ == "__main__":
    unittest.main()
