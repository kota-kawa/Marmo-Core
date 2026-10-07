"""LLM-assisted routing layers: HyDE query transform, LLM re-ranking,
whole-catalog LLM selection, and the LLM Set Selector.

Four LLM-assisted variants from §15.2 / §15.3 of the requirements
document, all built on the ``LLMProvider`` abstraction so the core stays
dependency-free:

- ``HydeRetriever`` (案A 派生, HyDE-style query transform): one small LLM
  call rewrites the task statement into the description of a hypothetical
  ideal resource, and retrieval matches that description's vocabulary
  instead of the user's. The original task text is kept alongside the
  rewrite so direct-vocabulary matches never regress.
- ``LLMRerankRetriever`` (案C 最小プロトタイプ): an inner retriever
  proposes candidates, then one LLM call re-orders them by reading their
  lightweight metadata. This is the first-layer application of 案C.
- ``LLMCatalogRetriever``: no candidate retrieval at all — the LLM reads
  the name and the opening characters of every resource in the catalog and
  picks from that. It is the baseline the retrieve-then-rerank stack is
  measured against, and it is sharded when the catalog outgrows one prompt.
- ``LLMSetSelector`` (案C の第2層適用): one LLM call reads the candidate
  pool's metadata — including dependencies, conflicts, and permissions —
  and returns a resource *set* (or abstains / escalates). It is the
  strongest comparison target for 案H's constrained solvers (§15.3).

All accept an injectable ``cache`` mapping so benchmark runs are
reproducible and re-runs cost nothing; on any LLM failure the retrievers
degrade to the unmodified query / inner ranking, and the set selector
abstains, rather than failing the search.

That degradation is deliberate but never silent: every failure is reported
through the ``marmo_core.llm_routing`` logger and recorded on the object as
``failures`` (a count) and ``last_failure`` (the exception), so a run that
quietly fell back to plain lexical retrieval is visible rather than
indistinguishable from a successful one.
"""

from __future__ import annotations

from dataclasses import replace
from typing import MutableMapping
import hashlib
import json
import logging
import re

from .llm import ChatMessage, LLMProvider
from .budget import BudgetExceededError
from .models import ResourceDefinition, SearchQuery, SearchResult, SelectionResult
from .registry import ResourceRegistry
from .retriever import LexicalRetriever, Retriever
from .selector import SelectionContext, SetSelector

_HYDE_SYSTEM = (
    "You expand task statements into hypothetical catalog entries for a "
    "resource registry of tools, skills, memories, and agents. Given a task, "
    "write the description of the ideal resource that would accomplish it: "
    "what it does, its domain vocabulary, and typical inputs and outputs. "
    "Use concrete terms likely to appear in such a resource's documentation. "
    "Reply with 2-3 sentences and no preamble. Always write in English, even "
    "when the task is stated in another language, because the registry is "
    "documented in English."
)

_RERANK_SYSTEM = (
    "You route tasks to resources in a catalog. Given a task and a numbered "
    "candidate list (id, kind, name, description), pick the candidates that "
    "best accomplish the task. Reply with a JSON array of candidate ids, "
    "best first, at most {limit} items, and nothing else. Only use ids from "
    "the list."
)

_DESCRIPTION_LIMIT = 240

_LOGGER = logging.getLogger(__name__)


class _LLMFailureTracker:
    """Failure bookkeeping shared by the LLM-assisted layers.

    The first failure of an instance is logged at WARNING with the exception
    type and message; later ones drop to DEBUG. One line per failure would mean
    one line per uncached query against a provider that is down — loud enough to
    be ignored — while the first line is what tells a user that ``--retriever
    hyde`` is silently behaving like the plain lexical retriever.
    """

    def __init__(self) -> None:
        super().__init__()
        self.failures = 0
        self.last_failure: Exception | None = None

    def _record_failure(self, operation: str, error: Exception) -> None:
        self.failures += 1
        self.last_failure = error
        log = _LOGGER.warning if self.failures == 1 else _LOGGER.debug
        log(
            "%s: %s failed (%s: %s); degrading gracefully (failure %d for this instance)",
            type(self).__name__,
            operation,
            type(error).__name__,
            error,
            self.failures,
        )


