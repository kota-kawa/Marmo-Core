"""Offline tests for the LLM-assisted routing layers (HyDE / LLM rerank / LLM set selector)."""

from __future__ import annotations

import json
import unittest

from marmo_core import (
    HydeRetriever,
    LexicalRetriever,
    LLMCatalogRetriever,
    LLMRerankRetriever,
    LLMResponse,
    LLMSetSelector,
    MockLLMProvider,
    ResourceDefinition,
    ResourceRegistry,
    SearchQuery,
    SearchResult,
    SelectionContext,
)
from marmo_core.errors import ProviderHTTPError
from marmo_core.llm_routing import _extract_ids, _parse_set_reply


def _tool(resource_id: str, description: str) -> ResourceDefinition:
    return ResourceDefinition.from_mapping(
        {
            "id": resource_id,
            "kind": "tool",
            "name": resource_id.split(".")[-1],
            "version": "1.0.0",
            "description": description,
            "capabilities": [],
            "input_summary": "input",
            "output_summary": "output",
            "required_permissions": [],
            "cost_estimate": 0.0,
            "latency_class": "fast",
            "side_effect": "none",
            "trust_level": "core",
            "ref": f"tool://{resource_id}",
            "tags": [],
        }
    )


class HydeRetrieverTests(unittest.TestCase):
    def setUp(self) -> None:
        self.registry = ResourceRegistry()
        self.registry.add(_tool("tool.churn.analysis", "Analyze customer churn and retention cohorts."))
        self.registry.add(_tool("tool.invoice.builder", "Build and send invoices to clients."))

    def test_hyde_rewrite_recovers_zero_overlap_paraphrase(self) -> None:
        # The task shares no vocabulary with the target; the scripted rewrite does.
        llm = MockLLMProvider(
            script=[LLMResponse(content="A tool that analyzes customer churn and retention cohorts.")]
        )
        retriever = HydeRetriever(llm, LexicalRetriever())
        results = retriever.search(
            self.registry, SearchQuery(task="people keep leaving our product", top_k=2)
        )
        self.assertEqual(results[0].resource.metadata.id, "tool.churn.analysis")

    def test_hyde_caches_rewrites_per_task(self) -> None:
        llm = MockLLMProvider(script=[LLMResponse(content="churn analysis")])
        retriever = HydeRetriever(llm, LexicalRetriever())
        query = SearchQuery(task="people keep leaving", top_k=1)
        retriever.search(self.registry, query)
        retriever.search(self.registry, query)  # would raise if the script were consulted again
        self.assertEqual(len(llm.requests), 1)

    def test_hyde_falls_back_to_original_task_on_llm_failure(self) -> None:
        class FailingLLM(MockLLMProvider):
            def complete(self, messages, tools=()):
                raise RuntimeError("boom")

        retriever = HydeRetriever(FailingLLM(), LexicalRetriever())
        with self.assertLogs("marmo_core.llm_routing", "WARNING"):
            results = retriever.search(self.registry, SearchQuery(task="build an invoice", top_k=1))
        self.assertEqual(results[0].resource.metadata.id, "tool.invoice.builder")
        self.assertEqual(retriever.failures, 1)


