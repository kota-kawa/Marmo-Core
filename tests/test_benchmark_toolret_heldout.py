"""The ToolRet-SAE held-out split is drawn from unused queries, deterministically."""

from __future__ import annotations

import hashlib
import json
import sys
import unittest
from pathlib import Path

BENCHMARKS = Path(__file__).resolve().parents[1] / "benchmarks"
sys.path.insert(0, str(BENCHMARKS))

from toolret import ToolRetQuery, completeness_at_k, group_metrics, ndcg_at_k, recall_at_k, select_heldout  # noqa: E402


def _query(query_id: str, subset: str, text: str | None = None) -> ToolRetQuery:
    return ToolRetQuery(id=query_id, subset=subset, query=text or f"task {query_id}", instruction="", labels=("t",))


class SelectHeldoutTests(unittest.TestCase):
    def setUp(self) -> None:
        self.queries = [_query(f"a{n}", "alpha") for n in range(10)] + [_query(f"b{n}", "beta") for n in range(3)]
        self.used = self.queries[:2]

    def test_used_queries_and_repeated_texts_are_left_out(self) -> None:
        extra = [_query("dup", "alpha", text=self.used[0].query), _query("twin1", "beta", text="same"),
                 _query("twin2", "beta", text="same")]
        chosen = select_heldout(self.queries + extra, self.used, target=100)
        ids = {query.id for query in chosen}
        self.assertFalse(ids & {"a0", "a1", "dup"})
        self.assertEqual(len(ids & {"twin1", "twin2"}), 1)
        self.assertEqual(len(chosen), len({query.query for query in chosen}))

    def test_one_cap_per_subset_lands_closest_to_the_target(self) -> None:
        chosen = select_heldout(self.queries, self.used, target=6)
        per_subset = {subset: sum(query.subset == subset for query in chosen) for subset in ("alpha", "beta")}
        self.assertEqual(per_subset, {"alpha": 3, "beta": 3})

    def test_the_choice_does_not_depend_on_input_order(self) -> None:
        forward = select_heldout(self.queries, self.used, target=5)
        backward = select_heldout(list(reversed(self.queries)), self.used, target=5)
        self.assertEqual([query.id for query in forward], [query.id for query in backward])


class FrozenHeldoutTests(unittest.TestCase):
    def test_the_committed_id_list_matches_its_count_and_digest(self) -> None:
        frozen = json.loads((BENCHMARKS / "toolret_sae_heldout_ids.json").read_text(encoding="utf-8"))
        ids = frozen["ids"]
        self.assertEqual((len(ids), len(set(ids))), (frozen["count"], frozen["count"]))
        self.assertEqual(sum(frozen["per_subset"].values()), frozen["count"])
        self.assertEqual(hashlib.sha256("\n".join(ids).encode("utf-8")).hexdigest(), frozen["sha256"])


class GroupMetricsTests(unittest.TestCase):
    def test_one_member_groups_match_the_standard_metrics(self) -> None:
        ranked, gold = ["x", "a", "y", "b"], {"a", "b", "c"}
        scores = group_metrics(ranked, [{tool} for tool in sorted(gold)], 3)
        self.assertAlmostEqual(scores["ndcg"], ndcg_at_k(ranked, gold, 3))
        self.assertAlmostEqual(scores["recall"], recall_at_k(ranked, gold, 3))
        self.assertEqual(scores["complete"], completeness_at_k(ranked, gold, 3))

    def test_a_substitute_satisfies_its_group_once(self) -> None:
        scores = group_metrics(["sub", "other"], [{"a", "sub"}, {"b", "sub"}], 2)
        self.assertEqual((scores["recall"], scores["complete"]), (0.5, 0.0))
        self.assertLessEqual(scores["ndcg"], 1.0)
        self.assertEqual(group_metrics(["sub"], [{"a", "sub"}], 1), {"ndcg": 1.0, "recall": 1.0, "complete": 1.0})


if __name__ == "__main__":
    unittest.main()