class HydeRetriever(_LLMFailureTracker, Retriever):
    """Rewrite the task with one LLM call, then delegate to an inner retriever."""

    def __init__(
        self,
        llm: LLMProvider,
        inner: Retriever,
        *,
        cache: MutableMapping[str, str] | None = None,
    ) -> None:
        super().__init__()
        self.llm = llm
        self.inner = inner
        self.cache = cache if cache is not None else {}

    def search(self, registry: ResourceRegistry, query: SearchQuery) -> list[SearchResult]:
        task = query.task.strip()
        if not task:
            return self.inner.search(registry, query)
        return self.inner.search(registry, replace(query, task=self.transform(task)))

    def transform(self, task: str) -> str:
        cached = self.cache.get(task)
        if cached is None:
            try:
                response = self.llm.complete(
                    [
                        ChatMessage(role="system", content=_HYDE_SYSTEM),
                        ChatMessage(role="user", content=task),
                    ]
                )
                cached = response.content.strip()
            except BudgetExceededError:
                raise
            except Exception as error:
                self._record_failure("HyDE query rewrite", error)
                cached = ""
            self.cache[task] = cached
        # Keep the original wording so direct-vocabulary matches never regress.
        return f"{task}\n{cached}" if cached else task


class LLMRerankRetriever(_LLMFailureTracker, Retriever):
    """Re-order an inner retriever's candidates with one LLM call.

    The reranker only permutes: ids named by the LLM move to the front in
    the LLM's order, everything else keeps the inner ranking behind them.
    ``SearchResult`` scores are left untouched (they explain the inner
    ranking, not the LLM's), so treat the returned order — not the scores —
    as the ranking.

    Models sometimes answer with the candidates' list numbers instead of
    their ids. ``accept_positions=True`` reads such a number as the candidate
    at that position; the default ignores it, which is what runs replayed
    from an existing reply cache were scored with.
    """

    def __init__(
        self,
        llm: LLMProvider,
        inner: Retriever,
        *,
        rerank_pool: int = 50,
        rerank_limit: int = 10,
        description_limit: int = _DESCRIPTION_LIMIT,
        accept_positions: bool = False,
        cache: MutableMapping[str, str] | None = None,
    ) -> None:
        super().__init__()
        self.llm = llm
        self.inner = inner
        self.rerank_pool = max(1, rerank_pool)
        self.rerank_limit = max(1, rerank_limit)
        self.description_limit = max(0, description_limit)
        self.accept_positions = accept_positions
        self.cache = cache if cache is not None else {}

    def search(self, registry: ResourceRegistry, query: SearchQuery) -> list[SearchResult]:
        task = query.task.strip()
        if not task:
            return self.inner.search(registry, query)
        widened = replace(query, top_k=max(query.top_k, self.rerank_pool))
        candidates = self.inner.search(registry, widened)
        if len(candidates) < 2:
            return candidates[: query.top_k]
        pool = candidates[: self.rerank_pool]
        ranked_ids = self._ranked_ids(task, pool)
        by_id = {result.resource.metadata.id: result for result in pool}
        reordered = [by_id[rid] for rid in ranked_ids if rid in by_id]
        chosen = {result.resource.metadata.id for result in reordered}
        reordered += [r for r in candidates if r.resource.metadata.id not in chosen]
        return reordered[: query.top_k]

    def _ranked_ids(self, task: str, pool: list[SearchResult]) -> list[str]:
        ids = [result.resource.metadata.id for result in pool]
        # The limit joins the key only when it is not the default, so replies
        # cached before it became configurable still replay.
        key_parts: list[object] = [task, ids]
        if self.description_limit != _DESCRIPTION_LIMIT:
            key_parts.append(self.description_limit)
        key = hashlib.sha256(
            json.dumps(key_parts, ensure_ascii=False).encode("utf-8")
        ).hexdigest()
        cached = self.cache.get(key)
        if cached is None:
            try:
                response = self.llm.complete(
                    [
                        ChatMessage(
                            role="system",
                            content=_RERANK_SYSTEM.format(limit=self.rerank_limit),
                        ),
                        ChatMessage(role="user", content=self._prompt(task, pool)),
                    ]
                )
                cached = response.content
            except BudgetExceededError:
                raise
            except Exception as error:
                self._record_failure("candidate rerank", error)
                cached = ""
            self.cache[key] = cached
        return _extract_ids(cached, ids, accept_positions=self.accept_positions)

    def _prompt(self, task: str, pool: list[SearchResult]) -> str:
        return _candidate_prompt(
            task, [result.resource for result in pool], self.description_limit
        )


