from __future__ import annotations

from pathlib import Path
import re
import subprocess
import sys
import unittest

from marmo_core import __version__


ROOT = Path(__file__).resolve().parents[1]
WORKFLOWS = ROOT / ".github" / "workflows"

# The sdist and the Docker image ship the tests without the workflows and the
# contributor files, so the repository checks below only run from a checkout.
FULL_CHECKOUT = WORKFLOWS.is_dir() and (ROOT / ".dockerignore").is_file() and (ROOT / "pyproject.toml").is_file()


def _job_block(workflow: str, job: str) -> str:
    """Return the text of one top-level job of a workflow file (no YAML parser is a dependency)."""

    jobs = workflow.split("\njobs:\n", 1)[1]
    match = re.search(rf"^  {re.escape(job)}:\n(.*?)(?=^  \S[^\n]*:\n|\Z)", jobs, re.DOTALL | re.MULTILINE)
    assert match is not None, f"job {job!r} not found"
    return match.group(1)


class ReleaseReadinessTests(unittest.TestCase):
    def test_release_gate_passes_for_the_v2_candidate(self) -> None:
        completed = subprocess.run(
            [sys.executable, str(ROOT / "scripts" / "release_check.py")],
            cwd=ROOT,
            capture_output=True,
            check=False,
            text=True,
        )

        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertIn(f"release check passed: {__version__}", completed.stdout)


@unittest.skipUnless(FULL_CHECKOUT, "workflow files are not shipped in the sdist or the Docker image")
class ReleaseWorkflowTests(unittest.TestCase):
    def setUp(self) -> None:
        self.release = (WORKFLOWS / "release.yml").read_text(encoding="utf-8")
        self.ci = (WORKFLOWS / "ci.yml").read_text(encoding="utf-8")

    def test_manual_runs_publish_to_testpypi_only(self) -> None:
        testpypi = _job_block(self.release, "publish-testpypi")
        self.assertIn("if: github.event_name == 'workflow_dispatch'", testpypi)
        self.assertNotIn("refs/tags", testpypi)

    def test_pypi_is_published_only_for_a_pushed_version_tag(self) -> None:
        pypi = _job_block(self.release, "publish-pypi")
        self.assertIn("if: github.event_name == 'push' && startsWith(github.ref, 'refs/tags/v')", pypi)
        self.assertNotIn("workflow_dispatch", pypi)
        self.assertIn("url: https://pypi.org/p/marmo-core", pypi)

    def test_pypi_waits_for_the_required_ci_on_the_tagged_commit(self) -> None:
        pypi = _job_block(self.release, "publish-pypi")
        self.assertRegex(pypi, r"needs:\s*\[[^\]]*\bci\b[^\]]*\]")
        self.assertRegex(pypi, r"needs:\s*\[[^\]]*\bbuild\b[^\]]*\]")
        ci_job = _job_block(self.release, "ci")
        self.assertIn("uses: ./.github/workflows/ci.yml", ci_job)
        self.assertIn("startsWith(github.ref, 'refs/tags/v')", ci_job)
        self.assertRegex(self.ci, r"(?m)^on:\n(?:  .*\n)*?  workflow_call:")

    def test_called_ci_does_not_share_a_concurrency_group_with_the_direct_ci_run(self) -> None:
        self.assertIn("group: ci-${{ github.workflow }}-${{ github.ref }}", self.ci)

    def test_release_and_ci_smoke_test_the_built_wheel_outside_the_checkout(self) -> None:
        for name, workflow in (("release.yml", self.release), ("ci.yml", self.ci)):
            with self.subTest(workflow=name):
                self.assertIn("-m venv", workflow)
                self.assertIn("pip install --no-cache-dir dist/*.whl", workflow)
                self.assertIn('cd "$RUNNER_TEMP"', workflow)
                self.assertIn("wheel-smoke/bin/marmo\" --version", workflow)

    def test_ci_runs_the_optional_vector_index_tests_and_refuses_skips(self) -> None:
        job = _job_block(self.ci, "vector-indexes")
        self.assertIn("'.[benchmark-ann]'", job)
        self.assertIn("import numpy, usearch", job)
        self.assertIn("tests.test_vector_index", job)
        self.assertIn('grep -q "skipped"', job)
        self.assertIn("exit 1", job)


@unittest.skipUnless(FULL_CHECKOUT, "build configuration is not shipped in the Docker image")
class DistributionContentTests(unittest.TestCase):
    def test_docker_build_context_excludes_local_environment_files(self) -> None:
        patterns = (ROOT / ".dockerignore").read_text(encoding="utf-8").splitlines()
        self.assertIn("**/.env", patterns)
        self.assertIn("**/.env.*", patterns)
        self.assertNotIn("!.env.example", patterns)

    def test_dockerfile_does_not_copy_environment_files(self) -> None:
        for line in (ROOT / "Dockerfile").read_text(encoding="utf-8").splitlines():
            if line.startswith(("COPY", "ADD")):
                self.assertNotIn(".env", line)

    def test_developer_tools_are_not_part_of_the_sdist(self) -> None:
        manifest = (ROOT / "MANIFEST.in").read_text(encoding="utf-8")
        self.assertNotRegex(manifest, r"(?m)^\s*(?:recursive-)?include\s+tools\b")
        self.assertIn('"tools/**"', (ROOT / "pyproject.toml").read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
