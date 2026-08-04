"""Minimal offline MCP server over stdio for tests (newline-delimited JSON-RPC)."""

import json
import sys


TOOLS = [
    {
        "name": "echo",
        "description": "Echo the given text back.",
        "inputSchema": {
            "type": "object",
            "properties": {"text": {"type": "string"}},
            "required": ["text"],
        },
    },
    {
        "name": "add",
        "description": "Add two numbers.",
        "inputSchema": {
            "type": "object",
            "properties": {"a": {"type": "number"}, "b": {"type": "number"}},
            "required": ["a", "b"],
        },
    },
]


def reply(request_id, result):
    sys.stdout.write(json.dumps({"jsonrpc": "2.0", "id": request_id, "result": result}) + "\n")
    sys.stdout.flush()


def main() -> None:
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        message = json.loads(line)
        method = message.get("method")
        request_id = message.get("id")
        if method == "initialize":
            reply(
                request_id,
                {
                    "protocolVersion": message["params"]["protocolVersion"],
                    "capabilities": {"tools": {}},
                    "serverInfo": {"name": "fake-server", "version": "1.0.0"},
                },
            )
        elif method == "tools/list":
            reply(request_id, {"tools": TOOLS})
        elif method == "tools/call":
            name = message["params"]["name"]
            arguments = message["params"].get("arguments", {})
            if name == "echo":
                reply(request_id, {"content": [{"type": "text", "text": arguments.get("text", "")}]})
            elif name == "add":
                total = arguments.get("a", 0) + arguments.get("b", 0)
                reply(request_id, {"content": [{"type": "text", "text": str(total)}]})
            else:
                reply(request_id, {"content": [{"type": "text", "text": "unknown tool"}], "isError": True})
        elif request_id is not None:
            reply(request_id, {})
        # notifications are ignored


if __name__ == "__main__":
    main()