class LLMRerankRetrieverTests(unittest.TestCase):
    def setUp(self) -> None:
        self.registry = ResourceRegistry()
        self.registry.add(_tool("tool.alpha", "Verify report quality and structure."))
        self.registry.add(_tool("tool.beta", "Verify report quality and formatting details."))

    def test_llm_order_wins_and_rest_keep_inner_order(self) -> None:
        llm = MockLLMProvider(script=[LLMResponse(content='["tool.beta"]')])
        retriever = LLMRerankRetriever(llm, LexicalRetriever(), rerank_pool=10)
        results = retriever.search(self.registry, SearchQuery(task="verify report quality", top_k=2))
        self.assertEqual(
            [result.resource.metadata.id for result in results], ["tool.beta", "tool.alpha"]
        )

    def test_inner_order_survives_llm_failure(self) -> None:
        class FailingLLM(MockLLMProvider):
            def complete(self, messages, tools=()):
                raise RuntimeError("boom")

        retriever = LLMRerankRetriever(FailingLLM(), LexicalRetriever())
        with self.assertLogs("marmo_core.llm_routing", "WARNING"):
            results = retriever.search(self.registry, SearchQuery(task="verify report quality", top_k=2))
        self.assertEqual(len(results), 2)
        self.assertEqual(retriever.failures, 1)

    def test_rerank_uses_cache_for_identical_pool(self) -> None:
        llm = MockLLMProvider(script=[LLMResponse(content='["tool.beta"]')])
        retriever = LLMRerankRetriever(llm, LexicalRetriever())
        query = SearchQuery(task="verify report quality", top_k=2)
        retriever.search(self.registry, query)
        retriever.search(self.registry, query)
        self.assertEqual(len(llm.requests), 1)

    def test_description_limit_truncates_and_zero_shows_names_only(self) -> None:
        llm = MockLLMProvider(script=[LLMResponse(content="[]"), LLMResponse(content="[]")])
        query = SearchQuery(task="verify report quality", top_k=2)
        LLMRerankRetriever(llm, LexicalRetriever(), description_limit=6).search(self.registry, query)
        LLMRerankRetriever(llm, LexicalRetriever(), description_limit=0).search(self.registry, query)
        truncated, names_only = (request["messages"][-1]["content"] for request in llm.requests)
        self.assertIn("name=alpha: Verify\n", truncated)
        self.assertNotIn("report", truncated.split("Candidates:")[1])
        self.assertTrue(names_only.endswith("name=beta"))

    def test_non_default_description_limit_does_not_replay_default_cache(self) -> None:
        llm = MockLLMProvider(
            script=[LLMResponse(content='["tool.beta"]'), LLMResponse(content='["tool.alpha"]')]
        )
        cache: dict[str, str] = {}
        query = SearchQuery(task="verify report quality", top_k=2)
        LLMRerankRetriever(llm, LexicalRetriever(), cache=cache).search(self.registry, query)
        results = LLMRerankRetriever(
            llm, LexicalRetriever(), description_limit=80, cache=cache
        ).search(self.registry, query)
        self.assertEqual(len(llm.requests), 2)
        self.assertEqual(results[0].resource.metadata.id, "tool.alpha")


    def test_list_positions_are_ignored_unless_accepted(self) -> None:
        query = SearchQuery(task="verify report quality", top_k=2)
        inner_order = [r.resource.metadata.id for r in LexicalRetriever().search(self.registry, query)]
        for accept, expected in ((False, inner_order), (True, inner_order[::-1])):
            llm = MockLLMProvider(script=[LLMResponse(content="[2]")])
            retriever = LLMRerankRetriever(llm, LexicalRetriever(), accept_positions=accept)
            results = retriever.search(self.registry, query)
            self.assertEqual([r.resource.metadata.id for r in results], expected)


