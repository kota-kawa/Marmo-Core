"""ToolRet-SAE scoring: input checks, cache keys, published labels, and actionable escalations."""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

BENCHMARKS = Path(__file__).resolve().parents[1] / "benchmarks"
if not (BENCHMARKS / "run_toolret_sae.py").exists():
    # The Docker image carries only the benchmark modules its own tests import.
    raise unittest.SkipTest("the benchmark runners are not part of this distribution")
sys.path.insert(0, str(BENCHMARKS))

import run_toolret_sae as sae  # noqa: E402
import toolret  # noqa: E402
from marmo_core import SelectionResult  # noqa: E402
from run_toolret_benchmark import split_of  # noqa: E402

TOOLS = [f"t{number:02d}" for number in range(30)]


def _distinct_scope_tools(count: int) -> list[str]:
    """Tool ids whose scopes differ, so a test can tell which permission a tool needs."""

    chosen: dict[str, str] = {}
    for tool in TOOLS:
        chosen.setdefault(sae.scope_of(tool), tool)
    assert len(chosen) >= count
    return list(chosen.values())[:count]


GOLD, SUBSTITUTE, OTHER, SPARE = _distinct_scope_tools(4)


def _query(query_id: str, labels: tuple[str, ...] = (GOLD,)) -> toolret.ToolRetQuery:
    return toolret.ToolRetQuery(id=query_id, subset="alpha", query=f"task {query_id}", instruction="", labels=labels)


def _ids_with_split(split: str, count: int, prefix: str) -> list[str]:
    found: list[str] = []
    number = 0
    while len(found) < count:
        candidate = f"{prefix}{number}"
        number += 1
        if split_of(candidate) == split:
            found.append(candidate)
    return found


def _pool_rows(first: tuple[str, ...] = (GOLD, SUBSTITUTE)) -> list[list]:
    """Every tool ranked, ``first`` on top."""

    order = list(first) + [tool for tool in TOOLS if tool not in first]
    return [[tool, round(1.0 - 0.01 * rank, 6), {"relevance": round(1.0 - 0.01 * rank, 6)}] for rank, tool in enumerate(order)]


def _world(dev: int = 4, test: int = 3, heldout: int = 3, pooled: bool = True) -> sae.Data:
    sample = [_query(query_id) for query_id in _ids_with_split("dev", dev, "d") + _ids_with_split("test", test, "t")]
    held = [_query(f"h{number}") for number in range(heldout)]
    tools = {tool: {"name": tool, "description": f"tool number {tool}"} for tool in TOOLS}
    pools = {query.id: _pool_rows() for query in sample + held} if pooled else {}
    return sae.Data(0, 0, "test-retriever", tools=tools, all_queries=sample, heldout=held, pools=pools)


def _labels_payload(data: sae.Data, **overrides) -> dict:
    payload = {
        "label_model": "sonnet", "wide_pool": sae.WIDE,
        "queries": {query.id: {"split": data.split(query),
                               "labels": {GOLD: {"necessary": True, "substitutes": [SUBSTITUTE]}}}
                    for query in data.queries},
    }
    payload.update(overrides)
    return payload


def _args(labels_input: str | None, **overrides) -> SimpleNamespace:
    values = dict(eval_split="heldout", labels_input=labels_input, label_model="sonnet", agree_model="haiku",
                  method_model="haiku", method=None, reference=None)
    values.update(overrides)
    return SimpleNamespace(**values)


class TemporaryCache(unittest.TestCase):
    def setUp(self) -> None:
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        patcher = mock.patch.object(sae, "CACHE", self.root / "cache")
        patcher.start()
        self.addCleanup(patcher.stop)

    def write_labels(self, payload: dict) -> str:
        path = self.root / "labels.json"
        path.write_text(json.dumps(payload), encoding="utf-8")
        return str(path)


