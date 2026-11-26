# 0007. Keep runtime dependencies minimal and get user approval before adding one

[日本語](0007-minimal-runtime-dependencies-with-user-approval.md)

- Status: Accepted
- Date: 2026-09-23
- Evidence: Supersedes [0001](0001-single-runtime-dependency.en.md); `pyproject.toml`

## Context

ADR 0001 limited runtime dependencies to `python-dotenv` and required agreement in an issue before adding one. Avoiding pollution of dependency resolution in embedding applications remains important, but fixing the count at one can force us to implement something ourselves even when doing so with the standard library would greatly increase maintenance costs or the chance of defects.

## Decision

- Keep runtime dependencies minimal, but do not limit them to `python-dotenv`. First consider whether the standard library and existing dependencies can cover the need.
- Before adding a runtime dependency, explain its necessity, the cost of alternatives using the standard library or existing dependencies, and the impact on installation size, transitive dependencies, licensing, and conflicts with embedding applications; obtain user approval. Do not change `dependencies` in `pyproject.toml` without approval.
- Put anything that need not be mandatory behind an optional extra or provider ABC (`EmbeddingProvider` / `CrossEncoderProvider` / `LLMProvider`) so the core can run without it. Use the `benchmark` extra for benchmarks and the `dev` extra for development tools.

## Consequences

- If a dependency is added, describe its rationale and impact in the PR and add it to `## [Unreleased]` in `CHANGELOG.md`, since the installation contents change for users.
- Retain the separation from ADR 0001: model-related packages are in extras, and the core uses ABCs.

## Alternatives

- Keep ADR 0001 as-is and limit runtime dependencies to `python-dotenv`: rejected because dependencies could not be added even when the maintenance cost of a custom implementation is not justified.
- Allow dependencies to be added without approval: rejected because this would reintroduce dependency conflicts and installation-size problems for embedding applications.