class LLMCatalogRetrieverTests(unittest.TestCase):
    def setUp(self) -> None:
        self.registry = ResourceRegistry()
        self.registry.add(_tool("tool.churn.analysis", "Analyze customer churn and retention cohorts."))
        self.registry.add(_tool("tool.invoice.builder", "Build and send invoices to clients."))
        self.registry.add(_tool("tool.report.checker", "Verify report quality and structure."))
        self.registry.add(_tool("tool.report.writer", "Write a report from structured notes."))

    def _ids(self, results: list[SearchResult]) -> list[str]:
        return [result.resource.metadata.id for result in results]

    def test_llm_sees_resources_that_lexical_retrieval_would_never_surface(self) -> None:
        # No vocabulary overlap: the inner retriever returns nothing for this task.
        task = "people keep leaving our product"
        self.assertEqual(LexicalRetriever().search(self.registry, SearchQuery(task=task)), [])
        llm = MockLLMProvider(script=[LLMResponse(content='["tool.churn.analysis"]')])
        retriever = LLMCatalogRetriever(llm, LexicalRetriever())
        results = retriever.search(self.registry, SearchQuery(task=task, top_k=3))
        self.assertEqual(self._ids(results), ["tool.churn.analysis"])
        prompt = llm.requests[0]["messages"][-1]["content"]
        for resource_id in ("tool.churn.analysis", "tool.invoice.builder", "tool.report.checker", "tool.report.writer"):
            self.assertIn(f"id={resource_id} ", prompt)

    def test_llm_picks_lead_and_inner_ranking_fills_the_rest(self) -> None:
        llm = MockLLMProvider(script=[LLMResponse(content='["tool.invoice.builder", "tool.report.writer"]')])
        retriever = LLMCatalogRetriever(llm, LexicalRetriever())
        results = retriever.search(self.registry, SearchQuery(task="verify report quality", top_k=4))
        self.assertEqual(
            self._ids(results),
            ["tool.invoice.builder", "tool.report.writer", "tool.report.checker"],
        )

    def test_catalog_respects_query_filters(self) -> None:
        self.registry.add(
            ResourceDefinition.from_mapping(
                {**_tool("skill.report.style", "Report style guide.").metadata.to_dict(), "kind": "skill"}
            )
        )
        llm = MockLLMProvider(script=[LLMResponse(content='["skill.report.style"]')])
        retriever = LLMCatalogRetriever(llm, LexicalRetriever())
        results = retriever.search(
            self.registry, SearchQuery(task="verify report quality", kinds=("tool",), top_k=2)
        )
        self.assertNotIn("skill.report.style", llm.requests[0]["messages"][-1]["content"])
        self.assertNotIn("skill.report.style", self._ids(results))
        self.assertEqual(retriever.unknown_ids, 1)
        self.assertEqual(retriever.empty_replies, 1)

    def test_per_kind_limits_cap_the_llm_picks_too(self) -> None:
        llm = MockLLMProvider(
            script=[LLMResponse(content='["tool.invoice.builder", "tool.churn.analysis"]')]
        )
        retriever = LLMCatalogRetriever(llm, LexicalRetriever())
        results = retriever.search(
            self.registry,
            SearchQuery(task="verify report quality", top_k=4, per_kind_limits={"tool": 1}),
        )
        self.assertEqual(self._ids(results), ["tool.invoice.builder"])

    def test_permission_filter_keeps_ungranted_resources_out_of_the_prompt(self) -> None:
        self.registry.add(
            ResourceDefinition.from_mapping(
                {
                    **_tool("tool.report.publisher", "Publish the report externally.").metadata.to_dict(),
                    "required_permissions": ["net.write"],
                }
            )
        )
        llm = MockLLMProvider(script=[LLMResponse(content='["tool.report.publisher"]')])
        retriever = LLMCatalogRetriever(llm, LexicalRetriever())
        results = retriever.search(
            self.registry,
            SearchQuery(task="verify report quality", require_permissions=True, top_k=5),
        )
        self.assertNotIn("tool.report.publisher", llm.requests[0]["messages"][-1]["content"])
        self.assertNotIn("tool.report.publisher", self._ids(results))

    def test_shards_get_one_call_each_and_a_final_call_ranks_their_picks(self) -> None:
        llm = MockLLMProvider(
            script=[
                LLMResponse(content='["tool.invoice.builder"]'),
                LLMResponse(content='["tool.report.writer"]'),
                LLMResponse(content='["tool.report.writer", "tool.invoice.builder"]'),
            ]
        )
        retriever = LLMCatalogRetriever(llm, LexicalRetriever(), shard_size=2)
        results = retriever.search(self.registry, SearchQuery(task="draft the quarterly summary", top_k=2))
        self.assertEqual(self._ids(results), ["tool.report.writer", "tool.invoice.builder"])
        prompts = [request["messages"][-1]["content"] for request in llm.requests]
        self.assertEqual(len(prompts), 3)
        self.assertIn("tool.churn.analysis", prompts[0])
        self.assertNotIn("tool.report.writer", prompts[0])
        self.assertNotIn("tool.churn.analysis", prompts[2])

    def test_reply_may_name_candidates_by_list_position(self) -> None:
        # The catalog is listed in id order: 2 = invoice.builder, 4 = report.writer.
        llm = MockLLMProvider(script=[LLMResponse(content='[4, "2", 4, 9, true]')])
        retriever = LLMCatalogRetriever(llm, LexicalRetriever())
        results = retriever.search(self.registry, SearchQuery(task="draft the quarterly summary", top_k=4))
        self.assertEqual(self._ids(results), ["tool.report.writer", "tool.invoice.builder"])
        self.assertEqual(retriever.unknown_ids, 2)
        self.assertEqual(retriever.empty_replies, 0)

    def test_select_limit_caps_the_llm_picks(self) -> None:
        llm = MockLLMProvider(
            script=[LLMResponse(content='["tool.invoice.builder", "tool.churn.analysis"]')]
        )
        retriever = LLMCatalogRetriever(llm, LexicalRetriever(), select_limit=1)
        results = retriever.search(self.registry, SearchQuery(task="draft the quarterly summary", top_k=4))
        self.assertEqual(self._ids(results), ["tool.invoice.builder"])

    def test_llm_failure_degrades_to_the_inner_ranking(self) -> None:
        retriever = LLMCatalogRetriever(_FailingLLM(), LexicalRetriever())
        with self.assertLogs("marmo_core.llm_routing", "WARNING") as logs:
            results = retriever.search(self.registry, SearchQuery(task="verify report quality", top_k=1))
        self.assertEqual(self._ids(results), ["tool.report.checker"])
        self.assertEqual(retriever.failures, 1)
        self.assertEqual(retriever.empty_replies, 1)
        self.assertIn("LLMCatalogRetriever", logs.output[0])

    def test_identical_catalog_and_task_hit_the_cache(self) -> None:
        llm = MockLLMProvider(script=[LLMResponse(content='["tool.report.writer"]')])
        retriever = LLMCatalogRetriever(llm, LexicalRetriever())
        query = SearchQuery(task="verify report quality", top_k=2)
        retriever.search(self.registry, query)
        retriever.search(self.registry, query)
        self.assertEqual(len(llm.requests), 1)

    def test_shard_size_below_two_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            LLMCatalogRetriever(MockLLMProvider(), LexicalRetriever(), shard_size=1)