class ScoreFromPublishedLabelsTests(TemporaryCache):
    def test_scores_from_published_labels_and_records_the_inputs(self) -> None:
        data = _world()
        report = sae.stage_score(data, _args(self.write_labels(_labels_payload(data))))
        self.assertEqual(report["metric_version"], 2)
        self.assertEqual(report["inputs"]["labels"]["source"], "published")
        self.assertEqual(report["queries"], {"labelled": 10, "dev": 4, "heldout": 3})
        self.assertEqual(report["valid_variants"]["heldout"]["S"], 3)
        self.assertIn("actionable_escalation", report["methods"]["greedy"]["heldout"])

    def test_missing_dev_pools_fail_and_name_the_commands(self) -> None:
        data = _world()
        for query in data.queries:
            if data.split(query) == "dev":
                del data.pools[query.id]
        with self.assertRaises(SystemExit) as caught:
            sae.stage_score(data, _args(self.write_labels(_labels_payload(data))))
        message = str(caught.exception)
        self.assertIn("4 of 4 labelled dev queries have no stored candidate pool", message)
        self.assertIn("--stage pools --split dev", message)
        self.assertIn("--stage decompose", message)

    def test_a_cache_without_any_pool_is_not_scored_as_zero(self) -> None:
        data = _world(pooled=False)
        with self.assertRaises(SystemExit) as caught:
            sae.stage_score(data, _args(self.write_labels(_labels_payload(data))))
        self.assertIn("no stored candidate pool", str(caught.exception))
        self.assertNotEqual(caught.exception.code, 0)

    def test_labels_cache_path_requires_every_pooled_query_to_be_labelled(self) -> None:
        data = _world()
        with self.assertRaises(SystemExit) as caught:
            sae.stage_score(data, _args(None))
        self.assertIn("no label", str(caught.exception))
        self.assertIn("--stage label --split dev", str(caught.exception))

    def test_a_requested_llm_method_without_replies_fails(self) -> None:
        data = _world()
        with self.assertRaises(SystemExit) as caught:
            sae.stage_score(data, _args(self.write_labels(_labels_payload(data)), method=["llm-set"]))
        self.assertIn("--stage methods", str(caught.exception))

    def test_labels_from_another_model_or_data_are_refused(self) -> None:
        data = _world()
        cases = {
            "model": _labels_payload(data, label_model="haiku"),
            "unknown query": _labels_payload(data, queries={"nope": {"split": "dev", "labels": {}}}),
        }
        wrong_split = _labels_payload(data)
        some = next(iter(wrong_split["queries"].values()))
        some["split"] = "test" if some["split"] != "test" else "dev"
        cases["split"] = wrong_split
        wrong_gold = _labels_payload(data)
        next(iter(wrong_gold["queries"].values()))["labels"] = {"elsewhere": {"necessary": True, "substitutes": []}}
        cases["gold"] = wrong_gold
        for name, payload in cases.items():
            with self.subTest(name), self.assertRaises(SystemExit):
                sae.load_published_labels(Path(self.write_labels(payload)), data, "sonnet")

    def test_candidate_digests_catch_labels_made_on_other_candidates(self) -> None:
        data = _world()
        payload = _labels_payload(data)
        for query in data.queries:
            payload["queries"][query.id]["candidates_sha256"] = sae.candidates_digest(sae.label_candidates(data, query))
        path = Path(self.write_labels(payload))
        self.assertEqual(len(sae.load_published_labels(path, data, "sonnet")), len(data.queries))
        query = data.queries[0]
        data.pools[query.id] = list(reversed(data.pools[query.id]))
        with self.assertRaises(SystemExit) as caught:
            sae.load_published_labels(path, data, "sonnet")
        self.assertIn("candidates (ids or order) differ", str(caught.exception))

    def test_substitutes_outside_the_rebuilt_candidates_are_counted(self) -> None:
        data = _world()
        labels = sae.load_published_labels(Path(self.write_labels(_labels_payload(data))), data, "sonnet")
        self.assertEqual(sae.label_pool_mismatch(data, labels, data.queries), 0)
        query = data.queries[0]
        data.pools[query.id] = [row for row in data.pools[query.id] if row[0] != SUBSTITUTE]
        self.assertEqual(sae.label_pool_mismatch(data, labels, data.queries), 1)


