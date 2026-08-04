from __future__ import annotations

from dataclasses import replace as dataclass_replace
from pathlib import Path
import json
import subprocess
import sys
import unittest

from marmo_core import (
    BoundTool,
    HitlResponse,
    Kernel,
    LLMResponse,
    MockLLMProvider,
    MappingSecretResolver,
    PendingHitlBroker,
    PolicyContext,
    PolicyGateway,
    PolicyRejectedError,
    ResourceDefinition,
    ResourceRegistry,
    RuleBasedPlanner,
    SecretRef,
    ToolRuntime,
)


ROOT = Path(__file__).resolve().parents[1]


def _tool_definition(**overrides) -> ResourceDefinition:
    data = {
        "id": "tool.test.shell",
        "kind": "tool",
        "name": "Safety Test Shell",
        "version": "1.0.0",
        "description": "Run a shell command for safety policy tests.",
        "capabilities": ["shell command"],
        "input_summary": "command",
        "output_summary": "result",
        "required_permissions": ["shell.exec"],
        "cost_estimate": 0.0,
        "latency_class": "fast",
        "side_effect": "none",
        "trust_level": "core",
        "ref": "tool://test/shell",
        "tags": ["shell"],
        "input_schema": {
            "type": "object",
            "required": ["cmd"],
            "properties": {"cmd": {"type": "string"}},
        },
    }
    data.update(overrides)
    return ResourceDefinition.from_mapping(data)


def _bound_tool(definition: ResourceDefinition, handler) -> BoundTool:
    return BoundTool(
        definition=definition,
        input_schema=dict(definition.extras.get("input_schema", {})),
        output_schema={},
        handler=handler,
    )


