// ============================================================
// MEMU API — 7-Layer Memory Orchestrator
// NextHorizont AI · NemoClaw Stack
// ============================================================

import express, { Request, Response, NextFunction } from 'express'
import { createClient, SupabaseClient } from '@supabase/supabase-js'
import Redis from 'ioredis'
import { QdrantClient } from '@qdrant/js-client-rest'

// ── Types ────────────────────────────────────────────────────

interface MemoryEntry {
  content: string
  metadata?: Record<string, unknown>
  tags?: string[]
}

interface SemanticSearchResult {
  id: string
  content: string
  source_type: string
  similarity: number
  metadata: Record<string, unknown>
}

interface HealthStatus {
  status: 'ok' | 'degraded' | 'down'
  layers: Record<string, 'ok' | 'down'>
  uptime: number
  timestamp: string
}

// ── Config ───────────────────────────────────────────────────

const PORT = parseInt(process.env.PORT ?? '5000')
const MEMU_API_KEY = process.env.MEMU_API_KEY!
const REDIS_L1_TTL = parseInt(process.env.REDIS_L1_TTL_SECONDS ?? '3600')
const REDIS_L2_TTL = parseInt(process.env.REDIS_L2_TTL_SECONDS ?? '86400')
const SEMANTIC_THRESHOLD = 0.72

// ── Clients ──────────────────────────────────────────────────

const supabase: SupabaseClient = createClient(
  process.env.SUPABASE_URL!,
  process.env.SUPABASE_SERVICE_KEY!
)

const redis = new Redis(process.env.REDIS_URL ?? 'redis://redis:6379', {
  password: process.env.REDIS_PASSWORD,
  lazyConnect: true,
  retryStrategy: (times) => Math.min(times * 100, 3000),
})

const qdrant = new QdrantClient({ url: process.env.QDRANT_URL ?? 'http://qdrant:6333' })

// ── Embedding helper ─────────────────────────────────────────

async function getEmbedding(text: string): Promise<number[]> {
  const response = await fetch(
    'https://integrate.api.nvidia.com/v1/embeddings',
    {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${process.env.NVIDIA_API_KEY}`,
      },
      body: JSON.stringify({
        model: process.env.EMBEDDING_MODEL ?? 'nvidia/llama-3.2-nv-embedqa-1b-v2',
        input: text,
        input_type: 'query',
      }),
    }
  )
  if (!response.ok) throw new Error(`Embedding API error: ${response.status}`)
  const data = await response.json() as { data: Array<{ embedding: number[] }> }
  return data.data[0]!.embedding
}

// ── MEMU Layer Operations ────────────────────────────────────

/**
 * L1: Working Memory — Redis ephemeral, TTL 1h
 * Contexto de sesión activa en memoria RAM
 */
async function l1Set(sessionId: string, key: string, value: string): Promise<void> {
  const redisKey = `l1:${sessionId}:${key}`
  await redis.setex(redisKey, REDIS_L1_TTL, value)
}

async function l1Get(sessionId: string, key: string): Promise<string | null> {
  return redis.get(`l1:${sessionId}:${key}`)
}

async function l1GetAll(sessionId: string): Promise<Record<string, string>> {
  const keys = await redis.keys(`l1:${sessionId}:*`)
  if (!keys.length) return {}
  const values = await redis.mget(...keys)
  return Object.fromEntries(
    keys.map((k, i) => [k.replace(`l1:${sessionId}:`, ''), values[i] ?? ''])
  )
}

// ── Express App ──────────────────────────────────────────────

const app = express()
app.use(express.json({ limit: '2mb' }))

// Auth middleware
function requireApiKey(req: Request, res: Response, next: NextFunction): void {
  const key = req.headers['x-memu-api-key'] ?? req.headers['authorization']?.replace('Bearer ', '')
  if (key !== MEMU_API_KEY) {
    res.status(401).json({ error: 'Unauthorized' })
    return
  }
  next()
}

app.use('/api', requireApiKey)

// ── Health ───────────────────────────────────────────────────

app.get('/health', async (_req: Request, res: Response) => {
  const layers: Record<string, 'ok' | 'down'> = {}

  // Check Redis
  try {
    await redis.ping()
    layers['L1_L2_redis'] = 'ok'
  } catch {
    layers['L1_L2_redis'] = 'down'
  }

  // Check Supabase
  try {
    await supabase.from('memu_meta').select('id').limit(1)
    layers['L3_L6_L7_supabase'] = 'ok'
  } catch {
    layers['L3_L6_L7_supabase'] = 'down'
  }

  // Check Qdrant
  try {
    await qdrant.getCollections()
    layers['L4_qdrant'] = 'ok'
  } catch {
    layers['L4_qdrant'] = 'down'
  }

  const allOk = Object.values(layers).every((s) => s === 'ok')
  const health: HealthStatus = {
    status: allOk ? 'ok' : 'degraded',
    layers,
    uptime: process.uptime(),
    timestamp: new Date().toISOString(),
  }

  res.status(allOk ? 200 : 206).json(health)
})

// ── Start ─────────────────────────────────────────────────────

async function start(): Promise<void> {
  await redis.connect()
  console.log('[MEMU] Redis connected')

  // Inicializar colección Qdrant si no existe
  try {
    await qdrant.getCollection('memu_semantic')
  } catch {
    await qdrant.createCollection('memu_semantic', {
      vectors: { size: 1024, distance: 'Cosine' },
    })
    console.log('[MEMU] Qdrant collection created')
  }

  app.listen(PORT, () => {
    console.log(`[MEMU] API listening on port ${PORT}`)
    console.log('[MEMU] 7-layer memory system ready')
  })
}

start().catch((err: unknown) => {
  console.error('[MEMU] Fatal error:', err)
  process.exit(1)
})
