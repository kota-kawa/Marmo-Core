from __future__ import annotations

from pathlib import Path
import os
import subprocess
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]


class V2ExampleAcceptanceTests(unittest.TestCase):
    """Keep every v2 completion-line example executable and offline."""

    EXAMPLES = {
        "hello_world.py": "audit hash chain verified.",
        "agent_delegation.py": "delegation recorded in state",
        "human_in_the_loop.py": "resumed in a fresh kernel",
        "planned_execution.py": "independent steps overlapped",
        "recovery_fallback.py": "fallback selected through the guarded path",
    }

    def test_v2_examples_run_from_a_clean_process(self) -> None:
        for filename, marker in self.EXAMPLES.items():
            with self.subTest(example=filename):
                completed = subprocess.run(
                    [sys.executable, str(ROOT / "examples" / filename)],
                    cwd=ROOT,
                    env={**os.environ, "PYTHONPATH": str(ROOT)},
                    capture_output=True,
                    text=True,
                    timeout=20,
                    check=False,
                )
                self.assertEqual(
                    completed.returncode,
                    0,
                    f"{filename} failed:\nstdout:\n{completed.stdout}\nstderr:\n{completed.stderr}",
                )
                self.assertIn(marker, completed.stdout)


if __name__ == "__main__":
    unittest.main()
