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
    BoundTool,
    Kernel,
    LLMResponse,
    MockLLMProvider,
    PolicyContext,
    PolicyRejectedError,
    ResourceActivator,
    ResourceDefinition,
    ResourceRegistry,
    ToolCall,
    ToolInputError,
    ToolRuntime,
    validate_arguments,
)
from marmo_core.llm import default_arguments


ROOT = Path(__file__).resolve().parents[1]


def _base_fields(resource_id: str, kind: str, **overrides) -> dict:
    data = {
        "id": resource_id,
        "kind": kind,
        "name": resource_id,
        "version": "1.0.0",
        "description": f"{kind} resource for kernel tests: add numbers with a calculator",
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


def _tool_definition(**overrides) -> dict:
    data = _base_fields("tool.test.add", "tool", **overrides)
    data.setdefault(
        "input_schema",
        {
            "type": "object",
            "required": ["a", "b"],
            "properties": {"a": {"type": "number"}, "b": {"type": "number"}},
        },
    )
    return data


def _add(a: float, b: float) -> dict:
    return {"sum": a + b}


def _build_registry(*entries: dict) -> ResourceRegistry:
    registry = ResourceRegistry()
    for entry in entries:
        registry.add(ResourceDefinition.from_mapping(entry))
    return registry


def _kernel(registry: ResourceRegistry, **kwargs) -> Kernel:
    kwargs.setdefault("tool_implementations", {"tool.test.add": _add})
    kwargs.setdefault(
        "policy_context",
        PolicyContext(granted_permissions=("math.add",)),
    )
    llm = kwargs.pop("llm", None) or MockLLMProvider(tool_arguments={"tool.test.add": {"a": 2, "b": 3}})
    return Kernel(registry, llm, **kwargs)


class KernelEndToEndTests(unittest.TestCase):
    def test_full_guarded_loop_completes_and_audits(self) -> None:
        registry = _build_registry(
            _tool_definition(required_permissions=["math.add"]),
            _base_fields(
                "memory.test.style",
                "memory",
                content="Repeat the input numbers next to the result.",
            ),
            _base_fields(
                "skill.test.arithmetic",
                "skill",
                instructions=["Use the calculator tool.", "Never guess arithmetic."],
            ),
        )
        kernel = _kernel(registry)

        result = kernel.run_goal("Add 2 and 3 with the calculator")

        self.assertEqual(result.status, "completed", result.detail)
        self.assertEqual(len(result.tool_results), 1)
        self.assertEqual(result.tool_results[0].output, {"sum": 5})
        self.assertIn('"sum": 5', result.output)
        state = kernel.get_state(result.task_id)
        self.assertEqual(state["status"], "completed")
        self.assertEqual(state["step_results"][0]["tool_id"], "tool.test.add")
        self.assertIn("tool.test.add@1.0.0", state["activated"])

        kinds = {record.kind for record in kernel.audit_log.records}
        self.assertLessEqual({"retrieve", "policy", "activate", "compile", "llm", "execute", "task"}, kinds)
        self.assertEqual(kernel.audit_log.verify(), [])
        trace_ids = {record.trace_id for record in kernel.audit_log.records}
        self.assertEqual(len(trace_ids), 1)

    def test_escalating_side_effect_pauses_the_task(self) -> None:
        registry = _build_registry(_tool_definition(side_effect="external"))
        kernel = _kernel(registry)

        result = kernel.run_goal("Add 2 and 3 with the calculator")

        self.assertEqual(result.status, "escalated")
        self.assertIn("human approval", result.detail)
        self.assertIn("human_approved", result.detail)

    def test_write_side_effect_pauses_before_invoking_the_handler(self) -> None:
        calls: list[tuple[float, float]] = []

        def write_add(a: float, b: float) -> dict:
            calls.append((a, b))
            return {"sum": a + b}

        registry = _build_registry(_tool_definition(side_effect="write"))
        kernel = _kernel(registry, tool_implementations={"tool.test.add": write_add})

        result = kernel.run_goal("Add 2 and 3 and write the result")

        self.assertEqual(result.status, "escalated")
        self.assertEqual(calls, [])
        self.assertIn("paused for human approval", result.detail)
        self.assertIn("side_effect=write", result.detail)
        self.assertIsNotNone(kernel.pending_request(result.task_id))

    def test_human_approval_unblocks_escalation(self) -> None:
        registry = _build_registry(_tool_definition(side_effect="external"))
        kernel = _kernel(
            registry,
            policy_context=PolicyContext(granted_permissions=("math.add",), human_approved=True),
        )

        result = kernel.run_goal("Add 2 and 3 with the calculator")

        self.assertEqual(result.status, "completed", result.detail)

    def test_dry_run_completes_external_call_without_invoking_handler_or_hitl(self) -> None:
        calls: list[tuple[float, float]] = []

        def external_add(a: float, b: float) -> dict:
            calls.append((a, b))
            return {"sum": a + b}

        registry = _build_registry(_tool_definition(side_effect="external"))
        kernel = _kernel(
            registry,
            policy_context=PolicyContext(granted_permissions=("math.add",), dry_run=True),
            tool_implementations={"tool.test.add": external_add},
        )

        result = kernel.run_goal("Add 2 and 3 with the external calculator")

        self.assertEqual(result.status, "completed", result.detail)
        self.assertEqual(calls, [])
        self.assertEqual(len(result.tool_results), 1)
        self.assertEqual(result.tool_results[0].status, "dry_run")
        self.assertFalse(result.tool_results[0].executed)
        self.assertFalse(any(record.kind == "hitl" for record in kernel.audit_log.records))
        self.assertEqual(kernel.get_state(result.task_id)["step_results"][0]["status"], "dry_run")
        execute = [record for record in kernel.audit_log.records if record.kind == "execute"]
        self.assertEqual(execute[0].payload["status"], "dry_run")

    def test_denied_resource_is_skipped_with_audit_record(self) -> None:
        registry = _build_registry(_tool_definition(required_permissions=["math.add"]))
        kernel = _kernel(registry, policy_context=PolicyContext())

        result = kernel.run_goal("Add 2 and 3 with the calculator")

        self.assertEqual(result.status, "completed")
        self.assertEqual(result.tool_results, ())
        self.assertEqual(len(result.skipped_resources), 1)
        self.assertIn("missing required permissions", result.skipped_resources[0]["reason"])
        policy_records = [record for record in kernel.audit_log.records if record.kind == "policy"]
        self.assertTrue(any(record.payload["verdict"] == "deny" for record in policy_records))

    def test_unknown_requested_tool_fails_with_educational_detail(self) -> None:
        registry = _build_registry(_tool_definition())
        script = [
            LLMResponse(content="", tool_calls=(ToolCall(id="c1", name="tool.does.not.exist", arguments={}),)),
        ]
        kernel = _kernel(registry, llm=MockLLMProvider(script=script))

        result = kernel.run_goal("Add 2 and 3 with the calculator")

        self.assertEqual(result.status, "failed")
        self.assertIn("not available in the compiled context", result.detail)

    def test_tool_call_budget_is_enforced(self) -> None:
        registry = _build_registry(_tool_definition())
        call = ToolCall(id="c", name="tool.test.add", arguments={"a": 1, "b": 1})
        script = [LLMResponse(content="", tool_calls=(call,)) for _ in range(4)]
        kernel = _kernel(registry, llm=MockLLMProvider(script=script), max_tool_calls=2)

        result = kernel.run_goal("Add numbers forever")

        self.assertEqual(result.status, "failed")
        self.assertIn("max_tool_calls", result.detail)

    def test_submit_and_run_are_separate_and_run_is_idempotent(self) -> None:
        registry = _build_registry(_tool_definition())
        kernel = _kernel(registry)

        task_id = kernel.submit("Add 2 and 3 with the calculator")
        self.assertEqual(kernel.get_state(task_id)["status"], "submitted")
        first = kernel.run(task_id)
        second = kernel.run(task_id)

        self.assertIs(first, second)
        self.assertIs(kernel.resume(task_id), first)


class ResourceActivatorTests(unittest.TestCase):
    def test_memory_content_from_definition(self) -> None:
        definition = ResourceDefinition.from_mapping(
            _base_fields("memory.test.inline", "memory", content="inline body")
        )
        activation = ResourceActivator().activate(definition, PolicyContext())

        self.assertTrue(activation.ok)
        self.assertEqual(activation.activated.content, "inline body")

    def test_memory_content_from_file_ref(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            note = Path(temp_dir) / "note.txt"
            note.write_text("file body", encoding="utf-8")
            definition = ResourceDefinition.from_mapping(
                _base_fields("memory.test.file", "memory", ref=f"file:{note}")
            )
            activation = ResourceActivator().activate(definition, PolicyContext())

        self.assertTrue(activation.ok)
        self.assertEqual(activation.activated.content, "file body")

    def test_tool_binds_python_ref(self) -> None:
        definition = ResourceDefinition.from_mapping(
            _tool_definition(ref="python:json:dumps", input_schema={})
        )
        activation = ResourceActivator().activate(definition, PolicyContext())

        self.assertTrue(activation.ok)
        self.assertEqual(activation.activated.handler(obj=[1, 2]), "[1, 2]")

    def test_tool_without_implementation_reports_next_step(self) -> None:
        definition = ResourceDefinition.from_mapping(_tool_definition())
        activation = ResourceActivator().activate(definition, PolicyContext())

        self.assertFalse(activation.ok)
        self.assertIn("tool_implementations", activation.error)

    def test_agent_binds_registered_implementation(self) -> None:
        definition = ResourceDefinition.from_mapping(_base_fields("agent.test.helper", "agent"))

        def handler() -> dict[str, int]:
            return {"answer": 42}

        activation = ResourceActivator(
            agent_implementations={"agent.test.helper": handler}
        ).activate(definition, PolicyContext())

        self.assertTrue(activation.ok)
        self.assertIs(activation.activated.handler, handler)

    def test_denied_activation_carries_decision(self) -> None:
        definition = ResourceDefinition.from_mapping(_tool_definition(trust_level="untrusted"))
        activation = ResourceActivator().activate(definition, PolicyContext())

        self.assertFalse(activation.ok)
        self.assertEqual(activation.decision.verdict, "deny")


class ToolRuntimeTests(unittest.TestCase):
    def _bound_tool(self, handler, **overrides) -> BoundTool:
        definition = ResourceDefinition.from_mapping(_tool_definition(**overrides))
        return BoundTool(
            definition=definition,
            input_schema=dict(definition.extras.get("input_schema", {})),
            output_schema={},
            handler=handler,
        )

    def test_successful_execution(self) -> None:
        result = ToolRuntime().execute(self._bound_tool(_add), {"a": 1, "b": 2}, PolicyContext())

        self.assertTrue(result.succeeded)
        self.assertEqual(result.output, {"sum": 3})
        self.assertGreaterEqual(result.elapsed_ms, 0.0)

    def test_dry_run_validates_but_never_invokes_any_handler(self) -> None:
        for side_effect in ("none", "read", "write", "external", "irreversible"):
            with self.subTest(side_effect=side_effect):
                calls: list[tuple[float, float]] = []

                def handler(a: float, b: float) -> dict:
                    calls.append((a, b))
                    return {"sum": a + b}

                result = ToolRuntime().execute(
                    self._bound_tool(handler, side_effect=side_effect),
                    {"a": 1, "b": 2},
                    PolicyContext(dry_run=True),
                )

                self.assertEqual(calls, [])
                self.assertEqual(result.status, "dry_run")
                self.assertTrue(result.succeeded)
                self.assertFalse(result.executed)
                self.assertEqual(result.output["executed"], False)
                self.assertEqual(result.output["side_effect"], side_effect)

    def test_dry_run_still_enforces_schema_and_permissions(self) -> None:
        tool = self._bound_tool(_add, required_permissions=["math.add"])
        with self.assertRaises(PolicyRejectedError):
            ToolRuntime().execute(tool, {"a": 1, "b": 2}, PolicyContext(dry_run=True))

        with self.assertRaises(ToolInputError):
            ToolRuntime().execute(
                self._bound_tool(_add), {"a": "one"}, PolicyContext(dry_run=True)
            )

    def test_handler_exception_becomes_error_result(self) -> None:
        def broken(a: float, b: float) -> dict:
            raise RuntimeError("boom")

        result = ToolRuntime().execute(self._bound_tool(broken), {"a": 1, "b": 2}, PolicyContext())

        self.assertEqual(result.status, "error")
        self.assertIn("RuntimeError: boom", result.error)

    def test_timeout_is_reported(self) -> None:
        def slow(a: float, b: float) -> dict:
            time.sleep(0.3)
            return {"sum": a + b}

        result = ToolRuntime(timeout_seconds=0.05).execute(self._bound_tool(slow), {"a": 1, "b": 2}, PolicyContext())

        self.assertEqual(result.status, "timeout")
        self.assertIn("timeout_seconds", result.error)

    def test_invalid_input_raises_educational_error(self) -> None:
        with self.assertRaises(ToolInputError) as ctx:
            ToolRuntime().execute(self._bound_tool(_add), {"a": "one"}, PolicyContext())

        self.assertIn("missing required argument: b", str(ctx.exception))
        self.assertIn("input_schema", str(ctx.exception))

    def test_execution_gate_cannot_be_bypassed(self) -> None:
        tool = self._bound_tool(_add, required_permissions=["math.add"])

        with self.assertRaises(PolicyRejectedError) as ctx:
            ToolRuntime().execute(tool, {"a": 1, "b": 2}, PolicyContext())

        self.assertEqual(ctx.exception.decision.verdict, "deny")


class SchemaValidationTests(unittest.TestCase):
    SCHEMA = {
        "type": "object",
        "required": ["name"],
        "additionalProperties": False,
        "properties": {
            "name": {"type": "string"},
            "level": {"type": "integer", "minimum": 1, "maximum": 3},
            "mode": {"type": "string", "enum": ["fast", "slow"]},
        },
    }

    def test_valid_arguments_pass(self) -> None:
        self.assertEqual(validate_arguments(self.SCHEMA, {"name": "x", "level": 2, "mode": "fast"}), [])

    def test_violations_are_collected(self) -> None:
        issues = validate_arguments(self.SCHEMA, {"level": 9, "mode": "warp", "extra": 1})

        self.assertTrue(any("missing required argument: name" in issue for issue in issues))
        self.assertTrue(any("must be <= 3" in issue for issue in issues))
        self.assertTrue(any("must be one of" in issue for issue in issues))
        self.assertTrue(any("unknown argument: extra" in issue for issue in issues))

    def test_boolean_is_not_a_number(self) -> None:
        schema = {"type": "object", "properties": {"a": {"type": "number"}}}

        self.assertEqual(validate_arguments(schema, {"a": 1.5}), [])
        self.assertTrue(validate_arguments(schema, {"a": True}))


class MockLLMTests(unittest.TestCase):
    def test_default_arguments_come_from_schema(self) -> None:
        schema = {
            "type": "object",
            "required": ["path", "count"],
            "properties": {
                "path": {"type": "string"},
                "count": {"type": "integer", "default": 7},
                "flag": {"type": "boolean", "default": True},
            },
        }

        self.assertEqual(default_arguments(schema), {"path": "", "count": 7, "flag": True})

    def test_scripted_mode_returns_in_order_then_raises(self) -> None:
        provider = MockLLMProvider(script=[LLMResponse(content="one"), LLMResponse(content="two")])

        self.assertEqual(provider.complete([]).content, "one")
        self.assertEqual(provider.complete([]).content, "two")
        with self.assertRaises(ValueError):
            provider.complete([])


class ExampleAndCliTests(unittest.TestCase):
    def test_hello_world_example_runs(self) -> None:
        result = subprocess.run(
            [sys.executable, "examples/hello_world.py"],
            cwd=ROOT,
            env={**os.environ, "PYTHONPATH": str(ROOT)},
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("status: completed", result.stdout)
        self.assertIn("audit hash chain verified.", result.stdout)

    def test_cli_run_executes_python_ref_tool_and_writes_audit_log(self) -> None:
        resource = _tool_definition(
            id="tool.demo.dumps",
            ref="python:json:dumps",
            required_permissions=[],
            input_schema={
                "type": "object",
                "required": ["obj"],
                "properties": {"obj": {"type": "array"}},
            },
            description="Serialize a list to a JSON string for calculator demos.",
        )
        with tempfile.TemporaryDirectory() as temp_dir:
            resource_path = Path(temp_dir) / "demo_tool.json"
            resource_path.write_text(json.dumps(resource), encoding="utf-8")
            audit_path = Path(temp_dir) / "audit.jsonl"
            result = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "marmo_core.cli",
                    "run",
                    "--task",
                    "serialize a list to JSON",
                    str(resource_path),
                    "--tool-args",
                    '{"tool.demo.dumps": {"obj": [1, 2]}}',
                    "--audit-log",
                    str(audit_path),
                ],
                cwd=ROOT,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )
            self.assertEqual(result.returncode, 0, result.stderr or result.stdout)
            self.assertIn("status: completed", result.stdout)
            self.assertIn("tool: tool.demo.dumps status=success", result.stdout)
            lines = [json.loads(line) for line in audit_path.read_text(encoding="utf-8").splitlines() if line]

        kinds = {line["kind"] for line in lines}
        self.assertLessEqual({"retrieve", "policy", "activate", "compile", "llm", "execute", "task"}, kinds)
        for previous, current in zip(lines, lines[1:]):
            self.assertEqual(current["prev_hash"], previous["hash"])

    def test_cli_run_supports_dry_run(self) -> None:
        resource = _tool_definition(
            id="tool.demo.dumps",
            ref="python:json:dumps",
            required_permissions=[],
            side_effect="external",
            input_schema={
                "type": "object",
                "required": ["obj"],
                "properties": {"obj": {"type": "array"}},
            },
            description="Serialize a list through an external service.",
        )
        with tempfile.TemporaryDirectory() as temp_dir:
            resource_path = Path(temp_dir) / "demo_tool.json"
            resource_path.write_text(json.dumps(resource), encoding="utf-8")
            result = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "marmo_core.cli",
                    "run",
                    "--task",
                    "serialize a list to JSON",
                    str(resource_path),
                    "--tool-args",
                    '{"tool.demo.dumps": {"obj": [1, 2]}}',
                    "--dry-run",
                ],
                cwd=ROOT,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )

        self.assertEqual(result.returncode, 0, result.stderr or result.stdout)
        self.assertIn("status: completed", result.stdout)
        self.assertIn("tool: tool.demo.dumps status=dry_run", result.stdout)

    def test_cli_run_escalates_write_side_effect_by_default(self) -> None:
        resource = _tool_definition(
            id="tool.demo.dumps",
            ref="python:json:dumps",
            required_permissions=[],
            side_effect="write",
            input_schema={
                "type": "object",
                "required": ["obj"],
                "properties": {"obj": {"type": "array"}},
            },
            description="Serialize a list and write the result.",
        )
        with tempfile.TemporaryDirectory() as temp_dir:
            resource_path = Path(temp_dir) / "demo_tool.json"
            resource_path.write_text(json.dumps(resource), encoding="utf-8")
            result = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "marmo_core.cli",
                    "run",
                    "--task",
                    "serialize and write a list",
                    str(resource_path),
                    "--tool-args",
                    '{"tool.demo.dumps": {"obj": [1, 2]}}',
                ],
                cwd=ROOT,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )

        self.assertEqual(result.returncode, 1, result.stderr or result.stdout)
        self.assertIn("status: escalated", result.stdout)
        self.assertIn("paused for human approval", result.stdout)
        self.assertIn("side_effect=write", result.stdout)
        self.assertIn("awaiting confirmation:", result.stdout)


if __name__ == "__main__":
    unittest.main()
