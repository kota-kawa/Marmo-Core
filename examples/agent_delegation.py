"""Marmo-Core Agent delegation through the guarded Kernel path.

The specialist is exposed as a tool-wrapped Agent. Its permissions can only
shrink from the caller's grants, and its result is persisted and audited.
Runs offline without external services.

    python examples/agent_delegation.py
"""

from marmo_core import (
    AgentResponse,
    Kernel,
    MockLLMProvider,
    PolicyContext,
    ResourceDefinition,
    ResourceRegistry,
)


def research_specialist(question: str) -> AgentResponse:
    return AgentResponse(
        output={"answer": f"Reviewed by the specialist: {question}"},
        cost=0.05,
    )


AGENT = {
    "id": "agent.research.specialist",
    "kind": "agent",
    "name": "Research Specialist",
    "version": "1.0.0",
    "description": "Delegate a focused research question to a specialist Agent.",
    "capabilities": ["research", "summarization"],
    "input_summary": "One focused research question.",
    "output_summary": "A concise specialist answer.",
    "required_permissions": ["research.read"],
    "cost_estimate": 0.1,
    "latency_class": "fast",
    "side_effect": "read",
    "trust_level": "core",
    "ref": "agent://research/specialist",
    "tags": ["research", "delegation"],
    "agent_card": {
        "delegation_interface": "tool_wrap",
        "callable_name": "delegate_research",
        "input_schema": {
            "type": "object",
            "required": ["question"],
            "properties": {"question": {"type": "string"}},
            "additionalProperties": False,
        },
        "output_schema": {"type": "object"},
    },
}


def main() -> None:
    registry = ResourceRegistry()
    registry.add(ResourceDefinition.from_mapping(AGENT))
    kernel = Kernel(
        registry,
        MockLLMProvider(
            tool_arguments={
                "delegate_research": {
                    "question": "Which controls protect delegated execution?"
                }
            }
        ),
        agent_implementations={"agent.research.specialist": research_specialist},
        policy_context=PolicyContext(granted_permissions=("research.read",)),
    )

    result = kernel.run_goal("Ask the research specialist about delegated execution controls")
    assert result.completed, result.detail
    assert len(result.agent_results) == 1, "the specialist was not delegated to"
    delegated = result.agent_results[0]
    state = kernel.get_state(result.task_id)

    print(f"status: {result.status}")
    print(f"agent: {delegated.agent_id}@{delegated.agent_version}")
    print(f"delegated permissions: {', '.join(delegated.delegated_permissions)}")
    print(f"reported cost: {delegated.cost:.2f}")
    print(f"persisted step: {state['step_results'][0]['status']}")

    assert delegated.executed
    assert delegated.delegated_permissions == ("research.read",)
    assert state["step_results"][0]["agent_id"] == delegated.agent_id
    assert "delegate" in {record.kind for record in kernel.audit_log.records}
    assert kernel.audit_log.verify() == [], "audit hash chain is broken"
    print("delegation recorded in state; audit hash chain verified.")


if __name__ == "__main__":
    main()
