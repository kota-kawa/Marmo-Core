# 0006. Provider failures terminate tasks as `failed` and leave audit logs

[日本語](0006-provider-failures-terminate-the-task.md)

- Status: Accepted
- Date: 2026-09-17
- Evidence: 2080be3c (PR #12), CHANGELOG 0.5.0

## Context

When a provider exception escaped the kernel, `--audit-log` wrote no entries, tasks remained `running` even though side-effecting tools had executed, and they could not be resumed.

## Decision

- Catch `ProviderError` inside the kernel, terminate the task as `failed`, write `audit("task")`, and write `--audit-log` even on failure.
- Use CLI exit code 1 for a terminal failure, rather than 2 for an exception.
- Record provider messages in the audit log and task state after redacting them.

## Consequences

- Automation scripts receive exit code 1 for provider failures (previously 2). Document this in the CHANGELOG.
- Audit logs are always complete. Hash-chain verification succeeds after failures as well.

## Alternatives

- Propagate the exception as-is: rejected because this leaves gaps in the audit log and tasks stuck in `running`.