class PoolStageTests(TemporaryCache):
    def test_which_retrievers_replay_decompositions(self) -> None:
        for name in ("llm:hybrid-0.5", "llm!:hybrid-0.5", "llm@1!:lexical", "llm-rrf:hybrid-0.5", "rerank:llm!:hybrid-0.5"):
            self.assertTrue(sae.uses_cached_decompositions(name), name)
        for name in ("lexical", "hybrid-0.5", "clause:hybrid-0.5", "rerank:hybrid-0.5"):
            self.assertFalse(sae.uses_cached_decompositions(name), name)

    def test_pools_are_not_built_without_the_cached_decompositions(self) -> None:
        data = _world(pooled=False)
        data.retriever = "llm:hybrid-0.5"
        with mock.patch.object(sae, "DECOMPOSITION_CACHE", self.root / "missing.json"):
            with self.assertRaises(SystemExit) as caught:
                sae.stage_pools(data, data.queries, SimpleNamespace(embed_model="unused"))
        self.assertIn("--stage decompose", str(caught.exception))
        self.assertEqual(data.pools, {})


class SubstitutesStageTests(TemporaryCache):
    def test_the_matching_is_recorded_and_greedy_stays_the_default(self) -> None:
        data = _world()
        labels = sae.load_published_labels(Path(self.write_labels(_labels_payload(data))), data, "sonnet")
        for matching in ("greedy", "matched"):
            output = self.root / f"{matching}.json"
            sae.stage_substitutes(data, "sonnet", output, matching, labels)
            report = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(report["group_matching"], matching)
            self.assertEqual(report["all"]["gold_or_substitute"]["recall@10"]["macro"], 1.0)
        output = self.root / "default.json"
        sae.stage_substitutes(data, "sonnet", output, labels=labels)
        self.assertEqual(json.loads(output.read_text(encoding="utf-8"))["group_matching"], "greedy")

    def test_labels_without_stored_pools_are_not_scored_as_an_empty_result(self) -> None:
        data = _world(pooled=False)
        labels = sae.load_published_labels(Path(self.write_labels(_labels_payload(data))), data, "sonnet")
        with self.assertRaises(SystemExit):
            sae.stage_substitutes(data, "sonnet", self.root / "out.json", labels=labels)
        self.assertFalse((self.root / "out.json").exists())


class LabelCacheKeyTests(TemporaryCache):
    def test_a_reply_is_found_only_for_the_candidates_it_was_made_on(self) -> None:
        data = _world(dev=1, test=0, heldout=0)
        query = data.queries[0]
        prompt, candidates = sae.label_prompt(data, query)
        reply = json.dumps({"R1": {"necessary": True, "substitutes": ["C1"]}})
        sae.label_path("sonnet").parent.mkdir(parents=True)
        sae.label_path("sonnet").write_text(json.dumps({sae.label_key("sonnet", query, prompt, candidates): reply}),
                                            encoding="utf-8")
        self.assertEqual(sae.parsed_labels(data, "sonnet")[query.id][GOLD]["substitutes"], [candidates[0]])
        # The same cache after the pool is reordered: C1 would now mean another tool.
        data.pools[query.id] = list(reversed(data.pools[query.id]))
        self.assertEqual(sae.parsed_labels(data, "sonnet"), {})
        # A reply stored by query id alone (the old layout) is not trusted either.
        sae.label_path("sonnet").write_text(json.dumps({query.id: reply}), encoding="utf-8")
        data.pools[query.id] = list(reversed(data.pools[query.id]))
        self.assertEqual(sae.parsed_labels(data, "sonnet"), {})

    def test_the_key_depends_on_model_and_candidates(self) -> None:
        data = _world(dev=1, test=0, heldout=0)
        query = data.queries[0]
        prompt, candidates = sae.label_prompt(data, query)
        keys = {sae.label_key("sonnet", query, prompt, candidates),
                sae.label_key("haiku", query, prompt, candidates),
                sae.label_key("sonnet", query, prompt, list(reversed(candidates)))}
        self.assertEqual(len(keys), 3)

    def test_stage_label_labels_again_what_was_cached_without_a_candidate_digest(self) -> None:
        data = _world(dev=1, test=0, heldout=0)
        query = data.queries[0]
        calls: list[str] = []

        class Annotator:
            def complete(self, messages):
                calls.append(messages[-1].content)
                return SimpleNamespace(content=json.dumps({"R1": {"necessary": True, "substitutes": ["C1"]}}))

        sae.label_path("sonnet").parent.mkdir(parents=True)
        sae.label_path("sonnet").write_text(json.dumps({query.id: "{}"}), encoding="utf-8")
        with mock.patch.object(sae, "make_llm", return_value=Annotator()):
            sae.stage_label(data, [query], "sonnet", 1)
            sae.stage_label(data, [query], "sonnet", 1)
        self.assertEqual(len(calls), 1)
        self.assertIn(query.id, sae.parsed_labels(data, "sonnet"))


