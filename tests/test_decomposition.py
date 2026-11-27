"""Query decomposition, multi-intent retrieval, and coverage-based set selection."""

from __future__ import annotations

import unittest

from marmo_core import (
    ClauseQueryDecomposer,
    CoverageSetSelector,
    DecomposedRetriever,
    LexicalRetriever,
    LLMQueryDecomposer,
    LLMResponse,
    MockLLMProvider,
    ResourceDefinition,
    ResourceRegistry,
    SearchQuery,
    SearchResult,
    SelectionContext,
)
from marmo_core.decomposition import QueryDecomposer, parse_subtasks


def _resource(resource_id: str, description: str, kind: str = "tool", **overrides) -> ResourceDefinition:
    payload = {
        "id": resource_id,
        "kind": kind,
        "name": resource_id,
        "version": "1.0.0",
        "description": description,
        "capabilities": [],
        "input_summary": "in",
        "output_summary": "out",
        "required_permissions": [],
        "cost_estimate": 0.0,
        "latency_class": "fast",
        "side_effect": "read",
        "trust_level": "verified",
        "ref": f"{kind}://{resource_id}",
        "tags": [],
    }
    payload.update(overrides)
    return ResourceDefinition.from_mapping(payload)


def _result(resource_id: str, relevance: float, facets: tuple[float, ...] = (), **overrides) -> SearchResult:
    components = {"relevance": relevance}
    components.update({f"facet.{index}": value for index, value in enumerate(facets)})
    return SearchResult(_resource(resource_id, "x", **overrides), relevance, (), components)


class _Replying(MockLLMProvider):
    def __init__(self, reply: str | Exception) -> None:
        super().__init__()
        self.reply = reply
        self.calls = 0

    def complete(self, messages, tools=()):
        self.calls += 1
        if isinstance(self.reply, Exception):
            raise self.reply
        return LLMResponse(content=self.reply)


class ClauseQueryDecomposerTests(unittest.TestCase):
    def test_splits_sentences_lists_and_connectives(self) -> None:
        decomposer = ClauseQueryDecomposer()
        self.assertEqual(
            decomposer.decompose("Browse my emails for recent leads. Could you also check the weather in Paris?"),
            ["Browse my emails for recent leads", "check the weather in Paris"],
        )
        self.assertEqual(
            decomposer.decompose("Tasks: 1. Crawl popular blog posts 2. Extract the main topics 3. Draw a trend chart"),
            ["Crawl popular blog posts", "Extract the main topics", "Draw a trend chart"],
        )
        self.assertEqual(
            decomposer.decompose("summarize the repository and then post the summary to slack"),
            ["summarize the repository", "post the summary to slack"],
        )

    def test_plain_and_splits_only_between_full_clauses(self) -> None:
        decomposer = ClauseQueryDecomposer()
        self.assertEqual(decomposer.decompose("add salt and pepper to the soup"), [])
        self.assertEqual(
            decomposer.decompose("book a flight to Paris tomorrow and reserve a hotel near the venue"),
            ["book a flight to Paris tomorrow", "reserve a hotel near the venue"],
        )
        self.assertEqual(
            ClauseQueryDecomposer(split_and=False).decompose(
                "book a flight to Paris tomorrow and reserve a hotel near the venue"
            ),
            [],
        )

    def test_request_framing_is_not_a_sub_task(self) -> None:
        self.assertEqual(ClauseQueryDecomposer().decompose("Could you please help me? Translate this letter to French."), [])

    def test_japanese_connectives(self) -> None:
        self.assertEqual(
            ClauseQueryDecomposer().decompose("リポジトリを要約してからSlackに投稿して"),
            ["リポジトリを要約して", "Slackに投稿して"],
        )

    def test_single_need_and_duplicates_return_nothing(self) -> None:
        decomposer = ClauseQueryDecomposer()
        self.assertEqual(decomposer.decompose("What is the weather in Tokyo tomorrow?"), [])
        self.assertEqual(decomposer.decompose("Check the weather. Check the weather."), [])

    def test_max_subtasks_caps_the_list(self) -> None:
        task = ". ".join(f"Fetch report number {index} today" for index in range(10))
        self.assertEqual(len(ClauseQueryDecomposer(max_subtasks=3).decompose(task)), 3)


