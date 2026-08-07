"""MCP (Model Context Protocol) stdio adapter.

Marmo-Core does not build a parallel tool ecosystem: it treats MCP servers
as resource suppliers and layers unified retrieval, the Policy Gateway, and
the audit log on top of them (F-DIST-06). This module is a minimal,
standard-library-based MCP client for the stdio transport (newline-delimited
JSON-RPC 2.0 over a child process's stdin/stdout).

Security defaults are conservative (F-SEC-01): imported tools default to
``trust_level="community"`` and ``side_effect="external"``, so the default
Policy Gateway escalates every call to a human unless the context says
otherwise. Callers may relax or tighten both per server.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Sequence
import json
import re
import selectors
import subprocess
import threading

from .errors import MarmoError
from .models import ResourceDefinition
from ._version import __version__

MCP_PROTOCOL_VERSION = "2024-11-05"
_CLIENT_INFO = {"name": "marmo-core", "version": __version__}


class MCPError(MarmoError):
    """Raised when an MCP server misbehaves or reports an error."""


@dataclass(frozen=True)
class MCPToolInfo:
    """One tool advertised by an MCP server."""

    name: str
    description: str
    input_schema: dict[str, Any]


class MCPStdioClient:
    """JSON-RPC 2.0 client for one MCP server child process.

    Usage:

    .. code-block:: python

        client = MCPStdioClient(["python3", "my_mcp_server.py"])
        client.start()
        tools = client.list_tools()
        result = client.call_tool("echo", {"text": "hi"})
        client.close()

    The client answers server ``ping`` requests and ignores server
    notifications; it does not implement sampling or roots.
    """

    def __init__(
        self,
        command: Sequence[str],
        *,
        env: Mapping[str, str] | None = None,
        cwd: str | None = None,
        timeout: float = 30.0,
    ) -> None:
        if not command:
            raise ValueError("command must not be empty")
        self.command = list(command)
        self.env = dict(env) if env is not None else None
        self.cwd = cwd
        self.timeout = timeout
        self._process: subprocess.Popen[str] | None = None
        self._next_id = 0
        self._lock = threading.Lock()
        self.server_info: dict[str, Any] = {}

    # -- lifecycle -------------------------------------------------------------

    def start(self) -> dict[str, Any]:
        """Spawn the server and run the MCP initialize handshake."""

        if self._process is not None:
            raise MCPError("client is already started")
        self._process = subprocess.Popen(
            self.command,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            env=self.env,
            cwd=self.cwd,
            text=True,
            bufsize=1,
        )
        result = self._request(
            "initialize",
            {
                "protocolVersion": MCP_PROTOCOL_VERSION,
                "capabilities": {},
                "clientInfo": dict(_CLIENT_INFO),
            },
        )
        self.server_info = result.get("serverInfo", {}) if isinstance(result, dict) else {}
        self._notify("notifications/initialized", {})
        return result

    def close(self) -> None:
        process = self._process
        self._process = None
        if process is None:
            return
        try:
            if process.stdin:
                process.stdin.close()
            if process.poll() is None:
                process.terminate()
                process.wait(timeout=5.0)
        except Exception:
            if process.poll() is None:
                process.kill()
                process.wait(timeout=5.0)
        finally:
            if process.stdout:
                process.stdout.close()
            if process.stderr:
                process.stderr.close()

    def __enter__(self) -> "MCPStdioClient":
        self.start()
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.close()

    # -- MCP operations ----------------------------------------------------------

    def list_tools(self) -> list[MCPToolInfo]:
        tools: list[MCPToolInfo] = []
        cursor: str | None = None
        while True:
            params: dict[str, Any] = {"cursor": cursor} if cursor else {}
            result = self._request("tools/list", params)
            for item in result.get("tools", []):
                tools.append(
                    MCPToolInfo(
                        name=str(item.get("name", "")),
                        description=str(item.get("description", "")),
                        input_schema=dict(item.get("inputSchema", {}) or {}),
                    )
                )
            cursor = result.get("nextCursor")
            if not cursor:
                return tools

    def call_tool(self, name: str, arguments: Mapping[str, Any] | None = None) -> dict[str, Any]:
        """Invoke one tool and return ``{"content": str, "structured": Any, "is_error": bool}``."""

        result = self._request("tools/call", {"name": name, "arguments": dict(arguments or {})})
        blocks = result.get("content", [])
        text_parts = [
            str(block.get("text", ""))
            for block in blocks
            if isinstance(block, Mapping) and block.get("type") == "text"
        ]
        return {
            "content": "\n".join(part for part in text_parts if part),
            "structured": result.get("structuredContent"),
            "is_error": bool(result.get("isError", False)),
        }

    # -- JSON-RPC plumbing ---------------------------------------------------------

    def _request(self, method: str, params: Mapping[str, Any]) -> dict[str, Any]:
        with self._lock:
            self._next_id += 1
            request_id = self._next_id
            self._send({"jsonrpc": "2.0", "id": request_id, "method": method, "params": dict(params)})
            while True:
                message = self._read_message()
                if message.get("id") == request_id and ("result" in message or "error" in message):
                    if "error" in message:
                        error = message["error"]
                        raise MCPError(f"MCP {method} failed: {error.get('message', error)}")
                    result = message.get("result")
                    return result if isinstance(result, dict) else {}
                self._handle_unrelated(message)

    def _notify(self, method: str, params: Mapping[str, Any]) -> None:
        self._send({"jsonrpc": "2.0", "method": method, "params": dict(params)})

    def _handle_unrelated(self, message: Mapping[str, Any]) -> None:
        if message.get("method") == "ping" and "id" in message:
            self._send({"jsonrpc": "2.0", "id": message["id"], "result": {}})
        # Server notifications and other requests are ignored by this minimal client.

    def _send(self, message: Mapping[str, Any]) -> None:
        process = self._require_process()
        assert process.stdin is not None
        try:
            process.stdin.write(json.dumps(message, ensure_ascii=False) + "\n")
            process.stdin.flush()
        except (BrokenPipeError, ValueError) as error:
            raise MCPError(f"MCP server closed its stdin: {error}") from error

    def _read_message(self) -> dict[str, Any]:
        process = self._require_process()
        assert process.stdout is not None
        selector = selectors.DefaultSelector()
        selector.register(process.stdout, selectors.EVENT_READ)
        try:
            while True:
                if not selector.select(timeout=self.timeout):
                    raise MCPError(f"MCP server did not respond within {self.timeout}s")
                line = process.stdout.readline()
                if not line:
                    raise MCPError("MCP server closed the connection")
                line = line.strip()
                if not line:
                    continue
                try:
                    message = json.loads(line)
                except json.JSONDecodeError:
                    continue  # tolerate stray non-JSON output on stdout
                if isinstance(message, dict):
                    return message
        finally:
            selector.close()

    def _require_process(self) -> subprocess.Popen[str]:
        if self._process is None:
            raise MCPError("client is not started; call start() first")
        return self._process


def mcp_tool_resources(
    tools: Sequence[MCPToolInfo],
    *,
    server_name: str,
    trust_level: str = "community",
    side_effect: str = "external",
    isolation_level: str = "L0",
    version: str = "0.1.0",
) -> list[ResourceDefinition]:
    """Convert MCP tools into unified Tool resources.

    Each tool requires the ``mcp.<server>`` permission, so a policy context
    must grant it explicitly before any imported tool can activate.
    """

    slug = _slug(server_name)
    definitions = []
    for tool in tools:
        tool_slug = _slug(tool.name)
        definitions.append(
            ResourceDefinition.from_mapping(
                {
                    "id": f"tool.mcp.{slug}.{tool_slug}",
                    "kind": "tool",
                    "name": f"{tool.name} (MCP: {server_name})",
                    "version": version,
                    "description": tool.description or f"MCP tool {tool.name} from server {server_name}.",
                    "capabilities": [f"mcp:{slug}:{tool_slug}"],
                    "input_summary": _schema_summary(tool.input_schema),
                    "output_summary": "MCP tool result content.",
                    "required_permissions": [f"mcp.{slug}"],
                    "cost_estimate": 0.0,
                    "latency_class": "medium",
                    "side_effect": side_effect,
                    "trust_level": trust_level,
                    "ref": f"mcp://{slug}/{tool.name}",
                    "tags": ["mcp", slug],
                    "input_schema": dict(tool.input_schema),
                    "isolation_level": isolation_level,
                },
                source=f"mcp://{slug}",
            )
        )
    return definitions


def mcp_tool_implementations(
    client: MCPStdioClient,
    definitions: Sequence[ResourceDefinition],
) -> dict[str, Any]:
    """Build a ``tool_implementations`` mapping for the Kernel.

    Every call still passes the Policy Gateway's activation and execution
    gates before it reaches the MCP server.
    """

    implementations: dict[str, Any] = {}
    for definition in definitions:
        ref = definition.metadata.ref
        if not ref.startswith("mcp://"):
            continue
        tool_name = ref.split("/", 3)[-1]
        implementations[definition.metadata.id] = _MCPToolBinding(client, tool_name)
    return implementations


def connect_mcp_server(
    command: Sequence[str],
    *,
    server_name: str | None = None,
    trust_level: str = "community",
    side_effect: str = "external",
    isolation_level: str = "L0",
    env: Mapping[str, str] | None = None,
    cwd: str | None = None,
    timeout: float = 30.0,
) -> tuple[MCPStdioClient, list[ResourceDefinition], dict[str, Any]]:
    """Start an MCP server and return (client, resources, tool implementations).

    The caller owns the client and must ``close()`` it when done.
    """

    client = MCPStdioClient(command, env=env, cwd=cwd, timeout=timeout)
    client.start()
    name = server_name or str(client.server_info.get("name") or command[0])
    tools = client.list_tools()
    definitions = mcp_tool_resources(
        tools,
        server_name=name,
        trust_level=trust_level,
        side_effect=side_effect,
        isolation_level=isolation_level,
    )
    implementations = mcp_tool_implementations(client, definitions)
    return client, definitions, implementations


class _MCPToolBinding:
    """Callable bridging one unified Tool resource to ``tools/call``."""

    def __init__(self, client: MCPStdioClient, tool_name: str) -> None:
        self.client = client
        self.tool_name = tool_name

    def __call__(self, **arguments: Any) -> dict[str, Any]:
        result = self.client.call_tool(self.tool_name, arguments)
        if result["is_error"]:
            raise MCPError(f"MCP tool {self.tool_name} reported an error: {result['content']}")
        return result


def _schema_summary(schema: Mapping[str, Any]) -> str:
    properties = schema.get("properties")
    if isinstance(properties, Mapping) and properties:
        names = ", ".join(sorted(properties))
        return f"JSON object with properties: {names}."
    return "JSON object arguments."


def _slug(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.casefold()).strip("-")
    return slug or "server"
