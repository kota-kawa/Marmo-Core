# State Handoff - 2026-02-17

## Snapshot
- Repository: `Chlodomer/isf-agent`
- Workspace: `curitiba`
- Generated at (UTC): `2026-02-17 16:17:11Z`
- Current local branch: `Chlodomer/state-handoff`
- Current HEAD commit: `1e30c4b184990ef6573b86c0e64bca181dd238dc`
- Upstream tracking target: `origin/Chlodomer/pr-current-updates`

## Current Git State
- Working tree is **not clean**.
- Uncommitted files:
  - `web/src/app/proposal/[id]/page.tsx`
  - `web/src/components/onboarding/OnboardingExperience.tsx`
- These two local edits are the latest fixes for:
  - main workspace not starting at scroll top
  - onboarding Enter behavior on all steps

## PR / Branch Status
- Open PR:
  - #8 - "Improve researcher UX, source grounding, and readiness flow"
  - URL: https://github.com/Chlodomer/isf-agent/pull/8
  - Head: `Chlodomer/pr-current-updates`
  - Base: `main`
- Last merged PR:
  - #7 - "Add typing indicator and fix hydration/key issues"

## What Is Included In PR #8 (already pushed)
- Source-grounded workflow:
  - Source registry in state (`ReferenceSource`)
  - Upload integration from chat input
  - Source-aware backend context and citation guidance (`[S1]`, `[S2]`)
- Compliance engine and actions:
  - New validator module (`web/src/lib/compliance.ts`)
  - Chat/context actions for `/validate`, fix flow, and report cards
- Readiness dashboard:
  - New readiness model (`web/src/lib/readiness.ts`)
  - New panel (`SubmissionReadinessPanel`) and readiness tab wiring
- UX/onboarding improvements:
  - Researcher-friendly onboarding rewrite
  - Larger typography and clearer chat UI surfaces
  - Welcome option ordering updates and plain-language guidance
- Assistant behavior policy updates in API prompt:
  - Business tone, no flattery
  - Precision before drafting
  - One-question-at-a-time intake
  - Literature upload + user stance collection

## Local (Uncommitted) Changes After PR #8
These are present on `Chlodomer/state-handoff` and not yet committed/pushed:
1. `web/src/app/proposal/[id]/page.tsx`
   - Adds scroll reset when onboarding transitions to workspace (`onboardingStatus === "done"`).
2. `web/src/components/onboarding/OnboardingExperience.tsx`
   - Adds global Enter handling for all onboarding steps.
   - Prevents double-trigger from input Enter handlers.

## Before This Workspace (Recovered Context)
Source: `.context/attachments/summary-Add response indicator-v1.txt` plus repo/PR history.

Key events before current workspace work:
- Initial UX request: typing indicator while assistant is generating response.
- Implemented loading indicator in chat thread and loading prop wiring from main chat.
- Fixed environment/API key issue by adding proper `ANTHROPIC_API_KEY` in `web/.env.local`.
- Fixed onboarding Enter behavior for name/affiliation inputs (earlier pass).
- Fixed React duplicate key issue (`welcome-1` collision).
- Fixed hydration mismatch around onboarding/localStorage resolution.
- Created and merged PR #7 with those fixes.
- Then moved into broader researcher UX improvements (later consolidated into PR #8).

## Historical Repo Timeline (High Level)
- PR #1 (merged): initial ISF grant writing web UI
- PR #2 (merged): memory files and session learnings
- PR #3 (merged): transparent workflow + operations dashboards
- PR #4 (merged): onboarding UX + ISF docs tooling
- PR #6 (merged): gated onboarding before workspace
- PR #7 (merged): typing indicator + hydration/key fixes
- PR #8 (open): researcher UX, source grounding, compliance/readiness, tone/intake updates

## How To Start A New Branch From Here
Choose one of the following depending on whether you want to keep local uncommitted fixes:

- Keep current uncommitted fixes:
  - `git checkout -b <new-branch-name>`

- Start clean from PR #8 commit only (`1e30c4b`):
  - commit/stash current changes first, then branch

## Notes
- If the next branch should include the scroll + onboarding Enter fixes, commit current local changes first and branch from that commit.
- If the next branch should exclude those two fixes, stash/reset workflow should be decided before branching.