class LLMQueryDecomposerTests(unittest.TestCase):
    def test_parses_json_array_and_caches_by_task(self) -> None:
        llm = _Replying('```json\n["look up the show id", "get the cast of the episode"]\n```')
        decomposer = LLMQueryDecomposer(llm)
        self.assertEqual(decomposer.decompose("who acts in it"), ["look up the show id", "get the cast of the episode"])
        decomposer.decompose("who acts in it")
        self.assertEqual(llm.calls, 1)
        self.assertEqual(decomposer.failures, 0)

    def test_single_step_reply_means_no_decomposition(self) -> None:
        self.assertEqual(LLMQueryDecomposer(_Replying('["translate the letter"]')).decompose("translate it"), [])

    def test_failures_degrade_to_no_decomposition_and_are_recorded(self) -> None:
        for reply in (RuntimeError("provider down"), "Sure! Step one is to look up the id."):
            with self.subTest(reply=reply):
                decomposer = LLMQueryDecomposer(_Replying(reply))
                with self.assertLogs("marmo_core.llm_routing", level="WARNING"):
                    self.assertEqual(decomposer.decompose("do two things"), [])
                self.assertEqual(decomposer.failures, 1)
                self.assertIsNotNone(decomposer.last_failure)

    def test_unparseable_replies_are_not_cached(self) -> None:
        llm = _Replying("Sure! Step one is to look up the id.")
        cache: dict[str, str] = {}
        decomposer = LLMQueryDecomposer(llm, cache=cache)
        with self.assertLogs("marmo_core.llm_routing", level="WARNING"):
            decomposer.decompose("do two things")
        llm.reply = '["look up the id", "use the id"]'
        self.assertEqual(decomposer.decompose("do two things"), ["look up the id", "use the id"])
        self.assertEqual((llm.calls, list(cache)), (2, ["do two things"]))

    def test_parse_subtasks_rejects_non_string_arrays(self) -> None:
        self.assertIsNone(parse_subtasks('[1, 2]'))
        self.assertIsNone(parse_subtasks("no array here"))
        self.assertEqual(parse_subtasks('Here: ["a", " ", "b"]'), ["a", "b"])


class _Fixed(QueryDecomposer):
    def __init__(self, subtasks: list[str]) -> None:
        self.subtasks = subtasks

    def decompose(self, task: str) -> list[str]:
        return list(self.subtasks)


class _Table(LexicalRetriever):
    """A retriever whose relevance per task is fixed by a table."""

    def __init__(self, table: dict[str, dict[str, float]]) -> None:
        super().__init__()
        self.table = table
        self.tasks: list[str] = []

    def search(self, registry, query):
        self.tasks.append(query.task)
        results = []
        for resource_id, relevance in self.table.get(query.task, {}).items():
            definition = registry.get(resource_id)
            results.append(SearchResult(definition, 0.45 * relevance + 0.3, (), {"relevance": relevance}))
        results.sort(key=lambda r: -r.score)
        return results[: query.top_k]


