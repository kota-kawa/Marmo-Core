"""Tests for the developer-only skill collector under tools/ (offline: fetch functions are replaced)."""

from __future__ import annotations

from pathlib import Path
from unittest import mock
import contextlib
import hashlib
import importlib.util
import io
import json
import os
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"

COMMIT = "a" * 40
SKILL_MD = b"---\nname: Demo\ndescription: A demo skill\n---\nBody\n"
HELPER = b"print('helper')\n" * 10


def _load(name: str):
    spec = importlib.util.spec_from_file_location(f"tools_{name}", TOOLS / f"{name}.py")
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    with mock.patch.dict(os.environ, {"GH_TOKEN": "test-token"}):
        os.environ.pop("OUT_DIR", None)
        spec.loader.exec_module(module)
    return module


def _blob_sha(data: bytes) -> str:
    return hashlib.sha1(b"blob %d\0" % len(data) + data).hexdigest()


class FakeGitHub:
    """Serves one repository with one skill folder, and records which refs were asked for."""

    def __init__(self, files: dict[str, bytes] | None = None) -> None:
        self.files = files if files is not None else {"skills/demo/SKILL.md": SKILL_MD, "skills/demo/helper.py": HELPER}
        self.tree_refs: list[str] = []
        self.raw_refs: list[str] = []
        self.failing_paths: set[str] = set()
        self.failing_after: dict[str, int] = {}
        self.corrupt_paths: set[str] = set()
        self.truncated = False
        self.requests: dict[str, int] = {}

    def api_get(self, path, params=None, raw=False, retries=4):
        if path == "/repos/octo/skills":
            return {"license": {"spdx_id": "MIT"}, "default_branch": "main"}
        if path == "/repos/octo/skills/commits/main":
            return {"sha": COMMIT}
        if path.startswith("/repos/octo/skills/git/trees/"):
            self.tree_refs.append(path.rsplit("/", 1)[1])
            return {
                "truncated": self.truncated,
                "tree": [
                    {"type": "blob", "path": p, "size": len(data), "sha": _blob_sha(data)}
                    for p, data in self.files.items()
                ],
            }
        raise AssertionError(f"unexpected API request {path}")

    def raw_get(self, repo, ref, path):
        self.raw_refs.append(ref)
        self.requests[path] = self.requests.get(path, 0) + 1
        if path in self.failing_paths:
            return None
        if path in self.failing_after and self.requests[path] > self.failing_after[path]:
            return None
        data = self.files[path]
        return data + b"tampered" if path in self.corrupt_paths else data


