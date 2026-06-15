// route-auth-audit.mjs — example workflow.
//
// Fan out one agent per route file to flag missing auth checks, adversarially verify each
// finding with 3 skeptics, then synthesize a report. Demonstrates: parallel fan-out,
// reduce in plain JS, a per-finding verify barrier, and schema-validated agents.
//
// Run from the skill folder:
//   node references/route-auth-audit.mjs /path/to/your-app/src/routes
//   WF_JOURNAL=.wf/audit.json node references/route-auth-audit.mjs ./routes   (resumable)

import { readdirSync, statSync } from 'node:fs'
import { join } from 'node:path'
import { agent, parallel, phase, log } from '../tools/wf-runtime.mjs'

const ROOT = process.argv[2] || './routes'

// Collect route files to review.
function walk(dir) {
  const out = []
  for (const name of readdirSync(dir)) {
    const p = join(dir, name)
    if (statSync(p).isDirectory()) out.push(...walk(p))
    else if (/\.(ts|js|tsx|jsx)$/.test(name)) out.push(p)
  }
  return out
}
const files = walk(ROOT)
log(`Auditing ${files.length} route file(s) under ${ROOT}`)

const FINDINGS = {
  type: 'object',
  additionalProperties: false,
  properties: {
    findings: {
      type: 'array',
      items: {
        type: 'object',
        additionalProperties: false,
        properties: {
          file: { type: 'string' },
          route: { type: 'string' },
          issue: { type: 'string' },
          severity: { type: 'string', enum: ['high', 'medium', 'low'] },
        },
        required: ['file', 'route', 'issue', 'severity'],
      },
    },
  },
  required: ['findings'],
}

const VERDICT = {
  type: 'object',
  additionalProperties: false,
  properties: { refuted: { type: 'boolean' }, reason: { type: 'string' } },
  required: ['refuted', 'reason'],
}

// 1) Fan out: one reviewer per file.
phase('Review')
const reviews = await parallel(
  files.map((f) => () =>
    agent(
      `Read ${f} and list every route handler that performs a sensitive action (mutations, ` +
        `reading private data, admin ops) WITHOUT an authentication or authorization check. ` +
        `Be precise about the route path and what's missing.`,
      { schema: FINDINGS, label: f }
    )
  )
)

// 2) Reduce in plain JS.
const findings = reviews.filter(Boolean).flatMap((r) => r.findings)
log(`${findings.length} candidate finding(s)`)

// 3) Adversarial verify: 3 skeptics per finding, keep only if a majority fail to refute.
phase('Verify')
const verified = await parallel(
  findings.map((finding) => async () => {
    const votes = await parallel(
      [0, 1, 2].map(() => () =>
        agent(
          `A reviewer claims this is a real missing-auth vulnerability:\n${JSON.stringify(finding)}\n\n` +
            `Try hard to REFUTE it. Check ${finding.file} for middleware, guards, or framework-level ` +
            `auth that the reviewer may have missed. Default to refuted=true if you are uncertain.`,
          { schema: VERDICT, label: `verify:${finding.route}` }
        )
      )
    )
    const survived = votes.filter(Boolean).filter((v) => !v.refuted).length >= 2
    return survived ? finding : null
  })
)
const confirmed = verified.filter(Boolean)

// 4) Synthesize.
phase('Report')
const report = await agent(
  `Write a concise Markdown security report of these CONFIRMED missing-auth findings, ` +
    `grouped by severity, with a one-line fix suggestion each:\n${JSON.stringify(confirmed, null, 2)}`
)

console.log(report)
log(`\nDone: ${confirmed.length}/${findings.length} findings survived verification`)
