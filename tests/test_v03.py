"""Tests for the 0.3.0 features: indexed retrieval, semantic layer, MCP, providers."""

from __future__ import annotations

from pathlib import Path
import sys
import time
import unittest

from marmo_core import (
    AnthropicLLMProvider,
    ChatMessage,
    HashingEmbeddingProvider,
    HybridRetriever,
    Kernel,
    LexicalRetriever,
    MCPStdioClient,
    MockLLMProvider,
    OpenAICompatibleEmbeddingProvider,
    OpenAICompatibleLLMProvider,
    PolicyContext,
    ResourceDefinition,
    ResourceRegistry,
    SearchQuery,
    LLMToolSpec,
    ToolCall,
    connect_mcp_server,
)

REPO_ROOT = Path(__file__).resolve().parent.parent
FAKE_SERVER = Path(__file__).resolve().parent / "fake_mcp_server.py"


def _tool(resource_id: str, description: str, tags: list[str] | None = None) -> ResourceDefinition:
    return ResourceDefinition.from_mapping(
        {
            "id": resource_id,
            "kind": "tool",
            "name": resource_id.split(".")[-1],
            "version": "1.0.0",
            "description": description,
            "capabilities": [],
            "input_summary": "input",
            "output_summary": "output",
            "required_permissions": [],
            "cost_estimate": 0.0,
            "latency_class": "fast",
            "side_effect": "none",
            "trust_level": "core",
            "ref": f"tool://{resource_id}",
            "tags": tags or [],
        }
    )


class IndexedRetrieverTests(unittest.TestCase):
    def setUp(self) -> None:
        self.registry = ResourceRegistry()
        self.registry.add(_tool("tool.okr.checker", "Verify OKR quality and measurable key results."))
        self.registry.add(_tool("tool.db.designer", "Design a relational database schema with indexes."))
        self.registry.add(_tool("tool.generic.helper", "A generic helper for verifying quality of results."))

    def test_rare_terms_outrank_common_term_overlap(self) -> None:
        results = LexicalRetriever().search(self.registry, SearchQuery(task="verify OKR quality", top_k=3))
        self.assertEqual(results[0].resource.metadata.id, "tool.okr.checker")
        self.assertGreater(results[0].score, results[1].score)

    def test_index_invalidated_when_registry_changes(self) -> None:
        retriever = LexicalRetriever()
        query = SearchQuery(task="design a database schema", top_k=3)
        first = retriever.search(self.registry, query)
        self.assertEqual(first[0].resource.metadata.id, "tool.db.designer")
        self.registry.add(_tool("tool.db.expert", "Expert database schema design with indexes and migrations."))
        second = retriever.search(self.registry, query)
        ids = [result.resource.metadata.id for result in second]
        self.assertIn("tool.db.expert", ids)

    def test_repeated_search_uses_cached_index(self) -> None:
        retriever = LexicalRetriever()
        query = SearchQuery(task="verify OKR quality", top_k=3)
        retriever.search(self.registry, query)
        start = time.perf_counter()
        for _ in range(50):
            retriever.search(self.registry, query)
        elapsed = time.perf_counter() - start
        self.assertLess(elapsed, 1.0)