def _candidate_prompt(
    task: str, definitions: list[ResourceDefinition], description_limit: int
) -> str:
    """The numbered candidate list shown to the LLM.

    ``description_limit`` caps how much of each description is shown; ``0``
    shows the id, kind, and name only.
    """

    lines = [f"Task: {task}", "", "Candidates:"]
    for position, definition in enumerate(definitions, start=1):
        metadata = definition.metadata
        line = f"{position}. id={metadata.id} kind={metadata.kind} name={metadata.name}"
        if description_limit > 0:
            description = re.sub(r"\s+", " ", metadata.description).strip()[:description_limit]
            line += f": {description}"
        lines.append(line)
    return "\n".join(lines)


class LLMCatalogRetriever(_LLMFailureTracker, Retriever):
    """Rank by letting the LLM read the whole catalog, with no retrieval first.

    Every resource that passes the query's filters is listed — id, kind,
    name, and the first ``description_limit`` characters of its description —
    and the LLM names the best ones. Ids it names come first in its order;
    ``inner`` supplies the ranking behind them, and the whole ranking when
    the LLM fails. As with ``LLMRerankRetriever``, ``SearchResult`` scores
    are the lexical ones, not the LLM's: read the order, not the scores.

    What the query's filters and limits mean here: the kind, trust-level,
    side-effect, keyword, tag, and permission filters decide what the LLM is
    shown, and ``per_kind_limits`` and ``top_k`` cap the final order. An LLM
    pick is *not* held to ``min_score`` or to whatever narrowing ``inner``
    does on its own (a pool size, a routed group) — surfacing what ``inner``
    would not is the point — so a pick ``inner`` did not return carries its
    task-less lexical score. This is a ranking, not a gate: activation,
    execution, and output policy still decide what may run.

    A catalog larger than ``shard_size`` is split into consecutive shards
    with one call each, and one more call ranks the shards' picks against
    each other. ``shard_size=None`` always sends the catalog in one prompt.

    A reply may name a candidate by its id or by its number in the list;
    against a long list of long ids, models often answer with the numbers.
    ``empty_replies`` counts replies that named no listed candidate and
    ``unknown_ids`` counts entries that were neither a listed id nor a valid
    list number; both are tallied for cached replies too, so a replayed run
    reports them.
    """

    def __init__(
        self,
        llm: LLMProvider,
        inner: Retriever,
        *,
        select_limit: int = 10,
        description_limit: int = _DESCRIPTION_LIMIT,
        shard_size: int | None = None,
        cache: MutableMapping[str, str] | None = None,
    ) -> None:
        super().__init__()
        if shard_size is not None and shard_size < 2:
            raise ValueError("shard_size must be >= 2")
        self.llm = llm
        self.inner = inner
        self.select_limit = max(1, select_limit)
        self.description_limit = max(0, description_limit)
        self.shard_size = shard_size
        self.cache = cache if cache is not None else {}
        self.empty_replies = 0
        self.unknown_ids = 0
        self._catalog_filter = LexicalRetriever()

    def search(self, registry: ResourceRegistry, query: SearchQuery) -> list[SearchResult]:
        task = query.task.strip()
        if not task:
            return self.inner.search(registry, query)
        catalog = self._catalog(registry, query)
        ranked = self.inner.search(registry, query)
        if len(catalog) < 2:
            return ranked
        picked = self._select(task, [result.resource for result in catalog])
        by_id = {result.resource.metadata.id: result for result in ranked}
        listed = {result.resource.metadata.id: result for result in catalog}
        reordered = [by_id.get(rid, listed[rid]) for rid in picked]
        chosen = set(picked)
        reordered += [r for r in ranked if r.resource.metadata.id not in chosen]
        return self._catalog_filter.apply_limits(reordered, query)

    def _catalog(self, registry: ResourceRegistry, query: SearchQuery) -> list[SearchResult]:
        """Every resource passing the query's filters, in id order.

        A task-less lexical search applies the filters without ranking by the
        task, so the list the LLM reads does not depend on lexical overlap.
        """

        unranked = replace(
            query, task="", top_k=max(1, len(registry)), per_kind_limits={}, min_score=0.0
        )
        results = self._catalog_filter.search(registry, unranked)
        return sorted(results, key=lambda result: result.resource.metadata.id)

    def _select(self, task: str, catalog: list[ResourceDefinition]) -> list[str]:
        if self.shard_size is None or len(catalog) <= self.shard_size:
            return self._ask(task, catalog)
        by_id = {definition.metadata.id: definition for definition in catalog}
        finalists: list[ResourceDefinition] = []
        for start in range(0, len(catalog), self.shard_size):
            shard = catalog[start : start + self.shard_size]
            finalists += [by_id[rid] for rid in self._ask(task, shard)]
        if len(finalists) < 2:
            return [definition.metadata.id for definition in finalists]
        return self._ask(task, finalists)

    def _ask(self, task: str, definitions: list[ResourceDefinition]) -> list[str]:
        ids = [definition.metadata.id for definition in definitions]
        system = _RERANK_SYSTEM.format(limit=self.select_limit)
        prompt = _candidate_prompt(task, definitions, self.description_limit)
        key = hashlib.sha256(
            json.dumps([system, prompt], ensure_ascii=False).encode("utf-8")
        ).hexdigest()
        cached = self.cache.get(key)
        if cached is None:
            try:
                response = self.llm.complete(
                    [
                        ChatMessage(role="system", content=system),
                        ChatMessage(role="user", content=prompt),
                    ]
                )
                cached = response.content
            except BudgetExceededError:
                raise
            except Exception as error:
                self._record_failure("catalog selection", error)
                cached = ""
            self.cache[key] = cached
        named = _extract_ids(cached, ids, accept_positions=True)
        picked = list(dict.fromkeys(named))[: self.select_limit]
        if not picked:
            self.empty_replies += 1
        self.unknown_ids += _unknown_id_count(cached, ids)
        return picked


