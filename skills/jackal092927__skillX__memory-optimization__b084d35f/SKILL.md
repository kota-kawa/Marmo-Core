---
skillx:
  name: memory-optimization
  purpose: Keep parallel TF-IDF indexing and search memory-efficient so that speedup does not come from wasteful duplication or unstable RAM growth.
  scope_in:
    - the task processes many documents or queries in parallel
    - intermediate arrays, copies, or worker-local state could increase memory footprint significantly
    - memory efficiency matters for practical parallel speedup
  scope_out:
    - not for unrelated long-running memory leaks outside the task path
    - not for replacing the whole system with a new storage backend
    - not for premature micro-optimization when correctness or main concurrency design is still broken
  requires:
    - visibility into where large collections or copies appear
    - ability to process data in chunks or streams when needed
  preferred_tools:
    - generator or iterator patterns
    - chunked processing
    - careful data-structure choice
    - explicit cleanup of large temporary objects when appropriate
  risks:
    - copying the full corpus into each worker
    - materializing large intermediate lists unnecessarily
    - unbounded cache growth
    - memory-heavy structures offsetting the intended speedup
  examples:
    - input: Parallelize a TF-IDF pipeline without blowing up RAM or duplicating the full dataset per worker.
      expected_behavior: keep data flow compact, reduce unnecessary copies, and preserve correctness while supporting useful concurrency.
---

# Guidance

Treat memory efficiency as part of performance, not as a separate cleanup step.

Prefer process-and-discard or chunk-based patterns over building giant intermediate collections.

Avoid sending more data to workers than needed.
If worker inputs are large, reconsider what can be chunked, shared, or reconstructed locally.

Watch for hidden duplication caused by convenience code.
A parallel version that copies the entire corpus repeatedly may fail the real goal even if it looks faster on a tiny test.

# Notes for Agent

In this task, memory optimization is a supporting skill.
Do not let it dominate the implementation; use it to keep the parallel design practical and scalable.
