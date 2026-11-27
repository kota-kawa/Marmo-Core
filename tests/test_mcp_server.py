"""MCP gateway: tool search and gated calls for an MCP client."""

from __future__ import annotations

from io import StringIO
from pathlib import Path
from typing import Any, Callable
import json
import sys
import tempfile
import unittest

from marmo_core import (
    AuditLog,
    FunctionToolkit,
    GreedyConstrainedSetSelector,
    MCPGatewayServer,
    MCPStdioClient,
    PolicyContext,
    ResourceDefinition,
    ResourceRegistry,
)

CALLS: list[dict[str, Any]] = []


def lookup_order(order_id: str) -> dict[str, Any]:
    """Importable handler for the stdio round trip."""

    return {"order_id": order_id, "status": "shipped"}


def _resource(
    resource_id: str,
    description: str,
    *,
    kind: str = "tool",
    side_effect: str = "read",
    permissions: tuple[str, ...] = (),
    dependencies: tuple[str, ...] = (),
) -> ResourceDefinition:
    payload: dict[str, Any] = {
        "id": resource_id,
        "kind": kind,
        "name": resource_id.rsplit(".", 1)[-1],
        "version": "1.0.0",
        "description": description,
        "capabilities": [resource_id],
        "input_summary": "order_id",
        "output_summary": "result",
        "required_permissions": list(permissions),
        "cost_estimate": 0.0,
        "latency_class": "fast",
        "side_effect": side_effect,
        "trust_level": "verified",
        "ref": f"test://{resource_id}",
        "tags": ["orders"],
        "dependencies": list(dependencies),
    }
    if kind == "tool":
        payload["input_schema"] = {
            "type": "object",
            "properties": {"order_id": {"type": "string"}},
            "required": ["order_id"],
            "additionalProperties": False,
        }
    return ResourceDefinition.from_mapping(payload, source="test")


def _handler(label: str, output: Any = None) -> Callable[..., Any]:
    def handler(**arguments: Any) -> Any:
        CALLS.append({"tool": label, **arguments})
        return {"tool": label, **arguments} if output is None else output

    return handler


