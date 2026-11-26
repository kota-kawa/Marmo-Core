"""The ToolRet-SAE held-out split is drawn from unused queries, deterministically."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "benchmarks"))

from toolret import ToolRetQuery, select_heldout  # noqa: E402


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


if __name__ == "__main__":
    unittest.main()