class ActionableEscalationTests(unittest.TestCase):
    def escalate(self, *scopes: str) -> SelectionResult:
        return SelectionResult((), "blocked", status="escalate", missing_permissions=tuple(scopes))

    def test_naming_the_needed_permission_is_actionable(self) -> None:
        groups = [frozenset({GOLD, SUBSTITUTE})]
        pool = [OTHER, GOLD, SPARE]
        row = sae.escalation_request(self.escalate(sae.scope_of(GOLD)), groups, pool, set())
        self.assertEqual((row["grant_sufficient"], row["actionable"], row["satisfiable"]), (True, True, True))

    def test_an_escalation_naming_nothing_or_the_wrong_scope_is_not(self) -> None:
        groups = [frozenset({GOLD})]
        pool = [GOLD, OTHER]
        for selection in (self.escalate(), self.escalate(sae.scope_of(OTHER))):
            row = sae.escalation_request(selection, groups, pool, set())
            self.assertEqual((row["grant_sufficient"], row["actionable"]), (False, False))

    def test_asking_for_more_than_needed_is_sufficient_but_not_actionable(self) -> None:
        groups = [frozenset({GOLD})]
        row = sae.escalation_request(self.escalate(sae.scope_of(GOLD), sae.scope_of(OTHER)), groups, [GOLD, OTHER], set())
        self.assertEqual((row["grant_sufficient"], row["actionable"]), (True, False))

    def test_a_status_other_than_escalate_names_nothing(self) -> None:
        abstain = SelectionResult((), "no", status="abstain")
        row = sae.escalation_request(abstain, [frozenset({GOLD})], [GOLD], set())
        self.assertEqual((row["requested"], row["actionable"], row["satisfiable"]), (0, False, True))

    def test_a_pool_without_an_answer_cannot_be_satisfied_by_any_grant(self) -> None:
        row = sae.escalation_request(self.escalate(sae.scope_of(GOLD)), [frozenset({GOLD})], [OTHER], set())
        self.assertEqual((row["satisfiable"], row["grant_sufficient"]), (False, False))

    def test_one_substitute_satisfies_every_item_it_stands_in_for(self) -> None:
        first, second = "first", "second"
        groups = [frozenset({first, SUBSTITUTE}), frozenset({second, SUBSTITUTE})]
        self.assertTrue(sae.covers({SUBSTITUTE}, groups))
        row = sae.escalation_request(self.escalate(sae.scope_of(SUBSTITUTE)), groups, [SUBSTITUTE], set())
        self.assertTrue(row["actionable"])

    def test_the_result_does_not_depend_on_the_order_of_the_gold_tools(self) -> None:
        labels = {GOLD: {"necessary": True, "substitutes": [SUBSTITUTE]},
                  OTHER: {"necessary": True, "substitutes": [SUBSTITUTE]}}
        forward = _query("q", (GOLD, OTHER))
        backward = _query("q", (OTHER, GOLD))
        self.assertEqual(set(sae.need_groups(forward, labels)), set(sae.need_groups(backward, labels)))
        for chosen in ({SUBSTITUTE}, {GOLD}, {GOLD, OTHER}):
            self.assertEqual(sae.covers(chosen, sae.need_groups(forward, labels)),
                             sae.covers(chosen, sae.need_groups(backward, labels)))

    def test_outcome_keeps_the_status_metric_and_adds_the_actionable_one(self) -> None:
        query = _query("q")
        labels = {GOLD: {"necessary": True, "substitutes": []}}
        pool = [GOLD, OTHER]
        names_nothing = sae.outcome(query, "E", self.escalate(), labels, pool)
        self.assertEqual((names_nothing["correct"], names_nothing["correct_v2"]), (True, False))
        names_gold = sae.outcome(query, "E", self.escalate(sae.scope_of(GOLD)), labels, pool)
        self.assertEqual((names_gold["correct"], names_gold["correct_v2"]), (True, True))
        selected = sae.outcome(query, "A", SelectionResult((), "no", status="abstain"), labels, pool)
        self.assertEqual((selected["correct"], selected["correct_v2"]), (True, True))

    def test_version_two_adds_keys_and_keeps_every_version_one_key(self) -> None:
        old = json.loads((BENCHMARKS / "results" / "toolret-sae-heldout.json").read_text(encoding="utf-8"))
        old_keys = set(old["methods"]["llm-set"]["heldout"]) - {"oracle_candidates"}
        query = _query("q")
        labels = {GOLD: {"necessary": True, "substitutes": []}}
        rows = []
        for variant in sae.VARIANTS:
            row = sae.outcome(query, variant, self.escalate(sae.scope_of(GOLD)), labels, [GOLD])
            row.update({"id": "q", "subset": "alpha", "variant": variant, "multi": False, "reachable": True,
                        "permitted_reachable": True, "llm_calls": 0})
            rows.append(row)
        summary = sae.summarize(rows)
        self.assertLessEqual(old_keys, set(summary))
        self.assertEqual(summary["actionable_escalation"]["actionable"], 1.0)
        self.assertEqual(summary["macro_correct_v2"], round((0.0 + 1.0 + 0.0) / 3, 4))


