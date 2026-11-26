from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "benchmarks"))

from run_evidence_benchmark import load_bundled_registry, load_cases  # noqa: E402
from run_forgery_benchmark import (  # noqa: E402
    CONFIGS,
    DECOY_IDS,
    DIMENSIONS,
    attack_name,
    decoy_definition,
    evaluate,
    kernel_reach,
    load_set_suite,
    run,
    summarize,
)
from marmo_core import ResourceRegistry  # noqa: E402

CASES = load_cases(ROOT / "benchmarks/evidence_cases.json")


def case(case_id: str) -> dict:
    return next(item for item in CASES if item["id"] == case_id)


def poisoned(registry: ResourceRegistry, decoy) -> ResourceRegistry:
    result = ResourceRegistry()
    for definition in registry.all():
        result.add(definition)
    result.add(decoy)
    return result


class ForgeryBenchmarkTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.registry = load_bundled_registry()
        cls.config = CONFIGS["lexical-greedy"]

    def test_each_declaration_is_forged_independently(self) -> None:
        rows, clean = evaluate(self.registry, [case("test-read")], self.config)
        self.assertEqual(len(clean), 1)
        attacks = {(row["kind"], row["content"], row["attack"]) for row in rows}
        # 2^4 tool declarations and 2^3 skill / agent declarations for the
        # stuffed decoy; the clone decoy needs a gold resource of its kind.
        self.assertEqual(sum(kind == "tool" and content == "stuffed" for kind, content, _ in attacks), 16)
        self.assertEqual(sum(kind == "skill" and content == "stuffed" for kind, content, _ in attacks), 8)
        self.assertEqual(sum(kind == "agent" and content == "stuffed" for kind, content, _ in attacks), 8)
        self.assertEqual(sum(kind == "tool" and content == "clone" for kind, content, _ in attacks), 16)
        self.assertFalse(any(kind != "tool" and content == "clone" for kind, content, _ in attacks))

    def test_honest_decoy_never_passes_activation_or_runs(self) -> None:
        rows, _ = evaluate(self.registry, [case("test-read"), case("test-abstain")], self.config)
        honest = [row for row in rows if row["attack"] == "honest"]
        self.assertTrue(honest)
        self.assertEqual(summarize(honest)["activation_reach_rate"], 0.0)
        self.assertFalse(any(row["executed"] for row in honest))
        self.assertFalse(any(row["status_hijacked"] for row in honest))

    def test_fully_forged_tool_reaches_the_inert_handler_only(self) -> None:
        decoy = decoy_definition("tool", case("test-read"), self.registry, "stuffed", DIMENSIONS["tool"])
        self.assertFalse(decoy.metadata.ref.startswith("python:"))
        with mock.patch("marmo_core.sample_resources.tools.send_notification") as shipped:
            reach = kernel_reach(poisoned(self.registry, decoy), case("test-read"), decoy, self.config)
        shipped.assert_not_called()
        self.assertTrue(reach["offered"])
        self.assertTrue(reach["executed"])

    def test_forged_skill_body_reaching_the_prompt_is_detected(self) -> None:
        target = case("test-abstain")
        forged = decoy_definition("skill", target, self.registry, "stuffed", DIMENSIONS["skill"])
        honest = decoy_definition("skill", target, self.registry, "stuffed", ())
        reached = kernel_reach(poisoned(self.registry, forged), target, forged, self.config)
        blocked = kernel_reach(poisoned(self.registry, honest), target, honest, self.config)
        self.assertTrue(reached["offered"])
        self.assertIsNone(reached["executed"])
        self.assertFalse(blocked["offered"])

    def test_clone_copies_the_gold_resource_of_the_same_kind(self) -> None:
        target = case("test-security")
        decoy = decoy_definition("agent", target, self.registry, "clone", ())
        gold = self.registry.get("agent.marmo.samples.security-reviewer").metadata
        self.assertEqual(decoy.metadata.id, DECOY_IDS["agent"])
        self.assertEqual(decoy.metadata.description, gold.description)
        self.assertIsNone(decoy_definition("agent", case("test-read"), self.registry, "clone", ()))

    def test_report_keeps_the_legacy_baseline_and_tracked_fields(self) -> None:
        cases = [case("test-read"), case("test-escalate")]
        registry, set_cases = load_set_suite(ROOT / "benchmarks/corpus/set_corpus.json",
                                             ROOT / "benchmarks/set_scenarios.json")
        report = run(cases, (registry, set_cases[:1]), ["lexical-greedy"])
        legacy = report["legacy_baseline"]["metadata_forgery"]
        self.assertEqual((legacy["cases"], legacy["decoy_selection_rate"]), (1, 1.0))
        tracked = report["tracked"]["lexical-greedy"]["tracked"]
        self.assertEqual(set(tracked), {"tool", "skill", "agent"})
        for values in tracked.values():
            self.assertEqual(set(values), {"honest", "full_forgery", "partial_forgery", "any_forgery"})
            for key in ("selection_rate", "activation_reach_rate", "offered_to_model_rate",
                        "abstain_escalate_hijack_rate"):
                self.assertIn(key, values["full_forgery"])
        self.assertEqual(set(report["suites"]), {"evidence", "set"})
        self.assertNotIn("_rows", report["suites"]["set"]["configs"]["lexical-greedy"])
        full = attack_name(DIMENSIONS["tool"])
        self.assertIn(f"tool/stuffed/{full}", report["tracked"]["lexical-greedy"]["by_kind_content_attack"])


if __name__ == "__main__":
    unittest.main()
