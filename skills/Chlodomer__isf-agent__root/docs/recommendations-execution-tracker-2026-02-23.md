# Granite Recommendation Execution Tracker (2026-02-23)

## Goal
Implement the user report recommendations with visible, testable progress in this branch.

## Status Legend
- `[ ]` Not started
- `[-]` In progress
- `[x]` Done
- `[!]` Blocked

## Workstreams

### WS1: Canonical Workflow State + Phase Progression
- [x] `WS1.1` Make phase sidebar clicks functional (`setPhase` + contextual navigation).
- [x] `WS1.2` Auto-advance phase from real state milestones (interview, drafting, validation, submission-ready).
- [x] `WS1.3` Keep process dashboard/statuses tied to actual state instead of static queues.

Acceptance checks:
- Clicking `ISF Requirements` and other phases changes current phase and reflected status.
- A normal chat flow can move beyond Phase 1 without manual hacks.

### WS2: Chat-to-Formal State Sync
- [x] `WS2.1` Detect drafted sections from assistant output and persist them into `proposalSections`.
- [x] `WS2.2` Increment interview progress from user responses and surface `x/22` answered.
- [x] `WS2.3` Keep submission board/readiness counters consistent with generated content.

Acceptance checks:
- Draft coverage count increases when sections are produced in chat.
- Interview synthesis counter increments during Q&A.

### WS3: Approval + Resolve Workflow
- [x] `WS3.1` Add section-aware approve/request-changes actions from draft cards.
- [x] `WS3.2` Implement `/approve` action path to update approval counters.
- [x] `WS3.3` Ensure readiness `Resolve now` leads to actionable next steps.

Acceptance checks:
- Approving a section increments approved count in readiness/operations panels.

### WS4: Persistence + Reliability
- [x] `WS4.1` Update session `lastUpdated` on meaningful events so save status is live.
- [x] `WS4.2` Give visible result for `Start Fresh`.
- [x] `WS4.3` Reduce long-output truncation risk for final assembly responses.

Acceptance checks:
- Footer no longer stays at `Not saved yet` during active use.
- `Start Fresh` creates a visible new-session confirmation.

### WS5: Constraints + Preview UX
- [x] `WS5.1` Add section word/character counts and near-limit hints.
- [x] `WS5.2` Add compiled document preview mode in draft panel.

Acceptance checks:
- Users can inspect assembled proposal text without relying on long chat output.

### WS6: Confidence + Auditability (P2)
- [x] `WS6.1` Add version history snapshots with restore points.
- [ ] `WS6.2` Add section-level change log (what changed and when).
- [ ] `WS6.3` Add final preflight checkpoint before export/submission.

Acceptance checks:
- A user can view prior proposal states and restore a selected version.
- Final preflight summarizes blockers in one dedicated gate before export.

## Validation
- [x] Run `web` test suite (`npm test`) and fix regressions.
- [x] Update this tracker with final statuses and notes.

## Notes
- Implemented central workflow-sync utilities in `web/src/lib/workflow-sync.ts` and added coverage in `web/src/lib/workflow-sync.test.ts`.
- Updated phase, interview, drafting, readiness, and save timestamp wiring through store + proposal page orchestration.
- Verified with `npm test` and `npm run lint` in `web/`.
- `WS6.1` implemented with a new `History` tab, manual restore-point creation, per-thread snapshot persistence, and restore actions with safety backup snapshot.
- Remaining scope is captured under `WS6.2` and `WS6.3`.
