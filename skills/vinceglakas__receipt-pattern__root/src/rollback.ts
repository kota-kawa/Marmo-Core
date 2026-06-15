/**
 * Rollback Engine — The Receipt Pattern
 *
 * Reverses agent actions using pre-state captured in receipts.
 * Supports built-in handlers for common action types and
 * custom handlers for domain-specific operations.
 *
 * No external dependencies. Bring your own storage.
 */

import type { ActionRecord, Receipt, ReceiptStore } from './audit.js'

// ─── Types ───────────────────────────────────────────────────────────

export interface RollbackOptions {
  /** Preview what would be rolled back without executing */
  dryRun?: boolean
  /** Only roll back specific action IDs */
  actionIds?: string[]
  /** Reason for the rollback (recorded in the rollback receipt) */
  reason?: string
}

export interface RolledBackAction {
  actionId: string
  type: string
  target: string
  result: unknown
}

export interface SkippedAction {
  actionId: string
  type: string
  target: string
  reason: string
}

export interface RollbackResult {
  /** Actions that were successfully rolled back */
  rolledBack: RolledBackAction[]
  /** Actions that were skipped (not eligible, no pre-state, etc.) */
  skipped: SkippedAction[]
  /** Receipt ID for the rollback itself */
  rollbackReceiptId: string
  /** True if this was a dry run */
  dryRun: boolean
}

/** A function that reverses a single action */
export type RollbackHandler = (action: ActionRecord) => Promise<unknown>

// ─── Built-in Rollback Handlers ──────────────────────────────────────

/**
 * Capture pre-state before a mutating action.
 * Call this before executing writes to enable rollback.
 *
 * @example
 * const preState = capturePreState('file:write', '/tmp/config.json', existingContent)
 * // ... perform the write ...
 * // preState is stored in the action record for later rollback
 */
export function capturePreState(actionType: string, target: string, data: unknown): unknown {
  return {
    type: actionType,
    target,
    capturedAt: new Date().toISOString(),
    data,
  }
}

/**
 * Built-in handler: reverse a database write.
 * Returns the pre-state data for the caller to apply.
 *
 * In production, you'd execute the actual restore
 * (UPDATE/INSERT/DELETE) inside this handler.
 */
export async function rollbackDbWrite(action: ActionRecord): Promise<unknown> {
  if (!action.preState) {
    return { skipped: true, reason: 'no_pre_state' }
  }
  // In a real implementation, you'd restore the rows here.
  // Example: await db.query('UPDATE ...', preState.rows)
  return { restored: true, preState: action.preState }
}

/**
 * Built-in handler: reverse a file write.
 * Returns the pre-state content for the caller to write back.
 *
 * In production, you'd write the original content
 * back to the file system here.
 */
export async function rollbackFileWrite(action: ActionRecord): Promise<unknown> {
  if (!action.preState) {
    return { skipped: true, reason: 'no_pre_state' }
  }
  // In a real implementation: fs.writeFile(action.target, preState.content)
  return { restored: true, preState: action.preState }
}

/**
 * Built-in handler: "reverse" an email send.
 * You can't unsend email, so this generates a correction draft.
 */
export async function rollbackEmailSend(action: ActionRecord): Promise<unknown> {
  return {
    type: 'correction_draft',
    originalTarget: action.target,
    summary: `Correction email draft generated for: ${action.summary}`,
    draft: {
      subject: `[Correction] Re: ${action.summary}`,
      body: '', // Fill in with your correction message
    },
  }
}

// ─── Rollback Engine ─────────────────────────────────────────────────

/**
 * The rollback engine. Register handlers for action types,
 * then execute rollbacks against receipts.
 *
 * @example
 * const engine = new RollbackEngine()
 * engine.register('file:write', rollbackFileWrite)
 * engine.register('db:write', rollbackDbWrite)
 * engine.register('email:send', rollbackEmailSend)
 *
 * // Custom handler
 * engine.register('stripe:charge', async (action) => {
 *   const refund = await stripe.refunds.create({ charge: action.target })
 *   return { refundId: refund.id }
 * })
 *
 * const result = await engine.execute(receipt)
 */
export class RollbackEngine {
  private handlers = new Map<string, RollbackHandler>()

  constructor() {
    // Register built-in handlers
    this.handlers.set('db:write', rollbackDbWrite)
    this.handlers.set('file:write', rollbackFileWrite)
    this.handlers.set('email:send', rollbackEmailSend)
  }

  /** Register a rollback handler for an action type */
  register(actionType: string, handler: RollbackHandler): void {
    this.handlers.set(actionType, handler)
  }

  /**
   * Execute rollback for a receipt.
   * Actions are reversed in reverse-chronological order.
   */
  async execute(receipt: Receipt, options?: RollbackOptions): Promise<RollbackResult> {
    const dryRun = options?.dryRun ?? false
    const rolledBack: RolledBackAction[] = []
    const skipped: SkippedAction[] = []

    // Process actions in reverse order
    const actions = [...receipt.actions].reverse()
    const targetIds = options?.actionIds ? new Set(options.actionIds) : null

    for (const action of actions) {
      // Skip if filtering by action IDs and this one isn't included
      if (targetIds && !targetIds.has(action.id)) continue

      // Skip if not eligible
      if (!action.isRollbackEligible) {
        skipped.push({ actionId: action.id, type: action.type, target: action.target, reason: 'not_eligible' })
        continue
      }

      // Skip if already rolled back
      if (action.rolledBackAt) {
        skipped.push({ actionId: action.id, type: action.type, target: action.target, reason: 'already_rolled_back' })
        continue
      }

      const handler = this.handlers.get(action.type)
      if (!handler) {
        skipped.push({ actionId: action.id, type: action.type, target: action.target, reason: 'no_handler' })
        continue
      }

      if (dryRun) {
        rolledBack.push({ actionId: action.id, type: action.type, target: action.target, result: { dryRun: true } })
        continue
      }

      try {
        const result = await handler(action)
        const resultObj = result as Record<string, unknown>
        if (resultObj?.skipped) {
          skipped.push({ actionId: action.id, type: action.type, target: action.target, reason: String(resultObj.reason ?? 'handler_skipped') })
        } else {
          rolledBack.push({ actionId: action.id, type: action.type, target: action.target, result })
        }
      } catch (err) {
        skipped.push({ actionId: action.id, type: action.type, target: action.target, reason: `error: ${err}` })
      }
    }

    return {
      rolledBack,
      skipped,
      rollbackReceiptId: `rcpt_rollback_${receipt.id.slice(5)}`,
      dryRun,
    }
  }

  /** Format a rollback result as a human-readable string */
  summarize(result: RollbackResult): string {
    const lines = [
      result.dryRun ? '🔍 Rollback dry run' : '✅ Rollback complete',
      `Reversed: ${result.rolledBack.length} actions`,
      ...result.rolledBack.map(r => `  - [${r.type}] ${r.target} → reversed`),
      `Skipped: ${result.skipped.length}`,
      ...result.skipped.map(s => `  - [${s.type}] ${s.target} → ${s.reason}`),
      `Rollback receipt: ${result.rollbackReceiptId}`,
    ]
    return lines.join('\n')
  }
}
