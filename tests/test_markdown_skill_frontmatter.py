"""Regression tests for SKILL.md frontmatter parsing and JSON discovery errors."""

from __future__ import annotations

from pathlib import Path
import json
import tempfile
import unittest

from marmo_core import load_registry
from marmo_core.errors import ResourceValidationError
from marmo_core.loader import load_resource_definitions, validate_resource_paths
from marmo_core.markdown_skill import load_markdown_skill, parse_frontmatter
from marmo_core.package import write_package_lock


def _write_skill(directory: Path, frontmatter: str) -> Path:
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / "SKILL.md"
    path.write_text(f"---\n{frontmatter}\n---\n\n# Skill\n\nBody text.\n", encoding="utf-8")
    return path


class BlockScalarFrontmatterTests(unittest.TestCase):
    def test_folded_block_scalar_with_chomping_keeps_continuation_lines(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            skill_path = _write_skill(
                Path(temp_dir) / "skills" / "sast-ssrf",
                "name: sast-ssrf\n"
                "description: >-\n"
                "  Detect Server-Side Request Forgery (SSRF) vulnerabilities in a codebase\n"
                "  using a three-phase approach: recon, verify, report.",
            )

            definition = load_markdown_skill(skill_path, root=Path(temp_dir))

        self.assertEqual(
            definition.metadata.description,
            "Detect Server-Side Request Forgery (SSRF) vulnerabilities in a codebase "
            "using a three-phase approach: recon, verify, report.",
        )
        self.assertEqual(sorted(definition.extras["frontmatter"]), ["description", "name"])

    def test_literal_block_scalar_variants_are_parsed(self) -> None:
        for header in ("|", "|-", "|+", ">", ">-", ">+"):
            with self.subTest(header=header):
                frontmatter, _ = parse_frontmatter(
                    f"---\nname: demo\ndescription: {header}\n  First line: with a colon\n  Second line.\n---\n\nBody\n"
                )

                self.assertEqual(sorted(frontmatter), ["description", "name"])
                self.assertIn("First line: with a colon", str(frontmatter["description"]))
                self.assertIn("Second line.", str(frontmatter["description"]))

    def test_block_scalar_list_item_lines_stay_inside_the_value(self) -> None:
        frontmatter, _ = parse_frontmatter(
            "---\ndescription: >-\n  Steps:\n  - recon\n  - verify\ntags: [a, b]\n---\n\nBody\n"
        )

        self.assertIsInstance(frontmatter["description"], str)
        self.assertIn("- recon", str(frontmatter["description"]))
        self.assertEqual(frontmatter["tags"], ["a", "b"])

    def test_bundled_skills_never_expose_a_block_scalar_marker_as_description(self) -> None:
        skills_root = Path(__file__).resolve().parents[1] / "resources" / "skills"
        if not skills_root.is_dir():
            self.skipTest("bundled skills are not available in this checkout")

        registry = load_registry([skills_root])
        markers = {">", ">-", ">+", "|", "|-", "|+", ""}
        broken = [item.metadata.id for item in registry.list() if item.metadata.description.strip() in markers]

        self.assertEqual(broken, [])


def _tool_resource() -> dict:
    return {
        "id": "tool.demo.thing",
        "kind": "tool",
        "name": "Thing",
        "version": "1.0.0",
        "description": "Do a thing for the loader tests.",
        "capabilities": ["thing"],
        "input_summary": "nothing",
        "output_summary": "nothing",
        "required_permissions": [],
        "cost_estimate": 0.0,
        "latency_class": "fast",
        "side_effect": "none",
        "trust_level": "core",
        "ref": "tool://demo/thing",
        "tags": ["demo"],
        "input_schema": {"type": "object", "properties": {}},
    }


class MalformedJsonDiscoveryTests(unittest.TestCase):
    def test_malformed_json_found_in_a_directory_is_reported(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            broken = Path(temp_dir) / "broken.json"
            broken.write_text("{ this is not json", encoding="utf-8")

            issues = validate_resource_paths([temp_dir])

        warnings = [issue for issue in issues if issue.severity == "warning"]
        self.assertTrue(
            any("invalid JSON in" in issue.message and "broken.json" in issue.path for issue in warnings)
        )
        self.assertEqual([issue for issue in issues if issue.severity == "error"], [])

    def test_malformed_json_named_explicitly_is_still_an_error(self) -> None:
        # Naming the file is a statement that it is a resource, so guessing is
        # no longer needed and silence would be wrong.
        with tempfile.TemporaryDirectory() as temp_dir:
            broken = Path(temp_dir) / "broken.json"
            broken.write_text("{ this is not json", encoding="utf-8")

            with self.assertRaisesRegex(ResourceValidationError, "invalid JSON in"):
                load_resource_definitions([broken])

    def test_a_directory_with_unparsable_json_still_loads_its_resources(self) -> None:
        # JSON with comments and trailing commas is everywhere in a real
        # workspace; refusing the whole directory over one of them would make
        # the loader unusable outside a curated resource folder.
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "resources").mkdir()
            (root / "resources" / "tool.json").write_text(json.dumps(_tool_resource()), encoding="utf-8")
            (root / "tsconfig.json").write_text('{ // strict mode\n  "strict": true, }', encoding="utf-8")
            (root / ".vscode").mkdir()
            (root / ".vscode" / "settings.json").write_text("{ // comment\n}", encoding="utf-8")
            (root / "empty.json").write_text("", encoding="utf-8")

            definitions = load_resource_definitions([temp_dir])
            issues = validate_resource_paths([temp_dir])

        self.assertEqual([item.id for item in definitions], ["tool.demo.thing"])
        self.assertEqual([issue for issue in issues if issue.severity == "error"], [])
        self.assertEqual(len([issue for issue in issues if issue.severity == "warning"]), 3)

    def test_a_byte_order_mark_does_not_make_a_resource_unreadable(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "tool.json"
            path.write_text(json.dumps(_tool_resource()), encoding="utf-8-sig")

            definitions = load_resource_definitions([temp_dir])

        self.assertEqual([item.id for item in definitions], ["tool.demo.thing"])

    def test_an_undecodable_json_file_is_reported_not_raised(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            (Path(temp_dir) / "utf16.json").write_bytes(json.dumps({"id": "x"}).encode("utf-16"))

            issues = validate_resource_paths([temp_dir])
            definitions = load_resource_definitions([temp_dir])

        self.assertEqual(definitions, [])
        self.assertEqual([issue.severity for issue in issues], ["warning"])

    def test_valid_non_resource_json_is_still_skipped(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            (Path(temp_dir) / "package.json").write_text(
                json.dumps({"name": "demo", "version": "1.0.0"}), encoding="utf-8"
            )
            (Path(temp_dir) / "tsconfig.json").write_text(
                json.dumps({"compilerOptions": {"strict": True}}), encoding="utf-8"
            )

            issues = validate_resource_paths([temp_dir])
            definitions = load_resource_definitions([temp_dir])

        self.assertEqual(issues, [])
        self.assertEqual(definitions, [])

    def test_a_markdown_skill_bundle_with_unparsable_assets_still_loads(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            bundle = Path(temp_dir) / "skills" / "demo"
            _write_skill(bundle, "name: demo\ndescription: A demo skill bundle.")
            (bundle / "assets").mkdir()
            (bundle / "assets" / "config.json").write_text("{ // a comment\n}", encoding="utf-8")

            issues = validate_resource_paths([temp_dir])
            definitions = load_resource_definitions([temp_dir])

        self.assertEqual([issue for issue in issues if issue.severity == "error"], [])
        self.assertEqual([item.kind for item in definitions], ["skill"])


class PackagedMarkdownSkillNamespaceTests(unittest.TestCase):
    def _write_package(self, root: Path) -> None:
        root.mkdir(parents=True)
        (root / "marmo-package.json").write_text(
            json.dumps(
                {
                    "schema_version": 1,
                    "namespace": "com.example",
                    "name": "operations",
                    "version": "1.2.0",
                    "description": "Operations resources",
                    "kernel": ">=0.0.0",
                    "resources": ["resources.json", "skills/review/SKILL.md"],
                    "dependencies": [],
                }
            ),
            encoding="utf-8",
        )
        (root / "resources.json").write_text(
            json.dumps(
                {
                    "id": "memory.com.example.report-policy",
                    "kind": "memory",
                    "name": "Report policy",
                    "version": "1.0.0",
                    "description": "Policy for reports.",
                    "capabilities": ["policy"],
                    "input_summary": "A question",
                    "output_summary": "Policy text",
                    "required_permissions": [],
                    "cost_estimate": 0.0,
                    "latency_class": "fast",
                    "side_effect": "none",
                    "trust_level": "verified",
                    "ref": "memory://com.example/report-policy",
                    "tags": ["policy"],
                    "content": "Reports must be reviewed.",
                }
            ),
            encoding="utf-8",
        )
        _write_skill(root / "skills" / "review", "name: review\ndescription: Review a report.")

    def test_documented_package_layout_loads_without_an_explicit_id(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "my-package"
            self._write_package(root)
            write_package_lock(root)

            issues = validate_resource_paths([root])
            registry = load_registry([root])

        self.assertEqual([issue for issue in issues if issue.severity == "error"], [])
        self.assertEqual(registry.get("skill.com.example.review").metadata.name, "review")

    def test_explicit_frontmatter_id_still_wins_inside_a_package(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "my-package"
            self._write_package(root)
            _write_skill(
                root / "skills" / "review",
                "id: skill.com.example.custom-review\nname: review\ndescription: Review a report.",
            )
            write_package_lock(root)

            registry = load_registry([root])

        self.assertEqual(registry.get("skill.com.example.custom-review").metadata.name, "review")


if __name__ == "__main__":
    unittest.main()
