"""Multi-intent retrieval: split a goal into sub-tasks and search each one.

A goal such as "find the lead actor of Black Mirror's second season and show
what they look like" needs several resources, but a single ranked search
scores every candidate against the whole sentence. The resource for the
dominant sub-task takes the top ranks and the others, each relevant to only
part of the goal, fall below the cut: the set is incomplete before any set
selector sees it. On ToolRet (44,453 tools, multi-tool gold sets) the plain
lexical search puts *every* gold tool of a multi-tool query in its top 10 for
only 6.5% of those queries.

``DecomposedRetriever`` searches the full goal and every sub-task with the
same inner retriever and fuses the rankings, so each sub-task's best match
moves toward the top. Each fused result also records its relevance to
every sub-task (the ``facet.<i>`` components, ``facet.0`` being the full
goal), which ``CoverageSetSelector`` uses to choose a set that covers the
sub-tasks without redundant members.

Two decomposers are provided:

- ``LLMQueryDecomposer`` — one LLM call that also names implicit
  prerequisites ("look up the show's id" before "get its cast"). It degrades
  to no decomposition on any failure, logged like the other LLM-assisted
  layers. This is the one to use: on ToolRet it wrongly split 34% of the
  single-tool queries, against 60% for the rules below, and the fusion gain
  depends on how rarely a single need is split.
- ``ClauseQueryDecomposer`` — zero-dependency rules for needs a goal states
  explicitly: separate sentences, numbered or bulleted lists, ``;`` and
  connectives such as "and then", "also", "after that", and the Japanese
  equivalents. It is a baseline, not a recommendation: it split 60% of
  ToolRet's single-tool queries, and its sub-tasks did not improve the
  ranking (no significant difference over hybrid search, lower over BM25
  alone; ``benchmarks/README.md``).
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import replace
from typing import MutableMapping, Sequence
import json
import re

from .budget import BudgetExceededError
from .llm import ChatMessage, LLMProvider
from .llm_routing import _LLMFailureTracker
from .models import SearchQuery, SearchResult
from .registry import ResourceRegistry
from .retriever import RELEVANCE_WEIGHT, LexicalRetriever, Retriever, _tokens as tokenize

FACET_PREFIX = "facet."


class QueryDecomposer(ABC):
    """Splits a goal into sub-tasks. Implementations are swappable."""

    @abstractmethod
    def decompose(self, task: str) -> list[str]:
        """The goal's sub-tasks, or an empty list when it states a single need."""


# Sentence ends, newlines, and list markers ("1.", "2)", "-", "*", "•").
_SENTENCE_RE = re.compile(r"(?<=[.!?。！？])\s+|\n+|(?:^|\s)(?:\d{1,2}[.)]|[-*•])\s+")
# Connectives that start a new need inside one sentence.
_CONNECTIVE_RE = re.compile(
    r"\s*[;；]\s*"
    r"|,?\s+(?:and\s+then|and\s+also|then|also|additionally|furthermore|moreover|"
    r"as\s+well\s+as|after\s+that|afterwards|finally)\s+"
    r"|、?(?:そして|それから|その後|また、|さらに|次に)"
    r"|(?<=[てで])から、?|した後(?:に|で)?、?",
    re.IGNORECASE,
)
_AND_RE = re.compile(r",?\s+and\s+", re.IGNORECASE)
# Words of a request's framing ("could you please tell me"), not of its need.
_FRAMING_TERMS = frozenset(
    "i i'm im me my we us our you your can could would will shall should please kindly "
    "help want need like also just so then this that these those some any what how "
    "on at by be am was were do does did have has had get tell show give let make sure".split()
)


def _content_terms(text: str) -> list[str]:
    return [term for term in tokenize(text) if term not in _FRAMING_TERMS]


