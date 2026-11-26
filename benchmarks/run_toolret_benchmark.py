"""ToolRet benchmark: routing over 44,453 public tools with multi-tool gold sets.

The other suites in this directory use corpora and labels written in this
repository. This one runs Marmo-Core's first and second layers on ToolRet
(ACL 2025 Findings; 35 public tool-use datasets, 7,961 queries, 44,453 tools,
labels from the original datasets), so the numbers are not tuned to
scenarios written here. The conversion and sampling are this script's own,
so compare with published ToolRet results only after matching them.

Layer 1 (ranking), with ToolRet's metrics:
  nDCG@10, Recall@10, Completeness@10 (every gold tool in the top 10), and
  Recall/Completeness@100 (what a set selector can still reach).
Layer 2 (set selection over the top-100 pool):
  Set precision / recall / F1, exact match, complete-set rate, set size.

Every query is searched against the full 44k-tool corpus. Scores are
averaged per query (micro) and per subset (macro, ToolRet's convention).

Usage:
    python3 benchmarks/run_toolret_benchmark.py --download
    python3 benchmarks/run_toolret_benchmark.py --per-subset 60 \\
        --retrievers hybrid-0.5,lexical,llm:hybrid-0.5 --embed-model sentence-transformers/all-MiniLM-L6-v2

The dataset is downloaded into benchmarks/data/toolret (git-ignored, not
redistributed); dense runs cache document vectors under benchmarks/cache.
"""

from __future__ import annotations

import argparse
import hashlib
from dataclasses import replace
import json
import random
import statistics
import sys
import time
from collections import defaultdict
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(Path(__file__).parent))

from marmo_core.decomposition import parse_subtasks  # noqa: E402
from marmo_core.errors import ProviderError  # noqa: E402
from marmo_core import (  # noqa: E402
    ClauseQueryDecomposer,
    LLMProvider,
    LLMRerankRetriever,
    LLMSetSelector,
    CoverageSetSelector,
    DecomposedRetriever,
    ExactVectorIndex,
    QueryDecomposer,
    GreedyConstrainedSetSelector,
    HybridRetriever,
    LexicalRetriever,
    RRFRetriever,
    SearchQuery,
    SelectionContext,
)

import toolret  # noqa: E402
from _provenance import stamp  # noqa: E402

POOL = 100
DECOMPOSITION_CACHE = Path(__file__).parent / "cache" / "toolret-decompositions.json"
RERANK_CACHE = Path(__file__).parent / "cache" / "toolret-rerank.json"
TRANSLATION_CACHE = Path(__file__).parent / "cache" / "toolret-ja-translations.json"
SET_SELECT_CACHE = Path(__file__).parent / "cache" / "toolret-set-select.json"
RERANK_POOL = 30
SELECT_POOL = 20


class ReplayOnly(LLMProvider):
    """Fails every call: LLM components replay their caches and degrade on a miss."""

    def complete(self, messages, tools=()):
        raise ProviderError("reply not cached; run benchmarks/run_toolret_llm_stages.py first")


def load_cache(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}


class CachedReplyDecomposer(QueryDecomposer):
    """LLM decompositions replayed from the decomposition cache (task -> raw reply)."""

    def __init__(self, replies: dict[str, str]) -> None:
        self.replies = replies
        self.misses = 0

    def decompose(self, task: str) -> list[str]:
        reply = self.replies.get(task.strip())
        if reply is None:
            self.misses += 1
            return []
        subtasks = parse_subtasks(reply) or []
        unique = list(dict.fromkeys(subtasks))
        return unique[:8] if len(unique) > 1 else []


def build_retriever(name: str, provider, decompositions: dict | None = None):
    """``<base>``, ``rerank:<spec>``, or ``<decomposer>[-<fusion>][@<weight>][!]:<base>``.

    The weight is the sub-task weight for blend fusion and the goal weight for
    rrf; ``!`` turns off the unknown-term discount of the goal. Examples:
    ``llm:lexical``, ``llm@1:hybrid-0.5``, ``llm!:hybrid-0.5``, ``clause-rrf@3:hybrid-0.5``.
    """

    if name.startswith("rerank:"):
        inner = build_retriever(name.removeprefix("rerank:"), provider, decompositions)
        return LLMRerankRetriever(ReplayOnly(), inner, rerank_pool=RERANK_POOL, cache=load_cache(RERANK_CACHE))
    if ":" in name:
        prefix, base = name.split(":", 1)
        discount = not prefix.endswith("!")
        prefix, _, weight_text = prefix.removesuffix("!").partition("@")
        decomposer_name, _, fusion = prefix.partition("-")
        if decomposer_name == "clause":
            decomposer = ClauseQueryDecomposer()
        elif decomposer_name == "llm":
            decomposer = CachedReplyDecomposer(decompositions or {})
        else:
            raise SystemExit(f"unknown decomposer: {decomposer_name}")
        fusion = fusion or "blend"
        weight = {"goal_weight" if fusion == "rrf" else "facet_weight": float(weight_text)} if weight_text else {}
        return DecomposedRetriever(
            build_retriever(base, provider, decompositions),
            decomposer,
            depth=POOL,
            fusion=fusion,
            discount_unknown_terms=discount,
            **weight,
        )
    if name == "lexical":
        return LexicalRetriever()
    if name.startswith("hybrid"):
        weight = float(name.split("-", 1)[1]) if "-" in name else 0.5
        return HybridRetriever(provider, semantic_weight=weight, candidate_pool=POOL, vector_index=ExactVectorIndex)
    if name == "dense":
        return HybridRetriever(provider, semantic_weight=1.0, candidate_pool=POOL, vector_index=ExactVectorIndex)
    if name == "rrf":
        return RRFRetriever(
            LexicalRetriever(),
            HybridRetriever(provider, semantic_weight=1.0, candidate_pool=POOL, vector_index=ExactVectorIndex),
            depth=POOL,
        )
    raise SystemExit(f"unknown retriever: {name}")