_SET_SELECT_SYSTEM = (
    "You select the set of resources an AI agent kernel should activate for "
    "a task. Work in two steps.\n"
    "Step 1 — match: find the candidates whose name and description "
    "accomplish the task. Do NOT minimize the set: include every candidate "
    "that is relevant to the task and feasible, across all kinds — the "
    "relevant memory (context), skill (procedure), tool, and agent all "
    "belong in the set when the per-kind limits allow them.\n"
    "Step 2 — close and validate the set:\n"
    "- also include every id in a chosen candidate's 'requires' list "
    "(recursively); a set with a missing 'requires' member is invalid.\n"
    "- never include two ids where one lists the other in 'conflicts'. "
    "When two conflicting alternatives both match, keep the one that fits "
    "the task better and drop the other — a conflict never makes the task "
    "infeasible on its own.\n"
    "- a candidate is choosable iff its permissions=[...] list is a subset "
    "of the granted permissions; permissions=[] is always choosable. "
    "Permission names are opaque labels matched only against those lists — "
    "they say nothing else about what is allowed, and permission needs are "
    "never inferred from names or descriptions.\n"
    "- respect the per-kind limits, max resources, and cost budget.\n"
    "Reply with a single JSON object and nothing else:\n"
    '{"status": "selected", "ids": [...], "reason": "..."} — ids are the '
    "exact strings after 'id=' (never positions or names).\n"
    '{"status": "abstain", "ids": [], "reason": "..."} — no candidate '
    "matches the task.\n"
    '{"status": "escalate", "ids": [], "reason": "..."} — the task could '
    "only be accomplished with permissions that were not granted, so a "
    "human must decide.\n"
    "Example — granted permissions: db.read; candidates: id=memory.m "
    "permissions=[], id=skill.y permissions=[], id=tool.x "
    "requires=[skill.y] permissions=[], id=tool.z conflicts=[tool.x] "
    "permissions=[], id=agent.a requires=[tool.x] permissions=[] →\n"
    '{"status": "selected", "ids": ["agent.a", "tool.x", "skill.y", '
    '"memory.m"], "reason": "all four kinds are relevant: agent.a '
    "delegates the work and requires tool.x, which requires skill.y; "
    "memory.m holds the context; tool.z conflicts with tool.x so it is "
    'dropped"}'
)