class SafetyPolicyTests(unittest.TestCase):
    def setUp(self) -> None:
        self.gateway = PolicyGateway()
        self.shell = _tool_definition()
        self.context = PolicyContext(granted_permissions=("shell.exec",))

    def evaluate(self, arguments, context: PolicyContext | None = None):
        return self.gateway.evaluate(
            self.shell,
            context or self.context,
            gate="execution",
            arguments=arguments,
        )

    def test_root_recursive_delete_is_denied_even_with_blanket_approval(self) -> None:
        decision = self.evaluate(
            {"cmd": "rm -rf /"},
            PolicyContext(granted_permissions=("shell.exec",), human_approved=True),
        )

        self.assertTrue(decision.denied)
        self.assertEqual(decision.risk_findings[0]["code"], "shell.root_delete")

    def test_recursive_delete_requires_exact_operation_approval(self) -> None:
        decision = self.evaluate({"cmd": "rm -rf /tmp/build"})

        self.assertTrue(decision.escalated)
        self.assertTrue(decision.approval_token.startswith("operation:"))

        approved = dataclass_replace(self.context, approved_operations=(decision.approval_token,))
        allowed = self.evaluate({"cmd": "rm -rf /tmp/build"}, approved)
        changed = self.evaluate({"cmd": "rm -rf /tmp/other"}, approved)

        self.assertTrue(allowed.allowed)
        self.assertTrue(changed.escalated)
        self.assertNotEqual(changed.approval_token, decision.approval_token)

    def test_ordinary_shell_command_does_not_trigger_destructive_rule(self) -> None:
        decision = self.evaluate(
            {
                "cmd": "python3 -m unittest discover -s tests",
                "description": "documentation may mention rm -rf / without executing it",
            }
        )

        self.assertTrue(decision.allowed)
        self.assertEqual(decision.risk_findings, ())

    def test_database_tool_detects_destructive_sql_but_not_scoped_delete(self) -> None:
        resource = _tool_definition(
            required_permissions=["db.write"],
            capabilities=["sqlite database"],
            tags=["database"],
        )
        context = PolicyContext(granted_permissions=("db.write",))

        destructive = self.gateway.evaluate(
            resource,
            context,
            gate="execution",
            arguments={"cmd": "DROP TABLE users"},
        )
        scoped = self.gateway.evaluate(
            resource,
            context,
            gate="execution",
            arguments={"cmd": "DELETE FROM users WHERE id = 42"},
        )

        self.assertTrue(destructive.escalated)
        self.assertEqual(destructive.risk_findings[0]["code"], "database.destructive_statement")
        self.assertTrue(scoped.allowed)

    def test_external_host_blocklist_and_allowlist_are_enforced(self) -> None:
        resource = _tool_definition(
            required_permissions=[],
            capabilities=["http request"],
            tags=["http"],
        )
        blocked = self.gateway.evaluate(
            resource,
            PolicyContext(blocked_external_hosts=("blocked.example",)),
            gate="execution",
            arguments={"cmd": "GET https://api.blocked.example/data"},
        )
        outside = self.gateway.evaluate(
            resource,
            PolicyContext(allowed_external_hosts=("trusted.example",)),
            gate="execution",
            arguments={"cmd": "GET https://other.example/data"},
        )
        allowed = self.gateway.evaluate(
            resource,
            PolicyContext(allowed_external_hosts=("trusted.example",)),
            gate="execution",
            arguments={"cmd": "GET https://api.trusted.example/data"},
        )

        self.assertTrue(blocked.denied)
        self.assertTrue(outside.denied)
        self.assertTrue(allowed.allowed)

    def test_sensitive_external_input_needs_argument_scoped_approval(self) -> None:
        resource = _tool_definition(side_effect="external")
        arguments = {"cmd": "POST https://api.example/upload", "api_key": "do-not-log-this-secret"}
        context = PolicyContext(granted_permissions=("shell.exec",), human_approved=True)

        decision = self.gateway.evaluate(resource, context, gate="execution", arguments=arguments)

        self.assertTrue(decision.escalated)
        self.assertIn("data_exfiltration.sensitive_input", {item["code"] for item in decision.risk_findings})
        self.assertNotIn("do-not-log-this-secret", json.dumps(decision.to_dict()))

        approved = dataclass_replace(context, approved_operations=(decision.approval_token,))
        allowed = self.gateway.evaluate(resource, approved, gate="execution", arguments=arguments)
        self.assertTrue(allowed.allowed)

    def test_dry_run_reports_escalation_rule_without_pausing_or_running(self) -> None:
        calls: list[str] = []
        tool = _bound_tool(self.shell, lambda cmd: calls.append(cmd))

        result = ToolRuntime().execute(
            tool,
            {"cmd": "rm -rf /tmp/build"},
            PolicyContext(granted_permissions=("shell.exec",), dry_run=True),
        )

        self.assertEqual(result.status, "dry_run")
        self.assertEqual(calls, [])
        self.assertEqual(result.safety_findings[0]["code"], "shell.recursive_delete")

    def test_dry_run_still_denies_a_non_approvable_rule(self) -> None:
        with self.assertRaises(PolicyRejectedError) as raised:
            ToolRuntime().execute(
                _bound_tool(self.shell, lambda cmd: None),
                {"cmd": "rm -rf /"},
                PolicyContext(granted_permissions=("shell.exec",), dry_run=True),
            )

        self.assertTrue(raised.exception.decision.denied)