class FreshSplitStageTests(TemporaryCache):
    def test_the_frozen_split_leaves_out_prior_ids_and_texts_and_is_not_overwritten(self) -> None:
        data = _world(dev=3, test=3, heldout=2)
        extra = [toolret.ToolRetQuery(id=f"x{number}", subset="alpha", query=f"fresh {number}", instruction="", labels=(GOLD,))
                 for number in range(60)]
        # One more query repeats a sampled query's text under another id.
        twin = toolret.ToolRetQuery(id="twin", subset="alpha", query=data.sample[0].query.upper(), instruction="",
                                    labels=(GOLD,))
        data.all_queries = data.all_queries + extra + [twin]
        output = self.root / "fresh.json"
        sae.stage_fresh_heldout(data, 1000, output)
        payload = json.loads(output.read_text(encoding="utf-8"))
        prior_ids = {query.id for query in data.sample} | {query.id for query in data.queries if query.id in data.heldout_ids}
        test_ids = {query.id for query in data.all_queries if split_of(query.id) == "test"}
        self.assertFalse(set(payload["ids"]) & (prior_ids | test_ids | {"twin"}))
        self.assertEqual(payload["overlap_with_prior"]["same_id"], 0)
        self.assertEqual(payload["overlap_with_prior"]["same_text_other_id"], 0)
        with self.assertRaises(SystemExit):
            sae.stage_fresh_heldout(data, 1000, output)


if __name__ == "__main__":
    unittest.main()