class ExtractIdsTests(unittest.TestCase):
    def test_strict_json_array(self) -> None:
        self.assertEqual(_extract_ids('["b", "a"]', ["a", "b"]), ["b", "a"])

    def test_json_embedded_in_prose(self) -> None:
        self.assertEqual(
            _extract_ids('Best matches: ["a"] as requested.', ["a", "b"]), ["a"]
        )

    def test_fallback_to_first_occurrence_order(self) -> None:
        self.assertEqual(_extract_ids("I suggest b then a.", ["a", "b"]), ["b", "a"])

    def test_positions_resolve_only_when_accepted_and_ids_win(self) -> None:
        self.assertEqual(_extract_ids("[2, 1]", ["a", "b"]), [])
        self.assertEqual(_extract_ids("[2, 1]", ["a", "b"], accept_positions=True), ["b", "a"])
        self.assertEqual(_extract_ids('["2", 0, 3]', ["a", "2"], accept_positions=True), ["2"])

    def test_oversized_and_non_ascii_numbers_are_not_positions(self) -> None:
        reply = json.dumps(["9" * 5000, "\u0662", " 1 "])
        self.assertEqual(_extract_ids(reply, ["a", "b"], accept_positions=True), ["a"])

    def test_ids_are_matched_without_stripping_whitespace(self) -> None:
        self.assertEqual(_extract_ids('["x", " a"]', ["a", "x"]), ["x"])

    def test_invalid_ids_are_dropped(self) -> None:
        self.assertEqual(_extract_ids('["c", "a"]', ["a", "b"]), ["a"])


def _candidate(
    resource_id: str,
    score: float = 0.8,
    *,
    kind: str = "tool",
    dependencies: list[str] | None = None,
    conflicts_with: list[str] | None = None,
    required_permissions: list[str] | None = None,
) -> SearchResult:
    definition = ResourceDefinition.from_mapping(
        {
            "id": resource_id,
            "kind": kind,
            "name": resource_id.split(".")[-1],
            "version": "1.0.0",
            "description": f"resource {resource_id}",
            "capabilities": [],
            "input_summary": "input",
            "output_summary": "output",
            "required_permissions": required_permissions or [],
            "cost_estimate": 1.0,
            "latency_class": "fast",
            "side_effect": "none",
            "trust_level": "core",
            "ref": f"{kind}://{resource_id}",
            "tags": [],
            "dependencies": dependencies or [],
            "conflicts_with": conflicts_with or [],
        }
    )
    return SearchResult(definition, score, (), {"relevance": score})