class SemanticTests(unittest.TestCase):
    def test_hashing_embeddings_are_deterministic_and_normalized(self) -> None:
        provider = HashingEmbeddingProvider(dimensions=64)
        first, second = provider.embed(["read a file", "read a file"])
        self.assertEqual(first, second)
        norm = sum(value * value for value in first) ** 0.5
        self.assertAlmostEqual(norm, 1.0, places=6)

    def test_hybrid_retriever_adds_semantic_component(self) -> None:
        registry = ResourceRegistry()
        registry.add(_tool("tool.files.read", "Read a UTF-8 text file from disk."))
        registry.add(_tool("tool.web.fetch", "Fetch a web page over HTTP."))
        retriever = HybridRetriever(HashingEmbeddingProvider(dimensions=128), semantic_weight=0.5)
        results = retriever.search(registry, SearchQuery(task="read a text file", top_k=2))
        self.assertEqual(results[0].resource.metadata.id, "tool.files.read")
        self.assertIn("semantic", results[0].components)
        self.assertTrue(any(reason.startswith("semantic similarity") for reason in results[0].reasons))

    def test_hybrid_falls_back_to_lexical_without_task(self) -> None:
        registry = ResourceRegistry()
        registry.add(_tool("tool.files.read", "Read a text file.", tags=["file"]))
        retriever = HybridRetriever(HashingEmbeddingProvider(dimensions=64))
        results = retriever.search(registry, SearchQuery(tags=("file",), top_k=1))
        self.assertEqual(len(results), 1)

    def test_openai_embedding_provider_builds_request_offline(self) -> None:
        seen: dict = {}

        def transport(url, payload, headers, timeout):
            seen["url"] = url
            seen["payload"] = payload
            seen["headers"] = headers
            return {
                "data": [
                    {"index": index, "embedding": [0.1, 0.2]}
                    for index in range(len(payload["input"]))
                ]
            }

        provider = OpenAICompatibleEmbeddingProvider(api_key="sk-test", transport=transport)
        vectors = provider.embed(["hello", "world"])
        self.assertEqual(len(vectors), 2)
        self.assertTrue(seen["url"].endswith("/embeddings"))
        self.assertEqual(seen["headers"]["Authorization"], "Bearer sk-test")
        self.assertEqual(seen["payload"]["input"], ["hello", "world"])


class MCPTests(unittest.TestCase):
    def test_list_and_call_tools_via_fake_server(self) -> None:
        with MCPStdioClient([sys.executable, str(FAKE_SERVER)], timeout=10.0) as client:
            self.assertEqual(client.server_info.get("name"), "fake-server")
            tools = client.list_tools()
            self.assertEqual({tool.name for tool in tools}, {"echo", "add"})
            result = client.call_tool("add", {"a": 2, "b": 3})
            self.assertEqual(result["content"], "5")
            self.assertFalse(result["is_error"])

    def test_mcp_tools_run_through_kernel_with_policy_gate(self) -> None:
        client, definitions, implementations = connect_mcp_server(
            [sys.executable, str(FAKE_SERVER)],
            server_name="fake",
            side_effect="none",  # the fake server is local and side-effect free
            timeout=10.0,
        )
        try:
            registry = ResourceRegistry()
            registry.extend(definitions)
            kernel = Kernel(
                registry,
                MockLLMProvider(tool_arguments={"tool.mcp.fake.add": {"a": 2, "b": 3}}),
                policy_context=PolicyContext(granted_permissions=("mcp.fake",)),
                tool_implementations=implementations,
            )
            result = kernel.run_goal("add two numbers with the add tool")
            self.assertEqual(result.status, "completed")
            self.assertIn("5", result.output)
            state = kernel.get_state(result.task_id)
            self.assertEqual(state["status"], "completed")
            self.assertEqual(state["step_results"][0]["tool_id"], "tool.mcp.fake.add")
            self.assertIn("tool.mcp.fake.add@0.1.0", state["activated"])
            kinds = {record.kind for record in kernel.audit_log.records}
            self.assertLessEqual(
                {"retrieve", "policy", "activate", "compile", "llm", "execute", "task"},
                kinds,
            )
            self.assertEqual(kernel.audit_log.verify(), [])
            self.assertEqual(
                len({record.trace_id for record in kernel.audit_log.records}),
                1,
            )
        finally:
            client.close()

    def test_mcp_tools_are_blocked_without_permission(self) -> None:
        client, definitions, implementations = connect_mcp_server(
            [sys.executable, str(FAKE_SERVER)], server_name="fake", timeout=10.0
        )
        try:
            registry = ResourceRegistry()
            registry.extend(definitions)
            kernel = Kernel(
                registry,
                MockLLMProvider(),
                policy_context=PolicyContext(),  # no mcp.fake grant
                tool_implementations=implementations,
            )
            result = kernel.run_goal("add two numbers with the add tool")
            # Without the mcp.fake grant the tool must never activate or run;
            # the kernel finishes without it and the LLM answers unaided.
            self.assertNotIn("tool.mcp.fake", result.output)
            self.assertIn("No tool was required", result.output)
        finally:
            client.close()


