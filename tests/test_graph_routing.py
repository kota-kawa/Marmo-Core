"""Tests for the capability/dependency graph retriever (§15.2 案E)."""

from __future__ import annotations

import unittest

from marmo_core import (
    CapabilityGraphRetriever,
    GreedyConstrainedSetSelector,
    LexicalRetriever,
    ResourceDefinition,
    SearchQuery,
    SelectionContext,
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
    for definition in definitions:
        registry.add(definition)
    return registry


class CapabilityGraphRetrieverTests(unittest.TestCase):
    def _domain_registry(self) -> ResourceRegistry:
        # A "billing" cluster whose memory shares no vocabulary with the
        # task, plus an unrelated cluster.
        return _registry(
            [
                _resource(
                    "tool.billing.workbench",
                    "tool",
                    "Create and send invoices for the monthly billing run.",
                    capabilities=["billing.execution"],
                    dependencies=["skill.billing.procedure"],
                ),
                _resource(
                    "skill.billing.procedure",
                    "skill",
                    "Checklist for dunning and payment terms.",
                    capabilities=["billing.procedure"],
                ),
                _resource(
                    "memory.billing.context",
                    "memory",
                    "Accumulated ledger decisions and dunning history notes.",
                    capabilities=["billing.context"],
                ),
                _resource(
                    "agent.billing.specialist",
                    "agent",
                    "Specialist that plans revenue paperwork end to end.",
                    capabilities=["billing.orchestration"],
                    dependencies=["tool.billing.workbench"],
                ),
                _resource(
                    "tool.weather.forecast",
                    "tool",
                    "Forecast tomorrow's weather for a city.",
                    capabilities=["weather.forecast"],
                ),
            ]
        )

    def test_namespace_siblings_inherit_relevance(self) -> None:
        registry = self._domain_registry()
        query = SearchQuery(task="create and send the monthly invoices", top_k=10)
        lexical_ids = {
            r.resource.metadata.id for r in LexicalRetriever().search(registry, query)
        }
        self.assertNotIn("memory.billing.context", lexical_ids)

        results = CapabilityGraphRetriever(LexicalRetriever()).search(registry, query)
        by_id = {r.resource.metadata.id: r for r in results}
        self.assertIn("memory.billing.context", by_id)
        memory = by_id["memory.billing.context"]
        self.assertGreater(memory.components["relevance"], 0.0)
        self.assertIn("graph", memory.components)
        self.assertTrue(any("graph expansion" in reason for reason in memory.reasons))

    def test_unrelated_namespace_is_not_pulled_in(self) -> None:
        registry = self._domain_registry()
        results = CapabilityGraphRetriever(LexicalRetriever()).search(
            registry, SearchQuery(task="create and send the monthly invoices", top_k=10)
        )
        weather = [
            r for r in results if r.resource.metadata.id == "tool.weather.forecast"
        ]
        for result in weather:
            self.assertNotIn("graph", result.components)

    def test_inherited_relevance_decays_and_never_exceeds_seed(self) -> None:
        registry = self._domain_registry()
        retriever = CapabilityGraphRetriever(LexicalRetriever(), decay=0.5)
        results = retriever.search(
            registry, SearchQuery(task="create and send the monthly invoices", top_k=10)
        )
        by_id = {r.resource.metadata.id: r for r in results}
        seed_relevance = by_id["tool.billing.workbench"].components["relevance"]
        memory_relevance = by_id["memory.billing.context"].components["relevance"]
        self.assertLessEqual(memory_relevance, seed_relevance * 0.5 + 1e-9)

    def test_own_relevance_is_never_lowered(self) -> None:
        registry = self._domain_registry()
        query = SearchQuery(task="create and send the monthly invoices", top_k=10)
        base = {
            r.resource.metadata.id: r.components["relevance"]
            for r in LexicalRetriever().search(registry, query)
        }
        graphed = {
            r.resource.metadata.id: r.components["relevance"]
            for r in CapabilityGraphRetriever(LexicalRetriever()).search(registry, query)
        }
        for resource_id, relevance in base.items():
            self.assertGreaterEqual(graphed[resource_id] + 1e-9, relevance)

    def test_low_relevance_seeds_do_not_expand(self) -> None:
        registry = self._domain_registry()
        retriever = CapabilityGraphRetriever(LexicalRetriever(), seed_min_relevance=1.1)
        results = retriever.search(
            registry, SearchQuery(task="create and send the monthly invoices", top_k=10)
        )
        for result in results:
            self.assertNotIn("graph", result.components)

    def test_expansion_completes_the_gold_set_for_the_selector(self) -> None:
        registry = self._domain_registry()
        query = SearchQuery(task="create and send the monthly invoices", top_k=10)
        candidates = CapabilityGraphRetriever(LexicalRetriever()).search(registry, query)
        selection = GreedyConstrainedSetSelector().select(
            candidates,
            context=SelectionContext(
                per_kind_limits={"memory": 1, "skill": 1, "tool": 1, "agent": 1},
                min_relevance=0.2,
            ),
        )
        ids = {r.resource.metadata.id for r in selection.results}
        self.assertEqual(
            ids,
            {
                "memory.billing.context",
                "skill.billing.procedure",
                "tool.billing.workbench",
                "agent.billing.specialist",
            },
        )


if __name__ == "__main__":
    unittest.main()


class VersionedDependencyEdgeTests(unittest.TestCase):
    """A dependency reference becomes a graph edge only when it names one resource."""

    TASK = "create and send the monthly invoices"

    def _registry(self, dependency: str, *skill_versions: str) -> ResourceRegistry:
        definitions = [
            _resource(
                "tool.billing.workbench",
                "tool",
                "Create and send invoices for the monthly billing run.",
                capabilities=["billing.execution"],
                dependencies=[dependency],
            )
        ]
        definitions.extend(
            _resource(
                "skill.checklist",
                "skill",
                "Checklist for dunning and payment terms.",
                # One namespace per version, so no sibling edge links them.
                capabilities=[f"checklist{version[0]}.procedure"],
                version=version,
            )
            for version in skill_versions
        )
        return _registry(definitions)

    def _expanded(self, registry: ResourceRegistry) -> dict[str, str]:
        results = CapabilityGraphRetriever(LexicalRetriever()).search(
            registry, SearchQuery(task=self.TASK, top_k=10)
        )
        return {
            r.resource.identity: " ".join(r.reasons) for r in results if "graph" in r.components
        }

    def test_a_versioned_dependency_is_followed_to_exactly_that_version(self) -> None:
        registry = self._registry("skill.checklist@1.0.0", "1.0.0", "2.0.0")
        expanded = self._expanded(registry)
        self.assertEqual(set(expanded), {"skill.checklist@1.0.0"})
        self.assertIn("depends_on", expanded["skill.checklist@1.0.0"])

    def test_a_dependency_on_an_absent_version_adds_no_edge(self) -> None:
        self.assertEqual(self._expanded(self._registry("skill.checklist@3.0.0", "1.0.0", "2.0.0")), {})

    def test_a_bare_id_names_its_only_version(self) -> None:
        expanded = self._expanded(self._registry("skill.checklist", "2.0.0"))
        self.assertEqual(set(expanded), {"skill.checklist@2.0.0"})

    def test_a_bare_id_shared_by_several_versions_is_ambiguous(self) -> None:
        self.assertEqual(self._expanded(self._registry("skill.checklist", "1.0.0", "2.0.0")), {})
