# 0015. Task execution right and the call journal

[日本語](0015-execution-right-and-call-journal.md)

- Status: Accepted
- Date: 2026-11-27
- Evidence: `marmo_core/state.py`, `marmo_core/kernel.py`, `marmo_core/budget.py`, `tests/test_kernel_execution_integrity.py`, `tests/test_state_concurrency.py`

## Context

Two Kernels on the same State Store could both reach the handler of the same task; the state conflict surfaced only after the handler had run. When a process stopped right after saving a result (`step` event), the saved continuation (`frame` / `plan`) stayed behind it and the resumed task called the same handler again. A `cancel()` issued while the model was answering was overwritten by the late `completed`. Budget reservations checked the balance and appended separately, so two connections could reserve past the limit.

## Decision

- **Execution right**: `Kernel.run` / `resume` take `StateStore.execution(task_id)` first and stop with `StateConflictError` before any side effect when it is held. The JSONL and SQLite stores use OS file locks, which exclude other instances and processes and are released when the holder dies. The base class default excludes holders of the same instance only.
- **Call journal**: per call id, the log records a `call` event (`started`) before the call is handed to the runtime, the `step` event with the result (carrying `call_id`), and `closed_calls` on the event that saves the continuation past it. On resume, an open entry with a result is continued from without calling the handler; an entry with only a start is recorded as an unknown outcome (`timeout`) and, as in ADR 0008, is not retried automatically.
- **Terminal status**: status-changing writes (`status` / `paused` / `resumed`) are appended conditionally on the version they were decided at and are not written once the task is terminal. No new call starts after a cancellation.
- **Budget**: reserve and settle append conditionally on the version the balance was read at, and re-read on a conflict.
- State files stay at `schema_version: 1`. `call` is an added event kind; `call_id` on `step` and `closed_calls` are added keys. Logs without them load as before.

## Consequences

- The model loop saves a `frame` right after the model requests Tools: one more event per round, and one or two `call` events per call.
- A second `run` / `resume` of a task that is executing raises. Previously both proceeded.
- A custom `StateStore` subclass that needs cross-process exclusion implements `_execution_guard`.
- A call interrupted between the handler finishing and its result being saved is reported as unknown and waits for a person, even if it in fact succeeded.

## Alternatives

- Detecting the conflict from state versions alone: rejected because detection comes after the handler ran.
- Time-limited leases (owner and expiry stored in a row or file): releasing a dead holder needs clocks and renewal. An OS lock is released when its holder exits.
- Writing the result and the continuation as one event: deferred, because it requires restructuring the retry, fallback, and parallel-step paths.