LLM_STAGE_RETRIEVER = "llm!:hybrid-0.5"


def selectors(retriever_name: str = "", *, language: str = "en") -> dict:
    """Second-layer strategies over the same top-100 pool.

    ``llm-set`` replays ``LLMSetSelector`` replies cached for the candidates of
    ``LLM_STAGE_RETRIEVER`` (benchmarks/run_toolret_llm_stages.py), so it is
    scored for that retriever only.
    """

    def top(k):
        return lambda results, query: results[:k]

    def oracle_k(results, query):
        return results[: len(query.labels)]

    def greedy_default(results, query):
        # The library's constrained solver with the Kernel's default limits.
        selection = GreedyConstrainedSetSelector().select(
            results, context=SelectionContext(task=query.query, per_kind_limits={"tool": 3})
        )
        return list(selection.results)

    def ratio(threshold, limit=5):
        # Adaptive-size baseline: everything within ``threshold`` of the top relevance.
        def choose(results, query):
            if not results:
                return []
            top_relevance = float(results[0].components.get("relevance", 0.0))
            chosen = [r for r in results[:limit] if float(r.components.get("relevance", 0.0)) >= threshold * top_relevance]
            return chosen or results[:1]

        return choose

    def coverage(min_gain, include_within=None, max_resources=8):
        selector = CoverageSetSelector(min_gain=min_gain, include_within=include_within)

        def choose(results, query):
            context = SelectionContext(task=query.query, max_resources=max_resources)
            return list(selector.select(results, context=context).results)

        return choose

    strategies = {"top-1": top(1), "top-3": top(3), "top-5": top(5), "greedy-default": greedy_default, "oracle-k": oracle_k}
    if retriever_name == LLM_STAGE_RETRIEVER and language == "en" and SET_SELECT_CACHE.exists():
        llm_selector = LLMSetSelector(ReplayOnly(), cache=load_cache(SET_SELECT_CACHE))

        def llm_set(results, query):
            return list(llm_selector.select(results[:SELECT_POOL], context=SelectionContext(task=query.query)).results)

        llm_set.selector = llm_selector  # type: ignore[attr-defined]
        strategies["llm-set"] = llm_set
    strategies.update({f"ratio-{t}": ratio(t) for t in (0.7, 0.8, 0.9)})
    strategies.update({f"coverage-{g}": coverage(g) for g in COVERAGE_GAINS})
    strategies.update({f"coverage-0.1-within-{t}": coverage(0.1, t) for t in (0.85, 0.9, 0.95)})
    strategies["coverage-0.1-within-0.9-max5"] = coverage(0.1, 0.9, max_resources=5)
    return strategies


COVERAGE_GAINS = (0.02, 0.05, 0.1, 0.15, 0.2, 0.3)


def split_of(query_id: str) -> str:
    """Deterministic 50/50 dev/test split: tune thresholds on dev, report test."""

    return "dev" if int(hashlib.sha1(query_id.encode("utf-8")).hexdigest(), 16) % 2 == 0 else "test"