class SafetyKernelTests(unittest.TestCase):
    def _kernel(self, definition, handler, arguments, **kwargs) -> Kernel:
        registry = ResourceRegistry()
        registry.add(definition)
        return Kernel(
            registry,
            kwargs.pop("llm", MockLLMProvider(tool_arguments={definition.metadata.id: arguments})),
            tool_implementations={definition.metadata.id: handler},
            policy_context=kwargs.pop("policy_context", PolicyContext(granted_permissions=("shell.exec",))),
            hitl=kwargs.pop("hitl", PendingHitlBroker()),
            **kwargs,
        )

    def test_kernel_pauses_then_executes_only_the_reviewed_arguments(self) -> None:
        calls: list[str] = []
        kernel = self._kernel(
            self.shell_definition(),
            lambda cmd: calls.append(cmd) or {"ok": True},
            {"cmd": "rm -rf /tmp/build"},
        )

        paused = kernel.run_goal("run the safety test shell command")

        self.assertEqual(paused.status, "escalated")
        self.assertEqual(calls, [])
        request = kernel.pending_request(paused.task_id)
        self.assertIsNotNone(request)
        self.assertEqual(request.decision["risk_findings"][0]["code"], "shell.recursive_delete")

        completed = kernel.resume(
            paused.task_id,
            HitlResponse(kind="approve", request_id=request.request_id, responder="reviewer"),
        )

        self.assertEqual(completed.status, "completed", completed.detail)
        self.assertEqual(calls, ["rm -rf /tmp/build"])
        self.assertTrue(
            any(item.startswith("operation:") for item in kernel.get_state(paused.task_id)["operation_approvals"])
        )

    def test_kernel_denies_catastrophic_command_without_invoking_handler(self) -> None:
        calls: list[str] = []
        kernel = self._kernel(
            self.shell_definition(),
            lambda cmd: calls.append(cmd),
            {"cmd": "rm -rf /"},
        )

        result = kernel.run_goal("run the safety test shell command")

        self.assertEqual(result.status, "denied")
        self.assertEqual(calls, [])
        policy = [record for record in kernel.audit_log.records if record.kind == "policy"]
        self.assertTrue(any(record.payload.get("risk_findings") for record in policy))

    def test_sensitive_values_are_redacted_in_the_hitl_request(self) -> None:
        definition = self.shell_definition(side_effect="external")
        kernel = self._kernel(
            definition,
            lambda **arguments: arguments,
            {"cmd": "POST https://api.example/upload", "api_key": SecretRef("upload-key")},
            policy_context=PolicyContext(granted_permissions=("shell.exec",), human_approved=True),
            secret_resolver=MappingSecretResolver({"upload-key": "do-not-display-this-secret"}),
        )

        result = kernel.run_goal("run the safety test shell command")
        request = kernel.pending_request(result.task_id)

        self.assertEqual(result.status, "escalated")
        self.assertEqual(request.arguments["api_key"], "[REDACTED]")
        self.assertNotIn("do-not-display-this-secret", json.dumps(request.to_dict()))

    def test_planner_uses_the_same_execution_safety_gate(self) -> None:
        calls: list[str] = []
        definition = self.shell_definition(
            input_schema={
                "type": "object",
                "required": ["cmd"],
                "properties": {"cmd": {"type": "string", "default": "git push --force origin main"}},
            }
        )
        kernel = self._kernel(
            definition,
            lambda cmd: calls.append(cmd),
            {},
            planner=RuleBasedPlanner(),
            llm=MockLLMProvider(script=[LLMResponse(content="done")]),
        )

        result = kernel.run_goal("run the safety test shell command")

        self.assertEqual(result.status, "escalated")
        self.assertEqual(calls, [])
        self.assertIn("forced Git push", kernel.pending_request(result.task_id).impact)

    @staticmethod
    def shell_definition(**overrides) -> ResourceDefinition:
        return _tool_definition(**overrides)


class SafetyCliTests(unittest.TestCase):
    def test_policy_check_inspects_execution_arguments(self) -> None:
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "marmo_core.cli",
                "policy-check",
                "tool.shell.run-command",
                "examples/resources",
                "--gate",
                "execution",
                "--granted-permission",
                "shell.exec",
                "--human-approved",
                "--arguments",
                '{"cmd": "rm -rf /tmp/build"}',
                "--format",
                "json",
            ],
            cwd=ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )

        self.assertEqual(result.returncode, 1, result.stderr or result.stdout)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["decision"]["verdict"], "escalate")
        self.assertEqual(payload["decision"]["risk_findings"][0]["code"], "shell.recursive_delete")


if __name__ == "__main__":
    unittest.main()
