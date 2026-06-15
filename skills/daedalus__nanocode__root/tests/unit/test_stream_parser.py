"""Tests for streaming tool call parser."""

import json

import pytest

from nanocode.llm.stream_parser import (
    is_complete_json,
    parse_sse_stream,
)


class MockStreamResponse:
    """Mock HTTP streaming response for testing."""

    def __init__(self, chunks):
        self.chunks = chunks

    async def aiter_lines(self):
        for chunk in self.chunks:
            for line in chunk.split("\n"):
                yield line


class TestIsCompleteJson:
    """Tests for is_complete_json function."""

    def test_valid_empty_object(self):
        assert is_complete_json("{}")

    def test_valid_empty_array(self):
        assert is_complete_json("[]")

    def test_valid_object_with_content(self):
        assert is_complete_json('{"key": "value"}')

    def test_valid_nested(self):
        assert is_complete_json('{"key": {"nested": [1, 2, 3]}}')

    def test_partial_object(self):
        assert not is_complete_json("{")

    def test_partial_with_content(self):
        assert not is_complete_json('{"key": "val')

    def test_invalid_json(self):
        assert not is_complete_json("not json")

    def test_empty_string(self):
        assert not is_complete_json("")

    def test_whitespace_only(self):
        assert not is_complete_json("   ")

    def test_incomplete_array(self):
        assert not is_complete_json("[1, 2")

    def test_single_brace(self):
        assert not is_complete_json("}")


class TestParseSSEStream:
    """Tests for SSE stream parsing."""

    @pytest.mark.asyncio
    async def test_text_content(self):
        chunks = [
            'data: {"choices": [{"delta": {"content": "Hello"}}]}\n',
            'data: {"choices": [{"delta": {"content": " world"}}]}\n',
            "data: [DONE]\n",
        ]
        response = MockStreamResponse(chunks)
        events = [e async for e in parse_sse_stream(response)]

        text_events = [e for e in events if e.text is not None]
        assert len(text_events) == 2
        assert text_events[0].text == "Hello"
        assert text_events[1].text == " world"

    @pytest.mark.asyncio
    async def test_tool_call_single_chunk(self):
        chunk = {
            "choices": [
                {
                    "delta": {
                        "tool_calls": [
                            {
                                "index": 0,
                                "id": "call_1",
                                "function": {"name": "test", "arguments": "{}"},
                            }
                        ]
                    }
                }
            ]
        }
        chunks = [
            f"data: {json.dumps(chunk)}\n",
            "data: [DONE]\n",
        ]
        response = MockStreamResponse(chunks)
        events = [e async for e in parse_sse_stream(response)]

        # Find the complete tool call event
        complete_events = [e for e in events if e.tool_call_complete is not None]
        assert len(complete_events) == 1
        tool_id, tool_name, args = complete_events[0].tool_call_complete
        assert tool_id == "call_1"
        assert tool_name == "test"
        assert args == "{}"

    @pytest.mark.asyncio
    async def test_tool_call_with_arguments(self):
        args_json = json.dumps({"path": "/file.txt"})
        chunk = {
            "choices": [
                {
                    "delta": {
                        "tool_calls": [
                            {
                                "index": 0,
                                "id": "call_1",
                                "function": {"name": "read", "arguments": args_json},
                            }
                        ]
                    }
                }
            ]
        }
        chunks = [
            f"data: {json.dumps(chunk)}\n",
            "data: [DONE]\n",
        ]
        response = MockStreamResponse(chunks)
        events = [e async for e in parse_sse_stream(response)]

        complete_events = [e for e in events if e.tool_call_complete is not None]
        assert len(complete_events) == 1
        tool_id, tool_name, args = complete_events[0].tool_call_complete
        assert tool_id == "call_1"
        assert tool_name == "read"
        assert args == args_json

    @pytest.mark.asyncio
    async def test_multiple_tool_calls(self):
        tool1_args = json.dumps({"a": 1})
        tool2_args = json.dumps({"b": 2})

        chunk1 = {
            "choices": [
                {
                    "delta": {
                        "tool_calls": [
                            {
                                "index": 0,
                                "id": "call_1",
                                "function": {"name": "tool1", "arguments": tool1_args},
                            }
                        ]
                    }
                }
            ]
        }
        chunk2 = {
            "choices": [
                {
                    "delta": {
                        "tool_calls": [
                            {
                                "index": 1,
                                "id": "call_2",
                                "function": {"name": "tool2", "arguments": tool2_args},
                            }
                        ]
                    }
                }
            ]
        }

        chunks = [
            f"data: {json.dumps(chunk1)}\n",
            f"data: {json.dumps(chunk2)}\n",
            "data: [DONE]\n",
        ]
        response = MockStreamResponse(chunks)
        events = [e async for e in parse_sse_stream(response)]

        complete_events = [e for e in events if e.tool_call_complete is not None]
        assert len(complete_events) == 2

    @pytest.mark.asyncio
    async def test_finish_reason(self):
        chunk1 = {"choices": [{"delta": {"content": "Hello"}}]}
        chunk2 = {"choices": [{"finish_reason": "stop"}]}
        chunks = [
            f"data: {json.dumps(chunk1)}\n",
            f"data: {json.dumps(chunk2)}\n",
            "data: [DONE]\n",
        ]
        response = MockStreamResponse(chunks)
        events = [e async for e in parse_sse_stream(response)]

        finish_events = [e for e in events if e.finish_reason is not None]
        assert len(finish_events) == 1
        assert finish_events[0].finish_reason == "stop"

    @pytest.mark.asyncio
    async def test_usage(self):
        chunk = {
            "choices": [{"delta": {}}],
            "usage": {"prompt_tokens": 10, "completion_tokens": 5},
        }
        chunks = [
            f"data: {json.dumps(chunk)}\n",
            "data: [DONE]\n",
        ]
        response = MockStreamResponse(chunks)
        events = [e async for e in parse_sse_stream(response)]

        usage_events = [e for e in events if e.usage is not None]
        assert len(usage_events) == 1
        assert usage_events[0].usage["prompt_tokens"] == 10
