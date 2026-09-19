"""Zero-dependency indexed lexical retriever for Marmo-Core.

v1 shipped a ``difflib.SequenceMatcher`` scan over every resource, which is
O(corpus text) per query and degrades to seconds at 1,000 resources. This
module replaces it with an inverted index and BM25 ranking built entirely on
the standard library. The composite score (permissions, trust, side effects,
latency, cost, success history) is unchanged; only the text-relevance
component is computed differently.

Two properties of that component are load-bearing for everything downstream:

- **It is absolute, not rank-normalized.** The score a resource gets does not
  depend on what else the query happened to match, so a threshold means the
  same thing for every query. Normalizing by the best score in the result set
  made the top hit of *any* query look like a strong match, which left the set
  selector's abstain gate (§15.6) with nothing to threshold on. The yardstick
  is a per-query constant, so it would preserve the ranking exactly were it
  not for the clamp at 1.0: documents that beat the reference tie there, and
  on the 120-scenario benchmark that costs two scenarios at rank 1 (hit@1
  66.7% -> 65.0%, MRR 0.702 -> 0.694) while hit@5 and recall@20/@50 are
  unchanged. That is the price of a gate that can say no.
- **It is field-weighted.** Metadata a resource declares about itself (id,
  name, description, capabilities, tags) outranks the body of an attached
  document, so a 7,000-token SKILL.md cannot beat a purpose-built Tool on
  words its examples mention in passing.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections import defaultdict
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

# How much a term occurrence in an attached document body (the text of a
# SKILL.md) counts relative to the same term in the declared metadata head.
# Bodies are one to three orders of magnitude longer than the head -- in the
# bundled corpus, 667 tokens against 34 -- so counting both alike let a skill
# win on words its examples merely mention, over a Tool whose name and
# description are the task. Applied to the term frequency, the document
# length, and the coverage fraction alike, so the field stays a discounted
# member of the same BM25 model rather than a separate bolted-on score.
BODY_FIELD_WEIGHT = 0.25


class Retriever(ABC):
    """Retriever interface (F-RETR-01). Implementations are swappable."""

    @abstractmethod
    def search(self, registry: ResourceRegistry, query: SearchQuery) -> list[SearchResult]:
        """Return ranked search results for the query."""


class _Bm25Index:
    """Inverted index with BM25F statistics over one registry snapshot.

    Each resource is indexed as two fields: the metadata *head* it declares
    about itself, and the *body* of an attached document (a Markdown skill's
    SKILL.md). Body occurrences enter the term frequency and the document
    length discounted by ``BODY_FIELD_WEIGHT``, which is what keeps long
    documents from outranking resources whose declared purpose is the task.
    """

    def __init__(self, definitions: list[ResourceDefinition]) -> None:
        self.definitions = definitions
        self.doc_count = len(definitions)
        self.doc_index_by_identity = {
            definition.identity: doc_index for doc_index, definition in enumerate(definitions)
        }
        self.postings: dict[str, list[tuple[int, float]]] = defaultdict(list)
        self.doc_lengths: list[float] = []
        self.doc_token_sets: list[frozenset[str]] = []
        self.head_token_sets: list[frozenset[str]] = []
        self.name_texts: list[str] = []
        self._normalized_texts: list[str] | None = None
        total_length = 0.0
        for doc_index, definition in enumerate(definitions):
            head_text, body_text = _resource_search_fields(definition)
            head_tokens = _tokens(head_text)
            body_tokens = _tokens(body_text) if body_text else []
            counts: dict[str, float] = {}
            for token in head_tokens:
                counts[token] = counts.get(token, 0.0) + 1.0
            for token in body_tokens:
                counts[token] = counts.get(token, 0.0) + BODY_FIELD_WEIGHT
            length = len(head_tokens) + BODY_FIELD_WEIGHT * len(body_tokens)
            total_length += length
            self.doc_lengths.append(length)
            self.head_token_sets.append(frozenset(head_tokens))
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

    def refresh(self, definitions: list[ResourceDefinition]) -> None:
        """Adopt definition objects whose searchable text is unchanged.

        ``ExecutionEvaluator.apply`` rewrites ``stats`` on every resource it
        has observed. That leaves every indexed token identical but makes the
        definitions held here stale, and the composite score reads ``stats``
        off them. Swapping the list keeps the tokenization -- the part that
        costs a second at 1,000 resources -- and keeps the scores current.
        """

        self.definitions = definitions
        self._normalized_texts = None

    def normalized_text(self, doc_index: int) -> str:
        """Normalized full text of one document, tokenized once per index.

        Only the keyword substring filter needs this, so it is built on first
        use rather than for every index.
        """

        if self._normalized_texts is None:
            self._normalized_texts = [
                _normalize(_resource_search_text(definition)) for definition in self.definitions
            ]
        return self._normalized_texts[doc_index]

    def idf(self, token: str) -> float:
        document_frequency = len(self.postings.get(token, ()))
        if not document_frequency:
            return 0.0
        return self._idf(document_frequency)

    def _idf(self, document_frequency: float) -> float:
        return math.log(
            1.0 + (self.doc_count - document_frequency + 0.5) / (document_frequency + 0.5)
        )

    def reference_score(self, query_tokens: Iterable[str]) -> float:
        """BM25 of a document that names every query term once.

        The yardstick the relevance component is measured against. At
        ``frequency = 1`` and average length the BM25 term reduces to the
        term's ``idf``, so the reference is the query's summed idf: it
        depends on the query alone, never on the rest of the result set,
        which is what lets one threshold mean the same thing for every query
        — and what makes a coincidence on one term of a ten-term goal score
        as the coincidence it is instead of as the best answer available.

        A document that repeats the query's terms can exceed the reference,
        so the ratio is clamped; relevance 1.0 reads as "covers the whole
        query", not as "the best of whatever turned up".

        The yardstick is only as informative as the catalog's vocabulary.
        Terms the corpus has never seen add nothing to it, so a goal whose
        words are almost all absent is measured against the handful that are
        present, and a small catalog can still score an unrelated goal
        highly. Charging absent terms a full idf instead was measured and
        rejected: it ties the scale to catalog size and costs real set
        selection quality (Set F1 0.58 → 0.48 on the 28-scenario set
        benchmark) for scores that no longer transfer between catalogs. The
        abstain floor is therefore a deployment setting, measured against
        real resources, and not a library default.
        """

        return sum(self.idf(token) for token in set(query_tokens))

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
    registry's *content* revision, so writing execution stats back does not
    throw the tokenization away), and repeated searches cost milliseconds
    even at thousands of resources.
    """

    def __init__(self) -> None:
        self._index_cache: WeakKeyDictionary[
            ResourceRegistry, tuple[int, int, _Bm25Index]
        ] = WeakKeyDictionary()

    def search(self, registry: ResourceRegistry, query: SearchQuery) -> list[SearchResult]:
        self._validate_query(query)
        index = self._index_for(registry)
        task_tokens = [token for token in _tokens(query.task)]
        keyword_tokens = set(token for keyword in query.keywords for token in _tokens(keyword))

        if task_tokens:
            bm25 = index.bm25_scores(task_tokens)
            reference_bm25 = index.reference_score(task_tokens)
            candidate_indices: Iterable[int] = bm25.keys()
        else:
            bm25 = {}
            reference_bm25 = 0.0
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
                reference_bm25=reference_bm25,
            )
            if result.score >= query.min_score:
                scored.append(result)
        scored.sort(
            key=lambda item: (item.score, item.resource.metadata.trust_level != "untrusted", item.resource.metadata.id),
            reverse=True,
        )
        return self.apply_limits(scored, query)

    # -- index management ------------------------------------------------------

    def _index_for(self, registry: ResourceRegistry) -> _Bm25Index:
        """The cached index for this registry, rebuilt only when its text changed.

        Two counters, because they answer different questions: the content
        revision says whether the indexed *text* moved (rebuild), and the
        plain revision says whether any resource object was replaced at all
        (adopt the new objects, so the ``success`` component is not scored
        off a stale copy). An execution-stats write bumps only the second.
        """

        cached = self._index_cache.get(registry)
        content_revision = registry.content_revision
        revision = registry.revision
        if cached is not None and cached[0] == content_revision:
            index = cached[2]
            if cached[1] != revision:
                index.refresh(registry.all())
                self._index_cache[registry] = (content_revision, revision, index)
            return index
        index = _Bm25Index(registry.all())
        self._index_cache[registry] = (content_revision, revision, index)
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
                # Substring fallback (a keyword inside a longer word, or one
                # that tokenizes to nothing) reads the index's cached text:
                # re-normalizing every candidate's full document here cost 22x
                # the whole search at 1,000 resources.
                if _normalize(keyword) in index.normalized_text(doc_index):
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
        reference_bm25: float,
    ) -> SearchResult:
        metadata = definition.metadata
        doc_tokens = index.doc_token_sets[doc_index]

        relevance = _relevance(
            bm25_score=bm25_score,
            reference_bm25=reference_bm25,
            task_token_set=task_token_set,
            doc_tokens=doc_tokens,
            head_tokens=index.head_token_sets[doc_index],
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
                    reference_bm25=0.0,
                )
            )
        return results

    def apply_limits(self, results: list[SearchResult], query: SearchQuery) -> list[SearchResult]:
        """Truncate ranked results to ``top_k`` under any per-kind limits.

        Public because the retrievers that wrap this one (hybrid, re-rankers,
        graph expansion) re-rank a widened pool and then have to apply the
        caller's limits to the final order.
        """

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
    reference_bm25: float,
    task_token_set: set[str],
    doc_tokens: frozenset[str],
    head_tokens: frozenset[str],
    normalized_task: str,
    name_text: str,
) -> float:
    if not task_token_set:
        return 0.0
    coverage = _field_coverage(task_token_set, head_tokens, doc_tokens)
    # Against a document that answers the query, not against the best score
    # this query happened to produce: a query the catalog cannot serve has to
    # be allowed to score low, or no threshold downstream means anything.
    # Every candidate of one query is divided by the same constant, so the
    # only ranking the change moves is between documents that beat the
    # reference and tie at the clamp -- two scenarios of 120 at rank 1.
    bm25_norm = min(1.0, bm25_score / reference_bm25) if reference_bm25 > 0 else 0.0
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


def _resource_search_fields(definition: ResourceDefinition) -> tuple[str, str]:
    """The two indexed fields: declared metadata head, attached document body."""

    head = definition.metadata.search_text()
    body = ""
    if definition.extras.get("source_type") == "markdown_skill":
        body = str(definition.extras.get("content", ""))
    return head, body


def _resource_search_text(definition: ResourceDefinition) -> str:
    head, body = _resource_search_fields(definition)
    return f"{head} {body}" if body else head


def _permission_score(required: Iterable[str], granted: Iterable[str]) -> float:
    required_set = set(required)
    if not required_set:
        return 1.0
    granted_set = set(granted)
    covered = len(required_set & granted_set)
    if not granted_set:
        return 0.25
    return covered / len(required_set)


def _field_coverage(
    needles: set[str], head_tokens: frozenset[str], doc_tokens: frozenset[str]
) -> float:
    """Query-term coverage, with body-only matches discounted like the term frequency."""

    if not needles:
        return 0.0
    covered = 0.0
    for token in needles:
        if token in head_tokens:
            covered += 1.0
        elif token in doc_tokens:
            covered += BODY_FIELD_WEIGHT
    return covered / len(needles)


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
