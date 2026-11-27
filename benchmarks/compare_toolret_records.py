"""Paired comparison of two ToolRet runs from their ``--records`` files.

``run_toolret_benchmark.py`` compares retrievers within one run. Runs that
differ in the embedding model or the query instruction are separate runs,
so this script pairs their per-query records and reports, per retriever and
metric, the mean difference with a 95% percentile bootstrap interval:

    python3 benchmarks/run_toolret_benchmark.py ... --records /tmp/a.json
    python3 benchmarks/run_toolret_benchmark.py ... --records /tmp/b.json
    python3 benchmarks/compare_toolret_records.py b=/tmp/b.json a=/tmp/a.json --output results/x.json

Every run named after the first is compared against the first.

Metric definitions. The published tables average per subset first and then
across subsets (macro, ToolRet's convention), so the headline difference and
its interval use the same weighting: each bootstrap sample resamples the paired
queries *within* every subset and averages the per-subset mean differences with
equal weight. The query-equal (micro) difference is reported next to it under
``micro``; it weights large subsets more and is a different quantity, not a
tighter interval for the same one. Queries are paired by id; ids present in
only one run are counted under ``unpaired``, and a pair of runs with no id in
common is reported as ``no_shared_queries`` with the ids that were compared.
"""

from __future__ import annotations

import argparse
import json
import random
import statistics
import sys
from collections import defaultdict
from pathlib import Path
from typing import Mapping, Sequence

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _provenance import sha256_file, stamp  # noqa: E402

METRICS = ("ndcg@10", "complete@10", "complete@100")
PROVENANCE_KEY = "_provenance"
DEFINITIONS = {
    "macro": "mean over subsets of the per-subset mean difference; the bootstrap resamples queries "
    "within each subset (same weighting as the macro columns of the tables)",
    "micro": "mean over queries of the paired difference; the bootstrap resamples queries "
    "(weights large subsets more)",
}
_EXAMPLE_IDS = 3


def bootstrap_interval(groups: Sequence[Sequence[float]], *, samples: int = 2000, seed: int = 0) -> dict:
    """Mean of the group means, with a 95% percentile bootstrap interval.

    Every group is resampled on its own, so each keeps its size and the same
    weight in the average. One group is the ordinary mean over its items.
    """

    rng = random.Random(seed)
    means = sorted(
        statistics.fmean(statistics.fmean(rng.choices(group, k=len(group))) for group in groups)
        for _ in range(samples)
    )
    return {
        "mean_difference": round(statistics.fmean(statistics.fmean(group) for group in groups), 4),
        "ci95": [round(means[int(0.025 * samples)], 4), round(means[int(0.975 * samples) - 1], 4)],
    }


def paired(left: Mapping[str, Mapping], right: Mapping[str, Mapping], metric: str, samples: int = 2000) -> dict:
    """``left - right`` on the queries both runs scored, weighted as the tables are.

    ``left`` and ``right`` map a query id to a record with ``subset`` and the
    metric. The top-level fields are the macro (subset-equal) difference;
    ``micro`` is the query-equal one.
    """

    shared = sorted(set(left) & set(right))
    if not shared:
        return {
            "status": "no_shared_queries",
            "queries": 0,
            "left_queries": len(left),
            "right_queries": len(right),
            "left_example_ids": sorted(left)[:_EXAMPLE_IDS],
            "right_example_ids": sorted(right)[:_EXAMPLE_IDS],
            "hint": "the runs scored different queries: compare runs made with the same --per-subset, "
            "--seed, --split, and --language",
        }
    by_subset: dict[str, list[float]] = defaultdict(list)
    for key in shared:
        subset = left[key]["subset"]
        if right[key]["subset"] != subset:
            raise ValueError(f"query {key!r} is in subset {subset!r} in one run and {right[key]['subset']!r} in the other")
        by_subset[subset].append(left[key][metric] - right[key][metric])
    differences = [value for group in by_subset.values() for value in group]
    return {
        "weighting": "macro",
        **bootstrap_interval(list(by_subset.values()), samples=samples),
        "queries": len(shared),
        "subsets": len(by_subset),
        "unpaired": {"left_only": len(left) - len(shared), "right_only": len(right) - len(shared)},
        "micro": bootstrap_interval([differences], samples=samples),
    }


def load_records(path: Path) -> tuple[dict, dict | None]:
    """Per-retriever records of a ``--records`` file and the provenance stored with them, if any."""

    payload = json.loads(path.read_text(encoding="utf-8"))
    return {name: records for name, records in payload.items() if name != PROVENANCE_KEY}, payload.get(PROVENANCE_KEY)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("runs", nargs="+", help="name=path of a --records file; the first is the reference")
    parser.add_argument("--output", required=True)
    parser.add_argument("--split", choices=["all", "dev", "test"], default="all",
                        help="restrict both runs to one dev/test split before pairing")
    args = parser.parse_args()
    runs: dict[str, dict] = {}
    run_info: dict[str, dict] = {}
    for item in args.runs:
        name, _, path = item.partition("=")
        runs[name], provenance = load_records(Path(path))
        run_info[name] = {"records_file": Path(path).name, "records_sha256": sha256_file(Path(path)),
                          "provenance": provenance}
    if args.split != "all":
        runs = {
            name: {retriever: {key: record for key, record in records.items() if record["split"] == args.split}
                   for retriever, records in per_retriever.items()}
            for name, per_retriever in runs.items()
        }
    reference, *others = runs
    report: dict = {"reference": reference, "split": args.split, "definitions": DEFINITIONS,
                    "runs": run_info, "comparisons": {}, "skipped_retrievers": {}}
    failed = False
    for name in others:
        comparison = {}
        for retriever, records in runs[name].items():
            if retriever not in runs[reference]:
                continue
            comparison[retriever] = {
                metric: paired(records, runs[reference][retriever], metric) for metric in METRICS
            }
            failed |= any(entry.get("status") == "no_shared_queries" for entry in comparison[retriever].values())
        report["comparisons"][f"{name} - {reference}"] = comparison
        skipped = sorted(set(runs[name]) ^ set(runs[reference]))
        if skipped:
            report["skipped_retrievers"][name] = skipped
    output = Path(args.output)
    output.write_text(
        json.dumps(stamp(report, inputs={name: info["records_sha256"] for name, info in run_info.items()},
                         arguments=vars(args)), indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(report["comparisons"], indent=1))
    if report["skipped_retrievers"]:
        print(f"retrievers present in only one run were not compared: {report['skipped_retrievers']}", file=sys.stderr)
    if failed:
        print("no query id is shared between the runs; see no_shared_queries in the report", file=sys.stderr)
        raise SystemExit(2)


if __name__ == "__main__":
    main()
