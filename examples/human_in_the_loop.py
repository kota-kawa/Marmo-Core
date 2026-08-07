"""Marmo-Core HITL: a risky task pauses, survives a restart, then resumes.

Shows the Kernel pausing on an escalation, the State Store keeping the task
durable on disk, and a second Kernel -- standing in for a later process --
picking it up with a human's answer. Runs offline after installing the package.

    python examples/human_in_the_loop.py
"""

from pathlib import Path
import tempfile

from marmo_core import (
    HitlPolicy,
    HitlResponse,
    JsonFileStateStore,
    Kernel,
    MockLLMProvider,
    PendingHitlBroker,
    PolicyContext,
    ResourceDefinition,
    ResourceRegistry,
)


PUBLISHED: list[dict] = []


def publish_report(title: str) -> dict:
    """Stand-in for an irreversible external write."""

    PUBLISHED.append({"title": title})
    return {"published": title, "total": len(PUBLISHED)}


RESOURCES = [
    {
        "id": "tool.reports.publish",
        "kind": "tool",
        "name": "Publish Report",
        "version": "1.0.0",
        "description": "Publish a report to the public company feed.",
        "capabilities": ["publishing", "reports"],
        "input_summary": "Report title.",
        "output_summary": "Confirmation of the published report.",
        "required_permissions": ["reports.publish"],
        "cost_estimate": 0.0,
        "latency_class": "fast",
        "side_effect": "irreversible",
        "trust_level": "core",
        "ref": "tool://reports/publish",
        "tags": ["reports", "publishing"],
        "input_schema": {
            "type": "object",
            "required": ["title"],
            "properties": {"title": {"type": "string"}},
        },
    }
]


def build_kernel(state_dir: Path) -> Kernel:
    registry = ResourceRegistry()
    for entry in RESOURCES:
        registry.add(ResourceDefinition.from_mapping(entry))
    return Kernel(
        registry,
        MockLLMProvider(tool_arguments={"tool.reports.publish": {"title": "Q3 results"}}),
        policy_context=PolicyContext(granted_permissions=("reports.publish",)),
        tool_implementations={"tool.reports.publish": publish_report},
        # Only Dana may approve; everyone may reject (F-HITL-07).
        hitl=PendingHitlBroker(HitlPolicy(approvers=("dana",))),
        state_store=JsonFileStateStore(state_dir),
    )


def main() -> None:
    with tempfile.TemporaryDirectory() as temp_dir:
        state_dir = Path(temp_dir) / "state"

        paused = build_kernel(state_dir).run_goal("Publish the Q3 results report")
        print(f"status: {paused.status}")
        assert paused.paused, paused.detail
        assert not PUBLISHED, "nothing may run before a human answers"

        # A later process rebuilds everything and reads the pending request.
        resumed_kernel = build_kernel(state_dir)
        request = resumed_kernel.pending_request(paused.task_id)
        print("awaiting confirmation:")
        print(request.describe())

        result = resumed_kernel.resume(
            paused.task_id,
            HitlResponse(kind="approve", responder="dana", note="reviewed the figures"),
        )

    print(f"status: {result.status}")
    print(f"published: {PUBLISHED}")
    assert result.completed, result.detail
    assert len(PUBLISHED) == 1, "the tool must run exactly once"
    assert resumed_kernel.audit_log.verify() == [], "audit hash chain is broken"
    print("resumed in a fresh kernel; audit hash chain verified.")


if __name__ == "__main__":
    main()
