"""Adaptive-layer benchmark: routing cache (案F) and execution feedback (F-LOG-08).

§15.4 (第3層: 適応) cannot be scored with the static harnesses: it asks how
routing improves *from past executions*, so it needs a traffic stream and an
observed outcome per task, not a single pass over scenarios. This script
supplies both, and adds the End-to-end axis §15.7 requires alongside the
ranking and set metrics.

**Task Success Rate (simulated).** Executing 28 scenarios for real would need
28 working tool backends, so the outcome is derived from the routed set under
an explicit sufficiency model:

- ``selected`` scenarios succeed when the routed set is a superset of the
  gold set *and* is dependency-closed and policy-feasible. Extra members cost
  context, not correctness — the model has what the task needs.
- ``abstain`` / ``escalate`` scenarios succeed when the router returns that
  status. Correctly refusing is the successful outcome (§15.6).

This is a proxy and is labelled as one in the report (``task_success_model``).
It is deterministic, which is what the adaptive layer needs: the same routing
decision must always yield the same feedback signal, or per-epoch differences
could not be attributed to learning.

**Experiment 1 — routing cache (default).** Replays a shuffled stream of the
scenarios for ``--epochs`` passes under several configurations and reports
cache hit rate, Task Success Rate, Set F1, latency split by hit/miss, and
*regret*: on every cache hit the pipeline is also run in the shadow (never
timed, never fed back) so the harness can count hits where reuse produced a
worse outcome than re-deriving would have.

    no-cache          pipeline every time (baseline)
    cache-lexical     IDF token cosine over cached task statements
    cache-semantic    + embedding cosine (--cache-semantic-weight)
    cache-poisoned    store_failures=True — failed routings become cases too
    cache-stale-blind invalidate=False — cases key on resource id, not id@version

**Experiment 2 — threshold sweep (``--threshold-sweep``).** The similarity gate
is 案F's one real hyperparameter, and it trades hit rate against replaying a
set that does not fit. The sweep runs each threshold on several traffic seeds
(``--sweep-seeds``) and reports the spread, because which of a direct /
paraphrase pair is cached first is decided by the shuffle — and that is
exactly what decides whether the other can inherit it.

**Experiment 3 — registry drift (``--drift-probe``).** §15.4 names case
staleness as 案F's structural weakness. The probe warms a cache, republishes a
sample of the cached resources at 2.0.0 with an escalated ``side_effect``,
replays the stream, and compares the version-checking admission rule against
the id-only one — counting *unsafe replays*: cached sets handed back
containing a resource that is no longer what the selector approved.

**Experiment 4 — execution feedback (``--feedback``).** Runs the pipeline with
an ``ExecutionEvaluator`` writing measured ``ResourceStats`` back onto the
registry (F-LOG-08 → F-REG-05) between epochs, and reports per-epoch metrics.
``success`` is a scoring component of the composite score, so this measures
whether the loop the requirement document specifies actually moves routing —
in either direction.

Usage:
    python3 benchmarks/run_adaptive_benchmark.py [--retriever lexical|hybrid-model|...]
                                                 [--epochs 3] [--seed 7]
                                                 [--cache-embeddings hash|model]
                                                 [--threshold-sweep 0.3,0.4,0.5]
                                                 [--drift-probe] [--feedback]
"""

from __future__ import annotations

import argparse
import copy
import json
import random
import statistics
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(Path(__file__).parent))

from marmo_core import (  # noqa: E402
    CaseBasedRouter,
    ExecutionEvaluator,
    GreedyConstrainedSetSelector,
    HashingEmbeddingProvider,
    ResourceRegistry,
    RoutingCaseStore,
    SelectionContext,
    load_registry,
)
from marmo_core.loader import load_resource_definitions  # noqa: E402
from marmo_core.models import ResourceDefinition  # noqa: E402

from _provenance import stamp  # noqa: E402
from run_set_benchmark import PER_KIND_LIMITS, build_retriever  # noqa: E402

TASK_SUCCESS_MODEL = (
    "selected: gold set ⊆ routed set, dependency-closed and policy-feasible; "
    "abstain/escalate: routed status equals the expected status"
)


# -- outcome model ---------------------------------------------------------------


