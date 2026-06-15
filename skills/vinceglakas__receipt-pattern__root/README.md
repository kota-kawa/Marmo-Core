# The Receipt Pattern

**Agents can't be trusted because they don't leave receipts.**

You let an AI agent loose on your codebase. It ran for 4 minutes. It says "Done!" You ask what it did. It gives you a vague summary. You check git diff — 47 files changed. Some of them you didn't ask for. One of them is your production config.

Sound familiar?

## The Problem

AI agents are black boxes. They do things — write files, call APIs, modify databases, send emails — and you have no structured record of what happened. Logs exist, but they're streams of consciousness, not actionable records.

When something breaks at 2am, you need to know: what did the agent do, in what order, and can I undo it?

## The Solution

**After every significant action, the agent writes a receipt.** A structured JSON file that records exactly what happened, when, and whether it can be rolled back.

That's it. That's the pattern.

```json
{
  "id": "rcpt_1709641200_a3f8b2",
  "agentId": "claude-code",
  "sessionId": "sess_20260305_143200",
  "timestamp": "2026-03-05T14:35:22.847Z",
  "trigger": "manual",
  "status": "completed",
  "durationMs": 12847,
  "actions": [
    {
      "sequence": 1,
      "type": "file:write",
      "target": "src/auth/middleware.ts",
      "summary": "Added rate limiting middleware — 100 req/min per IP",
      "status": "success",
      "isRollbackEligible": true,
      "durationMs": 340,
      "timestamp": "2026-03-05T14:35:10.102Z"
    },
    {
      "sequence": 2,
      "type": "file:write",
      "target": "src/auth/middleware.test.ts",
      "summary": "Added 6 tests for rate limiting edge cases",
      "status": "success",
      "isRollbackEligible": true,
      "durationMs": 520,
      "timestamp": "2026-03-05T14:35:15.430Z"
    },
    {
      "sequence": 3,
      "type": "shell:exec",
      "target": "npm test -- --grep 'rate limit'",
      "summary": "Ran rate limiting tests — 6/6 passed",
      "status": "success",
      "isRollbackEligible": false,
      "durationMs": 4200,
      "timestamp": "2026-03-05T14:35:18.700Z"
    }
  ],
  "anomalies": [],
  "rollbackAvailable": true,
  "sdkVersion": "receipt-pattern/1.0.0"
}
```

You open the receipts folder. You see exactly what happened. You can audit it. You can roll it back. You can sleep at night.

## Quick Start

### 1. Install the skill

**Claude Code / Codex** — Drop `SKILL.md` into your project root or `.claude/skills/`:
```bash
curl -o .claude/skills/receipt-pattern.md https://raw.githubusercontent.com/vinceglakas/receipt-pattern/main/SKILL.md
```

**OpenClaw** — Install as a skill:
```bash
openclaw skill install https://github.com/vinceglakas/receipt-pattern
```

**Any agent** — Just add this to your system prompt:
> After every significant action (file write, API call, database change, deployment), write a receipt to `receipts/` following the schema in SKILL.md.

### 2. Let your agent work

The agent will now write a receipt after every session. Receipts land in:
```
receipts/
  2026-03-05-14-35-22-file-write.json
  2026-03-05-15-12-08-api-call.json
  2026-03-05-16-44-31-deploy.json
```

### 3. Review

```bash
# What did the agent do today?
ls receipts/2026-03-05*

# Any failures?
grep -l '"status": "failed"' receipts/*.json

# Any anomalies?
grep -l '"anomalies": \[{' receipts/*.json
```

## What Counts as a Receipt-Worthy Action

| Do write a receipt | Don't write a receipt |
|---|---|
| Writing/deleting files | Reading files |
| API calls that mutate state | GET requests |
| Database writes/deletes | Database reads |
| Sending emails/messages | Checking status |
| Deployments | Running linters |
| Shell commands with side effects | `ls`, `cat`, `grep` |

**The rule:** If it changes state or leaves the system, it gets a receipt.

## The Schema

See [`receipt-schema.json`](./receipt-schema.json) for the full JSON Schema, or the [example receipt](./examples/receipt.example.json).

Key fields:
- **`id`** — `rcpt_[unix_timestamp]_[random_hex]`
- **`actions[]`** — Ordered list of everything the agent did
- **`anomalies[]`** — Anything unexpected (file already existed, API returned unexpected status, etc.)
- **`rollbackAvailable`** — Can this session's actions be undone?
- **`status`** — `completed | failed | partial | rolled_back`

