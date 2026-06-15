-- ============================================================
-- MEMU 7-Layer Memory Schema for Supabase
-- NextHorizont AI · NemoClaw Stack
-- Migration: 20260317000000_memu_complete_schema.sql
-- ============================================================

-- Habilitar extensión de vectores para L4 (Semantic Memory)
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS pg_net;  -- para webhooks HTTP async

-- ============================================================
-- L3: EPISODIC MEMORY — historial de conversaciones
-- ============================================================
CREATE TABLE IF NOT EXISTS memu_episodes (
  id            UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  session_id    TEXT NOT NULL,
  agent_id      TEXT NOT NULL DEFAULT 'openclaw',
  role          TEXT NOT NULL CHECK (role IN ('user', 'assistant', 'system', 'tool')),
  content       TEXT NOT NULL,
  tokens        INTEGER,
  metadata      JSONB DEFAULT '{}',
  -- Promoted indica si ya fue consolidado a L6
  promoted_to_l6 BOOLEAN DEFAULT FALSE,
  created_at    TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX idx_episodes_session ON memu_episodes(session_id);
CREATE INDEX idx_episodes_agent ON memu_episodes(agent_id);
CREATE INDEX idx_episodes_created ON memu_episodes(created_at DESC);
CREATE INDEX idx_episodes_promoted ON memu_episodes(promoted_to_l6) WHERE NOT promoted_to_l6;

-- ============================================================
-- L4: SEMANTIC MEMORY — embeddings vectoriales
-- ============================================================
CREATE TABLE IF NOT EXISTS memu_semantic (
  id            UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  agent_id      TEXT NOT NULL DEFAULT 'openclaw',
  content       TEXT NOT NULL,
  embedding     VECTOR(1024),          -- dim para nv-embedqa-1b-v2
  source_type   TEXT NOT NULL,         -- 'episode' | 'fact' | 'protocol' | 'document'
  source_id     UUID,
  tags          TEXT[] DEFAULT '{}',
  metadata      JSONB DEFAULT '{}',
  created_at    TIMESTAMPTZ DEFAULT NOW()
);
-- Índice HNSW para búsqueda ANN eficiente
CREATE INDEX idx_semantic_embedding ON memu_semantic
  USING hnsw (embedding vector_cosine_ops)
  WITH (m = 16, ef_construction = 64);
CREATE INDEX idx_semantic_agent ON memu_semantic(agent_id);
CREATE INDEX idx_semantic_tags ON memu_semantic USING gin(tags);

-- ============================================================
-- L5: PROCEDURAL MEMORY — protocolos y SOPs
-- ============================================================
CREATE TABLE IF NOT EXISTS memu_protocols (
  id            UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  agent_id      TEXT NOT NULL DEFAULT 'openclaw',
  name          TEXT NOT NULL,
  slug          TEXT NOT NULL,
  description   TEXT,
  category      TEXT NOT NULL,         -- 'medical' | 'business' | 'carbon' | 'admin'
  trigger_event TEXT,                  -- evento que activa este protocolo
  trigger_cron  TEXT,                  -- cron expression si es periódico
  steps         JSONB NOT NULL DEFAULT '[]',  -- array de pasos
  is_active     BOOLEAN DEFAULT TRUE,
  priority      INTEGER DEFAULT 5,     -- 1 (máximo) - 10 (mínimo)
  metadata      JSONB DEFAULT '{}',
  created_at    TIMESTAMPTZ DEFAULT NOW(),
  updated_at    TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE(agent_id, slug)
);
CREATE INDEX idx_protocols_category ON memu_protocols(category);
CREATE INDEX idx_protocols_active ON memu_protocols(is_active) WHERE is_active;
CREATE INDEX idx_protocols_trigger ON memu_protocols(trigger_event) WHERE trigger_event IS NOT NULL;

-- ============================================================
-- L6: LONG-TERM MEMORY — hechos permanentes
-- ============================================================
CREATE TABLE IF NOT EXISTS memu_facts (
  id            UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  agent_id      TEXT NOT NULL DEFAULT 'openclaw',
  key           TEXT NOT NULL,         -- clave única del hecho
  value         TEXT NOT NULL,         -- valor del hecho
  category      TEXT NOT NULL,         -- 'preference' | 'knowledge' | 'entity' | 'context'
  confidence    FLOAT DEFAULT 1.0 CHECK (confidence BETWEEN 0 AND 1),
  source        TEXT,                  -- de dónde viene este hecho
  source_episode_id UUID REFERENCES memu_episodes(id) ON DELETE SET NULL,
  expires_at    TIMESTAMPTZ,           -- NULL = permanente
  metadata      JSONB DEFAULT '{}',
  created_at    TIMESTAMPTZ DEFAULT NOW(),
  updated_at    TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE(agent_id, key)
);
CREATE INDEX idx_facts_agent_category ON memu_facts(agent_id, category);
CREATE INDEX idx_facts_key ON memu_facts(agent_id, key);
CREATE INDEX idx_facts_expires ON memu_facts(expires_at) WHERE expires_at IS NOT NULL;

-- ============================================================
-- L7: META-MEMORY — calibración del sistema de memoria
-- ============================================================
CREATE TABLE IF NOT EXISTS memu_meta (
  id            UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  agent_id      TEXT NOT NULL DEFAULT 'openclaw',
  key           TEXT NOT NULL,         -- 'consolidation_state' | 'performance_metrics' | etc.
  value         JSONB NOT NULL DEFAULT '{}',
  updated_at    TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE(agent_id, key)
);

-- ============================================================
-- AGENDA / CALENDAR — control de citas y eventos
-- ============================================================
CREATE TABLE IF NOT EXISTS agent_calendar_events (
  id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  agent_id        TEXT NOT NULL DEFAULT 'openclaw',
  external_id     TEXT,                -- Google Calendar event ID
  title           TEXT NOT NULL,
  description     TEXT,
  start_at        TIMESTAMPTZ NOT NULL,
  end_at          TIMESTAMPTZ NOT NULL,
  location        TEXT,
  event_type      TEXT DEFAULT 'general',  -- 'meeting' | 'protocol' | 'reminder' | 'deadline'
  protocol_slug   TEXT REFERENCES memu_protocols(slug) ON DELETE SET NULL,
  attendees       JSONB DEFAULT '[]',
  status          TEXT DEFAULT 'scheduled',  -- 'scheduled' | 'active' | 'done' | 'cancelled'
  injected_to_agent BOOLEAN DEFAULT FALSE,
  metadata        JSONB DEFAULT '{}',
  created_at      TIMESTAMPTZ DEFAULT NOW(),
  updated_at      TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX idx_calendar_start ON agent_calendar_events(start_at);
CREATE INDEX idx_calendar_agent ON agent_calendar_events(agent_id);
CREATE INDEX idx_calendar_type ON agent_calendar_events(event_type);
CREATE INDEX idx_calendar_status ON agent_calendar_events(status);

-- ============================================================
-- TASK QUEUE — tareas generadas por el agente o protocolos
-- ============================================================
CREATE TABLE IF NOT EXISTS agent_tasks (
  id            UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  agent_id      TEXT NOT NULL DEFAULT 'openclaw',
  title         TEXT NOT NULL,
  description   TEXT,
  task_type     TEXT NOT NULL,         -- 'action' | 'reminder' | 'analysis' | 'report'
  status        TEXT DEFAULT 'pending',-- 'pending' | 'running' | 'done' | 'failed'
  priority      INTEGER DEFAULT 5,
  protocol_id   UUID REFERENCES memu_protocols(id) ON DELETE SET NULL,
  episode_id    UUID REFERENCES memu_episodes(id) ON DELETE SET NULL,
  result        JSONB,
  error         TEXT,
  scheduled_at  TIMESTAMPTZ,
  started_at    TIMESTAMPTZ,
  completed_at  TIMESTAMPTZ,
  metadata      JSONB DEFAULT '{}',
  created_at    TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX idx_tasks_status ON agent_tasks(status, priority);
CREATE INDEX idx_tasks_scheduled ON agent_tasks(scheduled_at) WHERE status = 'pending';

-- ============================================================
-- WATCHER EVENTS — logs del monitor transversal
-- ============================================================
CREATE TABLE IF NOT EXISTS watcher_events (
  id            UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  service       TEXT NOT NULL,         -- nombre del contenedor
  event_type    TEXT NOT NULL,         -- 'health_check' | 'alert' | 'restart' | 'metric'
  severity      TEXT DEFAULT 'info',   -- 'info' | 'warning' | 'critical'
  message       TEXT NOT NULL,
  details       JSONB DEFAULT '{}',
  resolved      BOOLEAN DEFAULT FALSE,
  resolved_at   TIMESTAMPTZ,
  created_at    TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX idx_watcher_service ON watcher_events(service, created_at DESC);
CREATE INDEX idx_watcher_severity ON watcher_events(severity) WHERE NOT resolved;
CREATE INDEX idx_watcher_created ON watcher_events(created_at DESC);

-- ============================================================
-- FUNCIONES HELPER
-- ============================================================

-- Búsqueda semántica por similitud coseno
CREATE OR REPLACE FUNCTION memu_search_semantic(
  query_embedding VECTOR(1024),
  match_threshold FLOAT DEFAULT 0.7,
  match_count     INTEGER DEFAULT 5,
  p_agent_id      TEXT DEFAULT 'openclaw'
)
RETURNS TABLE (
  id UUID,
  content TEXT,
  source_type TEXT,
  similarity FLOAT,
  metadata JSONB
)
LANGUAGE plpgsql
AS $$
BEGIN
  RETURN QUERY
  SELECT
    s.id,
    s.content,
    s.source_type,
    1 - (s.embedding <=> query_embedding) AS similarity,
    s.metadata
  FROM memu_semantic s
  WHERE
    s.agent_id = p_agent_id
    AND 1 - (s.embedding <=> query_embedding) > match_threshold
  ORDER BY s.embedding <=> query_embedding
  LIMIT match_count;
END;
$$;

-- Notificar a n8n via pg_net cuando se crea un episodio importante
CREATE OR REPLACE FUNCTION notify_n8n_on_episode()
RETURNS TRIGGER
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
  payload JSONB;
  n8n_url TEXT;
BEGIN
  -- Solo notificar si el episodio tiene contenido sustancial (>200 chars)
  IF LENGTH(NEW.content) > 200 AND NEW.role = 'assistant' THEN
    payload := jsonb_build_object(
      'event', 'new_episode',
      'episode_id', NEW.id,
      'session_id', NEW.session_id,
      'agent_id', NEW.agent_id,
      'tokens', NEW.tokens,
      'timestamp', NOW()
    );

    SELECT value->>'n8n_webhook_url'
    INTO n8n_url
    FROM memu_meta
    WHERE agent_id = NEW.agent_id AND key = 'config';

    IF n8n_url IS NOT NULL THEN
      PERFORM net.http_post(
        url := n8n_url,
        body := payload::TEXT,
        headers := '{"Content-Type": "application/json"}'::JSONB
      );
    END IF;
  END IF;
  RETURN NEW;
END;
$$;

CREATE TRIGGER trg_notify_episode
  AFTER INSERT ON memu_episodes
  FOR EACH ROW EXECUTE FUNCTION notify_n8n_on_episode();

-- Auto-update updated_at
CREATE OR REPLACE FUNCTION set_updated_at()
RETURNS TRIGGER LANGUAGE plpgsql AS $$
BEGIN
  NEW.updated_at = NOW();
  RETURN NEW;
END;
$$;

CREATE TRIGGER trg_facts_updated_at
  BEFORE UPDATE ON memu_facts
  FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE TRIGGER trg_protocols_updated_at
  BEFORE UPDATE ON memu_protocols
  FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE TRIGGER trg_calendar_updated_at
  BEFORE UPDATE ON agent_calendar_events
  FOR EACH ROW EXECUTE FUNCTION set_updated_at();

-- ============================================================
-- SEED: Protocolos base para NextHorizont AI
-- ============================================================
INSERT INTO memu_protocols (name, slug, category, description, trigger_event, priority, steps) VALUES

('Briefing matutino', 'morning-briefing', 'admin',
 'Resumen diario de agenda, tareas pendientes y contexto relevante',
 'schedule:daily:08:00', 1,
 '[
   {"step": 1, "action": "fetch_calendar_events", "params": {"days_ahead": 1}},
   {"step": 2, "action": "fetch_pending_tasks", "params": {"priority_lte": 3}},
   {"step": 3, "action": "query_l6_facts", "params": {"category": "context"}},
   {"step": 4, "action": "generate_briefing", "params": {"format": "markdown"}},
   {"step": 5, "action": "inject_to_agent_context", "params": {}}
 ]'::JSONB),

('Reunion detectada', 'meeting-prep', 'admin',
 'Preparar contexto antes de una reunión importante',
 'calendar:meeting:30min_before', 2,
 '[
   {"step": 1, "action": "fetch_event_details", "params": {}},
   {"step": 2, "action": "search_semantic_memory", "params": {"query": "{{event.title}} {{event.attendees}}"}},
   {"step": 3, "action": "fetch_related_facts", "params": {}},
   {"step": 4, "action": "generate_meeting_brief", "params": {}},
   {"step": 5, "action": "inject_to_agent_context", "params": {}}
 ]'::JSONB),

('Consolidacion memoria nocturna', 'nightly-consolidation', 'admin',
 'Promueve L2->L3 y resume L3->L6 episodios del día',
 'schedule:daily:02:00', 1,
 '[
   {"step": 1, "action": "flush_redis_l2_to_supabase_l3", "params": {"batch_size": 100}},
   {"step": 2, "action": "summarize_episodes_to_facts", "params": {"min_importance": 0.6}},
   {"step": 3, "action": "embed_new_facts_to_l4", "params": {}},
   {"step": 4, "action": "update_meta_stats", "params": {}},
   {"step": 5, "action": "prune_old_l3_episodes", "params": {"older_than_days": 30}}
 ]'::JSONB),

('Alerta critica sistema', 'critical-alert', 'admin',
 'Respuesta ante fallo crítico de un servicio del stack',
 'watcher:critical', 1,
 '[
   {"step": 1, "action": "log_event_to_supabase", "params": {}},
   {"step": 2, "action": "attempt_service_restart", "params": {"max_attempts": 3}},
   {"step": 3, "action": "notify_telegram", "params": {}},
   {"step": 4, "action": "update_agent_context_with_status", "params": {}}
 ]'::JSONB)

ON CONFLICT (agent_id, slug) DO NOTHING;

-- Seed meta config inicial
INSERT INTO memu_meta (agent_id, key, value) VALUES
('openclaw', 'config', '{
  "memory_layers_enabled": [1, 2, 3, 4, 5, 6, 7],
  "auto_consolidation": true,
  "max_context_tokens": 8000,
  "semantic_search_threshold": 0.72,
  "semantic_search_top_k": 5
}'),
('openclaw', 'stats', '{
  "total_episodes": 0,
  "total_facts": 0,
  "total_embeddings": 0,
  "last_consolidation": null
}')
ON CONFLICT (agent_id, key) DO NOTHING;

-- ============================================================
-- ROW LEVEL SECURITY
-- ============================================================
ALTER TABLE memu_episodes ENABLE ROW LEVEL SECURITY;
ALTER TABLE memu_semantic ENABLE ROW LEVEL SECURITY;
ALTER TABLE memu_protocols ENABLE ROW LEVEL SECURITY;
ALTER TABLE memu_facts ENABLE ROW LEVEL SECURITY;
ALTER TABLE memu_meta ENABLE ROW LEVEL SECURITY;
ALTER TABLE agent_calendar_events ENABLE ROW LEVEL SECURITY;
ALTER TABLE agent_tasks ENABLE ROW LEVEL SECURITY;
ALTER TABLE watcher_events ENABLE ROW LEVEL SECURITY;

-- Service role (backend) tiene acceso total
CREATE POLICY "service_role_all" ON memu_episodes FOR ALL TO service_role USING (TRUE);
CREATE POLICY "service_role_all" ON memu_semantic FOR ALL TO service_role USING (TRUE);
CREATE POLICY "service_role_all" ON memu_protocols FOR ALL TO service_role USING (TRUE);
CREATE POLICY "service_role_all" ON memu_facts FOR ALL TO service_role USING (TRUE);
CREATE POLICY "service_role_all" ON memu_meta FOR ALL TO service_role USING (TRUE);
CREATE POLICY "service_role_all" ON agent_calendar_events FOR ALL TO service_role USING (TRUE);
CREATE POLICY "service_role_all" ON agent_tasks FOR ALL TO service_role USING (TRUE);
CREATE POLICY "service_role_all" ON watcher_events FOR ALL TO service_role USING (TRUE);
