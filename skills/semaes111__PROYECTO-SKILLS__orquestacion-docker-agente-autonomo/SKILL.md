---
name: docker-agent-orchestration
description: >
  Orquestacion Docker de agente autonomo con Claude Max OAuth ($0 API billing),
  motor ClaudeMaxRunner (subprocess claude --print), SmartRouter dual-speed
  (5ms heuristic + 3s LLM fallback), bucle agentico multi-turn de 10 acciones,
  memoria 3-capas (Redis/mem0/pgvector 768-dim nomic embeddings), VeracityCore
  control epistemico con deteccion de degradacion, Watcher audit trail completo,
  sandboxes de ejecucion de codigo (snekbox + Docker), bot Telegram, n8n workflows.
  11 servicios Docker, 100% self-hosted en VPS. Basado en CLAUDE-BRAIN v2.0
  (Python 3.12 + FastAPI + PostgreSQL 15 + Redis + LibreChat).
  Usar cuando el usuario mencione: agente autonomo, orquestacion Docker,
  multi-agente, Claude Max, $0 API, agentic loop, router inteligente,
  sandbox de codigo, bot Telegram con IA, sistema de agentes, agent orchestration,
  self-hosted agent, watcher, audit trail, control epistemico, veracity.
metadata:
  version: "2.0.0"
  source_repo: "https://github.com/semaes111/CLAUDE-BRAIN"
  category: agent-infrastructure
  python: ">=3.12"
triggers:
  - "agente autonomo"
  - "orquestacion Docker"
  - "Claude Max OAuth"
  - "agentic loop"
  - "multi-agente"
  - "self-hosted agent"
  - "docker agent"
  - "watcher audit"
  - "veracity control"
---

# Docker Agent Orchestration: CLAUDE-BRAIN Architecture

## Vision General

CLAUDE-BRAIN es un agente autonomo 100% Dockerizado que ejecuta Claude via Max OAuth (subscription, **$0 API extra**) en lugar de API keys de pago. El diseno se basa en 5 pilares:

1. **ClaudeMaxRunner** — Motor subprocess que invoca `claude --print` CLI
2. **SmartRouter** — Enrutamiento dual-speed: heuristico (<5ms) + LLM fallback (~3s)
3. **AgenticLoop** — Bucle multi-turn con 10 tipos de accion y deteccion de atascos
4. **VeracityCore** — Control epistemico en 3 niveles con deteccion de degradacion
5. **Watcher** — Audit trail completo a Supabase + Redis con metricas en tiempo real

## Los 11 Servicios Docker

| Servicio | Imagen/Build | Puerto | Proposito |
|----------|-------------|--------|-----------|
| cb-agent | Build ./agent | 8000 | FastAPI principal: API, routing, loop, memoria |
| cb-webui | LibreChat | 3080 | Interfaz web de chat |
| cb-postgres | supabase/postgres:15.6.1 | 5432 | PostgreSQL + pgvector (768 dims) |
| cb-redis | redis:7-alpine | 6379 | Working memory (24h TTL) + metricas hot |
| cb-embeddings | ghcr.io/huggingface/tgi | 8080 | nomic-embed-text-v1.5 (768 dims, local, $0) |
| cb-snekbox | ghcr.io/python-discord/snekbox | — | Sandbox Python (nsjail, aislado) |
| cb-sandbox | Build ./sandbox | — | Sandbox Docker generico para code execution |
| cb-jupyter | Build ./jupyter | 8888 | IPython kernel con estado persistente |
| cb-n8n | n8n | 5678 | Workflow automation |
| cb-telegram | Build ./telegram | — | Bot Telegram como interfaz conversacional |
| cb-nginx | nginx | 80/443 | Reverse proxy + SSL termination |

## Modelo de Coste: $0 API

```
┌─────────────────────────────────────────────────────┐
│  CRITICO: NO usar ANTHROPIC_API_KEY                  │
│                                                      │
│  CLAUDE_CREDENTIALS_JSON = OAuth credentials         │
│  → claude CLI usa Max OAuth (incluido en suscripcion)│
│  → Sin ANTHROPIC_API_KEY → subprocess NO factura API │
│                                                      │
│  Coste mensual:                                      │
│  · Claude Max subscription: ~€200/mo                 │
│  · VPS (4 vCPU, 16GB RAM): €20-60/mo               │
│  · API extra: €0                                     │
│  · Embeddings: €0 (modelo local nomic)              │
└─────────────────────────────────────────────────────┘
```

## Stack Tecnico

| Componente | Tecnologia | Puerto |
|-----------|-----------|--------|
| CLAUDE-BRAIN API | FastAPI + Python 3.12 | 8000 |
| Redis | Redis 7 Alpine | 6379 |
| PostgreSQL | Supabase 15 + pgvector | 5432 |
| Embeddings | nomic-embed-text-v1.5 (local) | 8080 |
| Sandboxes | snekbox + Docker | — |
| Web UI | LibreChat | 3080 |
| n8n | Workflow engine | 5678 |
| Telegram | Bot interface | — |
| Jupyter | IPython kernel | 8888 |

## Implementacion Paso a Paso

### Paso 1: Variables de Entorno

```bash
# Credenciales Claude Max OAuth
CLAUDE_CREDENTIALS_JSON={"type":"oauth","..."}  # Exportar desde ~/.claude/.credentials.json

# Supabase
SUPABASE_URL=http://supabase-kong:8000
SUPABASE_SERVICE_KEY=eyJ...
POSTGRES_PASSWORD=<generado>

# Redis
REDIS_PASSWORD=<generado>

# Telegram (opcional)
TELEGRAM_BOT_TOKEN=<token>
TELEGRAM_ALLOWED_IDS=<user_id>

# n8n
N8N_USER=admin
N8N_PASSWORD=<segura>
```
