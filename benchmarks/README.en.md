# Routing Benchmarks

[日本語](README.md)

This suite empirically evaluates Marmo-Core’s core claim: “select only what is needed from a large set of resources, quickly, safely, and without context contamination.” It runs 120 labeled scenarios against a third-party Skill corpus of about 1,000 resources (`resources/skills`).

## Obtaining the corpus

The `resources/skills` corpus (about 260 MB) used by default by `run_benchmark.py` is a **third-party asset copied from an external repository and is included neither in git nor in PyPI distributions (sdist / wheel)**. This is because redistribution licensing has not yet been resolved (see “Notes” below).

If you run `run_benchmark.py` in an environment without the corpus, it stops with an explanatory error rather than a traceback:

- Specify a resource directory you already have with `--resources PATH`.
- Re-collect the corpus with `tools/collect_skills.py` (requires a GitHub token).
- Use another benchmark that includes its corpus (`run_set_benchmark.py` / `run_scale_benchmark.py` / `run_adaptive_benchmark.py`). These run using only `benchmarks/corpus/set_corpus.json` and the generation scripts, so they can be run as-is from the repository checkout or the root of an extracted sdist.

## Running the benchmark

```bash
python3 benchmarks/run_benchmark.py                          # BM25 (zero dependencies)
python3 benchmarks/run_benchmark.py --retriever hybrid-hash  # BM25 + hash embeddings
python3 benchmarks/run_benchmark.py --retriever hybrid-model --semantic-weight 0.9
                                                             # BM25 ∪ real embeddings (requires pip install '.[benchmark]')
python3 benchmarks/run_benchmark.py --query-transform hyde   # HyDE query transformation (derived from proposal A; requires OPENAI_API_KEY)
python3 benchmarks/run_benchmark.py --llm-rerank             # LLM reranking (minimal proposal C; requires OPENAI_API_KEY)
```

Results are saved as JSON under `benchmarks/results/`. The `--semantic-weight 0.9` setting for `hybrid-model` was the best in a sweep from 0.3 to 0.95 (table below). HyDE / reranking LLM responses are saved under `benchmarks/cache/` on the first run (this directory is not tracked by git); rerunning in the same environment deterministically replays cached responses without calling the LLM.

## Scenario design

There are 120 scenarios, grouped into three wording styles.

| Style | Count | Description |
|---------|------|------|
| `direct` | 52 | Task statements whose wording overlaps with resource descriptions (straightforward retrieval) |
| `paraphrase` | 35 | Task statements that deliberately remove lexical overlap through synonym substitution |
| `abstract` | 33 | Task statements that state only the goal without using domain vocabulary |

The corpus contains duplicate capabilities (for example, six TDD skills and multiple security-audit skills), so `expected` is a **list of acceptable resource ID substrings**; a hit is counted if any one matches. This eliminates “false misses” in the old version (one correct answer, 20 cases) where a competing resource in the same category merely ranked first.

## Latest results (120 scenarios / 1,000 resources)

| Metric | BM25 (lexical) | hybrid-hash | hybrid-model (bge-small, w=0.9) |
|------|------|------|------|
| hit@1 / hit@5 / MRR (overall) | 65% / 77% / 0.694 | 62% / 72% / 0.659 | **77% / 87% / 0.810** |
| hit@1 — direct | 85% | 85% | **92%** |
| hit@1 — paraphrase | 46% | 43% | **57%** |
| hit@1 — abstract | 55% | 46% | **73%** |
| recall@20 / recall@50 (overall) | 88% / 91% | 86% / 86% | **97% / 98%** |
| recall@50 — direct / paraphrase / abstract | 98% / 83% / 88% | 98% / 74% / 79% | **100% / 94% / 100%** |
| Warm search latency (mean / p95) | **7.0ms / 15.2ms** | 54.2ms / 62.1ms | 59.2ms / 88.0ms |
| Context tokens | Full catalog: about 221,000 → top-5: about 1,400 (**99.4% reduction**) | Comparable | Comparable |

`hybrid-model` uses `BAAI/bge-small-en-v1.5` (fastembed / ONNX / CPU). The initial index build (embedding all 1,000 resources) took about 140 seconds in this measurement environment and is cached per registry **content** revision (writing back usage statistics does not invalidate the cache). The latency values are from a single run recorded in `benchmarks/results/*.json`; they can vary by about 2× with machine load (accuracy metrics are deterministic and reproducible).

### Before-and-after comparison for the scoring change (absolute relevance + field weighting)

These measurements were taken in the same environment after changing the relevance component from “relative normalization by dividing by the highest score for that search” to an “absolute score based on a document containing every query term once,” and indexing SKILL.md bodies at a lower weight than declared metadata (BM25F, `BODY_FIELD_WEIGHT=0.25`).

| Metric | Before | After |
|------|------|------|
| BM25 hit@1 / hit@5 / MRR | 61.7% / 75.8% / 0.668 | **65.0% / 76.7% / 0.694** |
| BM25 hit@1 — direct / paraphrase / abstract | 90% / 31% / 48% | 85% / **46%** / **55%** |
| BM25 recall@20 / recall@50 | 84% / 90% | **88% / 91%** |
| hybrid-model (bge-small) w=0.5 (default) | 67% / 78% / 0.713 | **70% / 81% / 0.745** |
| hybrid-model (bge-small) w=0.9 (tuned) | 78% / 87% / 0.811 | 77% / 87% / 0.810 |
| hybrid (real OpenAI embeddings) w=0.5 | 68.3% / 81.7% / 0.740 | **72.5% / 88.3% / 0.789** |
| hybrid (real OpenAI embeddings) w=0.9 | 75.0% / 92.5% / 0.825 | 74.2% / 92.5% / **0.829** |

- **Only two cases are affected by clipping from absolute scoring.** Dividing by a query-specific constant should not change rankings in principle, but documents above the reference document are capped at 1.0 and become tied. When measured with the same code but reverting only the divisor to the old method, hit@5, recall@20, and recall@50 matched exactly; hit@1 changed from 66.7% to 65.0% (MRR 0.702 to 0.694), with two of 120 cases falling from rank 1. The improvements in the table come from field weighting; absolute scoring accepts those two cases as the cost of making the abstention threshold work.
- **Direct fell from 90% to 85%, while paraphrase rose from 31% to 46% and abstract from 48% to 55%.** This reflects fewer matches on words that happen to appear in the body and stronger matches on declared metadata.
- **The default `semantic_weight=0.5` also improves with real embeddings** (hit@1 by +3–4 points, recall@50 by +5–7.5 points). The tuned 0.9 setting is comparable (within ±1 scenario). The `semantic_weight` sweep documented in the old README (where 0.9 was best) used the pre-change scoring and needs to be run again.
- **Comparisons across resource types now work**: for “read a local text file safely,” `tool.marmo.samples.read-text` ranks first out of 1,030 resources (0.567), ahead of an XXE-checking skill with 7,551 body tokens (0.790).

## LLM-assisted routing (HyDE / LLM reranking, gpt-4o-mini)

We measured two ways to add a small LLM call to Layer 1 (derived from proposal A in 15.2 / minimal proposal C) under the same conditions as above.

| Metric | HyDE + BM25 | Rerank + BM25 | HyDE + hybrid-model | Rerank + hybrid-model | HyDE + rerank + hybrid-model |
|------|------|------|------|------|------|
| hit@1 / hit@5 / MRR | 66% / 83% / 0.729 | 79% / 86% / 0.819 | 87% / 94% / 0.894 | 85% / 92% / 0.879 | **92% / 97% / 0.936** |
| hit@1 — direct | 79% ⚠ | 94% | 92% | 94% | **98%** |
| hit@1 — paraphrase | 46% | 60% | 80% | 80% | **86%** |
| hit@1 — abstract | 67% | 76% | 85% | 76% | **88%** |
| recall@20 / recall@50 | 90% / 93% | 88% / 90% | 98% / 100% | 96% / 99% | **100% / 100%** |

- **HyDE (query transformation)** rewrites the task statement once into a “hypothetical resource description” using one LLM call, then searches. It substantially helps paraphrase / abstract cases, but **when combined with BM25 alone, direct falls from 90% to 79%** (the rewrite dilutes the original exact vocabulary). This regression nearly disappears when combined with embedding search.
- **LLM reranking (minimal proposal C)** shows the LLM lightweight metadata for the top 50 candidates and asks it to reorder them. It raises hit@1 at low cost (BM25 alone: 61% → 79%), but **cannot help if the candidate pool lacks the correct answer, and recall@50 is capped at the Layer 1 value** (remaining at BM25’s 90%). This directly demonstrates the Layer 15 claim that “Layer 1 recall sets the upper bound for later stages.”
- **The full stack (HyDE + reranking + hybrid-model) performs best**: hit@1 is 92% and recall@20 is 100%. It can provide Layer 2 (proposal H, set selection) with a candidate pool that always contains the correct answer in its top 20.
- **Cost and latency**: Each task makes one HyDE call (short text) and one reranking call (about 2–3k tokens). With gpt-4o-mini, the total for 120 scenarios is on the order of tens of yen. Without caching, warm latency is about 1.8–2.4 seconds per query, two orders of magnitude higher than non-LLM configurations (4–63ms). See each JSON file for detailed latency values.

## Interpreting the results

- **Result JSON files have two provenance formats.** Files with a `provenance` key (schema 2) record the 40-hex `marmo_core_commit`, whether the checkout was dirty, dataset revisions, input SHA-256 hashes, models, and arguments. Legacy files lack it: their `marmo_core_commit` is an 8-character short SHA or missing (the 15 `adaptive-*`, `scale-routing-*`, and `set-selection-*` files). Re-measure at the recorded commit before comparing a legacy number with a new run. Legacy ToolRet results fetched the dataset from the moving `main` branch, so the data version cannot be identified (both repositories were last updated in 2025-03, and downloads are now pinned to those commits).
- **The style breakdown accurately shows the strength of proposal A (the rule-based approach)**: hit@1 is a practical 90% for direct cases with overlapping vocabulary, but drops sharply for paraphrases (29%) and abstractions (48%). This quantitatively supports the weakness of proposal A in Section 15 of the requirements document (“depends on lexical matching”).
- **hybrid-hash is a zero-dependency offline alternative, not true semantic search.** It slightly improves paraphrase (+5 points), worsens abstract, and is on par with BM25 overall. The main proposal B configuration is model-based embeddings (hybrid-model).
- **Real embeddings (hybrid-model) demonstrate proposal B’s claim**: hit@1 61% → 77%, paraphrase 29% → 57%, abstract 48% → 70%, recall@50 90% → 99% (paraphrase 83% → 97%). This assumes candidate generation is expanded from “BM25 top results only” to the **union of BM25 results and embedding neighbors**. Reranking only BM25 candidates would omit paraphrases with no lexical overlap from the pool, capping recall at the BM25 ceiling.
- **Warm latency of about 60ms for hybrid configurations** comes from computing cosine similarity against the entire corpus in pure Python for every query. This is acceptable for 1,000 resources, but ANN or hierarchical routing (proposal I) is required at 10k or more.
- The old version’s hit@1 of 70% (one correct answer, 20 cases) was found to correspond to 90% for direct cases after labeling multiple acceptable answers. It cannot be compared directly with the old values.
- **Latency** was the main goal of the inverted index + BM25 implementation (v0.3.0), improving performance by about 500× over the v0.2 difflib implementation (about 2,460ms).
- **recall@K measures the input quality for Layer 2 (set selection / proposal H in Section 15 of the requirements document)**: the Set Selector chooses from the top K candidate pool, so no Selector can recover an answer that is not among the K candidates. BM25 has 90% recall@50 (83% even for paraphrase cases), which meets the condition for the pipeline “reduce to 50 candidates with BM25 → constrained set optimization.” Since labels match any acceptable ID, recall@K is equivalent to hit@K.

## Set-selection benchmark (Layer 2 / proposal H)

