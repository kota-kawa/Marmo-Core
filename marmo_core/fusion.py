"""Rank fusion of two retrievers (Reciprocal Rank Fusion).

``HybridRetriever`` blends a lexical and a semantic *relevance score*, which
requires the two scales to be comparable. Reciprocal Rank Fusion (Cormack et
al., 2009) is the common alternative that uses only the two *rankings*: a
resource at rank ``r`` in a list contributes ``1 / (k + r)``, and the
contributions of the two lists are summed. It is a standard strong baseline
for combining keyword and embedding search because it needs no score
calibration.
"""

from __future__ import annotations

from dataclasses import replace

from .models import SearchQuery, SearchResult
from .registry import ResourceRegistry
from .retriever import LexicalRetriever, Retriever


class RRFRetriever(Retriever):
    """Fuse the rankings of two retrievers with Reciprocal Rank Fusion.

    Both retrievers are asked for ``depth`` results (the caller's per-kind
    limits and score floor are applied after fusion, not before). The fused
    value is normalized by its maximum, ``2 / (k + 1)`` (rank 1 in both
    lists), and becomes the result's ``score``; it is also exposed as the
    ``rrf`` component. The other components, including ``relevance`` that
    selectors threshold, are those of the first list's result when the
    resource appears there, otherwise the second's — rank fusion produces no
    calibrated relevance of its own.
    """

    def __init__(self, first: Retriever, second: Retriever, *, k: int = 60, depth: int = 100) -> None:
        if k < 1:
            raise ValueError("k must be at least 1")
        if depth < 1:
            raise ValueError("depth must be at least 1")
        self.first = first
        self.second = second
        self.k = k
        self.depth = depth
        self._limits = LexicalRetriever()

    def search(self, registry: ResourceRegistry, query: SearchQuery) -> list[SearchResult]:
        widened = replace(query, top_k=max(query.top_k, self.depth), per_kind_limits={}, min_score=0.0)
        lists = (self.first.search(registry, widened), self.second.search(registry, widened))
        fused: dict[str, float] = {}
        base: dict[str, SearchResult] = {}
        for ranked in lists:
            for rank, result in enumerate(ranked[: self.depth], start=1):
                identity = result.resource.identity
                fused[identity] = fused.get(identity, 0.0) + 1.0 / (self.k + rank)
                base.setdefault(identity, result)
        ceiling = 2.0 / (self.k + 1)
        results: list[SearchResult] = []
        for identity, value in fused.items():
            result = base[identity]
            normalized = value / ceiling
            components = dict(result.components)
            components["rrf"] = normalized
            results.append(
                SearchResult(
                    result.resource,
                    normalized,
                    result.reasons + (f"reciprocal rank fusion {normalized:.3f}",),
                    components,
                )
            )
        results.sort(key=lambda item: (-item.score, item.resource.metadata.id))
        filtered = [result for result in results if result.score >= query.min_score]
        return self._limits.apply_limits(filtered, query)
