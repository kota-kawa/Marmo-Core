from __future__ import annotations

from pathlib import Path
import os
import tempfile
import time
import subprocess
import sys
import threading
import unittest
from unittest.mock import patch

from marmo_core import BoundTool, PolicyContext, ResourceDefinition, ToolInputError, ToolRuntime


def _late_write(path: str, delay: float) -> dict[str, bool]:
    time.sleep(delay)
    Path(path).write_text("ran", encoding="utf-8")
    return {"ran": True}


def _noisy_handler(path: str, delay: float) -> dict[str, bool]:
    print("handler output")
    os.write(1, b"native output\n")
    return _late_write(path, delay)


class ProcessPlatformTests(unittest.TestCase):
    def test_process_mode_rejects_platform_without_process_groups(self) -> None:
        with patch("marmo_core.tool_runtime.os.name", "nt"):
            with self.assertRaisesRegex(ValueError, "requires POSIX process groups"):
                ToolRuntime(timeout_mode="process")


@unittest.skipUnless(os.name == "posix", "process timeout requires POSIX process groups")
class ProcessTimeoutTests(unittest.TestCase):
    def _tool(self, handler) -> BoundTool:
        definition = ResourceDefinition.from_mapping(
            {
                "id": "tool.test.late-write",
                "kind": "tool",
                "name": "Late write",
                "version": "1.0.0",
                "description": "Write a marker after a delay",
                "capabilities": ["write marker"],
                "input_summary": "path and delay",
                "output_summary": "status",
                "required_permissions": [],
                "cost_estimate": 0.0,
                "latency_class": "fast",
                "side_effect": "write",
                "trust_level": "core",
                "ref": "tool://test/late-write",
                "tags": ["test"],
                "input_schema": {
                    "type": "object",
                    "required": ["path", "delay"],
                    "properties": {
                        "path": {"type": "string"},
                        "delay": {"type": "number"},
                    },
                },
            }
        )
        return BoundTool(definition, dict(definition.extras["input_schema"]), {}, handler)

    def test_timeout_stops_worker_before_late_side_effect(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            marker = Path(directory) / "marker.txt"
            runtime = ToolRuntime(timeout_seconds=0.2, timeout_mode="process")
            result = runtime.execute(
                self._tool(_late_write),
                {"path": str(marker), "delay": 0.5},
                PolicyContext(allowed_side_effects=("none", "read", "write"), escalate_side_effects=()),
            )
            self.assertEqual(result.status, "timeout")
            time.sleep(0.55)
            self.assertFalse(marker.exists())

    def test_process_mode_executes_importable_handler(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            marker = Path(directory) / "marker.txt"
            result = ToolRuntime(timeout_mode="process").execute(
                self._tool(_late_write),
                {"path": str(marker), "delay": 0.0},
                PolicyContext(allowed_side_effects=("none", "read", "write"), escalate_side_effects=()),
            )
            self.assertEqual(result.status, "success", result.error)
            self.assertEqual(marker.read_text(encoding="utf-8"), "ran")

    def test_handler_stdout_cannot_corrupt_result(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            marker = Path(directory) / "marker.txt"
            result = ToolRuntime(timeout_mode="process").execute(
                self._tool(_noisy_handler),
                {"path": str(marker), "delay": 0.0},
                PolicyContext(allowed_side_effects=("none", "read", "write"), escalate_side_effects=()),
            )
            self.assertEqual(result.status, "success", result.error)
            self.assertEqual(marker.read_text(encoding="utf-8"), "ran")

    def test_process_mode_rejects_unstoppable_closure_before_execution(self) -> None:
        calls: list[str] = []

        def local(path: str, delay: float) -> None:
            calls.append(path)

        with self.assertRaisesRegex(ToolInputError, "importable module-level handler"):
            ToolRuntime(timeout_mode="process").execute(
                self._tool(local),
                {"path": "x", "delay": 0.0},
                PolicyContext(allowed_side_effects=("none", "read", "write"), escalate_side_effects=()),
            )
        self.assertEqual(calls, [])

    def test_non_json_argument_is_rejected_before_worker_start(self) -> None:
        tool = self._tool(_late_write)
        permissive = BoundTool(tool.definition, {}, {}, tool.handler)
        with self.assertRaisesRegex(ToolInputError, "JSON-compatible"):
            ToolRuntime(timeout_mode="process").execute(
                permissive,
                {"path": threading.Lock(), "delay": 0.0},
                PolicyContext(allowed_side_effects=("none", "read", "write"), escalate_side_effects=()),
            )

    def test_worker_does_not_reexecute_unguarded_main_script(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            script = Path(directory) / "app.py"
            counter = Path(directory) / "counter.txt"
            marker = Path(directory) / "marker.txt"
            script.write_text(
                "from pathlib import Path\n"
                "from tests.test_process_execution import ProcessTimeoutTests, _late_write\n"
                "from marmo_core import PolicyContext, ToolRuntime\n"
                f"counter = Path({str(counter)!r})\n"
                "counter.write_text(str(int(counter.read_text()) + 1 if counter.exists() else 1))\n"
                "tool = ProcessTimeoutTests()._tool(_late_write)\n"
                "result = ToolRuntime(timeout_mode='process').execute(\n"
                f"    tool, {{'path': {str(marker)!r}, 'delay': 0.0}},\n"
                "    PolicyContext(allowed_side_effects=('none', 'read', 'write'), escalate_side_effects=()))\n"
                "assert result.status == 'success', result.error\n",
                encoding="utf-8",
            )
            completed = subprocess.run(
                [sys.executable, str(script)],
                capture_output=True,
                text=True,
                check=False,
                env={**os.environ, "PYTHONPATH": str(Path(__file__).resolve().parents[1])},
            )
            self.assertEqual(completed.returncode, 0, completed.stderr)
            self.assertEqual(counter.read_text(encoding="utf-8"), "1")
            self.assertEqual(marker.read_text(encoding="utf-8"), "ran")
