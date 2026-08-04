from __future__ import annotations

from pathlib import Path
import json
import subprocess
import sys
import tempfile
import unittest

from marmo_core import (
    LexicalRetriever,
    ResourceNotFoundError,
    RuleBasedSetSelector,
    SearchQuery,
    load_registry,
)
from marmo_core.loader import validate_resource_paths


ROOT = Path(__file__).resolve().parents[1]
SAMPLES = ROOT / "examples" / "resources"


class ResourceLoadingTests(unittest.TestCase):
    def test_sample_resources_load_all_four_kinds(self) -> None:
        registry = load_registry([SAMPLES])
        summary = registry.summary()

        self.assertEqual(summary["total"], 8)
        self.assertEqual(summary["memory"], 2)
        self.assertEqual(summary["skill"], 2)
        self.assertEqual(summary["tool"], 2)
        self.assertEqual(summary["agent"], 2)

    def test_validation_reports_invalid_enum(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "bad.json"
            resource = _minimal_resource()
            resource["side_effect"] = "dangerous"
            path.write_text(json.dumps(resource), encoding="utf-8")

            issues = validate_resource_paths([path])

        self.assertTrue(any("side_effect must be one of" in issue.message for issue in issues))

    def test_validation_reports_duplicate_identity(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "duplicates.json"
            resource = _minimal_resource()
            path.write_text(json.dumps({"resources": [resource, resource]}), encoding="utf-8")

            issues = validate_resource_paths([path])

        self.assertTrue(any("duplicate resource identity" in issue.message for issue in issues))

    def test_markdown_skill_files_are_loaded_as_skill_resources(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            skill_dir = Path(temp_dir) / "skills" / "demo-skill"
            skill_dir.mkdir(parents=True)
            skill_path = skill_dir / "SKILL.md"
            unrelated_json = skill_dir / "runtime-data.json"
            unrelated_json.write_text(json.dumps([1, 2, 3]), encoding="utf-8")
            skill_path.write_text(
                """---
name: demo-skill
description: |
  Find Kubernetes deployment drift and explain remediation steps.
tags: [kubernetes, drift]
---

# Demo Skill

Use kubectl rollout history and deployment manifests to diagnose drift.
""",
                encoding="utf-8",
            )

            registry = load_registry([Path(temp_dir) / "skills"])
            results = LexicalRetriever().search(registry, SearchQuery(task="diagnose kubectl deployment drift", top_k=3))

        self.assertEqual(registry.summary()["skill"], 1)
        self.assertEqual(results[0].resource.metadata.kind, "skill")
        self.assertEqual(results[0].resource.metadata.name, "demo-skill")
        self.assertIn("content", results[0].resource.extras)

    def test_markdown_skill_ids_strip_resources_skills_prefix(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            skill_dir = Path(temp_dir) / "resources" / "skills" / "demo-skill"
            skill_dir.mkdir(parents=True)
            skill_path = skill_dir / "SKILL.md"
            skill_path.write_text(
                """---
name: demo-skill
description: Demo skill for the canonical resources layout.
---

# Demo Skill
""",
                encoding="utf-8",
            )

            registry = load_registry([Path(temp_dir) / "resources"])
            resource = registry.get("skill.demo-skill")

        self.assertEqual(resource.metadata.id, "skill.demo-skill")

    def test_resources_can_be_disabled_and_re_enabled_without_removal(self) -> None:
        registry = load_registry([SAMPLES])
        resource_id = "tool.files.read-text"
        revision = registry.revision

        registry.disable(resource_id)

        self.assertGreater(registry.revision, revision)
        self.assertFalse(registry.is_enabled(resource_id, "1.0.0"))
        self.assertNotIn(resource_id, {item.metadata.id for item in registry.all()})
        self.assertIn(
            resource_id,
            {item.metadata.id for item in registry.all(include_disabled=True)},
        )
        with self.assertRaisesRegex(ResourceNotFoundError, "disabled"):
            registry.get(resource_id)

        registry.enable(resource_id, "1.0.0")

        self.assertTrue(registry.is_enabled(resource_id))
        self.assertEqual(registry.get(resource_id).metadata.id, resource_id)

    def test_disabling_a_resource_invalidates_the_retrieval_index(self) -> None:
        registry = load_registry([SAMPLES])
        retriever = LexicalRetriever()
        query = SearchQuery(
            task="Read a local text file safely",
            granted_permissions=("fs.read",),
            top_k=3,
        )
        self.assertEqual(
            retriever.search(registry, query)[0].resource.metadata.id,
            "tool.files.read-text",
        )

        registry.disable("tool.files.read-text")
        results = retriever.search(registry, query)

        self.assertNotIn("tool.files.read-text", [item.resource.metadata.id for item in results])


class SearchTests(unittest.TestCase):
    def setUp(self) -> None:
        self.registry = load_registry([SAMPLES])
        self.retriever = LexicalRetriever()

    def test_task_search_ranks_file_reader_highly_when_permission_is_granted(self) -> None:
        query = SearchQuery(
            task="Read a local text file safely and summarize its content",
            granted_permissions=("fs.read",),
            top_k=3,
        )

        results = self.retriever.search(self.registry, query)

        self.assertGreaterEqual(len(results), 1)
        self.assertEqual(results[0].resource.metadata.id, "tool.files.read-text")
        self.assertGreater(results[0].score, 0.5)

    def test_permission_filter_drops_tools_without_grants(self) -> None:
        query = SearchQuery(
            task="run tools",
            kinds=("tool",),
            require_permissions=True,
            top_k=10,
        )

        results = self.retriever.search(self.registry, query)

        self.assertEqual(results, [])

    def test_kind_trust_side_effect_and_tag_filters(self) -> None:
        query = SearchQuery(
            task="security review",
            kinds=("skill",),
            trust_levels=("core",),
            side_effects=("none",),
            tags=("security",),
            top_k=10,
        )

        results = self.retriever.search(self.registry, query)

        self.assertEqual([result.resource.metadata.id for result in results], ["skill.security.safe-tool-use"])

    def test_per_kind_limit_caps_result_distribution(self) -> None:
        query = SearchQuery(task="kernel safety policy tool agent", top_k=10, per_kind_limits={"memory": 1, "skill": 1})

        results = self.retriever.search(self.registry, query)
        counts: dict[str, int] = {}
        for result in results:
            kind = result.resource.metadata.kind
            counts[kind] = counts.get(kind, 0) + 1

        self.assertLessEqual(counts.get("memory", 0), 1)
        self.assertLessEqual(counts.get("skill", 0), 1)

    def test_rule_based_set_selector_picks_compact_cross_kind_set(self) -> None:
        query = SearchQuery(task="Review prompt injection and exfiltration risks", tags=("security",), top_k=10)
        results = self.retriever.search(self.registry, query)

        selected = RuleBasedSetSelector().select(results)
        by_kind = selected.by_kind

        self.assertLessEqual(len(by_kind["memory"]), 1)
        self.assertLessEqual(len(by_kind["skill"]), 1)
        self.assertLessEqual(len(by_kind["agent"]), 1)
        self.assertTrue(selected.results)


class CliTests(unittest.TestCase):
    def run_cli(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, "-m", "marmo_core.cli", *args],
            cwd=ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )

    def test_cli_validate(self) -> None:
        result = self.run_cli("validate", "examples/resources")

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("valid: 8 resources", result.stdout)

    def test_cli_search_outputs_results_and_selected_set(self) -> None:
        result = self.run_cli(
            "search",
            "examples/resources",
            "--task",
            "Read a local text file safely",
            "--granted-permission",
            "fs.read",
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("tool.files.read-text", result.stdout)
        self.assertIn("Selected set:", result.stdout)

    def test_cli_inspect_json(self) -> None:
        result = self.run_cli("inspect", "tool.files.read-text", "examples/resources", "--format", "json")

        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["id"], "tool.files.read-text")
        self.assertIn("input_schema", payload["extras"])


def _minimal_resource() -> dict[str, object]:
    return {
        "id": "memory.test",
        "kind": "memory",
        "name": "Test Memory",
        "version": "1.0.0",
        "description": "A minimal test memory.",
        "capabilities": ["test"],
        "input_summary": "test input",
        "output_summary": "test output",
        "required_permissions": [],
        "cost_estimate": 0.0,
        "latency_class": "fast",
        "side_effect": "none",
        "trust_level": "core",
        "ref": "memory://test",
        "tags": ["test"],
    }


if __name__ == "__main__":
    unittest.main()