class ClauseQueryDecomposer(QueryDecomposer):
    """Rule-based decomposition of explicitly stated needs (zero dependencies).

    The goal is split into sentences and list items, then at connectives
    that introduce another need. A plain "and" splits only when both sides
    keep more than ``min_terms`` content terms, so "salt and pepper" stays one
    need while "book a flight and reserve a hotel near the venue" becomes
    two. Content terms exclude the framing of a request ("could you please
    tell me"); fragments with fewer than ``min_terms`` of them ("Could you",
    "Thanks!") are dropped, duplicates are removed, and at most
    ``max_subtasks`` are returned. A goal that yields one fragment states a
    single need and returns an empty list.
    """

    def __init__(self, *, min_terms: int = 2, max_subtasks: int = 8, split_and: bool = True) -> None:
        if min_terms < 1:
            raise ValueError("min_terms must be at least 1")
        if max_subtasks < 1:
            raise ValueError("max_subtasks must be at least 1")
        self.min_terms = min_terms
        self.max_subtasks = max_subtasks
        self.split_and = split_and

    def decompose(self, task: str) -> list[str]:
        fragments: list[str] = []
        for sentence in _SENTENCE_RE.split(task):
            for clause in _CONNECTIVE_RE.split(sentence):
                fragments.extend(self._split_and(clause))
        subtasks: list[str] = []
        seen: set[tuple[str, ...]] = set()
        for fragment in fragments:
            cleaned = fragment.strip(" \t,.;:!?-*•、。")
            terms = tuple(_content_terms(cleaned))
            if len(terms) < self.min_terms or terms in seen:
                continue
            seen.add(terms)
            subtasks.append(cleaned)
        if len(subtasks) < 2:
            return []
        return subtasks[: self.max_subtasks]

    def _split_and(self, clause: str) -> list[str]:
        if not self.split_and:
            return [clause]
        parts = _AND_RE.split(clause)
        if len(parts) < 2:
            return [clause]
        merged = [parts[0]]
        for part in parts[1:]:
            if len(_content_terms(merged[-1])) > self.min_terms and len(_content_terms(part)) > self.min_terms:
                merged.append(part)
            else:
                merged[-1] = f"{merged[-1]} and {part}"
        return merged


_DECOMPOSE_SYSTEM = (
    "You plan tool use for an AI agent. Split the user's task into the minimal "
    "ordered list of sub-tasks, where each sub-task needs exactly one tool or "
    "capability. Include prerequisite steps the task implies but does not state, "
    "such as looking up an id, a token, or a location before using it. Do not "
    "split a single action into several steps, and do not add steps for "
    "answering, summarizing, or replying to the user. Write each sub-task as a "
    "short imperative phrase in English. Reply with a JSON array of strings and "
    "nothing else; reply with a one-element array when the task needs one tool."
)


class LLMQueryDecomposer(_LLMFailureTracker, QueryDecomposer):
    """Decompose a goal with one LLM call, including implicit prerequisites.

    The reply must be a JSON array of strings; anything else, or a failed
    call, counts as a failure (logged once at WARNING, then DEBUG, with
    ``failures`` / ``last_failure`` on the instance) and yields no
    decomposition, so retrieval falls back to the full goal. Replies that
    parse are cached per task in ``cache``; failures are not, so they are
    retried.
    """

    def __init__(
        self,
        llm: LLMProvider,
        *,
        max_subtasks: int = 8,
        cache: MutableMapping[str, str] | None = None,
    ) -> None:
        super().__init__()
        if max_subtasks < 1:
            raise ValueError("max_subtasks must be at least 1")
        self.llm = llm
        self.max_subtasks = max_subtasks
        self.cache = cache if cache is not None else {}

    def decompose(self, task: str) -> list[str]:
        task = task.strip()
        if not task:
            return []
        reply = self.cache.get(task)
        if reply is None:
            try:
                response = self.llm.complete(
                    [ChatMessage(role="system", content=_DECOMPOSE_SYSTEM), ChatMessage(role="user", content=task)]
                )
                reply = response.content
            except BudgetExceededError:
                raise
            except Exception as error:
                self._record_failure("query decomposition", error)
                return []
        subtasks = parse_subtasks(reply)
        if subtasks is None:
            # Not cached, so the next search asks again instead of replaying it.
            self._record_failure("query decomposition", ValueError(f"reply is not a JSON array of strings: {reply[:120]!r}"))
            return []
        self.cache[task] = reply
        unique = list(dict.fromkeys(item for item in subtasks if tokenize(item)))
        return unique[: self.max_subtasks] if len(unique) > 1 else []


def parse_subtasks(reply: str) -> list[str] | None:
    """The JSON array of strings in an LLM reply (code fences allowed), or None."""

    text = reply.strip()
    fenced = re.search(r"```(?:json)?\s*(.*?)```", text, re.DOTALL)
    if fenced:
        text = fenced.group(1).strip()
    start, end = text.find("["), text.rfind("]")
    if start < 0 or end <= start:
        return None
    try:
        value = json.loads(text[start : end + 1])
    except ValueError:
        return None
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        return None
    return [item.strip() for item in value if item.strip()]


