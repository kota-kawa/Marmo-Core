"""Candidate pools: what the set selector is handed for one goal.

Retrieval ranks the catalog; a candidate pool turns that ranking into the
list a ``SetSelector`` chooses from. The Kernel used to build that list
itself (policy pre-filtering plus a per-kind top-up search), which meant a
selector comparison run through the Kernel also measured that logic. The
pool is now its own extension point, passed as ``Kernel(candidate_pool=...)``:

- ``KindBalancedCandidatePool`` is the Kernel default and keeps the
  behaviour the Kernel always had.
- ``RetrieverCandidatePool`` hands over the retriever's ranking unchanged,
  so a selector sees exactly what layer 1 returned.

A pool never decides whether a resource may run. Whatever it returns still
goes through set selection, the activation gate, and the execution gate.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections import Counter
from dataclasses import dataclass, replace as dataclass_replace
from typing import Callable, Mapping

from .models import SearchQuery, SearchResult
from .errors import CandidatePoolLimitError, ResourceNotFoundError
from .registry import ResourceRegistry
from .retriever import Retriever
from .routing_contracts import ResourceContract


@dataclass(frozen=True)
class CandidatePoolRequest:
    """Everything a pool needs for one goal, assembled by the Kernel.

    ``per_kind_limits`` is the selector's effective per-kind limits (its
    defaults with the Kernel's ``set_limits`` on top) and ``min_score`` its
    composite floor. ``is_denied`` is the activation-gate verdict the Kernel
    uses for selection. ``keep_best_denied_of_kind`` asks the pool to keep
    the best match of each kind even when it is denied, so the run can
    report which permission is missing.
    """

    goal: str
    registry: ResourceRegistry
    retriever: Retriever
    granted_permissions: tuple[str, ...]
    top_k: int
    per_kind_limits: Mapping[str, int]
    min_score: float
    is_denied: Callable[[SearchResult], bool]
    keep_best_denied_of_kind: bool = True


class CandidatePool(ABC):
    """Builds the candidate list for one goal. Implementations are swappable."""

    @abstractmethod
    def build(self, request: CandidatePoolRequest) -> list[SearchResult]:
        """Return the candidates the set selector chooses from, best first."""


class RetrieverCandidatePool(CandidatePool):
    """The retriever's top ``top_k`` ranking, with no filtering or top-up."""

    def build(self, request: CandidatePoolRequest) -> list[SearchResult]:
        return request.retriever.search(request.registry, _query(request))


class DependencyExpandedCandidatePool(CandidatePool):
    """Append discoverable declared dependencies to an inner pool.

    All context alternatives are discovered; selection still chooses between
    them and every execution gate still applies. Added resources have zero
    relevance, so discovery does not reward dependency count. Missing, disabled,
    ambiguous and policy-denied references remain unresolved, rather than making
    an unrelated root invalidate the whole pool. Overflow raises explicitly;
    callers must not interpret a truncated pool as a complete catalog.
    """

    preflight_before_task_spec = True

    def __init__(self, inner: CandidatePool | None = None, *, max_candidates: int = 128) -> None:
        if type(max_candidates) is not int or max_candidates < 1:
            raise ValueError("max_candidates must be a positive integer")
        self.inner = inner if inner is not None else RetrieverCandidatePool()
        self.max_candidates = max_candidates
        self.last_missing_references: tuple[str, ...] = ()
        self.last_added_ids: tuple[str, ...] = ()

    def build(self, request: CandidatePoolRequest) -> list[SearchResult]:
        self.last_missing_references = ()
        self.last_added_ids = ()
        results: list[SearchResult] = []
        seen: set[str] = set()
        missing: list[str] = []
        added: list[str] = []

        def append(result: SearchResult, *, dependency: bool = False) -> None:
            identity = result.resource.identity
            if identity in seen:
                return
            if len(results) >= self.max_candidates:
                self.last_missing_references = tuple(dict.fromkeys(missing))
                self.last_added_ids = tuple(added)
                raise CandidatePoolLimitError(
                    f"declared candidate expansion exceeds max_candidates={self.max_candidates}; "
                    "candidate coverage is incomplete"
                )
            seen.add(identity)
            results.append(result)
            if dependency:
                added.append(identity)

        for result in self.inner.build(request):
            if not request.is_denied(result):
                append(result)
        index = 0
        while index < len(results):
            current = results[index]
            index += 1
            contract = ResourceContract.from_resource(current.resource)
            references = list(current.resource.metadata.dependencies) + list(contract.context_all_of)
            for alternatives in contract.context_one_of:
                references.extend(alternatives)
            for reference in dict.fromkeys(references):
                try:
                    definition = request.registry.get(reference)
                except ResourceNotFoundError:
                    missing.append(reference)
                    continue
                if definition.identity in seen:
                    continue
                dependency = SearchResult(
                    resource=definition, score=0.0,
                    reasons=(f"declared dependency of {current.resource.identity}",),
                    components={"relevance": 0.0},
                )
                if request.is_denied(dependency):
                    missing.append(reference)
                    continue
                append(dependency, dependency=True)
        self.last_missing_references = tuple(dict.fromkeys(missing))
        self.last_added_ids = tuple(added)
        return results


