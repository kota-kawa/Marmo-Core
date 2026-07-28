"""案E: capability/dependency graph candidate generation (§15.2 拡張版案E).

``CapabilityGraphRetriever`` wraps a layer-1 base retriever (案A lexical /
案B hybrid) and expands its seed pool over the graph declared in resource
metadata: Goal —(text match via the base retriever)→ seed resources
—(depends_on closure / reverse dependents / capability-namespace
siblings)→ structurally implied complements. The capability namespace is
the segment before the first ``.`` in a capability id (``invoicing`` for
``invoicing.execution``), so resources that declare capabilities in one
namespace form a cluster even when their descriptions share no vocabulary.

Expansion inherits relevance from the strongest seed that reaches a
resource, decayed per hop. That single mechanism addresses the bottleneck
the 案H solver comparison isolated (the exact Σu optimum scores worse than
greedy because u(i, q) is blind to structure): complements that share no
vocabulary with the task (i) enter the candidate pool at all, and
(ii) carry a relevance component that survives the selector's abstain gate
and raises their unit utility Σu. The graph is built from declared
metadata only (capabilities / dependencies — F-REG-09), never from natural
language, matching 案H's design stance.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import replace
from typing import AbstractSet
from weakref import WeakKeyDictionary

from .models import SearchQuery, SearchResult
from .registry import ResourceRegistry
from .retriever import (
    RELEVANCE_WEIGHT,
    LexicalRetriever,
    Retriever,
    _resource_search_text,
    _tokens,
)
from .semantic import HybridRetriever


class _MetadataGraph:
    """Edges over one registry snapshot: dependencies, dependents, siblings.

    ``max_namespace_size`` drops sibling edges for namespaces above the
    cap: a namespace shared by hundreds of resources (free-text capability
    boilerplate like "skill instructions" in imported catalogs) is a hub,
    not structure — every member would inherit relevance from any member,
    which measurably floods the pool under distractor noise.
    """

    def __init__(self, registry: ResourceRegistry, *, max_namespace_size: int) -> None:
        definitions = registry.all()
        self.identity_by_id: dict[str, str] = {}
        self.dependencies: dict[str, tuple[str, ...]] = {}
        dependents: dict[str, set[str]] = defaultdict(set)
        members_by_namespace: dict[str, set[str]] = defaultdict(set)
        namespaces_by_id: dict[str, tuple[str, ...]] = {}
        for definition in definitions:
            metadata = definition.metadata
            self.identity_by_id[metadata.id] = definition.identity
            self.dependencies[metadata.id] = metadata.dependencies
            for dependency in metadata.dependencies:
                dependents[dependency].add(metadata.id)
            spaces = tuple(
                dict.fromkeys(capability.split(".", 1)[0] for capability in metadata.capabilities)
            )
            namespaces_by_id[metadata.id] = spaces
            for space in spaces:
                members_by_namespace[space].add(metadata.id)
        self.dependents = {rid: tuple(sorted(ids)) for rid, ids in dependents.items()}
        self.namespaces_by_id = namespaces_by_id
        self.members_by_namespace = {
            space: tuple(sorted(ids))
            for space, ids in members_by_namespace.items()
            if len(ids) <= max_namespace_size
        }

    def neighbors(self, resource_id: str) -> list[tuple[str, str]]:
        """(neighbor id, edge label) pairs one hop away from ``resource_id``."""

        pairs: list[tuple[str, str]] = []
        for dependency in self.dependencies.get(resource_id, ()):
            pairs.append((dependency, "depends_on"))
        for dependent in self.dependents.get(resource_id, ()):
            pairs.append((dependent, "dependent"))
        for space in self.namespaces_by_id.get(resource_id, ()):
            for member in self.members_by_namespace.get(space, ()):
                if member != resource_id:
                    pairs.append((member, f"capability:{space}"))
        return pairs


class CapabilityGraphRetriever(Retriever):
    """案E layer-1 route: base-retriever seeds expanded over the metadata graph.

    ``seed_min_relevance`` keeps noise seeds from dragging their clusters
    into the pool; ``decay`` discounts inherited relevance per hop, so a
    complement two hops from a seed (agent → tool → skill) still enters
    with credible relevance while unrelated namespaces stay below the
    selector's abstain gate. Inherited relevance never lowers a resource's
    own text relevance (``max`` merge) and never exceeds the seed's.

    ``min_seed_token_matches`` demands absolute evidence before a seed may
    expand: BM25 relevance is rank-normalized, so for an off-catalog task
    even a one-token coincidence ("full" matching "full workbench tool")
    ranks ~0.7 — without this guard such a seed pulls its dependency into
    the pool, completes a closure that was rightly incomplete, and flips a
    correct abstain into a wrong selection. A seed with fewer token matches
    still qualifies when its (absolute) embedding similarity reaches
    ``min_seed_semantic``, so purely semantic paraphrase seeds from a
    hybrid base keep their expansion power.

    ``top_seeds`` and ``max_expanded`` bound the expansion under noisy
    pools (measured on the 1,000-distractor benchmark): mid-ranked seeds
    from *adjacent* domains otherwise drag their whole clusters in, and
    the boosted bystanders evict tail-ranked gold members (typically the
    specialist agent) from the fixed-size pool — breaking exactly the
    dependency closures the expansion exists to complete.
    """

    def __init__(
        self,
        base: Retriever,
        *,
        lexical: LexicalRetriever | None = None,
        seed_min_relevance: float = 0.35,
        min_seed_token_matches: int = 2,
        min_seed_semantic: float = 0.55,
        top_seeds: int = 5,
        max_expanded: int = 12,
        max_namespace_size: int = 12,
        decay: float = 0.8,
        max_hops: int = 2,
    ) -> None:
        if not 0.0 < decay <= 1.0:
            raise ValueError("decay must be in (0.0, 1.0]")
        if max_hops < 1:
            raise ValueError("max_hops must be >= 1")
        self.base = base
        if lexical is not None:
            self.lexical = lexical
        elif isinstance(base, LexicalRetriever):
            self.lexical = base
        elif isinstance(base, HybridRetriever):
            self.lexical = base.lexical
        else:
            self.lexical = LexicalRetriever()
        self.seed_min_relevance = seed_min_relevance
        self.min_seed_token_matches = max(0, min_seed_token_matches)
        self.min_seed_semantic = min_seed_semantic
        self.top_seeds = max(1, top_seeds)
        self.max_expanded = max(0, max_expanded)
        self.max_namespace_size = max(1, max_namespace_size)
        self.decay = decay
        self.max_hops = max_hops
        self._graph_cache: WeakKeyDictionary[ResourceRegistry, tuple[int, _MetadataGraph]] = (
            WeakKeyDictionary()
        )

    def search(self, registry: ResourceRegistry, query: SearchQuery) -> list[SearchResult]:
        widened = replace(query, per_kind_limits={}, min_score=0.0)
        seeds = self.base.search(registry, widened)
        if not query.task.strip():
            return self._finalize(seeds, query)
        graph = self._graph_for(registry)

        task_tokens = set(_tokens(query.task))

        qualified: list[SearchResult] = []
        for seed in seeds:
            seed_relevance = float(seed.components.get("relevance", 0.0))
            if seed_relevance < self.seed_min_relevance:
                continue
            # Edge-less resources (imported catalogs without curated
            # metadata) cannot expand anything; letting them consume
            # top_seeds slots would stop the scan before it reaches the
            # first seed that actually carries structure.
            if not graph.neighbors(seed.resource.metadata.id):
                continue
            if self.min_seed_token_matches > 0:
                seed_tokens = set(_tokens(_resource_search_text(seed.resource)))
                lexical_evidence = (
                    len(task_tokens & seed_tokens) >= self.min_seed_token_matches
                )
                semantic_evidence = (
                    float(seed.components.get("semantic", 0.0)) >= self.min_seed_semantic
                )
                if not lexical_evidence and not semantic_evidence:
                    continue
            qualified.append(seed)
            if len(qualified) >= self.top_seeds:
                break

        # Strongest inherited relevance per resource, with provenance.
        inherited: dict[str, float] = {}
        provenance: dict[str, tuple[str, str]] = {}
        for seed in qualified:
            seed_id = seed.resource.metadata.id
            seed_relevance = float(seed.components.get("relevance", 0.0))
            frontier = [(seed_id, seed_relevance)]
            visited = {seed_id}
            for _ in range(self.max_hops):
                next_frontier: list[tuple[str, float]] = []
                for current, current_relevance in frontier:
                    passed = current_relevance * self.decay
                    for neighbor, edge in graph.neighbors(current):
                        if neighbor in visited:
                            continue
                        visited.add(neighbor)
                        if passed > inherited.get(neighbor, 0.0):
                            inherited[neighbor] = passed
                            provenance[neighbor] = (seed_id, edge)
                        next_frontier.append((neighbor, passed))
                frontier = next_frontier

        pooled_ids = {seed.resource.metadata.id for seed in seeds}
        missing = sorted(
            (rid for rid in inherited if rid not in pooled_ids),
            key=lambda rid: (-inherited[rid], rid),
        )[: self.max_expanded]
        expanded = self.lexical.score_semantic_candidates(
            registry,
            widened,
            [graph.identity_by_id[rid] for rid in missing if rid in graph.identity_by_id],
        )
        # Structural additions get reserved pool slots instead of competing
        # on composite score: a workbench tool reached over a declared
        # dependency/capability edge carries cost and community-trust
        # penalties by design, so under distractor noise it ranks below
        # boilerplate resources with perfect trust/cost components — and the
        # selector can never repair a closure whose members were truncated
        # out of the pool. Reserving |expanded| slots evicts the lowest-
        # scoring unstructured candidates instead.
        reserved_ids = {result.resource.metadata.id for result in expanded}

        merged: list[SearchResult] = []
        for result in list(seeds) + expanded:
            resource_id = result.resource.metadata.id
            graph_relevance = inherited.get(resource_id, 0.0)
            own_relevance = float(result.components.get("relevance", 0.0))
            if graph_relevance <= own_relevance:
                merged.append(result)
                continue
            score = max(
                0.0, min(1.0, result.score + RELEVANCE_WEIGHT * (graph_relevance - own_relevance))
            )
            components = dict(result.components)
            components["relevance"] = graph_relevance
            components["graph"] = graph_relevance
            seed_id, edge = provenance[resource_id]
            reasons = result.reasons + (
                f"graph expansion: inherited relevance {graph_relevance:.2f} from {seed_id} via {edge}",
            )
            merged.append(SearchResult(result.resource, score, reasons, components))
        return self._finalize(merged, query, reserved_ids=reserved_ids)

    def _finalize(
        self,
        results: list[SearchResult],
        query: SearchQuery,
        *,
        reserved_ids: AbstractSet[str] = frozenset(),
    ) -> list[SearchResult]:
        ordered = sorted(
            results,
            key=lambda item: (
                item.score,
                item.resource.metadata.trust_level != "untrusted",
                item.resource.metadata.id,
            ),
            reverse=True,
        )
        filtered = [result for result in ordered if result.score >= query.min_score]
        if reserved_ids and len(filtered) > query.top_k:
            reserved = [
                result for result in filtered if result.resource.metadata.id in reserved_ids
            ][: query.top_k]
            keep = query.top_k - len(reserved)
            head = [
                result for result in filtered if result.resource.metadata.id not in reserved_ids
            ][:keep]
            filtered = sorted(
                head + reserved,
                key=lambda item: (
                    item.score,
                    item.resource.metadata.trust_level != "untrusted",
                    item.resource.metadata.id,
                ),
                reverse=True,
            )
        return self.lexical._apply_limits(filtered, query)

    def _graph_for(self, registry: ResourceRegistry) -> _MetadataGraph:
        cached = self._graph_cache.get(registry)
        revision = registry.revision
        if cached is not None and cached[0] == revision:
            return cached[1]
        graph = _MetadataGraph(registry, max_namespace_size=self.max_namespace_size)
        self._graph_cache[registry] = (revision, graph)
        return graph
