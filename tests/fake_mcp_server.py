"""Minimal offline MCP server over stdio for tests (newline-delimited JSON-RPC)."""

import json
import sys
import time

# Optional first argument selects how tools/list is answered:
#   batched  - a notification and the response in one write
#   trailing - the response and a following notification in one write
#   split    - the response line is written in two parts with a pause between
#   noisy    - a notification every 0.1s for 5s before the response
MODE = sys.argv[1] if len(sys.argv) > 1 else ""


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


def encode(payload):
    return json.dumps(payload) + "\n"


def notification(index=0):
    return encode({"jsonrpc": "2.0", "method": "notifications/message", "params": {"index": index}})


def reply_tools_list(request_id):
    response = encode({"jsonrpc": "2.0", "id": request_id, "result": {"tools": TOOLS}})
    if MODE == "batched":
        sys.stdout.write(notification() + response)
    elif MODE == "trailing":
        sys.stdout.write(response + notification())
    elif MODE == "split":
        middle = len(response) // 2
        sys.stdout.write(response[:middle])
        sys.stdout.flush()
        time.sleep(0.3)
        sys.stdout.write(response[middle:])
    elif MODE == "noisy":
        for index in range(50):
            sys.stdout.write(notification(index))
            sys.stdout.flush()
            time.sleep(0.1)
        sys.stdout.write(response)
    else:
        sys.stdout.write(response)
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
            reply_tools_list(request_id)
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