class ProviderTests(unittest.TestCase):
    def test_anthropic_request_and_response_mapping(self) -> None:
        seen: dict = {}

        def transport(url, payload, headers, timeout):
            seen.update(url=url, payload=payload, headers=headers)
            return {
                "content": [
                    {"type": "text", "text": "calling the tool"},
                    {"type": "tool_use", "id": "toolu_1", "name": "add", "input": {"a": 1, "b": 2}},
                ],
                "stop_reason": "tool_use",
                "usage": {"input_tokens": 10, "output_tokens": 5},
            }

        provider = AnthropicLLMProvider(api_key="key", transport=transport)
        messages = [
            ChatMessage(role="system", content="be terse"),
            ChatMessage(role="user", content="add 1 and 2"),
        ]
        tools = [LLMToolSpec(name="add", description="add numbers", input_schema={"type": "object"})]
        response = provider.complete(messages, tools)

        self.assertTrue(seen["url"].endswith("/v1/messages"))
        self.assertEqual(seen["headers"]["x-api-key"], "key")
        self.assertEqual(seen["payload"]["system"], "be terse")
        self.assertEqual(seen["payload"]["messages"], [{"role": "user", "content": "add 1 and 2"}])
        self.assertEqual(seen["payload"]["tools"][0]["name"], "add")
        self.assertEqual(response.finish_reason, "tool_calls")
        self.assertEqual(response.tool_calls[0].arguments, {"a": 1, "b": 2})
        self.assertEqual(response.usage["input_tokens"], 10)

    def test_anthropic_tool_result_reconstructs_tool_use_id(self) -> None:
        provider = AnthropicLLMProvider(api_key="key", transport=lambda *args: {"content": []})
        messages = [
            ChatMessage(role="user", content="add"),
            ChatMessage(
                role="assistant",
                content="",
                tool_calls=(ToolCall(id="toolu_9", name="add", arguments={"a": 1, "b": 2}),),
            ),
            ChatMessage(role="tool", content='{"sum": 3}', name="add"),
        ]
        payload = provider.build_request(messages, ())
        tool_result = payload["messages"][2]["content"][0]
        self.assertEqual(tool_result["type"], "tool_result")
        self.assertEqual(tool_result["tool_use_id"], "toolu_9")

    def test_openai_request_and_response_mapping(self) -> None:
        seen: dict = {}

        def transport(url, payload, headers, timeout):
            seen.update(url=url, payload=payload, headers=headers)
            return {
                "choices": [
                    {
                        "finish_reason": "tool_calls",
                        "message": {
                            "content": None,
                            "tool_calls": [
                                {
                                    "id": "call_1",
                                    "type": "function",
                                    "function": {"name": "add", "arguments": '{"a": 1, "b": 2}'},
                                }
                            ],
                        },
                    }
                ],
                "usage": {"prompt_tokens": 7, "completion_tokens": 3},
            }

        provider = OpenAICompatibleLLMProvider(api_key="sk", transport=transport)
        response = provider.complete(
            [ChatMessage(role="user", content="add 1 and 2")],
            [LLMToolSpec(name="add", description="", input_schema={"type": "object"})],
        )
        self.assertTrue(seen["url"].endswith("/chat/completions"))
        self.assertEqual(seen["headers"]["Authorization"], "Bearer sk")
        self.assertEqual(seen["payload"]["tools"][0]["function"]["name"], "add")
        self.assertEqual(response.finish_reason, "tool_calls")
        self.assertEqual(response.tool_calls[0].arguments, {"a": 1, "b": 2})
        self.assertEqual(response.usage["input_tokens"], 7)


if __name__ == "__main__":
    unittest.main()
