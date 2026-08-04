"""Routing benchmark: retrieval quality, latency, and context-token savings.

Runs labeled scenarios (benchmarks/scenarios.json) against a resource corpus
(default: the bundled resources/skills, ~1,000 third-party skills) and reports:

- hit@1 / hit@5 / MRR — did an expected resource rank at the top? Scenarios
  may list several acceptable resource-id substrings (the corpus contains
  duplicate capabilities); the best rank among them counts.
- recall@20 / recall@50 — is an expected resource anywhere in the candidate
  pool a downstream set selector would receive? (With "any acceptable id
  counts" labels, recall@K equals hit@K.) Retrieval therefore always fetches
  at least 50 results; warm latency is measured at that depth.
- the same metrics broken down by task-wording style (direct / paraphrase /
  abstract), to show where lexical matching degrades
- index build time and warm per-query latency (mean / p95)
- estimated context-token savings of routing top-k metadata into the LLM
  instead of the whole catalog (the "context pollution" claim, measured)

Usage:
    python3 benchmarks/run_benchmark.py [--resources DIR] [--retriever lexical|hybrid-hash|hybrid-model]
                                        [--query-transform hyde] [--llm-rerank]

`hybrid-model` re-ranks with a real embedding model via fastembed (ONNX, CPU).
It needs `pip install '.[benchmark]'`; the core library stays zero-dependency.

`--cross-encoder` (§15.7 項目4) re-ranks the candidate pool with a local
cross-encoder via fastembed — the zero-LLM comparison target for
`--llm-rerank`: deterministic, offline, no per-query LLM cost.

`--query-transform hyde` (§15.2 案A 派生) and `--llm-rerank` (§15.2 案C 最小)
wrap the chosen retriever with LLM calls through the OpenAI-compatible
provider (OPENAI_API_KEY). Replies are cached in benchmarks/cache/ keyed by
task (and candidate pool), so re-runs are free and reproducible; warm latency
only includes LLM time on uncached calls.
"""

from __future__ import annotations

import argparse
import json
import statistics
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from marmo_core import (  # noqa: E402
    CrossEncoderProvider,
    CrossEncoderRerankRetriever,
    HashingEmbeddingProvider,
    HybridRetriever,
    HydeRetriever,
    LexicalRetriever,
    LLMRerankRetriever,
    OpenAICompatibleLLMProvider,
    EmbeddingProvider,
    SearchQuery,
    estimate_tokens,
    load_registry,
)

from _provenance import stamp  # noqa: E402

CACHE_DIR = Path(__file__).parent / "cache"


class FastembedEmbeddingProvider(EmbeddingProvider):
    """Real embedding model via fastembed (ONNX, CPU). Benchmark-only dependency."""

    def __init__(self, model: str = "BAAI/bge-small-en-v1.5") -> None:
        try:
            from fastembed import TextEmbedding
        except ImportError as error:
            raise SystemExit(
                "hybrid-model requires fastembed: pip install '.[benchmark]'"
            ) from error
        self.model_name = model
        self._model = TextEmbedding(model)
        self._memo: dict[str, list[float]] = {}

    def embed(self, texts):
        missing = [text for text in texts if text not in self._memo]
        if missing:
            for text, vector in zip(missing, self._model.embed(missing)):
                self._memo[text] = [float(value) for value in vector]
        return [self._memo[text] for text in texts]


class FastembedCrossEncoderProvider(CrossEncoderProvider):
    """Local cross-encoder via fastembed (ONNX, CPU). Benchmark-only dependency."""

    def __init__(self, model: str = "Xenova/ms-marco-MiniLM-L-6-v2") -> None:
        try:
            from fastembed.rerank.cross_encoder import TextCrossEncoder
        except ImportError as error:
            raise SystemExit(
                "--cross-encoder requires fastembed: pip install '.[benchmark]'"
            ) from error
        self.model_name = model
        self._model = TextCrossEncoder(model)

    def score(self, query, documents):
        return [float(value) for value in self._model.rerank(query, list(documents))]


def build_retriever(name: str, *, semantic_weight: float, candidate_pool: int, embed_model: str):
    if name == "lexical":
        return LexicalRetriever()
    if name == "hybrid-hash":
        return HybridRetriever(
            HashingEmbeddingProvider(dimensions=512),
            semantic_weight=semantic_weight,
            candidate_pool=candidate_pool,
        )
    if name == "hybrid-model":
        return HybridRetriever(
            FastembedEmbeddingProvider(embed_model),
            semantic_weight=semantic_weight,
            candidate_pool=candidate_pool,
        )
    raise SystemExit(f"unknown retriever: {name}")


