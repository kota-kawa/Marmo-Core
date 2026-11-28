"""Fill the ToolRet LLM caches for decomposition, re-ranking, and set selection.

    python3 benchmarks/run_toolret_llm_stages.py --stage decompose --workers 8
    python3 benchmarks/run_toolret_llm_stages.py --stage rerank --stage select --workers 8
    python3 benchmarks/run_toolret_llm_stages.py --stage translate-ja --stage decompose

Every stage runs the library's own component unchanged — ``LLMQueryDecomposer``,
``LLMRerankRetriever``, ``LLMSetSelector`` — against the Claude Code CLI
(``benchmarks/_claude_cli.py``), with replies cached under benchmarks/cache.
``run_toolret_benchmark.py`` replays the caches, so scoring never calls a model.

Re-ranking and set selection see the candidates of ``--base`` decomposed with the
cached LLM sub-tasks, without the unknown-term discount (``llm!:<base>``): the re-ranker the top ``--rerank-pool``, the
set selector the top ``--select-pool``. ``translate-ja`` translates ``--ja-per-subset``
test-split queries per subset into Japanese (the cross-lingual run of
``run_toolret_benchmark.py --language ja``); ``decompose`` then covers them too.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).parent))

from marmo_core.llm import ChatMessage  # noqa: E402
from marmo_core import (  # noqa: E402
    LLMQueryDecomposer,
    LLMRerankRetriever,
    LLMSetSelector,
    Retriever,
    SearchQuery,
    SelectionContext,
)

import toolret  # noqa: E402
from _claude_cli import ClaudeCLIProvider, add_spend_arguments, ledger_from_arguments  # noqa: E402
from run_toolret_benchmark import (  # noqa: E402
    DECOMPOSITION_CACHE,
    TRANSLATION_CACHE,
    split_of,
    RERANK_CACHE,
    SET_SELECT_CACHE,
    POOL,
    build_retriever,
)


TRANSLATE_SYSTEM = (
    "Translate each task in the JSON object into natural Japanese, the way a Japanese user would ask an "
    "AI assistant. Keep names, numbers, quoted strings, URLs, and code identifiers unchanged. Reply with a "
    "JSON object mapping the same keys to the translations and nothing else."
)


def japanese_sample(queries, per_subset: int) -> list:
    """The first ``per_subset`` test-split queries of every subset, by id."""

    by_subset: dict[str, list] = {}
    for query in sorted(queries, key=lambda q: q.id):
        if split_of(query.id) == "test":
            by_subset.setdefault(query.subset, []).append(query)
    return [query for subset in sorted(by_subset) for query in by_subset[subset][:per_subset]]


class Precomputed(Retriever):
    """Replays stored candidate lists, so LLM stages run without re-searching."""

    def __init__(self, lists: dict) -> None:
        self.lists = lists

    def search(self, registry, query):
        return self.lists[query.task][: query.top_k]


class LockedCache(dict):
    """A reply cache that worker threads write while the main thread saves it."""

    lock = threading.Lock()

    def __setitem__(self, key, value) -> None:
        with self.lock:
            super().__setitem__(key, value)

    def snapshot(self) -> dict:
        with self.lock:
            return dict(self)


def load(path: Path) -> LockedCache:
    cache = LockedCache()
    if path.exists():
        cache.update(json.loads(path.read_text(encoding="utf-8")))
    return cache


def save(path: Path, cache: LockedCache) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(cache.snapshot(), ensure_ascii=False, indent=1, sort_keys=True) + "\n"
    path.write_text(text, encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument(
        "--stage", action="append", choices=["translate-ja", "decompose", "rerank", "select"], required=True
    )
    parser.add_argument("--per-subset", type=int, default=60)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--model", default="sonnet", help="sonnet or haiku (or a full id of those families)")
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--limit", type=int, default=0, help="first N queries of the split (0 = all)")
    parser.add_argument("--sample", type=int, default=0,
                        help="N queries of the split in SHA-1 order of the id, as in run_toolret_sae.py (0 = all)")
    parser.add_argument("--base", default="hybrid-0.5")
    parser.add_argument("--embed-model", default="sentence-transformers/all-MiniLM-L6-v2")
    parser.add_argument("--rerank-pool", type=int, default=30)
    parser.add_argument("--select-pool", type=int, default=20)
    parser.add_argument("--ja-per-subset", type=int, default=6, help="test-split queries per subset to translate")
    parser.add_argument("--split", choices=["all", "dev", "test", "heldout"], default="all",
                        help="restrict the queries to one split; heldout is the frozen ToolRet-SAE held-out split")
    add_spend_arguments(parser)
    args = parser.parse_args()
    ledger = ledger_from_arguments(parser, args)

    every = toolret.load_queries()
    queries = toolret.sample_queries(every, args.per_subset or None, seed=args.seed)
    if args.split == "heldout":
        queries = toolret.load_heldout(every)
    elif args.split != "all":
        queries = [query for query in queries if split_of(query.id) == args.split]
    if args.sample:
        queries = sorted(queries, key=lambda q: hashlib.sha1(q.id.encode("utf-8")).hexdigest())[: args.sample]
    if args.limit:
        queries = queries[: args.limit]
    tasks = list(dict.fromkeys(query.query for query in queries))
    try:
        llm = ClaudeCLIProvider(args.model, ledger=ledger)
    except ValueError as error:
        parser.error(str(error))
    lock = threading.Lock()
    jobs: list = []
    caches: dict[Path, LockedCache] = {}

    if "translate-ja" in args.stage:
        translations = caches.setdefault(TRANSLATION_CACHE, load(TRANSLATION_CACHE))
        chosen = japanese_sample(queries, args.ja_per_subset)
        pending = [query for query in chosen if query.id not in translations]
        jobs.extend(("translate-ja", pending[start : start + 15]) for start in range(0, len(pending), 15))
    if "decompose" in args.stage:
        cache = caches.setdefault(DECOMPOSITION_CACHE, load(DECOMPOSITION_CACHE))
        # Japanese versions of the sample are decomposed too, once translated.
        for task in tasks + list(load(TRANSLATION_CACHE).values()):
            if task.strip() not in cache:
                jobs.append(("decompose", task))

    registry = candidates = None
    if {"rerank", "select"} & set(args.stage):
        tools = toolret.load_tools()
        registry, _ = toolret.build_registry(tools)
        provider = toolret.CachedEmbeddingProvider(args.embed_model)
        # The undiscounted pool the committed caches were built from (llm!:<base>).
        retriever = build_retriever(f"llm!:{args.base}", provider, load(DECOMPOSITION_CACHE))
        started = time.time()
        candidates = {task: retriever.search(registry, SearchQuery(task=task, top_k=POOL)) for task in tasks}
        provider.save()
        print(f"retrieved candidates for {len(tasks)} tasks in {time.time() - started:.0f}s", flush=True)
        for stage, path in (("select", SET_SELECT_CACHE), ("rerank", RERANK_CACHE)):
            if stage in args.stage:
                caches.setdefault(path, load(path))
                jobs.extend((stage, task) for task in tasks)

    print(f"{len(jobs)} jobs", flush=True)
    done = 0

    def work(job) -> None:
        nonlocal done
        stage, task = job
        if stage == "translate-ja":
            path = TRANSLATION_CACHE
            reply = llm.complete(
                [
                    ChatMessage(role="system", content=TRANSLATE_SYSTEM),
                    ChatMessage(role="user", content=json.dumps({query.id: query.query for query in task}, ensure_ascii=False)),
                ]
            ).content
            parsed = json.loads(reply[reply.find("{") : reply.rfind("}") + 1])
            for query in task:
                if isinstance(parsed.get(query.id), str) and parsed[query.id].strip():
                    caches[path][query.id] = parsed[query.id].strip()
        elif stage == "decompose":
            path = DECOMPOSITION_CACHE
            LLMQueryDecomposer(llm, cache=caches[path]).decompose(task)
        elif stage == "rerank":
            path = RERANK_CACHE
            component = LLMRerankRetriever(llm, Precomputed(candidates), rerank_pool=args.rerank_pool, cache=caches[path])
            component.search(registry, SearchQuery(task=task, top_k=args.rerank_pool))
        else:
            path = SET_SELECT_CACHE
            selector = LLMSetSelector(llm, cache=caches[path])
            selector.select(candidates[task][: args.select_pool], context=SelectionContext(task=task))
        with lock:
            done += 1
            if done % 100 == 0:
                for cache_path, cache in caches.items():
                    save(cache_path, cache)
                print(f"  {done}/{len(jobs)}", flush=True)

    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        list(pool.map(work, jobs))
    for cache_path, cache in caches.items():
        save(cache_path, cache)
    print("done", {str(path.name): len(cache) for path, cache in caches.items()})
    if ledger is not None:
        print("spend ledger", ledger.snapshot())


if __name__ == "__main__":
    main()
