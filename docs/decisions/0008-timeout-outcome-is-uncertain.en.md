# 0008. Treat the outcome of an operation after a timeout as uncertain

[日本語](0008-timeout-outcome-is-uncertain.md)

- Status: Accepted
- Date: 2026-09-25
- Evidence: `marmo_core/tool_runtime.py`, `marmo_core/recovery.py`

## Context

Previously, a Tool timeout only abandoned the waiting thread; its handler kept running. The default recovery policy retried timeouts, which could cause duplicate writes or sends.

## Decision

- Record a timeout as an operation with an uncertain outcome; do not automatically retry or substitute another operation for the same operation.
- Add a stoppable process mode for importable Python handlers. In this mode, reject callables that cannot be imported and arguments that are not JSON-compatible before execution. Offer this mode only in POSIX environments where child process groups can be stopped, and explicitly reject it on Windows.
- Retain the existing thread mode for compatibility. Before changing the default to process mode, make a separate compatibility decision that provides a migration path for users' callables and Connectors.

## Consequences

The standard recovery action for a timeout is escalation to a human. Even in process mode, side effects already accepted by an external service cannot be undone. Handlers in strict mode must be importable module-level functions.

## Alternatives

Do not abandon a thread and automatically retry: rejected because it can execute the same side effect more than once.
