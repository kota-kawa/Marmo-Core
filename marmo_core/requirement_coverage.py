"""Requirement coverage: an LLM judges capability, the solver decides the set and status.

``LLMSetSelector`` asks one model call for the whole answer: the set, and
whether to abstain or escalate. The model then has to read permission labels
and constraint rules as well as descriptions, and on the repository's
constrained corpus it under-selected and once inferred undeclared permission
needs from permission names (ADR 0005). ``CoverageSetSelector`` keeps the
constraints in the solver but decides from retrieval scores, which cannot say
whether *any* candidate fulfils a requirement: relevance distributions of
answerable and unanswerable goals overlap, so a fixed floor separates them
poorly.

``RequirementCoverageSelector`` splits the work along that line:

1. One LLM call lists the capabilities the task needs ("requirements") and,
   for each, the candidates whose description says they can fulfil it. The
   prompt shows names, kinds, and descriptions only: no permissions, costs,
   trust levels, or constraint rules, so the judgment is about capability.
2. The solver builds dependency-closed units from the candidates (the same
   units as the constrained solvers), and per requirement splits the
   satisfying units into feasible ones and ones blocked only by missing
   permissions.
3. The outcome follows from the declared constraints:

   - a requirement no candidate satisfies (or none whose unit can be built)
     → ``abstain``: granting permissions would not help;
   - otherwise a requirement only permission-blocked units satisfy
     → ``escalate``, with the fewest missing permissions that unblock it;
   - otherwise → ``selected``: a greedy set cover, taking first the feasible
     unit that covers the most uncovered requirements (ties by retrieval
     rank), under the conflict, per-kind, ``max_resources``, and budget
     constraints. With ``per_requirement="all"``, every other feasible unit
     the judge listed is added afterwards, in rank order, while it fits.

The LLM never decides the status and never sees a permission, so a forged or
mislabelled permission cannot talk it into or out of a set; the solver reads
the declarations exactly as the other solvers do. What the model can get
wrong is capability: listing a requirement the task does not need (a false
abstain), or crediting a candidate that cannot fulfil one (a wrong set). On
an LLM failure, or a reply without requirements, it abstains instead of
guessing, and records the failure like the other LLM-assisted layers.

The selector shows at most ``max_candidates`` candidates (default 20, the
pool ``LLMSetSelector`` sees in the ToolRet benchmark) after the score and
relevance floors. Replies are cached by prompt, so the same candidates under
different grants reuse one judgment. Budgeted Kernel tasks reject it, like
other selectors that do not declare ``budget_aware``.

Two options, both off by default:

- ``extra_candidates``: before escalating, look once at the next
  ``extra_candidates`` results in rank order, keeping those whose unit needs
  no ungranted permission, and ask in a second call which of them fulfil the
  requirements that only permission-blocked candidates fulfilled. If every
  such requirement gets a permitted candidate the set is selected instead.
  This is one more LLM call on those selections and none on the others.
- ``judge="strict"``: the prompt tells the judge to credit a candidate only
  when its description states the capability, and to leave it out when in
  doubt.

``last_llm_calls`` is the number of judge calls the last selection needed
(replies served from the cache count, so it is what an uncached run costs).
"""

from __future__ import annotations

import hashlib
import json
import re
from collections import defaultdict
from dataclasses import dataclass
from decimal import Decimal
from typing import Any, MutableMapping

from .budget import BudgetExceededError
from .llm import ChatMessage, LLMProvider
from .llm_routing import _LLMFailureTracker
from .models import SearchResult, SelectionResult
from .selector import SelectionContext, SetSelector, _build_units, _misfit, _total_cost, _Unit

PER_REQUIREMENT_CHOICES = ("best", "all")
JUDGE_CHOICES = ("standard", "strict")
_DESCRIPTION_LIMIT = 240

