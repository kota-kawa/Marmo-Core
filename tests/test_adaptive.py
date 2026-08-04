"""Tests for the adaptive layer: routing cache (案F) and Execution Evaluator."""

from __future__ import annotations

import unittest

from marmo_core import (
    AuditLog,
    CaseBasedRouter,
    ExecutionEvaluator,
    GreedyConstrainedSetSelector,
    HashingEmbeddingProvider,
    LexicalRetriever,
    ResourceDefinition,
    ResourceRegistry,
    ResourceStats,
    RoutingCase,
    RoutingCaseStore,
    SelectionContext,
    outcomes_from_audit,
    resolve_case,
)


def _resource(resource_id: str, kind: str = "tool", **overrides) -> ResourceDefinition:
    payload = {
        "id": resource_id,
        "kind": kind,
        "name": resource_id.replace(".", " "),
        "version": "1.0.0",
        "description": f"resource {resource_id}",
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


def _registry(*definitions: ResourceDefinition) -> ResourceRegistry:
    registry = ResourceRegistry()
    registry.extend(definitions)
    return registry


def _router(registry: ResourceRegistry, **kwargs) -> CaseBasedRouter:
    return CaseBasedRouter(
        LexicalRetriever(), GreedyConstrainedSetSelector(), store=RoutingCaseStore(), **kwargs
    )


INVOICE_TASK = "send the monthly customer invoices for the billing run"


def _invoice_registry() -> ResourceRegistry:
    return _registry(
        _resource(
            "tool.invoicing",
            description="send monthly customer invoices for the billing run",
            capabilities=["invoicing.execution"],
        ),
        _resource(
            "tool.unrelated",
            description="compose orchestral symphony movements",
            capabilities=["music.composition"],
        ),
    )


class RoutingCacheTest(unittest.TestCase):
    def _context(self, permissions: tuple[str, ...] = ()) -> SelectionContext:
        return SelectionContext(
            task=INVOICE_TASK, granted_permissions=permissions, min_relevance=0.0, min_score=0.0
        )

    def test_cold_start_falls_back_to_the_pipeline(self) -> None:
        registry = _invoice_registry()
        router = _router(registry)
        decision = router.route(registry, INVOICE_TASK, context=self._context())
        self.assertEqual(decision.source, "pipeline")
        self.assertEqual(decision.miss_reasons, ("empty-cache",))
        self.assertTrue(decision.selection.results)

    def test_successful_case_is_replayed_without_retrieval(self) -> None:
        registry = _invoice_registry()
        router = _router(registry)
        first = router.route(registry, INVOICE_TASK, context=self._context())
        router.record(first, success=True)

        second = router.route(registry, INVOICE_TASK, context=self._context())
        self.assertEqual(second.source, "cache")
        self.assertAlmostEqual(second.similarity, 1.0, places=6)
        self.assertEqual(
            [result.resource.metadata.id for result in second.selection.results],
            [result.resource.metadata.id for result in first.selection.results],
        )
        self.assertEqual(second.selection.results[0].components["cache"], 1.0)

    def test_failed_routing_is_not_stored(self) -> None:
        registry = _invoice_registry()
        router = _router(registry)
        decision = router.route(registry, INVOICE_TASK, context=self._context())
        router.record(decision, success=False)
        self.assertEqual(len(router.store), 0)
        self.assertEqual(
            router.route(registry, INVOICE_TASK, context=self._context()).source, "pipeline"
        )

    def test_store_failures_admits_failed_cases_but_they_are_never_replayed(self) -> None:
        registry = _invoice_registry()
        router = _router(registry, store_failures=True)
        decision = router.route(registry, INVOICE_TASK, context=self._context())
        router.record(decision, success=False)
        self.assertEqual(len(router.store), 1)

        replay = router.route(registry, INVOICE_TASK, context=self._context())
        self.assertEqual(replay.source, "pipeline")
        self.assertIn("failed-case", replay.miss_reasons)

    def test_a_replayed_case_that_fails_is_evicted(self) -> None:
        registry = _invoice_registry()
        router = _router(registry)
        router.record(router.route(registry, INVOICE_TASK, context=self._context()), success=True)

        replay = router.route(registry, INVOICE_TASK, context=self._context())
        self.assertEqual(replay.source, "cache")
        router.record(replay, success=False)
        self.assertEqual(len(router.store), 0)
        self.assertEqual(router.evictions, 1)

    def test_dissimilar_task_misses_below_the_threshold(self) -> None:
        registry = _invoice_registry()
        router = _router(registry, threshold=0.72)
        router.record(router.route(registry, INVOICE_TASK, context=self._context()), success=True)

        other = "compose a four movement symphony for a full orchestra"
        decision = router.route(
            registry, other, context=SelectionContext(task=other, min_relevance=0.0, min_score=0.0)
        )
        self.assertEqual(decision.source, "pipeline")
        self.assertIn("below-threshold", decision.miss_reasons)


class RoutingCacheGuardTest(unittest.TestCase):
    """The four admission guards: staleness, permissions, outcome, feasibility."""

    def _warm(self, registry, *, permissions=(), **kwargs):
        router = _router(registry, **kwargs)
        context = SelectionContext(
            task=INVOICE_TASK, granted_permissions=permissions, min_relevance=0.0, min_score=0.0
        )
        router.record(router.route(registry, INVOICE_TASK, context=context), success=True)
        return router

    def test_re_versioned_resource_makes_the_case_stale(self) -> None:
        registry = _invoice_registry()
        router = self._warm(registry)

        republished = _registry(
            _resource(
                "tool.invoicing",
                version="2.0.0",
                description="send monthly customer invoices for the billing run",
                capabilities=["invoicing.execution"],
            ),
            _resource("tool.unrelated", description="compose orchestral symphony movements"),
        )
        decision = router.route(
            republished,
            INVOICE_TASK,
            context=SelectionContext(task=INVOICE_TASK, min_relevance=0.0, min_score=0.0),
        )
        self.assertEqual(decision.source, "pipeline")
        self.assertIn("stale", decision.miss_reasons)

    def test_invalidate_off_replays_across_a_version_change(self) -> None:
        registry = _invoice_registry()
        router = self._warm(registry, invalidate=False)

        republished = _registry(
            _resource(
                "tool.invoicing",
                version="2.0.0",
                description="send monthly customer invoices for the billing run",
                side_effect="irreversible",
            ),
            _resource("tool.unrelated", description="compose orchestral symphony movements"),
        )
        decision = router.route(
            republished,
            INVOICE_TASK,
            context=SelectionContext(task=INVOICE_TASK, min_relevance=0.0, min_score=0.0),
        )
        self.assertEqual(decision.source, "cache")
        self.assertEqual(decision.selection.results[0].resource.metadata.version, "2.0.0")
        self.assertEqual(
            decision.selection.results[0].resource.metadata.side_effect, "irreversible"
        )

    def test_permissions_are_re_verified_against_live_metadata(self) -> None:
        registry = _registry(
            _resource(
                "tool.invoicing",
                description="send monthly customer invoices for the billing run",
                required_permissions=["billing.read"],
            )
        )
        router = self._warm(registry, permissions=("billing.read",))

        # The resource now demands a permission the caller was never granted.
        tightened = _registry(
            _resource(
                "tool.invoicing",
                description="send monthly customer invoices for the billing run",
                required_permissions=["billing.read", "billing.write"],
            )
        )
        decision = router.route(
            tightened,
            INVOICE_TASK,
            context=SelectionContext(
                task=INVOICE_TASK,
                granted_permissions=("billing.read",),
                min_relevance=0.0,
                min_score=0.0,
            ),
        )
        self.assertEqual(decision.source, "pipeline")
        self.assertIn("infeasible", decision.miss_reasons)

    def test_selected_case_is_not_replayed_under_narrowed_grants(self) -> None:
        registry = _registry(
            _resource(
                "tool.invoicing",
                description="send monthly customer invoices for the billing run",
                required_permissions=["billing.read"],
            )
        )
        router = self._warm(registry, permissions=("billing.read",))
        decision = router.route(
            registry,
            INVOICE_TASK,
            context=SelectionContext(task=INVOICE_TASK, min_relevance=0.0, min_score=0.0),
        )
        self.assertEqual(decision.source, "pipeline")
        self.assertIn("permission-narrowed", decision.miss_reasons)

    def test_escalate_case_is_not_replayed_after_new_grants(self) -> None:
        """New permissions are exactly what can turn an escalate into a set."""

        registry = _registry(
            _resource(
                "tool.invoicing",
                description="send monthly customer invoices for the billing run",
                required_permissions=["billing.write"],
            )
        )
        router = _router(registry)
        blocked = SelectionContext(task=INVOICE_TASK, min_relevance=0.0, min_score=0.0)
        first = router.route(registry, INVOICE_TASK, context=blocked)
        self.assertEqual(first.selection.status, "escalate")
        router.record(first, success=True)

        granted = SelectionContext(
            task=INVOICE_TASK,
            granted_permissions=("billing.write",),
            min_relevance=0.0,
            min_score=0.0,
        )
        decision = router.route(registry, INVOICE_TASK, context=granted)
        self.assertEqual(decision.source, "pipeline")
        self.assertIn("permission-widened", decision.miss_reasons)
        self.assertEqual(decision.selection.status, "selected")


class RoutingCaseStoreTest(unittest.TestCase):
    def test_rank_orders_by_similarity(self) -> None:
        store = RoutingCaseStore(
            [
                RoutingCase(task="send the monthly customer invoices", status="selected"),
                RoutingCase(task="compose a symphony for orchestra", status="selected"),
            ]
        )
        ranked = store.rank("send the monthly customer invoices please")
        self.assertEqual(ranked[0][0].task, "send the monthly customer invoices")
        self.assertGreater(ranked[0][1], ranked[1][1])

    def test_semantic_weight_requires_a_provider(self) -> None:
        with self.assertRaises(ValueError):
            RoutingCaseStore(semantic_weight=0.5)
        store = RoutingCaseStore(
            [RoutingCase(task="send invoices", status="selected")],
            embeddings=HashingEmbeddingProvider(dimensions=64),
            semantic_weight=0.5,
        )
        self.assertEqual(len(store.rank("send invoices")), 1)

    def test_add_replaces_the_case_for_the_same_task_and_keeps_hits(self) -> None:
        store = RoutingCaseStore()
        first = store.add(RoutingCase(task="t", status="selected", reason="first"))
        first.hits = 3
        store.add(RoutingCase(task="t", status="abstain", reason="second"))
        self.assertEqual(len(store), 1)
        self.assertEqual(store.cases[0].reason, "second")
        self.assertEqual(store.cases[0].hits, 3)

    def test_capacity_evicts_the_least_reused_case(self) -> None:
        store = RoutingCaseStore(capacity=2)
        kept = store.add(RoutingCase(task="a", status="selected"))
        kept.hits = 5
        store.add(RoutingCase(task="b", status="selected"))
        store.add(RoutingCase(task="c", status="selected"))
        self.assertEqual({case.task for case in store.cases}, {"a", "c"})

    def test_prune_drops_cases_with_missing_resources(self) -> None:
        registry = _invoice_registry()
        store = RoutingCaseStore()
        store.add(RoutingCase(task="t", status="selected"))
        router = _router(registry)
        warm = router.route(
            registry,
            INVOICE_TASK,
            context=SelectionContext(task=INVOICE_TASK, min_relevance=0.0, min_score=0.0),
        )
        router.record(warm, success=True)
        self.assertIsNotNone(resolve_case(router.store.cases[0], registry))
        self.assertEqual(router.store.prune(registry), 0)
        self.assertIsNone(resolve_case(router.store.cases[0], _registry(_resource("tool.other"))))

    def test_round_trips_through_json(self) -> None:
        import tempfile
        from pathlib import Path

        store = RoutingCaseStore()
        store.add(
            RoutingCase(
                task="send invoices",
                status="selected",
                granted_permissions=("billing.read",),
                reason="greedy",
            )
        )
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "cases.json"
            store.save(path)
            restored = RoutingCaseStore()
            self.assertEqual(restored.load(path), 1)
        self.assertEqual(restored.cases[0].task, "send invoices")
        self.assertEqual(restored.cases[0].granted_permissions, ("billing.read",))


class ExecutionEvaluatorTest(unittest.TestCase):
    def test_shrinkage_keeps_one_failure_from_zeroing_a_resource(self) -> None:
        evaluator = ExecutionEvaluator(prior_weight=2.0, prior_success_rate=0.5)
        evaluator.observe_task("t", ["tool.a"], success=False)
        stats = evaluator.stats_for("tool.a")
        self.assertAlmostEqual(stats.success_rate, 1 / 3, places=6)
        self.assertEqual(stats.usage_count, 1)

    def test_success_rate_converges_with_observations(self) -> None:
        evaluator = ExecutionEvaluator(prior_weight=2.0, prior_success_rate=0.5)
        for _ in range(48):
            evaluator.observe_task("t", ["tool.a"], success=True)
        self.assertGreater(evaluator.stats_for("tool.a").success_rate, 0.95)

    def test_unobserved_resource_has_no_stats(self) -> None:
        self.assertIsNone(ExecutionEvaluator().stats_for("tool.missing"))

    def test_apply_writes_stats_back_and_bumps_the_revision(self) -> None:
        registry = _invoice_registry()
        before = registry.revision
        evaluator = ExecutionEvaluator()
        evaluator.observe_task("t", ["tool.invoicing"], success=True, latency_ms=12.0, cost=0.5)

        self.assertEqual(evaluator.apply(registry), 1)
        stats = registry.get("tool.invoicing").metadata.stats
        self.assertEqual(stats.usage_count, 1)
        self.assertAlmostEqual(stats.average_latency_ms, 12.0)
        self.assertAlmostEqual(stats.average_cost, 0.5)
        self.assertGreater(registry.revision, before)

        # Re-applying identical stats is a no-op.
        self.assertEqual(evaluator.apply(registry), 0)

    def test_registry_replace_rejects_unknown_identities(self) -> None:
        from marmo_core import ResourceNotFoundError

        registry = _invoice_registry()
        with self.assertRaises(ResourceNotFoundError):
            registry.replace(_resource("tool.never.registered"))

    def test_outcomes_are_reconstructed_from_an_audit_log(self) -> None:
        log = AuditLog()
        trace = "trace-1"
        log.append(
            "retrieve",
            {
                "task": "send invoices",
                "selection_status": "selected",
                "selected": ["tool.invoicing@1.0.0", "skill.invoicing@1.0.0"],
            },
            trace_id=trace,
        )
        log.append("execute", {"tool_id": "tool.invoicing", "elapsed_ms": 8.0}, trace_id=trace)
        log.append("task", {"goal": "send invoices", "status": "completed"}, trace_id=trace)

        outcomes = outcomes_from_audit(log)
        self.assertEqual(len(outcomes), 1)
        self.assertTrue(outcomes[0].success)
        self.assertEqual(outcomes[0].resource_ids, ("tool.invoicing", "skill.invoicing"))
        self.assertAlmostEqual(outcomes[0].latency_ms, 8.0)

    def test_incomplete_traces_are_skipped(self) -> None:
        log = AuditLog()
        log.append("retrieve", {"selection_status": "selected", "selected": []}, trace_id="t")
        self.assertEqual(outcomes_from_audit(log), [])

    def test_failed_task_lowers_the_success_rate(self) -> None:
        log = AuditLog()
        log.append(
            "retrieve",
            {"task": "g", "selection_status": "selected", "selected": ["tool.a@1.0.0"]},
            trace_id="t",
        )
        log.append("task", {"goal": "g", "status": "failed"}, trace_id="t")
        evaluator = ExecutionEvaluator()
        evaluator.ingest_audit(log)
        self.assertLess(evaluator.stats_for("tool.a").success_rate, 0.5)

    def test_stats_feed_the_retrieval_score(self) -> None:
        """The loop is only closed if written stats change ranking (F-REG-05)."""

        registry = _registry(
            _resource("tool.alpha", description="send monthly customer invoices"),
            _resource("tool.beta", description="send monthly customer invoices"),
        )
        from marmo_core import SearchQuery

        retriever = LexicalRetriever()
        query = SearchQuery(task="send monthly customer invoices", top_k=5)
        baseline = {r.resource.metadata.id: r.score for r in retriever.search(registry, query)}
        self.assertAlmostEqual(baseline["tool.alpha"], baseline["tool.beta"], places=6)

        evaluator = ExecutionEvaluator(prior_weight=0.0)
        for _ in range(10):
            evaluator.observe_task("t", ["tool.alpha"], success=True)
            evaluator.observe_task("t", ["tool.beta"], success=False)
        evaluator.apply(registry)

        after = {r.resource.metadata.id: r.score for r in retriever.search(registry, query)}
        self.assertGreater(after["tool.alpha"], after["tool.beta"])

    def test_report_summarizes_observations(self) -> None:
        evaluator = ExecutionEvaluator()
        evaluator.observe_task("t", ["tool.a"], success=True)
        evaluator.observe_task("t", ["tool.a", "tool.b"], success=False)
        report = evaluator.report()
        self.assertEqual(report["observations"], 2)
        self.assertEqual(report["resources_observed"], 2)
        self.assertAlmostEqual(report["success_rate"], 0.5)
        self.assertIn("tool.a", report["stats"])

    def test_reset_clears_state(self) -> None:
        evaluator = ExecutionEvaluator()
        evaluator.observe_task("t", ["tool.a"], success=True)
        evaluator.reset()
        self.assertIsNone(evaluator.stats_for("tool.a"))
        self.assertEqual(evaluator.snapshot(), {})

    def test_invalid_priors_are_rejected(self) -> None:
        with self.assertRaises(ValueError):
            ExecutionEvaluator(prior_weight=-1.0)
        with self.assertRaises(ValueError):
            ExecutionEvaluator(prior_success_rate=1.5)


class ResourceStatsRoundTripTest(unittest.TestCase):
    def test_written_stats_survive_serialization(self) -> None:
        registry = _invoice_registry()
        evaluator = ExecutionEvaluator()
        evaluator.observe_task("t", ["tool.invoicing"], success=True, latency_ms=3.0)
        evaluator.apply(registry)
        definition = registry.get("tool.invoicing")
        restored = ResourceDefinition.from_mapping(definition.to_dict(include_extras=False))
        self.assertEqual(
            restored.metadata.stats, ResourceStats.from_mapping(definition.metadata.stats.to_dict())
        )


if __name__ == "__main__":
    unittest.main()