class DecomposedRetriever(Retriever):
    """Search the goal and each of its sub-tasks, then fuse the rankings.

    The inner retriever runs once for the full goal and once per sub-task
    (``1 + len(subtasks)`` searches; a goal with no sub-tasks is a single
    pass-through search).

    The default ``fusion="blend"`` ranks by the goal relevance plus
    ``facet_weight`` times the best sub-task relevance, normalized:
    ``(a * g + w * max_n f_n) / (a + w)``, swapped into the composite score
    the way ``HybridRetriever`` swaps in its blended relevance, so the policy
    components still order ties. The goal keeps the lead and a resource that
    serves one sub-task well moves up past ones that serve none. ``w`` = 0.25
    was chosen on a ToolRet dev split. ``fusion="rrf"`` is Reciprocal Rank
    Fusion instead, the goal's list weighted ``goal_weight``; it was weaker
    on the same data.

    ``a`` is the share of the goal's distinct terms that occur anywhere in the
    catalog (``discount_unknown_terms=True``; 1.0 when off). Relevance is
    measured against the terms a catalog knows, so a goal written in another
    language than the catalog -- a Japanese request over English tool
    descriptions -- scores its few known tokens (names, numbers) as strong
    matches. Counting the unknown terms as unmatched hands the ranking to the
    sub-tasks, which ``LLMQueryDecomposer`` writes in English. On ToolRet the
    share averages 0.92 for English goals and 0.32 for Japanese translations
    of them; the discount left English nDCG@10 unchanged and raised Japanese
    nDCG@10 from 0.046 to 0.115 (``benchmarks/README.md``). The index is the
    inner retriever's own when it is, or wraps, a ``LexicalRetriever``;
    otherwise one is built per registry content revision. The share is
    lexical: with a multilingual embedding model behind ``HybridRetriever``
    the goal's relevance can be sound in any language, so turn the discount
    off there. It is not applied when ``facet_weight`` is 0.
    ``last_goal_weight`` holds the ``a`` of the most recent search (1.0 when
    it was not decomposed or not blended).

    Every result records its relevance to each list as ``facet.0`` (the goal)
    to ``facet.<n>`` (sub-task n), 0.0 where it was not retrieved for that
    list, for ``CoverageSetSelector``. Its ``relevance`` — what selectors
    threshold — is the strongest relevance it reached for the goal or any
    one sub-task. ``last_subtasks`` holds the most recent decomposition.
    """

    def __init__(
        self,
        inner: Retriever,
        decomposer: QueryDecomposer,
        *,
        depth: int = 50,
        fusion: str = "blend",
        facet_weight: float = 0.25,
        goal_weight: float = 1.0,
        rrf_k: int = 60,
        discount_unknown_terms: bool = True,
    ) -> None:
        if depth < 1:
            raise ValueError("depth must be at least 1")
        if fusion not in FUSIONS:
            raise ValueError(f"fusion must be one of: {', '.join(FUSIONS)}")
        if facet_weight < 0.0 or goal_weight < 0.0:
            raise ValueError("facet_weight and goal_weight must be non-negative")
        if rrf_k < 1:
            raise ValueError("rrf_k must be at least 1")
        self.inner = inner
        self.decomposer = decomposer
        self.depth = depth
        self.fusion = fusion
        self.facet_weight = facet_weight
        self.goal_weight = goal_weight
        self.rrf_k = rrf_k
        self.discount_unknown_terms = discount_unknown_terms
        self.last_subtasks: list[str] = []
        self.last_goal_weight = 1.0
        self._limits = LexicalRetriever()

    def search(self, registry: ResourceRegistry, query: SearchQuery) -> list[SearchResult]:
        subtasks = self.decomposer.decompose(query.task) if query.task.strip() else []
        self.last_subtasks = subtasks
        self.last_goal_weight = 1.0
        if not subtasks:
            return self.inner.search(registry, query)
        widened = replace(query, top_k=max(query.top_k, self.depth), per_kind_limits={}, min_score=0.0)
        lists = [self.inner.search(registry, widened)]
        lists += [self.inner.search(registry, replace(widened, task=subtask)) for subtask in subtasks]
        if self.fusion == "blend":
            # With no weight on the sub-tasks there is nothing to hand the ranking to.
            if self.discount_unknown_terms and self.facet_weight > 0.0:
                self.last_goal_weight = self._known_term_share(registry, query.task)
            fused = blend_facet_rankings(lists, self.facet_weight, goal_weight=self.last_goal_weight)
        else:
            fused = rrf_facet_rankings(lists, self.goal_weight, self.rrf_k)
        return self._limits.apply_limits([result for result in fused if result.score >= query.min_score], query)

    def _known_term_share(self, registry: ResourceRegistry, task: str) -> float:
        """Share of the goal's distinct terms that occur anywhere in the catalog."""

        terms = set(tokenize(task))
        if not terms:
            return 1.0
        owner = next(
            (
                candidate
                for candidate in (self.inner, getattr(self.inner, "lexical", None))
                if isinstance(candidate, LexicalRetriever)
            ),
            self._limits,
        )
        postings = owner._index_for(registry).postings
        return sum(1 for term in terms if term in postings) / len(terms)


