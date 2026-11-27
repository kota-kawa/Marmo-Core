from __future__ import annotations

import json
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "benchmarks"))

import compare_toolret_records  # noqa: E402
from compare_toolret_records import paired  # noqa: E402
from run_toolret_benchmark import aggregate, comparisons  # noqa: E402


def record(subset: str, value: float, *, split: str = "test") -> dict:
    return {"subset": subset, "split": split, "ndcg@10": value, "complete@10": value, "complete@100": value}


class PairedComparisonTests(unittest.TestCase):
    def test_pairs_queries_by_id_and_ignores_unpaired_ones(self) -> None:
        left = {"q1": record("a", 0.5), "q2": record("a", 1.0), "only-left": record("a", 1.0)}
        right = {"q1": record("a", 0.25), "q2": record("a", 0.5)}
        result = paired(left, right, "ndcg@10", samples=200)
        self.assertEqual(result["queries"], 2)
        self.assertEqual(result["unpaired"], {"left_only": 1, "right_only": 0})
        self.assertEqual(result["mean_difference"], 0.375)
        low, high = result["ci95"]
        self.assertTrue(0.25 <= low <= 0.375 <= high <= 0.5)

    def test_identical_runs_have_a_zero_interval(self) -> None:
        records = {f"q{i}": record("a", float(i % 2)) for i in range(20)}
        result = paired(records, records, "complete@10", samples=100)
        self.assertEqual((result["mean_difference"], result["ci95"]), (0.0, [0.0, 0.0]))

    def test_headline_difference_weights_subsets_equally_like_the_tables(self) -> None:
        # 9 queries of a big subset gain 0.1 each; the only query of a small subset gains 0.9.
        left = {f"big{i}": record("big", 0.2) for i in range(9)} | {"small": record("small", 1.0)}
        right = {f"big{i}": record("big", 0.1) for i in range(9)} | {"small": record("small", 0.1)}
        result = paired(left, right, "ndcg@10", samples=200)
        self.assertEqual(result["weighting"], "macro")
        self.assertEqual(result["subsets"], 2)
        self.assertAlmostEqual(result["mean_difference"], (0.1 + 0.9) / 2, places=4)
        self.assertAlmostEqual(result["micro"]["mean_difference"], (9 * 0.1 + 0.9) / 10, places=4)

    def test_macro_interval_resamples_within_subsets(self) -> None:
        # The small subset has a single query, so it cannot vary: the interval of the macro
        # difference is half as wide as the big subset's spread, not the micro interval.
        left = {f"big{i}": record("big", float(i % 2)) for i in range(40)} | {"small": record("small", 1.0)}
        right = {key: record(value["subset"], 0.0) for key, value in left.items()}
        result = paired(left, right, "ndcg@10", samples=500)
        micro_width = result["micro"]["ci95"][1] - result["micro"]["ci95"][0]
        macro_width = result["ci95"][1] - result["ci95"][0]
        self.assertNotAlmostEqual(macro_width, micro_width, places=2)
        self.assertAlmostEqual(result["mean_difference"], (0.5 + 1.0) / 2, places=4)

    def test_no_shared_ids_returns_a_diagnostic_instead_of_failing(self) -> None:
        result = paired({"a1": record("a", 1.0), "a2": record("a", 1.0)}, {"b1": record("a", 1.0)}, "ndcg@10")
        self.assertEqual(result["status"], "no_shared_queries")
        self.assertEqual((result["queries"], result["left_queries"], result["right_queries"]), (0, 2, 1))
        self.assertEqual(result["left_example_ids"], ["a1", "a2"])
        self.assertEqual(result["right_example_ids"], ["b1"])

    def test_a_query_in_different_subsets_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "subset"):
            paired({"q": record("a", 1.0)}, {"q": record("b", 1.0)}, "ndcg@10")