def task_succeeded(selection, scenario: dict, resources_by_id: dict) -> bool:
    """Simulated end-to-end outcome for one routed set (see module docstring)."""

    if scenario["expected_status"] != "selected":
        return selection.status == scenario["expected_status"]
    if selection.status != "selected":
        return False
    selected_ids = {result.resource.metadata.id for result in selection.results}
    gold = set(scenario["gold_set"])
    granted = set(scenario["granted_permissions"])
    if not gold <= selected_ids:
        return False
    closed = all(
        dependency in selected_ids
        for rid in selected_ids
        for dependency in resources_by_id[rid].metadata.dependencies
    )
    feasible = all(
        set(resources_by_id[rid].metadata.required_permissions) <= granted for rid in selected_ids
    )
    return closed and feasible


def set_scores(selection, scenario: dict) -> dict | None:
    if scenario["expected_status"] != "selected":
        return None
    gold = set(scenario["gold_set"])
    selected_ids = {result.resource.metadata.id for result in selection.results}
    true_positive = len(selected_ids & gold)
    precision = true_positive / len(selected_ids) if selected_ids else 0.0
    recall = true_positive / len(gold) if gold else 0.0
    f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) else 0.0
    return {"f1": f1, "exact": selected_ids == gold}


# -- stream ----------------------------------------------------------------------


def build_stream(scenarios: list[dict], *, epochs: int, seed: int) -> list[tuple[int, dict]]:
    """(epoch, scenario) traffic: each epoch is an independent shuffle.

    Shuffling per epoch keeps the cache from being warmed in a fixed order
    that would flatter it; the seed keeps every configuration on the exact
    same stream so differences are the router's, not the traffic's.
    """

    rng = random.Random(seed)
    stream: list[tuple[int, dict]] = []
    for epoch in range(epochs):
        ordered = list(scenarios)
        rng.shuffle(ordered)
        stream.extend((epoch, scenario) for scenario in ordered)
    return stream


def selection_context(scenario: dict, args) -> SelectionContext:
    return SelectionContext(
        task=scenario["task"],
        granted_permissions=tuple(sorted(set(scenario["granted_permissions"]))),
        per_kind_limits=PER_KIND_LIMITS,
        min_score=args.min_score,
        min_relevance=args.min_relevance,
    )


# -- experiment 1: routing cache -------------------------------------------------


def make_router(config: str, args, retriever, selector) -> CaseBasedRouter:
    store = RoutingCaseStore()
    kwargs = {"threshold": args.threshold, "top_k": args.pool}
    if config == "cache-semantic":
        store = RoutingCaseStore(
            embeddings=embedding_provider(args), semantic_weight=args.cache_semantic_weight
        )
    elif config == "cache-poisoned":
        kwargs["store_failures"] = True
    elif config == "cache-stale-blind":
        kwargs["invalidate"] = False
    return CaseBasedRouter(retriever, selector, store=store, **kwargs)


_EMBEDDINGS: dict[str, object] = {}


def embedding_provider(args):
    """One warmed provider per kind, shared across configurations.

    Model load happens on the first ``embed`` call; leaving it lazy would
    charge it to whichever cache miss came first and inflate that
    configuration's miss latency by hundreds of milliseconds.
    """

    provider = _EMBEDDINGS.get(args.cache_embeddings)
    if provider is None:
        if args.cache_embeddings == "hash":
            provider = HashingEmbeddingProvider(dimensions=512)
        else:
            from run_benchmark import FastembedEmbeddingProvider

            provider = FastembedEmbeddingProvider()
        provider.embed(["warm up"])
        _EMBEDDINGS[args.cache_embeddings] = provider
    return provider


