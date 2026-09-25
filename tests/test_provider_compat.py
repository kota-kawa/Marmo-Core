"""Regression tests for running against real LLM APIs (tool names, parameters, errors)."""

from __future__ import annotations

from contextlib import redirect_stderr, redirect_stdout
from decimal import Decimal
from io import BytesIO, StringIO
from pathlib import Path
from unittest import mock
import json
import os
import tempfile
import unittest
import urllib.error

from marmo_core import (
    AnthropicLLMProvider,
    ChatMessage,
    ContextCompiler,
    Kernel,
    ModelPrice,
    LLMToolSpec,
    MockLLMProvider,
    OpenAICompatibleEmbeddingProvider,
    OpenAICompatibleLLMProvider,
    ProviderError,
    ProviderHTTPError,
    ResourceDefinition,
    ResourceRegistry,
    TaskBudget,
    ToolCall,
    ToolNameCodec,
)
from marmo_core.cli import main
from marmo_core.compiler import NO_TOOLS_SYSTEM_PROMPT
from marmo_core.kernel import NO_RESOURCE_MATCHED_DETAIL
from marmo_core import providers, semantic
from marmo_core.providers import DEFAULT_OPENAI_BASE_URL
from marmo_core.semantic import USER_AGENT, _post_json


def _tool(resource_id: str, description: str, *, permissions: tuple[str, ...] = ()) -> ResourceDefinition:
    return ResourceDefinition.from_mapping(
        {
            "id": resource_id,
            "kind": "tool",
            "name": resource_id,
            "version": "1.0.0",
            "description": description,
            "capabilities": [description],
            "input_summary": "Arguments.",
            "output_summary": "Result.",
            "required_permissions": list(permissions),
            "cost_estimate": 0.0,
            "latency_class": "fast",
            "side_effect": "none",
            "trust_level": "core",
            "ref": f"tool://{resource_id}",
            "tags": ["test"],
            "input_schema": {"type": "object", "properties": {}},
        }
    )


def _openai_tool_call_response(name: str) -> dict:
    return {
        "choices": [
            {
                "finish_reason": "tool_calls",
                "message": {
                    "content": None,
                    "tool_calls": [
                        {"id": "call_1", "type": "function", "function": {"name": name, "arguments": "{}"}}
                    ],
                },
            }
        ],
        "usage": {"prompt_tokens": 1, "completion_tokens": 1},
    }


class ToolNameCodecTests(unittest.TestCase):
    def test_dotted_resource_ids_become_provider_safe_and_round_trip(self) -> None:
        codec = ToolNameCodec()
        for original in ("tool.marmo.samples.read-text", "connector.file.read_text", "agent.x.y"):
            encoded = codec.encode(original)
            self.assertRegex(encoded, r"^[a-zA-Z0-9_-]{1,64}$")
            self.assertEqual(codec.decode(encoded), original)

    def test_collisions_and_long_names_stay_distinct_and_short(self) -> None:
        codec = ToolNameCodec()
        first = codec.encode("tool.a.b")
        second = codec.encode("tool.a_b")
        self.assertNotEqual(first, second)
        self.assertEqual(codec.decode(second), "tool.a_b")
        long_name = "tool." + ".".join(["segment"] * 12)
        encoded = codec.encode(long_name)
        self.assertLessEqual(len(encoded), 64)
        self.assertEqual(codec.decode(encoded), long_name)

    def test_unknown_names_decode_to_themselves(self) -> None:
        self.assertEqual(ToolNameCodec().decode("plain"), "plain")