class ReportedDifferenceMatchesTableTests(unittest.TestCase):
    def test_in_run_difference_equals_the_difference_of_the_macro_columns(self) -> None:
        def run_records(boost: float) -> list[dict]:
            rows = []
            for subset, size in (("big", 12), ("small", 2), ("mid", 5)):
                for index in range(size):
                    value = min(1.0, 0.1 * (index % 5) + (boost if subset == "small" else boost / 10))
                    rows.append({"id": f"{subset}{index}", "subset": subset, "split": "test", "gold_size": 1,
                                 "ndcg@10": value, "recall@10": value, "complete@10": value,
                                 "recall@100": value, "complete@100": value,
                                 "sets": {"top-1": dict.fromkeys(("precision", "recall", "f1", "exact", "complete", "size"), 0.0)}})
            return rows

        base, better = run_records(0.0), run_records(0.3)
        table = {name: aggregate(rows, [])["macro_test"]["ndcg@10"] for name, rows in (("base", base), ("llm", better))}
        report = comparisons({"base": base, "llm": better}, "base", [])
        difference = report["ranking_vs_baseline"]["llm"]["ndcg@10"]
        self.assertAlmostEqual(difference["mean_difference"], table["llm"] - table["base"], places=3)
        self.assertEqual(difference["weighting"], "macro")
        self.assertIn("macro", report["definitions"]["ranking_vs_baseline"])


class CommandLineTests(unittest.TestCase):
    def run_main(self, runs: dict[str, dict], extra: list[str] | None = None) -> tuple[dict, int | None]:
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            arguments = []
            for name, payload in runs.items():
                (directory / f"{name}.json").write_text(json.dumps(payload), encoding="utf-8")
                arguments.append(f"{name}={directory / f'{name}.json'}")
            output = directory / "out.json"
            code = None
            with mock.patch.object(sys, "argv", ["compare", *arguments, "--output", str(output), *(extra or [])]):
                with redirect_stdout(StringIO()), redirect_stderr(StringIO()):
                    try:
                        compare_toolret_records.main()
                    except SystemExit as error:
                        code = error.code
            return json.loads(output.read_text(encoding="utf-8")), code

    def test_report_names_the_metric_definitions_and_the_inputs(self) -> None:
        provenance = {"schema": 2, "marmo_core_commit": "a" * 40}
        a = {"_provenance": provenance, "hybrid": {"q1": record("s", 0.5), "q2": record("s", 0.5)}}
        b = {"hybrid": {"q1": record("s", 0.25), "q2": record("s", 0.5)}}
        report, code = self.run_main({"a": a, "b": b})
        self.assertIsNone(code)
        self.assertEqual(set(report["definitions"]), {"macro", "micro"})
        entry = report["comparisons"]["b - a"]["hybrid"]["ndcg@10"]
        self.assertEqual((entry["weighting"], entry["queries"]), ("macro", 2))
        self.assertEqual(report["runs"]["a"]["provenance"], provenance)
        self.assertEqual(len(report["runs"]["a"]["records_sha256"]), 64)
        self.assertIn("a", report["provenance"]["inputs"])

    def test_disjoint_runs_write_the_diagnostic_and_exit_nonzero(self) -> None:
        a = {"hybrid": {"q1": record("s", 0.5)}}
        b = {"hybrid": {"other": record("s", 0.5)}}
        report, code = self.run_main({"a": a, "b": b})
        self.assertEqual(code, 2)
        self.assertEqual(report["comparisons"]["b - a"]["hybrid"]["ndcg@10"]["status"], "no_shared_queries")

    def test_retrievers_missing_from_one_run_are_listed(self) -> None:
        a = {"hybrid": {"q1": record("s", 0.5)}, "lexical": {"q1": record("s", 0.5)}}
        b = {"hybrid": {"q1": record("s", 0.5)}}
        report, _ = self.run_main({"a": a, "b": b})
        self.assertEqual(report["skipped_retrievers"], {"b": ["lexical"]})

    def test_split_option_restricts_both_runs(self) -> None:
        a = {"hybrid": {"d": record("s", 1.0, split="dev"), "t": record("s", 0.5)}}
        b = {"hybrid": {"d": record("s", 0.0, split="dev"), "t": record("s", 0.5)}}
        report, _ = self.run_main({"a": a, "b": b}, ["--split", "test"])
        entry = report["comparisons"]["b - a"]["hybrid"]["ndcg@10"]
        self.assertEqual((entry["queries"], entry["mean_difference"]), (1, 0.0))
        self.assertEqual(report["split"], "test")


if __name__ == "__main__":
    unittest.main()
