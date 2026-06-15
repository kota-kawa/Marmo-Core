---
name: create-specialist
version: "2.0.1"
description: "Scaffold a new specialist directory conforming to the v2.x specialist/specialty specs, grounded in cookbook artifacts. Use when adding a specialist to a team."
argument-hint: "<name> [--into <specialists-parent>] [--from <existing-dir>] [--cookbook <root>]"
allowed-tools: Read, Glob, Write, Bash
context: fork
---

# Create Specialist

Scaffold a specialist that conforms to the runtime loader contract, as described
by `pipeline/engine/definitions/specialist-spec.md` and
`specialty-team-spec.md`. A specialist is a **directory**, and its specialties
are **discovered by globbing** `specialities/*.md` — there is no manifest.

Read both specs before scaffolding; they are the source of truth for layout and
frontmatter. Validate the result with the `lint-specialist` skill's linter — do
not hand-check.

## Startup

If `$ARGUMENTS` is `--version`, respond with `create-specialist v2.0.0` and STOP.

## Step 1 — Parse arguments

From `$ARGUMENTS`:

- **name** (required, first positional): the specialist domain in kebab-case
  (`[a-z][a-z0-9]*(-[a-z0-9]+)*`, e.g. `infrastructure`, `ai-ml`). If absent,
  ask for it.
- **--into `<parent>`** (optional): the specialists parent directory. Default
  `teams/devteam/specialists`.
- **--from `<existing-dir>`** (optional): an existing specialist directory to
  use as a structural template.
- **--cookbook `<root>`** (optional): cookbook root for resolving sources.
  Default `external/agenticcookbook/cookbook`.

The target is `<parent>/<name>/`. If it already exists, STOP:
"Specialist `<name>` already exists at `<parent>/<name>/`."

If `--from` was given, read that directory's `specialist.md` and one specialty
file to mirror the structure.

## Step 2 — Gather domain info

Follow the user's clarifying-question rules: tell them **"I have 3 questions."**,
then ask them **one at a time** in prose (no menus, no checkboxes), waiting for
each answer:

1. What does this specialist cover? (1–3 sentences → the `## Role`.)
2. What `review_signals` should route changesets here? (comma-separated
   kebab tokens — file types or domain keywords, e.g. `auth, jwt, oauth`. If it
   should instead run on every review, say so → `always_on: true`.)
3. Which cookbook sources does it own? (file or directory paths relative to the
   cookbook root, e.g. `guidelines/reviewing/security/` — each `.md` becomes one
   specialty.)

## Step 3 — Resolve cookbook sources

For each source path under `<cookbook>`:

- A directory → glob its `*.md` files (skip any `index.md`).
- A file → verify it exists.

Build the list of artifact `.md` files; each becomes one specialty. If a path
doesn't resolve, surface it and ask rather than inventing one.

## Step 4 — Draft the specialties

For each artifact file, read it and derive:

- **name**: the filename stem (kebab-case).
- **logical_model**: `fast-cheap` | `balanced` | `high-reasoning` — pick the
  tier the concern warrants; default `balanced`.
- **description**: ~120-char summary.
- **artifact**: the path relative to the cookbook root.
- **Worker Focus**: the artifact's core review concerns, synthesized.
- **Verify**: concrete PASS/FAIL acceptance criteria drawn from the artifact.
- *(optional)* **Planner Focus**: only if the planner emphasis differs from
  Worker Focus; it falls back to Worker Focus when omitted.

Present the drafts to the user for review **before** writing.

Write each to `<parent>/<name>/specialities/<specialty>.md`:

```markdown
---
name: <specialty>
logical_model: balanced
description: <summary>
artifact: <path-under-cookbook>
version: 1.0.0
---

## Worker Focus
<derived>

## Verify
<derived>
```

> A specialist with **zero** specialty files is silently DROPPED at load time,
> so write at least one.

## Step 5 — Write `specialist.md`

Write `<parent>/<name>/specialist.md`:

```markdown
---
review_signals: <tokens from Q2>      # OR: always_on: true
---

# <Title Case Name> Specialist

## Role
<answer to Q1>

## Persona
(coming)

## Cookbook Sources
- <each source path from Q3>

## Exploratory Prompts
1. <domain question>?
2. <domain question>?
3. <domain question>?
```

- `review_signals` must be a comma-separated string, never a YAML block list —
  the loader's flat parser splits on commas and silently reads `[]`/block lists
  as no signals.
- Omit `name` from the frontmatter (it defaults to the directory name).
- Generate 3–5 exploratory prompts about trade-offs, blind spots, and edge cases
  in the domain; each ends with `?`.
- `## Persona` may stay `(coming)` (a transitional placeholder) — offer to draft
  Archetype/Voice/Priorities if the user wants it.

## Step 6 — Validate

Run the linter over the new directory and fix any FAILs before finishing:

```
python3 ../lint-specialist/scripts/lint_specialist.py <parent>/<name> --cookbook <cookbook> --quiet
```

(Resolve the script via the installed `lint-specialist` skill — it is
`scripts/lint_specialist.py` under that skill's directory.) Expected clean
result: no FAILs. ST06b WARNs mean a cookbook path didn't resolve — recheck the
`artifact` you wrote. An S06 WARN is expected only if you deliberately made the
specialist signal-less and not `always_on` (dispatched by name).

## Step 7 — Summary

Print:

```
Created <parent>/<name>/
  specialist.md         role: <role summary>
  specialities/         <N> specialty file(s): <names>
  Artifacts covered:    <N>
Linter: <N> FAIL  <N> WARN
```

Remind the user to `python3 install` to register the new specialist, and to run
`/lint-specialist <parent>/<name>` again after any edits.

## Usage

```
/create-specialist infrastructure
/create-specialist ai-ml --from teams/devteam/specialists/security
/create-specialist platform-db --into teams/projectteam/specialists
```