class GatewayCase(unittest.TestCase):
    def setUp(self) -> None:
        CALLS.clear()
        self._next_id = 0

    def gateway(
        self,
        definitions: list[ResourceDefinition],
        handlers: dict[str, Callable[..., Any]] | None = None,
        **options: Any,
    ) -> MCPGatewayServer:
        registry = ResourceRegistry()
        registry.extend(definitions)
        if handlers is None:
            handlers = {d.metadata.id: _handler(d.metadata.id) for d in definitions if d.metadata.kind == "tool"}
        return MCPGatewayServer(registry, tool_implementations=handlers, **options)

    def request(self, server: MCPGatewayServer, method: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        self._next_id += 1
        response = server.handle_message(
            {"jsonrpc": "2.0", "id": self._next_id, "method": method, "params": params or {}}
        )
        assert response is not None
        self.assertEqual(response["id"], self._next_id)
        return response

    def tool(self, server: MCPGatewayServer, name: str, arguments: dict[str, Any]) -> tuple[bool, str]:
        result = self.request(server, "tools/call", {"name": name, "arguments": arguments})["result"]
        return result["isError"], result["content"][0]["text"]

    def search(self, server: MCPGatewayServer, goal: str) -> dict[str, Any]:
        is_error, text = self.tool(server, "search_tools", {"goal": goal})
        self.assertFalse(is_error)
        return json.loads(text)

    def call(self, server: MCPGatewayServer, name: str, **arguments: Any) -> tuple[bool, str]:
        return self.tool(server, "call_tool", {"name": name, "arguments": arguments})


class ProtocolTests(GatewayCase):
    def test_initialize_lists_the_two_gateway_tools_whatever_the_catalog_holds(self) -> None:
        server = self.gateway([_resource(f"tool.orders.t{i}", "look up an order") for i in range(20)])
        initialized = self.request(server, "initialize")["result"]
        self.assertEqual(initialized["capabilities"], {"tools": {}})
        self.assertEqual(initialized["serverInfo"]["name"], "marmo-core")
        tools = self.request(server, "tools/list")["result"]["tools"]
        self.assertEqual([tool["name"] for tool in tools], ["search_tools", "call_tool"])
        self.assertEqual(self.request(server, "ping")["result"], {})

    def test_notifications_get_no_reply_and_unknown_methods_get_an_error(self) -> None:
        server = self.gateway([])
        self.assertIsNone(server.handle_message({"jsonrpc": "2.0", "method": "notifications/initialized"}))
        self.assertEqual(self.request(server, "resources/list")["error"]["code"], -32601)
        self.assertEqual(self.request(server, "tools/call", {"name": "nope"})["error"]["code"], -32602)
        self.assertEqual(server.handle_message([])["error"]["code"], -32600)

    def test_serve_answers_line_by_line_and_reports_a_line_that_is_not_json(self) -> None:
        server = self.gateway([])
        reader = StringIO('{"jsonrpc":"2.0","id":1,"method":"ping"}\n\nnot json\n{"jsonrpc":"2.0","method":"x"}\n')
        writer = StringIO()
        server.serve(reader, writer)
        replies = [json.loads(line) for line in writer.getvalue().splitlines()]
        self.assertEqual(replies[0], {"jsonrpc": "2.0", "id": 1, "result": {}})
        self.assertEqual(replies[1]["error"]["code"], -32700)
        self.assertEqual(len(replies), 2)


class SearchAndCallTests(GatewayCase):
    def test_search_discloses_matching_tools_with_schemas_and_call_runs_one(self) -> None:
        lookup = _resource("tool.orders.lookup", "look up the shipping status of an order")
        server = self.gateway([lookup, _resource("tool.weather.today", "weather forecast for a city")], max_tools=1)
        found = self.search(server, "what is the shipping status of my order")
        self.assertEqual(found["status"], "selected")
        self.assertEqual([tool["name"] for tool in found["tools"]], ["tool.orders.lookup@1.0.0"])
        self.assertEqual(found["tools"][0]["input_schema"], lookup.extras["input_schema"])
        is_error, text = self.call(server, "tool.orders.lookup@1.0.0", order_id="A1")
        self.assertFalse(is_error)
        self.assertIn('"order_id": "A1"', text)
        self.assertIn('<untrusted-content trust="untrusted_content" source="tool:tool.orders.lookup@1.0.0">', text)
        self.assertEqual(CALLS, [{"tool": "tool.orders.lookup", "order_id": "A1"}])

    def test_a_tool_the_session_was_not_shown_cannot_be_called(self) -> None:
        server = self.gateway(
            [
                _resource("tool.orders.lookup", "look up the shipping status of an order"),
                _resource("tool.weather.today", "weather forecast for a city"),
            ],
            max_tools=1,
        )
        self.search(server, "shipping status of an order")
        is_error, text = self.call(server, "tool.weather.today@1.0.0", order_id="A1")
        self.assertTrue(is_error)
        self.assertIn("search_tools", text)
        self.assertEqual(CALLS, [])

    def test_invalid_arguments_are_reported_without_running_the_handler(self) -> None:
        server = self.gateway([_resource("tool.orders.lookup", "look up an order")])
        self.search(server, "look up an order")
        is_error, text = self.call(server, "tool.orders.lookup@1.0.0", order="A1")
        self.assertTrue(is_error)
        self.assertIn("missing required argument: order_id", text)
        is_error, _ = self.tool(server, "call_tool", {"name": "tool.orders.lookup@1.0.0", "arguments": "A1"})
        self.assertTrue(is_error)
        self.assertEqual(CALLS, [])

    def test_a_handler_failure_is_an_error_result_and_long_output_is_cut(self) -> None:
        def broken(**arguments: Any) -> Any:
            raise RuntimeError("backend down")

        server = self.gateway(
            [_resource("tool.orders.lookup", "look up an order"), _resource("tool.orders.export", "export every order")],
            {"tool.orders.lookup": broken, "tool.orders.export": _handler("export", "x" * 5000)},
            max_tool_output_tokens=10,
        )
        self.search(server, "look up an order and export every order")
        is_error, text = self.call(server, "tool.orders.lookup@1.0.0", order_id="A1")
        self.assertTrue(is_error)
        self.assertIn("backend down", text)
        is_error, text = self.call(server, "tool.orders.export@1.0.0", order_id="A1")
        self.assertFalse(is_error)
        self.assertIn("[truncated:", text)
        self.assertTrue(text.endswith("</untrusted-content>"))


class PolicyTests(GatewayCase):
    def test_a_tool_missing_a_permission_is_withheld_with_the_reason_and_cannot_run(self) -> None:
        server = self.gateway([_resource("tool.orders.refund", "refund an order", permissions=("orders.refund",))])
        found = self.search(server, "refund an order")
        self.assertEqual((found["status"], found["tools"]), ("abstain", []))
        self.assertEqual(found["withheld"][0]["resource"], "tool.orders.refund@1.0.0")
        self.assertIn("missing required permissions: orders.refund", found["withheld"][0]["reason"])
        is_error, _ = self.call(server, "tool.orders.refund@1.0.0", order_id="A1")
        self.assertTrue(is_error)
        self.assertEqual(CALLS, [])

    def test_tools_the_gate_will_not_allow_do_not_take_the_slots_of_usable_ones(self) -> None:
        blocked = [
            _resource(f"tool.orders.refund{i}", "refund an order", permissions=("orders.refund",))
            for i in range(3)
        ]
        usable = _resource("tool.billing.history", "list the payment history, including each refund, of a customer")
        server = self.gateway([*blocked, usable])
        found = self.search(server, "refund an order")
        self.assertEqual([tool["name"] for tool in found["tools"]], ["tool.billing.history@1.0.0"])
        self.assertEqual(len(found["withheld"]), 1)
        self.assertIn("tool.orders.refund", found["withheld"][0]["resource"])

    def test_a_side_effect_that_needs_approval_is_withheld_until_the_operator_approves_it(self) -> None:
        cancel = _resource("tool.orders.cancel", "cancel an order", side_effect="write")
        found = self.search(self.gateway([cancel]), "cancel an order")
        self.assertEqual(found["tools"], [])
        self.assertIn("requires human approval", found["withheld"][0]["reason"])

        approved = self.gateway([cancel], policy_context=PolicyContext(approved_resources=("tool.orders.cancel",)))
        self.assertEqual(self.search(approved, "cancel an order")["status"], "selected")
        is_error, _ = self.call(approved, "tool.orders.cancel@1.0.0", order_id="A1")
        self.assertFalse(is_error)
        self.assertEqual(CALLS, [{"tool": "tool.orders.cancel", "order_id": "A1"}])

    def test_after_a_tool_result_a_side_effecting_call_is_refused(self) -> None:
        server = self.gateway(
            [
                _resource("tool.orders.lookup", "look up an order"),
                _resource("tool.orders.cancel", "cancel an order", side_effect="write"),
            ],
            policy_context=PolicyContext(approved_resources=("tool.orders.cancel",)),
        )
        self.search(server, "look up an order and cancel an order")
        self.assertFalse(self.call(server, "tool.orders.lookup@1.0.0", order_id="A1")[0])
        is_error, text = self.call(server, "tool.orders.cancel@1.0.0", order_id="A1")
        self.assertTrue(is_error)
        self.assertIn("trust_boundary.untrusted_side_effect", text)
        self.assertIn("cannot collect", text)
        self.assertFalse(self.call(server, "tool.orders.lookup@1.0.0", order_id="A2")[0])
        self.assertEqual([call["tool"] for call in CALLS], ["tool.orders.lookup", "tool.orders.lookup"])

    def test_a_selector_escalation_is_reported_with_the_missing_permissions(self) -> None:
        server = self.gateway(
            [_resource("tool.orders.refund", "refund an order", permissions=("orders.refund",))],
            selector=GreedyConstrainedSetSelector(),
        )
        found = self.search(server, "refund an order")
        self.assertEqual((found["status"], found["tools"]), ("escalate", []))
        self.assertEqual(found["missing_permissions"], ["orders.refund"])

    def test_a_tool_whose_dependency_cannot_be_delivered_is_withheld(self) -> None:
        server = self.gateway(
            [
                _resource("skill.orders.policy", "order policy", kind="skill"),
                _resource("tool.orders.audit", "audit an order", dependencies=("skill.orders.policy",)),
                _resource("tool.orders.sign", "sign an order"),
                _resource("tool.orders.ship", "ship an order", dependencies=("tool.orders.sign",)),
            ],
            {"tool.orders.audit": _handler("audit"), "tool.orders.ship": _handler("ship")},
        )
        found = self.search(server, "audit an order and ship an order")
        self.assertEqual(found["tools"], [])
        reasons = {item["resource"]: item["reason"] for item in found["withheld"]}
        self.assertIn("serves tools only", reasons["tool.orders.audit@1.0.0"])
        self.assertIn("no executable implementation", reasons["tool.orders.sign@1.0.0"])
        self.assertIn("dependency tool.orders.sign was withheld", reasons["tool.orders.ship@1.0.0"])

    def test_every_search_and_call_is_on_one_verifiable_audit_chain(self) -> None:
        log = AuditLog()
        server = self.gateway([_resource("tool.orders.lookup", "look up an order")], audit_log=log)
        self.search(server, "look up an order")
        self.call(server, "tool.orders.lookup@1.0.0", order_id="A1")
        self.call(server, "tool.orders.lookup@1.0.0")
        self.assertEqual([record.kind for record in log.records], ["policy", "retrieve", "execute", "execute"])
        self.assertEqual(log.records[1].payload["selected"], ["tool.orders.lookup@1.0.0"])
        self.assertEqual(log.records[3].payload["status"], "invalid_input")
        self.assertEqual(len({record.trace_id for record in log.records}), 1)
        self.assertEqual(log.verify(), [])


class ToolkitAndCliTests(GatewayCase):
    def test_a_decorated_toolkit_is_served_end_to_end(self) -> None:
        orders = FunctionToolkit("orders", side_effect="read", required_permissions=())

        @orders.tool
        def shipping_status(order_id: str) -> dict[str, str]:
            """Look up the shipping status of an order."""

            return {"order_id": order_id, "status": "shipped"}

        registry = ResourceRegistry()
        registry.extend(orders.resources)
        server = MCPGatewayServer(registry, tool_implementations=orders.implementations)
        found = self.search(server, "shipping status of an order")
        self.assertEqual([tool["name"] for tool in found["tools"]], ["tool.orders.shipping-status@0.1.0"])
        is_error, text = self.call(server, "tool.orders.shipping-status@0.1.0", order_id="A1")
        self.assertFalse(is_error)
        self.assertIn('"status": "shipped"', text)

    def test_marmo_mcp_serve_answers_the_stdio_client_and_appends_the_audit_log(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            resources = Path(directory) / "tools.json"
            resources.write_text(
                json.dumps([_resource("tool.orders.lookup", "look up the shipping status of an order").to_dict()]),
                encoding="utf-8",
            )
            audit_path = Path(directory) / "audit.jsonl"
            command = [
                sys.executable,
                "-m",
                "marmo_core.cli",
                "mcp-serve",
                "--tool-impl",
                "tool.orders.lookup=tests.test_mcp_server:lookup_order",
                "--audit-log",
                str(audit_path),
                str(resources),
            ]
            with MCPStdioClient(command, cwd=str(Path(__file__).resolve().parent.parent), timeout=20.0) as client:
                self.assertEqual(client.server_info["name"], "marmo-core")
                self.assertEqual([tool.name for tool in client.list_tools()], ["search_tools", "call_tool"])
                found = json.loads(client.call_tool("search_tools", {"goal": "shipping status of an order"})["content"])
                self.assertEqual([tool["name"] for tool in found["tools"]], ["tool.orders.lookup@1.0.0"])
                result = client.call_tool(
                    "call_tool", {"name": "tool.orders.lookup@1.0.0", "arguments": {"order_id": "A1"}}
                )
                self.assertFalse(result["is_error"])
                self.assertIn('"status": "shipped"', result["content"])
                process = client._process
                assert process is not None and process.stdin is not None
                process.stdin.close()
                self.assertEqual(process.wait(timeout=20.0), 0)
            log = AuditLog.from_jsonl(audit_path)
            self.assertEqual([record.kind for record in log.records], ["policy", "retrieve", "execute"])
            self.assertEqual(log.verify(), [])


if __name__ == "__main__":
    unittest.main()
