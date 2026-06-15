/**
 * Audit Trail Example — The Receipt Pattern
 *
 * Shows how to build receipts and query the audit trail.
 * Run: npx tsx examples/audit-example.ts
 */

import { ReceiptBuilder, AuditTrail } from '../src/audit.js'

async function main() {
  // 1. Create an audit trail (uses in-memory store by default)
  const audit = new AuditTrail()

  // 2. Start building a receipt for an agent run
  const builder = new ReceiptBuilder('claude-code', 'Claude Code', {
    trigger: 'manual',
    operatorEmail: 'dev@example.com',
  })

  // 3. Record actions as they happen
  builder.addAction({
    type: 'file:write',
    target: 'src/auth/middleware.ts',
    summary: 'Added rate limiting middleware — 100 req/min per IP',
    status: 'completed',
    isRollbackEligible: true,
    preState: { content: '// original file content...' },
    durationMs: 340,
  })

  builder.addAction({
    type: 'file:write',
    target: 'src/auth/middleware.test.ts',
    summary: 'Added 6 tests for rate limiting edge cases',
    status: 'completed',
    isRollbackEligible: true,
    preState: null, // new file, no pre-state
    durationMs: 520,
  })

  builder.addAction({
    type: 'shell:exec',
    target: 'npm test -- --grep "rate limit"',
    summary: 'Ran rate limiting tests — 6/6 passed',
    status: 'completed',
    isRollbackEligible: false, // can't undo a test run
    durationMs: 4200,
  })

  // 4. Finalize the receipt
  const receipt = builder.build()

  // 5. Store it in the audit trail
  await audit.record(receipt)

  // 6. Query and display
  console.log('=== Receipt Summary ===')
  console.log(audit.summarize(receipt))
  console.log()

  // 7. List all receipts
  const all = await audit.list()
  console.log(`Total receipts: ${all.length}`)

  // 8. Filter by status
  const completed = await audit.list({ status: 'completed' })
  console.log(`Completed: ${completed.length}`)

  // 9. Raw JSON
  console.log('\n=== Raw Receipt JSON ===')
  console.log(JSON.stringify(receipt, null, 2))
}

main().catch(console.error)
