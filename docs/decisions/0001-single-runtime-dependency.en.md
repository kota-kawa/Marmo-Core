# 0001. Keep runtime dependencies limited to `python-dotenv` only

[日本語](0001-single-runtime-dependency.md)

- Status: Superseded by [0007](0007-minimal-runtime-dependencies-with-user-approval.en.md)
- Date: 2026-08-07
- Evidence: 49076f8b (Document minimal dependency policy), [Setup in the contributing guide](../../CONTRIBUTING.md#setup), `pyproject.toml`

## Context

Marmo-Core is a kernel embedded in agent runtimes, and not polluting users' dependency resolution is a prerequisite for adoption. At the same time, embedding models and cross-encoders are needed for benchmarks.

## Decision

- The only runtime dependency is `python-dotenv`. Use `urllib` for HTTP, JSONL / `sqlite3` for persistence, and a custom parser for front matter.
- Put model-related packages in the `benchmark` extra (fastembed); the core only has the `EmbeddingProvider` / `CrossEncoderProvider` / `LLMProvider` ABCs.
- Put development tools in the `dev` extra. Dependabot targets GitHub Actions only (PR #8).

## Consequences

- Agree on new runtime dependencies in an issue first. State the rationale and impact in the PR.
- Write numerical computations in pure Python. Cosine similarity is acceptable at a scale of 1,000 items, but 10k or more items require hierarchical routing (`hierarchy.py`) ([`benchmarks/README.en.md`](../../benchmarks/README.en.md)).

## Alternatives

- Adopt `httpx` / `pydantic` / `numpy`: rejected because the convenience gains do not outweigh dependency conflicts with embedding applications and installation size.