class ProviderToolNameTests(unittest.TestCase):
    def test_budget_charges_reservation_when_openai_omits_usage(self) -> None:
        policy = TaskBudget(
            amount=Decimal("0.01"),
            currency="USD",
            resource_cost_unit="USD",
            model_price=ModelPrice(Decimal("1"), Decimal("1"), 1000, 1000),
        )
        for usage in (None, {"prompt_tokens": None, "completion_tokens": None}):
            with self.subTest(usage=usage):
                response = {"choices": [{"finish_reason": "stop", "message": {"content": "Done"}}]}
                if usage is not None:
                    response["usage"] = usage
                provider = OpenAICompatibleLLMProvider(
                    model="m", api_key="k", transport=lambda *args: response
                )
                kernel = Kernel(ResourceRegistry(), provider, task_budget=policy)

                result = kernel.run_goal("Say done")

                self.assertEqual(result.status, "completed", result.detail)
                self.assertEqual(kernel.budget_status(result.task_id)["spent"], "0.002")

    def test_openai_encodes_tool_names_and_decodes_calls(self) -> None:
        seen: list[dict] = []

        def transport(url, payload, headers, timeout):
            seen.append(payload)
            return _openai_tool_call_response(payload["tools"][0]["function"]["name"])

        provider = OpenAICompatibleLLMProvider(model="m", api_key="k", transport=transport)
        history = [
            ChatMessage(role="user", content="read it"),
            ChatMessage(
                role="assistant",
                content="",
                tool_calls=(ToolCall(id="call_0", name="tool.files.read-text", arguments={"path": "a"}),),
            ),
            ChatMessage(role="tool", content="{}", name="tool.files.read-text"),
        ]
        tools = [LLMToolSpec(name="tool.files.read-text", description="", input_schema={"type": "object"})]
        response = provider.complete(history, tools)

        wire_name = seen[0]["tools"][0]["function"]["name"]
        self.assertRegex(wire_name, r"^[a-zA-Z0-9_-]{1,64}$")
        self.assertEqual(seen[0]["messages"][1]["tool_calls"][0]["function"]["name"], wire_name)
        self.assertEqual(response.tool_calls[0].name, "tool.files.read-text")

    def test_anthropic_encodes_tool_names_and_decodes_calls(self) -> None:
        seen: list[dict] = []

        def transport(url, payload, headers, timeout):
            seen.append(payload)
            return {
                "content": [{"type": "tool_use", "id": "toolu_1", "name": payload["tools"][0]["name"], "input": {}}],
                "stop_reason": "tool_use",
                "usage": {"input_tokens": 1, "output_tokens": 1},
            }

        provider = AnthropicLLMProvider(model="m", api_key="k", max_tokens=64, transport=transport)
        history = [
            ChatMessage(role="user", content="read it"),
            ChatMessage(
                role="assistant",
                content="",
                tool_calls=(ToolCall(id="toolu_0", name="connector.file.read_text", arguments={}),),
            ),
            ChatMessage(role="tool", content="{}", name="connector.file.read_text"),
        ]
        tools = [LLMToolSpec(name="connector.file.read_text", description="", input_schema={"type": "object"})]
        response = provider.complete(history, tools)

        wire_name = seen[0]["tools"][0]["name"]
        self.assertRegex(wire_name, r"^[a-zA-Z0-9_-]{1,64}$")
        self.assertEqual(seen[0]["messages"][1]["content"][0]["name"], wire_name)
        self.assertEqual(response.tool_calls[0].name, "connector.file.read_text")


