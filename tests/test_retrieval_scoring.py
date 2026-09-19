"""Absolute relevance, field-weighted indexing, and cache invalidation."""

from __future__ import annotations

import unittest

from marmo_core import (
    HashingEmbeddingProvider,
    HybridRetriever,
    Kernel,
    LexicalRetriever,
    MockLLMProvider,
    PolicyContext,
    ResourceDefinition,
    ResourceRegistry,
    SearchQuery,
    SelectionContext,
    RuleBasedSetSelector,
)
from marmo_core.evaluator import ExecutionEvaluator


def _resource(resource_id: str, kind: str, description: str, **overrides) -> ResourceDefinition:
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
        "side_effect": "none",
        "trust_level": "core",
        "ref": f"{kind}://{resource_id}",
        "tags": [],
    }
    payload.update(overrides)
    return ResourceDefinition.from_mapping(payload)


def _markdown_skill(resource_id: str, description: str, body: str) -> ResourceDefinition:
    definition = _resource(resource_id, "skill", description, trust_level="community")
    definition.extras.update({"source_type": "markdown_skill", "content": body, "body": body})
    return definition


class _CountingEmbeddings(HashingEmbeddingProvider):
    """Hashing embeddings that record how much text each caller sent."""

    def __init__(self) -> None:
        super().__init__(dimensions=32)
        self.embedded_texts = 0

    def embed(self, texts):
        self.embedded_texts += len(texts)
        return super().embed(texts)


class AbsoluteRelevanceTests(unittest.TestCase):
    def test_off_topic_query_scores_far_below_a_real_match(self) -> None:
        registry = ResourceRegistry()
        registry.add(_resource("tool.invoice", "tool", "Generate a monthly invoice from billing records."))
        registry.add(_resource("tool.deploy", "tool", "Deploy the release to the production cluster."))
        retriever = LexicalRetriever()

        matched = retriever.search(registry, SearchQuery(task="generate a monthly invoice", top_k=1))
        unmatched = retriever.search(
            registry, SearchQuery(task="compose a symphony for string quartet in D minor", top_k=1)
        )

        self.assertEqual(matched[0].resource.metadata.id, "tool.invoice")
        self.assertGreater(matched[0].components["relevance"], 0.5)
        # The best of a catalog that has nothing to offer is allowed to score
        # low; under rank normalization it was pinned near the matched value.
        self.assertLess(max((r.components["relevance"] for r in unmatched), default=0.0), 0.2)

    def test_relevance_does_not_depend_on_the_rest_of_the_result_set(self) -> None:
        query = SearchQuery(task="deploy the release to production", top_k=10)
        alone = ResourceRegistry()
        alone.add(_resource("tool.deploy", "tool", "Deploy the release to the production cluster."))
        crowded = ResourceRegistry()
        crowded.add(_resource("tool.deploy", "tool", "Deploy the release to the production cluster."))
        for index in range(5):
            crowded.add(
                _resource(f"tool.deploy.rival{index}", "tool", "Deploy the release to the production cluster.")
            )

        relevance_alone = LexicalRetriever().search(alone, query)[0].components["relevance"]
        crowded_results = LexicalRetriever().search(crowded, query)
        relevance_crowded = next(
            result.components["relevance"]
            for result in crowded_results
            if result.resource.metadata.id == "tool.deploy"
        )

        # Not identical (idf moves with the corpus), but the same resource must
        # not be re-scored just because rivals showed up.
        self.assertAlmostEqual(relevance_alone, relevance_crowded, delta=0.15)

    def test_relevance_floor_is_reachable_for_the_default_selector(self) -> None:
        registry = ResourceRegistry()
        registry.add(_resource("tool.invoice", "tool", "Generate a monthly invoice from billing records."))
        registry.add(_resource("tool.deploy", "tool", "Deploy the release to the production cluster."))
        registry.add(_resource("tool.chart", "tool", "Draw a bar chart from a table of numbers."))
        registry.add(_resource("skill.review", "skill", "Review a pull request for correctness."))
        task = "chart a course across the north atlantic by sextant"
        results = LexicalRetriever().search(registry, SearchQuery(task=task, top_k=5))
        selector = RuleBasedSetSelector()
        self.assertTrue(results)
        floor = max(result.components["relevance"] for result in results) + 0.01

        without_floor = selector.select(results, context=SelectionContext(task=task))
        with_floor = selector.select(
            results, context=SelectionContext(task=task, min_relevance=floor)
        )

        # The default selector used to ignore the floor entirely, so this set
        # reached the model however unrelated it was to the goal.
        self.assertTrue(without_floor.results)
        self.assertEqual(with_floor.results, ())
        self.assertIn("minimum relevance", with_floor.reason)


class FieldWeightedIndexTests(unittest.TestCase):
    def test_a_long_skill_body_does_not_outrank_the_tool_the_task_describes(self) -> None:
        registry = ResourceRegistry()
        registry.add(_resource("tool.read-text", "tool", "Read a local text file safely."))
        registry.add(
            _markdown_skill(
                "skill.xxe",
                "Detect XML external entity vulnerabilities in application code.",
                "# XXE\n" + ("The scanner can read a local text file safely as part of the audit. " * 60),
            )
        )

        results = LexicalRetriever().search(
            registry, SearchQuery(task="read a local text file safely", top_k=5)
        )

        self.assertEqual(results[0].resource.metadata.id, "tool.read-text")

    def test_the_body_still_carries_signal_when_nothing_else_matches(self) -> None:
        registry = ResourceRegistry()
        registry.add(_resource("tool.read-text", "tool", "Read a local text file safely."))
        registry.add(
            _markdown_skill(
                "skill.xxe",
                "Detect vulnerabilities in application code.",
                "# XXE\nXML external entity payloads are resolved by the parser.",
            )
        )

        results = LexicalRetriever().search(
            registry, SearchQuery(task="xml external entity payloads", top_k=5)
        )

        self.assertEqual(results[0].resource.metadata.id, "skill.xxe")

    def test_keyword_substring_filter_still_matches_inside_a_word(self) -> None:
        registry = ResourceRegistry()
        registry.add(_resource("tool.db", "tool", "Query a PostgreSQL database."))
        registry.add(_resource("tool.mail", "tool", "Send an email message."))

        results = LexicalRetriever().search(
            registry, SearchQuery(task="query the database", keywords=("sql",), top_k=5)
        )

        self.assertEqual([result.resource.metadata.id for result in results], ["tool.db"])