`run_set_benchmark.py` evaluates Layer 2 (set selection) with set metrics. Its corpus is a **four-type mixed, constrained corpus** (63 resources: 12 domains × {memory, skill, primary tool, alternate tool, agent}; dependency chains agent→primary tool→skill; declared conflicts between primary and alternate tools; domains with permission gates; and tools with missing dependencies) generated by `generate_set_corpus.py`, plus 28 scenarios with gold sets (selected 24 / escalate 2 / abstain 2).

```bash
python3 benchmarks/generate_set_corpus.py                    # regenerate corpus and scenarios
python3 benchmarks/run_set_benchmark.py --pool 63            # BM25 retrieval + selection
python3 benchmarks/run_set_benchmark.py --retriever hybrid-model --pool 63
python3 benchmarks/run_set_benchmark.py --retriever hybrid-model --distractors resources/skills --pool 50
python3 benchmarks/run_set_benchmark.py --llm-selector --llm-model gpt-4o   # also compare the LLM Set Selector (requires OPENAI_API_KEY)
python3 benchmarks/run_set_benchmark.py --retriever graph-hybrid-model --distractors resources/skills   # proposal E graph expansion
```

**Comparators**: `topk` (Top-1 per type, the v1 RuleBasedSetSelector baseline with no constraint inference); `greedy` (first proposal H solver, `GreedyConstrainedSetSelector`: greedily selects by total utility Σu per dependency closure, satisfying conflict, permission, and budget constraints); `beam` (second proposal H solver, `BeamSearchSetSelector`); `bnb` (exact proposal H solver, `BranchAndBoundSetSelector`: exhaustively searches include/exclude choices per dependency closure with branch-and-bound and an admissible upper bound, returning the **exact optimum** for Σu; used to measure the gap from approximate solvers); `llm` (when `--llm-selector` is specified, proposal C applied to Layer 2, `LLMSetSelector`: presents candidate metadata, dependencies, conflicts, permissions, and budget in one LLM call and asks for a set or abstain/escalate in JSON. **Responses are evaluated as-is without constraint repair** — whether the LLM follows the constraints is itself measured). All Selectors return `SelectionResult = selected | abstain | escalate`. LLM responses are saved under `benchmarks/cache/set-selector-*.json` (not tracked by git) and deterministically replayed on reruns in the same environment (temperature=0).

### Results (min_relevance=0.55; rerun on 2026-07-17. The lexical column was remeasured with absolute relevance on 2026-09-19)

| Metric | topk (lexical) | greedy (lexical) | llm gpt-4o (lexical) | topk (hybrid) | greedy (hybrid) | llm gpt-4o (hybrid) | greedy (hybrid + 1,000 Skill distractors) |
|------|------|------|------|------|------|------|------|
| Set F1 / Exact Match | 0.438 → 0.454 / 0% | **0.582 → 0.577 / 50% → 54%** | 0.488 / 8% | 0.667 / 0% | **0.720 / 62%** | 0.628 / 25% | 0.442 / 33% |
| Dependency Closure Rate | 29% | **100%** | **100%** | 0% | **100%** | 96% | **100%** |
| Conflict-Free / Policy-Feasible | 100% / 100% | 100% / 100% | 100% / 100% | 100% / 100% | 100% / 100% | 100% / 100% | 100% / 100% |
| abstain/escalate precision | 0% | **100%** | **100%** | 0% | **100%** | **100%** | 25% |
| Layer 1 gold recall (upper bound) | 66% | 66% | 66% | **100%** | **100%** | **100%** | 58% |
| Mean selection latency | 0.03ms | 0.08ms | about 1.2 sec | 0.04ms | 0.07ms | about 1.0 sec | 0.17ms |

gpt-4o-mini performs even worse under the same conditions (lexical: Set F1 0.228 / status precision 32%; hybrid: 0.408 / 54%), showing that a small model is insufficient for constrained set selection. beam is nearly identical to greedy, but slightly worse with hybrid in this rerun (0.708 vs. 0.720)—the set maximizing Σu is not necessarily the set maximizing gold F1. Branch-and-bound (bnb) proved Σu optimality in all 28 scenarios (0.10ms mean), but its gold F1 matched greedy for lexical (0.582) and reached the same set as beam for hybrid, below greedy (0.708).

### Interpreting the results

- **Top-K systematically violates set constraints**: with hybrid retrieval, Dependency Closure Rate is 0% (it selects an agent without its dependency, the primary tool), and Exact Match is 0%. Greedy preserves 100% closure and achieves a higher Set F1, directly demonstrating that **“set selection” in F-RETR-04 cannot be replaced by the top K ranked results**.
- **The LLM Set Selector (proposal C, Layer 2) does not beat the solver**: even in the best condition (gpt-4o, temperature 0, 100% gold recall with hybrid, constraints and selection rules stated explicitly in the prompt, with few-shot examples), its Set F1 0.628 / Exact 25% falls short of greedy (0.720 / 62%) and its latency is four orders of magnitude higher (about 1 sec vs. 0.07ms). Of 18 errors, 16 were **under-selection of a strict subset of the gold set** (dropping a specialist agent or memory even when explicitly instructed); there was no over-selection. Constraint satisfaction was mostly maintained (96% closure), and abstain/escalate decisions were 100% accurate. During prompt development, we also observed the model inferring **undeclared permission requirements from permission names** (e.g. `kernel.read`), causing a near-total failure (Set F1 0.03). This supports proposal H’s design decision that constraints should be resolved from declared metadata rather than natural-language inference.
- **The key to greedy ordering is total utility Σu per dependency closure**: naive greedy based on individual candidate scores first selects the high-scoring “alternate tool,” then blocks the intended agent+tool+skill chain through the conflict constraint (measured during implementation: Set F1 0.375 → 0.625 when ordering by unit utility).
- **The exact solver does not beat greedy—the bottleneck is the utility function, not search**: branch-and-bound proves Σu optimality across all scenarios (“proven optimal,” 0.10ms mean), and is always at least as good as greedy on Σu. Still, its gold F1 is 0.708 with hybrid, below greedy (0.720). In the sole differing support scenario, a high-scoring conflicting tool (quickdraft 0.641, no dependencies) outranks the gold workbench (0.554, depends on a skill) under Σu (1.937 vs. 1.850), so exact optimization moves **away** from gold. Greedy’s closure-level ordering acts as a structural prior that evaluates resources linked by dependencies as a unit, which aligns with gold. The Layer 2 search comparison (Top-K / greedy / beam / bnb / LLM) is therefore complete; improvement lies not in the search algorithm but in **incorporating structural information into u(i, q) (proposal E / observed metadata)**.
- **Abstention (15.6) trades off Coverage and Selective Accuracy**: sweeping the relevance threshold gives, with hybrid, {rel≥0.55: Coverage 71% / abstain·escalate 100%}, {rel≥0.50: 93% / 25%}, {no threshold: 100% / 0%}. The composite score includes trust, cost, etc., so it cannot be used for abstention; **only the relevance component should be thresholded**. Absolute relevance makes the threshold mean the same thing across queries for the first time (measured on 1,000 Skills: median relevance for a gold answer 0.72 / 10th percentile 0.22; top irrelevant result for unrelated tasks 0.15–0.52), but **the distributions still overlap and cannot be fully separated**. Thresholds must be set from measurements on each catalog, and the library default remains 0.0 (the benchmark script’s default is read as 0.35 rather than 0.55 due to the changed threshold scale).
- **Layer 1 gold recall is the upper bound for Layer 2** (reconfirming the previous PR’s finding): after adding noise from 1,000 Skills, gold recall drops to 58%, and greedy reaches only Set F1 0.442. Candidate generation at large catalog sizes (proposal I) is the next bottleneck.

## Proposal E: Candidate augmentation with capability and dependency graphs (extended proposal E in 15.2)

`--retriever graph-<base>` (`graph-lexical` / `graph-hybrid-model`, etc.) expands the base Retriever’s seed candidates with `CapabilityGraphRetriever` (`marmo_core/graph_routing.py`; zero dependencies and deterministic). Starting from the top seed candidates (5 by default), it follows up to two hops of declared metadata edges (depends_on / reverse dependencies / peers in the capability namespace), and propagates each seed’s relevance to reached resources with decay (0.8 per hop by default). This brings in structurally complementary resources (memory, skill, agent) whose vocabulary does not match the task, gives them relevance high enough to pass the abstention gate, and raises total utility Σu per dependency closure — a Layer 1 response to the “utility function does not know structure” bottleneck established by the B&B comparison.

| Configuration | gold recall | greedy Set F1 | Exact | Safety metrics |
|------|------|------|------|------|
| lexical → graph-lexical | 66% → 66% | 0.582 → **0.588** | 50% → **54%** | non-inferior |
| (remeasured with absolute relevance) lexical → graph-lexical | 66% → 66% | 0.577 → 0.577 | 54% → 54% | non-inferior |
| hybrid → graph-hybrid | 100% → 99% | 0.720 → 0.720 | 62% → 62% | non-inferior |
| hybrid + 1,000 distractors → graph | 58% → **68%** | 0.444 → **0.462** | 33% → **38%** | non-inferior |

### Interpreting the results

- **The effect is largest under noise, as intended**: augmentation addresses cases where “the seed is found but its companions fall out of the candidate pool.” Clean hybrid (recall 100%) has no room to improve, so the unchanged result is expected.
- **Three safeguards proved essential in measurement** (each caused a measured regression when removed):
  1. **Suppress false seeds** — At the time, BM25 relevance was relatively normalized, so even an accidental one-word match in an off-catalog task (“full” matching “Full workbench tool”) became a seed with relevance 0.7. When expansion added its dependent skill to the pool, it completed a closure that should not have been formed and flipped a correct abstention into a false selection (symphony scenario). This was fixed by requiring **absolute evidence**: at least two task tokens or embedding similarity of 0.55 or higher. Now that relevance is absolute, the same accidental match falls to around 0.1, so this guard is a second safety net (default unchanged).
  2. **Namespace hub cap (12 items)** — Free-text capabilities in imported catalogs tend to use formulaic phrases. All 1,000 Skill distractors share the “skill instructions” namespace, turning it into a hub that connects every distractor. Without the cap, a noise seed floods the pool with an entire cluster, pushing the gold workbench/agent out and regressing F1 from 0.444 to 0.415.
  3. **Reserve pool slots for structural additions** — By corpus design, workbench (cost 2.0, community trust) and agent (slow) lose to distractors with perfect trust/cost components in the composite score. Even if graph expansion reaches them, pool truncation drops them again, leaving only memory/skill and breaking closure. Reserving slots for added candidates (up to 12 by default) raises recall from 62% to 68%.
- **Limitation: the graph cannot create seeds**. If there is no in-domain seed, as in noisy paraphrase cases, the graph has nothing to expand (all remaining misses at 68% recall have this pattern). The Layer 1 scale bottleneck remains, strengthening the motivation for proposal I. **Calibration coupling** is also an open issue: inherited relevance (seed × 0.8) can land near the abstention gate (0.55).

## Policy ablation (15.6 / where to insert safety constraints)

`--policy-ablation` compares five ways of applying permission constraints in the pipeline (the gate’s PolicyContext disables side-effect escalation to isolate the permission axis; the permission_fit soft component of the search score is shared across all conditions).

```bash
python3 benchmarks/run_set_benchmark.py --retriever hybrid-model --policy-ablation \
    --output benchmarks/results/set-selection-policy-hybrid.json
```

| Condition | Permission handling | Set F1 | Policy-Feasible | Status accuracy | abstain/escalate accuracy | Coverage | Gate activations |
|------|-----------|--------|------|------|------|------|------|
| none | none | 0.720 | 96% | 79% | 50% | 79% | — |
| gate-only | downstream Activation Gate only | 0.720 | 100% | 82% | **100%** | 68% | 3 |
| **selector (default)** | enforced by the selector as constraints | 0.720 | **100%** | **86%** | **100%** | 71% | — |
| pushdown | hard filter at retrieval + selector | 0.720 | 100% | 79% | 50% | 71% | — |
| full | pushdown + Gate | 0.720 | 100% | 79% | 50% | 71% | 0 |