class LLMSetSelector(_LLMFailureTracker, SetSelector):
    """案C applied to the second layer: one LLM call picks the resource set.

    The comparison target for 案H's constrained solvers (§15.3). The LLM is
    shown the same information the solvers get — candidate metadata with
    dependencies, conflicts, permissions, and cost, plus the context's
    constraints — and must return a set or abstain/escalate (§15.6).

    The reply is deliberately **not** repaired against the constraints:
    whether the LLM respects dependency closure, conflict exclusion, and
    permission feasibility is exactly what the benchmark's Closure /
    Conflict-Free / Policy-Feasible rates measure. The only sanitization is
    dropping ids that are not in the candidate pool (a selector cannot
    activate what the retriever never surfaced). On any LLM failure the
    selector abstains instead of guessing.
    """

    def __init__(
        self,
        llm: LLMProvider,
        *,
        cache: MutableMapping[str, str] | None = None,
    ) -> None:
        super().__init__()
        self.llm = llm
        self.cache = cache if cache is not None else {}

    def select(
        self, results: list[SearchResult], *, context: SelectionContext | None = None
    ) -> SelectionResult:
        ctx = context or SelectionContext()
        candidates = [
            r
            for r in results
            if r.score >= ctx.min_score
            and float(r.components.get("relevance", 1.0)) >= ctx.min_relevance
        ]
        if not candidates:
            return SelectionResult(
                (), "no candidate met the minimum score and relevance thresholds", status="abstain"
            )
        reply = self._reply(ctx, candidates)
        if reply is None:
            return SelectionResult(
                (), "LLM set selection failed; abstaining instead of guessing", status="abstain"
            )
        status, ids, reason = reply
        pool = {result.resource.metadata.id: result for result in candidates}
        picked = [pool[rid] for rid in ids if rid in pool]
        if status == "selected" and not picked:
            return SelectionResult(
                (), f"LLM selected no valid candidate ids ({reason})", status="abstain"
            )
        if status != "selected":
            return SelectionResult((), f"LLM {status}: {reason}", status=status)
        ordered = tuple(sorted(picked, key=lambda r: (-r.score, r.resource.metadata.id)))
        return SelectionResult(ordered, f"LLM selected {len(ordered)} resource(s): {reason}")

    def _reply(
        self, ctx: SelectionContext, candidates: list[SearchResult]
    ) -> tuple[str, list[str], str] | None:
        prompt = self._prompt(ctx, candidates)
        # The system prompt is part of the key: prompt-wording changes must
        # not replay replies produced under the old instructions.
        key = hashlib.sha256(
            json.dumps([_SET_SELECT_SYSTEM, prompt], ensure_ascii=False).encode("utf-8")
        ).hexdigest()
        cached = self.cache.get(key)
        if cached is None:
            try:
                response = self.llm.complete(
                    [
                        ChatMessage(role="system", content=_SET_SELECT_SYSTEM),
                        ChatMessage(role="user", content=prompt),
                    ]
                )
                cached = response.content
            except BudgetExceededError:
                raise
            except Exception as error:
                self._record_failure("set selection", error)
                cached = ""
            self.cache[key] = cached
        if not cached:
            return None
        return _parse_set_reply(cached, [r.resource.metadata.id for r in candidates])

    def _prompt(self, ctx: SelectionContext, candidates: list[SearchResult]) -> str:
        granted = ", ".join(sorted(ctx.granted_permissions)) or "(none)"
        limits = (
            ", ".join(f"{kind}<={limit}" for kind, limit in sorted(ctx.per_kind_limits.items()))
            or "(none)"
        )
        budget = f"{ctx.budget_cost:g}" if ctx.budget_cost is not None else "(none)"
        lines = [
            f"Task: {ctx.task}",
            "",
            "Constraints:",
            f"- granted permissions: {granted} — a candidate is choosable iff its "
            "permissions=[...] list is a subset of these; permissions=[] means "
            "it needs no permissions and is always choosable",
            f"- per-kind limits: {limits}",
            f"- max resources: {ctx.max_resources}",
            f"- cost budget: {budget}",
            "",
            "Candidates:",
        ]
        for result in candidates:
            metadata = result.resource.metadata
            description = re.sub(r"\s+", " ", metadata.description).strip()[:_DESCRIPTION_LIMIT]
            parts = [
                f"- id={metadata.id} kind={metadata.kind} name={metadata.name}",
                f"cost={metadata.cost_estimate:g}",
            ]
            if metadata.dependencies:
                parts.append("requires=[" + ", ".join(metadata.dependencies) + "]")
            if metadata.conflicts_with:
                parts.append("conflicts=[" + ", ".join(metadata.conflicts_with) + "]")
            parts.append("permissions=[" + ", ".join(metadata.required_permissions) + "]")
            lines.append(" ".join(parts) + f": {description}")
        return "\n".join(lines)


