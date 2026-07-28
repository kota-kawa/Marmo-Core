"""Cross-encoder re-ranking: the zero-LLM comparison target (§15.7 項目4).

The LLM re-ranker (``LLMRerankRetriever``, 案C 最小) lifts hit@1 substantially
but costs one LLM call (~2s, non-deterministic, auditable only through a
cache) per query. A cross-encoder asks the same question — "how well does
this resource answer this task?" — with a small local model that reads the
(task, resource metadata) pair jointly, so it can catch the term-level
correspondences a bi-encoder's independent embeddings miss, while staying
deterministic, offline, and free of LLM cost.

``CrossEncoderProvider`` is the swap point that keeps the core
dependency-free, exactly like ``EmbeddingProvider`` in ``semantic.py``: the
benchmark supplies a fastembed/ONNX implementation, and tests supply a
deterministic stub.

``CrossEncoderRerankRetriever`` blends the model's relevance into the same
``relevance`` slot the lexical and hybrid retrievers use, rather than only
permuting the order like the LLM re-ranker does. That choice matters
downstream: the composite score keeps its policy-aware components
(permissions, trust, side effects, cost), and the second-layer selector's
abstain gate — which thresholds the *relevance component* (§15.6) — sees a
re-ranked relevance instead of the first-layer one.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import replace
from typing import Sequence
import math

from .models import SearchQuery, SearchResult
from .registry import ResourceRegistry
from .retriever import RELEVANCE_WEIGHT, LexicalRetriever, Retriever, _resource_search_text

_DOCUMENT_TEXT_LIMIT = 1200


class CrossEncoderProvider(ABC):
    """Joint (query, document) relevance scoring. Implementations are plugins."""

    @abstractmethod
    def score(self, query: str, documents: Sequence[str]) -> list[float]:
        """Return one relevance score per document, higher is more relevant.

        Scores may use any scale (ms-marco models emit unbounded logits);
        the retriever normalizes them before blending.
        """


class CrossEncoderRerankRetriever(Retriever):
    """Re-score an inner retriever's candidate pool with a cross-encoder.

    The inner retriever proposes ``rerank_pool`` candidates (a widened
    search, so the pool is the recall ceiling — a cross-encoder can only
    reorder what the first layer surfaced, the same structural limit the
    LLM re-ranker demonstrated in §15.2 案C). Each candidate's metadata
    text is scored against the task, squashed to [0, 1] with a logistic
    function, and blended into the relevance component:
    ``(1 - weight) * inner_relevance + weight * cross_encoder``.

    ``weight`` defaults to 1.0: the cross-encoder reads the same text the
    inner relevance was computed from, so averaging the two mostly dilutes
    the stronger signal. Lower it to keep first-layer lexical evidence in
    the blend.
    """

    def __init__(
        self,
        provider: CrossEncoderProvider,
        inner: Retriever,
        *,
        rerank_pool: int = 50,
        weight: float = 1.0,
        temperature: float = 1.0,
        lexical: LexicalRetriever | None = None,
    ) -> None:
        if not 0.0 <= weight <= 1.0:
            raise ValueError("weight must be between 0.0 and 1.0")
        if temperature <= 0.0:
            raise ValueError("temperature must be > 0.0")
        self.provider = provider
        self.inner = inner
        self.rerank_pool = max(1, rerank_pool)
        self.weight = weight
        self.temperature = temperature
        self.lexical = lexical or _inner_lexical(inner)

    def search(self, registry: ResourceRegistry, query: SearchQuery) -> list[SearchResult]:
        task = query.task.strip()
        if not task:
            return self.inner.search(registry, query)
        widened = replace(
            query,
            top_k=max(query.top_k, self.rerank_pool),
            per_kind_limits={},
            min_score=0.0,
        )
        candidates = self.inner.search(registry, widened)
        if len(candidates) < 2:
            return candidates[: query.top_k]
        pool = candidates[: self.rerank_pool]
        documents = [_document_text(result) for result in pool]
        raw = self.provider.score(task, documents)
        if len(raw) != len(pool):
            raise ValueError("cross-encoder returned a score count that does not match the pool")

        rescored: list[SearchResult] = []
        for result, raw_score in zip(pool, raw):
            cross = _logistic(raw_score, self.temperature)
            inner_relevance = float(result.components.get("relevance", 0.0))
            blended = (1.0 - self.weight) * inner_relevance + self.weight * cross
            score = max(
                0.0, min(1.0, result.score + RELEVANCE_WEIGHT * (blended - inner_relevance))
            )
            components = dict(result.components)
            components["cross_encoder"] = cross
            components["relevance"] = blended
            reasons = result.reasons + (f"cross-encoder relevance {cross:.2f}",)
            rescored.append(SearchResult(result.resource, score, reasons, components))
        # Candidates beyond the re-ranked pool keep their inner ranking and
        # stay behind it: they were never shown to the cross-encoder, so
        # their scores are not comparable with the re-scored ones.
        rescored.sort(
            key=lambda item: (
                item.score,
                item.resource.metadata.trust_level != "untrusted",
                item.resource.metadata.id,
            ),
            reverse=True,
        )
        ordered = rescored + list(candidates[self.rerank_pool :])
        filtered = [result for result in ordered if result.score >= query.min_score]
        return self.lexical._apply_limits(filtered, query)


def _inner_lexical(inner: Retriever) -> LexicalRetriever:
    """Reuse the inner retriever's lexical helper for per-kind limiting."""

    candidate = getattr(inner, "lexical", None)
    if isinstance(candidate, LexicalRetriever):
        return candidate
    if isinstance(inner, LexicalRetriever):
        return inner
    return LexicalRetriever()


def _document_text(result: SearchResult) -> str:
    return _resource_search_text(result.resource)[:_DOCUMENT_TEXT_LIMIT]


def _logistic(value: float, temperature: float) -> float:
    """Squash an unbounded relevance logit into [0, 1]."""

    scaled = max(-60.0, min(60.0, value / temperature))
    return 1.0 / (1.0 + math.exp(-scaled))