class StatsFeedbackCacheTests(unittest.TestCase):
    def _registry(self) -> ResourceRegistry:
        registry = ResourceRegistry()
        registry.add(_resource("tool.invoice", "tool", "Generate a monthly invoice from billing records."))
        registry.add(_resource("tool.deploy", "tool", "Deploy the release to the production cluster."))
        return registry

    def test_writing_stats_does_not_move_the_content_revision(self) -> None:
        registry = self._registry()
        content_revision = registry.content_revision
        revision = registry.revision

        evaluator = ExecutionEvaluator()
        evaluator.observe_task("invoice", ["tool.invoice"], success=True)
        self.assertEqual(evaluator.apply(registry), 1)

        self.assertGreater(registry.revision, revision)
        self.assertEqual(registry.content_revision, content_revision)

    def test_editing_a_resource_does_move_the_content_revision(self) -> None:
        registry = self._registry()
        content_revision = registry.content_revision

        registry.replace(_resource("tool.invoice", "tool", "Generate a quarterly invoice instead."))

        self.assertGreater(registry.content_revision, content_revision)

    def test_stats_feedback_does_not_re_embed_the_catalog(self) -> None:
        registry = self._registry()
        provider = _CountingEmbeddings()
        retriever = HybridRetriever(provider)
        query = SearchQuery(task="generate a monthly invoice", top_k=2)

        retriever.search(registry, query)
        after_first = provider.embedded_texts
        retriever.search(registry, query)
        self.assertEqual(provider.embedded_texts, after_first, "query vectors should be cached")

        evaluator = ExecutionEvaluator()
        evaluator.observe_task("invoice", ["tool.invoice"], success=True)
        evaluator.apply(registry)
        retriever.search(registry, query)

        self.assertEqual(provider.embedded_texts, after_first)

    def test_stats_feedback_still_reaches_the_score(self) -> None:
        registry = self._registry()
        retriever = LexicalRetriever()
        query = SearchQuery(task="generate a monthly invoice", top_k=2)
        before = retriever.search(registry, query)[0].components["success"]

        evaluator = ExecutionEvaluator()
        for _ in range(4):
            evaluator.observe_task("invoice", ["tool.invoice"], success=True)
        evaluator.apply(registry)
        after = retriever.search(registry, query)[0].components["success"]

        self.assertGreater(after, before)

    def test_editing_a_resource_rebuilds_the_index(self) -> None:
        registry = self._registry()
        retriever = LexicalRetriever()
        query = SearchQuery(task="quarterly revenue reconciliation", top_k=2)
        self.assertEqual(retriever.search(registry, query), [])

        registry.replace(
            _resource("tool.invoice", "tool", "Quarterly revenue reconciliation for finance.")
        )
        results = retriever.search(registry, query)

        self.assertEqual(results[0].resource.metadata.id, "tool.invoice")
        self.assertGreater(results[0].components["relevance"], 0.5)


class RegistryCountTests(unittest.TestCase):
    def test_count_tracks_enabled_resources_per_kind(self) -> None:
        registry = ResourceRegistry()
        registry.add(_resource("tool.a", "tool", "A tool."))
        registry.add(_resource("tool.b", "tool", "Another tool."))
        registry.add(_resource("skill.a", "skill", "A skill."))

        self.assertEqual(registry.count("tool"), 2)
        self.assertEqual(registry.count("skill"), 1)
        self.assertEqual(registry.count("memory"), 0)

        registry.disable("tool.b")
        self.assertEqual(registry.count("tool"), 1)
        registry.enable("tool.b")
        self.assertEqual(registry.count("tool"), 2)


class CandidatePoolSearchBudgetTests(unittest.TestCase):
    def test_one_goal_issues_at_most_two_searches(self) -> None:
        registry = ResourceRegistry()
        for index in range(12):
            registry.add(_resource(f"skill.s{index}", "skill", "Write a deployment runbook."))
        registry.add(_resource("tool.deploy", "tool", "Publish a deployment runbook."))
        registry.add(_resource("memory.deploy", "memory", "Deployment runbook history notes."))
        registry.add(_resource("agent.deploy", "agent", "Deployment runbook specialist agent."))

        class _CountingRetriever(LexicalRetriever):
            searches = 0

            def search(self, registry, query):
                type(self).searches += 1
                return super().search(registry, query)

        retriever = _CountingRetriever()
        kernel = Kernel(registry, MockLLMProvider(), retriever=retriever, policy_context=PolicyContext())
        pool = kernel._candidate_pool("write a deployment runbook", kernel.policy_context)

        self.assertLessEqual(_CountingRetriever.searches, 2)
        kinds = {result.resource.kind for result in pool}
        self.assertIn("tool", kinds)
        self.assertIn("skill", kinds)


if __name__ == "__main__":
    unittest.main()
