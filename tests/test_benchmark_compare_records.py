from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "benchmarks"))

from compare_toolret_records import paired  # noqa: E402


class PairedComparisonTests(unittest.TestCase):
    def test_pairs_queries_by_id_and_ignores_unpaired_ones(self) -> None:
        left = {"q1": {"ndcg@10": 0.5}, "q2": {"ndcg@10": 1.0}, "only-left": {"ndcg@10": 1.0}}
        right = {"q1": {"ndcg@10": 0.25}, "q2": {"ndcg@10": 0.5}}
        result = paired(left, right, "ndcg@10", samples=200)
        self.assertEqual(result["queries"], 2)
        self.assertEqual(result["mean_difference"], 0.375)
        low, high = result["ci95"]
        self.assertTrue(0.25 <= low <= 0.375 <= high <= 0.5)

    def test_identical_runs_have_a_zero_interval(self) -> None:
        records = {f"q{i}": {"complete@10": float(i % 2)} for i in range(20)}
        result = paired(records, records, "complete@10", samples=100)
        self.assertEqual((result["mean_difference"], result["ci95"]), (0.0, [0.0, 0.0]))


if __name__ == "__main__":
    unittest.main()