@unittest.skipUnless(TOOLS.is_dir(), "tools/ is not part of this distribution")
class CollectSkillsTests(unittest.TestCase):
    def setUp(self) -> None:
        self.collect = _load("collect_skills")
        self.collect.STOP.clear()
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.out = Path(self.tmp.name) / "skills"
        self.out.mkdir()
        self.manifest_file = open(self.out / "manifest.jsonl", "a", encoding="utf-8")
        self.addCleanup(self.manifest_file.close)
        self.github = FakeGitHub()

    def run_repo(self, pins: dict[str, str] | None = None) -> bool:
        ctx = self.collect.Ctx(set(), set(), 0, self.manifest_file, str(self.out), pins)
        self.ctx = ctx
        with (
            mock.patch.object(self.collect, "api_get", self.github.api_get),
            mock.patch.object(self.collect, "raw_get", self.github.raw_get),
            contextlib.redirect_stdout(io.StringIO()),
        ):
            return self.collect.process_repo("octo/skills", ctx)

    def manifest_rows(self) -> list[dict]:
        self.manifest_file.flush()
        text = (self.out / "manifest.jsonl").read_text(encoding="utf-8")
        return [json.loads(line) for line in text.splitlines() if line]

    def collected_folders(self) -> list[str]:
        return sorted(entry.name for entry in self.out.iterdir() if entry.is_dir())

    def assert_nothing_recorded(self) -> None:
        self.assertEqual(self.manifest_rows(), [])
        self.assertEqual(self.collected_folders(), [])
        self.assertEqual(self.ctx.count, 0)
        self.assertEqual(self.ctx.skill_hashes, set())

    def test_collected_skill_is_recorded_with_the_commit_every_request_used(self) -> None:
        self.assertTrue(self.run_repo())

        (row,) = self.manifest_rows()
        self.assertEqual(row["commit"], COMMIT)
        self.assertEqual(row["branch"], "main")
        self.assertEqual(row["files"], 2)
        self.assertEqual((self.out / row["local"] / "SKILL.md").read_bytes(), SKILL_MD)
        self.assertEqual((self.out / row["local"] / "helper.py").read_bytes(), HELPER)
        self.assertEqual(set(self.github.tree_refs), {COMMIT})
        self.assertEqual(set(self.github.raw_refs), {COMMIT})
        self.assertEqual(self.collected_folders(), [row["local"]])

    def test_an_explicit_commit_replaces_the_branch_head(self) -> None:
        pinned = "b" * 40

        self.assertTrue(self.run_repo({"octo/skills": pinned}))

        (row,) = self.manifest_rows()
        self.assertEqual(row["commit"], pinned)
        self.assertEqual(set(self.github.tree_refs), {pinned})
        self.assertEqual(set(self.github.raw_refs), {pinned})

    def test_skill_md_is_downloaded_once_and_saved_from_the_verified_bytes(self) -> None:
        # A second request for the saved copy used to be able to fail after the hashed copy arrived,
        # leaving a recorded folder without SKILL.md. There is one request now, and its bytes are what is saved.
        self.github.failing_after = {"skills/demo/SKILL.md": 1}

        self.assertTrue(self.run_repo())

        (row,) = self.manifest_rows()
        self.assertEqual(self.github.requests["skills/demo/SKILL.md"], 1)
        self.assertEqual((self.out / row["local"] / "SKILL.md").read_bytes(), SKILL_MD)

    def test_a_skill_md_that_never_downloads_is_not_recorded(self) -> None:
        self.github.failing_paths = {"skills/demo/SKILL.md"}

        self.assertFalse(self.run_repo())

        self.assert_nothing_recorded()

    def test_a_missing_sibling_file_leaves_the_skill_out(self) -> None:
        self.github.failing_paths = {"skills/demo/helper.py"}

        self.assertFalse(self.run_repo())

        self.assert_nothing_recorded()

    def test_bytes_that_do_not_match_the_tree_blob_are_rejected(self) -> None:
        self.github.corrupt_paths = {"skills/demo/helper.py"}

        self.assertFalse(self.run_repo())

        self.assert_nothing_recorded()

    def test_bytes_that_change_while_being_saved_are_rejected(self) -> None:
        original = self.collect._write_file

        def write_damaged(path, content):
            original(path, content + b"x" if path.endswith("helper.py") else content)

        with mock.patch.object(self.collect, "_write_file", write_damaged):
            self.assertFalse(self.run_repo())

        self.assert_nothing_recorded()
        self.assertEqual([entry.name for entry in self.out.iterdir() if entry.name.startswith(".partial")], [])

    def test_a_failed_skill_can_be_collected_on_a_later_run(self) -> None:
        self.github.failing_paths = {"skills/demo/helper.py"}
        self.assertFalse(self.run_repo())

        self.github.failing_paths = set()
        self.assertTrue(self.run_repo())

        self.assertEqual(len(self.manifest_rows()), 1)

    def test_a_truncated_tree_is_not_collected(self) -> None:
        self.github.truncated = True

        self.assertFalse(self.run_repo())

        self.assert_nothing_recorded()

    def test_oversize_files_are_listed_instead_of_silently_dropped(self) -> None:
        with mock.patch.object(self.collect, "MAX_FILE", len(SKILL_MD)):
            self.assertTrue(self.run_repo())

        (row,) = self.manifest_rows()
        self.assertEqual(row["skipped_oversize"], ["helper.py"])
        self.assertEqual(row["files"], 1)

    def test_oversize_skill_md_leaves_the_skill_out(self) -> None:
        with mock.patch.object(self.collect, "MAX_FILE", 1):
            self.assertFalse(self.run_repo())

        self.assert_nothing_recorded()

    def test_identical_skill_md_is_collected_once(self) -> None:
        self.github.files["skills/copy/SKILL.md"] = SKILL_MD

        self.assertTrue(self.run_repo())

        self.assertEqual(len(self.manifest_rows()), 1)

    def test_defaults_match_the_benchmark_corpus_path_and_the_git_ignore(self) -> None:
        expected = str(ROOT / "resources" / "skills")
        self.assertEqual(self.collect.OUT_DIR, expected)
        self.assertEqual(_load("make_url_list").OUT_DIR, expected)

    @unittest.skipUnless((ROOT / "benchmarks" / "run_benchmark.py").is_file(), "requires the full repository checkout")
    def test_default_output_is_the_benchmark_default_corpus(self) -> None:
        source = (ROOT / "benchmarks" / "run_benchmark.py").read_text(encoding="utf-8")
        self.assertIn('DEFAULT_RESOURCES = REPO_ROOT / "resources" / "skills"', source)

    @unittest.skipUnless((ROOT / ".git").exists(), "requires a git checkout")
    def test_collector_output_is_ignored_by_git(self) -> None:
        for path in ("resources/skills/manifest.jsonl", "resources/skills/a__b__c/SKILL.md", "resources/skills/.state.json"):
            with self.subTest(path=path):
                completed = subprocess.run(
                    ["git", "-C", str(ROOT), "check-ignore", "-q", path], check=False, capture_output=True
                )
                self.assertEqual(completed.returncode, 0)

    def test_commit_pins_are_validated(self) -> None:
        self.assertEqual(self.collect.parse_pins([f"octo/skills={COMMIT}"]), {"octo/skills": COMMIT})
        for bad in ("octo/skills", "octo/skills=main", "skills=" + COMMIT, f"a/b/c={COMMIT}"):
            with self.subTest(value=bad), self.assertRaises(ValueError):
                self.collect.parse_pins([bad])


