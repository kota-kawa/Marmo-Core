# 0010. Restore the selected execution snapshot on resume

[日本語](0010-execution-snapshot.md)

- Status: Accepted
- Date: 2026-09-25
- Evidence: `marmo_core/execution_snapshot.py`, `marmo_core/kernel.py`

## Context

If the catalog, Retriever, or Selector changed after a task was paused for HITL, a different Resource could be selected when the task resumed. The approved operation must match the actual execution target.

## Decision

- When selection is finalized, append the resource identity, fingerprint of its declaration, score, and selection rationale to a `snapshot` state event.
- On resume, restore the saved selection result; do not rerun retrieval or selection. If selection escalates because of insufficient permissions, the Resource set is not yet finalized, so select after permissions are granted.
- After activation, also save the compiled context fingerprint. If a selected Resource or the context changes, terminate the task as failed.
- Append a hash of memory / skill content immediately after policy allows activation. If that content changes while a task is paused at a later activation gate and then resumed, terminate the task as failed.
- Even for an existing task with no snapshot, if its history shows it passed activation / execution, terminate it as failed rather than selecting again from the current catalog. A pause at the selection stage leaves the set unfinalized, so selection may be repeated.
- Exclude Resource outcome statistics (`stats`) from the fingerprint so operational-statistics updates do not invalidate a task.

## Consequences

If the catalog or the content of loaded memory / skills changes while a task is paused, the change prevents that task from executing when resumed. Resumption requires the same selection and compilation result as the original catalog. The snapshot does not save the internal code of the selected executable function or the state of external services. A task paused at activation / execution before snapshots were introduced cannot have its target restored and is rejected.

## Alternatives

- Search and select again each time: rejected because this can change the approved target.
- Copy the entire Resource definition into state: rejected because it would duplicate contents such as memory and settings.
