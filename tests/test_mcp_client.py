"""MCP stdio client: message framing and the per-request deadline."""

from __future__ import annotations

from pathlib import Path
import sys
import time
import unittest

from marmo_core import MCPError, MCPStdioClient

FAKE_SERVER = Path(__file__).resolve().parent / "fake_mcp_server.py"


def _client(mode: str = "", timeout: float = 10.0) -> MCPStdioClient:
    command = [sys.executable, str(FAKE_SERVER)] + ([mode] if mode else [])
    return MCPStdioClient(command, timeout=timeout)


class MCPFramingTests(unittest.TestCase):
    def test_notification_and_response_in_one_write_are_both_consumed(self) -> None:
        with _client("batched") as client:
            started = time.monotonic()
            tools = client.list_tools()
            self.assertLess(time.monotonic() - started, 5.0)
        self.assertEqual([tool.name for tool in tools], ["echo", "add"])

    def test_message_following_the_response_stays_buffered_for_the_next_request(self) -> None:
        with _client("trailing") as client:
            self.assertEqual(len(client.list_tools()), 2)
            result = client.call_tool("add", {"a": 2, "b": 3})
        self.assertEqual(result["content"], "5")

    def test_response_line_written_in_two_parts_is_reassembled(self) -> None:
        with _client("split") as client:
            self.assertEqual(len(client.list_tools()), 2)

    def test_stale_buffer_is_dropped_when_the_client_restarts(self) -> None:
        client = _client("trailing")
        client.start()
        client.list_tools()
        client.close()
        client.start()
        try:
            self.assertEqual(len(client.list_tools()), 2)
        finally:
            client.close()


class MCPDeadlineTests(unittest.TestCase):
    def test_notifications_do_not_extend_the_request_deadline(self) -> None:
        client = _client("noisy", timeout=0.6)
        client.start()
        try:
            started = time.monotonic()
            with self.assertRaises(MCPError) as caught:
                client.list_tools()
            elapsed = time.monotonic() - started
        finally:
            client.close()
        self.assertIn("did not respond", str(caught.exception))
        self.assertLess(elapsed, 3.0)


if __name__ == "__main__":
    unittest.main()
