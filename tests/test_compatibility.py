from __future__ import annotations

from pathlib import Path
import json
import shutil
import tempfile
import unittest

import marmo_core
from marmo_core import InMemoryStateStore, JsonFileStateStore, ResourceDefinition


FIXTURES = Path(__file__).resolve().parent / "fixtures" / "compat" / "v0.3.0"


class CompatibilityContractTests(unittest.TestCase):
    """Protect the same-major compatibility surfaces named in the v2 DoD."""

    def test_v030_public_api_remains_available(self) -> None:
        expected = {
            line.strip()
            for line in (FIXTURES / "public_api.txt").read_text(encoding="utf-8").splitlines()
            if line.strip()
        }
        current = set(marmo_core.__all__)

        self.assertFalse(expected - current, f"removed public names: {sorted(expected - current)}")
        for name in expected:
            self.assertTrue(hasattr(marmo_core, name), f"marmo_core.{name} is not importable")

    def test_v030_resource_defaults_new_optional_metadata(self) -> None:
        payload = json.loads((FIXTURES / "resource.json").read_text(encoding="utf-8"))
        resource = ResourceDefinition.from_mapping(payload, source="v0.3.0/resource.json")

        self.assertEqual(resource.validate(), [])
        self.assertEqual(resource.metadata.dependencies, ())
        self.assertEqual(resource.metadata.conflicts_with, ())
        self.assertIsNone(resource.metadata.stats.success_rate)
        self.assertEqual(resource.extras["input_schema"]["type"], "object")

        reloaded = ResourceDefinition.from_mapping(resource.to_dict(), source=resource.source)
        self.assertEqual(reloaded.metadata, resource.metadata)
        self.assertEqual(reloaded.extras["extras"], resource.extras)

    def test_v030_jsonl_state_loads_and_accepts_new_events(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            state_path = Path(directory) / "compat-task.jsonl"
            shutil.copyfile(FIXTURES / "state.jsonl", state_path)
            store = JsonFileStateStore(directory)

            state = store.load("compat-task")
            self.assertEqual(state.goal, "verify persisted state compatibility")
            self.assertEqual(state.status, "running")
            self.assertEqual(state.trace_id, "trace-v030")
            self.assertEqual(state.activated, ("tool.compat.echo@0.3.0",))
            self.assertEqual(state.variables, {"message": "hello"})
            self.assertEqual(state.version, 4)

            updated = store.append(
                "compat-task",
                "variable",
                {"key": "compatible", "value": True},
                expected_version=state.version,
            )
            self.assertEqual(updated.variables["compatible"], True)
            self.assertEqual(updated.version, 5)

    def test_malformed_persisted_rollback_has_an_explicit_error(self) -> None:
        store = InMemoryStateStore()
        state = store.create("validate rollback compatibility")

        with self.assertRaisesRegex(ValueError, "target_seq must be an integer"):
            store.append(state.task_id, "rollback", {"target_seq": "not-an-integer"})


if __name__ == "__main__":
    unittest.main()
