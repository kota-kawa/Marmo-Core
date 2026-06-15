---
skillx:
  name: workload-balancing
  purpose: Distribute indexing and search work across workers so that multi-core parallelism reduces stragglers and achieves real speedup.
  scope_in:
    - parallel workers process document chunks or query batches with potentially uneven cost
    - throughput depends on how work is partitioned, not only on how many workers exist
  scope_out:
    - not for full distributed-system scheduling
    - not for changing TF-IDF correctness rules
    - not for overly elaborate balancing machinery when simple chunking is enough
  requires:
    - a way to partition documents or queries into work units
    - awareness of whether tasks are roughly uniform or highly skewed
  preferred_tools:
    - static chunking for uniform workloads
    - dynamic scheduling when work costs are variable
    - chunk sizes large enough to amortize process overhead
  risks:
    - over-partitioning into tiny tasks
    - heavy stragglers from badly chosen chunk sizes
    - balance logic that adds more overhead than it saves
  examples:
    - input: Speed up TF-IDF indexing/search on an 8-core system where some chunks are more expensive than others.
      expected_behavior: choose chunking and worker scheduling that reduce idle time and preserve correctness.
---

# Guidance

Do not assume more workers automatically mean better throughput.
The quality of partitioning often matters as much as the parallel primitive itself.

For document indexing, start with sensible chunks rather than per-document process spawning.
For query search, think about whether query batches are uniform or whether a dynamic queue is safer.

Tune chunk size to reduce both stragglers and overhead.

# Notes for Agent

This skill should complement `python-parallelization`, not replace it.
Use it when performance depends on better work distribution rather than only on adding processes.