(greedy, hybrid-model, 28 scenarios. The ordering is the same for lexical. beam follows the same trend as greedy; topk is constraint-blind and improves only with gate-only: status accuracy 86% → 89%.)

### Interpreting the results

- **Enforcing constraints inside the selector (the current default) is best.** Constraints are resolved where candidates are visible, allowing both (1) a feasible alternative to be selected and (2) cases that become feasible if a human grants permission to be correctly reported as escalate.
- **A downstream gate alone cannot replan**: if a permission-blind selection creates a set with an infeasible member, the gate can only block (escalate); it cannot choose an available feasible alternative (measured in the incident scenario: the selector condition chose the alternative, while gate-only escalated unnecessarily). For Top-K, which has no constraint reasoning, it is the only safety net, and gate-only improves status accuracy from 86% to 89%.
- **A hard filter during retrieval (pushdown) destroys escalation capability**: candidates lacking permission disappear from the pool, so a scenario that could run if permission were granted degrades into abstain (abstain/escalate accuracy 100% → 50%). This is safer, but it loses the correct connection to HITL (4.12)—the 15.6 design point that filtering is not always better earlier in the pipeline.
- **The downstream gate in full never activates** (after pushdown, an infeasible member cannot enter the set). It contributes nothing to accuracy and serves only as defense in depth for F-GATE-01 (no bypass path).
- **Set F1 is unchanged in all conditions** (0.720). At 63 resources, permissions affect **safety (Policy-Feasible) and status decisions**, not accuracy. The none condition activated an infeasible set in 4% of cases.

## Cross-encoder reranking (15.7 item 4 / non-LLM counterpart to LLM reranking)

LLM reranking (minimal proposal C) greatly improves hit@1 but requires an LLM call per query (about 2 seconds, nondeterministic, and dependent on cached responses for audit). We tested the hypothesis that a small local model reading each (task, resource metadata) pair **jointly** could answer the same question—“How well does this candidate satisfy this task?”—with comparable quality, deterministically, offline, and with no API cost.

```bash
python3 benchmarks/run_benchmark.py --cross-encoder                     # BM25 + cross-encoder
python3 benchmarks/run_benchmark.py --retriever hybrid-model --semantic-weight 0.9 --cross-encoder
python3 benchmarks/run_set_benchmark.py --retriever ce-lexical [--ce-weight 0.3]
```

`CrossEncoderRerankRetriever` (`marmo_core/rerank.py`) uses `CrossEncoderProvider` as an extension point (the core remains dependency-free; the fastembed implementation is on the benchmark side). It maps model scores to [0,1] with a logistic function and **mixes them into the relevance component**. Unlike LLM reranking, which only changes rank order, this preserves the policy components of the composite score (permission, trust, side effects, cost) while also affecting the Layer 2 abstention gate (15.6 thresholds the relevance component).

### Ranking quality (120 scenarios / 1,000 resources)

| Configuration | hit@1 | hit@5 | direct | paraphrase | recall@50 | Warm latency |
|------|------|------|------|------|------|------|
| lexical (baseline) | 61% | 76% | 90% | 29% | 90% | **3.9ms** |
| **lexical + cross-encoder** | 73% | 83% | 90% | 49% | 90% | 2141ms |
| lexical + LLM reranking | **79%** | 86% | 94% | **60%** | 90% | 1834ms |
| hybrid-model (baseline) | 77% | 87% | 94% | 57% | 99% | **63ms** |
| **hybrid-model + cross-encoder** | 76% ⚠ | 88% | 92% | 51% ⚠ | 99% | 3220ms |
| hybrid-model + LLM reranking | 85% | 92% | 94% | 80% | 99% | 2448ms |
| hybrid + HyDE + LLM reranking | **92%** | **97%** | 98% | **86%** | 100% | 2241ms |

The cross-encoder is `Xenova/ms-marco-MiniLM-L-6-v2` (fastembed / ONNX / CPU, reranking pool of 50).

### Effect on set selection (28 scenarios / 63 resources, greedy)

| ce mix weight | gold recall | Set F1 | Exact | Status accuracy | abstain/escalate | Coverage |
|------|------|------|------|------|------|------|
| 0.0 (= lexical baseline) | 66% | **0.582** | 50% | **75%** | **100%** | 61% |
| 0.3 | 66% | 0.458 | 46% | 50% | 75% | — |
| 0.5 | 66% | 0.446 | 38% | 50% | 75% | — |
| 0.7 | 66% | 0.438 | 38% | 50% | 75% | — |
| 1.0 (default) | 66% | 0.431 | 38% | 50% | 75% | 39% |

### Interpreting the results

- **It helps a weak base but not a strong one**: with BM25 alone, hit@1 improves substantially from 61% to 73% (paraphrase 29% to 49%), but there is **no improvement on top of proposal B’s hybrid** (77% → 76%; paraphrase actually regresses from 57% to 51%). Once embeddings capture semantic similarity, the ms-marco cross-encoder has no additional signal to contribute. It did not match LLM reranking under any condition (best comparison: 76% vs. 92%).
- **It is not a “cheap alternative” on CPU**: scoring 50 candidates takes about 1–3 seconds, comparable to or longer than LLM reranking (about 1.8–2.4 seconds) (8-core WSL2 / ONNX). The cross-encoder’s advantages are not speed but **determinism, offline operation, and zero API cost**. The latency conclusion may change with a GPU.
- **It regresses Layer 2; the cause is calibration, not ranking**: gold recall is the same in all conditions (66%; reranking does not change pool membership), yet Set F1 falls from 0.582 to 0.431 and Coverage from 61% to 39%. In other words, **the right candidates are present but no longer selected**. Lowering the mix weight does not fix this; performance degrades monotonically, and even at 0.3 abstain/escalate accuracy falls from 100% to 75%. The cross-encoder score distribution is not aligned with the abstention gate calibrated at relevance 0.55 (15.6), reproducing in another layer the **calibration coupling left open by proposal E**. Using reranking with Layer 2 therefore also requires recalibrating the threshold.
- **Design implication**: changes that “replace the relevance component” cannot be accepted based on Layer 1 ranking metrics alone. Since the abstention gate is shared, viability can only be established after measuring Layer 2 Coverage / Selective Accuracy as well.

## Proposal I: Hierarchical coarse-to-fine routing (15.2 / 10k–100k scale)

This evaluates the central claim 2 in 12.1: “routing can maintain accuracy, latency, and context cost even with catalogs of 10,000 or more resources.” `generate_scale_corpus.py` deterministically generates a synthetic catalog (domain → provider → hierarchy of five resource families; with dependencies and conflicts matching the gold corpus structure, making noise structurally indistinguishable). `run_scale_benchmark.py` compares flat and hierarchical retrieval on 28 gold scenarios plus 6 cross-domain scenarios (gold sets span two domains). Catalog JSON is not committed because it can be regenerated deterministically.

```bash
python3 benchmarks/run_scale_benchmark.py --size 10000    # all configurations (requires fastembed)
python3 benchmarks/run_scale_benchmark.py --size 100000 \
    --retrievers lexical,hier-namespace-lexical,hier-provider-lexical
```

`hier-<strategy>-<base>` uses `HierarchicalRetriever`: stage 1 (coarse) ranks groups with BM25 (or a blend with group-centroid cosine for hybrid bases) and selects the top `route_k` (default 3); stage 2 (fine) applies the base Retriever only to members of the selected groups. The four group-building strategies are capability namespace (`namespace`), provider / MCP server (`provider`), permission boundary (`permission`), and k-means over description embeddings (`embedding`).

### 10,063 resources (63 gold + 10,000 synthetic / 200 domains, 73 providers / greedy, pool 50, route_k 3)

| Configuration | gold recall@50 | Set F1 (regular/cross) | Exact | Status accuracy | abstain/escalate | p50 / p95 | Scanned share | Cluster Recall (measured/oracle) |
|------|------|------|------|------|------|------|------|------|
| lexical (flat) | 64% | 0.617(0.565 / 0.822) | 50% | 82% | 100% | 6.1ms / 49.5ms | 100% | — |
| hybrid-model (flat) | 64% | 0.550(0.519 / 0.671) | 30% | 88% | **50% ⚠** | **1036ms / 1199ms ⚠** | 100% | — |
| hier-namespace-lexical | 60% | 0.537(0.480 / 0.767) | 37% | 79% | 100% | 6.4ms / 18.9ms | 18.3%※ | 80% / 100% |
| hier-provider-lexical | 60% | 0.571(0.511 / 0.811) | 40% | 82% | 100% | 14.9ms / 91.1ms | 19.3%※ | 80% / 100% |
| hier-permission-lexical | 64% | 0.617(0.565 / 0.822) | 50% | 82% | 100% | 90.5ms / 1663ms | 94.5% ⚠ | 100% / 100% |
| hier-embedding-lexical | 37% ⚠ | 0.263(0.243 / 0.343) | 3% | 82% | 100% | 24.3ms / 40.0ms | 20.9%※ | 57% / 72% ⚠ |
| **hier-namespace-hybrid-model** | **69%** | **0.589(0.524 / 0.848)** | **47%** | **94%** | **100%** | **24.1ms / 31.3ms** | **0.9%** | 78% / 100% |
| hier-provider-hybrid-model | 67% | 0.552(0.506 / 0.735) | 33% | 94% | 100% | 44.0ms / 103.7ms | 3.2% | 80% / 100% |
| hier-embedding-hybrid-model | 35% ⚠ | 0.241(0.226 / 0.300) | 3% | 91% | 100% | 51.7ms / 85.6ms | 4.0% | 39% / 72% ⚠ |

※ The scanned share for lexical bases includes the flat fallback when there is no signal (6 scenarios, counted as 100% scanned), averaged in. For queries successfully routed, namespace scans about 0.8%.

### 100,063 resources (lexical-based only; flat hybrid full-corpus cosine already fails at 10k)

| Configuration | gold recall@50 | Set F1 | Exact | p50 / p95 | Scanned share | Cluster Recall (measured/oracle) |
|------|------|------|------|------|------|------|
| lexical (flat) | 64% | 0.617 | 50% | 37.8ms / **808.6ms ⚠** | 100% | — |
| hier-namespace-lexical | 60% | 0.549 | 40% | 18.1ms / **52.3ms** | 17.9%※ | 80% / 100% |
| hier-provider-lexical | 60% | 0.591 | 43% | 56.0ms / 273.8ms | 19.0%※ | 80% / 100% |

**Remeasurement after lexical search pruning**: After `LexicalRetriever` began stopping scoring at the upper bound of the composite score, we compared main (59275d58) with the same 100,063 resources, 34 scenarios, and `min_relevance` 0.35. Flat lexical p50 fell from 40.0 to 15.1ms, p95 from 839.0 to 101.5ms, and mean from 148.4 to 21.4ms. All quality metrics, including Set F1 0.595, were identical ([`results/scale-lexical-100000-before.json`](results/scale-lexical-100000-before.json) / [`-after.json`](results/scale-lexical-100000-after.json)). The 100k table above is from an older run with no provenance recorded (relative relevance, `min_relevance` 0.55) and is retained as-is for comparison.

### Interpreting the results

