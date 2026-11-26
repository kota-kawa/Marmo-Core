# 0012. Decompose multi-intent goals for retrieval and select sets by facet coverage (opt-in)

[日本語](0012-multi-intent-retrieval-and-coverage-selection.md)

- Status: Accepted
- Date: 2026-11-24
- Evidence: `marmo_core/decomposition.py`, `marmo_core/coverage.py`,
  `benchmarks/run_toolret_benchmark.py`, `benchmarks/results/toolret.json`,
  the ToolRet section of `benchmarks/README.md`

## Context

Existing evaluations used corpora and labels created in the repository, and most goals had a single request. In the public ToolRet benchmark (ACL 2025 Findings; 35 datasets and 44,453 tools), 726 of a sample of 1,689 queries had multiple tools as answers. Measurements revealed two problems:

1. A single retrieval pass ranks candidates against the full goal sentence, so tools for a dominant request crowd out tools for other requests. With lexical retrieval, all correct answers for only 6.5% of multi-tool queries appeared in the top 10.
2. Existing solvers maximize Σu (the sum of scores for selected units), so adding candidates that seem relevant keeps increasing the objective and does not determine set size. Fixed top-3 had a Set F1 of 0.12.

## Decision

Keep Kernel defaults unchanged and add the following as extension points:

- `DecomposedRetriever`: split a goal into subtasks with a `QueryDecomposer`, retrieve the goal and each subtask with the inner Retriever, and fuse the results. The default `fusion="blend"` replaces the relevance component of the combined score with `(goal relevance + 0.25 × best subtask relevance) / 1.25`, and adds a relevance component for each subtask (`facet.<i>`) to every result. The weight 0.25 was selected on ToolRet's dev split. Weight the goal by the fraction of its terms present in the catalog index (known-term rate, `discount_unknown_terms=True`). Since relevance is measured only against terms known to the catalog, a goal written in a language different from the catalog can receive a high relevance score based on just a few known terms (names or numbers). Counting unknown terms as terms that did not match allows ranking to rely on English subtasks.
- `LLMQueryDecomposer`: use one LLM call to return subtasks and implicit prerequisite steps as a JSON array. On failure, fall back to no decomposition (search using only the goal), and record a warning and `failures` / `last_failure` as the existing LLM assistance layer does.
- `CoverageSetSelector`: greedily maximize the facet-coverage facility-location objective `F(S) = Σ_k Σ_f w_f · max_{i∈S, kind(i)=k} r_f(i)`, stopping when marginal gain falls below `min_gain` (default 0.1). Count coverage separately for each kind `k`. Memory, Skill, Tool, and Agent have different roles, so a Skill or Memory is not redundant just because a Tool helps with the same subtask. Reuse the same helpers as `GreedyConstrainedSetSelector` for units (dependency closure), conflicts, permissions, count / kind / budget constraints, and abstain / escalate handling. Because F is monotone submodular, the greedy algorithm under a cardinality constraint has a `(1 − 1/e)` approximation guarantee.
- `ClauseQueryDecomposer`: a dependency-free, rule-based decomposition baseline. Retain it for comparison, but do not recommend it.

## Consequences

- On ToolRet's test split (856 queries, MiniLM-L6 embeddings + BM25F hybrid, Claude Sonnet for LLM decomposition), decomposition and blend fusion improved nDCG@10 by +0.019 (95% CI [0.012, 0.026]) and Completeness@10 by +0.012 [0.001, 0.023]. Numbers are in `benchmarks/README.md` and `benchmarks/results/toolret.json`.
- Most of the set-selection improvement came from ranking. On the sampled test set (856 queries), of the +0.022 Set F1 from pre-decomposition top-1 to post-decomposition coverage, +0.017 came from post-decomposition top-1, while the added gain from coverage was +0.004 [−0.005, 0.014], not significant. On the full test split (3,920 queries, `toolret-test-full.json`), the added gain from coverage was significant at +0.012 [0.006, 0.017], and +0.021 [0.015, 0.027] with `include_within=0.95` (F1 0.229; oracle top-k 0.234). Coverage selected smaller sets and had higher Exact, but a relative threshold of 0.9 of the top score achieved higher F1 (0.189 vs. 0.181), because ToolRet answers often include nearby candidates (multiple endpoints of the same API). Retain coverage because it selects one item per subtask and kind while preserving dependency closure, conflict, permission, and budget constraints and abstain / escalate handling. Use a relative threshold or an LLM when maximizing F1 is the objective.
- `LLMSetSelector` (Sonnet, top 20) was best at F1 0.243 (top-1 difference +0.067 [0.049, 0.086]). The solver beat the LLM on the repository's synthetic benchmark with declared constraints (ADR 0005), but ToolRet has no declared constraints and benefits from interpreting the meaning of descriptions. Kernel constrains the output of every Selector, so assigning relevance to an LLM and constraints to a solver does not conflict with ADR 0005.
- For Japanese-translated goals (206 queries), lexical retrieval and English-only embeddings barely worked (nDCG@10 0.013 / 0.029); decomposition without discount scored 0.057 and with discount 0.134. For English versions of the same queries, scores were unchanged by discounting (0.268). A fixed higher weight (1.0) did as well for Japanese, but nearly erased the decomposition gain on English dev (nDCG@10 0.276 → 0.266), so switch based on known-term rate rather than a fixed weight.
- Rule-based decomposition brought no gain. It incorrectly decomposed 60% of single-tool queries (LLM: 34%), reduced dev nDCG@10 on BM25 at every fusion weight, and showed no significant difference on hybrid (test +0.005 [−0.000, 0.010], dev −0.008). Decomposition gains depend on decomposition accuracy.
- Retrieval takes `1 + number of subtasks` passes per goal, and LLM decomposition adds one model call. Kernel rejects budgeted tasks because this does not declare `budget_aware`.
- The `facet.<i>` components are a contract between `DecomposedRetriever` and `CoverageSetSelector`. Without these components, coverage behaves as one goal facet (`relevance`) and selects the best unit per kind. In the mixed four-kind set-selection benchmark (28 scenarios, lexical, pool 63), coverage without kind separation scored Set F1 0.536 / Exact 0%, whereas kind-separated coverage matched greedy at 0.609 / 54% (closure 100%, abstain/escalate 100%).
- The first-layer accuracy remains the limit on overall performance. ToolRet's top result has a Set F1 around 0.18, which bounds the gains possible from set selection. Adding LLM reranking improved nDCG@10 by +0.043.

## Alternatives

- RRF fusion: weighting the goal's list still underperformed blend on dev. Retain it as an option.
- Fix the subtask weight at 1.0: loses the English gains described above.
- Max fusion using the best score: short subtasks tend to score higher in relevance, which caused substantial degradation on single-tool queries. Rejected.
- Determine set size with a relative threshold against top relevance: with decomposed rankings, this outperformed coverage on F1 (0.189 vs. 0.181). Rather than making it a standalone Selector, include it as `include_within` in coverage (after coverage, keep candidates whose relevance is at least a specified fraction of the top candidate's, subject to constraints). The test score was 0.189 at 0.95, selected on dev. The default remains `None` (precision-oriented behavior that drops near-duplicate candidates).
- Calibrate per-candidate inclusion probabilities with logistic regression and choose `k` to maximize expected F1: with lexical retrieval, all probabilities were low and the result was no different from top-1.
- Add prerequisite Tools based on matching input and output names (data-flow completion): although 28% of correct sets had input/output name chains, the top starting candidate was often wrong, and the F1 gain was less than +0.01.
