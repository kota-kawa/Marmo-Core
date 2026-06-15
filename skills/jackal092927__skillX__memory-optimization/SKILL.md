---
skillx:
  name: memory-optimization
  purpose: Keep parallel TF-IDF/index/search execution memory-stable so concurrency gains are not erased by duplication, large temporaries, or runaway RAM growth.
  role: secondary-support
  scope_in:
    - reduce unnecessary data copies across workers
    - enforce chunked/streaming data flow where full materialization is costly
    - keep caches and intermediate structures bounded during parallel execution
  scope_out:
    - not for redesigning the full storage architecture
    - not for unrelated leak hunts outside the indexing/search task path
    - not for micro-optimizations before parallel correctness and partitioning strategy are stable
  requires:
    - visibility into large allocations, copies, and worker-local state
    - ability to alter data flow shape (chunk/process-discard/iterator paths)
    - preserved output equivalence constraints from python-parallelization
  preferred_tools:
    - generator/iterator patterns
    - chunked processing and bounded buffers
    - conservative temporary-object lifecycle management
  risks:
    - full-corpus duplication per worker
    - large intermediate list/materialization patterns
    - unbounded caches masking as speed optimization
    - memory savings that accidentally alter output semantics
  precedence:
    - never trade output equivalence for RAM reduction
    - apply after core parallel design exists; co-tune with workload balancing when chunking drives memory pressure
  examples:
    - input: Parallel TF-IDF indexing runs faster but RAM spikes due to worker data duplication.
      expected_behavior: reduce duplication and intermediate footprint while preserving exact results and practical throughput.
---

# Objective Order (Bundle-Aware)

1. Preserve correctness-equivalent behavior.
2. Keep memory growth bounded under realistic parallel load.
3. Support throughput by reducing wasteful allocation/copy patterns.

# Role Contract

This skill is a **resource-discipline guardrail** for the parallel pipeline.
It should not take over concurrency architecture or scheduling policy, but should constrain them when RAM behavior becomes impractical.

Use it to:
- eliminate avoidable full materialization,
- reduce cross-worker duplication,
- keep temporary and cached state bounded.

# Conflict Resolution Rules

If recommendations conflict:
- correctness constraints from `python-parallelization` remain dominant,
- chunk/scheduling policy from `workload-balancing` may be adjusted when memory pressure is high,
- reject memory "wins" that depend on changing ranking/output semantics.

# Practical Guidance

Prefer process-and-discard flows over giant retained intermediates.
Treat memory metrics as part of performance acceptance, not a post-hoc cleanup task.
Use bounded structures and explicit lifecycle discipline where parallel workers handle large data slices.
