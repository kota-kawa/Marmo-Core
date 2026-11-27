# 0016. The MCP gateway applies the same gates outside the Kernel and refuses what needs a human

[日本語](0016-mcp-gateway-outside-the-kernel.md)

- Status: Accepted
- Date: 2026-11-27
- Evidence: `marmo_core/mcp_server.py`, `tests/test_mcp_server.py`, "5. OSS として出す形" in issue #35

## Context

Using Marmo-Core's retrieval, set selection, and gates meant embedding a `Kernel` and letting it
call the model. A host with its own model and agent loop (an MCP client) could not use selection
and the gates alone. An MCP client's model and conversation live outside Marmo-Core and share no
Kernel state.

## Decision

- Add `MCPGatewayServer`, which exposes two MCP tools, `search_tools` and `call_tool`. The client
  starts with two definitions whatever the size of the catalog.
- It does not go through the Kernel, because the Kernel is the loop that calls a model and the
  model is on the client's side. It runs the same components in the same order instead:
  `KindBalancedCandidatePool`, the `SetSelector`, `_enforce_set_constraints`, the activation gate,
  and `ToolRuntime.execute` (execution gate, argument validation, `SafetyInspector`, timeout).
- The client is outside the trust boundary. Whoever starts the gateway fixes the `PolicyContext`
  and the client cannot change it. A Tool that `search_tools` has not returned in the session
  cannot be called.
- Nobody can approve on this channel. An operation the gates escalate is refused with the reason.
  The operator gives approval in advance with `approved_resources` (`--approve-resource` on the CLI).
- As in the Kernel, a write / external / irreversible call made after a Tool result was returned
  to the client counts as proposed after untrusted content. It needs an approval scoped to the
  operation, so the gateway refuses it.
- A Tool result is wrapped by `label_untrusted_content` and cut at `max_tool_output_tokens`.
- Only Tools are served. A Tool that depends on a Memory, Skill, or Agent is withheld.

## Consequences

- A side-effecting Tool cannot be called once the session has returned any Tool result, even when
  it was approved in advance. The gateway suits read-mostly catalogs; work that writes belongs in
  the Kernel, which has HITL.
- The gateway has no retry, fallback, compensation, circuit breaker, task budget, call limit
  (`max_tool_calls`), saved state or resume, Connectors, `SecretResolver`, or `HitlPolicy`
  "always confirm". One call is one attempt, and its decision and result are in the audit log.
- Dependency and conflict constraints apply to the set of one search. In addition, a Tool that
  conflicts with one already returned in the session is not returned.
- A selector with `requires_contract_verification` (`GoalAwareSetSelector`) is refused, because
  only the Kernel runs TaskSpec extraction and the check of the compiled context.
- The steps from selection to activation now exist in the Kernel and in `mcp_server.py`. Gate
  verdicts cannot diverge, because both use `PolicyGateway` and `ToolRuntime`; a change to the
  Kernel's steps (the candidate pool, constraint enforcement) needs a check of the gateway.
- Kernel defaults and the existing public API do not change. The additions are
  `MCPGatewayServer` and `marmo mcp-serve`.

## Alternatives

- List every Tool in the MCP tool listing: every definition enters the client's context and nothing is
  selected.
- Expose `Kernel.run_goal` as one tool: the gateway would need its own model and could not hand
  a HITL pause back to the client.
- Ask the client's user through MCP elicitation when a gate escalates: that changes who may
  approve (`HitlPolicy.approvers`), so it is left as a separate decision.
- Do not track returned results: the gateway cannot see the client's whole conversation, but a
  Tool result it returned is certainly untrusted content. Without tracking, this path would be
  weaker than the Kernel.
