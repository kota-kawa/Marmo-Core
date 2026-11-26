"""Paired comparison of two ToolRet runs from their ``--records`` files.

``run_toolret_benchmark.py`` compares retrievers within one run. Runs that
differ in the embedding model or the query instruction are separate runs,
so this script pairs their per-query records and reports, per retriever and
metric, the mean difference with a 95% percentile bootstrap interval:

    python3 benchmarks/run_toolret_benchmark.py ... --records /tmp/a.json
    python3 benchmarks/run_toolret_benchmark.py ... --records /tmp/b.json
    python3 benchmarks/compare_toolret_records.py b=/tmp/b.json a=/tmp/a.json --output results/x.json

Every run named after the first is compared against the first.
"""

from __future__ import annotations

import argparse
import json
import random
import statistics
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _provenance import stamp  # noqa: E402

METRICS = ("ndcg@10", "complete@10", "complete@100")


def paired(left: dict, right: dict, metric: str, samples: int = 2000) -> dict:
    keys = sorted(set(left) & set(right))
    differences = [left[key][metric] - right[key][metric] for key in keys]
    rng = random.Random(0)
    means = sorted(statistics.mean(rng.choices(differences, k=len(differences))) for _ in range(samples))
    return {"mean_difference": round(statistics.mean(differences), 4),
            "ci95": [round(means[int(0.025 * samples)], 4), round(means[int(0.975 * samples) - 1], 4)],
            "queries": len(keys)}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("runs", nargs="+", help="name=path of a --records file; the first is the reference")
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    runs = {}
    for item in args.runs:
        name, _, path = item.partition("=")
        runs[name] = json.loads(Path(path).read_text(encoding="utf-8"))
    reference, *others = runs
    report: dict = {"reference": reference, "comparisons": {}}
    for name in others:
        report["comparisons"][f"{name} - {reference}"] = {
            retriever: {metric: paired(records, runs[reference][retriever], metric) for metric in METRICS}
            for retriever, records in runs[name].items() if retriever in runs[reference]
        }
    output = Path(args.output)
    output.write_text(json.dumps(stamp(report), indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report["comparisons"], indent=1))


if __name__ == "__main__":
    main()
