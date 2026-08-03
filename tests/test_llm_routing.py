"""Offline tests for the LLM-assisted routing layers (HyDE / LLM rerank / LLM set selector)."""

from __future__ import annotations

import json
import unittest

from marmo_core import (
    HydeRetriever,
    LexicalRetriever,
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


class ExtractIdsTests(unittest.TestCase):
    def test_strict_json_array(self) -> None:
        self.assertEqual(_extract_ids('["b", "a"]', ["a", "b"]), ["b", "a"])

    def test_json_embedded_in_prose(self) -> None:
        self.assertEqual(
            _extract_ids('Best matches: ["a"] as requested.', ["a", "b"]), ["a"]
        )

    def test_fallback_to_first_occurrence_order(self) -> None:
        self.assertEqual(_extract_ids("I suggest b then a.", ["a", "b"]), ["b", "a"])

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


if __name__ == "__main__":
    unittest.main()
