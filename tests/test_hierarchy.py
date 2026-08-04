"""Tests for hierarchical coarse-to-fine routing (§15.2 案I)."""

from __future__ import annotations

import unittest

from marmo_core import (
    EmbeddingClusterGrouping,
    HashingEmbeddingProvider,
    HierarchicalRetriever,
    HybridRetriever,
    LexicalRetriever,
    NamespaceGrouping,
    PermissionGrouping,
    ProviderGrouping,
    ResourceDefinition,
    SearchQuery,
)
from marmo_core.registry import ResourceRegistry


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


def _registry(definitions: list[ResourceDefinition]) -> ResourceRegistry:
    registry = ResourceRegistry()
    registry.extend(definitions)
    return registry


def _two_domain_definitions() -> list[ResourceDefinition]:
    return [
        _resource(
            "skill.invoicing.procedure",
            "skill",
            "Procedure for invoice creation and billing runs.",
            capabilities=["invoicing.procedure"],
            tags=["invoicing"],
        ),
        _resource(
            "tool.invoicing.workbench",
            "tool",
            "Workbench tool executing invoices and dunning end to end.",
            capabilities=["invoicing.execution"],
            tags=["invoicing"],
            dependencies=["skill.invoicing.procedure"],
        ),
        _resource(
            "skill.deploy.procedure",
            "skill",
            "Procedure for production deployment and canary rollouts.",
            capabilities=["deploy.procedure"],
            tags=["deploy"],
        ),
        _resource(
            "tool.deploy.workbench",
            "tool",
            "Workbench tool executing release pipelines and rollbacks.",
            capabilities=["deploy.execution"],
            tags=["deploy"],
            dependencies=["skill.deploy.procedure"],
        ),
    ]


class GroupingStrategyTests(unittest.TestCase):
    def test_namespace_grouping_uses_capability_namespace(self) -> None:
        groups = NamespaceGrouping().partition(_two_domain_definitions())
        self.assertEqual(sorted(groups), ["deploy", "invoicing"])
        self.assertEqual(len(groups["invoicing"]), 2)

    def test_namespace_grouping_falls_back_to_tag_then_kind(self) -> None:
        definitions = [
            _resource("memory.notes", "memory", "notes", tags=["ops"]),
            _resource("tool.bare", "tool", "bare tool"),
        ]
        groups = NamespaceGrouping().partition(definitions)
        self.assertEqual(sorted(groups), ["kind:tool", "ops"])

    def test_provider_grouping_resolution_order(self) -> None:
        definitions = [
            _resource("tool.a", "tool", "a", tags=["provider:billing-suite", "x"]),
            _resource("tool.b", "tool", "b", ref="mcp://ops-suite/tool.b"),
            _resource("tool.c", "tool", "c", tags=["invoicing"]),
            _resource("tool.d", "tool", "d"),
        ]
        groups = ProviderGrouping().partition(definitions)
        self.assertEqual(
            sorted(groups), ["billing-suite", "invoicing", "kind:tool", "ops-suite"]
        )

    def test_permission_grouping(self) -> None:
        definitions = [
            _resource("tool.open", "tool", "open"),
            _resource("tool.gated", "tool", "gated", required_permissions=["db.write", "net.external"]),
        ]
        groups = PermissionGrouping().partition(definitions)
        self.assertEqual(sorted(groups), ["perm:db.write+net.external", "perm:public"])

    def test_embedding_cluster_grouping_is_deterministic_and_total(self) -> None:
        definitions = _two_domain_definitions()
        strategy = EmbeddingClusterGrouping(HashingEmbeddingProvider(dimensions=64), clusters=2)
        first = strategy.partition(definitions)
        second = strategy.partition(definitions)
        self.assertEqual(
            {definition.metadata.id for members in first.values() for definition in members},
            {definition.metadata.id for definition in definitions},
        )
        self.assertEqual(
            {group: [d.metadata.id for d in members] for group, members in first.items()},
            {group: [d.metadata.id for d in members] for group, members in second.items()},
        )


class HierarchicalRetrieverTests(unittest.TestCase):
    def setUp(self) -> None:
        self.registry = _registry(_two_domain_definitions())
        self.retriever = HierarchicalRetriever(
            LexicalRetriever(), NamespaceGrouping(), route_k=1
        )

    def test_route_ranks_matching_group_first(self) -> None:
        decisions = self.retriever.route(
            self.registry, SearchQuery(task="create and send the customer invoices")
        )
        self.assertEqual(decisions[0].group, "invoicing")
        self.assertGreater(decisions[0].score, decisions[1].score)

    def test_search_is_confined_to_routed_groups(self) -> None:
        results = self.retriever.search(
            self.registry, SearchQuery(task="create and send the customer invoices", top_k=10)
        )
        ids = {result.resource.metadata.id for result in results}
        self.assertTrue(ids)
        self.assertTrue(all(rid.split(".")[1] == "invoicing" for rid in ids))

    def test_empty_task_falls_back_to_flat_base_search(self) -> None:
        flat = LexicalRetriever().search(self.registry, SearchQuery(top_k=10))
        hier = self.retriever.search(self.registry, SearchQuery(top_k=10))
        self.assertEqual(
            [result.resource.metadata.id for result in flat],
            [result.resource.metadata.id for result in hier],
        )

    def test_no_token_overlap_falls_back_to_flat(self) -> None:
        query = SearchQuery(task="zzz qqq unrelated nonsense", top_k=10)
        flat = LexicalRetriever().search(self.registry, query)
        hier = self.retriever.search(self.registry, query)
        self.assertEqual(
            [result.resource.metadata.id for result in flat],
            [result.resource.metadata.id for result in hier],
        )

    def test_partition_refreshes_after_registry_change(self) -> None:
        self.assertNotIn("secaudit", self.retriever.partition(self.registry))
        self.registry.add(
            _resource(
                "skill.secaudit.procedure",
                "skill",
                "Procedure for vulnerability scanning.",
                capabilities=["secaudit.procedure"],
            )
        )
        self.assertIn("secaudit", self.retriever.partition(self.registry))

    def test_route_k_widens_the_scanned_set(self) -> None:
        wide = HierarchicalRetriever(LexicalRetriever(), NamespaceGrouping(), route_k=2)
        results = wide.search(
            self.registry,
            SearchQuery(task="workbench tool executing invoices and release pipelines", top_k=10),
        )
        domains = {result.resource.metadata.id.split(".")[1] for result in results}
        self.assertEqual(domains, {"invoicing", "deploy"})

    def test_hybrid_base_supplies_routing_embeddings(self) -> None:
        base = HybridRetriever(HashingEmbeddingProvider(dimensions=64), semantic_weight=0.5)
        retriever = HierarchicalRetriever(base, NamespaceGrouping(), route_k=1)
        self.assertIs(retriever.embedding_provider, base.embedding_provider)
        decisions = retriever.route(
            self.registry, SearchQuery(task="create and send the customer invoices")
        )
        self.assertEqual(decisions[0].group, "invoicing")
        self.assertGreater(decisions[0].semantic, 0.0)

    def test_union_registry_is_cached_per_route_set(self) -> None:
        query = SearchQuery(task="create and send the customer invoices", top_k=10)
        self.retriever.search(self.registry, query)
        state = self.retriever._state_for(self.registry)
        self.assertIn(("invoicing",), state._unions)
        first = state.union_registry(("invoicing",))
        second = state.union_registry(("invoicing",))
        self.assertIs(first, second)


if __name__ == "__main__":
    unittest.main()