_SYSTEM = (
    "You check which candidate resources can fulfil a task for an AI agent. Work in two steps.\n"
    "Step 1 — requirements: list the distinct capabilities the task needs from resources, as short "
    "imperative phrases. Include only what the task asks for or cannot be done without; merge steps one "
    "resource would naturally do together; do not add generic steps such as asking the user, "
    "reasoning, or formatting the answer. Most tasks need one to three requirements.\n"
    "Step 2 — candidates: for each requirement, list the id of every candidate whose name and "
    "description show that it can fulfil that requirement by itself. Judge capability only: ignore "
    "cost, trust, and any access rules. Do not stretch a description to fit; if no candidate can "
    "fulfil a requirement, give it an empty list.{strict}\n"
    "Reply with a single JSON object and nothing else:\n"
    '{{"requirements": [{{"need": "...", "ids": ["..."]}}]}}\n'
    "ids are the exact strings after 'id=' (never positions or names)."
)
_EXTRA_SYSTEM = (
    "You check which candidate resources can fulfil numbered requirements of a task for an AI agent. "
    "For each requirement, list the id of every candidate whose name and description show that it can "
    "fulfil that requirement by itself. Judge capability only: ignore cost, trust, and any access "
    "rules. Do not stretch a description to fit; if no candidate can fulfil a requirement, give it an "
    "empty list.{strict}\n"
    "Reply with a single JSON object and nothing else:\n"
    '{{"matches": [{{"requirement": 1, "ids": ["..."]}}]}}\n'
    "ids are the exact strings after 'id=' (never positions or names)."
)
_STRICT = (
    " Credit a candidate only when its own description states that capability for the kind of input "
    "the task has. A candidate for a related task, for a broader or narrower category, or for a "
    "different data source does not fulfil the requirement. When in doubt, leave the candidate out."
)


@dataclass(frozen=True)
class Requirement:
    """One capability the judge listed, with the candidate ids it credited."""

    need: str
    ids: tuple[str, ...]


