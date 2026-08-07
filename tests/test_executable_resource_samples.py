from __future__ import annotations

from contextlib import contextmanager
from email.message import Message
from importlib.util import find_spec
from pathlib import Path
from unittest.mock import patch
import os
import tempfile
import unittest

from marmo_core import AgentRuntime, PolicyContext, ResourceActivator, ToolRuntime, load_registry


ROOT = Path(__file__).resolve().parents[1]
SAMPLE_PATHS = (ROOT / "resources" / "tools", ROOT / "resources" / "agents")


class _Response:
    def __init__(self, body: bytes, status: int = 200, message_id: str = "sample-message") -> None:
        self.body = body
        self.status = status
        self.headers = Message()
        self.headers["Content-Type"] = "application/json; charset=utf-8"
        self.headers["X-Message-Id"] = message_id

    def read(self, amount: int = -1) -> bytes:
        return self.body if amount < 0 else self.body[:amount]

    def __enter__(self) -> "_Response":
        return self

    def __exit__(self, *_: object) -> None:
        return None


@contextmanager
def _working_directory(path: Path):
    previous = Path.cwd()
    os.chdir(path)
    try:
        yield
    finally:
        os.chdir(previous)


class ExecutableToolSampleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.registry = load_registry(SAMPLE_PATHS)
        cls.context = PolicyContext(
            granted_permissions=("fs.read", "fs.write", "net.external", "process.exec", "message.send"),
            human_approved=True,
            available_isolation_levels=("L0", "L1", "L2", "L3"),
        )
        cls.activator = ResourceActivator()
        cls.runtime = ToolRuntime()

    def _bound_tool(self, resource_id: str):
        activation = self.activator.activate(self.registry.get(resource_id), self.context)
        self.assertTrue(activation.ok, activation.error)
        return activation.activated

    def test_all_ten_tool_refs_resolve_without_manual_bindings(self) -> None:
        tools = self.registry.list(kinds=("tool",))

        self.assertEqual(len(tools), 10)
        for definition in tools:
            with self.subTest(resource=definition.metadata.id):
                activation = self.activator.activate(definition, self.context)
                self.assertTrue(activation.ok, activation.error)
                self.assertTrue(definition.metadata.ref.startswith("python:marmo_core.sample_resources.tools:"))

    def test_filesystem_tools_execute_inside_the_workspace(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir, _working_directory(Path(temp_dir)):
            written = self.runtime.execute(
                self._bound_tool("tool.marmo.samples.write-text"),
                {"path": "notes/input.txt", "content": "alpha\nbeta alpha\n"},
                self.context,
            )
            read = self.runtime.execute(
                self._bound_tool("tool.marmo.samples.read-text"),
                {"path": "notes/input.txt", "max_bytes": 1024},
                self.context,
            )
            listed = self.runtime.execute(
                self._bound_tool("tool.marmo.samples.list-files"),
                {"directory": ".", "pattern": "**/*.txt"},
                self.context,
            )
            searched = self.runtime.execute(
                self._bound_tool("tool.marmo.samples.search-text"),
                {"query": "alpha", "root": ".", "limit": 10},
                self.context,
            )
            archived = self.runtime.execute(
                self._bound_tool("tool.marmo.samples.create-archive"),
                {"paths": ["notes"], "output": "artifacts/notes.zip"},
                self.context,
            )

            self.assertEqual(written.status, "success")
            self.assertEqual(read.output["content"], "alpha\nbeta alpha\n")
            self.assertEqual(listed.output["files"], ["notes/input.txt"])
            self.assertEqual(len(searched.output["matches"]), 2)
            self.assertEqual(archived.output["file_count"], 1)
            self.assertTrue(Path("artifacts/notes.zip").is_file())

    def test_file_tool_rejects_a_path_outside_the_workspace(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir, _working_directory(Path(temp_dir)):
            result = self.runtime.execute(
                self._bound_tool("tool.marmo.samples.read-text"),
                {"path": "../outside.txt"},
                self.context,
            )

        self.assertEqual(result.status, "error")
        self.assertIn("escapes the current workspace", result.error)

    def test_json_validation_and_test_runner_execute(self) -> None:
        validation = self.runtime.execute(
            self._bound_tool("tool.marmo.samples.validate-json"),
            {
                "value": {"name": "Marmo", "count": 3},
                "schema": {
                    "type": "object",
                    "required": ["name", "count"],
                    "properties": {"name": {"type": "string"}, "count": {"type": "integer"}},
                    "additionalProperties": False,
                },
            },
            self.context,
        )
        tests = self.runtime.execute(
            self._bound_tool("tool.marmo.samples.run-tests"),
            {"suite": "tests/test_formatting.py", "timeout_seconds": 30},
            self.context,
        )

        self.assertEqual(validation.status, "success")
        self.assertTrue(validation.output["valid"])
        self.assertEqual(tests.status, "success")
        self.assertEqual(tests.output["exit_code"], 0, tests.output["output"])

    @unittest.skipUnless(find_spec("ruff") is not None, "format-code requires Ruff (install with .[dev])")
    def test_formatter_executes_on_an_explicit_file(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir, _working_directory(Path(temp_dir)):
            source = Path("sample.py")
            source.write_text("values={'a':1,'b':2}\n", encoding="utf-8")
            result = self.runtime.execute(
                self._bound_tool("tool.marmo.samples.format-code"),
                {"paths": ["sample.py"]},
                self.context,
            )

            self.assertEqual(result.status, "success")
            self.assertEqual(result.output["exit_code"], 0, result.output["diagnostics"])
            self.assertEqual(result.output["changed"], ["sample.py"])
            self.assertIn('"a": 1', source.read_text(encoding="utf-8"))

    def test_network_tools_execute_against_configured_https_boundaries(self) -> None:
        http_response = _Response(b'{"ok": true}')
        notification_response = _Response(b"accepted", status=202)
        with patch("marmo_core.sample_resources.tools.urlopen", return_value=http_response) as get_url:
            fetched = self.runtime.execute(
                self._bound_tool("tool.marmo.samples.http-get"),
                {"url": "https://example.test/status", "timeout_seconds": 2},
                self.context,
            )
        with (
            patch.dict(os.environ, {"MARMO_NOTIFICATION_OPS_URL": "https://hooks.example.test/notify"}),
            patch(
                "marmo_core.sample_resources.tools.urlopen",
                return_value=notification_response,
            ) as post_url,
        ):
            notified = self.runtime.execute(
                self._bound_tool("tool.marmo.samples.send-notification"),
                {"destination": "ops", "subject": "Ready", "message": "Release checks passed."},
                self.context,
            )

        self.assertEqual(fetched.status, "success")
        self.assertEqual(fetched.output["status"], 200)
        self.assertEqual(notified.status, "success")
        self.assertEqual(notified.output, {"message_id": "sample-message", "status": "202"})
        self.assertEqual(get_url.call_args.kwargs["timeout"], 2)
        self.assertEqual(post_url.call_args.kwargs["timeout"], 10)


class ExecutableAgentSampleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.registry = load_registry(SAMPLE_PATHS)
        cls.context = PolicyContext()
        cls.activator = ResourceActivator()
        cls.runtime = AgentRuntime(ToolRuntime())

    def test_all_ten_agents_resolve_and_execute_without_manual_bindings(self) -> None:
        agents = self.registry.list(kinds=("agent",))
        arguments = {
            "agent.marmo.samples.code-reviewer": {"goal": "Review change", "diff": "+ TODO remove"},
            "agent.marmo.samples.security-reviewer": {"goal": "Review webhook", "context": "external upload"},
            "agent.marmo.samples.test-planner": {"goal": "Test parser", "changed_files": ["parser.py"]},
            "agent.marmo.samples.docs-writer": {"goal": "Document resources", "audience": "operators"},
            "agent.marmo.samples.incident-triager": {"goal": "API unavailable", "symptoms": "many users see 5xx"},
            "agent.marmo.samples.data-analyst": {"goal": "Summarize latency", "records": [{"latency": 10}, {"latency": 20}]},
            "agent.marmo.samples.api-designer": {"goal": "Create jobs", "method": "POST", "path": "/jobs"},
            "agent.marmo.samples.release-manager": {"goal": "Release 1.0", "checks": {"tests": True}},
            "agent.marmo.samples.support-specialist": {"goal": "Draft reply", "customer_message": "Export failed"},
            "agent.marmo.samples.research-assistant": {"goal": "Compare evidence", "sources": ["Source fact."]},
        }

        self.assertEqual(len(agents), 10)
        for definition in agents:
            with self.subTest(resource=definition.metadata.id):
                activation = self.activator.activate(definition, self.context)
                self.assertTrue(activation.ok, activation.error)
                result = self.runtime.execute(
                    activation.activated,
                    arguments[definition.metadata.id],
                    self.context,
                )
                self.assertEqual(result.status, "success", result.error)
                self.assertIsInstance(result.output, dict)
                self.assertTrue(definition.metadata.ref.startswith("python:marmo_core.sample_resources.agents:"))


if __name__ == "__main__":
    unittest.main()