## Examples

- [`examples/receipt.example.json`](./examples/receipt.example.json) — A realistic receipt
- [`examples/typescript-example.ts`](./examples/typescript-example.ts) — Minimal TypeScript implementation
- [`examples/python-example.py`](./examples/python-example.py) — Minimal Python implementation

## Audit Trail

The `src/audit.ts` module provides a standalone audit trail you can drop into any project. No external dependencies.

### Core Concepts

- **`ReceiptBuilder`** — Incrementally builds a receipt as your agent performs actions
- **`AuditTrail`** — High-level manager for storing, querying, and summarizing receipts
- **`ReceiptStore`** — Pluggable storage interface (in-memory store included, bring your own DB/filesystem)

### Usage

```typescript
import { ReceiptBuilder, AuditTrail } from './src/audit.js'

// Create an audit trail
const audit = new AuditTrail()

// Build a receipt during an agent run
const builder = new ReceiptBuilder('my-agent', 'My Agent', {
  trigger: 'automated',
  operatorEmail: 'dev@example.com',
})

builder.addAction({
  type: 'file:write',
  target: 'config.json',
  summary: 'Updated database connection string',
  status: 'completed',
  isRollbackEligible: true,
  preState: { content: '...original content...' },
})

// Finalize and store
const receipt = builder.build()
await audit.record(receipt)

// Query later
const all = await audit.list({ status: 'completed' })
console.log(audit.summarize(receipt))
```

### Custom Storage

Implement the `ReceiptStore` interface to persist receipts anywhere:

```typescript
import type { ReceiptStore, Receipt } from './src/audit.js'

class PostgresReceiptStore implements ReceiptStore {
  async save(receipt: Receipt) { /* INSERT INTO receipts ... */ }
  async load(id: string) { /* SELECT FROM receipts WHERE id = ... */ }
  async list(filter?) { /* SELECT FROM receipts WHERE ... */ }
}

const audit = new AuditTrail(new PostgresReceiptStore())
```

See [`examples/audit-example.ts`](./examples/audit-example.ts) for a full working example.

## Rollback

The `src/rollback.ts` module lets you reverse agent actions using pre-state captured in receipts.

### How It Works

1. **Before** a mutating action, capture the pre-state with `capturePreState()`
2. Store the pre-state in the action record (via `ReceiptBuilder.addAction()`)
3. When rollback is needed, the `RollbackEngine` processes actions in reverse order
4. Each action type has a handler that knows how to reverse it

### Built-in Handlers

| Action Type | Rollback Behavior |
|---|---|
| `db:write` | Returns pre-state rows for the caller to restore |
| `file:write` | Returns original file content to write back |
| `email:send` | Generates a correction email draft (can't unsend) |

### Usage

```typescript
import { RollbackEngine, capturePreState } from './src/rollback.js'

const engine = new RollbackEngine()

// Register custom handlers for your domain
engine.register('stripe:charge', async (action) => {
  const refund = await stripe.refunds.create({ charge: action.target })
  return { refundId: refund.id }
})

// Dry run first — see what would happen
const preview = await engine.execute(receipt, { dryRun: true })
console.log(engine.summarize(preview))

// Execute for real
const result = await engine.execute(receipt)
console.log(engine.summarize(result))
// ✅ Rollback complete
// Reversed: 3 actions
//   - [db:write] invoices → reversed
//   - [email:send] customer@acme.com → reversed
//   - [stripe:charge] ch_abc123 → reversed
// Skipped: 1
//   - [log:write] audit.log → not_eligible
```

### Options

```typescript
// Only roll back specific actions
await engine.execute(receipt, { actionIds: ['act_123', 'act_456'] })

// Dry run
await engine.execute(receipt, { dryRun: true })
```

See [`examples/rollback-example.ts`](./examples/rollback-example.ts) for a full working example.

## Beyond the Pattern

The Receipt Pattern gives you visibility. Plain JSON files in a folder. It's simple and it works.

If you need more — immutable receipt chains, rollback execution, team dashboards, compliance exports — I'm building that infrastructure. Coming soon. Follow along: [vinceglakas](https://x.com/vinceglakas).

---

**By [Vince Thomas](https://x.com/vinceglakas) — building in public.**

## License

MIT — do whatever you want with it.
