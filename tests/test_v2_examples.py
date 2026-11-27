from __future__ import annotations

from pathlib import Path
import contextlib
import importlib.util
import io
import itertools
import os
import subprocess
import sys
import types
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
        "tool_catalog_routing.py": "selected functions: book_hotel, search_flights, weather_forecast",
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

    def test_planned_execution_success_does_not_depend_on_elapsed_time(self) -> None:
        spec = importlib.util.spec_from_file_location("planned_execution_example", ROOT / "examples" / "planned_execution.py")
        assert spec is not None and spec.loader is not None
        example = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(example)
        # A clock that jumps ten seconds per reading: a wall-clock threshold would fail,
        # while overlap and dependency order come from the barrier and the event order.
        ticks = itertools.count()
        example.time = types.SimpleNamespace(perf_counter=lambda: next(ticks) * 10.0)

        with contextlib.redirect_stdout(io.StringIO()) as output:
            example.main()

        self.assertIn("independent steps overlapped", output.getvalue())
        self.assertEqual(
            sorted(label for _, event, label in example.TIMELINE if event == "start"),
            sorted([*example.COLLECTORS, "tool.render"]),
        )


if __name__ == "__main__":
    unittest.main()