- **Evidence for central claim 2 (10k)**: full-corpus cosine scanning with flat hybrid reaches about 1 sec p50 at 10k and is not viable. Namespace hierarchy reduces scanning to **0.9%**, bringing p50 to 24ms (**43×**), while also outperforming flat on quality: gold recall 69% vs. 64%, Set F1 0.589 vs. 0.550, and status accuracy 94% vs. 88% (hierarchical routing structurally removes the 10,000 noise resources from the candidate pool). Achieving this without an ANN index or added dependencies is the value of proposal I.
- **Hierarchical routing restores abstention under noise**: flat hybrid semantically matches off-catalog tasks (such as composing a symphony) to noise, and abstain/escalate accuracy collapses to 50%. Hierarchical routing keeps the pool small and irrelevant, allowing the abstention gate to work correctly and maintaining 100% across all hierarchical configurations.
- **Declared taxonomy is best for group construction; learned clusters fail**: k-means (embedding strategy) groups “similar descriptions,” splitting gold four-type sets (memory/skill/tool/agent have different descriptions) across **different clusters** (oracle cluster recall 72%, a low ceiling imposed by the split itself). Routing partitions should be built from declared metadata aligned with dependency closure (capability namespace, provider), leading to the same conclusion as proposal E: “structure comes from declarations, not language similarity.” The permission boundary is ineffective for routing because public resources make up 94.5%; as in 15.6, permissions should be handled as constraints inside the selector.
- **Cross-domain performance improves over flat despite concerns about multi-stage error propagation** (0.848 vs. 0.671): route_k=3 picks up groups from both domains, and each group contains less noise. For single-domain tasks (the usual 28), the **first-stage routing error** remains the bottleneck (cluster recall 80% vs. oracle 100%, mainly paraphrases); this also explains the Set F1 gap from flat lexical (0.537–0.571 vs. 0.617).
- **Routing accuracy does not degrade at 100k**: cluster recall and Set F1 are nearly unchanged from 10k to 100k (errors depend on domain count and wording, not catalog size). Flat lexical p95 degrades to 808ms, while hier-namespace remains at 52ms (15× faster). BM25 p50 is still 38ms at 100k, so **flat remains more accurate with a lexical base**—the main value of hierarchy is making embedding-based retrieval scale.
- **Warm-up**: hybrid configurations initially compute embeddings for the entire catalog (about 272 seconds for 10k resources on CPU / bge-small). All configurations within a process share the embedding memo, so later configurations take only a few seconds.

## Layer 3 (adaptation): proposal F routing cache and execution feedback (15.4 / F-LOG-08)

Layers 1 and 2 are static and derive a set from scratch each time. Layer 3 asks “how can past executions improve the next selection?” and therefore requires **traffic replay and per-task outcomes**, rather than a single pass through scenarios. `run_adaptive_benchmark.py` provides both and adds the end-to-end metric required by 15.7 (Task Success Rate).

```bash
python3 benchmarks/run_adaptive_benchmark.py --retriever lexical --epochs 3
python3 benchmarks/run_adaptive_benchmark.py --retriever hybrid-model --cache-embeddings model --epochs 3
python3 benchmarks/run_adaptive_benchmark.py --retriever hybrid-model --cache-embeddings model \
        --threshold-sweep 0.30,0.40,0.50,0.60,0.72          # similarity-gate sweep (mean over 4 seeds)
python3 benchmarks/run_adaptive_benchmark.py --drift-probe   # stale cases after registry changes
python3 benchmarks/run_adaptive_benchmark.py --feedback --epochs 5   # write back observed metadata
```

### Task Success Rate is a **simulation**

Executing all 28 scenarios for real would require 28 real backends, so success is derived from routing results with an explicit fulfillment model (documented in the report’s `task_success_model`).

- `selected` scenario: success if the selected set is a **superset of gold**, dependency-closed, and executable under the permissions. Extra resources count as context cost, not as an incorrect answer.
- `abstain` / `escalate` scenarios: success if the expected status is returned. **Correctly declining is success** (15.6).

Determinism matters: the same routing decision must always produce the same feedback signal for changes across epochs to be attributable to learning.

### Experiment 1: Routing-cache configurations (3 epochs × 28 scenarios, seed 7)

`hybrid-model` base (proposal B at Layer 1, greedy at Layer 2):

| Configuration | TSR | Hit rate | Set F1 | Status accuracy | p50 (hit / miss) | regret | Cases |
|------|------|------|------|------|------|------|------|
| no-cache (baseline) | 0.679 | — | 0.720 | 86% | 2.619ms (— / 2.619) | — | — |
| **cache-lexical** | 0.679 | 45% | 0.720 | 86% | 2.209ms (**0.081** / 2.559) | 0 | 19 |
| cache-semantic | 0.679 | 45% | 0.720 | 86% | 2.269ms (0.719 / 2.983) | 0 | 19 |
| cache-poisoned (also stores failures) | 0.679 | 45% | 0.720 | 86% | 2.169ms (0.109 / 2.644) | 0 | 28 |
| cache-stale-blind (version check disabled) | 0.679 | 45% | 0.720 | 86% | 2.225ms (0.080 / 2.447) | 0 | 19 |

With a `lexical` base, no-cache p50 is 0.071ms and cache-hit p50 is 0.054ms (the benefit disappears because the pipeline is already cheap).

### Experiment 2: Similarity-gate sweep (hybrid-model + model embeddings, mean over 4 seeds [min–max])

| Threshold | Configuration | Hit rate | TSR | Set F1 | Status accuracy | regret / rescue |
|------|------|------|------|------|------|------|
| 0.30 | cache-semantic | 54% | 0.607 [0.595-0.619] ⚠ | 0.610 | 92% | 49 / 25 |
| **0.40** | **cache-semantic** | **60%** | **0.744 [0.714-0.774]** | **0.731** | **91%** | 21 / **43** |
| 0.50 | cache-semantic | 50% | 0.699 [0.667-0.714] | 0.744 | 90% | 3 / 10 |
| 0.60–0.72 | cache-semantic | 45–47% | 0.679 (same as baseline) | 0.720 | 86% | 0 / 0 |
| 0.30 | cache-lexical | 49% | 0.670 [0.643-0.702] ⚠ | 0.698 | 89% | 13 / 10 |
| 0.40–0.72 | cache-lexical | 45–47% | 0.679 (same as baseline) | 0.720 | 86% | 0 / 0 |

### Experiment 3: Registry changes (republish 25% of cached resources as 2.0.0; promote `side_effect` to irreversible)

| Admission rule | TSR | Hit rate | Stale misses | Reuse of stale cases | **Unsafe replays** |
|------|------|------|------|------|------|
| version-checked (default) | 0.571 | 25% | 9 | 0 | **0** |
| id-only | 0.571 | 57% | 0 | 9 | **9 ⚠** |

### Experiment 4: Execution feedback (5 epochs, lexical, writeback by `ExecutionEvaluator`)

| Condition | TSR | Set F1 | Exact | TSR by epoch |
|------|------|------|------|------|
| static | 0.571 | 0.582 | 50% | 0.571 / 0.571 / 0.571 / 0.571 / 0.571 |
| **feedback** | **0.600** | **0.607** | 53% | 0.571 / **0.607** / 0.607 / 0.607 / 0.607 |

### Interpreting the results

- **With the default configuration, caching only makes things faster; quality is unchanged**: exact repeat visits replay the same set as the pipeline, so TSR, Set F1, and status accuracy match baseline and regret is 0. With a hybrid base, cache-hit latency is **0.081ms vs. 2.6ms (32×)**. But **the gain disappears when the pipeline is cheap** (with a lexical base, 0.054ms vs. 0.071ms). The value of proposal F scales with Layer 1 cost.
- **Lowering the threshold makes the cache a quality mechanism for the first time**: using a model-embedding case index at **t=0.40** raises TSR from **0.679 to 0.744** (above baseline in all 4 seeds) and status accuracy from 86% to 91%. The mechanism is straightforward: **a paraphrased query inherits the set that succeeded for its directly worded sibling query** (43 rescues vs. 21 regrets). Paraphrases are where Layer 1 is weakest (no-cache paraphrase TSR is 0.25), and the cache fills that gap. At t=0.30, unrelated cases also get reused and results collapse (TSR 0.607 / regret 49).
- **A lexical case index does not generalize**: cache-lexical is always the same as baseline at t≥0.40 (only exact repeat visits match); at t=0.30, regrets exceed rescues and performance regresses. **Embedding provides the cache’s generalization; lexical similarity does not allow the threshold to be lowered safely.** The cost is about 0.6ms per query for cosine computation (0.719ms on a hit vs. 0.081ms).
- **Staleness is a default behavior, not an “accident”**: republishing 25% produces **9 unsafe replays** with the id-only rule—the selector returns a set approved when `side_effect=read` even though it includes a resource promoted to `irreversible`. The default `id@version` rule holds this to zero, but hit rate falls from 57% to 25%. **Cache correctness directly trades off against hit rate**, and revision numbers are too coarse (even an unrelated `add` flushes everything). The Activation Gate (F-GATE-01, established as permanent in 12.1) still acts as the last line of defense, while version checking prevents the gate from ever receiving a dangerous set.
- **Storing failed cases is harmless but useless**: cache-poisoned also records failed routes, but admission rejects them as `failed-case`, so they are never reused (18 miss reasons). Only the number of cases grows from 19 to 28. Recording failures is useful for proposal D (as a learning signal for utility), not for proposal F reuse.
- **The feedback loop is closed, and its effect is small but real**: writeback by `ExecutionEvaluator` raises TSR from 0.571 to 0.600 and Set F1 from 0.582 to 0.607. Improvement **plateaus after epoch 1** (unchanged afterward); direct remains at 0.875, while **only paraphrase moves, from 0.167 to 0.233**. Since `success` has weight only 0.05 in the composite score, only close candidates change rank. In light of the B&B conclusion (the bottleneck is the utility function u(i, q), not search), this confirms that **proposal D targets the right place** and that **one fixed-weight 0.05 component is insufficient**.
- **Limitations**: TSR is simulated; it does not include real-backend failures (timeouts, schema mismatches, external API errors). Traffic is repeated over 28 scenarios, not a real-world long-tail distribution. The cache hit rate **depends entirely on task repetition**, so the 45–60% here should not be read as an operational estimate.

## Independent test, execution outcomes, and adversarial metadata

The existing evaluations of 120 and 28 cases above are exploratory results also used during configuration search. `run_evidence_benchmark.py` adds a separate, small evaluation. Each task in `evidence_cases.json` is marked `dev` / `test` and assigned a unique task-series `family`; the script checks that a series never appears in both. Only dev execution outcomes are recorded in `CaseBasedRouter`, and test is evaluated once while held fixed. The corpus consists of bundled Memory / Tool / Agent resources and two Skills from `examples/resources/core_resources.json`. Gold sets are explicit for each task.

```bash
python3 benchmarks/run_evidence_benchmark.py
```

For Tool tasks, only selected Tools are executed through the normal activation / execution gates with **bundled real handlers**. In addition, `Kernel.run_goal` is exercised with fixed Tool-call responses and its artifact is checked through the public API path. Each case gets a new temporary workspace; write Tools are pre-approved only for their target IDs. The Tool `status=success` value is checked separately from file contents, ZIP contents, and return values. The denominator of `tool_success_rate_conditional` is the Tools actually called; the denominator of `task_completion_rate` is all tasks requiring a Tool. The latter counts cases where the correct Tool was not selected and therefore not executed as failures. LLM Tool selection, argument generation, and final responses are fixed, so these values measure single-step Tool-task completion—not completion rates for an agent using a real model or HITL approval quality.

| Fixed test (10 cases, including 6 Tool tasks) | baseline | cache learned from dev executions |
|---|---:|---:|
| Set F1 / Exact | 0.704 / 37.5% | 0.704 / 37.5% |
| abstain / escalate accuracy (1 each) | 2/2 | 2/2 |
| Tool success rate (5 actually executed) | 5/5 | 5/5 |
| Task completion rate (6 Tool tasks) | 5/6 | 5/6 |
| Task completion via `Kernel.run_goal` | 5/6 | — |
| cache hit | — | 0/10 |

On dev-series repeat visits, the cache hit on 2 of 8 Tool tasks and produced the correct execution artifacts. On the held-out test series, it hit 0 of 10 cases, so generalization was not established. With the default lexical similarity threshold of 0.72, it does not match a different series; therefore, the hit rate from synthetic repeat traffic cannot be treated as an operational estimate. The number of cases is small, and gold labels were created in this repository rather than independently annotated by a third party, so these results should not be used to claim confidence intervals or generalization performance.