FUSIONS = ("blend", "rrf")


def _facet_table(lists: Sequence[Sequence[SearchResult]]) -> tuple[dict[str, list[float]], dict[str, list[SearchResult | None]]]:
    relevances: dict[str, list[float]] = {}
    results: dict[str, list[SearchResult | None]] = {}
    for position, ranked in enumerate(lists):
        for result in ranked:
            identity = result.resource.identity
            relevances.setdefault(identity, [0.0] * len(lists))[position] = float(result.components.get("relevance", 0.0))
            results.setdefault(identity, [None] * len(lists))[position] = result
    return relevances, results


def _annotated(result: SearchResult, relevances: list[float], score: float, extra: dict[str, float]) -> SearchResult:
    components = dict(result.components)
    components.update({f"{FACET_PREFIX}{index}": value for index, value in enumerate(relevances)})
    components["relevance"] = max(relevances)
    components.update(extra)
    return SearchResult(result.resource, max(0.0, min(1.0, score)), result.reasons, components)


def blend_facet_rankings(
    lists: Sequence[Sequence[SearchResult]], facet_weight: float, *, goal_weight: float = 1.0
) -> list[SearchResult]:
    """Rank by ``(a * goal relevance + w * best sub-task relevance) / (a + w)``; ``lists[0]`` is the goal's."""

    relevances, results = _facet_table(lists)
    fused: list[SearchResult] = []
    for identity, values in relevances.items():
        per_list = results[identity]
        base = per_list[0] or max((r for r in per_list if r is not None), key=lambda r: r.score)
        best_subtask = max(values[1:], default=0.0)
        total = goal_weight + facet_weight
        blended = (goal_weight * values[0] + facet_weight * best_subtask) / total if total else 0.0
        base_relevance = float(base.components.get("relevance", 0.0))
        score = base.score + RELEVANCE_WEIGHT * (blended - base_relevance)
        fused.append(_annotated(base, values, score, {"facet_blend": blended}))
    fused.sort(key=_fused_order)
    return fused


def _fused_order(item: SearchResult) -> tuple[float, bool, str]:
    # Untrusted resources lose ties, as in LexicalRetriever.
    return (-item.score, item.resource.metadata.trust_level == "untrusted", item.resource.metadata.id)


def rrf_facet_rankings(lists: Sequence[Sequence[SearchResult]], goal_weight: float, rrf_k: int = 60) -> list[SearchResult]:
    """Reciprocal Rank Fusion of the goal's list (weight ``goal_weight``) and each sub-task's (weight 1)."""

    relevances, results = _facet_table(lists)
    weights = [goal_weight] + [1.0] * (len(lists) - 1)
    fused_values: dict[str, float] = {}
    for position, ranked in enumerate(lists):
        for rank, result in enumerate(ranked, start=1):
            identity = result.resource.identity
            fused_values[identity] = fused_values.get(identity, 0.0) + weights[position] / (rrf_k + rank)
    ceiling = sum(weights) / (rrf_k + 1)
    fused: list[SearchResult] = []
    for identity, value in fused_values.items():
        base = max((r for r in results[identity] if r is not None), key=lambda r: r.score)
        score = value / ceiling if ceiling else 0.0
        fused.append(_annotated(base, relevances[identity], score, {"rrf": score}))
    fused.sort(key=_fused_order)
    return fused
