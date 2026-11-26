# 0003. Use absolute relevance scores and BM25F that downweights SKILL.md bodies

[日本語](0003-absolute-relevance-and-bm25f.md)

- Status: Accepted
- Date: 2026-09-19
- Evidence: 11648de1, 3de214ca (PR #13), CHANGELOG 0.6.0, `benchmarks/README.md`

## Context

The relevance component was a BM25 score divided by the highest score in the same result set. This made the top result score highly for every query, so all cutoffs such as `min_relevance` and `seed_min_relevance` were ineffective: an unrelated goal (ramen) launched the AWS Step Functions skill at 0.63. In addition, SKILL.md bodies (median 667 tokens) were indexed with the same weight as metadata (34 tokens), allowing a long Skill to outrank the intended Tool based on coincidental words in its body.

## Decision

- Define relevance on an absolute scale where a document containing every query term once scores 1.0.
- Use two BM25F fields for metadata and body, and downweight the body with `BODY_FIELD_WEIGHT=0.25`.
- Make the default `RuleBasedSetSelector` respect `min_relevance`. Expose `Kernel(min_relevance=...)`, with a default of 0.0 so it can be calibrated for each corpus.
- Reinterpret the benchmark's default threshold from 0.55 to 0.35.

## Consequences

- Scores and rankings change for existing users. Thresholds calibrated on the old scale need recalibration.
- As a tradeoff of the absolute scale, documents that outperform the reference document tie at 1.0; 2 of 120 items fall from rank 1 (hit@1 66.7% → 65.0%). Overall, BM25F raises hit@1 from 61.7% to 65.0% and paraphrase from 31% to 46%.
- When making future changes that replace the relevance component, evaluate Coverage and abstain accuracy in the second layer (set selection) before deciding whether to adopt them.

## Alternatives

- Keep relative normalization and add workarounds such as `min_seed_token_matches`: rejected because this would patch individual symptoms and abstention would remain fundamentally impossible.
- Do not index the body: rejected because recall for paraphrases / abstracts would fall.