def evaluate(name: str, retriever, registry, to_toolret, queries, selection_strategies) -> dict:
    records = []
    latencies = []
    decomposed = retriever if isinstance(retriever, DecomposedRetriever) else getattr(retriever, "inner", None)
    goal_weights: list[float] = []
    for position, query in enumerate(queries):
        started = time.perf_counter()
        results = retriever.search(registry, SearchQuery(task=query.query, top_k=POOL))
        elapsed = (time.perf_counter() - started) * 1000
        if position:  # the first query builds indexes and embeddings
            latencies.append(elapsed)
        if isinstance(decomposed, DecomposedRetriever) and decomposed.last_subtasks:
            goal_weights.append(decomposed.last_goal_weight)
        ranked = [to_toolret[result.resource.metadata.id] for result in results]
        gold = set(query.labels)
        record = {
            "id": query.id,
            "subset": query.subset,
            "split": split_of(query.id),
            "gold_size": len(gold),
            "ndcg@10": toolret.ndcg_at_k(ranked, gold, 10),
            "recall@10": toolret.recall_at_k(ranked, gold, 10),
            "complete@10": toolret.completeness_at_k(ranked, gold, 10),
            "recall@100": toolret.recall_at_k(ranked, gold, 100),
            "complete@100": toolret.completeness_at_k(ranked, gold, 100),
            "sets": {},
        }
        for label, strategy in selection_strategies.items():
            chosen = strategy(results, query)
            record["sets"][label] = toolret.set_scores({to_toolret[r.resource.metadata.id] for r in chosen}, gold)
        records.append(record)
        if (position + 1) % 200 == 0:
            print(f"  {name}: {position + 1}/{len(queries)}", flush=True)
    return {"records": records, "latencies": latencies, "goal_weights": goal_weights}


def aggregate(records: list[dict], latencies: list[float]) -> dict:
    metrics = ["ndcg@10", "recall@10", "complete@10", "recall@100", "complete@100"]

    def mean(rows, key):
        return round(statistics.mean(row[key] for row in rows), 4) if rows else 0.0

    def macro(rows):
        by_subset: dict[str, list[dict]] = defaultdict(list)
        for record in rows:
            by_subset[record["subset"]].append(record)
        if not by_subset:
            return {}
        return {key: round(statistics.mean(mean(group, key) for group in by_subset.values()), 4) for key in metrics}

    by_subset: dict[str, list[dict]] = defaultdict(list)
    for record in records:
        by_subset[record["subset"]].append(record)
    multi = [record for record in records if record["gold_size"] > 1]
    summary = {
        "queries": len(records),
        "multi_tool_queries": len(multi),
        "micro": {key: mean(records, key) for key in metrics},
        "macro": macro(records),
        "macro_dev": macro([record for record in records if record["split"] == "dev"]),
        "macro_test": macro([record for record in records if record["split"] == "test"]),
        "multi_tool": {key: mean(multi, key) for key in metrics},
        "per_subset": {subset: {key: mean(rows, key) for key in metrics} | {"queries": len(rows)} for subset, rows in sorted(by_subset.items())},
        "latency_ms": {
            "mean": round(statistics.mean(latencies), 2) if latencies else 0.0,
            "p50": round(statistics.median(latencies), 2) if latencies else 0.0,
            "p95": round(sorted(latencies)[int(len(latencies) * 0.95)], 2) if latencies else 0.0,
        },
        "sets": {},
    }
    labels = records[0]["sets"].keys() if records else []
    for label in labels:
        summary["sets"][label] = {}
        for split in ("all", "dev", "test"):
            rows = [record for record in records if split == "all" or record["split"] == split]
            if not rows:
                continue
            sets = [record["sets"][label] for record in rows]
            multi_rows = [record["sets"][label] for record in rows if record["gold_size"] > 1]
            summary["sets"][label][split] = {
                key: round(statistics.mean(row[key] for row in sets), 4)
                for key in ("precision", "recall", "f1", "exact", "complete", "size")
            } | {"multi_tool_f1": round(statistics.mean(row["f1"] for row in multi_rows), 4) if multi_rows else 0.0}
    return summary


def paired_bootstrap(differences: list[float], *, samples: int = 2000, seed: int = 0) -> dict:
    """Mean of per-query differences with a 95% percentile bootstrap interval."""

    rng = random.Random(seed)
    count = len(differences)
    means = sorted(statistics.mean(rng.choices(differences, k=count)) for _ in range(samples))
    return {
        "mean_difference": round(statistics.mean(differences), 4),
        "ci95": [round(means[int(0.025 * samples)], 4), round(means[int(0.975 * samples) - 1], 4)],
        "queries": count,
    }


