# 0002. Implement research methods on `research/*` branches and pin the commit SHA used for evaluation

[日本語](0002-research-branches-and-frozen-sha.md)

- Status: Accepted
- Date: 2026-09-22
- Evidence: 2aa8ff19 (PR #14), `AGENTS.md`, the workspace-root `AGENTS.md`, `benchmarks/_provenance.py`

## Context

Marmo-Core is both a public library and a research subject. Research must move quickly without compromising the stability of `main`, and the implementation that produced each paper result must remain unambiguous.

## Decision

- Implement new Routers / Retrievers / Selectors on `research/<method-name>` branches and add unit tests.
- Evaluate from `Object-Routing-Research` with the Marmo-Core commit SHA pinned. `_provenance.py` records the SHA in result JSON.
- Make a PR to `main` only for methods whose effectiveness has been confirmed. Do not merge ineffective methods into `main`; keep their comparison results and experimental conditions in Research.
- Do not copy Marmo-Core itself into Research.

## Consequences

- Prefer implementing research methods through the extension points in `ARCHITECTURE.md`, without changing Kernel defaults.
- Treat `benchmarks/results/*.json` as frozen artifacts; do not change numbers without corresponding implementation changes.

## Alternatives

- Keep implementations in Research: rejected because this would duplicate the source of truth and break the correspondence between papers and the public release.
- Experiment directly on `main`: rejected because unvalidated methods could end up in the PyPI release.
