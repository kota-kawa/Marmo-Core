// wf-runtime.mjs — deterministic multi-agent orchestration on top of the GitHub Copilot CLI.
//
// Each agent() call runs a fresh, headless `copilot -p` child process. The runtime gives
// you Claude-Code-Workflow-style primitives — agent / parallel / pipeline / phase / log —
// plus an optional on-disk journal so a crashed or edited run can resume from cached steps.
//
// Usage from an orchestrator script:
//   import { agent, parallel, pipeline, phase, log } from './wf-runtime.mjs'

import { spawn } from 'node:child_process'
import { createHash } from 'node:crypto'
import os from 'node:os'
import fs from 'node:fs'
import path from 'node:path'

// ── Config (override via env) ────────────────────────────────────────────────
const MAX_CONCURRENT = Number(process.env.WF_CONCURRENCY) || Math.max(1, os.cpus().length - 2)
const COPILOT_BIN = process.env.WF_COPILOT_BIN || 'copilot'
const JOURNAL_PATH = process.env.WF_JOURNAL || null // set to a file path to enable resume
const AGENT_TIMEOUT_MS = Number(process.env.WF_TIMEOUT_MS) || 10 * 60 * 1000

// ── Concurrency pool ─────────────────────────────────────────────────────────
let active = 0
const waiters = []
const acquire = () =>
  active < MAX_CONCURRENT
    ? ((active += 1), Promise.resolve())
    : new Promise((resolve) => waiters.push(resolve))
const release = () => {
  active -= 1
  const next = waiters.shift()
  if (next) {
    active += 1
    next()
  }
}

// ── Progress output (stderr, so stdout stays clean for the final result) ──────
let currentPhase = ''
const counts = {}
export const log = (msg) => process.stderr.write(`▸ ${msg}\n`)
export const phase = (title) => {
  currentPhase = title
  counts[title] = counts[title] || 0
  log(`\n── ${title} ──`)
}

// ── Journal (optional resume) ─────────────────────────────────────────────────
let journal = {}
if (JOURNAL_PATH && fs.existsSync(JOURNAL_PATH)) {
  try {
    journal = JSON.parse(fs.readFileSync(JOURNAL_PATH, 'utf8'))
    log(`Resuming: ${Object.keys(journal).length} cached step(s) from ${JOURNAL_PATH}`)
  } catch {
    journal = {}
  }
}
const journalKey = (prompt, opts) =>
  createHash('sha256').update(JSON.stringify({ prompt, m: opts.model || '', s: opts.schema || null })).digest('hex')
const persist = () => {
  if (JOURNAL_PATH) {
    fs.mkdirSync(path.dirname(JOURNAL_PATH), { recursive: true })
    fs.writeFileSync(JOURNAL_PATH, JSON.stringify(journal, null, 2))
  }
}

// ── The Copilot child process ─────────────────────────────────────────────────
function runCopilot(prompt, { model } = {}) {
  return new Promise((resolve, reject) => {
    const args = [
      '-p', prompt,
      '--allow-all-tools', // non-interactive needs this; scope it down in real use
      '--no-ask-user', // agent never blocks waiting for human input
      '-s', // silent: print only the response, no stats
      '--no-custom-instructions', // children must NOT re-trigger the workflow skill (no fork bombs)
    ]
    if (model) args.push('--model', model)

    const child = spawn(COPILOT_BIN, args, { stdio: ['ignore', 'pipe', 'pipe'] })
    let out = ''
    let err = ''
    const timer = setTimeout(() => {
      child.kill('SIGKILL')
      reject(new Error('agent timed out'))
    }, AGENT_TIMEOUT_MS)

    child.stdout.on('data', (d) => (out += d))
    child.stderr.on('data', (d) => (err += d))
    child.on('error', (e) => {
      clearTimeout(timer)
      reject(e)
    })
    child.on('close', (code) => {
      clearTimeout(timer)
      if (code === 0) resolve(out.trim())
      else reject(new Error(`copilot exited ${code}: ${err.slice(0, 500)}`))
    })
  })
}

// Pull the first JSON object/array out of a model response (handles ``` fences).
function extractJson(text) {
  const fenced = text.match(/```(?:json)?\s*([\s\S]*?)```/)
  const body = fenced ? fenced[1] : text
  const start = body.search(/[[{]/)
  if (start === -1) throw new Error('no JSON found')
  return JSON.parse(body.slice(start))
}

/**
 * Run one headless Copilot agent.
 * @param {string} prompt
 * @param {{schema?:object, model?:string, label?:string, retries?:number}} [opts]
 * @returns {Promise<any>} parsed object if `schema` given, else raw text. null on failure.
 */
export async function agent(prompt, opts = {}) {
  const { schema, model, label, retries = 2 } = opts
  const key = journalKey(prompt, opts)
  if (journal[key] !== undefined) {
    log(`✓ cached ${label || currentPhase}`)
    return journal[key]
  }

  await acquire()
  const tag = label || currentPhase || 'agent'
  if (currentPhase) counts[currentPhase] += 1
  log(`→ ${tag}`)
  try {
    let p = schema
      ? `${prompt}\n\nReturn ONLY valid JSON matching this JSON Schema. No prose, no markdown fences:\n${JSON.stringify(schema)}`
      : prompt

    for (let attempt = 0; attempt <= retries; attempt += 1) {
      const text = await runCopilot(p, { model })
      if (!schema) {
        journal[key] = text
        persist()
        return text
      }
      try {
        const parsed = extractJson(text)
        journal[key] = parsed
        persist()
        return parsed
      } catch {
        p = `${prompt}\n\nYour previous output was not valid JSON. Return ONLY JSON matching this schema:\n${JSON.stringify(schema)}`
      }
    }
    log(`✗ ${tag}: gave up after ${retries + 1} attempts`)
    return null
  } catch (e) {
    log(`✗ ${tag}: ${e.message}`)
    return null
  } finally {
    release()
  }
}

/**
 * Run thunks concurrently. BARRIER: waits for all. Failures resolve to null
 * (never rejects the whole call) — always .filter(Boolean) the results.
 * @param {Array<() => Promise<any>>} thunks
 */
export const parallel = (thunks) => Promise.all(thunks.map((t) => Promise.resolve().then(t).catch(() => null)))

/**
 * Stream each item through all stages independently — NO barrier between stages.
 * Item A can be in stage 3 while item B is still in stage 1.
 * Each stage callback gets (prevResult, originalItem, index). A throwing stage drops
 * that item to null and skips its remaining stages.
 * @param {any[]} items
 * @param {...((prev:any, item:any, i:number) => Promise<any>)} stages
 */
export const pipeline = (items, ...stages) =>
  Promise.all(
    items.map(async (item, i) => {
      let acc = item
      for (const stage of stages) {
        try {
          acc = await stage(acc, item, i)
        } catch {
          return null
        }
      }
      return acc
    })
  )
