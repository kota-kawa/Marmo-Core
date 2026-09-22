# Contributing to Marmo-Core

## Setup

Marmo-Core supports Python 3.10 through 3.14 and keeps its runtime dependency
surface minimal — `python-dotenv` is the only required dependency. Please do
not add a runtime dependency without discussing it in an issue first; the dev
and benchmark extras are the place for anything that is not needed at runtime.

```bash
python -m pip install -e '.[dev]'
```

## Tests

```bash
python -W error::ResourceWarning -m unittest discover -s tests
```

`-W error::ResourceWarning` is not optional: CI runs it this way, so an
unclosed file or socket in a test fails the build even when the assertions
pass.

## Branches and pull requests

`main` is the released, stable branch and is never pushed to directly. Work on
a branch named `<type>/<topic>` (`fix/`, `feat/`, `docs/`, `chore/`, `ci/`; new
routing methods under evaluation live on `research/<method-name>`, see
[AGENTS.md](AGENTS.md)) and open a pull request.

- Commit subjects follow the existing history: `<type>: <English summary>`.
  When a fix changes behaviour, say in the body what was wrong, what was
  measured, and what the trade-off is.
- Keep unrelated kinds of change (a bug fix and a refactor, a feature and a
  reformat) in separate commits.
- Pull request titles and descriptions include both Japanese and English, and
  follow [.github/PULL_REQUEST_TEMPLATE.md](.github/PULL_REQUEST_TEMPLATE.md):
  what changed, related issues, the test commands you ran and their result,
  and anything a reviewer has to decide (a changed default, exit code, score,
  or public name).
- A user-visible change gets a line under `## [Unreleased]` in
  `CHANGELOG.md` in the same pull request. Version bumps are a separate
  maintainer commit (see Releasing).

The merge conditions and the required CI jobs are recorded in
[.github/BRANCH_PROTECTION.md](.github/BRANCH_PROTECTION.md).

## Reproducing CI locally

CI runs the test suite on every supported Python version, plus the static and
release checks below. Run these before opening a pull request:

```bash
ruff check marmo_core tests scripts tools
mypy marmo_core
python scripts/release_check.py
python scripts/check_doc_paths.py
python scripts/check_env_documentation.py
check-manifest
python -m build
python -m twine check dist/*
check-wheel-contents dist/*.whl
```

If `check-manifest` reports a mismatch after you add a file, either add the
matching rule to `MANIFEST.in` (to ship it in the sdist) or list the file under
`[tool.check-manifest] ignore` in `pyproject.toml` (to keep it repository-only).

`check_doc_paths.py` fails when a Markdown document names a repository path
that no longer exists; fix the reference, or, for a path that is documented
although it is intentionally untracked, add it to the script's allowlist with
the reason. `check_env_documentation.py` fails when `.env.example` and the
environment variables read by `marmo_core/` or `benchmarks/` disagree, so a new
variable and its `.env.example` line land in the same change.

A Docker job also builds the image and runs the suite inside it:

```bash
docker build --tag marmo-core:ci .
docker run --rm marmo-core:ci python -m unittest discover -s tests
```

## Resource samples

The bundled samples under `resources/memory`, `resources/tools`, and
`resources/agents` are executable and covered by tests. A new sample must
resolve a working implementation through its `python:` ref, declare the
permissions and side effects it actually needs, and stay within the current
working directory for filesystem access. Validate a change with:

```bash
marmo validate resources/memory resources/tools resources/agents
```

## Documentation

- [ARCHITECTURE.md](ARCHITECTURE.md) is the internal design reference: layers,
  the request path through `Kernel.run_goal`, contracts, and extension points.
- [docs/knowledge/](docs/knowledge/README.md) holds the development
  conventions, debugging procedures, compatibility contracts, and the lessons
  recorded from this repository's history. Read
  `docs/knowledge/development_conventions.md` before changing code.
- [docs/decisions/](docs/decisions/README.md) records the architecture
  decisions; add or update an ADR when you change one of them.
- [AGENTS.md](AGENTS.md) lists every document with when to read it, and is the
  rule set for coding agents working in this repository. When you add or remove
  a document, update that list in the same commit; CI checks that documented
  paths exist.

## Security-relevant changes

Changes to permissions, side-effect classification, policy evaluation, secret
handling, or the human-in-the-loop gates should be reviewed against
[docs/threat-model.md](docs/threat-model.md), and should update that document
when they move a trust boundary. See [SECURITY.md](SECURITY.md) for reporting a
vulnerability rather than opening a pull request for it.

## Releasing

Releases are published to PyPI by `.github/workflows/release.yml` through
Trusted Publishing. The workflow refuses to publish when the tag and the
packaged version disagree.

1. Update the version in **both** `marmo_core/_version.py` and
   `pyproject.toml` — `scripts/release_check.py` fails if they diverge.
2. Add a `## [x.y.z] - YYYY-MM-DD` section to `CHANGELOG.md` and update the
   comparison links at the bottom of the file. `release_check.py` fails if the
   new version has no dated section.
3. Run the checks above, then commit and merge to `main`.
4. Optionally run the `Release` workflow manually (`workflow_dispatch`) to
   publish to TestPyPI first and verify the rendered project page.
5. Tag and push:

   ```bash
   git tag v0.4.0
   git push origin v0.4.0
   ```

The `pypi` environment requires an approval before the upload step runs.
