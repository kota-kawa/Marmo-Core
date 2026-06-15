---
name: persistent-memory-7layer
description: >
  Sistema de memoria persistente de 7 capas (MEMU) para agentes de IA.
  Implementa L1 working memory (Redis 1h), L2 short-term (Redis 24h),
  L3 episodic (Supabase), L4 semantic (pgvector embeddings), L5 procedural
  (protocolos/SOPs), L6 long-term facts (Supabase), L7 meta-memory (calibracion).
  Incluye consolidacion nocturna automatica L2->L3->L6, busqueda semantica
  por similitud coseno, inyeccion de calendario, y watcher transversal.
  Basado en NEMOCLAW-AGENT (TypeScript + Express + Supabase + Redis + Qdrant).
  Usar cuando el usuario mencione: memoria persistente, agente con memoria,
  recordar entre sesiones, sistema de memoria, 7 capas, MEMU, consolidacion
  de memoria, busqueda semantica de conversaciones, contexto persistente,
  knowledge base para agente, RAG para agente, embeddings de conversaciones.
metadata:
  version: "1.0.0"
  source_repo: "https://github.com/semaes111/NEMOCLAW-AGENT"
  category: agent-infrastructure
triggers:
  - "memoria persistente"
  - "agente con memoria"
  - "sistema de memoria"
  - "7 capas"
  - "MEMU"
  - "recordar entre sesiones"
---

# MEMU: Sistema de Memoria Persistente de 7 Capas

## Arquitectura General

MEMU (Memory Management Unit) es un orquestador de memoria para agentes de IA que implementa 7 capas con diferentes backends, TTLs y propositos. El principio de diseno es que **la memoria del agente debe funcionar como la memoria humana**: working memory volatil para la tarea actual, memoria episodica para conversaciones pasadas, memoria semantica para busqueda por significado, y memoria a largo plazo para hechos consolidados.

```
                    ┌─────────────────────────────────────────┐
                    │            MEMU API (:5000)              │
                    │         Express + TypeScript              │
                    └─────────┬───────────────┬───────────────┘
                              │               │
                    ┌─────────▼─────┐  ┌──────▼──────────────┐
                    │  Redis (:6379) │  │  Supabase (pgvector) │
                    │  L1 + L2       │  │  L3 + L4 + L5 + L6  │
                    │  (volatil)     │  │  + L7 (persistente)  │
                    └───────────────┘  └──────────────────────┘
```

## Las 7 Capas

| Capa | Nombre | Backend | TTL | Proposito |
|------|--------|---------|-----|-----------|
| L1 | Working Memory | Redis | 1h | Contexto de sesion activa (tarea actual, archivos abiertos) |
| L2 | Short-Term | Redis | 24h | Interacciones recientes del dia (max 200 entradas) |
| L3 | Episodic | Supabase | Permanente | Historial completo de conversaciones por sesion |
| L4 | Semantic | Supabase pgvector | Permanente | Embeddings para busqueda por similitud coseno |
| L5 | Procedural | Supabase | Permanente | Protocolos/SOPs con triggers y pasos ejecutables |
| L6 | Long-Term Facts | Supabase | Configurable | Hechos clave extraidos: preferencias, entidades, conocimiento |
| L7 | Meta-Memory | Supabase | Permanente | Configuracion y metricas del sistema de memoria |

## Implementacion Paso a Paso

### Paso 1: Schema de Base de Datos

Ejecutar la migracion completa. Ver `references/memu-schema.sql` para el SQL completo.

Tablas creadas:
- `memu_episodes` — L3: historial con session_id, agent_id, role, content, tokens
- `memu_semantic` — L4: embeddings VECTOR(1024) con indice HNSW (m=16, ef=64)
- `memu_protocols` — L5: SOPs con trigger_event, trigger_cron, steps JSONB
- `memu_facts` — L6: key/value con category, confidence, expires_at
- `memu_meta` — L7: config y stats del sistema como JSONB
- `agent_calendar_events` — agenda con protocolo asociado
- `agent_tasks` — cola de tareas con prioridad y estado
- `watcher_events` — logs del monitor con severidad

## Patrones Clave

### buildAgentContext() — El Corazon de MEMU

Cuando se guarda un episodio, se indexa en DOS capas simultaneamente:
- L3 (Supabase): para consulta por session_id (historial lineal)
- L4 (pgvector): para busqueda semantica (embeddings)

## Nota sobre Sistemas Complementarios

Este skill documenta MEMU (TypeScript + Express), el sistema de memoria de 7 capas para NEMOCLAW-AGENT. Es **independiente** del sistema de memoria de 3 capas de CLAUDE-BRAIN (Python + FastAPI, documentado en `docker-agent-orchestration`). Ambos usan pgvector pero con dimensiones diferentes:

- **MEMU**: NVIDIA llama-3.2-nv-embedqa-1b-v2 → VECTOR(**1024**) dims
- **CLAUDE-BRAIN**: nomic-embed-text-v1.5 → VECTOR(**768**) dims

NO son intercambiables. Elige uno segun tu stack (TypeScript vs Python).