@unittest.skipUnless(TOOLS.is_dir(), "tools/ is not part of this distribution")
class MakeUrlListTests(unittest.TestCase):
    def setUp(self) -> None:
        self.make = _load("make_url_list")
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.out = Path(self.tmp.name)

    def write_manifest(self, rows: list[dict]) -> None:
        (self.out / "manifest.jsonl").write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")

    def run_main(self) -> str:
        output = io.StringIO()
        with (
            mock.patch.object(self.make, "OUT_DIR", str(self.out)),
            mock.patch.object(self.make, "MANIFEST", str(self.out / "manifest.jsonl")),
            contextlib.redirect_stdout(output),
        ):
            self.make.main()
        return output.getvalue()

    def test_urls_point_at_the_recorded_commit_not_a_branch(self) -> None:
        self.write_manifest(
            [{"id": 1, "name": "Demo", "repo": "octo/skills", "commit": COMMIT, "path": "skills/my demo/SKILL.md", "local": "x"}]
        )

        self.run_main()

        expected = f"https://github.com/octo/skills/blob/{COMMIT}/skills/my%20demo/SKILL.md"
        self.assertEqual((self.out / "sources.txt").read_text(encoding="utf-8"), expected + "\n")
        table = (self.out / "SOURCES.md").read_text(encoding="utf-8")
        self.assertIn(expected, table)
        self.assertIn(COMMIT[:12], table)
        self.assertNotIn("HEAD", table)

    def test_rows_without_a_commit_are_refused(self) -> None:
        self.write_manifest([{"id": 7, "name": "Old", "repo": "octo/skills", "path": "SKILL.md", "local": "x"}])

        with self.assertRaises(SystemExit) as raised:
            self.run_main()

        self.assertIn("no commit", str(raised.exception))
        self.assertFalse((self.out / "sources.txt").exists())


if __name__ == "__main__":
    unittest.main()
