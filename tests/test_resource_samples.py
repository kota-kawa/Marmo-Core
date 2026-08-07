from __future__ import annotations

from collections import Counter
from pathlib import Path
import unittest

from marmo_core import load_resource_definitions


ROOT = Path(__file__).resolve().parents[1]
SAMPLE_DIRECTORIES = {
    "memory": ROOT / "resources" / "memory",
    "tool": ROOT / "resources" / "tools",
    "agent": ROOT / "resources" / "agents",
}


class ResourceSampleTests(unittest.TestCase):
    def test_bundled_directories_each_load_ten_samples_of_the_expected_kind(self) -> None:
        definitions = load_resource_definitions(SAMPLE_DIRECTORIES.values())

        self.assertEqual(
            Counter(item.metadata.kind for item in definitions),
            Counter({"memory": 10, "tool": 10, "agent": 10}),
        )
        self.assertEqual(len({item.identity for item in definitions}), 30)

        for kind, directory in SAMPLE_DIRECTORIES.items():
            with self.subTest(kind=kind):
                files = sorted(directory.glob("*.json"))
                loaded = load_resource_definitions([directory])
                self.assertEqual(len(files), 10)
                self.assertEqual(len(loaded), 10)
                self.assertTrue(all(item.metadata.kind == kind for item in loaded))
                self.assertTrue(all("sample" in item.metadata.tags for item in loaded))


if __name__ == "__main__":
    unittest.main()
