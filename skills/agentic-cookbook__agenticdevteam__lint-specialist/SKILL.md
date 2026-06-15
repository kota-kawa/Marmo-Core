---
name: lint-specialist
version: "2.1.1"
description: "Validate specialist directories against the v2.x specialist/specialty specs by running the deterministic linter. Use when creating, editing, or reviewing a specialist."
argument-hint: "[<specialist-dir>...] [--all <parent>] [--cookbook <root>]"
allowed-tools: Read, Bash
context: fork
---

# Lint Specialist

Validate one or more specialist **directories** against the runtime loader
contract. The check logic lives in a deterministic Python script —
`${CLAUDE_SKILL_DIR}/scripts/lint_specialist.py` — which mirrors
`pipeline/engine/source/engine/conductor/team_loader.py` exactly. This skill is
a thin shell: it resolves targets, runs the script, and helps interpret FAILs.
Do not re-implement the checks by hand; the script is the single source of
truth for *how* to lint, and the specs below are the source of truth for *what*
the checks mean:

- `pipeline/engine/definitions/specialist-spec.md` — S01–S06, C01–C04
- `pipeline/engine/definitions/specialty-team-spec.md` — ST01–ST07, ST06b

## Startup

If `$ARGUMENTS` is `--version`, respond with `lint-specialist v2.1.0` and STOP.

## Step 1 — Resolve targets

A target is a specialist directory (the one containing `specialist.md`), not a
file. From `$ARGUMENTS`:

- One or more directory paths → lint exactly those.
- `--all <parent>` → lint every immediate subdirectory of `<parent>`.
- `--cookbook <root>` → check `artifact:` paths resolve under that cookbook
  (ST06b). Omit it and the script defaults to `external/agenticcookbook/cookbook`
  when that exists, else skips ST06b.
- Empty `$ARGUMENTS` → default to `--all teams/devteam/specialists`.
  Mention that you're defaulting there.

## Step 2 — Run the linter

Run it via Bash from the repo root, forwarding the resolved arguments:

```
python3 ${CLAUDE_SKILL_DIR}/scripts/lint_specialist.py <targets-or---all> [--cookbook <root>] --quiet
```

Use `--quiet` to suppress PASS lines (show only WARN/FAIL) unless the user asked
for the full report. The script exits 0 when there are no FAILs, 1 when any
FAIL, 2 on bad invocation. Echo its output.

## Step 3 — Report and explain

Relay the script's findings. For each **FAIL**, give the one-line fix, grounding
it in the spec — the common ones:

- **S01** — `specialist.md` is missing or has no `---` frontmatter. Add the
  frontmatter block (at minimum `review_signals` or `always_on`).
- **S02** — zero `specialities/*.md` (the loader silently DROPS such a
  specialist). Add at least one specialty file.
- **S03** — `review_signals` is `[]`/empty/non-kebab. The flat parser splits on
  commas and cannot read a YAML block list: use `review_signals: a, b, c` or omit
  the key entirely.
- **ST04 / ST05** — a specialty is missing `## Worker Focus` / `## Verify`; the
  reviewer/verifier would have no lens/criteria. Add the section.

For **WARN**s, summarize rather than belabor:

- **S06** (no signals and not `always_on`) is fine *only* if the specialist is
  dispatched explicitly by name (e.g. the review report writer); otherwise it
  will never be selected — flag it.
- **ST06b** (artifact not found under the cookbook) means provenance drift — the
  cookbook moved/renamed the guideline. Note it for the next cookbook-sync pass.

Do **not** silently edit authored specialist files to clear FAILs/WARNs. If the
user asks you to fix, read the file, propose the change grounded in the spec, and
apply it only after they confirm — then bump the specialty `version` if you
touched a specialty file.

## Usage

```
/lint-specialist teams/devteam/specialists/accessibility
/lint-specialist --all teams/devteam/specialists
/lint-specialist --all teams/devteam/specialists --cookbook external/agenticcookbook/cookbook
```
