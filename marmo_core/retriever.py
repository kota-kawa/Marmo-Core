"""Zero-dependency indexed lexical retriever for Marmo-Core.

v1 shipped a ``difflib.SequenceMatcher`` scan over every resource, which is
O(corpus text) per query and degrades to seconds at 1,000 resources. This
module replaces it with an inverted index and BM25 ranking built entirely on
the standard library. The composite score (permissions, trust, side effects,
latency, cost, success history) is unchanged; only the text-relevance
component is computed differently.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections import Counter, defaultdict
from typing import Iterable
from weakref import WeakKeyDictionary
import math
import re

from .models import (
    KINDS,
    SIDE_EFFECTS,
    TRUST_LEVELS,
    ResourceDefinition,
    SearchQuery,
    SearchResult,
)
from .registry import ResourceRegistry


_ASCII_TOKEN_RE = re.compile(r"[a-z0-9_./:+-]+")
_CJK_RUN_RE = re.compile(r"[ぁ-んァ-ヶー一-龥]+")
_STOPWORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "for",
    "from",
    "in",
    "into",
    "is",
    "it",
    "its",
    "of",
    "or",
    "the",
    "their",
    "to",
    "with",
}

_TRUST_SCORE = {
    "core": 1.0,
    "verified": 0.85,
    "community": 0.6,
    "untrusted": 0.2,
}

_SIDE_EFFECT_SCORE = {
    "none": 1.0,
    "read": 0.85,
    "write": 0.55,
    "external": 0.4,
    "irreversible": 0.1,
}

_LATENCY_SCORE = {
    "fast": 1.0,
    "medium": 0.7,
    "slow": 0.4,
}

_BM25_K1 = 1.5
_BM25_B = 0.75

# Weight of the text-relevance component in the composite score. Shared with
# the hybrid retriever, which swaps blended relevance into the same slot.
RELEVANCE_WEIGHT = 0.45


class Retriever(ABC):
    """Retriever interface (F-RETR-01). Implementations are swappable."""

    @abstractmethod
    def search(self, registry: ResourceRegistry, query: SearchQuery) -> list[SearchResult]:
        """Return ranked search results for the query."""


class _Bm25Index:
    """Inverted index with BM25 statistics over one registry snapshot."""

    def __init__(self, definitions: list[ResourceDefinition]) -> None:
        self.definitions = definitions
        self.doc_count = len(definitions)
        self.doc_index_by_identity = {
            definition.identity: doc_index for doc_index, definition in enumerate(definitions)
        }
        self.postings: dict[str, list[tuple[int, int]]] = defaultdict(list)
        self.doc_lengths: list[int] = []
        self.doc_token_sets: list[frozenset[str]] = []
        self.name_texts: list[str] = []
        total_length = 0
        for doc_index, definition in enumerate(definitions):
            tokens = _tokens(_resource_search_text(definition))
            counts = Counter(tokens)
            length = len(tokens)
            total_length += length
            self.doc_lengths.append(length)
            self.doc_token_sets.append(frozenset(counts))
            self.name_texts.append(
                _normalize(
                    " ".join(
                        (
                            definition.metadata.id,
                            definition.metadata.name,
                            " ".join(definition.metadata.tags),
                        )
                    )
                )
            )
            for token, frequency in counts.items():
                self.postings[token].append((doc_index, frequency))
        self.average_length = (total_length / self.doc_count) if self.doc_count else 0.0

    def idf(self, token: str) -> float:
        document_frequency = len(self.postings.get(token, ()))
        if not document_frequency:
            return 0.0
        return math.log(1.0 + (self.doc_count - document_frequency + 0.5) / (document_frequency + 0.5))

    def bm25_scores(self, query_tokens: Iterable[str]) -> dict[int, float]:
        """BM25 over documents containing at least one query token."""

        scores: dict[int, float] = defaultdict(float)
        for token in set(query_tokens):
            postings = self.postings.get(token)
            if not postings:
                continue
            idf = self.idf(token)
            for doc_index, frequency in postings:
                length_norm = 1.0 - _BM25_B + _BM25_B * (
                    self.doc_lengths[doc_index] / self.average_length if self.average_length else 1.0
                )
                scores[doc_index] += idf * (frequency * (_BM25_K1 + 1.0)) / (frequency + _BM25_K1 * length_norm)
        return dict(scores)


class LexicalRetriever(Retriever):
    """Search resources using lightweight metadata, an inverted index, and BM25.

    The index is built once per registry snapshot (invalidated by the
    registry revision counter), so repeated searches cost milliseconds even
    at thousands of resources.
    """

    def __init__(self) -> None:
        self._index_cache: WeakKeyDictionary[ResourceRegistry, tuple[int, _Bm25Index]] = WeakKeyDictionary()

    def search(self, registry: ResourceRegistry, query: SearchQuery) -> list[SearchResult]:
        self._validate_query(query)
        index = self._index_for(registry)
        task_tokens = [token for token in _tokens(query.task)]
        keyword_tokens = set(token for keyword in query.keywords for token in _tokens(keyword))

        if task_tokens:
            bm25 = index.bm25_scores(task_tokens)
            max_bm25 = max(bm25.values(), default=0.0)
            candidate_indices: Iterable[int] = bm25.keys()
        else:
            bm25 = {}
            max_bm25 = 0.0
            candidate_indices = range(index.doc_count)

        task_token_set = set(task_tokens)
        normalized_task = _normalize(query.task)
        scored: list[SearchResult] = []
        for doc_index in candidate_indices:
            definition = index.definitions[doc_index]
            if not self._passes_filters(definition, index, doc_index, query):
                continue
            result = self._score(
                definition=definition,
                index=index,
                doc_index=doc_index,
                query=query,
                task_token_set=task_token_set,
                keyword_tokens=keyword_tokens,
                normalized_task=normalized_task,
                bm25_score=bm25.get(doc_index, 0.0),
                max_bm25=max_bm25,
            )
            if result.score >= query.min_score:
                scored.append(result)
        scored.sort(
            key=lambda item: (item.score, item.resource.metadata.trust_level != "untrusted", item.resource.metadata.id),
            reverse=True,
        )
        return self._apply_limits(scored, query)

    # -- index management ------------------------------------------------------

    def _index_for(self, registry: ResourceRegistry) -> _Bm25Index:
        cached = self._index_cache.get(registry)
        revision = registry.revision
        if cached is not None and cached[0] == revision:
            return cached[1]
        index = _Bm25Index(registry.all())
        self._index_cache[registry] = (revision, index)
        return index

    # -- validation and filtering ----------------------------------------------

    def _validate_query(self, query: SearchQuery) -> None:
        invalid_kinds = set(query.kinds) - set(KINDS)
        if invalid_kinds:
            raise ValueError(f"invalid kind filter: {', '.join(sorted(invalid_kinds))}")
        invalid_trust = set(query.trust_levels) - set(TRUST_LEVELS)
        if invalid_trust:
            raise ValueError(f"invalid trust_level filter: {', '.join(sorted(invalid_trust))}")
        invalid_side = set(query.side_effects) - set(SIDE_EFFECTS)
        if invalid_side:
            raise ValueError(f"invalid side_effect filter: {', '.join(sorted(invalid_side))}")
        if query.top_k < 1:
            raise ValueError("top_k must be >= 1")
        for kind, limit in query.per_kind_limits.items():
            if kind not in KINDS:
                raise ValueError(f"invalid per-kind limit kind: {kind}")
            if limit < 0:
                raise ValueError(f"per-kind limit for {kind} must be >= 0")

    def _passes_filters(
        self,
        definition: ResourceDefinition,
        index: _Bm25Index,
        doc_index: int,
        query: SearchQuery,
    ) -> bool:
        metadata = definition.metadata
        if query.kinds and metadata.kind not in query.kinds:
            return False
        if query.trust_levels and metadata.trust_level not in query.trust_levels:
            return False
        if query.side_effects and metadata.side_effect not in query.side_effects:
            return False
        if query.keywords:
            doc_tokens = index.doc_token_sets[doc_index]
            for keyword in query.keywords:
                keyword_parts = _tokens(keyword)
                if keyword_parts and all(part in doc_tokens for part in keyword_parts):
                    continue
                if _normalize(keyword) in _normalize(_resource_search_text(definition)):
                    continue
                return False
        tag_set = set(metadata.tags)
        if query.tags and not set(query.tags).issubset(tag_set):
            return False
        if query.require_permissions:
            granted = set(query.granted_permissions)
            if not set(metadata.required_permissions).issubset(granted):
                return False
        return True

    # -- scoring -----------------------------------------------------------------

    def _score(
        self,
        *,
        definition: ResourceDefinition,
        index: _Bm25Index,
        doc_index: int,
        query: SearchQuery,
        task_token_set: set[str],
        keyword_tokens: set[str],
        normalized_task: str,
        bm25_score: float,
        max_bm25: float,
    ) -> SearchResult:
        metadata = definition.metadata
        doc_tokens = index.doc_token_sets[doc_index]

        relevance = _relevance(
            bm25_score=bm25_score,
            max_bm25=max_bm25,
            task_token_set=task_token_set,
            doc_tokens=doc_tokens,
            normalized_task=normalized_task,
            name_text=index.name_texts[doc_index],
        )
        keyword_score = _coverage(keyword_tokens, doc_tokens) if keyword_tokens else 0.0
        tag_score = _coverage(set(query.tags), set(metadata.tags)) if query.tags else 0.0
        filter_match = max(keyword_score, tag_score)
        permission_score = _permission_score(metadata.required_permissions, query.granted_permissions)
        trust_score = _TRUST_SCORE.get(metadata.trust_level, 0.0)
        side_score = _SIDE_EFFECT_SCORE.get(metadata.side_effect, 0.0)
        latency_score = _LATENCY_SCORE.get(metadata.latency_class, 0.0)
        cost_score = 1.0 / (1.0 + max(metadata.cost_estimate, 0.0))
        success_score = metadata.stats.success_rate if metadata.stats.success_rate is not None else 0.5

        if not query.task and not query.keywords and not query.tags:
            relevance = 0.25

        score = (
            RELEVANCE_WEIGHT * relevance
            + 0.12 * filter_match
            + 0.10 * permission_score
            + 0.10 * trust_score
            + 0.08 * side_score
            + 0.05 * latency_score
            + 0.05 * cost_score
            + 0.05 * success_score
        )
        score = max(0.0, min(1.0, score))
        components = {
            "relevance": relevance,
            "filter_match": filter_match,
            "permission_fit": permission_score,
            "trust": trust_score,
            "side_effect": side_score,
            "latency": latency_score,
            "cost": cost_score,
            "success": success_score,
        }
        reasons = tuple(
            _build_reasons(
                metadata=metadata,
                query=query,
                task_tokens=task_token_set,
                haystack_tokens=doc_tokens,
                components=components,
            )
        )
        return SearchResult(definition, score, reasons, components)

    def score_semantic_candidates(
        self,
        registry: ResourceRegistry,
        query: SearchQuery,
        identities: Iterable[str],
    ) -> list[SearchResult]:
        """Score resources that share no token with the query (BM25 relevance 0).

        Hybrid retrievers use this to pool embedding-nearest documents the
        inverted index cannot surface (true paraphrases with zero lexical
        overlap). Query filters still apply; ranking is left to the caller.
        """

        self._validate_query(query)
        index = self._index_for(registry)
        task_token_set = set(_tokens(query.task))
        keyword_tokens = set(token for keyword in query.keywords for token in _tokens(keyword))
        normalized_task = _normalize(query.task)
        results: list[SearchResult] = []
        for identity in identities:
            doc_index = index.doc_index_by_identity.get(identity)
            if doc_index is None:
                continue
            definition = index.definitions[doc_index]
            if not self._passes_filters(definition, index, doc_index, query):
                continue
            results.append(
                self._score(
                    definition=definition,
                    index=index,
                    doc_index=doc_index,
                    query=query,
                    task_token_set=task_token_set,
                    keyword_tokens=keyword_tokens,
                    normalized_task=normalized_task,
                    bm25_score=0.0,
                    max_bm25=1.0,
                )
            )
        return results

    def _apply_limits(self, results: list[SearchResult], query: SearchQuery) -> list[SearchResult]:
        if not query.per_kind_limits:
            return results[: query.top_k]
        counts: dict[str, int] = defaultdict(int)
        limited: list[SearchResult] = []
        for result in results:
            kind = result.resource.metadata.kind
            limit = query.per_kind_limits.get(kind)
            if limit is not None and counts[kind] >= limit:
                continue
            counts[kind] += 1
            limited.append(result)
            if len(limited) >= query.top_k:
                break
        return limited


def _relevance(
    *,
    bm25_score: float,
    max_bm25: float,
    task_token_set: set[str],
    doc_tokens: frozenset[str],
    normalized_task: str,
    name_text: str,
) -> float:
    if not task_token_set:
        return 0.0
    coverage = _coverage(task_token_set, doc_tokens)
    bm25_norm = (bm25_score / max_bm25) if max_bm25 > 0 else 0.0
    # BM25 carries term rarity (a match on "okr" outranks matches on common
    # words); coverage keeps multi-facet queries honest.
    relevance = bm25_norm * (0.6 + 0.4 * coverage)
    if normalized_task and (normalized_task in name_text or name_text in normalized_task):
        relevance = max(relevance, 0.95)
    return max(0.0, min(1.0, relevance))


def _build_reasons(
    *,
    metadata,
    query: SearchQuery,
    task_tokens: set[str],
    haystack_tokens: frozenset[str],
    components: dict[str, float],
) -> Iterable[str]:
    matches = sorted(task_tokens & haystack_tokens)[:6]
    if matches:
        yield "matched task terms: " + ", ".join(matches)
    if query.keywords:
        yield "matched required keywords"
    if query.tags:
        yield "matched required tags: " + ", ".join(query.tags)
    if metadata.required_permissions:
        missing = set(metadata.required_permissions) - set(query.granted_permissions)
        if missing:
            yield "missing permissions unless granted: " + ", ".join(sorted(missing))
        else:
            yield "required permissions are covered"
    else:
        yield "requires no permissions"
    yield f"trust={metadata.trust_level}"
    yield f"side_effect={metadata.side_effect}"
    if components["relevance"] >= 0.45:
        yield "high metadata relevance"


def _resource_search_text(definition: ResourceDefinition) -> str:
    text = definition.metadata.search_text()
    if definition.extras.get("source_type") == "markdown_skill":
        text += " " + str(definition.extras.get("content", ""))
    return text


def _permission_score(required: Iterable[str], granted: Iterable[str]) -> float:
    required_set = set(required)
    if not required_set:
        return 1.0
    granted_set = set(granted)
    covered = len(required_set & granted_set)
    if not granted_set:
        return 0.25
    return covered / len(required_set)


def _coverage(needles: set[str], haystack: Iterable[str]) -> float:
    if not needles:
        return 0.0
    haystack_set = haystack if isinstance(haystack, (set, frozenset)) else set(haystack)
    if not haystack_set:
        return 0.0
    return len(needles & haystack_set) / len(needles)


def _tokens(value: str) -> list[str]:
    """ASCII word tokens plus CJK bigrams, shared by documents and queries."""

    normalized = _normalize(value)
    tokens = [token for token in _ASCII_TOKEN_RE.findall(normalized) if token not in _STOPWORDS]
    for run in _CJK_RUN_RE.findall(normalized):
        if len(run) == 1:
            tokens.append(run)
        else:
            tokens.extend(run[index : index + 2] for index in range(len(run) - 1))
    return tokens


def _normalize(value: str) -> str:
    return re.sub(r"\s+", " ", value.casefold()).strip()