class OpenAIParameterTests(unittest.TestCase):
    def test_openai_endpoint_uses_max_completion_tokens(self) -> None:
        provider = OpenAICompatibleLLMProvider(model="m", api_key="k", transport=lambda *a: {"choices": []})
        payload = provider.build_request([ChatMessage(role="user", content="hi")], ())
        self.assertIn("max_completion_tokens", payload)
        self.assertNotIn("max_tokens", payload)

    def test_other_endpoints_keep_max_tokens(self) -> None:
        provider = OpenAICompatibleLLMProvider(
            model="m", api_key="k", base_url="http://localhost:11434/v1", transport=lambda *a: {"choices": []}
        )
        payload = provider.build_request([ChatMessage(role="user", content="hi")], ())
        self.assertIn("max_tokens", payload)
        self.assertNotIn("max_completion_tokens", payload)

    def test_base_url_comes_from_environment(self) -> None:
        with mock.patch.dict(os.environ, {"OPENAI_BASE_URL": "https://api.groq.com/openai/v1/"}):
            provider = OpenAICompatibleLLMProvider(model="m", api_key="k", transport=lambda *a: {"choices": []})
        self.assertEqual(provider.base_url, "https://api.groq.com/openai/v1")
        self.assertEqual(provider.max_tokens_parameter, "max_tokens")

    def test_explicit_parameter_is_validated(self) -> None:
        with self.assertRaises(ValueError):
            OpenAICompatibleLLMProvider(model="m", api_key="k", max_tokens_parameter="tokens")

    def test_unsupported_parameter_switches_once_and_retries(self) -> None:
        payloads: list[dict] = []
        body = json.dumps(
            {
                "error": {
                    "message": "Unsupported parameter: 'max_tokens' is not supported with this model. "
                    "Use 'max_completion_tokens' instead.",
                    "param": "max_tokens",
                }
            }
        )

        def transport(url, payload, headers, timeout):
            payloads.append(payload)
            if "max_tokens" in payload:
                raise ProviderHTTPError(message="HTTP 400", status=400, body=body, url=url)
            return {"choices": [{"finish_reason": "stop", "message": {"content": "ok"}}]}

        provider = OpenAICompatibleLLMProvider(
            model="m", api_key="k", base_url="https://example.test/v1", transport=transport
        )
        response = provider.complete([ChatMessage(role="user", content="hi")], ())

        self.assertEqual(response.content, "ok")
        self.assertEqual([("max_tokens" in p, "max_completion_tokens" in p) for p in payloads], [(True, False), (False, True)])
        self.assertEqual(provider.max_tokens_parameter, "max_completion_tokens")

    def test_unrelated_errors_are_not_retried(self) -> None:
        calls = 0

        def transport(url, payload, headers, timeout):
            nonlocal calls
            calls += 1
            raise ProviderHTTPError(message="HTTP 401", status=401, body='{"error":{"message":"bad key"}}', url=url)

        provider = OpenAICompatibleLLMProvider(model="m", api_key="k", transport=transport)
        with self.assertRaises(ProviderHTTPError):
            provider.complete([ChatMessage(role="user", content="hi")], ())
        self.assertEqual(calls, 1)


class TransportErrorTests(unittest.TestCase):
    def test_http_errors_carry_status_and_api_message(self) -> None:
        body = json.dumps({"error": {"message": "Invalid 'tools[0].function.name': bad pattern"}}).encode()
        error = urllib.error.HTTPError("https://api.test/v1", 400, "Bad Request", {}, BytesIO(body))
        with mock.patch("urllib.request.urlopen", side_effect=error):
            with self.assertRaises(ProviderHTTPError) as caught:
                _post_json("https://api.test/v1", {"a": 1}, {"Content-Type": "application/json"}, 1.0)
        error.close()
        self.assertEqual(caught.exception.status, 400)
        self.assertIn("Invalid 'tools[0].function.name'", str(caught.exception))
        self.assertIn("HTTP 400", str(caught.exception))

    def test_network_errors_become_provider_errors(self) -> None:
        with mock.patch("urllib.request.urlopen", side_effect=urllib.error.URLError("refused")):
            with self.assertRaises(ProviderError) as caught:
                _post_json("https://api.test/v1", {}, {}, 1.0)
        self.assertIn("refused", str(caught.exception))

    def test_requests_identify_the_client(self) -> None:
        seen: list = []

        class _Response:
            def __enter__(self):
                return self

            def __exit__(self, *args):
                return False

            def read(self):
                return b"{}"

        def fake_urlopen(request, timeout):
            seen.append(request)
            return _Response()

        with mock.patch("urllib.request.urlopen", fake_urlopen):
            _post_json("https://api.test/v1", {}, {"Authorization": "Bearer x"}, 1.0)
        self.assertEqual(seen[0].get_header("User-agent"), USER_AGENT)
        self.assertEqual(seen[0].get_header("Authorization"), "Bearer x")