def _set_reply(status: str, ids: list[str], reason: str = "because") -> LLMResponse:
    return LLMResponse(content=json.dumps({"status": status, "ids": ids, "reason": reason}))


class LLMSetSelectorTests(unittest.TestCase):
    def test_selected_ids_become_the_set(self) -> None:
        llm = MockLLMProvider(script=[_set_reply("selected", ["tool.a", "skill.a"])])
        selector = LLMSetSelector(llm)
        selection = selector.select(
            [_candidate("tool.a", 0.9, dependencies=["skill.a"]), _candidate("skill.a", 0.5, kind="skill"), _candidate("tool.b", 0.4)],
            context=SelectionContext(task="do the thing"),
        )
        self.assertEqual(selection.status, "selected")
        self.assertEqual(
            {r.resource.metadata.id for r in selection.results}, {"tool.a", "skill.a"}
        )

    def test_ids_outside_the_pool_are_dropped_not_repaired(self) -> None:
        llm = MockLLMProvider(script=[_set_reply("selected", ["tool.a", "tool.ghost"])])
        selection = LLMSetSelector(llm).select(
            [_candidate("tool.a")], context=SelectionContext(task="t")
        )
        self.assertEqual([r.resource.metadata.id for r in selection.results], ["tool.a"])

    def test_abstain_and_escalate_pass_through(self) -> None:
        for status in ("abstain", "escalate"):
            llm = MockLLMProvider(script=[_set_reply(status, [], "needs review")])
            selection = LLMSetSelector(llm).select(
                [_candidate("tool.a")], context=SelectionContext(task="t")
            )
            self.assertEqual(selection.status, status)
            self.assertIn("needs review", selection.reason)

    def test_llm_failure_abstains(self) -> None:
        class FailingLLM(MockLLMProvider):
            def complete(self, messages, tools=()):
                raise RuntimeError("api down")

        selector = LLMSetSelector(FailingLLM())
        with self.assertLogs("marmo_core.llm_routing", "WARNING"):
            selection = selector.select([_candidate("tool.a")], context=SelectionContext(task="t"))
        self.assertEqual(selection.status, "abstain")
        self.assertEqual(selector.failures, 1)

    def test_selected_with_no_valid_ids_abstains(self) -> None:
        llm = MockLLMProvider(script=[_set_reply("selected", ["tool.ghost"])])
        selection = LLMSetSelector(llm).select(
            [_candidate("tool.a")], context=SelectionContext(task="t")
        )
        self.assertEqual(selection.status, "abstain")

    def test_identical_pool_and_context_hits_cache(self) -> None:
        llm = MockLLMProvider(script=[_set_reply("selected", ["tool.a"])])
        selector = LLMSetSelector(llm)
        context = SelectionContext(task="t")
        pool = [_candidate("tool.a")]
        selector.select(pool, context=context)
        selector.select(pool, context=context)
        self.assertEqual(len(llm.requests), 1)

    def test_prompt_includes_constraints_and_metadata(self) -> None:
        llm = MockLLMProvider(script=[_set_reply("selected", ["tool.a"])])
        selector = LLMSetSelector(llm)
        selector.select(
            [
                _candidate(
                    "tool.a",
                    dependencies=["skill.a"],
                    conflicts_with=["tool.b"],
                    required_permissions=["net.read"],
                ),
                _candidate("skill.a", kind="skill"),
            ],
            context=SelectionContext(
                task="summarize the report",
                granted_permissions=("net.read",),
                per_kind_limits={"tool": 1},
                budget_cost=5.0,
            ),
        )
        prompt = llm.requests[0]["messages"][1]["content"]
        self.assertIn("summarize the report", prompt)
        self.assertIn("net.read", prompt)
        self.assertIn("tool<=1", prompt)
        self.assertIn("requires=[skill.a]", prompt)
        self.assertIn("conflicts=[tool.b]", prompt)