def run_cache_config(
    config: str, args, registry, resources_by_id, stream, retriever, selector
) -> dict:
    """One configuration over the whole stream, with shadow-pipeline regret."""

    rows: list[dict] = []
    router = None if config == "no-cache" else make_router(config, args, retriever, selector)
    evaluator = ExecutionEvaluator()
    miss_reasons: dict[str, int] = {}

    for epoch, scenario in stream:
        context = selection_context(scenario, args)
        if router is None:
            start = time.perf_counter()
            selection = run_pipeline(registry, scenario, context, retriever, selector, args)
            latency_ms = (time.perf_counter() - start) * 1000.0
            source, similarity = "pipeline", 0.0
            decision = None
        else:
            decision = router.route(registry, scenario["task"], context=context)
            selection, latency_ms = decision.selection, decision.latency_ms
            source, similarity = decision.source, decision.similarity
            for reason in decision.miss_reasons:
                miss_reasons[reason] = miss_reasons.get(reason, 0) + 1

        success = task_succeeded(selection, scenario, resources_by_id)

        # Shadow run: what would re-deriving have produced on this hit? Never
        # timed and never recorded as a case — it only measures reuse regret.
        shadow_success = None
        if source == "cache" and args.shadow:
            shadow = run_pipeline(registry, scenario, context, retriever, selector, args)
            shadow_success = task_succeeded(shadow, scenario, resources_by_id)

        if router is not None and decision is not None:
            router.record(decision, success=success)
        evaluator.observe_task(
            scenario["task"],
            [result.resource.metadata.id for result in selection.results],
            success=success,
            latency_ms=latency_ms,
        )

        row = {
            "epoch": epoch,
            "style": scenario["style"],
            "expected_status": scenario["expected_status"],
            "status": selection.status,
            "status_ok": selection.status == scenario["expected_status"],
            "source": source,
            "similarity": similarity,
            "latency_ms": latency_ms,
            "success": success,
            "shadow_success": shadow_success,
        }
        row.update(set_scores(selection, scenario) or {})
        rows.append(row)

    summary = summarize_rows(rows)
    summary["cases_stored"] = len(router.store) if router else 0
    summary["evictions"] = router.evictions if router else 0
    summary["miss_reasons"] = dict(sorted(miss_reasons.items()))
    return summary


def warm_up(registry, scenarios, retriever, selector, args) -> None:
    """Pay every one-off cost before any latency is recorded.

    The first search builds the BM25 index and, for hybrid routes, embeds the
    whole corpus (~1s). Left cold, that lands entirely in whichever
    configuration runs first and would show up as that configuration being
    slower — the exact quantity this benchmark is comparing.

    The cache's embedding provider is warmed on the same task statements,
    because the retriever's provider memoizes query vectors during this pass
    and leaving the cache's cold would charge the semantic case index for an
    embedding the pipeline had already been given for free. On CPU a single
    fastembed call costs ~10ms; a genuinely novel task pays it on *either*
    path, so it does not separate the two and is excluded from both.
    """

    for scenario in scenarios:
        context = selection_context(scenario, args)
        run_pipeline(registry, scenario, context, retriever, selector, args)
    if getattr(args, "cache_embeddings", None):
        embedding_provider(args).embed([scenario["task"] for scenario in scenarios])


def run_pipeline(registry, scenario, context, retriever, selector, args):
    from marmo_core import SearchQuery

    query = SearchQuery(
        task=scenario["task"],
        granted_permissions=context.granted_permissions,
        top_k=args.pool,
    )
    return selector.select(retriever.search(registry, query), context=context)


