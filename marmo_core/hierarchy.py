"""案I: hierarchical coarse-to-fine routing (§15.2).

``HierarchicalRetriever`` never searches the catalog as one flat index.
Stage 1 (coarse) ranks *groups* of resources against the task — BM25 over
each group's aggregated metadata text, optionally blended with the cosine
between the query embedding and the group centroid — and keeps the top
``route_k`` groups. Stage 2 (fine) runs the wrapped base retriever (案A
lexical / 案B hybrid) over a registry restricted to the members of the
routed groups, so results, scores, and downstream selector behavior are
exactly "the flat pipeline, confined to the routed subset".

Group construction is a swappable ``GroupingStrategy`` because §15.2 案I
requires comparing several partitions of the same catalog:

- ``NamespaceGrouping``   — capability namespaces (declared taxonomy)
- ``ProviderGrouping``    — provider / MCP-server units
- ``PermissionGrouping``  — permission / trust boundaries
- ``EmbeddingClusterGrouping`` — k-means over description embeddings

The failure mode this architecture trades for scale is mis-routing: a
resource whose group is not selected in stage 1 can never be recovered in
stage 2. Benchmarks therefore measure Routed vs Oracle Cluster Recall via
the public ``partition`` / ``route`` methods rather than treating the
retriever as a black box. When the coarse stage has no signal at all
(empty task, zero group scores) the retriever falls back to the flat base
search instead of returning nothing.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections import Counter, defaultdict
from dataclasses import dataclass
from typing import Sequence
from weakref import WeakKeyDictionary
import math
import random

from .models import ResourceDefinition, SearchQuery, SearchResult
from .registry import ResourceRegistry
from .retriever import _BM25_B, _BM25_K1, Retriever, _resource_search_text, _tokens
from .semantic import EmbeddingProvider, HybridRetriever, _cosine_01, _embedding_text


class GroupingStrategy(ABC):
    """Partition a catalog into named groups from declared metadata only."""

    label = "abstract"

    @abstractmethod
    def partition(self, definitions: Sequence[ResourceDefinition]) -> dict[str, list[ResourceDefinition]]:
        """Return group id -> member definitions. Every definition appears once."""


class NamespaceGrouping(GroupingStrategy):
    """Group by the declared capability namespace (the segment before the
    first ``.``), the same taxonomy the capability graph (案E) uses.
    Resources without capabilities fall back to their first tag, then kind.
    """

    label = "namespace"

    def partition(self, definitions: Sequence[ResourceDefinition]) -> dict[str, list[ResourceDefinition]]:
        groups: dict[str, list[ResourceDefinition]] = defaultdict(list)
        for definition in definitions:
            metadata = definition.metadata
            if metadata.capabilities:
                group = metadata.capabilities[0].split(".", 1)[0]
            elif metadata.tags:
                group = metadata.tags[0]
            else:
                group = f"kind:{metadata.kind}"
            groups[group].append(definition)
        return dict(groups)


class ProviderGrouping(GroupingStrategy):
    """Group by provider / MCP-server unit.

    Resolution order: an explicit ``provider:<name>`` tag, the host of an
    ``mcp://`` ref, the first tag, then kind. Local resources whose refs
    carry no provider (``tool://<id>``) thus cluster by their domain tag
    instead of degenerating into singleton groups.
    """

    label = "provider"

    def partition(self, definitions: Sequence[ResourceDefinition]) -> dict[str, list[ResourceDefinition]]:
        groups: dict[str, list[ResourceDefinition]] = defaultdict(list)
        for definition in definitions:
            metadata = definition.metadata
            group = ""
            for tag in metadata.tags:
                if tag.startswith("provider:"):
                    group = tag.split(":", 1)[1]
                    break
            if not group and metadata.ref.startswith("mcp://"):
                group = metadata.ref[len("mcp://") :].split("/", 1)[0]
            if not group:
                group = metadata.tags[0] if metadata.tags else f"kind:{metadata.kind}"
            groups[group].append(definition)
        return dict(groups)


class PermissionGrouping(GroupingStrategy):
    """Group by the declared permission boundary (sorted required_permissions).

    Permission-free resources share one ``perm:public`` group, so this
    partition is expected to be coarse; it exists to measure whether trust
    boundaries alone carry enough signal to route by (§15.2 案I).
    """

    label = "permission"

    def partition(self, definitions: Sequence[ResourceDefinition]) -> dict[str, list[ResourceDefinition]]:
        groups: dict[str, list[ResourceDefinition]] = defaultdict(list)
        for definition in definitions:
            required = definition.metadata.required_permissions
            group = "perm:" + "+".join(sorted(required)) if required else "perm:public"
            groups[group].append(definition)
        return dict(groups)


class EmbeddingClusterGrouping(GroupingStrategy):
    """k-means over description embeddings (deterministic, seeded).

    Uses numpy for the assignment step when it is importable (it ships
    with the benchmark's embedding stack); the pure-Python fallback keeps
    the core dependency-free but is only meant for small catalogs.
    """

    label = "embedding"

    def __init__(
        self,
        embedding_provider: EmbeddingProvider,
        *,
        clusters: int | None = None,
        iterations: int = 8,
        seed: int = 7,
    ) -> None:
        if clusters is not None and clusters < 2:
            raise ValueError("clusters must be >= 2")
        if iterations < 1:
            raise ValueError("iterations must be >= 1")
        self.embedding_provider = embedding_provider
        self.clusters = clusters
        self.iterations = iterations
        self.seed = seed

    def partition(self, definitions: Sequence[ResourceDefinition]) -> dict[str, list[ResourceDefinition]]:
        if not definitions:
            return {}
        count = len(definitions)
        k = self.clusters or max(2, min(256, round(math.sqrt(count))))
        k = min(k, count)
        vectors = self.embedding_provider.embed([_embedding_text(definition) for definition in definitions])
        assignments = _kmeans(vectors, k, iterations=self.iterations, seed=self.seed)
        groups: dict[str, list[ResourceDefinition]] = defaultdict(list)
        for definition, cluster in zip(definitions, assignments):
            groups[f"cluster:{cluster:03d}"].append(definition)
        return dict(groups)


@dataclass(frozen=True)
class RouteDecision:
    """Ranked coarse-stage outcome for one query."""

    group: str
    score: float
    lexical: float
    semantic: float


class HierarchicalRetriever(Retriever):
    """案I layer-1 route: coarse group routing, then the base retriever
    confined to the routed groups.

    ``route_k`` bounds how many groups stage 2 may scan; the scanned
    fraction of the catalog (Σ routed group sizes / catalog size) is the
    quantity this retriever exists to shrink. ``route_semantic_weight``
    blends the group-level BM25 score with the query-to-centroid cosine
    when an embedding provider is available (explicitly, or inherited from
    a hybrid base retriever) — without it, paraphrased tasks lose the
    correct group in stage 1 and stage 2 cannot recover.
    """

    def __init__(
        self,
        base: Retriever,
        strategy: GroupingStrategy,
        *,
        route_k: int = 3,
        route_semantic_weight: float = 0.5,
        embedding_provider: EmbeddingProvider | None = None,
    ) -> None:
        if route_k < 1:
            raise ValueError("route_k must be >= 1")
        if not 0.0 <= route_semantic_weight <= 1.0:
            raise ValueError("route_semantic_weight must be between 0.0 and 1.0")
        self.base = base
        self.strategy = strategy
        self.route_k = route_k
        self.route_semantic_weight = route_semantic_weight
        self.embedding_provider: EmbeddingProvider | None
        if embedding_provider is not None:
            self.embedding_provider = embedding_provider
        elif isinstance(base, HybridRetriever):
            self.embedding_provider = base.embedding_provider
        else:
            self.embedding_provider = None
        self._cache: WeakKeyDictionary[ResourceRegistry, tuple[int, _HierarchyState]] = (
            WeakKeyDictionary()
        )

    # -- public surface used by benchmarks ------------------------------------

    def partition(self, registry: ResourceRegistry) -> dict[str, tuple[str, ...]]:
        """Group id -> member resource ids (for cluster-recall accounting)."""

        state = self._state_for(registry)
        return {
            group: tuple(definition.metadata.id for definition in members)
            for group, members in state.groups.items()
        }

    def route(self, registry: ResourceRegistry, query: SearchQuery) -> list[RouteDecision]:
        """All groups ranked by coarse-stage score (descending)."""

        state = self._state_for(registry)
        routing_tokens = _tokens(query.task) + [
            token for keyword in query.keywords for token in _tokens(keyword)
        ]
        if not routing_tokens or not state.group_names:
            return []
        bm25 = state.bm25(routing_tokens)
        max_bm25 = max(bm25.values(), default=0.0)
        semantic: dict[str, float] = {}
        provider = self.embedding_provider
        weight = self.route_semantic_weight if provider is not None else 0.0
        if weight > 0.0 and query.task.strip() and provider is not None:
            query_vector = provider.embed([query.task])[0]
            centroids = state.centroids(provider)
            semantic = {
                group: _cosine_01(query_vector, centroid) for group, centroid in centroids.items()
            }
        decisions = []
        for group in state.group_names:
            lexical = (bm25.get(group, 0.0) / max_bm25) if max_bm25 > 0 else 0.0
            sem = semantic.get(group, 0.0)
            score = (1.0 - weight) * lexical + weight * sem
            decisions.append(RouteDecision(group=group, score=score, lexical=lexical, semantic=sem))
        decisions.sort(key=lambda decision: (decision.score, decision.group), reverse=True)
        return decisions

    def search(self, registry: ResourceRegistry, query: SearchQuery) -> list[SearchResult]:
        routed = [decision for decision in self.route(registry, query) if decision.score > 0.0]
        if not routed:
            # No coarse signal (empty task or zero overlap): degrade to the
            # flat base search rather than returning nothing.
            return self.base.search(registry, query)
        selected = tuple(decision.group for decision in routed[: self.route_k])
        state = self._state_for(registry)
        return self.base.search(state.union_registry(selected), query)

    # -- cached per-registry state ---------------------------------------------

    def _state_for(self, registry: ResourceRegistry) -> "_HierarchyState":
        cached = self._cache.get(registry)
        revision = registry.revision
        if cached is not None and cached[0] == revision:
            return cached[1]
        state = _HierarchyState(self.strategy.partition(registry.all()))
        self._cache[registry] = (revision, state)
        return state


class _HierarchyState:
    """Partition-derived caches for one registry snapshot: group BM25
    statistics, embedding centroids, and union sub-registries per route set.
    """

    def __init__(self, groups: dict[str, list[ResourceDefinition]]) -> None:
        self.groups = groups
        self.group_names = sorted(groups)
        self._doc_counts: dict[str, Counter[str]] = {}
        self._doc_lengths: dict[str, int] = {}
        total_length = 0
        for group, members in groups.items():
            counts: Counter[str] = Counter()
            for definition in members:
                counts.update(_tokens(_resource_search_text(definition)))
            self._doc_counts[group] = counts
            length = sum(counts.values())
            self._doc_lengths[group] = length
            total_length += length
        self._average_length = (total_length / len(groups)) if groups else 0.0
        self._postings: dict[str, list[str]] = defaultdict(list)
        for group in self.group_names:
            for token in self._doc_counts[group]:
                self._postings[token].append(group)
        self._centroids: dict[int, dict[str, list[float]]] = {}
        self._unions: dict[tuple[str, ...], ResourceRegistry] = {}

    def bm25(self, query_tokens: Sequence[str]) -> dict[str, float]:
        scores: dict[str, float] = defaultdict(float)
        group_count = len(self.group_names)
        for token in set(query_tokens):
            groups = self._postings.get(token)
            if not groups:
                continue
            document_frequency = len(groups)
            idf = math.log(1.0 + (group_count - document_frequency + 0.5) / (document_frequency + 0.5))
            for group in groups:
                frequency = self._doc_counts[group][token]
                length_norm = 1.0 - _BM25_B + _BM25_B * (
                    self._doc_lengths[group] / self._average_length if self._average_length else 1.0
                )
                scores[group] += idf * (frequency * (_BM25_K1 + 1.0)) / (
                    frequency + _BM25_K1 * length_norm
                )
        return dict(scores)

    def centroids(self, provider: EmbeddingProvider) -> dict[str, list[float]]:
        key = id(provider)
        cached = self._centroids.get(key)
        if cached is not None:
            return cached
        centroids: dict[str, list[float]] = {}
        for group, members in self.groups.items():
            vectors = provider.embed([_embedding_text(definition) for definition in members])
            dimensions = len(vectors[0])
            centroid = [0.0] * dimensions
            for vector in vectors:
                for index in range(dimensions):
                    centroid[index] += vector[index]
            centroids[group] = [value / len(vectors) for value in centroid]
        self._centroids[key] = centroids
        return centroids

    def union_registry(self, selected: tuple[str, ...]) -> ResourceRegistry:
        key = tuple(sorted(selected))
        cached = self._unions.get(key)
        if cached is not None:
            return cached
        registry = ResourceRegistry()
        for group in key:
            registry.extend(self.groups.get(group, ()))
        self._unions[key] = registry
        return registry


def _kmeans(vectors: list[list[float]], k: int, *, iterations: int, seed: int) -> list[int]:
    """Deterministic k-means. numpy path when importable, else pure Python."""

    rng = random.Random(seed)
    initial = rng.sample(range(len(vectors)), k)
    try:
        import numpy  # type: ignore[import-not-found]  # Optional vectorization dependency.
    except ImportError:
        return _kmeans_pure(vectors, k, initial, iterations)

    data = numpy.asarray(vectors, dtype=numpy.float64)
    centers = data[initial].copy()
    assignments = numpy.zeros(len(vectors), dtype=numpy.int64)
    for _ in range(iterations):
        # Squared euclidean distance to every center, argmin per row.
        distances = ((data[:, None, :] - centers[None, :, :]) ** 2).sum(axis=2)
        new_assignments = distances.argmin(axis=1)
        if (new_assignments == assignments).all():
            assignments = new_assignments
            break
        assignments = new_assignments
        for cluster in range(k):
            members = data[assignments == cluster]
            if len(members):
                centers[cluster] = members.mean(axis=0)
    return [int(value) for value in assignments]


def _kmeans_pure(vectors: list[list[float]], k: int, initial: list[int], iterations: int) -> list[int]:
    centers = [list(vectors[index]) for index in initial]
    assignments = [0] * len(vectors)
    for _ in range(iterations):
        changed = False
        for index, vector in enumerate(vectors):
            best_cluster = 0
            best_distance = math.inf
            for cluster, center in enumerate(centers):
                distance = sum((a - b) ** 2 for a, b in zip(vector, center))
                if distance < best_distance:
                    best_distance = distance
                    best_cluster = cluster
            if assignments[index] != best_cluster:
                assignments[index] = best_cluster
                changed = True
        if not changed:
            break
        totals = [[0.0] * len(vectors[0]) for _ in range(k)]
        counts = [0] * k
        for index, vector in enumerate(vectors):
            cluster = assignments[index]
            counts[cluster] += 1
            for dimension, value in enumerate(vector):
                totals[cluster][dimension] += value
        for cluster in range(k):
            if counts[cluster]:
                centers[cluster] = [value / counts[cluster] for value in totals[cluster]]
    return assignments
