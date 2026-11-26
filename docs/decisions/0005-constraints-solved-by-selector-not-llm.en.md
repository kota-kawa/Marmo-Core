# 0005. Solve set-selection constraints with a solver, not an LLM or retrieval-time filters

[日本語](0005-constraints-solved-by-selector-not-llm.md)

- Status: Accepted
- Date: 2026-07-17
- Evidence: [`benchmarks/README.en.md`](../../benchmarks/README.en.md) (set selection, Policy ablation, B&B comparison), `selector.py`

## Context

For the second layer, which selects a set satisfying dependency closure, conflicts, permissions, and budget constraints, Top-K, greedy, beam search, branch and bound, and LLMs (gpt-4o / gpt-4o-mini) were compared under the same conditions. The location for enforcing permission constraints was also compared across five conditions: retrieval-time filtering / inside the selector / a downstream gate.

## Decision

- Solve constraints over declared metadata with a solver (by default, `GreedyConstrainedSetSelector` orders dependency-closure units by utility). Keep the LLM Set Selector for comparison, but not as the default.
- Enforce permission constraints inside the selector. Do not use hard filters (pushdown) during retrieval. Keep a downstream gate as defense in depth against bypasses.

## Consequences

- Even under its best conditions, the LLM reached only Set F1 0.628 / Exact 25%, below greedy (0.720 / 62%); under-selection was the main cause. Latency was four orders of magnitude higher.
- Retrieval-time filtering degraded cases that were executable with permissions into abstentions, reducing abstain/escalate accuracy from 100% to 50%. The connection to HITL was lost.
- Even an exact solution did not outperform greedy. The bottleneck is the utility function, not the search, so improvements should reflect structural information in `u(i,q)` (capability graphs, outcome metadata).

## Alternatives

- Let an LLM select the set: rejected for the reasons above. Asking natural-language reasoning to enforce constraints also caused all candidates to be eliminated after inferring permission requirements that were not declared.
- Filter by permissions during retrieval: rejected because, although safe, it breaks the ability to escalate.