class DecomposedRetrieverTests(unittest.TestCase):
    GOAL = "book a flight and reserve a hotel"

    def _registry(self) -> ResourceRegistry:
        registry = ResourceRegistry()
        for resource_id in ("tool.flights", "tool.flights-2", "tool.flights-3", "tool.hotel", "tool.noise"):
            registry.add(_resource(resource_id, "x"))
        return registry

    def _table(self) -> dict[str, dict[str, float]]:
        return {
            self.GOAL: {"tool.flights": 0.8, "tool.flights-2": 0.75, "tool.flights-3": 0.7, "tool.hotel": 0.6, "tool.noise": 0.65},
            "book a flight": {"tool.flights": 0.95, "tool.flights-2": 0.9, "tool.flights-3": 0.85},
            "reserve a hotel": {"tool.hotel": 1.0},
        }

    def test_results_of_a_failed_and_a_successful_decomposition_stay_comparable_for_coverage(self) -> None:
        """The first search gets no sub-tasks (the decomposer failed), a later top-up search does."""

        class FailsOnce(QueryDecomposer):
            def __init__(self) -> None:
                self.calls = 0

            def decompose(self, task: str) -> list[str]:
                self.calls += 1
                return [] if self.calls == 1 else ["book a flight", "reserve a hotel"]

        registry = self._registry()
        retriever = DecomposedRetriever(_Table(self._table()), FailsOnce())
        primary = retriever.search(registry, SearchQuery(task=self.GOAL, top_k=5))
        top_up = retriever.search(registry, SearchQuery(task=self.GOAL, top_k=5, kinds=("tool",)))
        self.assertFalse(any(key.startswith("facet.") for result in primary for key in result.components))
        self.assertTrue(all("facet.0" in result.components for result in top_up))

        flights = next(result for result in primary if result.resource.metadata.id == "tool.flights")
        hotel = next(result for result in top_up if result.resource.metadata.id == "tool.hotel")
        selection = CoverageSetSelector().select([flights, hotel], context=SelectionContext())

        self.assertEqual(
            sorted(result.resource.metadata.id for result in selection.results), ["tool.flights", "tool.hotel"]
        )

    def test_without_sub_tasks_it_is_the_inner_search(self) -> None:
        registry = self._registry()
        inner = _Table(self._table())
        query = SearchQuery(task=self.GOAL, top_k=3)
        expected = [(r.resource.identity, r.score) for r in inner.search(registry, query)]
        actual = DecomposedRetriever(inner, _Fixed([])).search(registry, query)
        self.assertEqual([(r.resource.identity, r.score) for r in actual], expected)

    def test_blend_moves_a_sub_task_match_past_resources_that_serve_none(self) -> None:
        registry = self._registry()
        query = SearchQuery(task=self.GOAL, top_k=4)
        goal_only = [r.resource.metadata.id for r in _Table(self._table()).search(registry, query)]
        self.assertEqual(goal_only, ["tool.flights", "tool.flights-2", "tool.flights-3", "tool.noise"])

        inner = _Table(self._table())
        retriever = DecomposedRetriever(
            inner, _Fixed(["book a flight", "reserve a hotel"]), discount_unknown_terms=False
        )
        results = retriever.search(registry, query)
        self.assertEqual([r.resource.metadata.id for r in results][:2], ["tool.flights", "tool.flights-2"])
        self.assertIn("tool.hotel", [r.resource.metadata.id for r in results])
        self.assertNotIn("tool.noise", [r.resource.metadata.id for r in results])
        self.assertEqual(inner.tasks, [self.GOAL, "book a flight", "reserve a hotel"])
        hotel = next(r for r in results if r.resource.metadata.id == "tool.hotel")
        self.assertEqual((hotel.components["facet.0"], hotel.components["facet.1"], hotel.components["facet.2"]), (0.6, 0.0, 1.0))
        self.assertEqual(hotel.components["relevance"], 1.0)
        self.assertAlmostEqual(hotel.components["facet_blend"], (0.6 + 0.25 * 1.0) / 1.25)
        self.assertEqual(retriever.last_subtasks, ["book a flight", "reserve a hotel"])

    def test_goal_terms_the_catalog_never_uses_discount_the_goal(self) -> None:
        registry = ResourceRegistry()
        registry.add(_resource("tool.hotel", "reserve a hotel room"))
        registry.add(_resource("tool.noise", "unrelated words"))
        goal = "ホテルの部屋を予約して"  # no term of it occurs in the English catalog
        table = {goal: {"tool.noise": 0.9, "tool.hotel": 0.1}, "reserve a hotel room": {"tool.hotel": 1.0}}
        retriever = DecomposedRetriever(_Table(table), _Fixed(["reserve a hotel room"]))
        results = retriever.search(registry, SearchQuery(task=goal, top_k=2))
        self.assertEqual(retriever.last_goal_weight, 0.0)
        self.assertEqual(results[0].resource.metadata.id, "tool.hotel")
        undiscounted = DecomposedRetriever(_Table(table), _Fixed(["reserve a hotel room"]), discount_unknown_terms=False)
        self.assertEqual(undiscounted.search(registry, SearchQuery(task=goal, top_k=2))[0].resource.metadata.id, "tool.noise")
        english = DecomposedRetriever(_Table({"reserve a hotel room": {"tool.hotel": 1.0}}), _Fixed(["reserve a hotel room"]))
        english.search(registry, SearchQuery(task="reserve a hotel room", top_k=2))
        self.assertEqual(english.last_goal_weight, 1.0)

    def test_the_share_comes_from_the_inner_lexical_index(self) -> None:
        registry = self._registry()
        inner = LexicalRetriever()
        retriever = DecomposedRetriever(inner, _Fixed(["book a flight", "reserve a hotel"]))
        retriever.search(registry, SearchQuery(task="x flights near Lisbon", top_k=3))
        self.assertIn(registry, inner._index_cache)
        self.assertNotIn(registry, retriever._limits._index_cache)
        self.assertAlmostEqual(retriever.last_goal_weight, 1 / 4)  # x of x, flights, near, lisbon
        retriever.decomposer = _Fixed([])
        retriever.search(registry, SearchQuery(task="flights", top_k=3))
        self.assertEqual(retriever.last_goal_weight, 1.0)

    def test_no_sub_task_weight_means_no_discount(self) -> None:
        registry = self._registry()
        goal = "予約して"
        table = {goal: {"tool.flights": 0.9}, "book a flight": {"tool.flights": 1.0}}
        retriever = DecomposedRetriever(_Table(table), _Fixed(["book a flight"]), facet_weight=0.0)
        results = retriever.search(registry, SearchQuery(task=goal, top_k=1))
        self.assertEqual(retriever.last_goal_weight, 1.0)
        self.assertAlmostEqual(results[0].components["facet_blend"], 0.9)

    def test_fused_ties_go_against_untrusted_resources(self) -> None:
        registry = ResourceRegistry()
        registry.add(_resource("tool.a", "x", trust_level="untrusted"))
        registry.add(_resource("tool.b", "x"))
        table = {"goal": {"tool.a": 0.5, "tool.b": 0.5}, "sub": {"tool.a": 0.5, "tool.b": 0.5}}
        retriever = DecomposedRetriever(_Table(table), _Fixed(["sub"]), discount_unknown_terms=False)
        results = retriever.search(registry, SearchQuery(task="goal", top_k=2))
        self.assertEqual([r.resource.metadata.id for r in results], ["tool.b", "tool.a"])

    def test_rrf_fusion_and_settings(self) -> None:
        registry = self._registry()
        retriever = DecomposedRetriever(_Table(self._table()), _Fixed(["book a flight", "reserve a hotel"]), fusion="rrf")
        results = retriever.search(registry, SearchQuery(task=self.GOAL, top_k=5))
        self.assertEqual(results[0].resource.metadata.id, "tool.flights")
        self.assertIn("rrf", results[0].components)
        for kwargs in ({"depth": 0}, {"goal_weight": -1.0}, {"facet_weight": -0.1}, {"fusion": "max"}, {"rrf_k": 0}):
            with self.subTest(kwargs=kwargs), self.assertRaises(ValueError):
                DecomposedRetriever(LexicalRetriever(), _Fixed([]), **kwargs)


