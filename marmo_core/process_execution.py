"""Stop-capable execution for importable, JSON-compatible tool handlers."""

from __future__ import annotations

from dataclasses import dataclass
from importlib import import_module
from typing import Any, Callable, Mapping
import json
import os
import signal
import subprocess
import sys


@dataclass(frozen=True)
class ProcessOutcome:
    status: str
    output: Any = None
    error: str | None = None


def importable_handler(handler: Callable[..., Any]) -> str | None:
    """Return a stable import path, excluding closures and runtime bindings."""

    module_name = getattr(handler, "__module__", None)
    qualname = getattr(handler, "__qualname__", None)
    if not isinstance(module_name, str) or not isinstance(qualname, str) or "<locals>" in qualname:
        return None
    try:
        value: Any = import_module(module_name)
        for segment in qualname.split("."):
            value = getattr(value, segment)
    except (ImportError, AttributeError):
        return None
    return f"{module_name}:{qualname}" if value is handler else None


def run_importable(
    reference: str,
    arguments: Mapping[str, Any],
    timeout_seconds: float,
) -> ProcessOutcome:
    """Run a handler without re-importing the caller's main script."""

    if os.name != "posix":
        return ProcessOutcome("error", error="process timeout mode requires POSIX process groups")

    try:
        payload = json.dumps(dict(arguments), ensure_ascii=False, allow_nan=False).encode("utf-8")
    except (TypeError, ValueError):
        return ProcessOutcome("error", error="tool arguments must contain JSON-compatible values")
    command = [sys.executable, "-m", "marmo_core.process_execution", "--worker", reference]
    worker_environment = dict(os.environ)
    worker_environment["PYTHONPATH"] = os.pathsep.join(
        os.path.abspath(path or os.getcwd()) for path in sys.path if isinstance(path, str)
    )
    try:
        process = subprocess.Popen(
            command,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
            env=worker_environment,
        )
    except OSError as exc:
        return ProcessOutcome("error", error=f"tool worker could not start: {type(exc).__name__}: {exc}")
    try:
        try:
            output, _ = process.communicate(payload, timeout=timeout_seconds)
        except subprocess.TimeoutExpired:
            _stop_process(process)
            return ProcessOutcome("timeout")
        if process.returncode != 0:
            return ProcessOutcome("error", error="tool worker exited without a result")
        try:
            response = json.loads(output)
        except (TypeError, ValueError):
            return ProcessOutcome("error", error="tool worker returned an invalid result")
        if not isinstance(response, dict) or response.get("status") not in ("success", "error"):
            return ProcessOutcome("error", error="tool worker returned an invalid result")
        if response["status"] == "success":
            return ProcessOutcome("success", output=response.get("output"))
        return ProcessOutcome("error", error=str(response.get("error", "tool failed")))
    finally:
        if process.poll() is None:
            _stop_process(process)
        try:
            process.wait(timeout=1.0)
        except subprocess.TimeoutExpired:
            pass
        if process.stdin is not None:
            process.stdin.close()
        if process.stdout is not None:
            process.stdout.close()


def _stop_process(process: subprocess.Popen[bytes]) -> None:
    try:
        os.killpg(process.pid, signal.SIGKILL)
    except ProcessLookupError:
        pass


def _worker(reference: str) -> None:
    # Keep the protocol pipe separate from output written by imported handlers.
    protocol_fd = os.dup(sys.stdout.fileno())
    discarded_fd = os.open(os.devnull, os.O_WRONLY)
    os.dup2(discarded_fd, sys.stdout.fileno())
    os.close(discarded_fd)
    try:
        arguments = json.loads(sys.stdin.buffer.read())
        if not isinstance(arguments, dict):
            raise TypeError("tool arguments must be an object")
        module_name, qualname = reference.split(":", 1)
        handler: Any = import_module(module_name)
        for segment in qualname.split("."):
            handler = getattr(handler, segment)
        result = handler(**arguments)
        from .agent_runtime import AgentResponse

        if isinstance(result, AgentResponse):
            if (
                not isinstance(result.cost, (int, float))
                or isinstance(result.cost, bool)
                or result.cost < 0
            ):
                raise ValueError("AgentResponse.cost must be a non-negative number")
            result = {"__marmo_agent_response__": True, "output": result.output, "cost": result.cost}
        response = {"status": "success", "output": result}
        encoded = json.dumps(response, ensure_ascii=False, allow_nan=False).encode("utf-8")
    except Exception as exc:  # noqa: BLE001 - handler failures become data
        response = {"status": "error", "error": f"{type(exc).__name__}: {exc}"}
        encoded = json.dumps(response, ensure_ascii=False).encode("utf-8")
    with os.fdopen(protocol_fd, "wb") as protocol:
        protocol.write(encoded)


if __name__ == "__main__":
    if len(sys.argv) != 3 or sys.argv[1] != "--worker":
        raise SystemExit(2)
    _worker(sys.argv[2])
