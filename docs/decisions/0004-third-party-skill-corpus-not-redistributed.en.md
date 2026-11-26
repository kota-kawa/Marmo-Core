# 0004. Do not redistribute the third-party Skill corpus

[日本語](0004-third-party-skill-corpus-not-redistributed.md)

- Status: Accepted
- Date: 2026-09-17
- Evidence: 6ef6ad03, 583473e1 (CHANGELOG 0.5.0), comment in `MANIFEST.in`, [`benchmarks/README.en.md`](../../benchmarks/README.en.md)

## Context

The routing benchmark uses about 1,000 SKILL.md files (about 260 MB) from external repositories. Collection is limited to permissively licensed sources (MIT / Apache-2.0 / BSD-3 / MIT-0), but redistribution terms have not been fully reviewed. Including them in the sdist would also distribute hundreds of megabytes with every `pip install`.

## Decision

- Exclude `resources/skills` from both `.gitignore` and `MANIFEST.in`; do not redistribute it. Record sources in `resources/skills/SOURCES.md`, which is not tracked by git along with the corpus.
- If the corpus is unavailable, `run_benchmark.py` explains how to obtain it and stops.
- Make suites that do not depend on the corpus (set selection, scale, adaptation) self-contained using only generation scripts, so they also run from distributions.

## Consequences

- Fully reproducing benchmarks requires recollecting the corpus with `tools/collect_skills.py` (which requires a GitHub token) or specifying a local corpus with `--resources`.
- Commit result JSON as comparison baselines and track corpus versions in `SOURCES.md`.

## Alternatives

- Include it with Git LFS: rejected because the licenses have not been fully reviewed.
- Use only a synthetic corpus: rejected because it cannot measure the vocabulary distribution of real SKILL.md files; keep it only as a supplement.