def comparisons(records_by_retriever: dict[str, list[dict]], baseline: str, pairs: list[tuple[str, str]]) -> dict:
    """Paired test-split differences: ranking metrics vs ``baseline``, set F1 vs top-1."""

    out: dict = {"ranking_vs_baseline": {}, "set_f1_vs_top1": {}}
    base = {record["id"]: record for record in records_by_retriever.get(baseline, []) if record["split"] == "test"}
    for name, records in records_by_retriever.items():
        test = [record for record in records if record["split"] == "test"]
        if name != baseline and base:
            out["ranking_vs_baseline"][name] = {
                metric: paired_bootstrap([record[metric] - base[record["id"]][metric] for record in test])
                for metric in ("ndcg@10", "complete@10")
            }
        out["set_f1_vs_top1"][name] = {
            strategy: paired_bootstrap([record["sets"][strategy]["f1"] - record["sets"]["top-1"]["f1"] for record in test])
            for strategy, reference in pairs
            if reference == "top-1" and strategy in test[0]["sets"]
        }
    return out


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--download", action="store_true", help="fetch the dataset into benchmarks/data/toolret first")
    parser.add_argument("--per-subset", type=int, default=60, help="queries sampled per subset (0 = all 7,961)")
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--retrievers", default="lexical")
    parser.add_argument("--embed-model", default="sentence-transformers/all-MiniLM-L6-v2")
    parser.add_argument("--query-prefix", default="", help="instruction prepended to queries only (asymmetric models)")
    parser.add_argument("--embed-threads", type=int, default=None)
    parser.add_argument(
        "--language",
        choices=["en", "ja", "en-translated"],
        default="en",
        help="ja: the Japanese translations of a test sample (run_toolret_llm_stages.py --stage translate-ja); "
        "en-translated: the same queries in English",
    )
    parser.add_argument("--split", choices=["all", "dev", "test"], default="all", help="restrict the queries to one split")
    parser.add_argument("--output", default=str(Path(__file__).parent / "results" / "toolret.json"))
    parser.add_argument("--records", default=None,
                        help="also write per-query ranking metrics here, for paired comparisons across runs")
    args = parser.parse_args()

    if args.download:
        toolret.download()
    if not (toolret.DATA_DIR / "tools" / "web.parquet").exists():
        raise SystemExit("ToolRet is not downloaded: run with --download (needs network access to huggingface.co)")

    tools = toolret.load_tools()
    queries = toolret.sample_queries(toolret.load_queries(), args.per_subset or None, seed=args.seed)
    if args.split != "all":
        queries = [query for query in queries if split_of(query.id) == args.split]
    if args.language != "en":
        translations = load_cache(TRANSLATION_CACHE)
        queries = [query for query in queries if query.id in translations]
        if args.language == "ja":
            queries = [replace(query, query=translations[query.id]) for query in queries]
    registry, to_toolret = toolret.build_registry(tools)
    names = [name.strip() for name in args.retrievers.split(",") if name.strip()]
    decompositions = load_cache(DECOMPOSITION_CACHE)
    provider = None
    if any(name != "lexical" for name in names):
        provider = toolret.CachedEmbeddingProvider(args.embed_model, threads=args.embed_threads,
                                                   query_prefix=args.query_prefix)

    report: dict = {
        "benchmark": "ToolRet (mangopy/ToolRet-Queries, mangopy/ToolRet-Tools)",
        "corpus_tools": len(tools),
        "queries": len(queries),
        "per_subset": args.per_subset,
        "language": args.language,
        "split": args.split,
        "seed": args.seed,
        "embedding_model": args.embed_model if provider else None,
        "query_prefix": args.query_prefix if provider else None,
        "pool": POOL,
        "retrievers": {},
    }
    records_by_retriever: dict[str, list[dict]] = {}
    for name in names:
        print(f"running {name} on {len(queries)} queries", flush=True)
        retriever = build_retriever(name, provider, decompositions)
        strategies = selectors(name, language=args.language)
        outcome = evaluate(name, retriever, registry, to_toolret, queries, strategies)
        records_by_retriever[name] = outcome["records"]
        report["retrievers"][name] = aggregate(outcome["records"], outcome["latencies"])
        if outcome["goal_weights"]:
            weights = outcome["goal_weights"]
            report["retrievers"][name]["decomposed_queries"] = len(weights)
            report["retrievers"][name]["goal_weight_mean"] = round(statistics.mean(weights), 4)
        if "llm-set" in strategies:
            report["retrievers"][name]["llm_set_cache_misses"] = strategies["llm-set"].selector.failures
        for component in (retriever, getattr(retriever, "inner", None)):
            if isinstance(component, LLMRerankRetriever):
                report["retrievers"][name]["rerank_cache_misses"] = component.failures
        if provider is not None:
            provider.save()
        summary = report["retrievers"][name]
        print(json.dumps({"micro": summary["micro"], "macro": summary["macro"], "latency": summary["latency_ms"]}), flush=True)

    pairs = [(strategy, "top-1") for strategy in ("coverage-0.1", "coverage-0.1-within-0.95", "ratio-0.9", "llm-set", "oracle-k")]
    report["comparisons"] = comparisons(records_by_retriever, names[0], pairs)
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(stamp(report), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {output}")
    if args.records:
        keys = ("subset", "split", "ndcg@10", "complete@10", "recall@100", "complete@100")
        per_query = {name: {record["id"]: {key: record[key] for key in keys} for record in records}
                     for name, records in records_by_retriever.items()}
        Path(args.records).write_text(json.dumps(per_query) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
