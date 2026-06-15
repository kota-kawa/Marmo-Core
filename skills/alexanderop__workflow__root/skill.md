---
name: workflow
description: >
  Deterministic multi-agent orchestration powered by the GitHub Copilot CLI. Use when asked to
  "run a workflow", "orchestrate", "fan out agents", "run agents in parallel", "spawn subagents",
  or to decompose a job across many independent agents — audits, code review, sweeps, research,
  migrations. Instead of working turn-by-turn, write a small JavaScript orchestrator on the fly;
  each step runs as a headless `copilot -p` child process. Reach for this when a job needs
  breadth, independent verification, or scale a single context can't hold.
metadata:
  version: 0.1.0
---

# Workflow: deterministic orchestration with Copilot

You hold the control flow (loops, fan-out, branching) in plain JavaScript; each individual step
is delegated to a fresh headless Copilot agent. The orchestration is deterministic — only the
work inside each `agent()` call is model-powered.

## Prerequisites

- GitHub Copilot CLI installed and logged in (`copilot` once interactively, or `copilot login`).
- Node ≥ 18.

## How to run a workflow

When this skill triggers, do **not** do the task turn-by-turn. Instead:

1. **Write an orchestrator script** (e.g. `workflow.mjs` in the project root), importing the
   runtime that ships with this skill:
   ```js
   import { agent, parallel, pipeline, phase, log } from './.claude/skills/workflow/tools/wf-runtime.mjs'
   ```
   Adjust the path to wherever this skill is installed (e.g. `.github/skills/workflow/tools/…`
   or `~/.copilot/skills/workflow/tools/…`). If unsure, locate `wf-runtime.mjs` first.

2. **Follow the shape: fan out → reduce → synthesize.**
   ```js
   phase('Find')
   const found = await parallel(items.map((x) => () => agent(promptFor(x), { schema: ITEM, label: x.id })))
   const clean = found.filter(Boolean).flatMap((r) => r.items)   // reduce in plain JS — no agent
   phase('Synthesize')
   const report = await agent(`Write a report from:\n${JSON.stringify(clean)}`)
   console.log(report)
   ```

3. **Run it and report the result:**
   ```bash
   node workflow.mjs
   ```
   Progress prints to stderr; the final `console.log` is the answer to relay to the user.

## The primitives

- `agent(prompt, { schema?, model?, label?, retries? })` — one headless Copilot agent.
  With `schema` (a JSON Schema) it returns parsed JSON and retries on invalid output;
  without, it returns raw text. Returns `null` on failure — `.filter(Boolean)`.
- `parallel(thunks)` — run concurrently. **Barrier**: awaits all. Failures become `null`.
- `pipeline(items, ...stages)` — stream each item through stages, **no barrier**. Each stage
  gets `(prev, originalItem, index)`.
- `phase(title)` / `log(msg)` — progress lines on stderr.

## Rules (do not skip)

- **Default to `pipeline()`.** Only use a `parallel()` barrier between stages when a stage
  genuinely needs ALL prior results at once (dedupe/rank across everything, early-exit on total
  count, "compare against the other findings").
- **Each agent is stateless** — a separate process with no memory of the others. Put every bit
  of context it needs into its prompt.
- **Never remove the recursion guard.** The runtime launches children with
  `--no-custom-instructions` so they don't re-load this skill and spawn more workflows.
- **Reduce with plain JS**, not agents — flatten, dedupe, filter, sort are just code.
- **Quota costs are real**: every agent is a full Copilot invocation. Scope `--allow-all-tools`
  down for untrusted tasks, and route cheap stages with `{ model: '<smaller-model>' }`.

## Confidence patterns (compose as needed)

- **Adversarial verify**: for each finding, spawn N skeptics prompted to *refute* it; keep it
  only if a majority survive.
- **Perspective-diverse verify**: give each verifier a different lens (correctness, security,
  performance, reproducibility) rather than N identical ones.
- **Loop-until-dry**: for unknown-size discovery, keep spawning finders until K consecutive
  rounds surface nothing new. Dedupe against everything *seen*, not just confirmed results.

## Resume

Set `WF_JOURNAL=.wf/run.json` before running to cache every `agent()` step. Re-running with the
same journal replays cached results instantly and only re-runs new/changed steps.

## Reference

See `references/route-auth-audit.mjs` for a complete fan-out → adversarial-verify → report
workflow. `tools/smoke.mjs` is a 4-agent end-to-end check that the runtime can drive Copilot.
