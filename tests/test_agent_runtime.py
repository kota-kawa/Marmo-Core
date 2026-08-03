from __future__ import annotations

import time
import unittest

from marmo_core import (
    AgentResponse,
    AgentRuntime,
    BoundAgent,
    Kernel,
    HitlResponse,
    LLMResponse,
    MockLLMProvider,
    PolicyContext,
    PolicyRejectedError,
    RecoveryManager,
    ResourceActivator,
    ResourceDefinition,
    ResourceRegistry,
    RuleBasedPlanner,
    RetryPolicy,
    ToolCall,
    ToolInputError,
    ToolRuntime,
)


def _agent_definition(**overrides) -> ResourceDefinition:
    data = {
        "id": "agent.test.researcher",
        "kind": "agent",
        "name": "Researcher",
        "version": "1.0.0",
        "description": "Delegate a small research question to a specialist",
        "capabilities": ["research", "summarize"],
        "input_summary": "a question",
        "output_summary": "a concise answer",
        "required_permissions": ["research.read"],
        "cost_estimate": 0.25,
        "latency_class": "fast",
        "side_effect": "read",
        "trust_level": "core",
        "ref": "agent://test/researcher",
        "tags": ["research"],
        "agent_card": {
            "delegation_interface": "tool_wrap",
            "callable_name": "delegate_research",
            "input_schema": {
                "type": "object",
                "required": ["question"],
                "properties": {"question": {"type": "string"}},
                "additionalProperties": False,
            },
            "output_schema": {"type": "object"},
        },
    }
    data.update(overrides)
    return ResourceDefinition.from_mapping(data)


def _bound(handler, **overrides) -> BoundAgent:
    definition = _agent_definition(**overrides)
    activation = ResourceActivator(
        agent_implementations={definition.metadata.id: handler}
    ).activate(
        definition,
        PolicyContext(
            granted_permissions=("research.read",),
            allowed_trust_levels=("core", "verified", "community", "untrusted"),
        ),
    )
    assert activation.ok
    assert isinstance(activation.activated, BoundAgent)
    return activation.activated


class AgentRuntimeTests(unittest.TestCase):
    def test_runs_through_tool_runtime_and_reports_actual_cost(self) -> None:
        agent = _bound(lambda question: AgentResponse({"answer": question.upper()}, cost=0.1))
        result = AgentRuntime(ToolRuntime()).execute(
            agent,
            {"question": "why"},
            PolicyContext(granted_permissions=("research.read",)),
        )

        self.assertEqual(result.status, "success")
        self.assertEqual(result.output, {"answer": "WHY"})
        self.assertEqual(result.cost, 0.1)
        self.assertEqual(result.delegated_permissions, ("research.read",))

    def test_dry_run_never_invokes_agent(self) -> None:
        calls: list[str] = []
        agent = _bound(lambda question: calls.append(question))
        result = AgentRuntime(ToolRuntime()).execute(
            agent,
            {"question": "why"},
            PolicyContext(granted_permissions=("research.read",), dry_run=True),
        )

        self.assertEqual(result.status, "dry_run")
        self.assertEqual(result.cost, 0.0)
        self.assertEqual(calls, [])

    def test_timeout_is_an_agent_result(self) -> None:
        def slow(question: str) -> str:
            time.sleep(0.05)
            return question

        result = AgentRuntime(ToolRuntime(timeout_seconds=0.01)).execute(
            _bound(slow),
            {"question": "why"},
            PolicyContext(granted_permissions=("research.read",)),
        )
        self.assertEqual(result.status, "timeout")
        self.assertIn("0.01s", result.error)

    def test_delegated_permissions_cannot_expand(self) -> None:
        with self.assertRaisesRegex(ToolInputError, "subset"):
            AgentRuntime(ToolRuntime()).execute(
                _bound(lambda question: question),
                {"question": "why"},
                PolicyContext(granted_permissions=("research.read",)),
                delegated_permissions=("research.read", "admin.write"),
            )

    def test_depth_and_total_cost_are_bounded_before_execution(self) -> None:
        calls: list[str] = []
        agent = _bound(lambda question: calls.append(question))
        runtime = AgentRuntime(ToolRuntime(), max_depth=1, max_total_cost=0.3)
        with self.assertRaisesRegex(ToolInputError, "max_depth"):
            runtime.execute(
                agent,
                {"question": "depth"},
                PolicyContext(granted_permissions=("research.read",)),
                depth=2,
            )
        with self.assertRaisesRegex(ToolInputError, "max_total_cost"):
            runtime.execute(
                agent,
                {"question": "cost"},
                PolicyContext(granted_permissions=("research.read",)),
                cumulative_cost=0.1,
            )
        self.assertEqual(calls, [])

    def test_untrusted_agent_is_denied_by_default_policy(self) -> None:
        agent = _bound(lambda question: question, trust_level="untrusted")
        with self.assertRaises(PolicyRejectedError):
            AgentRuntime(ToolRuntime()).execute(
                agent,
                {"question": "why"},
                PolicyContext(granted_permissions=("research.read",)),
            )

    def test_structured_task_is_rejected_as_v3(self) -> None:
        definition = _agent_definition(
            agent_card={"delegation_interface": "structured_task"}
        )
        activation = ResourceActivator(
            agent_implementations={definition.metadata.id: lambda **_: None}
        ).activate(definition, PolicyContext(granted_permissions=("research.read",)))
        self.assertFalse(activation.ok)
        self.assertIn("v3", activation.error)