class KindBalancedCandidatePool(CandidatePool):
    """Rank candidates for the goal, leaving every kind a fillable share.

    Retrieval returns one globally ranked ``top_k``, so a kind holding many
    entries -- a thousand-skill catalog next to ten Tools -- can take every
    slot and leave the set selector nothing to fill its per-kind limits with.
    The run then reports ``tool=0/3`` and the model answers with no tools at
    all, which reads as a clean completion. The kinds that come back short
    therefore get *one* extra search between them, restricted to those kinds
    and limited per kind, over the same cached index. One, not one per kind:
    with an embedding-backed or LLM-backed retriever each search is a paid
    round trip on the same goal string.

    Lower-ranked candidates the activation gate would deny are dropped. A
    denied resource that is the *best* match of its kind stays (when
    ``keep_best_denied_of_kind`` is set) so the run can report it as skipped,
    which tells the caller which permission is missing; a denied resource
    that would only fill a spare slot is left out, so widening the set never
    turns a clean read-only run into a strict failure because an unrelated
    write tool was pulled in.

    Top-ups drop denied candidates too, and respect the selector's
    ``min_score`` floor: the point is to give the selector something it can
    actually use. Filling the Tool slots does mean a goal can now be offered
    a Tool that a crowded pool used to hide from it. That exposure is not
    new -- the same Tool is selected in any registry small enough not to
    crowd -- but the crowding was masking it. The activation and execution
    gates, the HITL escalation for side-effecting resources, ``set_limits``,
    and a selector ``min_score`` remain the controls.
    """

    def build(self, request: CandidatePoolRequest) -> list[SearchResult]:
        query = _query(request)
        results = self._feasible(request.retriever.search(request.registry, query), request)
        limits = request.per_kind_limits
        counts = Counter(result.resource.metadata.kind for result in results)
        seen = {result.resource.identity for result in results}
        shortfalls = {
            kind: limits[kind] - counts.get(kind, 0)
            for kind in sorted(limits)
            if limits[kind] - counts.get(kind, 0) > 0 and request.registry.count(kind)
        }
        if not shortfalls:
            return results
        # Each starved kind gets its own depth to walk (candidates already in
        # the pool, or denied at the activation gate, do not count against the
        # shortfall).
        topup = dataclass_replace(
            query,
            kinds=tuple(shortfalls),
            per_kind_limits={kind: request.top_k for kind in shortfalls},
            top_k=request.top_k * len(shortfalls),
        )
        for result in request.retriever.search(request.registry, topup):
            kind = result.resource.kind
            if shortfalls.get(kind, 0) <= 0 or result.resource.identity in seen:
                continue
            if result.score < request.min_score:
                continue
            if request.is_denied(result):
                continue
            seen.add(result.resource.identity)
            results.append(result)
            shortfalls[kind] -= 1
        return results

    @staticmethod
    def _feasible(results: list[SearchResult], request: CandidatePoolRequest) -> list[SearchResult]:
        kept: list[SearchResult] = []
        seen_kinds: set[str] = set()
        for result in results:
            kind = result.resource.metadata.kind
            first_of_kind = kind not in seen_kinds
            seen_kinds.add(kind)
            if (first_of_kind and request.keep_best_denied_of_kind) or not request.is_denied(result):
                kept.append(result)
        return kept


def _query(request: CandidatePoolRequest) -> SearchQuery:
    return SearchQuery(
        task=request.goal,
        granted_permissions=request.granted_permissions,
        top_k=request.top_k,
    )
