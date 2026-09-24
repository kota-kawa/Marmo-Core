from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "benchmarks"))

from run_evidence_benchmark import (  # noqa: E402
    evaluate_case,
    load_bundled_registry,
    load_cases,
    oracle_satisfied,
    run,
    run_kernel_case,
    select,
)
from marmo_core import GreedyConstrainedSetSelector, LexicalRetriever  # noqa: E402


class EvidenceBenchmarkTests(unittest.TestCase):
    def test_rejects_family_leakage_between_dev_and_test(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "cases.json"
            path.write_text(json.dumps({"cases": [
                {"id": "dev", "split": "dev", "family": "same", "task": "A", "gold_set": ["x"]},
                {"id": "test", "split": "test", "family": "same", "task": "B", "gold_set": ["x"]},
            ]}), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "family crosses dev/test"):
                load_cases(path)

    def test_tool_completion_depends_on_real_artifact(self) -> None:
        cases = load_cases(ROOT / "benchmarks/evidence_cases.json")
        case = next(item for item in cases if item["id"] == "test-write")
        registry = load_bundled_registry()
        selection = select(registry, case, LexicalRetriever(), GreedyConstrainedSetSelector(), min_relevance=0.35)
        row = evaluate_case(registry, case, selection, source="pipeline")
        self.assertTrue(row["attempted"])
        self.assertTrue(row["tool_success"])
        self.assertTrue(row["task_completed"])
        self.assertTrue(run_kernel_case(registry, case, min_relevance=0.35)["task_completed"])
        with tempfile.TemporaryDirectory() as temporary:
            self.assertFalse(oracle_satisfied(case["expect"], {"path": "handoff.txt"}, Path(temporary)))

    def test_frozen_test_does_not_add_cache_cases_and_reports_attack_outcomes(self) -> None:
        report = run(load_cases(ROOT / "benchmarks/evidence_cases.json"))
        adaptive = report["adaptive"]
        self.assertGreater(adaptive["dev"]["summary"]["cache_hits"], 0)
        self.assertEqual(adaptive["stored_cases_at_test_start"], adaptive["stored_cases_at_test_end"])
        self.assertEqual(report["baseline"]["test"]["summary"]["cases"], 10)
        self.assertEqual(report["baseline"]["test"]["summary"]["tool_tasks"], 6)
        self.assertEqual(report["kernel"]["test"]["tasks"], 6)
        self.assertEqual(report["baseline"]["test"]["summary"]["abstain_escalate_accuracy"], 1.0)
        self.assertEqual(report["adversarial_test"]["metadata_forgery"]["cases"], 6)
        self.assertEqual(report["adversarial_test"]["keyword_stuffing"]["unsafe_activation_candidates"], 0)
        self.assertEqual(report["adversarial_test"]["keyword_stuffing"]["details"][0]["declared_isolation"], "L3")
        self.assertEqual(report["adversarial_test"]["metadata_forgery"]["details"][0]["declared_isolation"], "L0")


if __name__ == "__main__":
    unittest.main()
