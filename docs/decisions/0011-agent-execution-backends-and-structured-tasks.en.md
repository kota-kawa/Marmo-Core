# 0011. Select Agent execution backends and delegate structured tasks to child Kernels

[日本語](0011-agent-execution-backends-and-structured-tasks.md)

- Status: Accepted
- Date: 2026-09-25
- Evidence: `marmo_core/agent_runtime.py`, `marmo_core/kernel.py`

## Context

Previously, Agents ran local Python handlers through `ToolRuntime`. Resource definitions could declare `structured_task`, but activation rejected it, and Kernel's Agent delegation depth was always 1. Structured Agents need a resumable execution path to use Tools without receiving the parent's entire registry, permissions, and cost limit.

## Decision

`AgentRuntime` passes activated Agents to an `AgentExecutionBackend`. The built-in `tool_wrap` backend runs local handlers. The `structured_task` backend creates a child Kernel task whose registry contains only the transitive closure of the dependencies declared by the Agent. Its input schema has a required string field `goal`.

The child Kernel uses the same LLM, Retriever, Selector, Planner, Policy Gateway, Tool Runtime, State Store, Audit Log, Recovery Manager, and task budget as its parent. Permissions in the PolicyContext are narrowed to those declared by the Agent. Requests for human approval are relayed to the parent, which responds to the deterministic child task. Results from child Tools are recorded in the parent state so compensation can also refer to them. Configured `max_agent_depth` and `max_agent_cost` limits apply to nested Agents as well.

## Consequences

Registering a custom backend extends the Agent execution environment. Structured tasks preserve the parent's policy and budget boundaries even when Tools and Agents are combined. Since child tasks are persisted individually, users can inspect their state through `AgentResult.child_task_id`. The default depth remains 1, and nesting Agents requires an explicit limit configuration. Available Resources for a child are determined by the dependency declaration, so they should be reviewed by the same criteria as other executable Resources.

## Alternatives

- Restrict all Agents to local Python handlers: rejected because declared `structured_task` Resources could not run.
- Give the child the parent's entire registry and permissions: rejected because this would expose unrelated Resources and permissions.
- Give each child an independent budget: rejected because nested delegation could amplify the parent's limit.
