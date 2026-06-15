---
skillx:
  name: python-parallelization
  purpose: Parallelize CPU-bound TF-IDF indexing and batch search while preserving identical results to the sequential reference implementation.
  scope_in:
    - the task asks for multi-core speedup of a sequential Python implementation
    - iterations or work units are mostly independent and CPU-bound
    - correctness must remain identical to the original implementation
  scope_out:
    - not for distributed systems or cluster scheduling
    - not for changing the algorithmic semantics of TF-IDF or search ranking
    - not for GPU-specific acceleration work
  requires:
    - a working sequential baseline to compare against
    - multiple CPU cores available
    - functions and data structures that can be serialized safely if process-based parallelism is used
  preferred_tools:
    - concurrent.futures.ProcessPoolExecutor
    - multiprocessing when CPU-bound
    - vectorization before adding concurrency if the bottleneck is array-heavy
  risks:
    - using threads for CPU-bound Python and getting little real speedup due to the GIL
    - pickling failures for nested functions or unsupported objects
    - shared mutable state causing correctness drift
    - order instability or result mismatches relative to the original engine
    - parallel overhead dominating when chunks are too small
  examples:
    - input: Parallelize TF-IDF index building and batch search on an 8-core machine while keeping outputs identical.
      expected_behavior: choose CPU-appropriate parallelism, preserve output equivalence, and structure work so speedup is plausible rather than purely cosmetic.
---

# Guidance

First classify the workload correctly. For TF-IDF indexing and search over many documents/queries, assume CPU-bound work unless the profile clearly shows otherwise.

Prefer process-based parallelism over threads for the heavy compute path.

Preserve semantics before chasing speed:
- keep the same TF-IDF structure and result ordering expectations
- compare outputs to the sequential engine
- avoid hidden algorithm changes disguised as optimization

Parallelize independent work units such as document chunks or query batches.
Use bounded worker counts and avoid tiny task granularity that only adds overhead.

If large objects must be copied to each worker, reconsider chunking and data flow before scaling worker count.

# Notes for Agent

A fast wrong answer is still wrong.
The most common mistakes are GIL-blind threading, non-picklable worker code, and speedup claims that disappear once correctness checks are applied.
