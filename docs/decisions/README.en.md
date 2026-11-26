# Architecture Decision Records

[日本語](README.md)

Records of important technical decisions. When changing or adding a decision, review existing ADRs and update the rationale and impact, or record them in a new ADR. File names use the form `NNNN-<slug>.md`; statuses are Accepted / Superseded / Deprecated.

| ADR | Decision | Status |
|---|---|---|
| [0001](0001-single-runtime-dependency.en.md) | Keep runtime dependencies limited to `python-dotenv`; isolate model-related packages in extras and provider ABCs | Superseded by 0007 |
| [0002](0002-research-branches-and-frozen-sha.en.md) | Implement research methods on `research/*` branches and pin the commit SHA used for evaluation | Accepted |
| [0003](0003-absolute-relevance-and-bm25f.en.md) | Use absolute relevance scores and BM25F that downweights SKILL.md bodies | Accepted |
| [0004](0004-third-party-skill-corpus-not-redistributed.en.md) | Exclude the third-party Skill corpus used for benchmarks from git and distributions | Accepted |
| [0005](0005-constraints-solved-by-selector-not-llm.en.md) | Solve set-selection constraints from declared metadata rather than delegating them to an LLM or retrieval-time filters | Accepted |
| [0006](0006-provider-failures-terminate-the-task.en.md) | Terminate tasks as `failed` on provider failures and leave audit logs; CLI exit code is 1 | Accepted |
| [0007](0007-minimal-runtime-dependencies-with-user-approval.en.md) | Keep runtime dependencies minimal; explain the need and impact and get user approval before adding one | Accepted |
| [0008](0008-timeout-outcome-is-uncertain.en.md) | Treat side effects after a timeout as uncertain and do not automatically retry; add a stoppable execution mode | Accepted |
| [0009](0009-task-budget-reservations.en.md) | Fix the task budget and reserve it before running models and Resources | Accepted |
| [0010](0010-execution-snapshot.en.md) | On resume, restore the saved selected Resources and validate the compiled context | Accepted |
| [0011](0011-agent-execution-backends-and-structured-tasks.en.md) | Run Agents through backends and delegate structured tasks to child Kernels with declared dependencies | Accepted |
| [0012](0012-multi-intent-retrieval-and-coverage-selection.en.md) | Decompose multi-intent goals for retrieval and select sets by marginal facet coverage (opt-in; defaults unchanged) | Accepted |

## Format

```markdown
# NNNN. Title

- Status: Accepted
- Date: YYYY-MM-DD
- Evidence: commit / PR / CHANGELOG reference

## Context
## Decision
## Consequences
## Alternatives
```

Update this table when adding an ADR. Put empirical evidence behind the decision in [`benchmarks/README.en.md`](../../benchmarks/README.en.md), user-facing explanations in `CHANGELOG.md`, and the decision and rationale in the ADR.