class RequirementCoverageSelector(_LLMFailureTracker, SetSelector):
    """LLM capability judgment per requirement; set and status from the solver."""

    def __init__(
        self,
        llm: LLMProvider,
        *,
        cache: MutableMapping[str, str] | None = None,
        max_candidates: int = 20,
        max_requirements: int = 8,
        per_requirement: str = "best",
        extra_candidates: int = 0,
        judge: str = "standard",
    ) -> None:
        super().__init__()
        if max_candidates < 1:
            raise ValueError("max_candidates must be at least 1")
        if max_requirements < 1:
            raise ValueError("max_requirements must be at least 1")
        if per_requirement not in PER_REQUIREMENT_CHOICES:
            raise ValueError(f"per_requirement must be one of: {', '.join(PER_REQUIREMENT_CHOICES)}")
        if extra_candidates < 0:
            raise ValueError("extra_candidates must not be negative")
        if judge not in JUDGE_CHOICES:
            raise ValueError(f"judge must be one of: {', '.join(JUDGE_CHOICES)}")
        self.llm = llm
        self.cache = cache if cache is not None else {}
        self.max_candidates = max_candidates
        self.max_requirements = max_requirements
        self.per_requirement = per_requirement
        self.extra_candidates = extra_candidates
        self.judge = judge
        self.last_requirements: tuple[Requirement, ...] = ()
        self.last_llm_calls = 0

    def select(
        self, results: list[SearchResult], *, context: SelectionContext | None = None
    ) -> SelectionResult:
        ctx = context or SelectionContext()
        self.last_requirements = ()
        self.last_llm_calls = 0
        eligible = [
            r
            for r in results
            if r.score >= ctx.min_score and float(r.components.get("relevance", 1.0)) >= ctx.min_relevance
        ]
        candidates = eligible[: self.max_candidates]
        if not candidates:
            return SelectionResult((), "no candidate met the minimum score and relevance thresholds", status="abstain")
        requirements = self._judge(ctx.task, candidates)
        if requirements is None:
            return SelectionResult((), "requirement judgment failed; abstaining instead of guessing", status="abstain")
        self.last_requirements = requirements

        # Dependency closures may reach any retrieved result, as in the other
        # solvers; only the judged candidates can be credited with a requirement.
        pool = {result.resource.metadata.id: result for result in results}
        notes: list[str] = []
        units, blocked = _build_units(candidates, pool, ctx, notes)
        feasible_by_root = {unit.root: unit for unit in units}
        blocked_by_root = {unit.root: unit for unit in blocked}
        rank = {result.resource.metadata.id: position for position, result in enumerate(candidates)}

        unmet: list[str] = []
        needs_grant: dict[int, list[_Unit]] = {}
        options: list[list[_Unit]] = []
        for index, requirement in enumerate(requirements):
            feasible = [feasible_by_root[rid] for rid in requirement.ids if rid in feasible_by_root]
            gated = [blocked_by_root[rid] for rid in requirement.ids if rid in blocked_by_root]
            if not feasible and not gated:
                unmet.append(requirement.need)
            elif not feasible:
                needs_grant[index] = gated
            options.append(sorted(feasible, key=lambda unit: rank[unit.root]))

        if unmet:
            return SelectionResult(
                (), "no candidate can fulfil: " + "; ".join(unmet) + _judged(requirements), status="abstain"
            )
        if needs_grant and self.extra_candidates:
            # One more look before asking a person: the next candidates in rank
            # order that need no grant, judged for the blocked requirements only.
            extras = eligible[self.max_candidates : self.max_candidates + self.extra_candidates]
            permitted = {unit.root: unit for unit in _build_units(extras, pool, ctx, [])[0]}
            shown = [result for result in extras if result.resource.metadata.id in permitted]
            rank.update({r.resource.metadata.id: len(candidates) + position for position, r in enumerate(shown)})
            pending = sorted(needs_grant)
            credited = self._judge_extras(ctx.task, [requirements[index].need for index in pending], shown)
            revised = list(requirements)
            for index, ids in zip(pending, credited):
                if ids:
                    options[index] = [permitted[rid] for rid in ids]
                    revised[index] = Requirement(requirements[index].need, requirements[index].ids + ids)
                    del needs_grant[index]
            requirements = tuple(revised)
            self.last_requirements = requirements
        if needs_grant:
            missing: set[str] = set()
            parts = []
            for index, gated in sorted(needs_grant.items()):
                cheapest = min(gated, key=lambda unit: (len(unit.missing_permissions), rank[unit.root]))
                missing |= cheapest.missing_permissions
                parts.append(f"{requirements[index].need} needs {', '.join(sorted(cheapest.missing_permissions))}")
            return SelectionResult(
                (),
                "only candidates without granted permissions can fulfil: " + "; ".join(parts)
                + "; a human can grant them and re-run" + _judged(requirements),
                status="escalate",
                missing_permissions=tuple(sorted(missing)),
            )
        return self._cover(requirements, options, pool, rank, ctx)

    def _cover(
        self,
        requirements: tuple[Requirement, ...],
        options: list[list[_Unit]],
        pool: dict[str, SearchResult],
        rank: dict[str, int],
        ctx: SelectionContext,
    ) -> SelectionResult:
        """Greedy set cover over feasible units, then optional extras."""

        picked: dict[str, SearchResult] = {}
        counts: dict[str, int] = defaultdict(int)
        total_cost = Decimal(0)
        budget = Decimal(str(ctx.budget_cost)) if ctx.budget_cost is not None else None
        uncovered = set(range(len(requirements)))
        serves: dict[str, set[int]] = defaultdict(set)
        by_root: dict[str, _Unit] = {}
        for index, units in enumerate(options):
            for unit in units:
                serves[unit.root].add(index)
                by_root[unit.root] = unit

        def add(unit: _Unit) -> None:
            nonlocal total_cost
            for uid in unit.ids:
                if uid not in picked:
                    picked[uid] = pool[uid]
                    counts[pool[uid].resource.metadata.kind] += 1
                    total_cost += _total_cost([pool[uid]])

        while uncovered:
            best: tuple[int, int, str] | None = None
            for root, served in serves.items():
                gain = len(served & uncovered)
                if not gain:
                    continue
                members = [pool[uid] for uid in by_root[root].ids if uid not in picked]
                if members and _misfit(members, picked, counts, total_cost, budget, ctx) is not None:
                    continue
                key = (-gain, rank[root], root)
                if best is None or key < best:
                    best = key
            if best is None:
                blocked_needs = [requirements[index].need for index in sorted(uncovered)]
                return SelectionResult(
                    (),
                    "no set within the conflict, count, and budget constraints covers: "
                    + "; ".join(blocked_needs) + _judged(requirements),
                    status="abstain",
                )
            add(by_root[best[2]])
            uncovered -= serves[best[2]]

        if self.per_requirement == "all":
            for root in sorted(by_root, key=lambda item: rank[item]):
                members = [pool[uid] for uid in by_root[root].ids if uid not in picked]
                if members and _misfit(members, picked, counts, total_cost, budget, ctx) is None:
                    add(by_root[root])

        ordered = tuple(sorted(picked.values(), key=lambda r: (-r.score, r.resource.metadata.id)))
        return SelectionResult(
            ordered,
            f"covered {len(requirements)} requirement(s) with {len(ordered)} resource(s)" + _judged(requirements),
        )

    def _judge(self, task: str, candidates: list[SearchResult]) -> tuple[Requirement, ...] | None:
        cached = self._reply(_SYSTEM, _prompt(task, candidates))
        if not cached:
            return None
        requirements = parse_requirements(cached, [r.resource.metadata.id for r in candidates])
        if not requirements:
            self._record_failure("requirement judgment", ValueError("reply listed no requirements"))
            return None
        return requirements[: self.max_requirements]

    def _judge_extras(self, task: str, needs: list[str], extras: list[SearchResult]) -> list[tuple[str, ...]]:
        """The extra candidates credited with each need, in the order of ``needs``.

        Nothing is credited when there are no extras or the call fails: the
        first judgment then stands and the selection escalates as before.
        """

        if not extras:
            return [() for _ in needs]
        numbered = "\n".join(f"{position}. {need}" for position, need in enumerate(needs, start=1))
        prompt = _prompt(task, extras).replace("\n\nCandidates:", f"\n\nRequirements:\n{numbered}\n\nCandidates:", 1)
        reply = self._reply(_EXTRA_SYSTEM, prompt)
        return parse_matches(reply, len(needs), [r.resource.metadata.id for r in extras])

    def _reply(self, system_template: str, prompt: str) -> str:
        """The judge's reply to ``prompt``, cached; empty when the call failed."""

        self.last_llm_calls += 1
        system = system_template.format(strict=_STRICT if self.judge == "strict" else "")
        key = hashlib.sha256(json.dumps([system, prompt], ensure_ascii=False).encode("utf-8")).hexdigest()
        cached = self.cache.get(key)
        if cached is None:
            try:
                response = self.llm.complete(
                    [ChatMessage(role="system", content=system), ChatMessage(role="user", content=prompt)]
                )
                cached = response.content
            except BudgetExceededError:
                raise
            except Exception as error:
                self._record_failure("requirement judgment", error)
                cached = ""
            self.cache[key] = cached
        return cached


