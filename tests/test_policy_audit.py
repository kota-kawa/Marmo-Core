from __future__ import annotations

from pathlib import Path
import json
import subprocess
import sys
import tempfile
import unittest

from marmo_core import AuditLog, PolicyContext, PolicyGateway, ResourceDefinition, load_registry
from marmo_core.audit import AuditRecord


ROOT = Path(__file__).resolve().parents[1]
SAMPLES = ROOT / "examples" / "resources"


class PolicyGatewayTests(unittest.TestCase):
    def setUp(self) -> None:
        self.registry = load_registry([SAMPLES])
        self.gateway = PolicyGateway()

    def test_allows_resource_when_required_permissions_are_granted(self) -> None:
        resource = self.registry.get("tool.files.read-text")
        context = PolicyContext(granted_permissions=("fs.read",))

        decision = self.gateway.evaluate(resource, context, gate="activation")

        self.assertTrue(decision.allowed)
        self.assertEqual(decision.verdict, "allow")
        self.assertEqual(decision.missing_permissions, ())

    def test_denies_resource_when_required_permission_is_missing(self) -> None:
        resource = self.registry.get("tool.files.read-text")

        decision = self.gateway.evaluate(resource, PolicyContext(), gate="activation")

        self.assertTrue(decision.denied)
        self.assertEqual(decision.missing_permissions, ("fs.read",))
        self.assertIn("missing required permissions", decision.reason)

    def test_escalates_external_side_effect_without_human_approval(self) -> None:
        resource = self.registry.get("tool.shell.run-command")
        context = PolicyContext(granted_permissions=("shell.exec",))

        decision = self.gateway.evaluate(resource, context, gate="execution")

        self.assertTrue(decision.escalated)
        self.assertIn("requires human approval", decision.reason)

    def test_escalates_write_side_effect_by_default(self) -> None:
        resource = ResourceDefinition.from_mapping(
            {
                **self.registry.get("tool.files.read-text").to_dict(include_extras=True),
                "side_effect": "write",
            }
        )
        context = PolicyContext(granted_permissions=("fs.read",))

        decision = self.gateway.evaluate(resource, context, gate="execution")

        self.assertTrue(decision.escalated)
        self.assertIn("side_effect write requires human approval", decision.reason)

    def test_write_escalation_can_be_explicitly_overridden(self) -> None:
        resource = ResourceDefinition.from_mapping(
            {
                **self.registry.get("tool.files.read-text").to_dict(include_extras=True),
                "side_effect": "write",
            }
        )
        context = PolicyContext(
            granted_permissions=("fs.read",),
            escalate_side_effects=("external", "irreversible"),
        )

        decision = self.gateway.evaluate(resource, context, gate="execution")

        self.assertTrue(decision.allowed)
        self.assertIn("side_effect write is allowed", decision.reason)

    def test_human_approval_allows_escalation_class_side_effect(self) -> None:
        resource = self.registry.get("tool.shell.run-command")
        context = PolicyContext(granted_permissions=("shell.exec",), human_approved=True)

        decision = self.gateway.evaluate(resource, context, gate="execution")

        self.assertTrue(decision.allowed)
        self.assertIn("human-approved", decision.reason)

    def test_dry_run_does_not_escalate_when_no_handler_can_run(self) -> None:
        resource = self.registry.get("tool.shell.run-command")
        context = PolicyContext(granted_permissions=("shell.exec",), dry_run=True)

        decision = self.gateway.evaluate(resource, context, gate="execution")

        self.assertTrue(decision.allowed)
        self.assertTrue(decision.dry_run)
        self.assertIn("would require human approval outside dry_run", decision.reason)

    def test_max_cost_denies_expensive_resources(self) -> None:
        resource = self.registry.get("agent.security.reviewer")
        context = PolicyContext(max_cost=0.01)

        decision = self.gateway.evaluate(resource, context)

        self.assertTrue(decision.denied)
        self.assertIn("exceeds max_cost", decision.reason)


class AuditLogTests(unittest.TestCase):
    def test_hash_chain_and_secret_masking(self) -> None:
        audit_log = AuditLog()
        first = audit_log.append("policy", {"api_key": "abc", "nested": {"token": "def"}, "safe": True})
        second = audit_log.append("activate", {"resource_id": "tool.files.read-text"})

        self.assertEqual(first.payload["api_key"], "[REDACTED]")
        self.assertEqual(first.payload["nested"]["token"], "[REDACTED]")
        self.assertEqual(second.prev_hash, first.hash)
        self.assertEqual(audit_log.verify(), [])

    def test_hash_chain_detects_tampering(self) -> None:
        audit_log = AuditLog()
        record = audit_log.append("policy", {"verdict": "allow"})
        tampered = record.to_dict()
        tampered["payload"] = {"verdict": "deny"}

        issues = AuditLog([AuditRecord.from_dict(tampered)]).verify()

        self.assertTrue(any("invalid hash" in issue for issue in issues))

    def test_jsonl_append_preserves_hash_chain(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "audit.jsonl"

            AuditLog.append_jsonl(path, "policy", {"password": "secret"})
            AuditLog.append_jsonl(path, "policy", {"verdict": "allow"})
            loaded = AuditLog.from_jsonl(path)

        self.assertEqual(len(loaded.records), 2)
        self.assertEqual(loaded.verify(), [])
        self.assertEqual(loaded.records[0].payload["password"], "[REDACTED]")


class PolicyCliTests(unittest.TestCase):
    def run_cli(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, "-m", "marmo_core.cli", *args],
            cwd=ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )

    def test_policy_check_allows_with_permission(self) -> None:
        result = self.run_cli(
            "policy-check",
            "tool.files.read-text",
            "examples/resources",
            "--granted-permission",
            "fs.read",
            "--format",
            "json",
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["decision"]["verdict"], "allow")

    def test_policy_check_returns_nonzero_for_denial(self) -> None:
        result = self.run_cli("policy-check", "tool.files.read-text", "examples/resources")

        self.assertEqual(result.returncode, 1)
        self.assertIn("deny:", result.stdout)

    def test_policy_check_writes_audit_log(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "audit.jsonl"
            result = self.run_cli(
                "policy-check",
                "tool.files.read-text",
                "examples/resources",
                "--granted-permission",
                "fs.read",
                "--audit-log",
                str(path),
                "--format",
                "json",
            )
            loaded = AuditLog.from_jsonl(path)

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(len(loaded.records), 1)
        self.assertEqual(loaded.records[0].kind, "policy")


if __name__ == "__main__":
    unittest.main()