class CoverageSetSelectorTests(unittest.TestCase):
    def test_covers_each_facet_once_and_skips_redundant_members(self) -> None:
        results = [
            _result("tool.flights", 0.9, (0.9, 0.9, 0.1)),
            _result("tool.flights-2", 0.85, (0.85, 0.88, 0.1)),
            _result("tool.hotel", 0.6, (0.5, 0.1, 0.8)),
            _result("tool.noise", 0.3, (0.2, 0.1, 0.3)),
        ]
        selection = CoverageSetSelector(min_gain=0.1).select(results, context=SelectionContext())
        self.assertEqual(selection.status, "selected")
        self.assertEqual([r.resource.metadata.id for r in selection.results], ["tool.flights", "tool.hotel"])

    def test_a_result_ranked_without_decomposition_counts_as_the_goal_facet(self) -> None:
        results = [
            _result("tool.flights", 0.9),
            _result("tool.flights-2", 0.5, (0.5, 0.0)),
        ]
        selection = CoverageSetSelector().select(results, context=SelectionContext())
        self.assertEqual([r.resource.metadata.id for r in selection.results], ["tool.flights"])

    def test_coverage_is_counted_per_kind(self) -> None:
        results = [
            _result("tool.invoice", 0.9, (0.9, 0.9)),
            _result("memory.invoice-terms", 0.7, (0.7, 0.7), kind="memory"),
            _result("tool.invoice-2", 0.85, (0.85, 0.85)),
        ]
        selection = CoverageSetSelector().select(results, context=SelectionContext())
        self.assertEqual(
            sorted(r.resource.metadata.id for r in selection.results), ["memory.invoice-terms", "tool.invoice"]
        )

    def test_without_facets_the_best_unit_of_each_kind_is_selected(self) -> None:
        results = [
            _result("tool.a", 0.9),
            _result("tool.b", 0.85),
            _result("skill.a", 0.6, kind="skill"),
            _result("memory.a", 0.05, kind="memory"),
        ]
        selection = CoverageSetSelector().select(results, context=SelectionContext())
        self.assertEqual(sorted(r.resource.metadata.id for r in selection.results), ["skill.a", "tool.a"])

    def test_reasons_name_the_limit_that_kept_a_unit_out(self) -> None:
        results = [_result("tool.a", 0.9, (0.9, 0.9, 0.0)), _result("tool.b", 0.8, (0.5, 0.0, 0.9))]
        capped = CoverageSetSelector().select(results, context=SelectionContext(max_resources=1))
        self.assertIn("tool.b: would exceed max_resources=1", capped.reason)
        limited = CoverageSetSelector().select(results, context=SelectionContext(per_kind_limits={"tool": 1}))
        self.assertIn("tool.b: per-kind limit for tool reached", limited.reason)

    def test_without_facets_one_best_unit_is_selected(self) -> None:
        results = [_result("tool.a", 0.9), _result("tool.b", 0.88), _result("tool.c", 0.2)]
        selection = CoverageSetSelector().select(results, context=SelectionContext())
        self.assertEqual([r.resource.metadata.id for r in selection.results], ["tool.a"])

    def test_min_gain_controls_set_size(self) -> None:
        results = [_result("tool.a", 0.9, (0.9, 0.9, 0.0)), _result("tool.b", 0.4, (0.3, 0.0, 0.15))]
        loose = CoverageSetSelector(min_gain=0.1).select(results, context=SelectionContext())
        strict = CoverageSetSelector(min_gain=0.2).select(results, context=SelectionContext())
        self.assertEqual(len(loose.results), 2)
        self.assertEqual(len(strict.results), 1)

    def test_units_bring_their_dependencies_and_respect_conflicts(self) -> None:
        results = [
            _result("agent.trip", 0.9, (0.9, 0.9, 0.0), kind="agent", dependencies=["tool.flights"]),
            _result("tool.flights", 0.5, (0.5, 0.6, 0.0)),
            _result("tool.hotel", 0.7, (0.4, 0.0, 0.9), conflicts_with=["tool.flights"]),
            _result("tool.hotel-2", 0.6, (0.4, 0.0, 0.7)),
        ]
        selection = CoverageSetSelector().select(results, context=SelectionContext())
        self.assertEqual(
            sorted(r.resource.metadata.id for r in selection.results), ["agent.trip", "tool.flights", "tool.hotel-2"]
        )
        self.assertIn("tool.hotel: conflicts with an already selected resource", selection.reason)

    def test_limits_floors_and_permissions(self) -> None:
        results = [_result("tool.a", 0.9, (0.9, 0.9, 0.0)), _result("tool.b", 0.8, (0.5, 0.0, 0.9))]
        capped = CoverageSetSelector().select(results, context=SelectionContext(max_resources=1))
        self.assertEqual(len(capped.results), 1)
        floored = CoverageSetSelector().select(results, context=SelectionContext(min_relevance=0.95))
        self.assertEqual(floored.status, "abstain")
        gated = [_result("tool.a", 0.9, (0.9, 0.9, 0.0), required_permissions=["net"])]
        self.assertEqual(CoverageSetSelector().select(gated, context=SelectionContext()).status, "escalate")

    def test_include_within_keeps_near_ties_of_the_top_candidate(self) -> None:
        results = [
            _result("tool.weather-now", 0.9, (0.9, 0.9)),
            _result("tool.weather-hourly", 0.88, (0.88, 0.88)),
            _result("tool.news", 0.5, (0.5, 0.5)),
        ]
        default = CoverageSetSelector().select(results, context=SelectionContext())
        self.assertEqual([r.resource.metadata.id for r in default.results], ["tool.weather-now"])
        near = CoverageSetSelector(include_within=0.95).select(results, context=SelectionContext())
        self.assertEqual([r.resource.metadata.id for r in near.results], ["tool.weather-now", "tool.weather-hourly"])
        self.assertNotIn("tool.weather-hourly", near.reason)
        capped = CoverageSetSelector(include_within=0.95).select(results, context=SelectionContext(max_resources=1))
        self.assertEqual(len(capped.results), 1)
        self.assertIn("tool.weather-hourly: would exceed max_resources=1", capped.reason)
        exact = CoverageSetSelector(include_within=1.0).select(results, context=SelectionContext())
        self.assertEqual(len(exact.results), 1)

    def test_near_ties_bring_their_dependencies_but_not_blocked_units(self) -> None:
        results = [
            _result("tool.a", 0.9, (0.9, 0.9)),
            _result("tool.b", 0.89, (0.89, 0.89), dependencies=["skill.b"]),
            _result("skill.b", 0.2, (0.2, 0.2), kind="skill"),
            _result("tool.c", 0.89, (0.89, 0.89), required_permissions=["net"]),
        ]
        selection = CoverageSetSelector(include_within=0.95).select(results, context=SelectionContext())
        self.assertEqual(sorted(r.resource.metadata.id for r in selection.results), ["skill.b", "tool.a", "tool.b"])
        for value in (0.0, 1.5):
            with self.subTest(value=value), self.assertRaises(ValueError):
                CoverageSetSelector(include_within=value)

    def test_rejects_negative_settings(self) -> None:
        with self.assertRaises(ValueError):
            CoverageSetSelector(min_gain=-0.1)
        with self.assertRaises(ValueError):
            CoverageSetSelector(goal_weight=-1.0)



