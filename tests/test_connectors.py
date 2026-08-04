from __future__ import annotations

from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from dataclasses import replace as dataclass_replace
from pathlib import Path
from threading import Thread
import shutil
import sqlite3
import tempfile
import unittest

from marmo_core import (
    BoundTool,
    ConnectorCircuitOpenError,
    ConnectorConfig,
    ConnectorError,
    ConnectorPathError,
    ConnectorRuntime,
    FileSystemConnector,
    HitlResponse,
    HTTPConnector,
    Kernel,
    MappingSecretResolver,
    MockLLMProvider,
    PolicyContext,
    PolicyRejectedError,
    ResourceRegistry,
    SQLiteConnector,
    SecretRef,
    ShellConnector,
    ToolRuntime,
    connector_tools,
)
from marmo_core.cli import build_parser


def _bound(connector, resource_id: str) -> BoundTool:
    tool = next(item for item in connector.tools() if item.resource_id == resource_id)
    return BoundTool(
        definition=tool.definition,
        input_schema=dict(tool.definition.extras["input_schema"]),
        output_schema=dict(tool.definition.extras["output_schema"]),
        handler=tool.handler,
    )


class ConnectorRuntimeTests(unittest.TestCase):
    def test_retry_safe_operation_uses_connector_retry_budget(self) -> None:
        calls = 0
        sleeps: list[float] = []
        runtime = ConnectorRuntime(
            ConnectorConfig(max_attempts=2, initial_backoff_seconds=0.25),
            sleeper=sleeps.append,
        )

        def flaky() -> str:
            nonlocal calls
            calls += 1
            if calls == 1:
                raise OSError("temporary")
            return "ok"

        output = runtime.execute("connector.test.read", flaky, {}, retry_safe=True)

        self.assertEqual(output, "ok")
        self.assertEqual(calls, 2)
        self.assertEqual(sleeps, [0.25])

    def test_non_retry_safe_operation_runs_once(self) -> None:
        calls = 0
        runtime = ConnectorRuntime(ConnectorConfig(max_attempts=3))

        def failing() -> None:
            nonlocal calls
            calls += 1
            raise OSError("do not repeat a write")

        with self.assertRaises(OSError):
            runtime.execute("connector.test.write", failing, {}, retry_safe=False)
        self.assertEqual(calls, 1)

    def test_circuit_opens_after_transient_failures(self) -> None:
        calls = 0
        runtime = ConnectorRuntime(
            ConnectorConfig(circuit_failure_threshold=1, circuit_reset_seconds=60)
        )

        def failing() -> None:
            nonlocal calls
            calls += 1
            raise OSError("offline")

        with self.assertRaises(OSError):
            runtime.execute("connector.test.read", failing, {}, retry_safe=False)
        with self.assertRaises(ConnectorCircuitOpenError):
            runtime.execute("connector.test.read", failing, {}, retry_safe=False)
        self.assertEqual(calls, 1)

    def test_rate_limit_is_per_operation(self) -> None:
        now = [10.0]
        sleeps: list[float] = []

        def wait(seconds: float) -> None:
            sleeps.append(seconds)
            now[0] += seconds

        runtime = ConnectorRuntime(
            ConnectorConfig(rate_limit_per_second=2),
            clock=lambda: now[0],
            sleeper=wait,
        )
        runtime.execute("a", lambda: 1, {}, retry_safe=True)
        runtime.execute("a", lambda: 2, {}, retry_safe=True)
        runtime.execute("b", lambda: 3, {}, retry_safe=True)

        self.assertEqual(sleeps, [0.5])


class FileSystemConnectorTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name) / "root"
        self.root.mkdir()
        (self.root / "note.txt").write_text("hello", encoding="utf-8")
        self.connector = FileSystemConnector(self.root)

    def tearDown(self) -> None:
        self.temp.cleanup()

    def test_read_list_and_atomic_write_stay_inside_root(self) -> None:
        tools = {item.operation: item.handler for item in self.connector.tools()}

        read = tools["read_text"](path="note.txt")
        listing = tools["list"](path=".")
        written = tools["write_text"](path="new.txt", text="new body")

        self.assertEqual(read["text"], "hello")
        self.assertEqual(listing["entries"][0]["name"], "note.txt")
        self.assertEqual(written["bytes_written"], 8)
        self.assertEqual((self.root / "new.txt").read_text("utf-8"), "new body")

    def test_parent_traversal_and_symlink_escape_are_rejected(self) -> None:
        read = {item.operation: item.handler for item in self.connector.tools()}["read_text"]
        outside = Path(self.temp.name) / "outside.txt"
        outside.write_text("secret", encoding="utf-8")

        with self.assertRaises(ConnectorPathError):
            read(path="../outside.txt")
        try:
            (self.root / "escape.txt").symlink_to(outside)
        except OSError:
            return
        with self.assertRaises(ConnectorPathError):
            read(path="escape.txt")

    def test_dry_run_validates_write_without_touching_file(self) -> None:
        tool = _bound(self.connector, "connector.file.write_text")
        result = ToolRuntime().execute(
            tool,
            {"path": "dry.txt", "text": "never written"},
            PolicyContext(
                granted_permissions=("connector.file.write",),
                dry_run=True,
                minimum_isolation_level="L2",
            ),
        )

        self.assertEqual(result.status, "dry_run")
        self.assertFalse((self.root / "dry.txt").exists())

    def test_kernel_installs_connector_resources_and_handlers(self) -> None:
        kernel = Kernel(
            ResourceRegistry(),
            MockLLMProvider(
                tool_arguments={"connector.file.read_text": {"path": "note.txt"}}
            ),
            connectors=(self.connector,),
            policy_context=PolicyContext(
                granted_permissions=("connector.file.read",),
                minimum_isolation_level="L2",
            ),
            set_limits={"tool": 1},
        )

        result = kernel.run_goal("Read the note text file")

        self.assertEqual(result.status, "completed", result.detail)
        self.assertEqual(result.tool_results[0].tool_id, "connector.file.read_text")
        self.assertEqual(result.tool_results[0].output["text"], "hello")

    def test_file_write_pauses_and_resume_does_not_repeat_it(self) -> None:
        kernel = Kernel(
            ResourceRegistry(),
            MockLLMProvider(
                tool_arguments={
                    "connector.file.write_text": {"path": "approved.txt", "text": "once"}
                }
            ),
            connectors=(self.connector,),
            policy_context=PolicyContext(
                granted_permissions=("connector.file.write",),
                minimum_isolation_level="L2",
            ),
            set_limits={"tool": 1},
        )

        paused = kernel.run_goal("Write text file approved.txt")
        self.assertEqual(paused.status, "escalated")
        self.assertFalse((self.root / "approved.txt").exists())

        completed = kernel.resume(paused.task_id, HitlResponse(kind="approve"))
        repeated = kernel.run(paused.task_id)
        self.assertEqual(completed.status, "completed", completed.detail)
        self.assertIs(repeated, completed)
        self.assertEqual((self.root / "approved.txt").read_text("utf-8"), "once")
        self.assertEqual(len(completed.tool_results), 1)


class _HTTPHandler(BaseHTTPRequestHandler):
    seen_authorization = ""

    def do_GET(self) -> None:  # noqa: N802 - stdlib callback name
        type(self).seen_authorization = self.headers.get("Authorization", "")
        if self.path == "/redirect":
            self.send_response(302)
            self.send_header("Location", "/ok")
            self.end_headers()
            return
        body = b"local response"
        self.send_response(200)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format: str, *args: object) -> None:
        return


class HTTPConnectorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), _HTTPHandler)
        cls.thread = Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.base_url = f"http://127.0.0.1:{cls.server.server_port}"

    @classmethod
    def tearDownClass(cls) -> None:
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(timeout=1)

    def setUp(self) -> None:
        _HTTPHandler.seen_authorization = ""
        self.connector = HTTPConnector(
            allowed_hosts=("127.0.0.1",),
            allow_private_networks=True,
        )
        self.tool = _bound(self.connector, "connector.http.request")
        self.context = PolicyContext(
            granted_permissions=("connector.http.request",),
            human_approved=True,
            allowed_external_hosts=("127.0.0.1",),
            minimum_isolation_level="L2",
        )

    def test_http_request_uses_secret_ref_without_persisting_secret(self) -> None:
        runtime = ToolRuntime(
            secret_resolver=MappingSecretResolver({"http_token": "Bearer private-token"})
        )
        reviewed = runtime.gateway.evaluate(
            self.tool.definition,
            self.context,
            gate="execution",
            arguments={
                "url": self.base_url + "/ok",
                "headers": {"Authorization": "Bearer private-token"},
            },
        )
        context = dataclass_replace(
            self.context,
            approved_operations=(reviewed.approval_token,),
        )
        result = runtime.execute(
            self.tool,
            {
                "url": self.base_url + "/ok",
                "headers": {"Authorization": SecretRef("http_token")},
            },
            context,
        )

        self.assertEqual(result.status, "success")
        self.assertEqual(result.output["body"], "local response")
        self.assertEqual(_HTTPHandler.seen_authorization, "Bearer private-token")
        self.assertEqual(result.arguments["headers"]["Authorization"], {"$secret": "http_token"})
        self.assertNotIn("private-token", str(result.to_dict()))

    def test_policy_blocklist_stops_request_before_handler(self) -> None:
        context = PolicyContext(
            granted_permissions=("connector.http.request",),
            human_approved=True,
            blocked_external_hosts=("127.0.0.1",),
            minimum_isolation_level="L2",
        )
        with self.assertRaises(PolicyRejectedError):
            ToolRuntime().execute(self.tool, {"url": self.base_url + "/ok"}, context)

    def test_redirects_are_not_followed(self) -> None:
        result = ToolRuntime().execute(
            self.tool,
            {"url": self.base_url + "/redirect"},
            self.context,
        )
        self.assertEqual(result.status, "error")
        self.assertIn("status 302", result.error)

    def test_private_networks_are_denied_by_default(self) -> None:
        connector = HTTPConnector()
        request = {item.operation: item.handler for item in connector.tools()}["request"]
        with self.assertRaisesRegex(ConnectorError, "private"):
            request(url=self.base_url + "/ok")

    def test_connector_host_allowlist_is_enforced_and_controls_isolation(self) -> None:
        unrestricted = HTTPConnector(allow_private_networks=True)
        self.assertEqual(
            _bound(unrestricted, "connector.http.request").definition.extras["isolation_level"],
            "L1",
        )
        restricted = HTTPConnector(
            allowed_hosts=("example.com",),
            allow_private_networks=True,
        )
        tool = _bound(restricted, "connector.http.request")
        self.assertEqual(tool.definition.extras["isolation_level"], "L2")
        with self.assertRaisesRegex(ConnectorError, "allowlist"):
            tool.handler(url=self.base_url + "/ok")


class ShellConnectorTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        command = shutil.which("echo") or shutil.which("printf")
        assert command is not None
        self.command = command
        self.connector = ShellConnector(self.root, (command,))

    def tearDown(self) -> None:
        self.temp.cleanup()

    def test_shell_false_prevents_redirection_and_expansion(self) -> None:
        run = {item.operation: item.handler for item in self.connector.tools()}["run"]
        result = run(command=f"{self.command} hello > escaped.txt")

        self.assertEqual(result["exit_code"], 0)
        self.assertFalse((self.root / "escaped.txt").exists())
        self.assertIn(">", result["stdout"])

    def test_disallowed_executable_and_cwd_escape_are_rejected(self) -> None:
        run = {item.operation: item.handler for item in self.connector.tools()}["run"]
        with self.assertRaisesRegex(Exception, "allowlist"):
            run(command="definitely-not-allowed")
        with self.assertRaises(ConnectorPathError):
            run(command=f"{self.command} hello", cwd="..")

    def test_policy_denies_root_delete_before_connector(self) -> None:
        tool = _bound(self.connector, "connector.shell.run")
        with self.assertRaises(PolicyRejectedError):
            ToolRuntime().execute(
                tool,
                {"command": "rm -rf /"},
                PolicyContext(
                    granted_permissions=("shell.exec",),
                    human_approved=True,
                    minimum_isolation_level="L1",
                ),
            )

    def test_l2_requirement_rejects_l1_shell_connector(self) -> None:
        decision = ToolRuntime().gateway.evaluate(
            _bound(self.connector, "connector.shell.run").definition,
            PolicyContext(granted_permissions=("shell.exec",), minimum_isolation_level="L2"),
            gate="activation",
        )
        self.assertTrue(decision.denied)


class SQLiteConnectorTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.database = Path(self.temp.name) / "test.sqlite3"
        with sqlite3.connect(self.database) as connection:
            connection.execute("CREATE TABLE notes (id INTEGER PRIMARY KEY, body TEXT)")
            connection.execute("INSERT INTO notes (body) VALUES (?)", ("first",))
        self.connector = SQLiteConnector(self.database)

    def tearDown(self) -> None:
        self.temp.cleanup()

    def test_parameterized_query_and_bounded_rows(self) -> None:
        query = {item.operation: item.handler for item in self.connector.tools()}["query"]
        result = query(
            sql="SELECT id, body FROM notes WHERE body = :body",
            parameters={"body": "first' OR 1=1 --"},
            limit=10,
        )
        self.assertEqual(result["rows"], [])

        result = query(sql="SELECT id, body FROM notes ORDER BY id", limit=1)
        self.assertEqual(result["columns"], ["id", "body"])
        self.assertEqual(result["rows"], [[1, "first"]])

    def test_execute_write_runs_through_policy_and_tool_runtime(self) -> None:
        tool = _bound(self.connector, "connector.sqlite.execute")
        result = ToolRuntime().execute(
            tool,
            {"sql": "INSERT INTO notes (body) VALUES (:body)", "parameters": {"body": "second"}},
            PolicyContext(
                granted_permissions=("connector.sqlite.write",),
                human_approved=True,
                minimum_isolation_level="L2",
            ),
        )
        self.assertEqual(result.status, "success")
        with sqlite3.connect(self.database) as connection:
            count = connection.execute("SELECT COUNT(*) FROM notes").fetchone()[0]
        self.assertEqual(count, 2)

    def test_query_connection_is_read_only(self) -> None:
        query = {item.operation: item.handler for item in self.connector.tools()}["query"]
        with self.assertRaisesRegex(ConnectorError, "only SELECT"):
            query(sql="DELETE FROM notes")

    def test_execute_rejects_attach_and_transaction_control(self) -> None:
        execute = {item.operation: item.handler for item in self.connector.tools()}["execute"]
        with self.assertRaisesRegex(ConnectorError, "accepts one"):
            execute(sql="ATTACH DATABASE ':memory:' AS other")
        with self.assertRaisesRegex(ConnectorError, "accepts one"):
            execute(sql="BEGIN")


class ConnectorRegistrationTests(unittest.TestCase):
    def test_duplicate_connector_tools_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as root:
            connector = FileSystemConnector(root)
            with self.assertRaisesRegex(Exception, "duplicate"):
                connector_tools((connector, connector))

    def test_cli_exposes_builtin_connector_configuration(self) -> None:
        parser = build_parser()
        args = parser.parse_args(
            [
                "run",
                "--task",
                "read a file",
                "--connector-file-root",
                ".",
                "--connector-max-attempts",
                "2",
            ]
        )
        self.assertEqual(args.connector_file_root, ".")
        self.assertEqual(args.connector_max_attempts, 2)


if __name__ == "__main__":
    unittest.main()
