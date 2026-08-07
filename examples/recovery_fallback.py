"""Marmo-Core Recovery: a failed Tool falls back to a compatible stand-in.

The primary fails permanently. Recovery re-searches the registry, verifies
that the standby has compatible capabilities and inputs, activates it through
the normal policy gate, and records the decision. Runs offline without
external services.

    python examples/recovery_fallback.py
"""

from marmo_core import (
    Kernel,
    LLMResponse,
    MockLLMProvider,
    PolicyContext,
    RecoveryManager,
    ResourceDefinition,
    ResourceRegistry,
    RetryPolicy,
    ToolCall,
)


def _tool(resource_id: str, description: str) -> dict:
    return {
        "id": resource_id,
        "kind": "tool",
        "name": resource_id,
        "version": "1.0.0",
        "description": description,
        "capabilities": ["reporting", "fetch"],
        "input_summary": "A report name.",
        "output_summary": "The requested report.",
        "required_permissions": [],
        "cost_estimate": 0.0,
        "latency_class": "fast",
        "side_effect": "none",
        "trust_level": "core",
        "ref": f"tool://reports/{resource_id.rsplit('.', 1)[-1]}",
        "tags": ["reporting", "recovery"],
        "input_schema": {
            "type": "object",
            "required": ["name"],
            "properties": {"name": {"type": "string"}},
        },
    }


RESOURCES = [
    _tool("tool.reports.primary", "Fetch the Q3 report from the primary feed."),
    _tool("tool.reports.standby", "Mirror feed for compatible report fetch requests."),
]


def unavailable_primary(name: str) -> dict:
    raise ValueError(f"primary feed is unavailable for {name}")


def standby_feed(name: str) -> dict:
    return {"report": name, "via": "standby"}


def main() -> None:
    registry = ResourceRegistry()
    for entry in RESOURCES:
        registry.add(ResourceDefinition.from_mapping(entry))

    llm = MockLLMProvider(
        script=[
            LLMResponse(
                content="",
                tool_calls=(
                    ToolCall(
                        id="fetch-q3",
                        name="tool.reports.primary",
                        arguments={"name": "q3"},
                    ),
                ),
            ),
            LLMResponse(content="Q3 report recovered from the standby feed."),
        ]
    )
    kernel = Kernel(
        registry,
        llm,
        policy_context=PolicyContext(),
        tool_implementations={
            "tool.reports.primary": unavailable_primary,
            "tool.reports.standby": standby_feed,
        },
        recovery=RecoveryManager(
            retry_policy=RetryPolicy(max_attempts=1),
            escalate_when_exhausted=False,
            sleep=lambda _: None,
        ),
        # Only the primary is selected initially; Recovery must re-search.
        set_limits={"tool": 1},
    )

    result = kernel.run_goal("Fetch the Q3 report from the primary feed")
    assert result.completed, result.detail
    assert [item.status for item in result.tool_results] == ["error", "success"]
    actions = [
        record.payload
        for record in kernel.audit_log.records
        if record.kind == "recover"
    ]
    fallback = next(item for item in actions if item.get("action") == "fallback_selected")

    print(f"status: {result.status}")
    print("attempts:")
    for attempt in result.tool_results:
        print(f"  {attempt.tool_id}: {attempt.status}")
    print(f"fallback: {fallback['from']} -> {fallback['to']}")
    print(f"checkpoints: {len(kernel.checkpoints(result.task_id))}")

    assert result.tool_results[-1].tool_id == "tool.reports.standby"
    assert kernel.audit_log.verify() == [], "audit hash chain is broken"
    print("fallback selected through the guarded path; audit hash chain verified.")


if __name__ == "__main__":
    main()
