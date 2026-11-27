from __future__ import annotations

import hashlib
import json
import re
import subprocess
import sys
import tempfile
import unittest
from argparse import Namespace
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "benchmarks"))

import _provenance  # noqa: E402
import run_ann_scale_benchmark  # noqa: E402
import run_toolret_benchmark  # noqa: E402
from _provenance import sha256_file, sha256_tree, stamp  # noqa: E402
from generate_scale_corpus import build_scale_corpus  # noqa: E402
from marmo_core import HashingEmbeddingProvider, HybridRetriever  # noqa: E402

REVISION = "0123456789abcdef0123456789abcdef01234567"


def git(directory: Path, *arguments: str) -> str:
    completed = subprocess.run(
        ["git", "-c", "user.name=test", "-c", "user.email=test@example.com", "-C", str(directory), *arguments],
        capture_output=True, text=True, check=True,
    )
    return completed.stdout.strip()


class StampTests(unittest.TestCase):
    def test_commit_is_the_full_sha_and_dirty_ignores_result_files(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            repository = Path(temporary)
            (repository / "benchmarks" / "results").mkdir(parents=True)
            (repository / "module.py").write_text("x = 1\n", encoding="utf-8")
            (repository / "benchmarks" / "results" / "r.json").write_text("{}", encoding="utf-8")
            git(repository, "init", "-q")
            git(repository, "add", ".")
            git(repository, "commit", "-q", "-m", "init")

            commit = _provenance._library_commit(repository)
            self.assertEqual(commit, git(repository, "rev-parse", "HEAD"))
            self.assertRegex(commit or "", r"[0-9a-f]{40}")
            self.assertFalse(_provenance._library_dirty(repository))
            (repository / "benchmarks" / "results" / "r.json").write_text('{"new": 1}', encoding="utf-8")
            self.assertFalse(_provenance._library_dirty(repository))
            (repository / "module.py").write_text("x = 2\n", encoding="utf-8")
            self.assertTrue(_provenance._library_dirty(repository))

    def test_stamp_records_commit_environment_and_run_conditions(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            data = Path(temporary) / "data"
            (data / "tools").mkdir(parents=True)
            (data / "tools" / "web.parquet").write_bytes(b"tools")
            report = stamp(
                {},
                dataset={"mangopy/ToolRet-Tools": {"repo": "mangopy/ToolRet-Tools", "revision": REVISION}},
                inputs=sha256_tree(data),
                model={"embedding": "m", "query_prefix": ""},
                arguments=Namespace(per_subset=60, output=ROOT / "benchmarks" / "results" / "x.json"),
            )
        provenance = report["provenance"]
        self.assertEqual(provenance["schema"], 2)
        self.assertEqual(provenance["dataset"]["mangopy/ToolRet-Tools"]["revision"], REVISION)
        self.assertEqual(provenance["inputs"], {"tools/web.parquet": hashlib.sha256(b"tools").hexdigest()})
        self.assertEqual(provenance["model"], {"embedding": "m", "query_prefix": ""})
        self.assertEqual(provenance["arguments"], {"per_subset": 60, "output": "benchmarks/results/x.json"})
        self.assertIn("numpy", provenance["dependencies"])
        self.assertIn("marmo_core_dirty", provenance)
        commit = report["marmo_core_commit"]
        self.assertTrue(commit is None or re.fullmatch(r"[0-9a-f]{40}", commit), commit)
        json.dumps(report)

    def test_stamp_without_run_conditions_keeps_the_legacy_fields(self) -> None:
        report = stamp({"x": 1})
        self.assertEqual({"marmo_core_version", "marmo_core_commit", "generated_at", "provenance"} - set(report), set())
        self.assertNotIn("dataset", report["provenance"])

    def test_a_dataset_branch_name_is_refused(self) -> None:
        for revision in ("main", "v1", REVISION[:7], REVISION.upper(), None):
            with self.subTest(revision=revision):
                with self.assertRaisesRegex(ValueError, "40-hex"):
                    stamp({}, dataset={"d": {"repo": "d", "revision": revision}})

    def test_hash_helpers(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "b").mkdir()
            (root / "b" / "two.txt").write_bytes(b"2")
            (root / "one.txt").write_bytes(b"1")
            self.assertEqual(sha256_file(root / "one.txt"), hashlib.sha256(b"1").hexdigest())
            self.assertEqual(list(sha256_tree(root)), ["b/two.txt", "one.txt"])


class ToolRetProvenanceTests(unittest.TestCase):
    def test_dataset_provenance_comes_from_the_pinned_revisions_of_toolret(self) -> None:
        revisions = {"ToolRet-Tools": REVISION, "ToolRet-Queries": REVISION[::-1]}
        with mock.patch.object(run_toolret_benchmark.toolret, "DATASET_REVISIONS", revisions, create=True):
            recorded = run_toolret_benchmark.dataset_provenance()
        self.assertEqual(recorded["mangopy/ToolRet-Queries"], {"repo": "mangopy/ToolRet-Queries", "revision": REVISION[::-1]})
        stamp({}, dataset=recorded)

    def test_cache_inputs_lists_only_the_caches_the_run_replays(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            paths = {name: Path(temporary) / f"{name}.json" for name in ("decomposition", "rerank", "select", "translation")}
            for path in paths.values():
                path.write_text("{}", encoding="utf-8")
            with mock.patch.multiple(
                run_toolret_benchmark, DECOMPOSITION_CACHE=paths["decomposition"], RERANK_CACHE=paths["rerank"],
                SET_SELECT_CACHE=paths["select"], TRANSLATION_CACHE=paths["translation"],
            ):
                self.assertEqual(run_toolret_benchmark.cache_inputs(["lexical", "hybrid-0.5"], "en"), {})
                self.assertEqual(set(run_toolret_benchmark.cache_inputs(["llm:hybrid-0.5"], "en")), {"decomposition_cache"})
                self.assertEqual(
                    set(run_toolret_benchmark.cache_inputs(["rerank:llm!:hybrid-0.5", "llm!:hybrid-0.5"], "en")),
                    {"decomposition_cache", "rerank_cache", "set_select_cache"},
                )
                self.assertEqual(set(run_toolret_benchmark.cache_inputs(["lexical"], "ja")), {"translation_cache"})


class _MemoizingHashProvider(HashingEmbeddingProvider):
    """Remembers which texts it has embedded, like the model provider does."""

    created: list["_MemoizingHashProvider"] = []

    def __init__(self, dimensions: int = 64) -> None:
        super().__init__(dimensions=dimensions)
        self.computed: set[str] = set()
        self.created.append(self)

    def embed(self, texts):
        self.computed.update(texts)
        return super().embed(texts)


class _FlatWithoutAnn(HybridRetriever):
    """Stands in for the USearch arm, which needs an optional dependency."""

    def __init__(self, provider, *, pool: int = 50, weight: float = 0.9) -> None:
        super().__init__(provider, semantic_weight=weight, candidate_pool=pool)
        self.index_seconds = 0.0
        self.index_bytes = 0


class AnnFirstBuildTests(unittest.TestCase):
    def test_each_arm_embeds_the_corpus_with_its_own_provider(self) -> None:
        _MemoizingHashProvider.created = []
        with tempfile.TemporaryDirectory() as temporary:
            corpus = Path(temporary) / "scale.json"
            corpus.write_text(json.dumps({"resources": build_scale_corpus(150)}), encoding="utf-8")
            with mock.patch.multiple(
                run_ann_scale_benchmark, FlatAnnHybrid=_FlatWithoutAnn,
                HashingEmbeddingProvider=_MemoizingHashProvider, ensure_scale_corpus=lambda size: corpus,
            ):
                report = run_ann_scale_benchmark.run(size=150, embedding="hash", pool=20, route_k=2, min_relevance=0.35)
        self.assertEqual(len(_MemoizingHashProvider.created), 2)
        flat_provider, hierarchical_provider = _MemoizingHashProvider.created
        for provider in (flat_provider, hierarchical_provider):
            self.assertGreaterEqual(len(provider.computed), report["corpus_size"])
        for arm in report["retrievers"].values():
            self.assertGreater(arm["cold_start"]["document_embedding_seconds"], 0.0)
        self.assertIn("independent", report["embedding_cache"])
        self.assertLessEqual(report["flat_ann_index_seconds_excluding_embeddings"],
                             report["flat_ann_index_seconds_including_embeddings"])
        self.assertEqual(set(report["provenance"]["inputs"]),
                         {"set_corpus.json", "scale_corpus_150.json", "set_scenarios.json", "scale_scenarios.json"})
        self.assertEqual(report["provenance"]["arguments"]["pool"], 20)


if __name__ == "__main__":
    unittest.main()
