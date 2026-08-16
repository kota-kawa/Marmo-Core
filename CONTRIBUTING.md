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

## Reproducing CI locally

CI runs the test suite on every supported Python version, plus the static and
release checks below. Run these before opening a pull request:

```bash
ruff check marmo_core tests scripts tools
mypy marmo_core
python scripts/release_check.py
check-manifest
python -m build
python -m twine check dist/*
check-wheel-contents dist/*.whl
```

If `check-manifest` reports a mismatch after you add a file, either add the
matching rule to `MANIFEST.in` (to ship it in the sdist) or list the file under
`[tool.check-manifest] ignore` in `pyproject.toml` (to keep it repository-only).

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