class _JsonFileCache(dict):
    """A dict backed by a JSON file; call save() after the run."""

    def __init__(self, path: Path) -> None:
        super().__init__()
        self.path = path
        if path.exists():
            self.update(json.loads(path.read_text(encoding="utf-8")))

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(
            json.dumps(dict(self), ensure_ascii=False, indent=1, sort_keys=True) + "\n",
            encoding="utf-8",
        )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--resources", default=str(REPO_ROOT / "resources" / "skills"))
    parser.add_argument("--scenarios", default=str(Path(__file__).parent / "scenarios.json"))
    parser.add_argument("--retriever", default="lexical", choices=["lexical", "hybrid-hash", "hybrid-model"])
    parser.add_argument("--top-k", type=int, default=5)
    parser.add_argument("--semantic-weight", type=float, default=0.3, help="blend weight for the semantic score in hybrid retrievers")
    parser.add_argument("--candidate-pool", type=int, default=50, help="BM25 candidate pool size re-ranked by hybrid retrievers")
    parser.add_argument("--embed-model", default="BAAI/bge-small-en-v1.5", help="fastembed model for --retriever hybrid-model")
    parser.add_argument("--query-transform", default="none", choices=["none", "hyde"], help="rewrite each task with one LLM call before retrieval (15.2 案A 派生)")
    parser.add_argument("--llm-rerank", action="store_true", help="re-rank the candidate pool with one LLM call per task (15.2 案C 最小)")
    parser.add_argument("--cross-encoder", action="store_true", help="re-rank the candidate pool with a local cross-encoder (15.7 項目4)")
    parser.add_argument("--cross-encoder-model", default="Xenova/ms-marco-MiniLM-L-6-v2", help="fastembed cross-encoder model for --cross-encoder")
    parser.add_argument("--cross-encoder-weight", type=float, default=1.0, help="blend weight of the cross-encoder score in the relevance component")
    parser.add_argument("--llm-model", default="gpt-5.6-terra", help="OpenAI-compatible chat model for --query-transform / --llm-rerank")
    parser.add_argument("--rerank-pool", type=int, default=50, help="candidates shown to the LLM re-ranker")
    parser.add_argument("--output", default=str(Path(__file__).parent / "results" / "latest.json"))
    args = parser.parse_args()

    scenarios = json.loads(Path(args.scenarios).read_text(encoding="utf-8"))["scenarios"]

    load_start = time.perf_counter()
    registry = load_registry([args.resources])
    load_seconds = time.perf_counter() - load_start
    corpus_size = len(registry)

    retriever = build_retriever(
        args.retriever,
        semantic_weight=args.semantic_weight,
        candidate_pool=args.candidate_pool,
        embed_model=args.embed_model,
    )

    retriever_label = args.retriever
    caches: list[_JsonFileCache] = []
    llm_wrappers: list = []
    if args.query_transform == "hyde" or args.llm_rerank:
        llm = OpenAICompatibleLLMProvider(model=args.llm_model, max_tokens=512)
        if not llm.api_key:
            raise SystemExit("--query-transform/--llm-rerank need OPENAI_API_KEY")
    if args.query_transform == "hyde":
        cache = _JsonFileCache(CACHE_DIR / f"hyde-{args.llm_model}.json")
        caches.append(cache)
        retriever = HydeRetriever(llm, retriever, cache=cache)
        llm_wrappers.append(retriever)
        retriever_label += "+hyde"
    if args.cross_encoder:
        retriever = CrossEncoderRerankRetriever(
            FastembedCrossEncoderProvider(args.cross_encoder_model),
            retriever,
            rerank_pool=args.rerank_pool,
            weight=args.cross_encoder_weight,
        )
        retriever_label += "+ce"
    if args.llm_rerank:
        cache = _JsonFileCache(CACHE_DIR / f"rerank-{args.llm_model}.json")
        caches.append(cache)
        retriever = LLMRerankRetriever(llm, retriever, rerank_pool=args.rerank_pool, cache=cache)
        llm_wrappers.append(retriever)
        retriever_label += "+rerank"

    eval_k = max(args.top_k, 50)

    # First search builds the index; measure it separately from warm latency.
    index_start = time.perf_counter()
    retriever.search(registry, SearchQuery(task=scenarios[0]["task"], top_k=eval_k))
    index_seconds = time.perf_counter() - index_start

    latencies_ms: list[float] = []
    ranks: list[int | None] = []
    styles: list[str] = []
    misses: list[dict] = []
    for scenario in scenarios:
        expected = scenario["expected"]
        if isinstance(expected, str):
            expected = [expected]
        query = SearchQuery(task=scenario["task"], top_k=eval_k)
        start = time.perf_counter()
        results = retriever.search(registry, query)
        latencies_ms.append((time.perf_counter() - start) * 1000.0)
        rank = next(
            (
                position + 1
                for position, result in enumerate(results)
                if any(needle in result.resource.metadata.id for needle in expected)
            ),
            None,
        )
        ranks.append(rank)
        styles.append(scenario.get("style", "unspecified"))
        if rank != 1:
            misses.append(
                {
                    "task": scenario["task"],
                    "expected": expected,
                    "style": scenario.get("style", "unspecified"),
                    "rank": rank,
                    "top1": results[0].resource.metadata.id if results else None,
                }
            )

    def metrics(subset: list[int | None]) -> dict:
        count = len(subset)
        return {
            "scenarios": count,
            "hit_at_1": round(sum(1 for rank in subset if rank == 1) / count, 3),
            "hit_at_5": round(sum(1 for rank in subset if rank is not None and rank <= 5) / count, 3),
            # MRR stays capped at top_k so numbers remain comparable with
            # reports produced before recall@K was added.
            "mrr": round(sum((1.0 / rank) for rank in subset if rank is not None and rank <= args.top_k) / count, 3),
            "recall_at_20": round(sum(1 for rank in subset if rank is not None and rank <= 20) / count, 3),
            "recall_at_50": round(sum(1 for rank in subset if rank is not None and rank <= 50) / count, 3),
        }

    total = len(scenarios)
    overall = metrics(ranks)
    hit1, hit5, mrr = overall["hit_at_1"], overall["hit_at_5"], overall["mrr"]
    recall20, recall50 = overall["recall_at_20"], overall["recall_at_50"]
    by_style = {
        style: metrics([rank for rank, s in zip(ranks, styles) if s == style])
        for style in sorted(set(styles))
    }

    # Token savings: metadata summaries of the whole catalog vs the routed top-k.
    all_summaries = "\n".join(
        json.dumps(definition.metadata.summary(), ensure_ascii=False) for definition in registry.all()
    )
    catalog_tokens = estimate_tokens(all_summaries)
    sample_results = retriever.search(registry, SearchQuery(task=scenarios[0]["task"], top_k=args.top_k))
    topk_text = "\n".join(
        json.dumps(result.resource.metadata.summary(), ensure_ascii=False) for result in sample_results
    )
    topk_tokens = estimate_tokens(topk_text)

    llm_failures = sum(wrapper.failures for wrapper in llm_wrappers)
    for cache in caches:
        cache.save()

    report = {
        "retriever": retriever_label,
        "retriever_config": (
            None
            if args.retriever == "lexical"
            else {
                "semantic_weight": args.semantic_weight,
                "candidate_pool": args.candidate_pool,
                "embed_model": args.embed_model if args.retriever == "hybrid-model" else None,
            }
        ),
        "llm_config": (
            {
                "model": args.llm_model,
                "query_transform": args.query_transform,
                "llm_rerank": args.llm_rerank,
                "rerank_pool": args.rerank_pool if args.llm_rerank else None,
                "failures": llm_failures,
            }
            if llm_wrappers
            else None
        ),
        "corpus_size": corpus_size,
        "scenarios": total,
        "top_k": args.top_k,
        "load_seconds": round(load_seconds, 3),
        "index_build_seconds": round(index_seconds, 3),
        "warm_latency_ms_mean": round(statistics.mean(latencies_ms), 2),
        "warm_latency_ms_p95": round(sorted(latencies_ms)[max(0, int(total * 0.95) - 1)], 2),
        "hit_at_1": hit1,
        "hit_at_5": hit5,
        "mrr": mrr,
        "recall_at_20": recall20,
        "recall_at_50": recall50,
        "by_style": by_style,
        "catalog_metadata_tokens": catalog_tokens,
        "routed_top_k_tokens": topk_tokens,
        "context_token_savings": round(1.0 - (topk_tokens / catalog_tokens), 4) if catalog_tokens else None,
        "misses": misses,
    }

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(stamp(report), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(f"corpus: {corpus_size} resources | retriever: {retriever_label}")
    if llm_wrappers:
        print(f"llm: {args.llm_model} | failures: {llm_failures}")
    print(f"load {load_seconds:.2f}s | index build {index_seconds:.2f}s")
    print(f"warm latency mean {report['warm_latency_ms_mean']}ms | p95 {report['warm_latency_ms_p95']}ms")
    print(
        f"hit@1 {hit1:.0%} | hit@5 {hit5:.0%} | MRR {mrr:.3f} "
        f"| recall@20 {recall20:.0%} | recall@50 {recall50:.0%}"
    )
    for style, stats in by_style.items():
        print(
            f"  {style}: hit@1 {stats['hit_at_1']:.0%} | hit@5 {stats['hit_at_5']:.0%} "
            f"| MRR {stats['mrr']:.3f} | recall@50 {stats['recall_at_50']:.0%} "
            f"({stats['scenarios']} scenarios)"
        )
    print(
        f"context tokens: full catalog ~{catalog_tokens:,} vs routed top-{args.top_k} ~{topk_tokens:,} "
        f"({report['context_token_savings']:.2%} saved)"
    )
    if misses:
        print(f"misses ({len(misses)}):")
        for miss in misses:
            print(f"  rank={miss['rank']} expected={miss['expected']} top1={miss['top1']}")
    print(f"report written to {output_path}")


if __name__ == "__main__":
    main()
