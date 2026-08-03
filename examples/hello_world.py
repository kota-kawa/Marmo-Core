"""Marmo-Core hello world: search -> policy gate -> activate -> execute -> audit.

Runs offline with zero external dependencies using the deterministic mock LLM.

    python examples/hello_world.py
"""

from marmo_core import (
    Kernel,
    MockLLMProvider,
    PolicyContext,
    ResourceDefinition,
    ResourceRegistry,
)


def add_numbers(a: float, b: float) -> dict:
    return {"sum": a + b}


RESOURCES = [
    {
        "id": "tool.math.add",
        "kind": "tool",
        "name": "Add Numbers",
        "version": "1.0.0",
        "description": "Add two numbers and return their sum.",
        "capabilities": ["arithmetic", "addition"],
        "input_summary": "Two numbers a and b.",
        "output_summary": "Object with the sum.",
        "required_permissions": ["math.add"],
        "cost_estimate": 0.0,
        "latency_class": "fast",
        "side_effect": "none",
        "trust_level": "core",
        "ref": "tool://math/add",
        "tags": ["math", "calculator", "addition"],
        "input_schema": {
            "type": "object",
            "required": ["a", "b"],
            "properties": {"a": {"type": "number"}, "b": {"type": "number"}},
        },
    },
    {
        "id": "memory.math.style",
        "kind": "memory",
        "name": "Answer Style Notes",
        "version": "1.0.0",
        "description": "Preference notes for arithmetic answers: state the numbers and the result.",
        "capabilities": ["style guidance"],
        "input_summary": "Arithmetic task.",
        "output_summary": "Style notes.",
        "required_permissions": [],
        "cost_estimate": 0.0,
        "latency_class": "fast",
        "side_effect": "none",
        "trust_level": "core",
        "ref": "memory://math/style",
        "tags": ["math", "style"],
        "content": "Always repeat the input numbers next to the computed result.",
    },
]


def main() -> None:
    registry = ResourceRegistry()
    for entry in RESOURCES:
        registry.add(ResourceDefinition.from_mapping(entry))

    kernel = Kernel(
        registry,
        MockLLMProvider(tool_arguments={"tool.math.add": {"a": 2, "b": 3}}),
        policy_context=PolicyContext(granted_permissions=("math.add",)),
        tool_implementations={"tool.math.add": add_numbers},
    )
    result = kernel.run_goal("Add 2 and 3 with the calculator tool")

    print(f"status: {result.status}")
    print(f"output: {result.output}")
    print("audit trail:")
    for record in kernel.audit_log.records:
        print(f"  {record.kind:<9} {record.hash[:16]}…")
    assert result.completed, result.detail
    assert kernel.audit_log.verify() == [], "audit hash chain is broken"
    print("audit hash chain verified.")


if __name__ == "__main__":
    main()
