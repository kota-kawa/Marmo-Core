# workflow

A skill for the **GitHub Copilot CLI** (and any agent that reads the open `SKILL.md` format)
that adds **deterministic multi-agent orchestration**. Instead of working a big job turn-by-turn,
the agent writes a small JavaScript orchestrator on the fly; each step runs as a headless
`copilot -p` child process. You own the control flow, Copilot does the thinking inside each step.

It recreates the idea behind Claude Code's *Workflows* — fan out → reduce → synthesize — but the
agents are Copilot CLI processes instead of an in-process tool.

## What it does

```
You: "run a workflow to audit every route for missing auth"
        │
        ▼
Copilot  ── reads skill.md, writes workflow.mjs, runs `node workflow.mjs`
        │
        ▼
wf-runtime.mjs   agent() ─┬─► copilot -p "review route A"   (child process)
  parallel / pipeline     ├─► copilot -p "review route B"
  + concurrency pool      └─► copilot -p "review route N"
        │  collects JSON → reduces in plain JS → synthesizes
        ▼
returns the final result
```

## Example prompts

```
"Run a workflow to audit every API route under src/routes for missing auth checks"
"Orchestrate a review of this diff — one agent per file, then verify each finding"
"Fan out agents to research X across 8 sources and synthesize a report"
"Spawn subagents to migrate every test file to the new helper"
```

## Prerequisites

- [GitHub Copilot CLI](https://docs.github.com/copilot/how-tos/copilot-cli), logged in
  (`copilot` once interactively, or `copilot login`).
- Node ≥ 18.

Every agent is a full Copilot invocation and consumes quota.

## Installation

### With `npx skills` (recommended)

```bash
npx skills add alexanderop/workflow
```

### Manual

Clone into your project's `.claude/skills/` directory (the Copilot CLI also reads
`.claude/skills/`, `.github/skills/`, and `.agents/skills/`):

```bash
git clone https://github.com/alexanderop/workflow .claude/skills/workflow
```

Or symlink from a shared location:

```bash
git clone https://github.com/alexanderop/workflow ~/skills/workflow
ln -s ~/skills/workflow .claude/skills/workflow
```

For a personal skill shared across every project, clone into `~/.copilot/skills/workflow`
instead.

After installing, in a Copilot session run `/skills reload` and check with
`/skills info workflow`.

## Usage

Just say the word in a Copilot session:

```
run a workflow to audit every API route under src/routes for missing auth checks,
verify each finding with a second pass, then report
```

Copilot writes a `workflow.mjs`, runs it, and reports back. Or run the bundled example directly:

```bash
node references/route-auth-audit.mjs ./src/routes
```

Smoke-test the runtime (≈4 small Copilot invocations):

```bash
node tools/smoke.mjs
```

## The primitives

From `tools/wf-runtime.mjs`:

| Primitive | What it does |
|---|---|
| `agent(prompt, { schema?, model?, label?, retries? })` | One headless Copilot agent. With `schema` → parsed, validated JSON (retries on bad output). Without → raw text. `null` on failure. |
| `parallel(thunks)` | Run concurrently. **Barrier** — awaits all. Failures become `null`; `.filter(Boolean)`. |
| `pipeline(items, ...stages)` | Stream each item through stages with **no barrier**. Stages get `(prev, item, index)`. |
| `phase(title)` / `log(msg)` | Progress lines on stderr. |

**Default to `pipeline()`.** Use a `parallel()` barrier between stages only when a stage needs
*all* prior results at once (dedupe/rank, early-exit, cross-comparison).

### Minimal example

```js
import { agent, parallel, phase } from './.claude/skills/workflow/tools/wf-runtime.mjs'

const ITEM = {
  type: 'object', additionalProperties: false,
  properties: { title: { type: 'string' }, url: { type: 'string' } },
  required: ['title', 'url'],
}

phase('Find')
const found = await parallel(
  sources.map((s) => () => agent(`Find releases for ${s}. Return title+url.`, { schema: ITEM, label: s }))
)
const items = found.filter(Boolean)                 // reduce in plain JS

phase('Write')
const digest = await agent(`Write a digest from:\n${JSON.stringify(items)}`)
console.log(digest)
```

## Config (env vars)

| Var | Default | Purpose |
|---|---|---|
| `WF_CONCURRENCY` | `cores - 2` | Max simultaneous agents |
| `WF_JOURNAL` | _off_ | Path to a journal file → cache steps, resume crashed/edited runs |
| `WF_COPILOT_BIN` | `copilot` | Path to the Copilot CLI binary |
| `WF_TIMEOUT_MS` | `600000` | Per-agent timeout |

Resume a run:

```bash
WF_JOURNAL=.wf/audit.json node workflow.mjs   # first run caches every agent() step
WF_JOURNAL=.wf/audit.json node workflow.mjs   # re-run: cached steps replay instantly
```

## How it differs from Claude Code Workflows

| | Claude Workflows | This skill (Copilot) |
|---|---|---|
| Agent | in-process subagent (`Workflow` tool) | headless `copilot -p` child process |
| Structured output | tool-enforced schema | prompt + parse + retry (best-effort) |
| Parallelism | runtime-managed | OS processes + a concurrency pool |
| Resume / journal | built in | opt-in via `WF_JOURNAL` |
| Trigger | `Workflow` tool / "workflow" keyword | the `workflow` agent skill |

## Safety notes

- **Recursion guard:** child agents run with `--no-custom-instructions` so they never re-load
  this skill and spawn more workflows. Don't remove it.
- **Permissions:** the runtime uses `--allow-all-tools` for autonomy. Scope it down
  (`--allow-tool` / `--deny-tool`) for untrusted tasks.
- **Quota:** every agent is a full Copilot invocation. A fan-out of 40 files = 40+ invocations.

## Layout

```
workflow/
├── skill.md                       # the skill — triggers + instructions (loaded at trigger time)
├── tools/
│   ├── wf-runtime.mjs             # the orchestration runtime
│   └── smoke.mjs                  # 4-agent end-to-end smoke test
├── references/
│   └── route-auth-audit.mjs       # example: fan-out → adversarial verify → report
├── README.md
└── LICENSE
```

## License

MIT
