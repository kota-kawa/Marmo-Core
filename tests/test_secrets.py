from __future__ import annotations

from pathlib import Path
import json
import os
import tempfile
import unittest
from unittest.mock import patch

from marmo_core import (
    BoundTool,
    EnvironmentSecretResolver,
    JsonFileStateStore,
    Kernel,
    MappingSecretResolver,
    MockLLMProvider,
    PolicyContext,
    PolicyRejectedError,
    ResourceDefinition,
    ResourceRegistry,
    SecretRef,
    SecretResolutionError,
    ToolCall,
    ToolRuntime,
)


SECRET_VALUE = "correct-horse-battery-staple"


def _definition() -> ResourceDefinition:
    return ResourceDefinition.from_mapping(
        {
            "id": "tool.test.authenticate",
            "kind": "tool",
            "name": "Authenticate",
            "version": "1.0.0",
            "description": "Use a referenced credential without exposing it.",
            "capabilities": ["authentication"],
            "input_summary": "credential reference",
            "output_summary": "authentication status",
            "required_permissions": [],
            "cost_estimate": 0.0,
            "latency_class": "fast",
            "side_effect": "none",
            "trust_level": "core",
            "ref": "tool://test/authenticate",
            "tags": ["authentication"],
            "input_schema": {
                "type": "object",
                "required": ["token"],
                "properties": {"token": {"type": "string"}},
            },
        }
    )


def _bound(handler) -> BoundTool:
    definition = _definition()
    return BoundTool(
        definition=definition,
        input_schema=dict(definition.extras["input_schema"]),
        output_schema={},
        handler=handler,
    )


class SecretResolverTests(unittest.TestCase):
    def test_mapping_resolver_materializes_only_for_the_handler(self) -> None:
        seen: list[str] = []
        runtime = ToolRuntime(
            secret_resolver=MappingSecretResolver({"service-token": SECRET_VALUE})
        )

        result = runtime.execute(
            _bound(lambda token: seen.append(token) or {"echo": f"used {token}"}),
            {"token": SecretRef("service-token")},
            PolicyContext(),
        )

        self.assertEqual(seen, [SECRET_VALUE])
        self.assertEqual(result.arguments, {"token": {"$secret": "service-token"}})
        self.assertEqual(result.output, {"echo": "used [SECRET_REF:service-token]"})
        self.assertNotIn(SECRET_VALUE, json.dumps(result.to_dict()))

    def test_json_marker_is_supported_and_missing_resolver_is_educational(self) -> None:
        with self.assertRaises(SecretResolutionError) as raised:
            ToolRuntime().execute(
                _bound(lambda token: token),
                {"token": {"$secret": "missing-token"}},
                PolicyContext(),
            )

        self.assertIn("configure Kernel(secret_resolver=...)", str(raised.exception))
        self.assertNotIn(SECRET_VALUE, str(raised.exception))

    def test_plaintext_credential_is_rejected_before_handler_execution(self) -> None:
        calls: list[str] = []
        with self.assertRaises(SecretResolutionError) as raised:
            ToolRuntime().execute(
                _bound(lambda token: calls.append(token)),
                {"token": SECRET_VALUE},
                PolicyContext(),
            )

        self.assertEqual(calls, [])
        self.assertIn("replace each value with SecretRef", str(raised.exception))
        self.assertNotIn(SECRET_VALUE, str(raised.exception))

    def test_environment_resolver_supports_a_prefix(self) -> None:
        with patch.dict(os.environ, {"MARMO_SERVICE_TOKEN": SECRET_VALUE}, clear=False):
            resolver = EnvironmentSecretResolver(prefix="MARMO_")
            self.assertEqual(resolver.resolve(SecretRef("SERVICE_TOKEN")), SECRET_VALUE)

    def test_policy_denial_happens_before_secret_resolution(self) -> None:
        definition = ResourceDefinition.from_mapping(
            {**_definition().to_dict(include_extras=False), "required_permissions": ["auth.use"],
             "input_schema": _definition().extras["input_schema"]}
        )
        calls: list[str] = []
        tool = BoundTool(
            definition=definition,
            input_schema=dict(definition.extras["input_schema"]),
            output_schema={},
            handler=lambda token: token,
        )

        class RecordingResolver(MappingSecretResolver):
            def resolve(self, reference):
                calls.append(reference.name)
                return super().resolve(reference)

        runtime = ToolRuntime(
            secret_resolver=RecordingResolver({"service-token": SECRET_VALUE})
        )
        with self.assertRaises(PolicyRejectedError):
            runtime.execute(tool, {"token": SecretRef("service-token")}, PolicyContext())
        self.assertEqual(calls, [])

    def test_exception_text_cannot_reflect_the_resolved_value(self) -> None:
        runtime = ToolRuntime(
            secret_resolver=MappingSecretResolver({"service-token": SECRET_VALUE})
        )

        def fail(token):
            raise RuntimeError(f"backend rejected {token}")

        result = runtime.execute(
            _bound(fail),
            {"token": SecretRef("service-token")},
            PolicyContext(),
        )
        self.assertEqual(result.status, "error")
        self.assertNotIn(SECRET_VALUE, result.error)
        self.assertIn("[SECRET_REF:service-token]", result.error)

    def test_resolved_value_still_passes_argument_safety_inspection(self) -> None:
        calls: list[str] = []
        runtime = ToolRuntime(
            secret_resolver=MappingSecretResolver(
                {"service-token": "https://blocked.example/credential"}
            )
        )

        with self.assertRaises(PolicyRejectedError) as raised:
            runtime.execute(
                _bound(lambda token: calls.append(token)),
                {"token": SecretRef("service-token")},
                PolicyContext(blocked_external_hosts=("blocked.example",)),
            )

        self.assertEqual(calls, [])
        self.assertIn(
            "external_host.blocked",
            {finding["code"] for finding in raised.exception.decision.risk_findings},
        )