We also add adversarial metadata to the same six fixed-test Tool tasks by filling a notification Tool’s description with words from each task. `keyword_stuffing` and `instruction_payload` remain `trust_level=untrusted`, while `metadata_forgery` also forges declared trust, permissions, side effects, and isolation level. The first two are never selected in all six cases, and the activation gate denies them. In the latter condition, the forged Tool is selected in 6/6 cases and can pass the activation gate. **No dangerous real handler was executed.** This measures an attack candidate arising because the core alone cannot verify the authenticity of metadata declarations; it does not represent actual harm incidents. See `benchmarks/results/evidence.json` under `adversarial_test` for details.

### Tracking forged metadata over time

The six cases above cover Tools only and forge four declarations at once. `run_forgery_benchmark.py` measures, in the same form for every change to retrieval, selection, or routing, which forged declaration gets a decoy how far.

```bash
python3 benchmarks/run_forgery_benchmark.py            # 2 to 4 min, no LLM
```

- **Cases**: the 22 cases of `evidence_cases.json` (dev / test, including two abstain and two escalate cases) and the 28 scenarios of the set-selection corpus (63 resources; two abstain, two escalate).
- **Decoys**: one each for Tool, Skill, and Agent, with two contents. `stuffed` repeats the task text five times as the description (as in the six legacy cases); `clone` copies the name, description, capabilities, and tags of the gold resource of the same kind (only for cases whose gold set has that kind).
- **Declarations**: the honest declaration is that of an unvetted third-party resource that posts to an external service (`trust_level=untrusted`, `net.external` and `message.send`, `side_effect=external`, and `isolation_level=L3` for Tools). Forging replaces each with `verified` / no permissions / `none` / `L0`, over **every combination** (16 for Tools over four declarations, 8 for Skills and Agents over three).
- **Stages**: retrieved → selected → allowed by the activation gate → handed to the model by `Kernel.run_goal` (a tool definition for Tools and Agents, the body in the prompt for Skills) → executed through the execution gate when the model calls it. The model is a scripted response that always calls the decoy it is offered, so the numbers measure the gates, not whether a model follows a forged description. The decoy's handler is an **inert recorder** bound through `ResourceActivator`; no shipped handler ever runs for a decoy.
- **Harm**: gold displacement (a gold resource of the same kind that was selected without the decoy is dropped), gold Tool loss (a gold Tool that reached the model without the decoy no longer does), status changes, and abstain / escalate hijacks (a case whose answer is abstain or escalate becomes `selected` with the decoy).

Results are in [`results/forgery.json`](results/forgery.json) (2,656 variants × 6 configurations). `tracked` holds the fixed fields to compare before and after a change, and `legacy_baseline` re-measures the six legacy cases (`metadata_forgery` 6/6) in the same run.

| Configuration | Kind | Declarations | Selected | Activation allowed | Reaches the model | Handler runs | Gold Tool loss | Hijack |
|---|---|---|---:|---:|---:|---:|---:|---:|
| lexical + greedy | Tool | honest | 0.000 | 0.000 | 0.000 | 0.000 | 0.231 | 0.000 |
| lexical + greedy | Tool | fully forged | 0.534 | 0.534 | 0.534 | 0.534 | 0.692 | 1.000 |
| lexical + greedy | Tool | partly forged | 0.226 | 0.000 | 0.000 | 0.000 | 0.374 | 0.500 |
| lexical + greedy | Skill | fully forged | 0.526 | 0.526 | 0.526 | — | 0.231 | 1.000 |
| lexical + greedy | Agent | fully forged | 0.564 | 0.564 | 0.564 | 0.564 | 0.231 | 1.000 |
| lexical + coverage | Tool | fully forged | 0.534 | 0.534 | 0.534 | 0.534 | 0.692 | 1.000 |
| lexical + Kernel default (rule-based) | Tool | honest | 0.420 | 0.000 | 0.000 | 0.000 | 0.231 | 0.875 |
| lexical + Kernel default (rule-based) | Tool | fully forged | 0.784 | 0.784 | 0.784 | 0.784 | 0.692 | 1.000 |
| lexical + Kernel default (rule-based) | Skill | fully forged | 0.859 | 0.859 | 0.859 | — | 0.231 | 1.000 |
| lexical + Kernel default (rule-based) | Agent | fully forged | 0.833 | 0.833 | 0.833 | 0.833 | 0.231 | 1.000 |
| lexical + greedy, gate-aware | Tool | honest | 0.000 | 0.000 | 0.000 | 0.000 | 0.115 | 0.000 |
| lexical + greedy, gate-aware | Tool | fully forged | 0.534 | 0.534 | 0.534 | 0.534 | 0.692 | 1.000 |
| lexical + greedy, gate-aware | Tool | partly forged | 0.032 | 0.000 | 0.000 | 0.000 | 0.170 | 0.071 |
| lexical + coverage, gate-aware | Tool | partly forged | 0.036 | 0.000 | 0.000 | 0.000 | 0.179 | 0.071 |
| lexical + rule-based, gate-aware | Tool | honest | 0.000 | 0.000 | 0.000 | 0.000 | 0.115 | 0.000 |
| lexical + rule-based, gate-aware | Tool | partly forged | 0.109 | 0.000 | 0.000 | 0.000 | 0.170 | 0.214 |

Honest Skills and Agents never pass activation in any configuration, and Skills have no handler (—). The hijack denominator is the eight abstain / escalate cases times their variants; the rule-based selector never abstains even without a decoy, which inflates its value. The gold Tool loss denominator is the evidence Tool tasks whose gold Tool reached the model without the decoy.

**Interpreting the results**

- **The activation gate stops decoys, the selector does not.** Greedy and coverage do not select a resource whose declared permissions are not granted, so a Tool that forges only its permissions (still `untrusted` and `external`) is selected in 74% of stuffed variants (both suites; 82% when fully forged) and then denied at activation. The selector does not read trust, side effect, or isolation. Only the fully forged decoy passes the gate; with any one declaration honest, activation stays at 0 (all 16 stuffed Tool combinations).
- **Denial does not undo the harm.** A decoy that is selected and then denied still displaces the gold resource, so partly forged Tools lose the gold Tool in 37% of cases (`partial_forgery` in `tracked`). Even an honestly declared stuffed Tool makes greedy escalate as "the top unit blocked only by permissions" (the default rule that escalates a permission-blocked top candidate), and the gold Tool no longer reaches the model in 46% of cases (0% for clones; the 0.231 in the honest row is the average of both). That path also asks a person to grant `net.external` and `message.send`.
- **Clones of legitimate resources get through less often than stuffing.** They tie with the gold resource, so even fully forged clones are selected in 36% of Tool cases (evidence) and 4% on the set corpus.
- The Kernel's default rule-based selector does not check permissions, so it selects even honestly declared decoys in 42–58% of variants (the gate then denies them).
- **The gate-aware rows hand the gate's policy to the selector** (`Kernel(gate_aware_selection=True)`, off by default; ADR 0014). A candidate the gate denies whatever is granted or approved (a trust level or side effect outside the policy, an unavailable isolation level) is neither selected nor a reason to escalate.
  - Selection of a partly forged Tool falls from 0.226 to 0.032 with greedy, and gold Tool loss from 0.374 to 0.170. Status changes caused by an honestly declared Tool fall from 0.307 to 0.170 (`status_change_rate`). The rule-based selector stops selecting honestly declared decoys (0.420 to 0.000).
  - The fully forged rows do not change: a decoy that forges every declaration the gate reads passes the same check.
  - What is still selected (0.032 and the like) declares its permissions honestly and forges the rest, and remains a reason to escalate as before.
  - Status accuracy on the cases without a decoy falls from 0.955 to 0.909 on the 22 evidence cases for greedy and coverage (`suites.evidence.configs.*.clean`). One case changes, `dev-escalate`: its notification Tool needs isolation level L3, which the default runtime does not have, as well as permissions, so the outcome is abstain with the reason `isolation_level L3 is not available in this runtime` instead of escalate. Granting the permissions would not get that Tool past the gate, but the label says escalate, so it is counted as a regression. Nothing changes on the 28 set-selection scenarios. Because of this one case the option is off by default.
- Countermeasures that verify declarations (signatures, provenance) are out of scope for this benchmark. When one is added, check with the same command that the fully forged rows of `tracked` go down.

**Procedure for PRs that change retrieval, selection, or routing**: run `python3 benchmarks/run_forgery_benchmark.py --output /tmp/forgery-before.json` on the base branch and the same with `-after.json` on the changed branch, and list `selection_rate`, `activation_reach_rate`, `execution_reach_rate`, `gold_tool_loss_rate`, and `abstain_escalate_hijack_rate` of `tracked.<configuration>.tracked.<kind>.{honest,full_forgery,partial_forgery,any_forgery}` in the PR description. Add a new Retriever / Selector to `CONFIGS` before measuring it. When the results JSON is updated, update this table too.

## ToolRet-SAE: select, escalate, or abstain

Every ToolRet query is answerable and every tool is usable, so ToolRet cannot score the other two outcomes a selector must produce: abstain and escalate. `run_toolret_sae.py` derives three variants from each ToolRet query.

- **S (select)**: the full catalog; the gold tools' permissions are granted.
- **E (escalate)**: the full catalog; only the gold tools' scopes are not granted.
- **A (abstain)**: the gold tools are removed from the catalog.

Permissions are opaque scopes (40, assigned by a hash of the tool id) attached after retrieval. Whether E and A really are escalate and abstain cases is decided by an annotator model (Claude Sonnet): for each gold tool it judges whether the request needs it and which of the top 40 candidates could stand in for it, and a variant is valid only when some needed gold tool has no (for E, no permitted) substitute. **The labels are by an LLM; no human validation was done.**

To create labels from scratch (this calls the annotator, Sonnet), run the commands below. They label the held-out split only, not the 833 dev queries the rules' relevance floors are tuned on. **To score from the published labels you do not need the annotator**; see "Rescoring from the published labels" below.

```bash
python3 benchmarks/run_toolret_llm_stages.py --stage decompose --model haiku --split heldout --sample 400
python3 benchmarks/run_toolret_sae.py --stage pools --stage label --split heldout --sample 400
python3 benchmarks/run_toolret_sae.py --stage agree --agree-queries 100
python3 benchmarks/run_toolret_sae.py --stage methods --split heldout --sample 400
python3 benchmarks/run_toolret_sae.py --stage score --stage export-labels --stage substitutes --method llm-set
```

