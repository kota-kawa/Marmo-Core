"""LLM-assisted routing layers: HyDE query transform, LLM re-ranking, and
the LLM Set Selector.

Three LLM-assisted variants from §15.2 / §15.3 of the requirements
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
- ``LLMSetSelector`` (案C の第2層適用): one LLM call reads the candidate
  pool's metadata — including dependencies, conflicts, and permissions —
  and returns a resource *set* (or abstains / escalates). It is the
  strongest comparison target for 案H's constrained solvers (§15.3).

All accept an injectable ``cache`` mapping so benchmark runs are
reproducible and re-runs cost nothing; on any LLM failure the retrievers
degrade to the unmodified query / inner ranking, and the set selector
abstains, rather than failing the search.
"""

from __future__ import annotations

from dataclasses import replace
from typing import MutableMapping
import hashlib
import json
import re

from .llm import ChatMessage, LLMProvider
from .models import SearchQuery, SearchResult, SelectionResult
from .registry import ResourceRegistry
from .retriever import Retriever
from .selector import SelectionContext, SetSelector

_HYDE_SYSTEM = (
    "You expand task statements into hypothetical catalog entries for a "
    "resource registry of tools, skills, memories, and agents. Given a task, "
    "write the description of the ideal resource that would accomplish it: "
    "what it does, its domain vocabulary, and typical inputs and outputs. "
    "Use concrete terms likely to appear in such a resource's documentation. "
    "Reply with 2-3 sentences and no preamble."
)

_RERANK_SYSTEM = (
    "You route tasks to resources in a catalog. Given a task and a numbered "
    "candidate list (id, kind, name, description), pick the candidates that "
    "best accomplish the task. Reply with a JSON array of candidate ids, "
    "best first, at most {limit} items, and nothing else. Only use ids from "
    "the list."
)

_DESCRIPTION_LIMIT = 240


class HydeRetriever(Retriever):
    """Rewrite the task with one LLM call, then delegate to an inner retriever."""

    def __init__(
        self,
        llm: LLMProvider,
        inner: Retriever,
        *,
        cache: MutableMapping[str, str] | None = None,
    ) -> None:
        self.llm = llm
        self.inner = inner
        self.cache = cache if cache is not None else {}
        self.failures = 0

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
            except Exception:
                self.failures += 1
                cached = ""
            self.cache[task] = cached
        # Keep the original wording so direct-vocabulary matches never regress.
        return f"{task}\n{cached}" if cached else task


class LLMRerankRetriever(Retriever):
    """Re-order an inner retriever's candidates with one LLM call.

    The reranker only permutes: ids named by the LLM move to the front in
    the LLM's order, everything else keeps the inner ranking behind them.
    ``SearchResult`` scores are left untouched (they explain the inner
    ranking, not the LLM's), so treat the returned order — not the scores —
    as the ranking.
    """

    def __init__(
        self,
        llm: LLMProvider,
        inner: Retriever,
        *,
        rerank_pool: int = 50,
        rerank_limit: int = 10,
        cache: MutableMapping[str, str] | None = None,
    ) -> None:
        self.llm = llm
        self.inner = inner
        self.rerank_pool = max(1, rerank_pool)
        self.rerank_limit = max(1, rerank_limit)
        self.cache = cache if cache is not None else {}
        self.failures = 0

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
        key = hashlib.sha256(
            json.dumps([task, ids], ensure_ascii=False).encode("utf-8")
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
            except Exception:
                self.failures += 1
                cached = ""
            self.cache[key] = cached
        return _extract_ids(cached, ids)

    def _prompt(self, task: str, pool: list[SearchResult]) -> str:
        lines = [f"Task: {task}", "", "Candidates:"]
        for position, result in enumerate(pool, start=1):
            metadata = result.resource.metadata
            description = re.sub(r"\s+", " ", metadata.description).strip()[:_DESCRIPTION_LIMIT]
            lines.append(f"{position}. id={metadata.id} kind={metadata.kind} name={metadata.name}: {description}")
        return "\n".join(lines)


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


class LLMSetSelector(SetSelector):
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
        self.llm = llm
        self.cache = cache if cache is not None else {}
        self.failures = 0

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
            except Exception:
                self.failures += 1
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


def _extract_ids(text: str, valid_ids: list[str]) -> list[str]:
    """Pull candidate ids out of the LLM reply, tolerating non-JSON output.

    Tries strict JSON first; otherwise falls back to first-occurrence order
    of any valid id appearing verbatim in the reply.
    """

    if not text:
        return []
    match = re.search(r"\[.*\]", text, re.DOTALL)
    if match:
        try:
            parsed = json.loads(match.group(0))
            if isinstance(parsed, list):
                valid = set(valid_ids)
                ordered = [str(item) for item in parsed if str(item) in valid]
                if ordered:
                    return ordered
        except json.JSONDecodeError:
            pass
    positions = [(text.find(rid), rid) for rid in valid_ids if rid in text]
    return [rid for _, rid in sorted(positions)]
