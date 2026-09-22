"""Tests for the repository hygiene checks under scripts/."""

from __future__ import annotations

from pathlib import Path
import importlib.util
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"


def _load(name: str):
    spec = importlib.util.spec_from_file_location(name, SCRIPTS / f"{name}.py")
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


check_doc_paths = _load("check_doc_paths")
check_env_documentation = _load("check_env_documentation")

# The Docker image and the sdist ship the package, tests, and scripts without
# the contributor documentation, so the checks against the real tree only run
# from a full checkout.
FULL_CHECKOUT = (ROOT / ".github").is_dir() and (ROOT / ".env.example").is_file() and (ROOT / "AGENTS.md").is_file()


class DocPathCheckTests(unittest.TestCase):
    def test_extracts_links_and_code_spans_but_skips_urls_anchors_and_placeholders(self) -> None:
        markdown = (
            "See [the guide](docs/guide.md#setup) and `marmo_core/kernel.py`.\n"
            "Not paths: [site](https://example.com), [top](#top), `benchmarks/results/*.json`,\n"
            "`resources/<name>/SKILL.md`, `python -m build`, `marmo_core\\gone.py`, `dist/`.\n"
        )
        self.assertEqual(
            list(check_doc_paths.iter_mentions(markdown)),
            ["docs/guide.md", "marmo_core/kernel.py", "dist"],
        )

    def test_links_resolve_relative_to_the_document_and_code_spans_do_not(self) -> None:
        markdown = "[sibling](guide.md) [up](../examples/demo.py) [escape](../../outside.md) `README.md`\n"

        self.assertEqual(
            list(check_doc_paths.iter_mentions(markdown, "docs")),
            ["docs/guide.md", "examples/demo.py", "README.md"],
        )

    def test_allowlist_matches_exact_path_children_and_globs_only(self) -> None:
        allowed = check_doc_paths._documented_untracked
        self.assertTrue(allowed(".env"))
        self.assertTrue(allowed("resources/skills/SOURCES.md"))
        self.assertTrue(allowed("benchmarks/corpus/scale_corpus_10000.json"))
        self.assertFalse(allowed(".env.example"))
        self.assertFalse(allowed("distribution/x.md"))
        self.assertFalse(allowed("benchmarks/cache_utils.py"))
        self.assertFalse(allowed("benchmarks/corpus/set_corpus.json"))

    def test_reports_only_repository_paths_that_do_not_exist(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "docs").mkdir()
            (root / "docs" / "present.md").write_text("ok", encoding="utf-8")
            document = root / "README.md"
            document.write_text(
                "[a](docs/present.md) [b](docs/missing.md) `marmo-package.json` `.env` `docs/nested/gone.py`\n",
                encoding="utf-8",
            )
            tracked = {"README.md", "docs/present.md"}

            stale = check_doc_paths.find_stale_references(root, [document], tracked)

        self.assertEqual(stale, [(document, "docs/missing.md"), (document, "docs/nested/gone.py")])

    def test_bare_module_names_must_match_a_tracked_python_file(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            document = root / "AGENTS.md"
            document.write_text("`kernel.py` `gone.py` `SKILL.md`\n", encoding="utf-8")

            stale = check_doc_paths.find_stale_references(root, [document], {"marmo_core/kernel.py"})

        self.assertEqual(stale, [(document, "gone.py")])

    def test_references_into_a_removed_known_directory_are_stale(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            document = root / "README.md"
            document.write_text("`examples/hello.py` `unknown/thing.md`\n", encoding="utf-8")

            stale = check_doc_paths.find_stale_references(root, [document], {"README.md"})

        self.assertEqual(stale, [(document, "examples/hello.py")])

    def test_falls_back_to_the_filesystem_without_git(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "marmo_core").mkdir()
            (root / "marmo_core" / "kernel.py").write_text("", encoding="utf-8")
            document = root / "README.md"
            document.write_text("`marmo_core/kernel.py` `kernel.py` `marmo_core/nope.py` `nope.py`\n", encoding="utf-8")

            stale = check_doc_paths.find_stale_references(root, [document], None)

        self.assertEqual(stale, [(document, "marmo_core/nope.py"), (document, "nope.py")])

    def test_directory_is_considered_present_when_a_tracked_file_lives_under_it(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            document = root / "README.md"
            document.write_text("`tests/fixtures`\n", encoding="utf-8")

            stale = check_doc_paths.find_stale_references(root, [document], {"tests/fixtures/compat/state.jsonl"})

        self.assertEqual(stale, [])

    @unittest.skipUnless(FULL_CHECKOUT, "requires the full repository checkout")
    def test_repository_documentation_has_no_stale_paths(self) -> None:
        completed = subprocess.run(
            [sys.executable, str(SCRIPTS / "check_doc_paths.py")],
            cwd=ROOT,
            capture_output=True,
            check=False,
            text=True,
        )

        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertIn("doc path check passed", completed.stdout)


class EnvDocumentationCheckTests(unittest.TestCase):
    def test_recognises_every_lookup_form_and_generalizes_dynamic_names(self) -> None:
        source = (
            'a = required_environment("OPENAI_MODEL")\n'
            "b = optional_environment('OPENAI_BASE_URL')\n"
            'c = required_positive_int_environment("ANTHROPIC_MAX_TOKENS")\n'
            'd = os.environ.get("OPENAI_API_KEY", "")\n'
            'e = os.environ["ANTHROPIC_API_KEY"]\n'
            'f = os.getenv("OPENAI_EMBEDDING_MODEL")\n'
            'g = f"MARMO_NOTIFICATION_{destination.upper()}_URL"\n'
            'ignored = os.environ.items()\n'
            'not_a_variable = f"HTTP_{status}: {detail}"\n'
        )

        self.assertEqual(
            check_env_documentation.variables_read(source),
            {
                "OPENAI_MODEL",
                "OPENAI_BASE_URL",
                "ANTHROPIC_MAX_TOKENS",
                "OPENAI_API_KEY",
                "ANTHROPIC_API_KEY",
                "OPENAI_EMBEDDING_MODEL",
                "MARMO_NOTIFICATION_<...>_URL",
            },
        )

    def test_reads_documented_keys_including_commented_placeholders(self) -> None:
        env_example = (
            "# comment without a key\n"
            "OPENAI_API_KEY=\n"
            "OPENAI_MODEL=gpt-5.6-terra\n"
            "# OPENAI_REASONING_EFFORT=\n"
            "# MARMO_NOTIFICATION_<DESTINATION>_URL=\n"
            "not_a_key=value\n"
        )

        self.assertEqual(
            check_env_documentation.variables_documented(env_example),
            {"OPENAI_API_KEY", "OPENAI_MODEL", "OPENAI_REASONING_EFFORT", "MARMO_NOTIFICATION_<...>_URL"},
        )

    def test_compare_reports_both_directions(self) -> None:
        undocumented, unused = check_env_documentation.compare({"A", "B"}, {"B", "C"})

        self.assertEqual((undocumented, unused), (["A"], ["C"]))

    @unittest.skipUnless(FULL_CHECKOUT, "requires the full repository checkout")
    def test_env_example_matches_the_code(self) -> None:
        completed = subprocess.run(
            [sys.executable, str(SCRIPTS / "check_env_documentation.py")],
            cwd=ROOT,
            capture_output=True,
            check=False,
            text=True,
        )

        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertIn("env documentation check passed", completed.stdout)


if __name__ == "__main__":
    unittest.main()