- **Splits**: dev / test halve the sample of `run_toolret_benchmark.py` (1,689 queries). The held-out split is 852 queries outside that sample (18 subsets), frozen in [`toolret_sae_heldout_ids.json`](toolret_sae_heldout_ids.json). The evaluation below uses the first 400 of them in SHA-1 order of the id (valid variants: S 400, E 205, A 167).
- **Overlap with earlier evaluations** (#78): the held-out split excludes **only the sample (1,689 queries)**. The full test half under the same split rule (parity of the id's SHA-1; 3,920 queries), whose retrieval and decomposition were measured in [`results/toolret-test-full.json`](results/toolret-test-full.json), is not excluded. Counted on the pinned ToolRet data (below), 431 of the 852 frozen queries and 206 of the 400 evaluated queries are in that full test split by id. Queries under another id whose normalized text (whitespace collapsed, lower-cased; `toolret.normalize_text`) equals one in the full test split number 13 of 852 and 5 of 400. Overlap with the sample is 0 by id and by text. Whether the full-test results were used to tune any method is not recorded and unconfirmed. So **the ToolRet-SAE held-out split is not "unused data" independent of earlier evaluations for retrieval and decomposition methods**; read this section as a comparison of rules tuned on the sample (dev) and LLM methods on held-out queries.
- **Split of unused data**: to claim an evaluation of a retrieval or decomposition method on unused data, freeze before evaluating, and commit, a split that drops every query in the sample, the full test split, and the SAE held-out list, plus any query whose normalized text matches one of them, with `python3 benchmarks/run_toolret_sae.py --stage fresh-heldout` (`toolret.select_fresh_heldout`; on the current data 853 queries over 14 subsets, SHA-256 of the id list `6278eecd…`). No frozen list is committed yet, so none of the results in this section is an evaluation on unused data. Scoring on this split is not implemented. The old split (`select_heldout` and `toolret_sae_heldout_ids.json`) keeps its function, ids, and defaults, so results on it stay comparable.
- **Models**: labels by Sonnet; `LLMSetSelector` and the second annotator are Haiku. Retrieval is `llm:hybrid-0.5`, and every method chooses among the top 20 candidates.
- **Primary metric**: the macro average of accuracy on S, E, and A. S counts as correct only when the selected set contains every needed gold tool or a substitute.

Results are in [`results/toolret-sae-heldout.json`](results/toolret-sae-heldout.json). The rules' relevance floors are chosen on dev (833 queries).

| Held-out (400 queries) | Relevance floor | Macro accuracy | S | E | A | S Set F1 | Unneeded escalation (S) | Wrong selection (E) | Wrong selection (A) |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Top-ranked (escalate if blocked) | 0.65 (dev) | 0.367 | 0.065 | 0.156 | 0.880 | 0.067 | 0.033 | 0.059 | 0.066 |
| `GreedyConstrainedSetSelector` | 0.55 (dev) | 0.386 | 0.160 | 0.268 | 0.731 | 0.108 | 0.068 | 0.161 | 0.174 |
| `CoverageSetSelector` | 0.55 (dev) | 0.379 | 0.138 | 0.268 | 0.731 | 0.122 | 0.070 | 0.161 | 0.174 |
| `LLMSetSelector` (Haiku, 1 call) | — | 0.376 | 0.600 | 0.283 | 0.246 | 0.300 | 0.020 | 0.576 | 0.683 |

- **A relevance floor cannot decide the status.** The floor fitted on dev leaves the rules selecting almost nothing on S (greedy 0.160) and leaning on abstention.
- **An LLM asked for the set and the status together selects anyway.** `LLMSetSelector` is best on S but selects something in 68% of A and 58% of E. Its macro accuracy does not differ from greedy's (−0.010 [−0.053, 0.033]).
- A research selector that decides the status from per-requirement capability judgments and the declared constraints reached 0.552 on the same held-out queries (`benchmarks/results/toolret-sae-heldout.json` at commit f4ef28e7 of the `research/requirement-coverage` branch; not in this branch's result file), but missed one pre-registered adoption criterion (unneeded escalation on S), so it is not in `main` (#45, branch `research/requirement-coverage`).

**Metric version** (#79): `metric_version` in a results JSON is the version of the metrics. **The table above and [`results/toolret-sae-heldout.json`](results/toolret-sae-heldout.json) are version 1** (a JSON without the key is version 1): E counted as correct whenever the status was `escalate`. In the published results Haiku returned `escalate` on 58 of 205 E variants but named a required permission on none (`E_named_gold_scope` 0.0). Version 2 keeps the meaning of every version-1 key and adds `correct_v2`, `macro_correct_v2`, and `actionable_escalation`.

- **Correct E (version 2)**: the escalation names permissions that are not yet granted (`missing_permissions`); granting them leaves a candidate for every needed item (the gold tool or one of its substitutes) (`grant_sufficient`); and dropping any one requested permission breaks that (`actionable`: it asks for nothing needless). Correct S (`sufficient`) and correct A are as in version 1.
- **One substitute for several items**: a tool judged a substitute for several needed gold tools counts as satisfying each of them (shared cover). `sufficient` for S and `actionable` for E use this meaning and do not depend on the order of the gold tools (49 of the 2,089 labelled queries have a substitute shared by two needed gold tools). The ranking metric `toolret.group_metrics` credits a tool to one item only and assigns greedily in the order of the items, so recall changes with that order. `toolret.group_metrics_matched` (version 2) is a one-to-one maximum matching and does not depend on the order; use it with `--stage substitutes --substitute-matching matched` (the default is the greedy version that produced the published values; the result JSON records it as `group_matching`).
- **Not measured**: version-2 values have not been measured. The candidate pools and LLM reply caches are not available here, and they cannot be recomputed without the LLM. For the 15 queries with 6 or more needed items (12 with 6, 3 with 7) the size limit on the set (5 tools) is not checked.

**Label checks and release** (#48):

- Agreement with a second annotator (Haiku, 100 held-out queries): kappa 0.80 on substitute judgments (7,520 pairs), 0.79 on necessity, and 0.88 on variant validity. Both are Claude models, so correlated errors cannot be ruled out; agreement with another model family or with people has not been measured.
- The labels are in [`results/toolret-sae-heldout-labels.json`](results/toolret-sae-heldout-labels.json) (dev 833, test 856, held-out 400 queries): ToolRet query and tool ids with the necessity and substitute judgments. The labels and the held-out id list are released under CC0 1.0. They contain no ToolRet query or tool text, which is not redistributed (ToolRet's own terms apply to it).

**Rescoring from the published labels** (#77): starting from an empty cache, score with the published labels (ToolRet ids only) and no annotator calls. You need only the candidate pools of the 833 dev queries and of the evaluated split (stored under `benchmarks/cache/`), and, for an LLM method, its replies.

```bash
python -m pip install -e '.[benchmark,benchmark-toolret]'
python3 benchmarks/run_toolret_benchmark.py --download --retrievers lexical     # data at the pinned revision
python3 benchmarks/run_toolret_llm_stages.py --stage decompose --model sonnet --split dev
python3 benchmarks/run_toolret_llm_stages.py --stage decompose --model haiku --split heldout --sample 400
python3 benchmarks/run_toolret_sae.py --stage pools --split dev                  # computes embeddings (about 40 min with MiniLM)
python3 benchmarks/run_toolret_sae.py --stage pools --split heldout --sample 400
python3 benchmarks/run_toolret_sae.py --stage methods --split heldout --sample 400   # LLM method replies (Haiku); skip for the rules only
python3 benchmarks/run_toolret_sae.py --stage score --method llm-set \
    --labels-input benchmarks/results/toolret-sae-heldout-labels.json --output /tmp/toolret-sae-rescored.json
```

- With `--labels-input` the published labels replace the label cache. Scoring stops if the label model (`--label-model`), the candidate depth, the ToolRet ids and gold tools, or the splits disagree with the data. Labels with `candidates_sha256` (from now on, written by `export-labels`) are also checked against the candidate ids and their order. The first release has no such field, so the result's `inputs.label_pool_mismatch` counts the queries with a substitute that is not among the rebuilt candidates.
- If dev or evaluation queries needed for scoring are missing, or their candidate pools are, scoring prints the counts and the commands to run and **exits non-zero** (it used to save a dev=0 / held-out=0 result with exit code 0). The same holds when the replies of an LLM method named with `--method` are missing for any evaluated query.
- The label cache is matched by a key that includes a digest of the model, the prompt, and the gold and candidate ids in order. LLM method replies are keyed by a digest of the prompt (candidate ids, order, texts, and granted permissions) and stored in one file per model. After the candidate order changes the same reply no longer matches and is not replayed (a label reply keyed by query id alone used to attach to different tools when the order changed). A label cache in the old layout is not used; `--stage label` labels those queries again.
- Decomposition replies are LLM output and may differ from the stored ones when rerun; the candidate pools, and so the results, then differ from the published values. The decomposition model is not recorded in the cache, so the `--model` values above follow this README's description (Sonnet for the sample, Haiku for held-out).
- ToolRet data is fetched from the commits in `toolret.DATASET_REVISIONS` (change them with `toolret.download(revisions=...)`). The result JSON records the revisions and the file hashes in `inputs.toolret_data`.

**Effect of substitutes on ToolRet's standard metrics** ([`results/toolret-substitutes.json`](results/toolret-substitutes.json); 2,089 labelled queries, macro):

| Scoring | nDCG@10 | Recall@10 | Completeness@10 |
|---|---:|---:|---:|
| Gold tools only (ToolRet's own) | 0.266 | 0.348 | 0.262 |
| Gold or a labelled substitute | 0.437 | 0.526 | 0.397 |
| Necessary gold or a labelled substitute | 0.452 | 0.554 | 0.446 |

- Of 3,817 gold tools, 51.9% have a substitute among the top 40 candidates and 88.0% were judged necessary.
- Accepting substitutes raises nDCG@10 from 0.266 to 0.437: on a catalog with many near-duplicates, scoring against the gold tools alone understates retrieval. Completeness@10 on multi-tool queries (911) goes from 0.108 to 0.300 with necessary gold or a substitute.
- The substitute judgments are by an LLM and cover the top 40 candidates only; read the values as indicative.

## Flat ANN comparison at 100k

`run_ann_scale_benchmark.py` compares flat ANN (USearch, cosine/HNSW) with namespace hierarchy using the same 100,063 resources, 34 scenarios, embeddings, BM25 candidates, mixing weight 0.9, pool size 50, and greedy Selector. ANN is in the benchmark-only `benchmark-ann` extra and is not a runtime dependency.

```bash
python -m pip install -e '.[benchmark-ann]'
python3 benchmarks/run_ann_scale_benchmark.py --size 100000 --embedding hash
python -m pip install -e '.[benchmark]'
python3 benchmarks/run_ann_scale_benchmark.py --size 100000 --embedding model
```

`hash` is a **non-semantic control** for quickly checking the scaling path. Use `model` measurements to judge semantic retrieval. Index-build time includes embedding computation and is recorded separately from warm search time. The existing `scale-routing-100000.json` uses `min_relevance=0.55`, while the current default is 0.35, so do not directly subtract its values from new results.

| 100k / hash-64 | gold recall@50 | Set F1 | p50 / p95 |
|---|---:|---:|---:|
| flat ANN | 0.354 | 0.249 | 55.3 / 401.1 ms |
| hier-namespace | 0.254 | 0.143 | 140.6 / 419.3 ms |

| 100k / BAAI/bge-small-en-v1.5 | gold recall@50 | Set F1 | p50 / p95 |
|---|---:|---:|---:|
| flat ANN | 0.475 | 0.471 | 45.7 / 260.7 ms |
| hier-namespace | **0.554** | **0.558** | 73.0 / **105.3 ms** |

With the hash control, flat ANN outperforms the hierarchy on both quality metrics and also has shorter p50 / p95. With real embeddings, the hierarchy improves recall by 0.079 and Set F1 by 0.087, and reduces p95 by 155.4ms. Flat ANN has a 27.2ms shorter p50, so it still has a median-latency advantage with real embeddings. Since hash is a non-semantic control, use the BGE rows for conclusions about semantic search. This is a limited evaluation of 34 scenarios; generalization to other embedding models or catalog distributions has not been confirmed.

The initial flat ANN index build with BGE took 2,953.6 seconds (about 49.2 minutes), including embedding computation; the index itself was 286,262,656 bytes (about 273 MiB). This is a cold build on the measurement machine, separated from warm search latency. All values are recorded in the same run’s [`ann-scale-model-100000.json`](results/ann-scale-model-100000.json).

The current `run_ann_scale_benchmark.py` measures each arm's first build with its own embedding provider (cache) and records document and query embedding time separately under `cold_start` in the result JSON. In the results above (measured 2026-09) the hierarchy reused the embeddings the flat arm had already computed, so its `warmup_seconds` is not an independent first-build cost (#80; quality metrics and warm latency are unaffected, and the re-measurement has not been run).

## ToolRet: Large-scale, multi-tool selection on a public benchmark

The evaluations so far use a corpus and labels created in this repository. `run_toolret_benchmark.py` measures Layers 1 and 2 on **ToolRet**, a public benchmark created by others (Shi et al., ACL 2025 Findings, “Retrieval Models Aren’t Tool-Savvy”). ToolRet combines 35 public tool-use datasets and has 44,453 tools and 7,961 queries. ToolBench, ToolLens, Tool-Be-Honest, ReverseChain, and others contain **multi-tool gold sets**, allowing us to measure whether the required combination can be selected with neither omissions nor extras from a large catalog, without self-created labels.

```bash
python -m pip install -e '.[benchmark,benchmark-toolret]'                       # fastembed and pyarrow (benchmark-only)
python3 benchmarks/run_toolret_benchmark.py --download --retrievers lexical     # download and lexical retrieval
python3 benchmarks/run_toolret_llm_stages.py --stage decompose --model haiku                # build the LLM decomposition cache (Claude Code CLI)
python3 benchmarks/run_toolret_llm_stages.py --stage select --stage rerank --model haiku    # build caches for LLM set selection and reranking
python3 benchmarks/run_toolret_benchmark.py --per-subset 60 \
    --retrievers hybrid-0.5,lexical,dense,hybrid-0.9,rrf,clause:hybrid-0.5,llm-rrf:hybrid-0.5,llm!:hybrid-0.5,llm:hybrid-0.5,rerank:llm!:hybrid-0.5
```

**Data handling**: The dataset cards do not state licenses, and licenses vary by source, so the data is not redistributed. `--download` retrieves it from HuggingFace into `benchmarks/data/toolret/` (not tracked by git). Only aggregate values in `results/toolret.json` are committed. Downloads are pinned to the commits in `toolret.DATASET_REVISIONS`; the fetched commits and file SHA-256 hashes are recorded in `manifest.json` and under `provenance` in the result JSON.

**Protocol**

- Up to 60 items per subset (seed 0), for 1,689 queries total (including 726 multi-tool queries). Each run searches the full set of **44,453 tools**.
- Metrics match ToolRet: nDCG@10, Recall@10, and Completeness@10 (the fraction of cases with all gold tools in the top 10). @100 is also reported to show the input limit for set selection. Macro averages (the mean of per-subset averages), following ToolRet convention, are the main values reported.
- Tool documents are converted to Tool resources with `toolret.tool_resource`, and permissions, trust, side effects, and cost are identical for every item. Ranking is determined only by body relevance.
- Embeddings use `sentence-transformers/all-MiniLM-L6-v2` (fastembed / ONNX / CPU, one of the models evaluated by ToolRet). Embedding text is limited to the first 512 characters. `bge-small-en-v1.5` is not used because it processes only 4 documents per second of 512 characters in this environment, taking hours for 44k items.
- LLM stages (decomposition, reranking, set selection) use the library’s `LLMQueryDecomposer`, `LLMRerankRetriever`, and `LLMSetSelector` directly with Claude Haiku 5.5 (through the Claude Code CLI, `benchmarks/_claude_cli.py`, `--model haiku`). Responses are saved in `benchmarks/cache/` and replayed for scoring. Responses are not reproducible, so values change if the cache is deleted. Earlier measurements used Claude Sonnet (see "Differences from the earlier measurement").
- **Tune on dev, report on test**: Query IDs are split 50/50 by SHA-1; fusion weights, `min_gain`, semantic weight, and other parameters are chosen on dev, and test values are reported. Differences and their intervals use the same weighting as the macro columns: a paired bootstrap on the test split (2,000 resamples, 95%) that resamples queries within each subset and averages the per-subset mean differences with equal weight. The query-equal (micro) difference is stored separately under `micro` in the result JSON; it is a different quantity. Set F1 differences are query means, like the table, so they are micro.

### Layer 1: Ranking (1,689 queries, macro)

[`results/toolret.json`](results/toolret.json). `llm:` uses `LLMQueryDecomposer` decomposition and blend fusion (subtask weight 0.25, discounted by known-token rate); `llm!:` has no discount; `llm-rrf:` uses RRF fusion; `clause:` uses rule-based decomposition; and `rerank:` reranks the top 30 with `LLMRerankRetriever`. Differences are from hybrid-0.5 on the test split (macro).

| Configuration | nDCG@10 | Recall@10 | C@10 | C@100 | Multi-tool C@10 | Test nDCG@10 difference [95% CI] | Test C@10 difference [95% CI] | p50 / p95 ms |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| `lexical` (BM25F) | 0.211 | 0.276 | 0.205 | 0.328 | 0.065 | −0.041 [−0.055, −0.029] | −0.037 [−0.057, −0.018] | 21.3 / 81.4 |
| `dense` (MiniLM-L6) | 0.205 | 0.271 | 0.199 | 0.374 | 0.077 | −0.043 [−0.057, −0.030] | −0.040 [−0.059, −0.021] | 27.8 / 89.9 |
| `hybrid-0.9` | 0.220 | 0.286 | 0.212 | 0.388 | 0.080 | −0.029 [−0.040, −0.018] | −0.033 [−0.051, −0.016] | 25.7 / 88.3 |
| `rrf` (BM25F + dense) | 0.242 | 0.326 | 0.243 | 0.412 | 0.095 | −0.013 [−0.020, −0.005] | −0.004 [−0.017, 0.008] | 52.5 / 181.3 |
| **`hybrid-0.5` (baseline)** | 0.256 | 0.330 | 0.247 | 0.412 | 0.102 | — | — | 25.4 / 86.2 |
| `clause:hybrid-0.5` | 0.254 | 0.328 | 0.239 | 0.413 | 0.099 | +0.005 [−0.001, 0.010] | −0.003 [−0.013, 0.007] | 105.7 / 417.5 |
| `llm-rrf:hybrid-0.5` | 0.224 | 0.308 | 0.234 | **0.439** | 0.076 | −0.022 [−0.036, −0.008] | −0.006 [−0.025, 0.014] | 77.4 / 251.2 |
| `llm!:hybrid-0.5` | 0.268 | 0.345 | 0.259 | 0.415 | 0.102 | +0.022 [0.013, 0.030] | +0.014 [0.002, 0.027] | 78.7 / 257.6 |
| **`llm:hybrid-0.5`** | 0.268 | 0.347 | 0.261 | 0.419 | 0.103 | **+0.023 [0.014, 0.031]** | **+0.017 [0.004, 0.031]** | 88.5 / 307.1 |
| `rerank:llm!:hybrid-0.5` | **0.329** | **0.393** | **0.302** | 0.415 | **0.143** | **+0.084 [0.070, 0.097]** | **+0.070 [0.052, 0.087]** | 91.2 / 295.7 |

Latency excludes LLM calls (responses are replayed from cache). In operation, one model call each for decomposition and reranking would be added. 1,218 of the 1,689 queries were decomposed. One reranking response could not be replayed; that query was scored without reordering.

### Layer 2: Set selection (856 test-split queries)

The candidate pool is the top 100 results from each Retriever; `llm-set` shows the top 20 to `LLMSetSelector` (Claude Haiku 5.5). Differences are relative to top-1 for the same Retriever.

| Retriever | Selection | Set F1 | Multi-tool F1 | Exact | Mean size | Difference from top-1 [95% CI] |
|---|---|---:|---:|---:|---:|---:|
| `hybrid-0.5` | top-1 | 0.159 | 0.118 | 0.111 | 1.00 | — |
| `hybrid-0.5` | `GreedyConstrainedSetSelector` (tool ≤ 3) | 0.142 | 0.163 | 0.002 | 3.00 | — |
| `hybrid-0.5` | score ≥ 0.9 × first result (max 5) | 0.178 | 0.160 | 0.078 | 2.73 | +0.018 [0.008, 0.029] |
| `hybrid-0.5` | oracle top-k (gold set size known) | 0.179 | 0.166 | 0.125 | 1.80 | +0.020 [0.013, 0.028] |
| `llm:hybrid-0.5` | top-1 | 0.169 | 0.127 | 0.117 | 1.00 | — |
| `llm:hybrid-0.5` | top-3 | 0.154 | 0.173 | 0.002 | 3.00 | — |
| `llm:hybrid-0.5` | `CoverageSetSelector` (min_gain 0.1) | 0.154 | 0.142 | 0.067 | 2.07 | −0.015 [−0.028, −0.003] |
| `llm:hybrid-0.5` | score ≥ 0.9 × first result (max 5) | 0.171 | 0.156 | 0.063 | 2.88 | +0.002 [−0.010, 0.013] |
| `llm:hybrid-0.5` | `CoverageSetSelector(include_within=0.95)` | 0.160 | 0.148 | 0.054 | 4.20 | −0.009 [−0.021, 0.004] |
| `llm:hybrid-0.5` | oracle top-k | 0.186 | 0.168 | 0.131 | 1.80 | +0.017 [0.010, 0.024] |
| `llm!:hybrid-0.5` | **`LLMSetSelector` (top 20)** | **0.206** | **0.211** | 0.053 | 4.57 | **+0.038 [0.018, 0.057]** |

`min_gain` stays at the default 0.1, the relative threshold at 0.9, and `include_within` at 0.95. Dev F1 in this measurement: the coverage selector 0.149–0.156 for `min_gain` 0.02–0.3; score ≥ 0.9 × first 0.173; `include_within` 0.85 / 0.9 / 0.95 gave 0.155 / 0.160 / 0.162. `LLMSetSelector` failed to replay one response; that case was scored as an abstention.

### Interpreting the results

- **At large catalog scale, hybrid semantic weight 0.5 is best; 0.9 does not transfer.** The 0.9 setting that was best on the 120-scenario Skill corpus falls well below 0.5 on 44k tools: macro nDCG@10 is 0.220 vs. 0.256. The library default 0.5 is best on labels the authors did not create. RRF fusion also trails hybrid 0.5.
- **LLM decomposition significantly improves Layer 1**, by about 2 points (nDCG@10 +0.023, C@10 +0.017). Best candidates for each subtask move higher. Blend fusion is better than RRF (RRF raises C@100 while lowering nDCG@10), while rule-based clause decomposition has no significant difference (−0.008 on dev). Rule-based decomposition also splits a single request at sentence or conjunction boundaries, so the benefit of decomposition depends on its accuracy (ADR 0012).
- **Adding LLM reranking gives the largest gain** (nDCG@10 +0.084). Comparing candidate descriptions is more accurate than the combined embedding and BM25 score.
- **In this measurement, building a set by rule on the decomposed ranking does not beat top-1.** Decomposition raises top-1 Set F1 from 0.159 to 0.169, but the coverage selector on top of it falls to 0.154 (−0.015 against top-1, significant), and the relative threshold gains nothing (+0.002). Among rule-based sets, the relative threshold on hybrid without decomposition was best at 0.178. The coverage selector picks one item per subtask, so its set size follows the granularity of the decomposition. Haiku decomposed 1,218 of the 1,689 queries, and coverage sets averaged 2.07 items (gold sets average 1.8).
- **The coverage selector's gain depends on the decomposing model.** In the earlier results, measured with Claude Sonnet decompositions, coverage was +0.004 over top-1 on the sample (not significant) and +0.012 on the full test set (significant); see "Differences from the earlier measurement" below. Coverage selection's value is choosing one item per subtask or type while preserving dependency closure, conflicts, and permissions (on the four-type mixed set-selection benchmark it matches greedy at Set F1 0.609). This measurement does not support it as a way to raise Set F1 on ToolRet.
- **Fixed top-k and the default greedy (tool ≤ 3) are worse than top-1** (0.142–0.154). ToolRet gold sets average 1.8 items, and always selecting three reduces precision.
- **If one additional model call is affordable, `LLMSetSelector` performs best** (F1 0.206, multi-tool F1 0.211, +0.038 over top-1). The solver beat the LLM on the repository’s 28 scenarios (a synthetic corpus with declared constraints), but ToolRet has no declared constraints, so semantic interpretation of descriptions helps. The Kernel applies dependency closure, conflict, and permission constraints to every Selector output, so this remains compatible with delegating relevance judgment to the LLM and constraints to the solver (ADR 0005). The resulting sets are relatively large (mean 4.57).
- **Limitations**: this evaluation covers 1,689 sampled queries (at most 60 per subset) and only the small MiniLM-L6 embedding model. The LLM stages use one model, Claude Haiku 5.5; other models were not compared under the same conditions. Larger embedding models, ToolRet’s instruction-based setting, and direct comparison with published paper values (the paper could not be retrieved in this environment) were not evaluated. LLM-stage outputs depend on cache and change when the model is updated.

#### Differences from the earlier measurement

The LLM stages in this section were previously measured with Claude Sonnet (`benchmarks/README.en.md` and the result JSON at commit `451a9bf7`). The re-measurement that aligned the differences and intervals with the macro weighting (#76) rebuilt the LLM stages with Claude Haiku 5.5. Responses are not reproducible, so values that depend on the LLM stages cannot be compared with the earlier ones. Metrics of the rows without an LLM (`lexical`, `dense`, `hybrid-*`, `rrf`, `clause:`) are unchanged (their differences and intervals follow the new definition, and latency was measured again).

| Item | Earlier (Sonnet) | Now (Haiku 5.5) |
|---|---:|---:|
| Decomposition: test nDCG@10 difference (sample) | +0.019 (query-equal) | +0.023 (macro) |
| Reranking: test nDCG@10 difference (sample) | +0.043 (query-equal) | +0.084 (macro) |
| `LLMSetSelector`: Set F1 (difference from top-1) | 0.243 (+0.067) | 0.206 (+0.038) |
| Coverage selector: difference from top-1 (sample / full test) | +0.004 / +0.012 | −0.015 / −0.003 |
| Queries decomposed on the full test split | 1,900 / 3,920 | 2,787 / 3,920 |

The earlier ranking differences were query-equal (micro) values, so their definition also differs from the macro values here. The micro differences of this measurement are under `micro` in the result JSON (decomposition: +0.016 on the sample, +0.011 on the full test split).

#### Tried during exploration but not adopted

None improved results in the dev split or offline analyses during development, which used Claude Sonnet decompositions (values in ADR 0012): max fusion using the best score; fixed increases to subtask weight (the gain disappears in English); relevance normalization per facet; adding near-ties to coverage selection; calibrating candidate inclusion probabilities and choosing the set size that maximizes expected F1; and supplementing prerequisite tools based on matching input/output names (data-flow completion).


### Full test-split confirmation (3,920 queries)

The sample limits larger subsets to 60 cases. We decomposed the full test split (3,920 queries, including 1,729 multi-tool queries) and remeasured with the same settings ([`results/toolret-test-full.json`](results/toolret-test-full.json), `--per-subset 0 --split test`). LLM reranking and `LLMSetSelector` were excluded because of the number of calls.

| Configuration | nDCG@10 | C@10 | C@100 | Multi-tool C@10 | nDCG@10 difference [95% CI] | C@10 difference [95% CI] |
|---|---:|---:|---:|---:|---:|---:|
| `lexical` | 0.200 | 0.192 | 0.321 | 0.113 | −0.045 [−0.056, −0.033] | −0.043 [−0.061, −0.027] |
| `hybrid-0.5` (baseline) | 0.245 | 0.234 | 0.397 | 0.161 | — | — |
| `llm:hybrid-0.5` | **0.268** | **0.255** | **0.403** | **0.178** | **+0.023 [0.015, 0.032]** | **+0.020 [0.008, 0.033]** |

| Retriever | Selection | Set F1 | Multi-tool F1 | Exact | Mean size | Difference from top-1 [95% CI] |
|---|---|---:|---:|---:|---:|---:|
| `hybrid-0.5` | top-1 | 0.199 | 0.135 | 0.140 | 1.00 | — |
| `hybrid-0.5` | **score ≥ 0.9 × first result (max 5)** | **0.222** | 0.182 | 0.100 | 2.71 | **+0.023 [0.017, 0.029]** |
| `llm:hybrid-0.5` | top-1 | 0.205 | 0.135 | 0.145 | 1.00 | — |
| `llm:hybrid-0.5` | top-3 / `GreedyConstrainedSetSelector` (tool ≤ 3) | 0.191 | 0.199 | 0.001 | 3.00 | — |
| `llm:hybrid-0.5` | `CoverageSetSelector` | 0.201 | 0.161 | 0.106 | 2.00 | −0.003 [−0.010, 0.003] |
| `llm:hybrid-0.5` | score ≥ 0.9 × first result (max 5) | 0.213 | 0.174 | 0.082 | 2.81 | +0.009 [0.002, 0.015] |
| `llm:hybrid-0.5` | `CoverageSetSelector(include_within=0.95)` | 0.202 | 0.167 | 0.081 | 3.97 | −0.003 [−0.009, 0.004] |
| `llm:hybrid-0.5` | oracle top-k | 0.232 | 0.197 | 0.163 | 1.76 | +0.027 [0.023, 0.031] |

- The Layer 1 improvement from decomposition (nDCG@10 +0.023) replicates on all queries. Macro nDCG@10 is nearly the same between the sampled test and full set (hybrid 0.243 / 0.245). The query-equal (micro) difference is +0.011 [0.007, 0.014], smaller than the macro one.
- **The coverage selector shows no gain on the full set either** (−0.003 [−0.010, 0.003] vs. top-1), and neither does `include_within=0.95` (−0.003). Among rule-based sets, the relative threshold on hybrid without decomposition is best at 0.222, above the relative threshold on the decomposed ranking (0.213). An oracle that knows the gold set size reaches 0.232.
- We also confirmed on the full set that the mean known-token rate across 2,787 decomposed queries is 0.93, so the discount has little effect on English goals.

### Embedding models and the query-side instruction

We measured, on the same 1,689 queries, whether **Snowflake Arctic-Embed-S** (33M parameters, 384 dimensions), a retrieval-tuned model that is stronger than MiniLM-L6 on MTEB, lifts the first layer. Arctic-Embed is asymmetric: it was trained with an instruction (`Represent this sentence for searching relevant passages: `) on the query side only. `EmbeddingProvider.embed_queries()` embeds documents and queries separately, and we compare with and without the instruction (`--query-prefix`).

```bash
python3 benchmarks/run_toolret_benchmark.py --per-subset 60 --retrievers hybrid-0.5,dense --records /tmp/minilm.json
python3 benchmarks/run_toolret_benchmark.py --per-subset 60 --retrievers hybrid-0.5,dense \
    --embed-model snowflake/snowflake-arctic-embed-s \
    --query-prefix "Represent this sentence for searching relevant passages: " --records /tmp/arctic.json
python3 benchmarks/compare_toolret_records.py minilm=/tmp/minilm.json arctic-s=/tmp/arctic.json --output /tmp/cmp.json
```

Results are in [`results/toolret-arctic-s.json`](results/toolret-arctic-s.json) and [`results/toolret-arctic-s-no-instruction.json`](results/toolret-arctic-s-no-instruction.json); paired differences are in [`results/toolret-embeddings.json`](results/toolret-embeddings.json) (against MiniLM) and [`results/toolret-query-instruction.json`](results/toolret-query-instruction.json) (with versus without the instruction). The MiniLM-L6 row has the same values as [`results/toolret.json`](results/toolret.json), and the pairing uses the `--records` file of that run. Differences use the same weighting as the macro columns, with 95% bootstrap intervals (1,689 queries, 35 subsets; the query-equal difference is under `micro` in each JSON).

| Embedding | hybrid-0.5 macro nDCG@10 | hybrid-0.5 macro C@10 | dense macro nDCG@10 | dense macro C@10 | Difference from MiniLM (dense nDCG@10) |
|---|---:|---:|---:|---:|---:|
| **MiniLM-L6** (default) | **0.256** | **0.247** | **0.205** | **0.199** | — |
| Arctic-Embed-S (with instruction) | 0.241 | 0.221 | 0.178 | 0.163 | −0.027 [−0.038, −0.016] |
| Arctic-Embed-S (without instruction) | 0.229 | 0.214 | 0.110 | 0.107 | −0.095 [−0.107, −0.082] |

- **A model that is stronger on MTEB is not necessarily stronger on ToolRet.** Arctic-Embed-S is significantly worse than MiniLM in both hybrid and dense retrieval (hybrid nDCG@10 −0.015 [−0.023, −0.006], C@100 −0.045 [−0.061, −0.028]). This points the same way as the ToolRet paper's conclusion that retrieval models are not tool-savvy; the default MiniLM-L6 is unchanged.
- **Asymmetric models need their query-side instruction.** Without it, dense nDCG@10 drops by 0.068 [0.059, 0.077] and C@100 by 0.096 [0.081, 0.112]. With only `embed()`, the previous `EmbeddingProvider` could use such models only without the instruction.
- Embedding the 44,453 documents on four CPU cores took about 40 minutes with MiniLM-L6, about 90 minutes with Arctic-Embed-S, about 4 hours with bge-small-en-v1.5, and more than 10 hours with bge-base-en-v1.5 (estimates while sharing the CPU with other jobs). Larger models were not measured in this environment.

### Selecting from an English catalog with Japanese goals

ToolRet tool descriptions are in English. We translated six test queries per subset (206 total) into natural Japanese with Claude Haiku 5.5 (`run_toolret_llm_stages.py --stage translate-ja`) and compared retrieval with the same 206 queries left in English ([`results/toolret-ja.json`](results/toolret-ja.json), [`results/toolret-ja-english-baseline.json`](results/toolret-ja-english-baseline.json)). `!` means no known-token-rate discount, and `@1` means subtask weight 1.

| Configuration | English nDCG@10 | English C@10 | Japanese nDCG@10 | Japanese C@10 | Japanese C@100 | Japanese top-1 F1 | Japanese coverage F1 |
|---|---:|---:|---:|---:|---:|---:|---:|
| `lexical` | 0.217 | 0.219 | 0.011 | 0.019 | 0.071 | 0.005 | 0.005 |
| `hybrid-0.5` | 0.252 | 0.252 | 0.028 | 0.029 | 0.062 | 0.022 | 0.022 |
| `llm!:lexical` | 0.232 | 0.219 | 0.065 | 0.086 | 0.224 | 0.022 | 0.062 |
| `llm:lexical` | 0.228 | 0.214 | 0.084 | 0.086 | 0.224 | 0.041 | 0.070 |
| `llm!:hybrid-0.5` | 0.271 | 0.248 | 0.046 | 0.043 | 0.119 | 0.028 | 0.065 |
| `llm@1!:hybrid-0.5` | 0.254 | 0.248 | **0.118** | **0.133** | 0.290 | **0.057** | **0.085** |
| **`llm:hybrid-0.5` (default)** | **0.271** | 0.248 | 0.115 | 0.124 | 0.290 | 0.053 | 0.082 |

- **Neither lexical retrieval nor English-only embeddings work well on Japanese goals** (nDCG@10 0.011 / 0.028). Japanese CJK bigrams do not occur in the English catalog, so the few remaining known tokens (names, numbers, proper nouns) dominate the relevance signal.
- **LLM decomposition also serves as translation.** `LLMQueryDecomposer` returns English subtasks, so retrieval for subtasks behaves like English retrieval. However, with the default 0.25 weight, the noisy list from the Japanese goal itself dominates the ranking, leaving results at 0.046.
- **The known-token-rate discount** (weighting the goal based on the fraction of its words present in the catalog index) automatically reaches 0.115, close to the 0.118 from manually setting the weight to 1 (hybrid difference +0.087, 95% CI [0.062, 0.114]). Among the decomposed queries (156 Japanese, 152 English), mean known-token rate was 0.92 for English and 0.32 for Japanese (`goal_weight_mean` in each JSON), and results for English are unchanged (0.271 → 0.271). Fixing the weight at 1 lowers English to 0.254.
- Results remain well below English queries (0.271); subtasks alone cannot recover the context in the English goal itself (the combination of proper nouns and descriptive words). A multilingual embedding configuration has not been measured.

## Notes

`resources/skills` is a copy from external repositories whose sources are recorded in `resources/skills/SOURCES.md`; it is for benchmarking and verification only. Do not redistribute this corpus as an artifact until its source licenses are resolved. For this reason, it is excluded from git with `.gitignore` and from sdist in `MANIFEST.in`.