def _parse_set_reply(text: str, valid_ids: list[str]) -> tuple[str, list[str], str] | None:
    """Parse the set-selection reply into (status, ids, reason).

    Accepts a JSON object (possibly wrapped in prose or a code fence); falls
    back to treating any valid ids appearing verbatim as a selected set.
    """

    match = re.search(r"\{.*\}", text, re.DOTALL)
    if match:
        try:
            parsed = json.loads(match.group(0))
        except json.JSONDecodeError:
            parsed = None
        if isinstance(parsed, dict):
            status = str(parsed.get("status", "selected"))
            if status not in ("selected", "abstain", "escalate"):
                status = "selected"
            raw_ids = parsed.get("ids", [])
            ids = [str(item) for item in raw_ids] if isinstance(raw_ids, list) else []
            reason = str(parsed.get("reason", "")).strip() or "no reason given"
            return status, ids, reason
    fallback = _extract_ids(text, valid_ids)
    if fallback:
        return "selected", fallback, "ids recovered from a non-JSON reply"
    return None


def _named_candidate(item: object, valid_ids: list[str], valid: set[str], accept_positions: bool) -> str | None:
    """The candidate id one reply entry names, or ``None`` when it names none.

    An entry is an id first; with ``accept_positions`` a whole number that is
    not itself an id is read as the 1-based position in the candidate list.
    """

    text = str(item)
    if text in valid:
        return text
    digits = text.strip()
    # ASCII digits only, and short enough that int() cannot be made to fail.
    if accept_positions and not isinstance(item, bool) and digits.isascii() and digits.isdecimal() and len(digits) <= 9:
        position = int(digits)
        if 1 <= position <= len(valid_ids):
            return valid_ids[position - 1]
    return None


def _unknown_id_count(text: str, valid_ids: list[str]) -> int:
    """How many entries of the reply's JSON array name no candidate, by id or position."""

    match = re.search(r"\[.*\]", text, re.DOTALL)
    if not match:
        return 0
    try:
        parsed = json.loads(match.group(0))
    except json.JSONDecodeError:
        return 0
    if not isinstance(parsed, list):
        return 0
    valid = set(valid_ids)
    return sum(1 for item in parsed if _named_candidate(item, valid_ids, valid, True) is None)


def _extract_ids(text: str, valid_ids: list[str], *, accept_positions: bool = False) -> list[str]:
    """Pull candidate ids out of the LLM reply, tolerating non-JSON output.

    Tries strict JSON first; otherwise falls back to first-occurrence order
    of any valid id appearing verbatim in the reply. ``accept_positions``
    also reads whole numbers in the JSON array as positions in ``valid_ids``.
    """

    if not text:
        return []
    match = re.search(r"\[.*\]", text, re.DOTALL)
    if match:
        try:
            parsed = json.loads(match.group(0))
            if isinstance(parsed, list):
                valid = set(valid_ids)
                named = (_named_candidate(item, valid_ids, valid, accept_positions) for item in parsed)
                ordered = [rid for rid in named if rid is not None]
                if ordered:
                    return ordered
        except json.JSONDecodeError:
            pass
    positions = [(text.find(rid), rid) for rid in valid_ids if rid in text]
    return [rid for _, rid in sorted(positions)]
