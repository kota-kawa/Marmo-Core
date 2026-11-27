"""Importing OpenAI / Anthropic / MCP function definitions as Tool resources."""

from __future__ import annotations

import unittest

from marmo_core import (
    LexicalRetriever,
    PolicyContext,
    PolicyGateway,
    ResourceRegistry,
    SearchQuery,
    function_tool_resources,
    validate_arguments,
)
from marmo_core.llm import default_arguments

WEATHER = {
    "type": "function",
    "function": {
        "name": "get_weather",
        "description": "Current weather for a city",
        "parameters": {
            "type": "object",
            "properties": {"city": {"type": "string", "description": "City name"}},
            "required": ["city"],
        },
    },
}
EMAIL = {"name": "send_email", "description": "Send an email", "input_schema": {"type": "object", "properties": {"to": {}}}}
FILES = {
    "name": "list_files",
    "description": "List files in a folder",
    "inputSchema": {"type": "object", "properties": {}},
    "outputSchema": {"type": "object", "properties": {"files": {"type": "array", "description": "file names"}}},
}


class FunctionToolResourcesTests(unittest.TestCase):
    def test_every_supported_shape_becomes_a_valid_tool(self) -> None:
        definitions = function_tool_resources([WEATHER, EMAIL, FILES], namespace="My App")
        self.assertEqual(
            [d.identity for d in definitions],
            ["tool.my-app.get-weather@0.1.0", "tool.my-app.send-email@0.1.0", "tool.my-app.list-files@0.1.0"],
        )
        for definition in definitions:
            self.assertEqual(definition.validate(), [])
        weather, _, files = definitions
        self.assertEqual(weather.metadata.input_summary, "city (required): City name")
        self.assertEqual(weather.extras["input_schema"], WEATHER["function"]["parameters"])
        self.assertEqual(files.metadata.output_summary, "files: file names")
        self.assertIn("output_schema", files.extras)

    def test_nullable_type_arrays_import_and_get_default_arguments(self) -> None:
        nullable = {
            "name": "find_user",
            "description": "Find a user",
            "inputSchema": {
                "type": "object",
                "properties": {"email": {"type": ["string", "null"]}},
                "required": ["email"],
            },
        }
        (definition,) = function_tool_resources([nullable], namespace="crm")
        self.assertEqual(definition.validate(), [])
        arguments = default_arguments(definition.extras["input_schema"])
        self.assertEqual(arguments, {"email": ""})
        self.assertEqual(validate_arguments(definition.extras["input_schema"], arguments), [])

    def test_defaults_are_conservative_and_need_an_explicit_grant(self) -> None:
        (weather,) = function_tool_resources([WEATHER], namespace="app")
        self.assertEqual(weather.metadata.trust_level, "community")
        self.assertEqual(weather.metadata.side_effect, "external")
        self.assertEqual(weather.metadata.required_permissions, ("tools.app",))
        gateway = PolicyGateway()
        decision = gateway.evaluate(weather, PolicyContext(), gate="activation")
        self.assertNotEqual(decision.verdict, "allow")
        self.assertEqual(decision.missing_permissions, ("tools.app",))
        (open_tool,) = function_tool_resources(
            [WEATHER], namespace="app", trust_level="verified", side_effect="read", required_permissions=()
        )
        self.assertEqual(open_tool.metadata.required_permissions, ())

    def test_search_finds_imported_functions(self) -> None:
        registry = ResourceRegistry()
        for definition in function_tool_resources([WEATHER, EMAIL, FILES], namespace="app"):
            registry.add(definition)
        results = LexicalRetriever().search(registry, SearchQuery(task="what is the weather in Paris", top_k=1))
        self.assertEqual([r.resource.metadata.id for r in results], ["tool.app.get-weather"])

    def test_names_without_ascii_get_distinct_stable_ids(self) -> None:
        first, second = function_tool_resources([{"name": "天気を調べる"}, {"name": "メールを送る"}], namespace="社内")
        self.assertNotEqual(first.metadata.id, second.metadata.id)
        self.assertEqual(first.metadata.id, function_tool_resources([{"name": "天気を調べる"}], namespace="社内")[0].metadata.id)
        self.assertEqual(first.validate(), [])

    def test_invalid_or_colliding_specs_raise(self) -> None:
        with self.assertRaises(ValueError):
            function_tool_resources([{"description": "no name"}], namespace="app")
        with self.assertRaises(ValueError):
            function_tool_resources(["not an object"], namespace="app")  # type: ignore[list-item]
        with self.assertRaises(ValueError):
            function_tool_resources([{"name": "get weather"}, {"name": "get-weather"}], namespace="app")


if __name__ == "__main__":
    unittest.main()
