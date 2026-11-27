"""Resource JSON round trip and one schema subset for load, defaults and validation."""

from __future__ import annotations

from pathlib import Path
import json
import subprocess
import sys
import tempfile
import unittest

from marmo_core import (
    ChatMessage,
    LLMToolSpec,
    MockLLMProvider,
    ResourceDefinition,
    ResourceValidationError,
    load_resource_definitions,
    validate_arguments,
)
from marmo_core.llm import default_arguments
from marmo_core.models import SCHEMA_TYPES

ROOT = Path(__file__).resolve().parents[1]

NULLABLE_SCHEMA = {
    "type": "object",
    "properties": {
        "city": {"type": ["string", "null"]},
        "limit": {"type": ["null", "integer"]},
        "note": {"type": "null"},
    },
    "required": ["city", "limit", "note"],
}


def _tool(input_schema: dict[str, object]) -> dict[str, object]:
    return {
        "id": "tool.example.lookup",
        "kind": "tool",
        "name": "Lookup",
        "version": "1.0.0",
        "description": "Look something up.",
        "capabilities": ["lookup"],
        "input_summary": "query",
        "output_summary": "result",
        "required_permissions": [],
        "cost_estimate": 0.0,
        "latency_class": "fast",
        "side_effect": "none",
        "trust_level": "verified",
        "ref": "python:json:dumps",
        "tags": ["lookup"],
        "input_schema": input_schema,
        "output_schema": {"type": "object"},
    }


class ResourceJsonRoundTripTests(unittest.TestCase):
    def test_published_dict_loads_back_with_its_extras_and_source(self) -> None:
        original = ResourceDefinition.from_mapping(_tool(NULLABLE_SCHEMA), source="resources/lookup.json#0")

        restored = ResourceDefinition.from_mapping(json.loads(json.dumps(original.to_dict())))

        self.assertEqual(restored.metadata, original.metadata)
        self.assertEqual(restored.extras, original.extras)
        self.assertEqual(restored.extras["input_schema"], NULLABLE_SCHEMA)
        self.assertEqual(restored.source, "resources/lookup.json#0")

    def test_explicit_source_wins_over_the_published_one(self) -> None:
        published = ResourceDefinition.from_mapping(_tool({}), source="old").to_dict()
        self.assertEqual(ResourceDefinition.from_mapping(published, source="new").source, "new")

    def test_extras_are_not_wrapped_when_to_dict_leaves_them_out(self) -> None:
        data = ResourceDefinition.from_mapping(_tool({})).to_dict(include_extras=False)
        self.assertEqual(ResourceDefinition.from_mapping(data).extras, {})

    def test_metadata_form_with_extras_wrapper_is_unwrapped(self) -> None:
        original = ResourceDefinition.from_mapping(_tool(NULLABLE_SCHEMA))
        nested = {"metadata": original.metadata.to_dict(), "extras": dict(original.extras)}
        self.assertEqual(ResourceDefinition.from_mapping(nested).extras, original.extras)

    def test_flat_input_form_is_unchanged(self) -> None:
        definition = ResourceDefinition.from_mapping(_tool(NULLABLE_SCHEMA))
        self.assertEqual(definition.extras["input_schema"], NULLABLE_SCHEMA)
        self.assertNotIn("extras", definition.extras)

    def test_cli_inspect_json_can_be_loaded_again(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            source = Path(temp_dir) / "lookup.json"
            source.write_text(json.dumps(_tool(NULLABLE_SCHEMA)), encoding="utf-8")
            inspected = subprocess.run(
                [
                    sys.executable, "-m", "marmo_core.cli", "inspect",
                    "--no-default-resources", "--format", "json", "tool.example.lookup", str(source),
                ],
                cwd=ROOT,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )
            self.assertEqual(inspected.returncode, 0, inspected.stderr)
            copy = Path(temp_dir) / "copy.json"
            copy.write_text(inspected.stdout, encoding="utf-8")
            (definition,) = load_resource_definitions([copy])
        self.assertEqual(definition.extras["input_schema"], NULLABLE_SCHEMA)


class SchemaSubsetTests(unittest.TestCase):
    def test_nullable_type_arrays_get_non_null_defaults(self) -> None:
        self.assertEqual(default_arguments(NULLABLE_SCHEMA), {"city": "", "limit": 0, "note": None})

    def test_mock_provider_builds_a_call_for_a_nullable_schema(self) -> None:
        spec = LLMToolSpec(name="lookup", description="", input_schema=NULLABLE_SCHEMA)
        response = MockLLMProvider().complete([ChatMessage(role="user", content="go")], [spec])
        self.assertEqual(response.tool_calls[0].arguments, {"city": "", "limit": 0, "note": None})

    def test_defaults_pass_validation_for_every_supported_type(self) -> None:
        for name in SCHEMA_TYPES:
            for declared in (name, [name], [name, "null"]):
                with self.subTest(declared=declared):
                    schema = {"type": "object", "properties": {"x": {"type": declared}}, "required": ["x"]}
                    self.assertEqual(validate_arguments(schema, default_arguments(schema)), [])

    def test_validation_accepts_any_listed_type_and_rejects_others(self) -> None:
        schema = {"type": "object", "properties": {"city": {"type": ["string", "null"]}}}
        self.assertEqual(validate_arguments(schema, {"city": None}), [])
        self.assertEqual(validate_arguments(schema, {"city": "Tokyo"}), [])
        self.assertEqual(
            validate_arguments(schema, {"city": 3}),
            ["argument city must be of type string or null"],
        )

    def test_unsupported_types_are_reported_when_validating_arguments(self) -> None:
        for bad in ("float", ["string", "decimal"], [], 5):
            with self.subTest(bad=bad):
                schema = {"type": "object", "properties": {"x": {"type": bad}}}
                issues = validate_arguments(schema, {"x": 1})
                self.assertEqual(len(issues), 1)
                self.assertIn("unsupported schema type", issues[0])

    def test_defaults_skip_properties_with_unsupported_types(self) -> None:
        schema = {"type": "object", "properties": {"x": {"type": "float"}}, "required": ["x"]}
        self.assertEqual(default_arguments(schema), {})
        self.assertEqual(validate_arguments(schema, {}), ["missing required argument: x"])

    def test_nullable_schema_is_valid_on_load(self) -> None:
        self.assertEqual(ResourceDefinition.from_mapping(_tool(NULLABLE_SCHEMA)).validate(), [])

    def test_unsupported_types_are_reported_on_validate_and_load(self) -> None:
        schema = {"type": "object", "properties": {"x": {"type": ["string", "decimal"]}, "y": {"type": "float"}}}
        issues = ResourceDefinition.from_mapping(_tool(schema), source="lookup.json").validate()
        self.assertEqual(
            sorted(issue.path for issue in issues),
            ["lookup.json.input_schema.properties.x.type", "lookup.json.input_schema.properties.y.type"],
        )
        with tempfile.TemporaryDirectory() as temp_dir:
            source = Path(temp_dir) / "lookup.json"
            source.write_text(json.dumps(_tool(schema)), encoding="utf-8")
            with self.assertRaisesRegex(ResourceValidationError, "unsupported schema type"):
                load_resource_definitions([source])


if __name__ == "__main__":
    unittest.main()