def _prompt(task: str, candidates: list[SearchResult]) -> str:
    lines = [f"Task: {task}", "", "Candidates:"]
    for result in candidates:
        metadata = result.resource.metadata
        description = re.sub(r"\s+", " ", metadata.description).strip()[:_DESCRIPTION_LIMIT]
        lines.append(f"- id={metadata.id} kind={metadata.kind} name={metadata.name}: {description}")
    return "\n".join(lines)


def parse_requirements(text: str, valid_ids: list[str]) -> tuple[Requirement, ...]:
    """Parse the judge's reply; unknown ids are dropped, duplicates merged.

    The reply may wrap the object in prose or a code fence, and a model
    sometimes follows a first answer with a corrected one; the last JSON
    object with a ``requirements`` list wins. Returns an empty tuple when
    there is none.
    """

    entries = None
    decoder = json.JSONDecoder()
    position = text.find("{")
    while position != -1:
        try:
            payload: Any
            payload, end = decoder.raw_decode(text, position)
        except ValueError:
            position = text.find("{", position + 1)
            continue
        if isinstance(payload, dict) and isinstance(payload.get("requirements"), list):
            entries = payload["requirements"]
        position = text.find("{", end)
    if entries is None:
        return ()
    valid = set(valid_ids)
    parsed: list[Requirement] = []
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        need = entry.get("need")
        ids = entry.get("ids", [])
        if not isinstance(need, str) or not need.strip() or not isinstance(ids, list):
            continue
        credited = tuple(dict.fromkeys(item for item in ids if isinstance(item, str) and item in valid))
        parsed.append(Requirement(need.strip(), credited))
    return tuple(parsed)


def parse_matches(text: str, count: int, valid_ids: list[str]) -> list[tuple[str, ...]]:
    """Parse the second call's reply: the valid ids credited to requirements 1..``count``.

    As in ``parse_requirements`` the last JSON object with a ``matches`` list
    wins; a missing or malformed entry credits nothing.
    """

    entries: list[Any] = []
    decoder = json.JSONDecoder()
    position = text.find("{")
    while position != -1:
        try:
            payload: Any
            payload, end = decoder.raw_decode(text, position)
        except ValueError:
            position = text.find("{", position + 1)
            continue
        if isinstance(payload, dict) and isinstance(payload.get("matches"), list):
            entries = payload["matches"]
        position = text.find("{", end)
    valid = set(valid_ids)
    credited: list[tuple[str, ...]] = [() for _ in range(count)]
    for entry in entries:
        if not isinstance(entry, dict) or not isinstance(entry.get("ids"), list):
            continue
        number = entry.get("requirement")
        if isinstance(number, bool) or not isinstance(number, int) or not 1 <= number <= count:
            continue
        credited[number - 1] = tuple(dict.fromkeys(i for i in entry["ids"] if isinstance(i, str) and i in valid))
    return credited


def _judged(requirements: tuple[Requirement, ...]) -> str:
    rendered = "; ".join(f"{item.need} -> {', '.join(item.ids) or '(none)'}" for item in requirements)
    return f" [requirements: {rendered}]"
