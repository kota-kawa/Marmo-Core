"""案I scale benchmark: flat vs hierarchical routing on a 10k+ catalog (§15.2).

Loads the gold set-selection corpus (63 resources, 28 scenarios) plus the
deterministic synthetic scale catalog (generate_scale_corpus.py, default
10,000 resources in a domain → provider → family hierarchy) and the six
cross-domain scenarios, then compares first-layer routes feeding the same
second layer (greedy constrained selector, the 12.1 default):

- flat:          ``lexical`` (案A), ``hybrid-model`` / ``hybrid-hash`` (案B)
- hierarchical:  ``hier-<strategy>-<base>`` where strategy ∈
                 {namespace, provider, permission, embedding} and base is a
                 flat route (e.g. ``hier-namespace-hybrid-model``)

案I-specific metrics (per retriever, §15.2):

- Routed Cluster Recall — gold resources whose group survived stage 1 —
  vs Oracle Cluster Recall (best possible group choice at the same
  route_k): the gap is pure routing error, the ceiling is partition error;
- scanned fraction: Σ routed group sizes / catalog size (search-space
  reduction is the point of 案I);
- candidate pool metadata tokens (what 案C would pay to show candidates);
- warm latency mean / p50 / p95 (first query per retriever is untimed
  warmup that builds indexes, embeddings, and partitions);
- everything run_set_benchmark reports (Set F1, closure, status accuracy),
  overall and split into standard vs cross-domain scenarios — cross-domain
  gold sets span two capability namespaces, the designed failure mode of
  coarse-to-fine routing.

Usage:
    python3 benchmarks/run_scale_benchmark.py \
        [--size 10000] [--route-k 3] [--retrievers lexical,hier-namespace-lexical,...]

``hybrid-model`` bases need ``pip install '.[benchmark]'``; one shared embedding
provider memoizes texts across all retrievers in the run.
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
sys.path.insert(0, str(Path(__file__).parent))

from marmo_core import (  # noqa: E402
    EmbeddingClusterGrouping,
    GreedyConstrainedSetSelector,
    HashingEmbeddingProvider,
    HierarchicalRetriever,
    HybridRetriever,
    LexicalRetriever,
    NamespaceGrouping,
    PermissionGrouping,
    ProviderGrouping,
    SearchQuery,
    SelectionContext,
    load_registry,
    tokenize,
)

from _provenance import stamp  # noqa: E402
from generate_scale_corpus import ensure_scale_corpus  # noqa: E402
from run_set_benchmark import PER_KIND_LIMITS, score_selection, summarize  # noqa: E402

CROSS_KIND_LIMITS = {kind: 2 for kind in PER_KIND_LIMITS}

DEFAULT_RETRIEVERS = ",".join(
    [
        "lexical",
        "hybrid-model",
        "hier-namespace-lexical",
        "hier-provider-lexical",
        "hier-permission-lexical",
        "hier-embedding-lexical",
        "hier-namespace-hybrid-model",
        "hier-provider-hybrid-model",
        "hier-embedding-hybrid-model",
    ]
)

STRATEGIES = ("namespace", "provider", "permission", "embedding")

_model_provider = None


def model_provider():
    global _model_provider
    if _model_provider is None:
        from run_benchmark import FastembedEmbeddingProvider

        _model_provider = FastembedEmbeddingProvider()
    return _model_provider


def build_flat(name: str):
    if name == "lexical":
        return LexicalRetriever()
    if name == "hybrid-hash":
        return HybridRetriever(HashingEmbeddingProvider(dimensions=512), semantic_weight=0.5)
    if name == "hybrid-model":
        return HybridRetriever(model_provider(), semantic_weight=0.9)
    raise SystemExit(f"unknown base retriever: {name}")


def build_strategy(name: str, base):
    if name == "namespace":
        return NamespaceGrouping()
    if name == "provider":
        return ProviderGrouping()
    if name == "permission":
        return PermissionGrouping()
    if name == "embedding":
        # Cluster with the base's own provider when it has one, so the
        # partition and the fine stage share a vector space; a lexical base
        # still needs a real model to cluster descriptions meaningfully.
        provider = base.embedding_provider if isinstance(base, HybridRetriever) else model_provider()
        return EmbeddingClusterGrouping(provider)
    raise SystemExit(f"unknown grouping strategy: {name}")


def build_retriever(name: str, route_k: int):
    if not name.startswith("hier-"):
        return build_flat(name)
    remainder = name.removeprefix("hier-")
    for strategy_name in STRATEGIES:
        if remainder.startswith(strategy_name + "-"):
            base = build_flat(remainder.removeprefix(strategy_name + "-"))
            return HierarchicalRetriever(base, build_strategy(strategy_name, base), route_k=route_k)
    raise SystemExit(f"unknown retriever spec: {name} (expected hier-<strategy>-<base>)")


def cluster_metrics(retriever, registry, query, gold: set[str], route_k: int) -> dict | None:
    """Routed vs oracle cluster recall and scanned fraction for one query."""

    if not isinstance(retriever, HierarchicalRetriever):
        return None
    partition = retriever.partition(registry)
    group_of = {rid: group for group, members in partition.items() for rid in members}
    total = sum(len(members) for members in partition.values())
    decisions = [decision for decision in retriever.route(registry, query) if decision.score > 0.0]
    routed = [decision.group for decision in decisions[:route_k]]
    if not routed:  # coarse stage had no signal: search() falls back to flat
        scanned = 1.0
        routed_recall = 1.0 if gold else None
    else:
        scanned = sum(len(partition[group]) for group in routed) / total if total else 0.0
        routed_recall = (
            sum(1 for rid in gold if group_of.get(rid) in set(routed)) / len(gold) if gold else None
        )
    oracle_recall = None
    if gold:
        gold_groups = sorted(
            {group_of[rid] for rid in gold if rid in group_of},
            key=lambda group: -sum(1 for rid in gold if group_of.get(rid) == group),
        )
        covered = set(gold_groups[:route_k])
        oracle_recall = sum(1 for rid in gold if group_of.get(rid) in covered) / len(gold)
    return {
        "scanned_fraction": scanned,
        "routed_cluster_recall": routed_recall,
        "oracle_cluster_recall": oracle_recall,
        "fallback": not routed,
    }


def subset_summary(records: list[dict], statuses: list[dict]) -> dict:
    summary = summarize(records, statuses, [])
    summary.pop("latency_ms_mean", None)
    summary.pop("mistakes", None)
    return summary


def run_one(name: str, retriever, registry, resources_by_id, scenarios, args) -> dict:
    selector = GreedyConstrainedSetSelector()
    warm_start = time.perf_counter()
    retriever.search(registry, SearchQuery(task=scenarios[0]["task"], top_k=args.pool))
    warmup_seconds = time.perf_counter() - warm_start

    records: list[dict] = []
    statuses: list[dict] = []
    latencies: list[float] = []
    pool_tokens: list[int] = []
    pool_recalls: list[float] = []
    cluster_rows: list[dict] = []
    tagged: list[tuple[dict, dict, dict | None]] = []

    for scenario in scenarios:
        gold = set(scenario["gold_set"])
        granted = set(scenario["granted_permissions"])
        cross = bool(scenario.get("cross_domain"))
        query = SearchQuery(
            task=scenario["task"],
            granted_permissions=tuple(sorted(granted)),
            top_k=args.pool,
        )
        start = time.perf_counter()
        candidates = retriever.search(registry, query)
        latencies.append((time.perf_counter() - start) * 1000.0)
        pool_tokens.append(
            sum(len(tokenize(result.resource.metadata.search_text())) for result in candidates)
        )
        if gold:
            surfaced = {result.resource.metadata.id for result in candidates}
            pool_recalls.append(len(gold & surfaced) / len(gold))
        row = cluster_metrics(retriever, registry, query, gold, args.route_k)
        if row is not None:
            cluster_rows.append(row)
        context = SelectionContext(
            task=scenario["task"],
            granted_permissions=tuple(sorted(granted)),
            per_kind_limits=CROSS_KIND_LIMITS if cross else PER_KIND_LIMITS,
            min_score=args.min_score,
            min_relevance=args.min_relevance,
        )
        selection = selector.select(candidates, context=context)
        status_record, set_record = score_selection(selection, scenario, resources_by_id)
        statuses.append(status_record)
        if set_record is not None:
            records.append(set_record)
        tagged.append((scenario, status_record, set_record))

    def split(cross: bool) -> dict:
        rows = [record for scenario, _, record in tagged if bool(scenario.get("cross_domain")) == cross and record]
        stats = [status for scenario, status, _ in tagged if bool(scenario.get("cross_domain")) == cross]
        return subset_summary(rows, stats)

    report = summarize(records, statuses, latencies)
    report["latency_ms_p50"] = round(statistics.median(latencies), 3)
    report["latency_ms_p95"] = round(sorted(latencies)[max(0, int(len(latencies) * 0.95) - 1)], 3)
    report["warmup_seconds"] = round(warmup_seconds, 2)
    report["retrieval_gold_recall"] = round(statistics.mean(pool_recalls), 3) if pool_recalls else 0.0
    report["pool_tokens_mean"] = round(statistics.mean(pool_tokens), 1) if pool_tokens else 0.0
    report["standard"] = split(cross=False)
    report["cross_domain"] = split(cross=True)
    if cluster_rows:
        routed = [row["routed_cluster_recall"] for row in cluster_rows if row["routed_cluster_recall"] is not None]
        oracle = [row["oracle_cluster_recall"] for row in cluster_rows if row["oracle_cluster_recall"] is not None]
        report["hierarchy"] = {
            "groups": len(retriever.partition(registry)),
            "route_k": args.route_k,
            "scanned_fraction_mean": round(statistics.mean(row["scanned_fraction"] for row in cluster_rows), 4),
            "routed_cluster_recall": round(statistics.mean(routed), 3) if routed else None,
            "oracle_cluster_recall": round(statistics.mean(oracle), 3) if oracle else None,
            "flat_fallbacks": sum(1 for row in cluster_rows if row["fallback"]),
        }
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--size", type=int, default=10_000, help="synthetic catalog size (0 disables the scale corpus)")
    parser.add_argument("--retrievers", default=DEFAULT_RETRIEVERS)
    parser.add_argument("--route-k", type=int, default=3)
    parser.add_argument("--pool", type=int, default=50)
    parser.add_argument("--min-score", type=float, default=0.45)
    parser.add_argument("--min-relevance", type=float, default=0.55)
    parser.add_argument("--output", default=None, help="default: results/scale-routing-<size>.json")
    args = parser.parse_args()

    corpus_paths = [str(Path(__file__).parent / "corpus" / "set_corpus.json")]
    if args.size:
        corpus_paths.append(str(ensure_scale_corpus(args.size)))
    registry = load_registry(corpus_paths)
    resources_by_id = {definition.metadata.id: definition for definition in registry.all()}

    scenarios = json.loads(
        (Path(__file__).parent / "set_scenarios.json").read_text(encoding="utf-8")
    )["scenarios"]
    scale_scenarios_path = Path(__file__).parent / "scale_scenarios.json"
    if scale_scenarios_path.exists():
        scenarios += json.loads(scale_scenarios_path.read_text(encoding="utf-8"))["scenarios"]

    report: dict = {
        "corpus_size": len(registry),
        "scale_size": args.size,
        "scenarios": len(scenarios),
        "pool": args.pool,
        "route_k": args.route_k,
        "min_score": args.min_score,
        "min_relevance": args.min_relevance,
        "selector": "greedy",
        "retrievers": {},
    }
    for name in [item.strip() for item in args.retrievers.split(",") if item.strip()]:
        retriever = build_retriever(name, args.route_k)
        result = run_one(name, retriever, registry, resources_by_id, scenarios, args)
        report["retrievers"][name] = result
        hierarchy = result.get("hierarchy")
        extra = ""
        if hierarchy:
            extra = (
                f" | scanned {hierarchy['scanned_fraction_mean']:.1%}"
                f" | cluster recall {hierarchy['routed_cluster_recall']:.0%}"
                f" (oracle {hierarchy['oracle_cluster_recall']:.0%})"
            )
        print(
            f"{name}: gold recall {result['retrieval_gold_recall']:.0%} | "
            f"SetF1 {result['set_f1']:.3f} (std {result['standard']['set_f1']:.3f} / "
            f"cross {result['cross_domain']['set_f1']:.3f}) | "
            f"status acc {result['status_accuracy']:.0%} | "
            f"p50 {result['latency_ms_p50']:.1f}ms p95 {result['latency_ms_p95']:.1f}ms{extra}"
        )

    output = Path(args.output) if args.output else (
        Path(__file__).parent / "results" / f"scale-routing-{args.size}.json"
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(stamp(report), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"report written to {output}")


if __name__ == "__main__":
    main()
