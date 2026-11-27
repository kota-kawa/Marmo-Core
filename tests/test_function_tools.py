"""Importing OpenAI / Anthropic / MCP function definitions as Tool resources."""

from __future__ import annotations

from typing import Annotated, Any, Literal, Optional
import unittest

from marmo_core import (
    FunctionToolkit,
    Kernel,
    LexicalRetriever,
    MockLLMProvider,
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


class FunctionToolkitTests(unittest.TestCase):
    def test_signature_and_docstring_become_the_tool_definition(self) -> None:
        crm = FunctionToolkit("CRM")

        @crm.tool
        def find_customer(
            email: Annotated[str, "Customer email address"],
            limit: int = 5,
            tier: Literal["free", "paid"] = "free",
            tags: list[str] | None = None,
            filters: Optional[dict[str, Any]] = None,
            score: float | int = 0,
            exact: bool = False,
            extra=None,
        ) -> list[dict[str, Any]]:
            """Look up customers
            by email address.

            Returns the newest first.
            """

            return []

        (definition,) = crm.resources
        self.assertEqual(definition.validate(), [])
        self.assertEqual(definition.identity, "tool.crm.find-customer@0.1.0")
        self.assertEqual(definition.metadata.description, "Look up customers by email address.")
        self.assertEqual(
            (definition.metadata.trust_level, definition.metadata.side_effect, definition.metadata.required_permissions),
            ("community", "external", ("tools.crm",)),
        )
        self.assertEqual(
            definition.extras["input_schema"],
            {
                "type": "object",
                "properties": {
                    "email": {"type": "string", "description": "Customer email address"},
                    "limit": {"type": "integer"},
                    "tier": {"type": "string", "enum": ["free", "paid"]},
                    "tags": {"type": ["array", "null"]},
                    "filters": {"type": ["object", "null"]},
                    "score": {"type": ["number", "integer"]},
                    "exact": {"type": "boolean"},
                    "extra": {},
                },
                "additionalProperties": False,
                "required": ["email"],
            },
        )
        self.assertIn("email (required): Customer email address", definition.metadata.input_summary)
        self.assertEqual(crm.implementations, {"tool.crm.find-customer@0.1.0": find_customer})
        self.assertEqual(find_customer("a@example.com"), [])

    def test_options_override_the_toolkit_defaults_for_one_function(self) -> None:
        crm = FunctionToolkit("crm", side_effect="read", trust_level="verified", version="2.0.0")

        @crm.tool(name="send-email", description="Send an email.", side_effect="external", required_permissions=["mail.send"])
        def deliver(to: str) -> str:
            return to

        @crm.tool
        def count_customers() -> int:
            """Count the customers."""

            return 0

        @crm.tool
        def tag_customer(note: Optional[Annotated[str, "ignored inside a union"]] = None, value: Optional[Any] = None) -> None:
            """Tag a customer."""

        sent, counted, tagged = crm.resources
        self.assertEqual(tagged.extras["input_schema"]["properties"], {"note": {"type": ["string", "null"]}, "value": {}})
        self.assertEqual(sent.identity, "tool.crm.send-email@2.0.0")
        self.assertEqual((sent.metadata.side_effect, sent.metadata.required_permissions), ("external", ("mail.send",)))
        self.assertEqual((counted.metadata.side_effect, counted.metadata.trust_level), ("read", "verified"))
        self.assertEqual(counted.extras["input_schema"], {"type": "object", "properties": {}, "additionalProperties": False})

    def test_functions_that_cannot_be_described_or_called_by_keyword_are_refused(self) -> None:
        crm = FunctionToolkit("crm")

        def undocumented(email: str) -> None:
            return None

        def variadic(*emails: str) -> None:
            """Look up customers."""

        def keywords(**fields: str) -> None:
            """Look up customers."""

        def positional(email: str, /) -> None:
            """Look up customers."""

        def custom(when: complex) -> None:
            """Look up customers."""

        async def asynchronous(email: str) -> None:
            """Look up customers."""

        def unresolved(email: "NoSuchType") -> None:  # noqa: F821 - the unresolvable name is the case under test
            """Look up customers."""

        for function in (undocumented, variadic, keywords, positional, custom, asynchronous, unresolved):
            with self.subTest(function=function.__name__), self.assertRaises(ValueError):
                crm.tool(function)
        self.assertEqual(crm.resources, [])

        @crm.tool
        def lookup(email: str) -> None:
            """Look up customers."""

        with self.assertRaisesRegex(ValueError, "already registered"):
            crm.tool(name="lookup", description="Again.")(undocumented)

    def test_kernel_runs_a_decorated_function_through_the_gates(self) -> None:
        crm = FunctionToolkit("crm", side_effect="read")
        seen: list[str] = []

        @crm.tool
        def find_customer(email: str) -> dict[str, str]:
            """Look up a customer by email address."""

            seen.append(email)
            return {"email": email, "name": "Ada"}

        registry = ResourceRegistry()
        registry.extend(crm.resources)

        def run(context: PolicyContext):
            llm = MockLLMProvider(tool_arguments={"tool.crm.find-customer": {"email": "ada@example.com"}})
            kernel = Kernel(registry, llm, policy_context=context, tool_implementations=crm.implementations)
            return kernel.run_goal("look up a customer by email address")

        self.assertEqual(run(PolicyContext()).tool_results, ())
        self.assertEqual(seen, [])
        result = run(PolicyContext(granted_permissions=("tools.crm",)))
        self.assertEqual(result.status, "completed")
        self.assertEqual([r.output for r in result.tool_results], [{"email": "ada@example.com", "name": "Ada"}])
        self.assertEqual(seen, ["ada@example.com"])


if __name__ == "__main__":
    unittest.main()