class AgentKernelTests(unittest.TestCase):
    def _kernel(self, handler, *, llm=None, **kwargs) -> Kernel:
        registry = ResourceRegistry()
        registry.add(_agent_definition())
        llm = llm or MockLLMProvider(
            tool_arguments={"delegate_research": {"question": "why"}}
        )
        return Kernel(
            registry,
            llm,
            agent_implementations={"agent.test.researcher": handler},
            policy_context=PolicyContext(granted_permissions=("research.read",)),
            **kwargs,
        )

    def test_model_driven_delegation_is_saved_and_audited(self) -> None:
        kernel = self._kernel(lambda question: {"answer": f"because: {question}"})
        result = kernel.run_goal("Research why")

        self.assertEqual(result.status, "completed", result.detail)
        self.assertEqual(len(result.agent_results), 1)
        self.assertEqual(result.agent_results[0].output, {"answer": "because: why"})
        self.assertEqual(result.tool_results, ())
        self.assertIn("because: why", result.output)
        self.assertIn("delegate", {record.kind for record in kernel.audit_log.records})
        state = kernel.get_state(result.task_id)
        self.assertEqual(state["step_results"][0]["agent_id"], "agent.test.researcher")

    def test_transient_failure_retries_and_records_each_result(self) -> None:
        calls = 0

        def flaky(question: str) -> dict[str, str]:
            nonlocal calls
            calls += 1
            if calls == 1:
                raise ConnectionError("temporary")
            return {"answer": question}

        kernel = self._kernel(
            flaky,
            recovery=RecoveryManager(
                retry_policy=RetryPolicy(max_attempts=2, initial_backoff_seconds=0),
                sleep=lambda _: None,
            ),
        )
        result = kernel.run_goal("Research why")

        self.assertEqual(result.status, "completed", result.detail)
        self.assertEqual([item.status for item in result.agent_results], ["error", "success"])
        self.assertEqual(calls, 2)

    def test_timeout_is_persisted_and_sent_to_recovery(self) -> None:
        def slow(question: str) -> str:
            time.sleep(0.05)
            return question

        kernel = self._kernel(
            slow,
            timeout_seconds=0.01,
            recovery=RecoveryManager(
                retry_policy=RetryPolicy(max_attempts=1),
                escalate_when_exhausted=False,
                sleep=lambda _: None,
            ),
        )

        result = kernel.run_goal("Research slowly")

        self.assertEqual(result.status, "failed")
        self.assertEqual(len(result.agent_results), 1)
        self.assertEqual(result.agent_results[0].status, "timeout")
        recovery_records = [
            record.payload for record in kernel.audit_log.records if record.kind == "recover"
        ]
        self.assertEqual(recovery_records[-1]["failure"]["stage"], "delegation")
        self.assertEqual(recovery_records[-1]["failure"]["kind"], "timeout")

    def test_failed_agent_falls_back_to_a_retrieved_compatible_agent(self) -> None:
        primary = _agent_definition(
            description="Primary specialist for the requested research question",
        )
        standby = _agent_definition(
            id="agent.test.researcher-standby",
            name="Standby Researcher",
            description="Backup specialist for research and summarization",
            ref="agent://test/researcher-standby",
            agent_card={
                "delegation_interface": "tool_wrap",
                "callable_name": "delegate_research_standby",
                "input_schema": primary.extras["agent_card"]["input_schema"],
                "output_schema": {"type": "object"},
            },
        )
        calls: list[str] = []

        def broken(question: str) -> dict[str, str]:
            raise ValueError(f"primary unavailable for {question}")

        def backup(question: str) -> dict[str, str]:
            calls.append(question)
            return {"answer": f"backup: {question}"}

        registry = ResourceRegistry()
        registry.extend((primary, standby))
        llm = MockLLMProvider(
            script=(
                LLMResponse(
                    content="",
                    tool_calls=(
                        ToolCall(
                            id="a1",
                            name="delegate_research",
                            arguments={"question": "why"},
                        ),
                    ),
                ),
                LLMResponse(content="done"),
            )
        )
        kernel = Kernel(
            registry,
            llm,
            agent_implementations={
                primary.metadata.id: broken,
                standby.metadata.id: backup,
            },
            policy_context=PolicyContext(granted_permissions=("research.read",)),
            recovery=RecoveryManager(
                retry_policy=RetryPolicy(max_attempts=1),
                escalate_when_exhausted=False,
                sleep=lambda _: None,
            ),
            set_limits={"agent": 1},
        )

        result = kernel.run_goal("Use the primary specialist to research why")

        self.assertEqual(result.status, "completed", result.detail)
        self.assertEqual(calls, ["why"])
        self.assertEqual(
            [item.agent_id for item in result.agent_results],
            ["agent.test.researcher", "agent.test.researcher-standby"],
        )
        fallbacks = [
            record.payload
            for record in kernel.audit_log.records
            if record.kind == "recover"
            and record.payload.get("action") == "fallback_selected"
        ]
        self.assertEqual(fallbacks[-1]["to"], "agent.test.researcher-standby@1.0.0")

    def test_rule_based_plan_executes_agent_step(self) -> None:
        kernel = self._kernel(
            lambda question: {"answer": question},
            planner=RuleBasedPlanner(
                step_arguments={"agent.test.researcher": {"question": "planned"}}
            ),
        )

        result = kernel.run_goal("Research with a plan")

        self.assertEqual(result.status, "completed", result.detail)
        self.assertEqual(len(result.agent_results), 1)
        self.assertEqual(result.agent_results[0].output, {"answer": "planned"})

    def test_agent_result_survives_state_reconstruction(self) -> None:
        calls = 0

        def handler(question: str) -> dict[str, str]:
            nonlocal calls
            calls += 1
            return {"answer": question}

        scripted = MockLLMProvider(
            script=(
                LLMResponse(
                    content="",
                    tool_calls=(
                        ToolCall(id="a1", name="delegate_research", arguments={"question": "why"}),
                    ),
                ),
                LLMResponse(content="done"),
            )
        )
        kernel = self._kernel(handler, llm=scripted)
        result = kernel.run_goal("Research why")
        rebuilt = kernel._result_from_state(kernel.state_store.load(result.task_id))

        self.assertEqual(result.status, "completed")
        self.assertEqual(calls, 1)
        self.assertEqual(len(rebuilt.agent_results), 1)
        self.assertEqual(rebuilt.agent_results[0].status, "success")

    def test_resume_does_not_repeat_completed_delegation(self) -> None:
        agent_calls = 0
        tool_calls = 0

        def delegate(question: str) -> dict[str, str]:
            nonlocal agent_calls
            agent_calls += 1
            return {"answer": question}

        def save(text: str) -> dict[str, str]:
            nonlocal tool_calls
            tool_calls += 1
            return {"saved": text}

        tool_data = {
            "id": "tool.test.save",
            "kind": "tool",
            "name": "Save research",
            "version": "1.0.0",
            "description": "Save the delegated research answer",
            "capabilities": ["research", "save"],
            "input_summary": "answer text",
            "output_summary": "save status",
            "required_permissions": [],
            "cost_estimate": 0.0,
            "latency_class": "fast",
            "side_effect": "write",
            "trust_level": "core",
            "ref": "tool://test/save",
            "tags": ["research"],
            "input_schema": {
                "type": "object",
                "required": ["text"],
                "properties": {"text": {"type": "string"}},
            },
        }
        registry = ResourceRegistry()
        registry.add(_agent_definition())
        registry.add(ResourceDefinition.from_mapping(tool_data))
        llm = MockLLMProvider(
            script=(
                LLMResponse(
                    content="",
                    tool_calls=(
                        ToolCall(id="a1", name="delegate_research", arguments={"question": "why"}),
                    ),
                ),
                LLMResponse(
                    content="",
                    tool_calls=(
                        ToolCall(id="t1", name="tool.test.save", arguments={"text": "because"}),
                    ),
                ),
                LLMResponse(content="done"),
            )
        )
        kernel = Kernel(
            registry,
            llm,
            agent_implementations={"agent.test.researcher": delegate},
            tool_implementations={"tool.test.save": save},
            policy_context=PolicyContext(
                granted_permissions=("research.read",),
                allowed_side_effects=("none", "read", "write"),
                escalate_side_effects=(),
            ),
        )

        paused = kernel.run_goal("Research why and save the answer")
        self.assertEqual(paused.status, "escalated")
        findings = paused.hitl_request["decision"]["risk_findings"]
        self.assertEqual(findings[0]["code"], "trust_boundary.untrusted_side_effect")
        self.assertEqual(agent_calls, 1)
        self.assertEqual(tool_calls, 0)

        completed = kernel.resume(
            paused.task_id,
            HitlResponse(kind="approve", responder="reviewer"),
        )
        self.assertEqual(completed.status, "completed", completed.detail)
        self.assertEqual(agent_calls, 1)
        self.assertEqual(tool_calls, 1)
        self.assertEqual(len(completed.agent_results), 1)


if __name__ == "__main__":
    unittest.main()
