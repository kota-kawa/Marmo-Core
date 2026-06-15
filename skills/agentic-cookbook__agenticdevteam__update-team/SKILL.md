---
name: update-team
version: "1.2.0"
description: "Sync the team specialists to the latest cookbook: bump the submodule, detect what guidelines/principles changed or were added, and hand a categorized drift report into a planning session. Use when syncing a team to a new cookbook release."
argument-hint: "[--version]"
allowed-tools: Read, Bash, Write
---

# Update Team

Reconcile the `myteam` review specialists against the latest
`external/agenticcookbook` cookbook. The recurring shape of that work — pull the
cookbook, find what changed, decide which specialists/specialities to update or
add, then plan and apply it — is packaged here so the next cookbook release is a
single command that ends by handing a grounded drift report into planning.

**This skill is read-mostly.** Its only mutation is Step 1 (advance the cookbook
submodule and bump the gitlink). Steps 2–5 are pure analysis driven by a
deterministic Python engine — `${CLAUDE_SKILL_DIR}/scripts/cookbook_drift.py` —
which emits the report only when there is drift. Step 6 — when a report was
written — commits it and transitions into plan mode **with the user**. The skill
never edits a specialist or the manifest; that is the follow-on plan's job
(`separation-of-concerns`: the detector and the mutator are independently
deletable).

The engine is the single source of truth for *how* drift is computed (use-case
collapsing, `artifact:`-only ownership, the six buckets). Do not re-derive its
categorization by hand — run it and interpret its output.

## Startup

If `$ARGUMENTS` is `--version`, respond with `update-team v1.2.0` and STOP.

## Step 1 — Sync the cookbook (the only mutation)

Advance the submodule to the latest cookbook on its default branch and bump the
gitlink. This is the skill's only write, and it is idempotent: if `/cwt` (or a
prior run) already advanced the submodule, the pull is a no-op and only the
gitlink commit remains; if the gitlink is already current, the whole step is a
no-op. Work from the repo root, deciding rather than blindly running:

1. **Record the baseline** (informational): `git ls-tree HEAD external/agenticcookbook`.

2. **Check where the submodule sits before touching it.** Read its current branch
   with `git -C external/agenticcookbook rev-parse --abbrev-ref HEAD` and its
   default branch (usually `main` — confirm with
   `git -C external/agenticcookbook remote show origin` if unsure).
   - On the default branch, or in detached `HEAD` (the normal at-gitlink state),
     proceed to advance it.
   - On a **different named branch**, someone put it there deliberately. **STOP
     and ask** before moving it — do not run `checkout` to switch it for them.

3. **Advance the working tree** to the latest default-branch commit:
   `git -C external/agenticcookbook fetch origin`, check out the default branch
   if not already on it, then `git -C external/agenticcookbook pull --ff-only
   origin <default>`. If the pull is not fast-forwardable (the submodule
   diverged), **STOP and surface that** — do not force it.

4. **Bump the gitlink if it moved** (stage only the submodule, never `-A`):
   `git add external/agenticcookbook`; if that staged anything
   (`git diff --cached --quiet external/agenticcookbook` returns non-zero),
   `git commit -m "chore: bump cookbook submodule to latest"` and `git push`.

## Step 2–5 — Analyze the drift

Run the engine from the repo root:

```
python3 ${CLAUDE_SKILL_DIR}/scripts/cookbook_drift.py
```

It reads each grounded team's `cookbook-sync.json` marker (the SHA the team
data was last reconciled against; absent, empty, or malformed on first run →
bootstrapped from the `origin/main` gitlink, noted as a warning), diffs it
against the submodule HEAD, and writes `docs/planning/cookbook-drift-<new_sha8>.md`
**only when drift is detected**. Specialties are discovered from the shared area
pool `specialities/<area>/<name>.md` (grounded via each specialty's `artifact:`
pointer and owned via each `specialist.md`'s `specialities:` references), with a
fallback to the legacy nested layout. It prints either that report path or
`no drift detected — no report written`, plus a one-line-per-team summary,
then exits 0 (or non-zero if a team errored — surface the warning verbatim
and stop).

The report's buckets map onto the original request:

- **Step 2 — `updated_guidelines`**: referenced guidelines/principles that
  changed. Entries flagged *materialized but unowned* are manifest `src`s no
  specialty grounds to — prunable.
- **Step 3 — `specialists_to_update`**: those changes rolled up to the owning
  specialists (whose `artifact:` pointers grounded them).
- **Step 4 — `new_specialities_existing`**: brand-new cookbook files in a domain
  a specialist already covers — candidate specialities to add. `owners` lists the
  candidate owner(s) by domain; a human picks in the plan.
- **Step 5 — `new_specialist_areas`**: brand-new files in a domain *no*
  specialist covers — candidate new specialists.
- **`stale_references`**: referenced files that were deleted or renamed (broken
  `artifact:` / manifest `src`), with a suggested replacement on renames. Fix
  these first — they are live breakage.

If the engine reports every team `up-to-date`, say so and STOP — there is
nothing to plan.

## Step 6 — Report, then plan with the user

If the engine reported **no drift** (it printed `no drift detected` and wrote no
report), there is nothing to plan — say so and STOP. Otherwise, a report was
written:

1. Commit the generated report so the planning session has a durable input:

   ```
   git add docs/planning/cookbook-drift-<new_sha8>.md
   git commit -m "docs(planning): cookbook drift report for <new_sha8>"
   git push
   ```

2. Present the compact summary (counts per bucket + the stale-reference list, if
   any) in chat.

3. **Enter plan mode with the user** to design the team-update plan from the
   report. State explicitly in the handoff that the resulting plan's **final
   step must**:
   - write each affected team's `cookbook-sync.json` `synced_sha = <new_sha>`
     (creating the marker on first run), gated on the specialist/manifest edits
     landing, and
   - re-run the linter (`/lint-specialist --all teams/<team>/specialists`) and the
     devteam reference-integrity tests, which must stay green.

   Advancing the marker is what makes a re-run idempotent: until it lands, re-running
   this skill reports the same drift.