class ParseSetReplyTests(unittest.TestCase):
    def test_json_object(self) -> None:
        self.assertEqual(
            _parse_set_reply('{"status": "selected", "ids": ["a"], "reason": "r"}', ["a"]),
            ("selected", ["a"], "r"),
        )

    def test_json_in_code_fence(self) -> None:
        text = '```json\n{"status": "abstain", "ids": [], "reason": "none fit"}\n```'
        self.assertEqual(_parse_set_reply(text, ["a"]), ("abstain", [], "none fit"))

    def test_unknown_status_defaults_to_selected(self) -> None:
        status, _, _ = _parse_set_reply('{"status": "maybe", "ids": ["a"]}', ["a"])
        self.assertEqual(status, "selected")

    def test_non_json_falls_back_to_id_extraction(self) -> None:
        self.assertEqual(
            _parse_set_reply("use b then a", ["a", "b"]),
            ("selected", ["b", "a"], "ids recovered from a non-JSON reply"),
        )

    def test_garbage_returns_none(self) -> None:
        self.assertIsNone(_parse_set_reply("no ids here", ["a", "b"]))


class _FailingLLM(MockLLMProvider):
    """An LLM that is down, the way a misconfigured real provider is."""

    def complete(self, messages, tools=()):
        raise ProviderHTTPError(
            message="HTTP 400 from https://api.groq.com/openai/v1/chat/completions: unsupported value",
            status=400,
            body="{}",
            url="https://api.groq.com/openai/v1/chat/completions",
        )


class FailureObservabilityTests(unittest.TestCase):
    """Degradation stays graceful, but must never be silent."""

    def setUp(self) -> None:
        self.registry = ResourceRegistry()
        self.registry.add(_tool("tool.alpha", "Verify report quality and structure."))
        self.registry.add(_tool("tool.beta", "Verify report quality and formatting details."))

    def test_hyde_warns_and_records_the_exception(self) -> None:
        retriever = HydeRetriever(_FailingLLM(), LexicalRetriever())
        with self.assertLogs("marmo_core.llm_routing", level="WARNING") as logs:
            retriever.search(self.registry, SearchQuery(task="verify report quality", top_k=1))
        self.assertEqual(len(logs.output), 1)
        self.assertIn("HydeRetriever", logs.output[0])
        self.assertIn("ProviderHTTPError", logs.output[0])
        self.assertIn("unsupported value", logs.output[0])
        self.assertEqual(retriever.failures, 1)
        self.assertIsInstance(retriever.last_failure, ProviderHTTPError)

    def test_rerank_warns_and_records_the_exception(self) -> None:
        retriever = LLMRerankRetriever(_FailingLLM(), LexicalRetriever())
        with self.assertLogs("marmo_core.llm_routing", level="WARNING") as logs:
            results = retriever.search(self.registry, SearchQuery(task="verify report quality", top_k=2))
        self.assertEqual(len(results), 2)  # still degrades to the inner ranking
        self.assertIn("LLMRerankRetriever", logs.output[0])
        self.assertIsInstance(retriever.last_failure, ProviderHTTPError)

    def test_set_selector_warns_and_records_the_exception(self) -> None:
        selector = LLMSetSelector(_FailingLLM())
        with self.assertLogs("marmo_core.llm_routing", level="WARNING") as logs:
            selection = selector.select([_candidate("tool.a")], context=SelectionContext(task="t"))
        self.assertEqual(selection.status, "abstain")
        self.assertIn("LLMSetSelector", logs.output[0])
        self.assertIsInstance(selector.last_failure, ProviderHTTPError)

    def test_only_the_first_failure_warns(self) -> None:
        retriever = HydeRetriever(_FailingLLM(), LexicalRetriever())
        with self.assertLogs("marmo_core.llm_routing", level="DEBUG") as logs:
            for task in ("verify report quality", "check formatting", "structure the report"):
                retriever.search(self.registry, SearchQuery(task=task, top_k=1))
        levels = [record.levelname for record in logs.records]
        self.assertEqual(levels, ["WARNING", "DEBUG", "DEBUG"])
        self.assertEqual(retriever.failures, 3)

    def test_a_healthy_run_logs_nothing(self) -> None:
        llm = MockLLMProvider(script=[LLMResponse(content="report quality checks")])
        retriever = HydeRetriever(llm, LexicalRetriever())
        with self.assertNoLogs("marmo_core.llm_routing", level="DEBUG"):
            retriever.search(self.registry, SearchQuery(task="verify report quality", top_k=1))
        self.assertEqual(retriever.failures, 0)
        self.assertIsNone(retriever.last_failure)


if __name__ == "__main__":
    unittest.main()
