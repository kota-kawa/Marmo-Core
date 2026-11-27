"""The ToolRet-SAE held-out split is drawn from unused queries, deterministically."""

from __future__ import annotations

import hashlib
import io
import itertools
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

BENCHMARKS = Path(__file__).resolve().parents[1] / "benchmarks"
sys.path.insert(0, str(BENCHMARKS))

import toolret  # noqa: E402
from toolret import (  # noqa: E402
    ToolRetQuery,
    completeness_at_k,
    group_metrics,
    group_metrics_matched,
    ndcg_at_k,
    normalize_text,
    prior_overlap,
    recall_at_k,
    select_fresh_heldout,
    select_heldout,
)


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


class FreshHeldoutTests(unittest.TestCase):
    def setUp(self) -> None:
        self.prior = [_query("p0", "alpha", text="Find  the Weather"), _query("p1", "alpha")]
        self.candidates = [
            _query("p1", "alpha"),
            _query("respaced", "alpha", text="find the weather"),
            _query("fresh1", "alpha"),
            _query("fresh2", "beta"),
        ]

    def test_a_text_seen_before_is_left_out_whatever_its_case_or_spacing(self) -> None:
        chosen = {query.id for query in select_fresh_heldout(self.candidates, self.prior, target=10)}
        self.assertEqual(chosen, {"fresh1", "fresh2"})

    def test_the_original_rule_compares_texts_as_written_and_is_unchanged(self) -> None:
        chosen = {query.id for query in select_heldout(self.candidates, self.prior, target=10)}
        self.assertEqual(chosen, {"respaced", "fresh1", "fresh2"})

    def test_overlap_counts_ids_and_texts_separately(self) -> None:
        counts = prior_overlap(self.candidates, self.prior)
        self.assertEqual(counts, {"queries": 4, "same_id": 1, "same_text_other_id": 1})
        self.assertEqual(normalize_text("  A\tb \n C "), "a b c")


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


class MatchedGroupMetricsTests(unittest.TestCase):
    def test_the_greedy_version_depends_on_the_order_of_the_groups(self) -> None:
        ranked = ["s", "a"]
        first = group_metrics(ranked, [{"a", "s"}, {"s"}], 2)
        second = group_metrics(ranked, [{"s"}, {"a", "s"}], 2)
        self.assertEqual((first["recall"], second["recall"]), (0.5, 1.0))

    def test_the_matched_version_does_not(self) -> None:
        ranked = ["s", "a", "x"]
        groups = [{"a", "s"}, {"s"}, {"x", "q"}]
        results = {tuple(map(tuple, map(sorted, order))): group_metrics_matched(ranked, list(order), 3)
                   for order in itertools.permutations(groups)}
        self.assertEqual(len({tuple(sorted(value.items())) for value in results.values()}), 1)
        self.assertEqual(next(iter(results.values()))["recall"], 1.0)

    def test_a_tool_is_credited_to_one_group_only(self) -> None:
        scores = group_metrics_matched(["sub", "other"], [{"a", "sub"}, {"b", "sub"}], 2)
        self.assertEqual((scores["recall"], scores["complete"]), (0.5, 0.0))
        self.assertLessEqual(scores["ndcg"], 1.0)

    def test_one_member_groups_match_the_standard_metrics(self) -> None:
        ranked, gold = ["x", "a", "y", "b"], {"a", "b", "c"}
        scores = group_metrics_matched(ranked, [{tool} for tool in sorted(gold)], 3)
        self.assertAlmostEqual(scores["ndcg"], ndcg_at_k(ranked, gold, 3))
        self.assertAlmostEqual(scores["recall"], recall_at_k(ranked, gold, 3))
        self.assertEqual(scores["complete"], completeness_at_k(ranked, gold, 3))


class _FakeResponse(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *exc) -> None:
        self.close()


class DownloadTests(unittest.TestCase):
    def setUp(self) -> None:
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.data_dir = Path(self.directory.name) / "toolret"
        self.urls: list[str] = []

    def fake_urlopen(self, request, timeout=None):
        url = request.full_url
        self.urls.append(url)
        if "/api/datasets/" in url:
            repository, revision = url.split("/datasets/mangopy/")[1].split("/revision/")
            return _FakeResponse(json.dumps({"sha": f"sha-of-{revision}"}).encode("utf-8"))
        return _FakeResponse(f"parquet from {url}".encode("utf-8"))

    def download(self, **kwargs):
        with mock.patch.object(toolret.urllib.request, "urlopen", self.fake_urlopen):
            return toolret.download(self.data_dir, **kwargs)

    def test_files_come_from_the_pinned_commits_and_the_snapshot_records_them(self) -> None:
        snapshot = self.download()
        files = [url for url in self.urls if "/resolve/" in url]
        self.assertEqual(len(files), len(toolret.TOOL_CONFIGS) + len(toolret.QUERY_CONFIGS))
        self.assertTrue(all("/resolve/sha-of-" in url and "/resolve/main/" not in url for url in files))
        self.assertEqual(snapshot.revisions, {"ToolRet-Tools": f"sha-of-{toolret.DATASET_REVISIONS['ToolRet-Tools']}",
                                              "ToolRet-Queries": f"sha-of-{toolret.DATASET_REVISIONS['ToolRet-Queries']}"})
        self.assertEqual(len(snapshot.files), len(files))
        record = snapshot.to_record()
        self.assertEqual(len(record["files_sha256"]), 64)
        self.assertEqual(toolret.snapshot(self.data_dir).to_record(), record)

    def test_a_revision_can_be_chosen_per_repository(self) -> None:
        snapshot = self.download(revisions={"ToolRet-Queries": "main"})
        self.assertEqual(snapshot.revisions["ToolRet-Queries"], "sha-of-main")
        self.assertEqual(snapshot.revisions["ToolRet-Tools"], f"sha-of-{toolret.DATASET_REVISIONS['ToolRet-Tools']}")
        with self.assertRaises(ValueError):
            self.download(revisions={"Other": "main"})

    def test_existing_files_are_kept_and_force_fetches_again(self) -> None:
        self.download()
        self.urls.clear()
        self.download()
        self.assertEqual(self.urls, [])
        self.download(force=True)
        self.assertEqual(len([url for url in self.urls if "/resolve/" in url]), 38)

    def test_files_fetched_before_the_manifest_have_no_known_revision(self) -> None:
        path = self.data_dir / "tools" / "code.parquet"
        path.parent.mkdir(parents=True)
        path.write_bytes(b"old")
        snapshot = toolret.snapshot(self.data_dir)
        self.assertEqual(snapshot.revisions, {"ToolRet-Tools": None})
        self.assertEqual(snapshot.files, {"tools/code.parquet": hashlib.sha256(b"old").hexdigest()})


if __name__ == "__main__":
    unittest.main()
