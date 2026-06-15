/**
 * Audit Trail — The Receipt Pattern
 *
 * Standalone audit trail for AI agent actions.
 * Records every significant action with full context,
 * enabling post-hoc review, compliance, and debugging.
 *
 * No external dependencies. Works with any storage backend.
 */

// ─── Types ───────────────────────────────────────────────────────────

/** A single action performed by an agent */
export interface ActionRecord {
  id: string
  runId: string
  agentId: string
  sequence: number
  type: string                // e.g. "file:write", "db:write", "email:send", "api:call"
  target: string              // what was acted on (file path, table name, endpoint)
  summary: string             // human-readable description
  status: 'completed' | 'failed' | 'anomaly'
  preState?: unknown          // state before the action (for rollback)
  isRollbackEligible: boolean
  rollbackHandler?: string    // name of the handler to use for rollback
  rolledBackAt?: string       // ISO timestamp if rolled back
  anomalyDetail?: string      // details if status is 'anomaly'
  durationMs?: number
  timestamp: string           // ISO timestamp
}

/** An anomaly detected during a run */
export interface Anomaly {
  actionId: string
  actionSequence: number
  detail: string
}

/** A complete receipt — the audit record of one agent run */
export interface Receipt {
  id: string
  runId: string
  agentId: string
  agentName: string
  agentVersion?: string
  orgId?: string
  orgName?: string
  operatorEmail?: string
  trigger: string
  status: 'completed' | 'failed' | 'partial' | 'rolled_back'
  startedAt: string
  completedAt: string
  durationMs: number
  actionCount: number
  anomalyCount: number
  rollbackAvailable: boolean
  rollbackExecutedAt?: string
  actions: ActionRecord[]
  anomalies: Anomaly[]
  sdkVersion: string
}

// ─── Storage Interface ───────────────────────────────────────────────

/**
 * Pluggable storage backend for receipts.
 * Implement this interface to store receipts in any backend
 * (filesystem, database, S3, etc.)
 */
export interface ReceiptStore {
  save(receipt: Receipt): Promise<void>
  load(receiptId: string): Promise<Receipt | null>
  list(filter?: { agentId?: string; status?: string; since?: string }): Promise<Receipt[]>
}

// ─── In-Memory Store (default) ───────────────────────────────────────

/** Simple in-memory store for development and testing */
export class InMemoryReceiptStore implements ReceiptStore {
  private receipts = new Map<string, Receipt>()

  async save(receipt: Receipt): Promise<void> {
    this.receipts.set(receipt.id, structuredClone(receipt))
  }

  async load(receiptId: string): Promise<Receipt | null> {
    return this.receipts.get(receiptId) ?? null
  }

  async list(filter?: { agentId?: string; status?: string; since?: string }): Promise<Receipt[]> {
    let results = Array.from(this.receipts.values())
    if (filter?.agentId) results = results.filter(r => r.agentId === filter.agentId)
    if (filter?.status) results = results.filter(r => r.status === filter.status)
    if (filter?.since) results = results.filter(r => r.completedAt >= filter.since)
    return results
  }
}

// ─── Receipt Builder ─────────────────────────────────────────────────

/** Incrementally build a receipt as actions are performed */
export class ReceiptBuilder {
  private actions: ActionRecord[] = []
  private startedAt: string
  private runId: string
  private receiptId: string

  constructor(
    private agentId: string,
    private agentName: string,
    private opts: { trigger?: string; orgId?: string; operatorEmail?: string } = {},
  ) {
    const now = Date.now()
    const hex = Math.random().toString(16).slice(2, 8)
    this.runId = `run_${now}_${hex}`
    this.receiptId = `rcpt_${now}_${hex}`
    this.startedAt = new Date(now).toISOString()
  }

  /** Record a completed action */
  addAction(action: Omit<ActionRecord, 'id' | 'runId' | 'agentId' | 'sequence' | 'timestamp'>): void {
    this.actions.push({
      ...action,
      id: `act_${Date.now()}_${Math.random().toString(16).slice(2, 6)}`,
      runId: this.runId,
      agentId: this.agentId,
      sequence: this.actions.length + 1,
      timestamp: new Date().toISOString(),
    })
  }

  /** Finalize and return the receipt */
  build(): Receipt {
    const now = new Date().toISOString()
    const anomalies: Anomaly[] = this.actions
      .filter(a => a.status === 'anomaly' && a.anomalyDetail)
      .map(a => ({ actionId: a.id, actionSequence: a.sequence, detail: a.anomalyDetail! }))

    const hasFailure = this.actions.some(a => a.status === 'failed')
    const hasAnomaly = anomalies.length > 0

    return {
      id: this.receiptId,
      runId: this.runId,
      agentId: this.agentId,
      agentName: this.agentName,
      orgId: this.opts.orgId,
      operatorEmail: this.opts.operatorEmail,
      trigger: this.opts.trigger ?? 'manual',
      status: hasFailure ? 'failed' : hasAnomaly ? 'partial' : 'completed',
      startedAt: this.startedAt,
      completedAt: now,
      durationMs: Date.now() - new Date(this.startedAt).getTime(),
      actionCount: this.actions.length,
      anomalyCount: anomalies.length,
      rollbackAvailable: this.actions.some(a => a.isRollbackEligible),
      actions: this.actions,
      anomalies,
      sdkVersion: 'receipt-pattern/1.0.0',
    }
  }
}

// ─── Audit Trail ─────────────────────────────────────────────────────

/**
 * High-level audit trail manager.
 * Wraps a store and provides convenience methods.
 */
export class AuditTrail {
  constructor(private store: ReceiptStore = new InMemoryReceiptStore()) {}

  /** Save a receipt to the audit trail */
  async record(receipt: Receipt): Promise<void> {
    await this.store.save(receipt)
  }

  /** Retrieve a receipt by ID */
  async get(receiptId: string): Promise<Receipt | null> {
    return this.store.load(receiptId)
  }

  /** List receipts with optional filters */
  async list(filter?: { agentId?: string; status?: string; since?: string }): Promise<Receipt[]> {
    return this.store.list(filter)
  }

  /** Get a human-readable summary of a receipt */
  summarize(receipt: Receipt): string {
    const lines = [
      `Receipt: ${receipt.id}`,
      `Agent: ${receipt.agentName} (${receipt.agentId})`,
      `Status: ${receipt.status}`,
      `Duration: ${receipt.durationMs}ms`,
      `Actions: ${receipt.actionCount} | Anomalies: ${receipt.anomalyCount}`,
      `Rollback: ${receipt.rollbackAvailable ? 'available' : 'not available'}`,
      '',
      'Actions:',
      ...receipt.actions.map(a =>
        `  ${a.sequence}. [${a.type}] ${a.target} — ${a.summary} (${a.status})`
      ),
    ]
    if (receipt.anomalies.length > 0) {
      lines.push('', 'Anomalies:')
      receipt.anomalies.forEach(a => lines.push(`  ⚠ Action #${a.actionSequence}: ${a.detail}`))
    }
    return lines.join('\n')
  }
}