class SecretKernelTests(unittest.TestCase):
    def test_state_audit_and_llm_never_receive_plaintext(self) -> None:
        definition = _definition()
        registry = ResourceRegistry()
        registry.add(definition)
        llm = MockLLMProvider(
            tool_arguments={definition.metadata.id: {"token": SecretRef("service-token")}}
        )
        seen: list[str] = []

        with tempfile.TemporaryDirectory() as directory:
            state_store = JsonFileStateStore(directory)
            kernel = Kernel(
                registry,
                llm,
                tool_implementations={
                    definition.metadata.id: lambda token: seen.append(token) or {"token": token}
                },
                state_store=state_store,
                secret_resolver=MappingSecretResolver({"service-token": SECRET_VALUE}),
            )

            result = kernel.run_goal("authenticate with the configured service token")

            self.assertEqual(result.status, "completed", result.detail)
            self.assertEqual(seen, [SECRET_VALUE])
            state_text = "\n".join(
                path.read_text(encoding="utf-8")
                for path in Path(directory).rglob("*")
                if path.is_file()
            )
            audit_text = json.dumps([record.to_dict() for record in kernel.audit_log.records])
            llm_text = json.dumps(llm.requests)

        self.assertNotIn(SECRET_VALUE, state_text)
        self.assertNotIn(SECRET_VALUE, audit_text)
        self.assertNotIn(SECRET_VALUE, llm_text)
        self.assertIn('"$secret": "service-token"', state_text)
        self.assertIn("[SECRET_REF:service-token]", llm_text)

    def test_plaintext_from_model_is_redacted_in_audit_and_not_persisted(self) -> None:
        definition = _definition()
        registry = ResourceRegistry()
        registry.add(definition)
        llm = MockLLMProvider(
            tool_arguments={definition.metadata.id: {"token": SECRET_VALUE}}
        )
        with tempfile.TemporaryDirectory() as directory:
            kernel = Kernel(
                registry,
                llm,
                tool_implementations={definition.metadata.id: lambda token: token},
                state_store=JsonFileStateStore(directory),
            )

            result = kernel.run_goal("authenticate")
            state_text = "\n".join(
                path.read_text(encoding="utf-8")
                for path in Path(directory).rglob("*")
                if path.is_file()
            )
            audit_text = json.dumps([record.to_dict() for record in kernel.audit_log.records])

        self.assertEqual(result.status, "failed")
        self.assertIn("SecretRef", result.detail)
        self.assertNotIn(SECRET_VALUE, state_text)
        self.assertNotIn(SECRET_VALUE, audit_text)

    def test_tool_call_serialization_never_uses_dataclass_repr(self) -> None:
        call = ToolCall("call-1", "tool.test.authenticate", {"token": SecretRef("service-token")})
        self.assertEqual(
            call.to_dict()["arguments"],
            {"token": {"$secret": "service-token"}},
        )

    def test_long_term_state_keeps_a_reference_and_rejects_plaintext(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            store = JsonFileStateStore(directory)
            store.remember("session", "token", SecretRef("service-token"))
            self.assertEqual(
                store.recall("session", "token"),
                {"$secret": "service-token"},
            )
            with self.assertRaises(SecretResolutionError):
                store.remember("session", "password", SECRET_VALUE)

            persisted = "\n".join(
                path.read_text(encoding="utf-8")
                for path in Path(directory).rglob("*")
                if path.is_file()
            )
        self.assertNotIn(SECRET_VALUE, persisted)


if __name__ == "__main__":
    unittest.main()
