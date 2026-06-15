/**
 * Rollback Example — The Receipt Pattern
 *
 * Shows how to roll back agent actions using the rollback engine.
 * Run: npx tsx examples/rollback-example.ts
 */

import { ReceiptBuilder, AuditTrail } from '../src/audit.js'
import { RollbackEngine, capturePreState } from '../src/rollback.js'

async function main() {
  const audit = new AuditTrail()
  const engine = new RollbackEngine()

  // Register a custom rollback handler for Stripe charges
  engine.register('stripe:charge', async (action) => {
    console.log(`  → Would refund Stripe charge: ${action.target}`)
    // In production: const refund = await stripe.refunds.create({ charge: action.target })
    return { refundId: 'rf_simulated_123', amount: (action.preState as any)?.amount }
  })

  // ─── Simulate an agent run ────────────────────────────────────────

  const builder = new ReceiptBuilder('billing-agent', 'Billing Agent', {
    trigger: 'automated',
    operatorEmail: 'ops@example.com',
  })

  // Action 1: Update database (rollback-eligible with pre-state)
  const dbPreState = capturePreState('db:write', 'invoices', {
    rows: [{ id: 42, status: 'pending', amount: 500 }],
  })

  builder.addAction({
    type: 'db:write',
    target: 'invoices',
    summary: 'Updated invoice #42 status to "paid"',
    status: 'completed',
    isRollbackEligible: true,
    preState: dbPreState,
    durationMs: 45,
  })

  // Action 2: Send confirmation email (generates correction draft on rollback)
  builder.addAction({
    type: 'email:send',
    target: 'customer@acme.com',
    summary: 'Payment confirmation for invoice #42',
    status: 'completed',
    isRollbackEligible: true,
    durationMs: 1200,
  })

  // Action 3: Stripe charge (custom handler)
  builder.addAction({
    type: 'stripe:charge',
    target: 'ch_abc123',
    summary: 'Charged $500 to card ending 4242',
    status: 'completed',
    isRollbackEligible: true,
    preState: { amount: 50000, currency: 'usd' },
    durationMs: 890,
  })

  // Action 4: Log entry (not rollback-eligible)
  builder.addAction({
    type: 'log:write',
    target: 'audit.log',
    summary: 'Logged payment event',
    status: 'completed',
    isRollbackEligible: false,
    durationMs: 5,
  })

  const receipt = builder.build()
  await audit.record(receipt)

  // ─── Dry run first ────────────────────────────────────────────────

  console.log('=== Dry Run ===')
  const preview = await engine.execute(receipt, { dryRun: true })
  console.log(engine.summarize(preview))

  // ─── Execute rollback ─────────────────────────────────────────────

  console.log('\n=== Executing Rollback ===')
  const result = await engine.execute(receipt)
  console.log(engine.summarize(result))

  // ─── Inspect details ──────────────────────────────────────────────

  console.log('\n=== Rollback Details ===')
  for (const action of result.rolledBack) {
    console.log(`\n[${action.type}] ${action.target}:`)
    console.log(JSON.stringify(action.result, null, 2))
  }
}

main().catch(console.error)
