// smoke.mjs — minimal end-to-end check that the runtime can drive Copilot.
// Spawns 3 trivial agents in parallel, each returning structured JSON, then synthesizes.
// Costs ~4 small Copilot invocations. Requires you to be logged in (`copilot` once).
//
//   node tools/smoke.mjs

import { agent, parallel, phase, log } from './wf-runtime.mjs'

const NUM = {
  type: 'object',
  additionalProperties: false,
  properties: { word: { type: 'string' }, length: { type: 'number' } },
  required: ['word', 'length'],
}

phase('Fan out')
const words = ['orchestration', 'copilot', 'workflow']
const results = await parallel(
  words.map((w) => () => agent(`The word is "${w}". Return its character count.`, { schema: NUM, label: w }))
)

const ok = results.filter(Boolean)
log(`Got ${ok.length}/${words.length} structured responses`)

phase('Synthesize')
const summary = await agent(
  `Write one sentence summarizing these word lengths: ${JSON.stringify(ok)}`
)

console.log('\n=== RESULT ===')
console.log(summary)
console.log('\n=== RAW ===')
console.log(JSON.stringify(ok, null, 2))
