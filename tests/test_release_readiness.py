from __future__ import annotations

from pathlib import Path
import subprocess
import sys
import unittest

from marmo_core import __version__


ROOT = Path(__file__).resolve().parents[1]


class ReleaseReadinessTests(unittest.TestCase):
    def test_release_gate_passes_for_the_v2_candidate(self) -> None:
        completed = subprocess.run(
            [sys.executable, str(ROOT / "scripts" / "release_check.py")],
            cwd=ROOT,
            capture_output=True,
            check=False,
            text=True,
        )

        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertIn(f"release check passed: {__version__}", completed.stdout)


if __name__ == "__main__":
    unittest.main()