class KernelSelectionTests(unittest.TestCase):
    def test_answer_without_matching_resource_is_flagged_in_detail(self) -> None:
        registry = ResourceRegistry()
        registry.add(_tool("tool.spreadsheet.sum", "Sum a column of a spreadsheet."))
        kernel = Kernel(registry, MockLLMProvider(), tool_implementations={"tool.spreadsheet.sum": lambda: {}})
        result = kernel.run_goal("Translate bonjour into English")
        self.assertTrue(result.completed)
        self.assertEqual(result.detail, NO_RESOURCE_MATCHED_DETAIL)

    def test_empty_registry_completion_has_no_detail(self) -> None:
        result = Kernel(ResourceRegistry(), MockLLMProvider()).run_goal("Say hello")
        self.assertTrue(result.completed)
        self.assertEqual(result.detail, "")

    def test_matching_tool_run_has_no_detail(self) -> None:
        registry = ResourceRegistry()
        registry.add(_tool("tool.greeting.say", "Say hello to a person."))
        kernel = Kernel(registry, MockLLMProvider(), tool_implementations={"tool.greeting.say": lambda: {"ok": True}})
        result = kernel.run_goal("Say hello to a person")
        self.assertTrue(result.completed)
        self.assertEqual(result.detail, "")
        self.assertEqual([item.tool_id for item in result.tool_results], ["tool.greeting.say"])

    def test_several_tools_are_selected_for_one_goal(self) -> None:
        registry = ResourceRegistry()
        registry.add(_tool("tool.files.list", "List text files in a directory."))
        registry.add(_tool("tool.files.read", "Read a text file from a directory."))
        kernel = Kernel(registry, MockLLMProvider())
        kernel.run_goal("List the text files in the directory and read each file")
        retrieve = next(record for record in kernel.audit_log.records if record.kind == "retrieve")
        self.assertEqual(
            sorted(retrieve.payload["selected"]), ["tool.files.list@1.0.0", "tool.files.read@1.0.0"]
        )

    def test_denied_fill_in_tools_are_not_selected_but_a_denied_best_match_is_reported(self) -> None:
        registry = ResourceRegistry()
        registry.add(_tool("tool.files.list", "List text files in a directory."))
        registry.add(_tool("tool.files.write", "Write text files in a directory.", permissions=("fs.write",)))
        kernel = Kernel(registry, MockLLMProvider(), tool_implementations={"tool.files.list": lambda: {"files": []}})
        result = kernel.run_goal("List the text files in a directory")
        self.assertEqual(result.skipped_resources, ())
        retrieve = next(record for record in kernel.audit_log.records if record.kind == "retrieve")
        self.assertEqual(retrieve.payload["selected"], ["tool.files.list@1.0.0"])

        only_denied = ResourceRegistry()
        only_denied.add(_tool("tool.files.write", "Write text files in a directory.", permissions=("fs.write",)))
        result = Kernel(only_denied, MockLLMProvider()).run_goal("Write text files in a directory")
        self.assertEqual([item["resource"] for item in result.skipped_resources], ["tool.files.write@1.0.0"])


class CompilerNoToolsTests(unittest.TestCase):
    def test_prompt_states_when_no_tools_exist(self) -> None:
        compiler = ContextCompiler()
        without = compiler.compile_execution("hello")
        self.assertIn(NO_TOOLS_SYSTEM_PROMPT, without.system_prompt)
        self.assertEqual(without.tools, ())


