"""Semantic retrieval layer: embedding interface and hybrid ranking.

``EmbeddingProvider`` is the swap point (F-RETR-02):
``HashingEmbeddingProvider`` is a deterministic offline stand-in for tests
and air-gapped runs, and ``OpenAICompatibleEmbeddingProvider`` talks to any
OpenAI-compatible ``/embeddings`` endpoint (OpenAI, vLLM, llama.cpp server,
Ollama) using only ``urllib``. Real semantic quality requires a real
embedding model; the hashing provider only mirrors lexical overlap in vector
form.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import replace
from typing import Callable, Sequence
from weakref import WeakKeyDictionary
import hashlib
import json
import math
import os
import urllib.request

from .environment import load_local_dotenv
from .models import SearchQuery, SearchResult
from .registry import ResourceRegistry
from .retriever import (
    RELEVANCE_WEIGHT,
    LexicalRetriever,
    Retriever,
    _resource_search_text,
    _tokens,
)

_EMBED_TEXT_LIMIT = 4000
_DEFAULT_BATCH_SIZE = 64


class EmbeddingProvider(ABC):
    """Text embedding interface. Implementations are swappable plugins."""

    @abstractmethod
    def embed(self, texts: Sequence[str]) -> list[list[float]]:
        """Return one vector per input text. All vectors share one dimension."""


class HashingEmbeddingProvider(EmbeddingProvider):
    """Deterministic zero-dependency embeddings via token feature hashing.

    Useful for tests, replay, and offline demos. It cannot capture synonyms
    or paraphrase; production semantic search needs a model-backed provider.
    """

    def __init__(self, dimensions: int = 512) -> None:
        if dimensions < 8:
            raise ValueError("dimensions must be >= 8")
        self.dimensions = dimensions

    def embed(self, texts: Sequence[str]) -> list[list[float]]:
        return [self._embed_one(text) for text in texts]

    def _embed_one(self, text: str) -> list[float]:
        vector = [0.0] * self.dimensions
        for token in _tokens(text):
            digest = hashlib.blake2b(token.encode("utf-8"), digest_size=8).digest()
            bucket = int.from_bytes(digest[:4], "big") % self.dimensions
            sign = 1.0 if digest[4] % 2 == 0 else -1.0
            vector[bucket] += sign
        norm = math.sqrt(sum(value * value for value in vector))
        if norm == 0.0:
            return vector
        return [value / norm for value in vector]


class OpenAICompatibleEmbeddingProvider(EmbeddingProvider):
    """Embeddings from any OpenAI-compatible ``/embeddings`` endpoint.

    Requests go through ``urllib``. The ``transport`` argument accepts a
    ``(url, payload, headers, timeout) -> dict`` callable so tests can run
    offline.
    """

    def __init__(
        self,
        model: str = "text-embedding-3-small",
        *,
        api_key: str | None = None,
        base_url: str = "https://api.openai.com/v1",
        timeout: float = 30.0,
        batch_size: int = _DEFAULT_BATCH_SIZE,
        transport: Callable[[str, dict, dict, float], dict] | None = None,
    ) -> None:
        self.model = model
        if api_key is None:
            load_local_dotenv()
        self.api_key = api_key if api_key is not None else os.environ.get("OPENAI_API_KEY", "")
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.batch_size = max(1, batch_size)
        self.transport = transport or _post_json

    def embed(self, texts: Sequence[str]) -> list[list[float]]:
        vectors: list[list[float]] = []
        for start in range(0, len(texts), self.batch_size):
            batch = list(texts[start : start + self.batch_size])
            payload = {"model": self.model, "input": batch}
            headers = {"Content-Type": "application/json"}
            if self.api_key:
                headers["Authorization"] = f"Bearer {self.api_key}"
            response = self.transport(f"{self.base_url}/embeddings", payload, headers, self.timeout)
            data = response.get("data")
            if not isinstance(data, list) or len(data) != len(batch):
                raise ValueError("embedding endpoint returned an unexpected payload shape")
            ordered = sorted(data, key=lambda item: item.get("index", 0))
            vectors.extend([list(map(float, item["embedding"])) for item in ordered])
        return vectors


class HybridRetriever(Retriever):
    """Union of BM25 and embedding-nearest candidates, re-ranked together.

    Lexical retrieval proposes a widened candidate pool, and the
    embedding-nearest documents it missed are pooled alongside it — a BM25-only
    pool caps recall at whatever the inverted index can surface, which loses
    true paraphrases with zero lexical overlap. The relevance component of
    every candidate is then blended: ``(1 - weight) * lexical + weight *
    semantic``. All other composite components (permissions, trust, side
    effects, cost, success history) are unchanged, so policy-aware ranking is
    preserved. Document embeddings are cached per registry revision.
    """

    def __init__(
        self,
        embedding_provider: EmbeddingProvider,
        *,
        lexical: LexicalRetriever | None = None,
        semantic_weight: float = 0.5,
        candidate_pool: int = 50,
    ) -> None:
        if not 0.0 <= semantic_weight <= 1.0:
            raise ValueError("semantic_weight must be between 0.0 and 1.0")
        self.embedding_provider = embedding_provider
        self.lexical = lexical or LexicalRetriever()
        self.semantic_weight = semantic_weight
        self.candidate_pool = max(1, candidate_pool)
        self._vector_cache: WeakKeyDictionary[ResourceRegistry, tuple[int, dict[str, list[float]]]] = (
            WeakKeyDictionary()
        )

    def search(self, registry: ResourceRegistry, query: SearchQuery) -> list[SearchResult]:
        if not query.task.strip() or self.semantic_weight == 0.0:
            return self.lexical.search(registry, query)
        widened = replace(
            query,
            top_k=max(query.top_k, self.candidate_pool),
            per_kind_limits={},
            min_score=0.0,
        )
        candidates = self.lexical.search(registry, widened)
        vectors = self._vectors_for(registry)
        query_vector = self.embedding_provider.embed([query.task])[0]
        semantic_scores = {
            identity: _cosine_01(query_vector, vector) for identity, vector in vectors.items()
        }
        # The inverted index only surfaces documents sharing at least one
        # token with the task, so pull in the embedding-nearest documents it
        # missed; they enter with zero lexical relevance and compete on the
        # blended score.
        pooled = {result.resource.identity for result in candidates}
        nearest = sorted(
            (identity for identity in semantic_scores if identity not in pooled),
            key=lambda identity: (semantic_scores[identity], identity),
            reverse=True,
        )[: self.candidate_pool]
        candidates += self.lexical.score_semantic_candidates(registry, widened, nearest)
        if not candidates:
            return []
        rescored: list[SearchResult] = []
        for result in candidates:
            identity = result.resource.identity
            semantic = semantic_scores.get(identity, 0.0)
            lexical_relevance = float(result.components.get("relevance", 0.0))
            blended = (1.0 - self.semantic_weight) * lexical_relevance + self.semantic_weight * semantic
            score = max(0.0, min(1.0, result.score + RELEVANCE_WEIGHT * (blended - lexical_relevance)))
            components = dict(result.components)
            components["semantic"] = semantic
            components["relevance"] = blended
            reasons = result.reasons + (f"semantic similarity {semantic:.2f}",)
            rescored.append(SearchResult(result.resource, score, reasons, components))
        rescored.sort(
            key=lambda item: (item.score, item.resource.metadata.trust_level != "untrusted", item.resource.metadata.id),
            reverse=True,
        )
        filtered = [result for result in rescored if result.score >= query.min_score]
        return self.lexical._apply_limits(filtered, query)

    def _vectors_for(self, registry: ResourceRegistry) -> dict[str, list[float]]:
        cached = self._vector_cache.get(registry)
        revision = registry.revision
        if cached is not None and cached[0] == revision:
            return cached[1]
        definitions = registry.all()
        texts = [_embedding_text(definition) for definition in definitions]
        embedded = self.embedding_provider.embed(texts)
        vectors = {definition.identity: vector for definition, vector in zip(definitions, embedded)}
        self._vector_cache[registry] = (revision, vectors)
        return vectors


def _embedding_text(definition) -> str:
    text = _resource_search_text(definition)
    return text[:_EMBED_TEXT_LIMIT]


def _cosine_01(left: Sequence[float], right: Sequence[float]) -> float:
    if len(left) != len(right) or not left:
        return 0.0
    dot = sum(a * b for a, b in zip(left, right))
    left_norm = math.sqrt(sum(a * a for a in left))
    right_norm = math.sqrt(sum(b * b for b in right))
    if left_norm == 0.0 or right_norm == 0.0:
        return 0.0
    cosine = dot / (left_norm * right_norm)
    return max(0.0, min(1.0, (cosine + 1.0) / 2.0)) if cosine < 0 else min(1.0, cosine)


def _post_json(url: str, payload: dict, headers: dict, timeout: float) -> dict:
    request = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers=headers,
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))
