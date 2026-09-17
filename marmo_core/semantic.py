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
import urllib.error
import urllib.request

from ._version import __version__
from .environment import load_local_dotenv, optional_environment, required_environment
from .errors import ProviderError, ProviderHTTPError
from .models import SearchQuery, SearchResult
from .registry import ResourceRegistry
from .retriever import (
    RELEVANCE_WEIGHT,
    LexicalRetriever,
    Retriever,
    _resource_search_text,
    _tokens,
)
from .secrets import redact_credentials

_EMBED_TEXT_LIMIT = 4000
_DEFAULT_BATCH_SIZE = 64

USER_AGENT = f"marmo-core/{__version__}"

# Lives here rather than in ``providers`` because this module is imported *by*
# ``providers``; both OpenAI-compatible clients resolve their endpoint the same
# way, so the literal must have exactly one home.
DEFAULT_OPENAI_BASE_URL = "https://api.openai.com/v1"

MISSING_API_KEY_HINT = (
    "no API key was sent: {variable} is empty (unset in the environment and .env) — "
    "set it, or point the provider at a server that needs no key"
)

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

    ``base_url`` resolves exactly like ``OpenAICompatibleLLMProvider``'s:
    the explicit argument wins, then ``OPENAI_BASE_URL`` from the environment
    or ``.env``, then the OpenAI endpoint. Defaulting to OpenAI regardless of
    the configured endpoint would send a non-OpenAI key (Groq, vLLM, an
    on-prem gateway) to ``api.openai.com``.
    """

    def __init__(
        self,
        model: str | None = None,
        *,
        api_key: str | None = None,
        base_url: str | None = None,
        timeout: float = 30.0,
        batch_size: int = _DEFAULT_BATCH_SIZE,
        transport: Callable[[str, dict, dict, float], dict] | None = None,
    ) -> None:
        self.model = model if model is not None else required_environment("OPENAI_EMBEDDING_MODEL")
        if api_key is None or base_url is None:
            load_local_dotenv()
        self.api_key = api_key if api_key is not None else os.environ.get("OPENAI_API_KEY", "")
        if base_url is None:
            base_url = optional_environment("OPENAI_BASE_URL") or DEFAULT_OPENAI_BASE_URL
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
            try:
                response = self.transport(f"{self.base_url}/embeddings", payload, headers, self.timeout)
            except ProviderHTTPError as error:
                raise with_missing_api_key_hint(error, self.api_key) from None
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
    # Some API gateways (Groq's Cloudflare front, for one) reject urllib's
    # default ``Python-urllib/x.y`` agent with a 403, so identify the client.
    request_headers = {"User-Agent": USER_AGENT, **headers}
    request = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers=request_headers,
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        # Error bodies echo the rejected credential (OpenAI's 401 returns a
        # partially masked key) and the CLI prints them to stderr, so redact
        # at this boundary — every caller of both providers benefits (F-SEC-06).
        body = redact_credentials(exc.read().decode("utf-8", errors="replace"))
        exc.close()
        safe_url = redact_credentials(url)
        raise ProviderHTTPError(
            message=f"HTTP {exc.code} from {safe_url}: {provider_error_message(body) or exc.reason}",
            status=int(exc.code),
            body=body,
            url=safe_url,
        ) from None
    except urllib.error.URLError as exc:
        raise ProviderError(message=f"cannot reach {redact_credentials(url)}: {exc.reason}") from None


def with_missing_api_key_hint(
    error: ProviderHTTPError, api_key: str, variable: str = "OPENAI_API_KEY"
) -> ProviderHTTPError:
    """Explain an auth rejection that an unset API key accounts for.

    Sending no ``Authorization`` header is deliberate (local servers such as
    Ollama and vLLM need no key), so an empty key is never an error by itself.
    It only becomes the likely explanation once the server answers 401/403, and
    the server's own status and message are kept alongside the hint.
    """

    if api_key or error.status not in (401, 403):
        return error
    return ProviderHTTPError(
        message=f"{error.message} ({MISSING_API_KEY_HINT.format(variable=variable)})",
        status=error.status,
        body=error.body,
        url=error.url,
    )


def provider_error_message(body: str) -> str:
    """Extract the human-readable message from a provider error body when present."""

    try:
        parsed = json.loads(body)
    except (TypeError, ValueError):
        return body.strip()[:500]
    error = parsed.get("error") if isinstance(parsed, dict) else None
    if isinstance(error, dict):
        return str(error.get("message") or "").strip() or json.dumps(error)[:500]
    if isinstance(error, str):
        return error
    return body.strip()[:500]