class CliRealProviderTests(unittest.TestCase):
    def test_version_flag(self) -> None:
        output = StringIO()
        with redirect_stdout(output), self.assertRaises(SystemExit) as exit_info:
            main(["--version"])
        self.assertEqual(exit_info.exception.code, 0)
        self.assertIn("marmo-core", output.getvalue())

    def test_strict_run_fails_when_no_resource_matches(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "tool.json"
            path.write_text(json.dumps(_tool("tool.spreadsheet.sum", "Sum a spreadsheet column.").to_dict()), "utf-8")
            output = StringIO()
            with redirect_stdout(output):
                status = main(["run", str(path), "--task", "Translate bonjour", "--strict", "--format", "json"])
        payload = json.loads(output.getvalue())
        self.assertEqual(status, 1)
        self.assertEqual(payload["status"], "completed")
        self.assertTrue(any("no resource matched" in item for item in payload["strict_violations"]))

    def test_list_in_empty_directory_explains_itself(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            stdout, stderr = StringIO(), StringIO()
            with redirect_stdout(stdout), redirect_stderr(stderr):
                status = main(["list", directory])
        self.assertEqual(status, 0)
        self.assertIn("no resource definitions were found", stderr.getvalue())

    def test_real_llm_choice_reads_configuration_from_environment(self) -> None:
        with mock.patch.dict(os.environ, {"OPENAI_MODEL": "", "OPENAI_API_KEY": "k"}, clear=False):
            os.environ.pop("OPENAI_MODEL")
            with mock.patch("marmo_core.environment.load_local_dotenv", lambda: None), mock.patch(
                "marmo_core.providers.load_local_dotenv", lambda: None
            ):
                stderr = StringIO()
                with redirect_stderr(stderr):
                    status = main(["run", "--task", "x", "--no-default-resources", "--llm", "openai"])
        self.assertEqual(status, 2)
        self.assertIn("OPENAI_MODEL", stderr.getvalue())


class EmbeddingEndpointTests(unittest.TestCase):
    """The embedding provider must follow OPENAI_BASE_URL like the LLM provider."""

    def test_base_url_comes_from_environment(self) -> None:
        with mock.patch.dict(os.environ, {"OPENAI_BASE_URL": "https://api.groq.com/openai/v1/"}):
            provider = OpenAICompatibleEmbeddingProvider(
                model="m", api_key="k", transport=lambda *a: {"data": []}
            )
        self.assertEqual(provider.base_url, "https://api.groq.com/openai/v1")

    def test_configured_endpoint_receives_the_request_not_openai(self) -> None:
        seen: list[str] = []

        def transport(url, payload, headers, timeout):
            seen.append(url)
            return {"data": [{"index": 0, "embedding": [0.0]}]}

        with mock.patch.dict(os.environ, {"OPENAI_BASE_URL": "https://api.groq.com/openai/v1"}):
            provider = OpenAICompatibleEmbeddingProvider(model="m", api_key="k", transport=transport)
            provider.embed(["hello"])

        self.assertEqual(seen, ["https://api.groq.com/openai/v1/embeddings"])
        self.assertNotIn("api.openai.com", seen[0])

    def test_explicit_base_url_wins_over_environment(self) -> None:
        with mock.patch.dict(os.environ, {"OPENAI_BASE_URL": "https://api.groq.com/openai/v1"}):
            provider = OpenAICompatibleEmbeddingProvider(
                model="m", api_key="k", base_url="http://localhost:11434/v1/", transport=lambda *a: {"data": []}
            )
        self.assertEqual(provider.base_url, "http://localhost:11434/v1")

    def test_openai_is_the_last_resort_default(self) -> None:
        # semantic.py holds its own reference to load_local_dotenv, so patching
        # only marmo_core.environment lets a developer's .env decide the result.
        with mock.patch.dict(os.environ, {"OPENAI_BASE_URL": ""}):
            os.environ.pop("OPENAI_BASE_URL")
            with (
                mock.patch("marmo_core.environment.load_local_dotenv", lambda: None),
                mock.patch("marmo_core.semantic.load_local_dotenv", lambda: None),
            ):
                provider = OpenAICompatibleEmbeddingProvider(
                    model="m", api_key="k", transport=lambda *a: {"data": []}
                )
        self.assertEqual(provider.base_url, DEFAULT_OPENAI_BASE_URL)

    def test_the_endpoint_default_has_a_single_source(self) -> None:
        self.assertIs(providers.DEFAULT_OPENAI_BASE_URL, semantic.DEFAULT_OPENAI_BASE_URL)


class MissingApiKeyHintTests(unittest.TestCase):
    """A 401/403 with no key configured must say so instead of only echoing the server."""

    @staticmethod
    def _rejecting_transport(status: int):
        def transport(url, payload, headers, timeout):
            raise ProviderHTTPError(
                message=f"HTTP {status} from {url}: Invalid API Key",
                status=status,
                body='{"error":{"message":"Invalid API Key"}}',
                url=url,
            )

        return transport

    def test_unauthorized_without_a_key_explains_the_cause(self) -> None:
        for status in (401, 403):
            with self.subTest(status=status):
                provider = OpenAICompatibleLLMProvider(
                    model="m", api_key="", base_url="https://example.test/v1",
                    transport=self._rejecting_transport(status),
                )
                with self.assertRaises(ProviderHTTPError) as caught:
                    provider.complete([ChatMessage(role="user", content="hi")], ())
                message = str(caught.exception)
                self.assertIn("no API key was sent", message)
                self.assertIn("OPENAI_API_KEY", message)
                self.assertIn("Invalid API Key", message)  # the server's own words survive
                self.assertEqual(caught.exception.status, status)

    def test_unauthorized_with_a_key_is_left_alone(self) -> None:
        provider = OpenAICompatibleLLMProvider(
            model="m", api_key="k", base_url="https://example.test/v1",
            transport=self._rejecting_transport(401),
        )
        with self.assertRaises(ProviderHTTPError) as caught:
            provider.complete([ChatMessage(role="user", content="hi")], ())
        self.assertNotIn("no API key was sent", str(caught.exception))

    def test_other_statuses_are_left_alone(self) -> None:
        provider = OpenAICompatibleLLMProvider(
            model="m", api_key="", base_url="https://example.test/v1",
            transport=self._rejecting_transport(429),
        )
        with self.assertRaises(ProviderHTTPError) as caught:
            provider.complete([ChatMessage(role="user", content="hi")], ())
        self.assertNotIn("no API key was sent", str(caught.exception))

    def test_the_embedding_provider_gets_the_same_hint(self) -> None:
        provider = OpenAICompatibleEmbeddingProvider(
            model="m", api_key="", base_url="https://example.test/v1",
            transport=self._rejecting_transport(401),
        )
        with self.assertRaises(ProviderHTTPError) as caught:
            provider.embed(["hello"])
        self.assertIn("OPENAI_API_KEY", str(caught.exception))


class ErrorBodyRedactionTests(unittest.TestCase):
    """Provider error bodies echo credentials; they must not reach logs or stderr."""

    def _error_from_body(self, body: str) -> ProviderHTTPError:
        error = urllib.error.HTTPError(
            "https://api.openai.com/v1/chat/completions", 401, "Unauthorized", {}, BytesIO(body.encode())
        )
        with mock.patch("urllib.request.urlopen", side_effect=error):
            with self.assertRaises(ProviderHTTPError) as caught:
                _post_json("https://api.openai.com/v1/chat/completions", {}, {}, 1.0)
        error.close()
        return caught.exception

    def test_masked_groq_key_echoed_by_openai_is_redacted(self) -> None:
        key = "gsk_AbCd" + "*" * 44 + "Wxyz"
        body = json.dumps({"error": {"message": f"Incorrect API key provided: {key}. You can find..."}})
        caught = self._error_from_body(body)
        self.assertNotIn(key, str(caught))
        self.assertNotIn(key, caught.body)
        self.assertIn("Incorrect API key provided", str(caught))

    def test_gateway_prose_about_bearer_auth_survives(self) -> None:
        for message in (
            "Missing Bearer authentication credentials in the request",
            "Bearer token_is_missing_entirely",
        ):
            with self.subTest(message=message):
                caught = self._error_from_body(json.dumps({"error": {"message": message}}))

                self.assertIn(message, str(caught))

    def test_whole_credentials_are_redacted(self) -> None:
        for key in ("gsk_" + "a" * 52, "sk-" + "b" * 48, "Bearer " + "c" * 40):
            with self.subTest(key=key):
                caught = self._error_from_body(json.dumps({"error": {"message": f"rejected {key}"}}))
                self.assertNotIn(key.split()[-1], str(caught))
                self.assertIn("rejected", str(caught))

    def test_ordinary_error_text_survives(self) -> None:
        body = json.dumps({"error": {"message": "Invalid 'tools[0].function.name': bad pattern", "param": "tools"}})
        caught = self._error_from_body(body)
        self.assertIn("Invalid 'tools[0].function.name'", str(caught))
        self.assertEqual(json.loads(caught.body)["error"]["param"], "tools")


if __name__ == "__main__":
    unittest.main()
