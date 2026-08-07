"""Marmo-Core planning: a goal becomes a step DAG that runs in parallel.

Three independent collectors and one step that depends on all of them. The
Planner derives the waves from the dependencies the resources declare, so the
collectors overlap and the render step waits. Runs offline after installation.

    python examples/planned_execution.py
"""

import threading
import time

from marmo_core import (
    Kernel,
    LLMResponse,
    MockLLMProvider,
    PolicyContext,
    ResourceDefinition,
    ResourceRegistry,
    RuleBasedPlanner,
)


TIMELINE: list[tuple[float, str, str]] = []
_LOCK = threading.Lock()
_STARTED = time.perf_counter()


def _collector(label: str):
    """A slow step, so overlapping is visible in wall-clock time."""

    def handler(name: str) -> dict:
        _record("start", label)
        time.sleep(0.15)
        _record("end", label)
        return {"tool": label, "period": name}

    return handler


def _record(event: str, label: str) -> None:
    with _LOCK:
        TIMELINE.append((round(time.perf_counter() - _STARTED, 2), event, label))


def _tool(resource_id: str, description: str, **overrides) -> dict:
    data = {
        "id": resource_id,
        "kind": "tool",
        "name": resource_id,
        "version": "1.0.0",
        "description": description,
        "capabilities": [resource_id.rsplit(".", 1)[-1]],
        "input_summary": "Reporting period.",
        "output_summary": "Collected figures.",
        "required_permissions": [],
        "cost_estimate": 0.0,
        "latency_class": "fast",
        "side_effect": "none",
        "trust_level": "core",
        "ref": f"tool://{resource_id}",
        "tags": ["report", "quarterly"],
        "input_schema": {
            "type": "object",
            "required": ["name"],
            "properties": {"name": {"type": "string", "default": "q3"}},
        },
    }
    data.update(overrides)
    return data


RESOURCES = [
    _tool("tool.sales", "Collect quarterly sales figures for the report."),
    _tool("tool.costs", "Collect quarterly cost figures for the report."),
    _tool("tool.risk", "Collect quarterly risk figures for the report."),
    _tool(
        "tool.render",
        "Render the quarterly report from the collected figures.",
        # Declared here, so the planner does not have to guess the order.
        dependencies=["tool.sales", "tool.costs", "tool.risk"],
    ),
]


def main() -> None:
    registry = ResourceRegistry()
    for entry in RESOURCES:
        registry.add(ResourceDefinition.from_mapping(entry))

    kernel = Kernel(
        registry,
        MockLLMProvider(script=[LLMResponse(content="Quarterly report assembled.")]),
        planner=RuleBasedPlanner(),
        policy_context=PolicyContext(),
        tool_implementations={entry["id"]: _collector(entry["id"]) for entry in RESOURCES},
        set_limits={"tool": 4},
    )

    started = time.perf_counter()
    result = kernel.run_goal("collect the quarterly figures and render the report")
    elapsed = time.perf_counter() - started

    print(f"status: {result.status}")
    print(f"output: {result.output}")
    print(f"wall clock: {elapsed:.2f}s (four 0.15s steps run one after another would be ~0.60s)")

    print("\nplan:")
    for step in kernel.get_state(result.task_id)["plan"]["steps"]:
        depends = ", ".join(step["depends_on"]) or "-"
        print(f"  {step['id']}  {step['resource_id']:<12} depends_on={depends:<12} {step['status']}")

    print("\ntimeline:")
    for at, event, label in TIMELINE:
        print(f"  t={at:>5}s  {event:<5} {label}")

    assert result.completed, result.detail
    assert elapsed < 0.55, "the independent steps did not overlap"
    assert kernel.audit_log.verify() == [], "audit hash chain is broken"
    print("\nindependent steps overlapped; audit hash chain verified.")


if __name__ == "__main__":
    main()
