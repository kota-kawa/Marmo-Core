"""案F: case-based routing — the routing cache (§15.4 第3層: 適応).

Layers 1 and 2 re-derive a resource set from scratch for every task. 案F
observes that production traffic repeats: store ``(task, chosen set,
outcome)`` as a *case*, and when a new task is close enough to a past
successful one, replay that set and skip retrieval and scoring entirely.
The structure is self-referential by design — the kernel improves its own
routing with the same case-memory mechanism it exposes as a Memory
resource.

    task → nearest admissible case ─ hit ─→ replayed set   (no retrieval)
                                  └ miss ─→ retriever → selector  (案A/B/E/I)

Cold start means the cache is empty and every task misses, so a fallback
pipeline is not optional — ``CaseBasedRouter`` always wraps one.

Four guards decide whether a case may be replayed. Each exists because
skipping the pipeline also skips the safety and freshness properties the
pipeline provided, and each is separately switchable so §15.4's ablations
can measure it:

- **staleness** (``invalidate``): every member must still resolve in the
  registry at the exact ``id@version`` that was cached. §15.4 names registry
  drift as the failure mode of 案F; a revision counter is too coarse (any
  unrelated ``add`` would flush the whole cache), so admission checks
  identities.
- **permission direction**: a ``selected`` case may be replayed only when
  the grants it was recorded under are a subset of today's, and every
  member's ``required_permissions`` are re-verified against *live* metadata
  — the cache is never trusted as a policy oracle (§15.6). An ``abstain`` /
  ``escalate`` case is the mirror image: it may not be replayed once new
  permissions have been granted, because those grants are exactly what
  could make a set feasible.
- **outcome admission** (``store_failures``): by default only cases whose
  execution succeeded are stored, so a wrong set cannot be locked in.
- **outcome eviction**: a replayed case that then fails is dropped, so a
  case that stops working cannot poison the cache indefinitely.

Similarity is IDF-weighted token cosine over cached task statements
(zero-dependency). An optional ``EmbeddingProvider`` blends in cosine over
task embeddings via ``semantic_weight`` — the same swap point 案B uses, and
the one that decides whether the cache generalizes to paraphrases or only
to verbatim repeats.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence
import json
import math
import time

from .errors import ResourceNotFoundError
from .models import (
    ResourceDefinition,
    SearchQuery,
    SearchResult,
    SelectionResult,
    parse_resource_ref,
)
from .registry import ResourceRegistry
from .retriever import Retriever, _tokens
from .selector import SelectionContext, SetSelector
from .semantic import EmbeddingProvider, _cosine_01


@dataclass(frozen=True)
class CaseMember:
    """One resource of a cached set, with the score it was chosen under.

    A cache hit skips the scorer, so the cached scores are the only ones
    available downstream; keeping ``relevance`` separately preserves the
    component the abstain gate thresholds (§15.6).
    """

    resource_id: str
    identity: str
    score: float
    relevance: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "resource_id": self.resource_id,
            "identity": self.identity,
            "score": round(self.score, 6),
            "relevance": round(self.relevance, 6),
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "CaseMember":
        return cls(
            resource_id=str(data["resource_id"]),
            identity=str(data["identity"]),
            score=float(data.get("score", 0.0)),
            relevance=float(data.get("relevance", 0.0)),
        )


@dataclass
class RoutingCase:
    """A past routing decision and how it turned out."""

    task: str
    status: str
    members: tuple[CaseMember, ...] = ()
    granted_permissions: tuple[str, ...] = ()
    reason: str = ""
    success: bool = True
    recorded_at: str = ""
    hits: int = 0

    @property
    def resource_ids(self) -> tuple[str, ...]:
        return tuple(member.resource_id for member in self.members)

    def to_dict(self) -> dict[str, Any]:
        return {
            "task": self.task,
            "status": self.status,
            "members": [member.to_dict() for member in self.members],
            "granted_permissions": list(self.granted_permissions),
            "reason": self.reason,
            "success": self.success,
            "recorded_at": self.recorded_at,
            "hits": self.hits,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "RoutingCase":
        return cls(
            task=str(data["task"]),
            status=str(data.get("status", "selected")),
            members=tuple(CaseMember.from_dict(item) for item in data.get("members", [])),
            granted_permissions=tuple(str(item) for item in data.get("granted_permissions", [])),
            reason=str(data.get("reason", "")),
            success=bool(data.get("success", True)),
            recorded_at=str(data.get("recorded_at", "")),
            hits=int(data.get("hits", 0)),
        )


@dataclass(frozen=True)
class RoutingDecision:
    """Outcome of one routing call, plus where the answer came from."""

    selection: SelectionResult
    source: str  # "cache" | "pipeline"
    task: str = ""
    granted_permissions: tuple[str, ...] = ()
    similarity: float = 0.0
    case: RoutingCase | None = None
    latency_ms: float = 0.0
    miss_reasons: tuple[str, ...] = ()

    @property
    def cached(self) -> bool:
        return self.source == "cache"

    def to_dict(self) -> dict[str, Any]:
        return {
            "source": self.source,
            "task": self.task,
            "similarity": round(self.similarity, 4),
            "latency_ms": round(self.latency_ms, 4),
            "miss_reasons": list(self.miss_reasons),
            "selection": self.selection.to_dict(),
        }


class RoutingCaseStore:
    """Nearest-neighbour store over past routing cases.

    Lexical similarity is IDF-weighted cosine over task tokens, with the IDF
    recomputed from the stored cases themselves (a term shared by every
    cached task carries no discriminative signal). ``semantic_weight``
    blends in embedding cosine when an ``EmbeddingProvider`` is supplied.
    """

    def __init__(
        self,
        cases: Iterable[RoutingCase] = (),
        *,
        embeddings: EmbeddingProvider | None = None,
        semantic_weight: float = 0.0,
        capacity: int | None = None,
    ) -> None:
        if not 0.0 <= semantic_weight <= 1.0:
            raise ValueError("semantic_weight must be between 0.0 and 1.0")
        if semantic_weight > 0.0 and embeddings is None:
            raise ValueError("semantic_weight > 0 requires an EmbeddingProvider")
        self.embeddings = embeddings
        self.semantic_weight = semantic_weight
        self.capacity = capacity
        self._cases: list[RoutingCase] = list(cases)
        self._idf: dict[str, float] = {}
        self._token_sets: list[Counter] = []
        self._vectors: list[list[float]] = []
        self._vector_cache: dict[str, list[float]] = {}
        self._dirty = True

    # -- contents --------------------------------------------------------------

    @property
    def cases(self) -> tuple[RoutingCase, ...]:
        return tuple(self._cases)

    def __len__(self) -> int:
        return len(self._cases)

    def add(self, case: RoutingCase) -> RoutingCase:
        """Store a case, replacing any earlier case for the same task text."""

        for index, existing in enumerate(self._cases):
            if existing.task == case.task:
                case.hits = existing.hits
                self._cases[index] = case
                self._dirty = True
                return case
        self._cases.append(case)
        if self.capacity is not None and len(self._cases) > self.capacity:
            # Evict the least-reused case; ties break toward the oldest.
            victim = min(range(len(self._cases)), key=lambda i: (self._cases[i].hits, i))
            self._cases.pop(victim)
        self._dirty = True
        return case

    def remove(self, case: RoutingCase) -> bool:
        for index, existing in enumerate(self._cases):
            if existing is case or existing.task == case.task:
                self._cases.pop(index)
                self._dirty = True
                return True
        return False

    def prune(self, registry: ResourceRegistry) -> int:
        """Drop cases whose members no longer resolve at the cached identity."""

        keep = [case for case in self._cases if resolve_case(case, registry) is not None]
        dropped = len(self._cases) - len(keep)
        if dropped:
            self._cases = keep
            self._dirty = True
        return dropped

    # -- similarity ------------------------------------------------------------

    def rank(self, task: str, *, limit: int = 5) -> list[tuple[RoutingCase, float]]:
        """Cases most similar to ``task``, highest first."""

        if not self._cases:
            return []
        self._reindex()
        query_counts = Counter(_tokens(task))
        # The query is embedded on every call (a genuinely new task has no
        # cached vector); only case texts are memoized, so the measured hit
        # latency includes the embedding a real deployment would pay.
        query_vector = self._embed([task])[0] if self.semantic_weight > 0.0 else None
        scored: list[tuple[RoutingCase, float]] = []
        for index, case in enumerate(self._cases):
            lexical = _idf_cosine(query_counts, self._token_sets[index], self._idf)
            similarity = lexical
            if query_vector is not None:
                semantic = _cosine_01(query_vector, self._vectors[index])
                similarity = self.semantic_weight * semantic + (1.0 - self.semantic_weight) * lexical
            scored.append((case, similarity))
        scored.sort(key=lambda item: (-item[1], item[0].task))
        return scored[:limit]

    def _reindex(self) -> None:
        if not self._dirty:
            return
        self._token_sets = [Counter(_tokens(case.task)) for case in self._cases]
        total = len(self._cases)
        document_frequency: Counter = Counter()
        for counts in self._token_sets:
            document_frequency.update(counts.keys())
        self._idf = {
            token: math.log((total + 1) / (frequency + 0.5)) + 1.0
            for token, frequency in document_frequency.items()
        }
        if self.semantic_weight > 0.0:
            self._vectors = [self._vector_for(case.task) for case in self._cases]
        self._dirty = False

    def _vector_for(self, text: str) -> list[float]:
        """Embed once per distinct task text and memoize.

        Adding a case marks the store dirty, so without memoization every
        insertion would re-embed the whole cache — quadratic work that would
        also land inside ``route`` and corrupt the very latency measurement
        the cache exists to improve.
        """

        vector = self._vector_cache.get(text)
        if vector is None:
            vector = self._embed([text])[0]
            self._vector_cache[text] = vector
        return vector

    def _embed(self, texts: Sequence[str]) -> list[list[float]]:
        assert self.embeddings is not None  # guarded in __init__
        return self.embeddings.embed(list(texts))

    # -- persistence -----------------------------------------------------------

    def to_dict(self) -> dict[str, Any]:
        return {"version": 1, "cases": [case.to_dict() for case in self._cases]}

    def save(self, path: str | Path) -> None:
        destination = Path(path)
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(
            json.dumps(self.to_dict(), ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )

    def load(self, path: str | Path) -> int:
        source = Path(path)
        if not source.exists():
            return 0
        data = json.loads(source.read_text(encoding="utf-8"))
        self._cases = [RoutingCase.from_dict(item) for item in data.get("cases", [])]
        self._dirty = True
        return len(self._cases)


class CaseBasedRouter:
    """案F router: replay a near-duplicate past decision, else run the pipeline.

    ``threshold`` is the similarity a case must reach to be replayed; below
    it the router falls back to ``retriever`` + ``selector``. Lowering it
    buys hit rate at the risk of replaying a set that does not fit the new
    task. The default is the conservative setting: with a lexical case index
    only near-verbatim repeats hit, which measurably reproduces the
    pipeline's own answer (§15.4, latency-only). A store backed by a real
    embedding model is the case where lowering it pays — around 0.40 a
    paraphrase inherits the set its direct-phrasing sibling proved — but
    that operating point was tuned on one 28-scenario corpus and is not the
    default here.
    """

    def __init__(
        self,
        retriever: Retriever,
        selector: SetSelector,
        *,
        store: RoutingCaseStore | None = None,
        threshold: float = 0.72,
        top_k: int = 50,
        store_failures: bool = False,
        store_negative: bool = True,
        invalidate: bool = True,
        scan_depth: int = 5,
    ) -> None:
        self.retriever = retriever
        self.selector = selector
        self.store = store if store is not None else RoutingCaseStore()
        self.threshold = threshold
        self.top_k = top_k
        self.store_failures = store_failures
        self.store_negative = store_negative
        self.invalidate = invalidate
        self.scan_depth = scan_depth
        self.evictions = 0

    def route(
        self,
        registry: ResourceRegistry,
        task: str,
        *,
        context: SelectionContext,
        query: SearchQuery | None = None,
    ) -> RoutingDecision:
        start = time.perf_counter()
        granted = set(context.granted_permissions)
        miss_reasons: list[str] = []

        for case, similarity in self.store.rank(task, limit=self.scan_depth):
            if similarity < self.threshold:
                miss_reasons.append("below-threshold")
                break
            reason = self._admit(case, registry, granted)
            if reason:
                miss_reasons.append(reason)
                continue
            selection = self._replay(case, registry, similarity)
            case.hits += 1
            return RoutingDecision(
                selection=selection,
                source="cache",
                task=task,
                granted_permissions=tuple(sorted(granted)),
                similarity=similarity,
                case=case,
                latency_ms=(time.perf_counter() - start) * 1000.0,
                miss_reasons=tuple(miss_reasons),
            )

        search_query = query or SearchQuery(
            task=task,
            granted_permissions=tuple(sorted(granted)),
            top_k=self.top_k,
        )
        candidates = self.retriever.search(registry, search_query)
        selection = self.selector.select(candidates, context=context)
        return RoutingDecision(
            selection=selection,
            source="pipeline",
            task=task,
            granted_permissions=tuple(sorted(granted)),
            case=None,
            latency_ms=(time.perf_counter() - start) * 1000.0,
            miss_reasons=tuple(miss_reasons or ["empty-cache"]),
        )

    def record(self, decision: RoutingDecision, *, success: bool) -> RoutingCase | None:
        """Feed an execution outcome back into the cache.

        A pipeline decision becomes a new case (subject to ``store_failures``
        / ``store_negative``); a replayed case that failed is evicted, which
        is what keeps a stale-but-still-resolvable set from being reused
        forever.
        """

        if decision.cached:
            if not success and decision.case is not None:
                self.store.remove(decision.case)
                self.evictions += 1
            return decision.case
        if not success and not self.store_failures:
            return None
        selection = decision.selection
        if selection.status != "selected" and not self.store_negative:
            return None
        members = tuple(
            CaseMember(
                resource_id=result.resource.metadata.id,
                identity=result.resource.identity,
                score=result.score,
                relevance=float(result.components.get("relevance", 0.0)),
            )
            for result in selection.results
        )
        case = RoutingCase(
            task=decision.task,
            status=selection.status,
            members=members,
            granted_permissions=decision.granted_permissions,
            reason=selection.reason,
            success=success,
            recorded_at=_utc_now(),
        )
        return self.store.add(case)

    # -- admission -------------------------------------------------------------

    def _admit(self, case: RoutingCase, registry: ResourceRegistry, granted: set[str]) -> str:
        """Return "" if the case may be replayed, else why it may not."""

        if not case.success:
            return "failed-case"
        cached = set(case.granted_permissions)
        if case.status == "selected":
            if not cached <= granted:
                # Recorded under grants we no longer hold: the set it chose
                # may now be infeasible, and re-deriving is the safe answer.
                return "permission-narrowed"
        elif granted > cached:
            # New grants are exactly what turns an abstain/escalate into a
            # feasible set — replaying the old refusal would hide it.
            return "permission-widened"
        definitions = resolve_case(case, registry, exact=self.invalidate)
        if definitions is None:
            return "stale"
        for definition in definitions:
            if not set(definition.metadata.required_permissions) <= granted:
                return "infeasible"
        return ""

    def _replay(
        self, case: RoutingCase, registry: ResourceRegistry, similarity: float
    ) -> SelectionResult:
        definitions = resolve_case(case, registry, exact=self.invalidate)
        if definitions is None:  # pragma: no cover - _admit already checked
            raise ResourceNotFoundError("routing case went stale between admission and replay")
        reason = f"reused routing case (similarity {similarity:.2f}): {case.task}"
        results = tuple(
            SearchResult(
                definition,
                member.score,
                (reason,),
                {"relevance": member.relevance, "cache": 1.0},
            )
            for definition, member in zip(definitions, case.members)
        )
        return SelectionResult(results, reason, status=case.status)


def resolve_case(
    case: RoutingCase, registry: ResourceRegistry, *, exact: bool = True
) -> list[ResourceDefinition] | None:
    """Resolve a case's members against the registry, or ``None`` if stale.

    With ``exact`` (the default) a member must still resolve at the cached
    ``id@version``: a re-versioned resource is a *different* resource whose
    permissions, dependencies, and behaviour may have changed, so the case
    is stale (§15.4 registry drift). With ``exact=False`` the cache keys on
    the id alone and silently replays whatever version now carries it —
    the naive implementation, kept switchable so the ablation can measure
    what the version check is worth.
    """

    definitions: list[ResourceDefinition] = []
    for member in case.members:
        resource_id, version = parse_resource_ref(member.identity)
        try:
            definitions.append(registry.get(resource_id, version if exact else None))
        except ResourceNotFoundError:
            return None
    return definitions


def _idf_cosine(left: Mapping[str, int], right: Mapping[str, int], idf: Mapping[str, float]) -> float:
    if not left or not right:
        return 0.0
    left_weights = {token: count * idf.get(token, 1.0) for token, count in left.items()}
    right_weights = {token: count * idf.get(token, 1.0) for token, count in right.items()}
    dot = sum(weight * right_weights.get(token, 0.0) for token, weight in left_weights.items())
    if dot <= 0.0:
        return 0.0
    left_norm = math.sqrt(sum(weight * weight for weight in left_weights.values()))
    right_norm = math.sqrt(sum(weight * weight for weight in right_weights.values()))
    if left_norm <= 0.0 or right_norm <= 0.0:
        return 0.0
    return max(0.0, min(1.0, dot / (left_norm * right_norm)))


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")