def percentile(values: list[float], fraction: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = min(len(ordered) - 1, max(0, int(round(fraction * (len(ordered) - 1)))))
    return round(ordered[index], 3)


def summarize_rows(rows: list[dict]) -> dict:
    def mean(values: list[float]) -> float:
        return round(statistics.mean(values), 3) if values else 0.0

    hits = [row for row in rows if row["source"] == "cache"]
    misses = [row for row in rows if row["source"] != "cache"]
    set_rows = [row for row in rows if "f1" in row]
    regret = [
        row for row in hits if row["shadow_success"] is not None and row["shadow_success"] and not row["success"]
    ]
    rescue = [
        row for row in hits if row["shadow_success"] is not None and row["success"] and not row["shadow_success"]
    ]
    epochs = sorted({row["epoch"] for row in rows})
    return {
        "requests": len(rows),
        "task_success_rate": mean([float(row["success"]) for row in rows]),
        "cache_hit_rate": round(len(hits) / len(rows), 3) if rows else 0.0,
        "set_f1": mean([row["f1"] for row in set_rows]),
        "set_exact_match": mean([float(row["exact"]) for row in set_rows]),
        "status_accuracy": mean([float(row["status_ok"]) for row in rows]),
        "abstain_escalate_accuracy": mean(
            [float(row["status_ok"]) for row in rows if row["expected_status"] != "selected"]
        ),
        "latency_ms_mean": mean([row["latency_ms"] for row in rows]),
        "latency_ms_p50": percentile([row["latency_ms"] for row in rows], 0.50),
        "latency_ms_p95": percentile([row["latency_ms"] for row in rows], 0.95),
        "latency_ms_hit": mean([row["latency_ms"] for row in hits]),
        "latency_ms_hit_p50": percentile([row["latency_ms"] for row in hits], 0.50),
        "latency_ms_miss": mean([row["latency_ms"] for row in misses]),
        "latency_ms_miss_p50": percentile([row["latency_ms"] for row in misses], 0.50),
        "hit_regret": len(regret),
        "hit_rescue": len(rescue),
        "hit_regret_rate": round(len(regret) / len(hits), 3) if hits else 0.0,
        "by_epoch": {
            str(epoch): {
                "task_success_rate": mean(
                    [float(row["success"]) for row in rows if row["epoch"] == epoch]
                ),
                "cache_hit_rate": round(
                    sum(1 for row in rows if row["epoch"] == epoch and row["source"] == "cache")
                    / max(1, sum(1 for row in rows if row["epoch"] == epoch)),
                    3,
                ),
            }
            for epoch in epochs
        },
        "by_style": {
            style: {
                "task_success_rate": mean(
                    [float(row["success"]) for row in rows if row["style"] == style]
                ),
                "cache_hit_rate": round(
                    sum(1 for row in rows if row["style"] == style and row["source"] == "cache")
                    / max(1, sum(1 for row in rows if row["style"] == style)),
                    3,
                ),
            }
            for style in sorted({row["style"] for row in rows})
        },
    }


def run_threshold_sweep(
    args, registry, resources_by_id, scenarios, retriever, selector, thresholds
) -> dict:
    """Hit rate vs. regret as the similarity gate moves.

    The threshold is 案F's one real hyperparameter: low enough and a
    loosely-related task replays someone else's set, high enough and only
    verbatim repeats hit. The sweep reports both sides so the default is
    chosen from the curve rather than asserted.
    """

    warm_up(registry, scenarios, retriever, selector, args)
    seeds = [int(value) for value in str(args.sweep_seeds).split(",")]
    aggregated = ("task_success_rate", "set_f1", "cache_hit_rate", "status_accuracy")
    sweep: dict[str, dict] = {}
    for config in ("cache-lexical", "cache-semantic"):
        rows: dict[str, dict] = {}
        for threshold in thresholds:
            local = argparse.Namespace(**vars(args))
            local.threshold = threshold
            per_seed = {}
            for seed in seeds:
                stream = build_stream(scenarios, epochs=args.epochs, seed=seed)
                per_seed[str(seed)] = run_cache_config(
                    config, local, registry, resources_by_id, stream, retriever, selector
                )
            # Report the spread, not one seed: which of a direct/paraphrase
            # pair is cached first is decided by the shuffle, and that is
            # exactly what determines whether the other one can inherit it.
            rows[f"{threshold:.2f}"] = {
                **{
                    metric: {
                        "mean": round(statistics.mean(s[metric] for s in per_seed.values()), 3),
                        "min": round(min(s[metric] for s in per_seed.values()), 3),
                        "max": round(max(s[metric] for s in per_seed.values()), 3),
                    }
                    for metric in aggregated
                },
                "hit_regret_total": sum(s["hit_regret"] for s in per_seed.values()),
                "hit_rescue_total": sum(s["hit_rescue"] for s in per_seed.values()),
                "per_seed": per_seed,
            }
        sweep[config] = rows
    return {"thresholds": list(thresholds), "sweep_seeds": seeds, "sweep": sweep}


# -- experiment 2: registry drift ------------------------------------------------


DRIFT_SIDE_EFFECT = "irreversible"


def drift(definition: ResourceDefinition) -> ResourceDefinition:
    """The realistic upgrade a routing cache has to survive.

    A resource is republished at a new major version and its ``side_effect``
    escalates (``read`` → ``irreversible``). Permissions are untouched on
    purpose: the cache's permission re-verification would catch a permission
    change on its own, so this isolates what the *version* check is worth.
    A set that was safe to activate at 1.0.0 is not safe at 2.0.0, and the
    only thing standing between a cached decision and an irreversible
    resource is whether admission noticed the identity moved.
    """

    from dataclasses import replace as dataclass_replace

    return dataclass_replace(
        definition,
        metadata=dataclass_replace(
            definition.metadata, version="2.0.0", side_effect=DRIFT_SIDE_EFFECT
        ),
    )


def run_drift_probe(args, definitions, resources_by_id, scenarios, retriever, selector) -> dict:
    """Warm a cache, republish one gold resource, replay, compare admission rules."""

    # Drift a seeded sample of the resources that actually get cached (the
    # gold union). Drifting arbitrary corpus members would leave the cases
    # untouched and measure nothing.
    cacheable = sorted({rid for scenario in scenarios for rid in scenario["gold_set"]})
    rng = random.Random(args.seed)
    sample_size = max(1, round(len(cacheable) * args.drift_fraction))
    targets = set(rng.sample(cacheable, sample_size))
    report = {
        "drifted_resources": sorted(targets),
        "drift": f"1.0.0 -> 2.0.0, side_effect -> {DRIFT_SIDE_EFFECT}",
        "drift_fraction": args.drift_fraction,
        "conditions": {},
    }
    for invalidate in (True, False):
        registry = registry_from(definitions)
        router = CaseBasedRouter(
            retriever,
            selector,
            store=RoutingCaseStore(),
            threshold=args.threshold,
            top_k=args.pool,
            invalidate=invalidate,
        )
        warm = [(0, scenario) for scenario in scenarios]
        for _, scenario in warm:
            context = selection_context(scenario, args)
            decision = router.route(registry, scenario["task"], context=context)
            router.record(
                decision,
                success=task_succeeded(decision.selection, scenario, resources_by_id),
            )

        drifted_definitions = [
            drift(definition) if definition.metadata.id in targets else definition
            for definition in definitions
        ]
        drifted_registry = registry_from(drifted_definitions)
        drifted_by_id = {d.metadata.id: d for d in drifted_definitions}
        live_identities = {d.identity for d in drifted_definitions}

        rows: list[dict] = []
        stale_misses = 0
        for scenario in scenarios:
            context = selection_context(scenario, args)
            decision = router.route(drifted_registry, scenario["task"], context=context)
            stale_misses += decision.miss_reasons.count("stale")
            success = task_succeeded(decision.selection, scenario, drifted_by_id)
            replayed_stale = decision.cached and any(
                member.identity not in live_identities
                for member in (decision.case.members if decision.case else ())
            )
            # Safety readout: did the router hand back a set that now contains
            # an irreversible resource it was never validated against?
            unsafe_replay = decision.cached and any(
                result.resource.metadata.side_effect == DRIFT_SIDE_EFFECT
                for result in decision.selection.results
            )
            rows.append(
                {
                    "epoch": 0,
                    "style": scenario["style"],
                    "expected_status": scenario["expected_status"],
                    "status": decision.selection.status,
                    "status_ok": decision.selection.status == scenario["expected_status"],
                    "source": decision.source,
                    "similarity": decision.similarity,
                    "latency_ms": decision.latency_ms,
                    "success": success,
                    "shadow_success": None,
                    "replayed_stale": replayed_stale,
                    "unsafe_replay": unsafe_replay,
                }
            )
            rows[-1].update(set_scores(decision.selection, scenario) or {})

        summary = summarize_rows(rows)
        summary["stale_misses"] = stale_misses
        summary["stale_identities_replayed"] = sum(1 for row in rows if row["replayed_stale"])
        summary["unsafe_replays"] = sum(1 for row in rows if row["unsafe_replay"])
        report["conditions"]["version-checked" if invalidate else "id-only"] = summary
    return report


def registry_from(definitions) -> ResourceRegistry:
    registry = ResourceRegistry()
    registry.extend(copy.deepcopy(list(definitions)))
    return registry


# -- experiment 3: execution feedback --------------------------------------------


def run_feedback_probe(args, definitions, scenarios, retriever, selector) -> dict:
    """Pipeline + ExecutionEvaluator write-back between epochs (F-LOG-08 → F-REG-05)."""

    report = {"conditions": {}}
    for feedback in (False, True):
        registry = registry_from(definitions)
        resources_by_id = {d.metadata.id: d for d in registry.all()}
        evaluator = ExecutionEvaluator(
            prior_weight=args.prior_weight, prior_success_rate=args.prior_success_rate
        )
        stream = build_stream(scenarios, epochs=args.epochs, seed=args.seed)
        rows: list[dict] = []
        applied = 0
        current_epoch = 0
        for epoch, scenario in stream:
            if feedback and epoch != current_epoch:
                applied += evaluator.apply(registry)
                resources_by_id = {d.metadata.id: d for d in registry.all()}
                current_epoch = epoch
            context = selection_context(scenario, args)
            start = time.perf_counter()
            selection = run_pipeline(registry, scenario, context, retriever, selector, args)
            latency_ms = (time.perf_counter() - start) * 1000.0
            success = task_succeeded(selection, scenario, resources_by_id)
            evaluator.observe_task(
                scenario["task"],
                [result.resource.metadata.id for result in selection.results],
                success=success,
                latency_ms=latency_ms,
            )
            row = {
                "epoch": epoch,
                "style": scenario["style"],
                "expected_status": scenario["expected_status"],
                "status": selection.status,
                "status_ok": selection.status == scenario["expected_status"],
                "source": "pipeline",
                "similarity": 0.0,
                "latency_ms": latency_ms,
                "success": success,
                "shadow_success": None,
            }
            row.update(set_scores(selection, scenario) or {})
            rows.append(row)
        summary = summarize_rows(rows)
        summary["stats_written"] = applied
        summary["resources_observed"] = evaluator.report()["resources_observed"]
        report["conditions"]["feedback" if feedback else "static"] = summary
    return report


# -- entrypoint ------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--corpus", default=str(Path(__file__).parent / "corpus" / "set_corpus.json"))
    parser.add_argument("--scenarios", default=str(Path(__file__).parent / "set_scenarios.json"))
    parser.add_argument("--distractors", default=None, help="extra resource dir mixed in as retrieval noise")
    parser.add_argument("--retriever", default="lexical", help="first-layer route used on cache misses")
    parser.add_argument("--pool", type=int, default=50)
    parser.add_argument("--min-score", type=float, default=0.45)
    parser.add_argument("--min-relevance", type=float, default=0.55)
    parser.add_argument("--epochs", type=int, default=3, help="passes over the scenario set")
    parser.add_argument("--seed", type=int, default=7, help="traffic shuffle seed (shared by all configs)")
    parser.add_argument("--threshold", type=float, default=0.72, help="case similarity needed for a cache hit")
    parser.add_argument("--cache-embeddings", default="hash", choices=["hash", "model"])
    parser.add_argument("--cache-semantic-weight", type=float, default=0.6)
    parser.add_argument("--prior-weight", type=float, default=2.0, help="ExecutionEvaluator shrinkage pseudo-counts")
    parser.add_argument("--prior-success-rate", type=float, default=0.5)
    parser.add_argument("--no-shadow", dest="shadow", action="store_false", help="skip the regret shadow pipeline")
    parser.add_argument("--drift-probe", action="store_true", help="run the registry-drift experiment only")
    parser.add_argument("--drift-fraction", type=float, default=0.25, help="share of cached resources republished in the drift probe")
    parser.add_argument("--feedback", action="store_true", help="run the execution-feedback experiment only")
    parser.add_argument(
        "--threshold-sweep",
        default=None,
        help="comma-separated similarity thresholds to sweep instead of the config comparison",
    )
    parser.add_argument(
        "--sweep-seeds",
        default="7,13,29,101",
        help="traffic seeds averaged in the threshold sweep",
    )
    parser.add_argument("--output", default=str(Path(__file__).parent / "results" / "adaptive-routing.json"))
    args = parser.parse_args()

    paths = [args.corpus] + ([args.distractors] if args.distractors else [])
    definitions = load_resource_definitions(paths)
    registry = load_registry(paths)
    resources_by_id = {d.metadata.id: d for d in registry.all()}
    scenarios = json.loads(Path(args.scenarios).read_text(encoding="utf-8"))["scenarios"]
    retriever = build_retriever(args.retriever)
    selector = GreedyConstrainedSetSelector()

    header = {
        "retriever": args.retriever,
        "selector": "greedy",
        "corpus_size": len(registry),
        "distractors": args.distractors,
        "scenarios": len(scenarios),
        "epochs": args.epochs,
        "seed": args.seed,
        "threshold": args.threshold,
        "pool": args.pool,
        "task_success_model": TASK_SUCCESS_MODEL,
    }

    if args.drift_probe:
        report = {**header, "mode": "drift-probe"}
        report.update(run_drift_probe(args, definitions, resources_by_id, scenarios, retriever, selector))
        print_drift(report)
    elif args.feedback:
        report = {**header, "mode": "feedback"}
        report.update(run_feedback_probe(args, definitions, scenarios, retriever, selector))
        print_feedback(report)
    elif args.threshold_sweep:
        thresholds = [float(value) for value in args.threshold_sweep.split(",")]
        report = {**header, "mode": "threshold-sweep"}
        report.update(
            run_threshold_sweep(
                args, registry, resources_by_id, scenarios, retriever, selector, thresholds
            )
        )
        print_sweep(report)
    else:
        warm_up(registry, scenarios, retriever, selector, args)
        stream = build_stream(scenarios, epochs=args.epochs, seed=args.seed)
        configs = [
            "no-cache",
            "cache-lexical",
            "cache-semantic",
            "cache-poisoned",
            "cache-stale-blind",
        ]
        report = {**header, "mode": "cache", "configs": {}}
        for config in configs:
            report["configs"][config] = run_cache_config(
                config, args, registry, resources_by_id, stream, retriever, selector
            )
        print_cache(report)

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(stamp(report), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"report written to {output_path}")


def print_cache(report: dict) -> None:
    print(
        f"corpus: {report['corpus_size']} resources | retriever: {report['retriever']} | "
        f"{report['epochs']} epochs x {report['scenarios']} scenarios (seed {report['seed']})"
    )
    for config, stats in report["configs"].items():
        print(
            f"  {config:<18} TSR {stats['task_success_rate']:.3f} | hit {stats['cache_hit_rate']:.0%} | "
            f"SetF1 {stats['set_f1']:.3f} | status {stats['status_accuracy']:.0%} "
            f"(abstain/esc {stats['abstain_escalate_accuracy']:.0%}) | "
            f"p50 {stats['latency_ms_p50']:.3f}ms (hit {stats['latency_ms_hit_p50']:.3f} / "
            f"miss {stats['latency_ms_miss_p50']:.3f}) | regret {stats['hit_regret']} | "
            f"cases {stats['cases_stored']} | evict {stats['evictions']}"
        )


def print_sweep(report: dict) -> None:
    print(
        f"threshold sweep | retriever {report['retriever']} | "
        f"seeds {report['sweep_seeds']} | mean [min-max] over seeds"
    )
    for config, rows in report["sweep"].items():
        print(f"  [{config}]")
        for threshold, stats in rows.items():
            tsr, f1 = stats["task_success_rate"], stats["set_f1"]
            print(
                f"    t={threshold} hit {stats['cache_hit_rate']['mean']:.0%} | "
                f"TSR {tsr['mean']:.3f} [{tsr['min']:.3f}-{tsr['max']:.3f}] | "
                f"SetF1 {f1['mean']:.3f} [{f1['min']:.3f}-{f1['max']:.3f}] | "
                f"regret {stats['hit_regret_total']} | rescue {stats['hit_rescue_total']} | "
                f"status {stats['status_accuracy']['mean']:.0%}"
            )


def print_drift(report: dict) -> None:
    print(
        f"drift probe: {len(report['drifted_resources'])} cached resources "
        f"({report['drift_fraction']:.0%} of the gold union) {report['drift']}"
    )
    for condition, stats in report["conditions"].items():
        print(
            f"  {condition:<16} TSR {stats['task_success_rate']:.3f} | hit {stats['cache_hit_rate']:.0%} | "
            f"SetF1 {stats['set_f1']:.3f} | stale misses {stats['stale_misses']} | "
            f"stale replays {stats['stale_identities_replayed']} | "
            f"unsafe replays {stats['unsafe_replays']}"
        )


def print_feedback(report: dict) -> None:
    print(f"feedback probe: {report['epochs']} epochs, retriever {report['retriever']}")
    for condition, stats in report["conditions"].items():
        per_epoch = " ".join(
            f"e{epoch}:{values['task_success_rate']:.3f}" for epoch, values in stats["by_epoch"].items()
        )
        print(
            f"  {condition:<10} TSR {stats['task_success_rate']:.3f} | SetF1 {stats['set_f1']:.3f} | "
            f"stats written {stats['stats_written']} | per-epoch {per_epoch}"
        )


if __name__ == "__main__":
    main()
