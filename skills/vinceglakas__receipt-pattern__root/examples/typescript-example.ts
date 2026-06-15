import { writeFileSync, mkdirSync, existsSync, readdirSync, readFileSync } from 'fs';
import { randomBytes } from 'crypto';

// --- Types ---

interface ReceiptAction {
  sequence: number;
  type: 'file:write' | 'file:delete' | 'api:call' | 'db:write' | 'email:send' | 'deploy' | 'shell:exec';
  target: string;
  summary: string;
  status: 'success' | 'failed' | 'anomaly';
  isRollbackEligible: boolean;
  durationMs: number;
  timestamp: string;
}

interface Anomaly {
  actionSequence: number;
  detail: string;
}

interface Receipt {
  id: string;
  agentId: string;
  sessionId: string;
  timestamp: string;
  trigger: 'manual' | 'scheduled' | 'webhook';
  status: 'completed' | 'failed' | 'partial' | 'rolled_back';
  durationMs: number;
  actions: ReceiptAction[];
  anomalies: Anomaly[];
  rollbackAvailable: boolean;
  sdkVersion: string;
}

// --- Helpers ---

function makeReceiptId(): string {
  return `rcpt_${Math.floor(Date.now() / 1000)}_${randomBytes(3).toString('hex')}`;
}

function writeReceipt(receipt: Receipt): string {
  if (!existsSync('receipts')) mkdirSync('receipts', { recursive: true });

  const now = new Date();
  const ts = now.toISOString().replace(/T/, '-').replace(/:/g, '-').replace(/\..+/, '');
  const mainType = receipt.actions[0]?.type.replace(':', '-') ?? 'unknown';
  const filePath = `receipts/${ts}-${mainType}.json`;

  writeFileSync(filePath, JSON.stringify(receipt, null, 2) + '\n');
  return filePath;
}

function getLastReceipt(): Receipt | null {
  if (!existsSync('receipts')) return null;
  const files = readdirSync('receipts').filter(f => f.endsWith('.json')).sort();
  if (files.length === 0) return null;
  return JSON.parse(readFileSync(`receipts/${files[files.length - 1]}`, 'utf-8'));
}

// --- Usage Example ---

const startTime = Date.now();

// ... your agent does work here ...

const receipt: Receipt = {
  id: makeReceiptId(),
  agentId: 'my-agent',
  sessionId: `sess_${new Date().toISOString().slice(0, 10).replace(/-/g, '')}`,
  timestamp: new Date().toISOString(),
  trigger: 'manual',
  status: 'completed',
  durationMs: Date.now() - startTime,
  actions: [
    {
      sequence: 1,
      type: 'file:write',
      target: 'src/index.ts',
      summary: 'Refactored main entry point — extracted config into separate module',
      status: 'success',
      isRollbackEligible: true,
      durationMs: 450,
      timestamp: new Date().toISOString(),
    },
  ],
  anomalies: [],
  rollbackAvailable: true,
  sdkVersion: 'receipt-pattern/1.0.0',
};

const path = writeReceipt(receipt);
console.log(`Receipt written: ${path}`);