class KernelIntegrationTests(unittest.TestCase):
    def test_kernel_selects_one_tool_per_sub_task(self) -> None:
        from marmo_core import Kernel, PolicyContext

        registry = ResourceRegistry()
        registry.add(_resource("tool.flights", "search airline flights between two cities", side_effect="none"))
        registry.add(_resource("tool.flights-fares", "compare airline flight fares between two cities", side_effect="none"))
        registry.add(_resource("tool.hotel", "reserve a hotel room in a city", side_effect="none"))
        registry.add(_resource("tool.weather", "weather forecast for a city", side_effect="none"))
        llm = _Replying('["search flights from Tokyo to Paris", "reserve a hotel room in Paris"]')
        decomposer = LLMQueryDecomposer(llm)
        kernel = Kernel(
            registry,
            MockLLMProvider(script=[LLMResponse(content="done")]),
            retriever=DecomposedRetriever(LexicalRetriever(), decomposer),
            selector=CoverageSetSelector(),
            policy_context=PolicyContext(),
        )
        result = kernel.run_goal("Find flights from Tokyo to Paris and a hotel room there")

        self.assertEqual(result.status, "completed")
        retrieve = [record for record in kernel.audit_log.records if record.kind == "retrieve"][-1]
        self.assertEqual(sorted(retrieve.payload["selected"]), ["tool.flights@1.0.0", "tool.hotel@1.0.0"])
        self.assertEqual(llm.calls, 1)


if __name__ == "__main__":
    unittest.main()
