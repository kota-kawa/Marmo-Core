---
name: optimizacion-consumo-tokens-openclaw
description: Diagnóstico y resolución de consumo elevado de tokens/credits en bots OpenClaw/ClawdBot (Mimo, Anthropic, OpenAI). Aplica los 4 vectores de coste — contexto inerte, estado acumulado, frecuencia y consumo externo. Activar cuando el usuario reporte un incidente de consumo, sangrado de credits, plan agotándose rápido, factura disparada, "el bot está costando demasiado", consumo desproporcionado, tokens elevados por turno, sesiones bloated, o cualquier discrepancia entre auditoría interna y facturación del proveedor LLM.
version: 1.0
created: 2026-05-06
based_on: Incidente NextHorizont AI 6-may-2026 (sangrado 1.82M cred/min → 0)
---

# Optimización de consumo de tokens en bots OpenClaw

## 🎯 Cuándo usar esta skill

Activar cuando el usuario reporte cualquiera de estos síntomas:

- "El plan Mimo/Anthropic se está agotando muy rápido"
- "Veo un sangrado de credits"
- "La factura del LLM está disparada"
- "Cada turno cuesta más de lo esperado"
- "Las sesiones están bloated/infladas"
- "La auditoría reporta consumo elevado"
- Discrepancia entre métricas internas y facturación del proveedor

## 🧠 Principio fundamental

```
EL COSTE/TURNO EN UN BOT LLM ES SUMA DE 4 VECTORES INDEPENDIENTES.
ATACAR UNO DEJA LOS OTROS 3 LATENTES, ESPERANDO PARA DETONAR.
```

| Vector | Qué es | Síntoma |
|--------|--------|---------|
| **1. Contexto inerte** | Skills auto-cargadas + system prompt + manifests | Cada turno cuesta lo mismo aunque no haya historia |
| **2. Estado acumulado** | sesión `.jsonl` + workspace + memoria persistente | Coste/turno crece linealmente con el tiempo |
| **3. Frecuencia** | Heartbeats, crons LLM-triggered, predictions | Consumo aunque nadie hable con el bot |
| **4. Consumo externo** | API key reusada en otros sistemas (backups, .env, etc.) | Discrepancia entre audit interno y facturación |

## 📋 Protocolo de diagnóstico (4 vectores)

Ejecutar **EN ORDEN**. No saltarse ninguno.

### Vector 1 — ¿Cuántas skills se inyectan en cada turno?

```bash
# Para cada bot, contar skills en disco y verificar config
for BOT in moltbot-gateway moltbot-container-bot2 moltbot-gateway-viocon; do
  echo "━━━ $BOT ━━━"
  TOTAL=$(docker exec "$BOT" sh -c "ls /home/node/clawd/.claude/skills/user/ 2>/dev/null | wc -l")
  echo "  Skills en disco: $TOTAL"

  ALLOWLIST=$(docker exec "$BOT" sh -c "
    cat /home/node/.clawdbot/clawdbot.json | python3 -c '
import sys, json
c = json.load(sys.stdin)
sk = c.get(\"agents\", {}).get(\"defaults\", {}).get(\"skills\")
if sk is None: print(\"NO definido (default=cargar TODAS)\")
elif isinstance(sk, list): print(f\"Allowlist: {len(sk)} skills permitidas\")
else: print(f\"Tipo inesperado: {type(sk).__name__}\")
' 2>/dev/null
  ")
  echo "  Config: $ALLOWLIST"
done
```

**INTERPRETACIÓN:**
- Si Skills en disco > 10 y allowlist NO definida → **VECTOR 1 ACTIVO**
- Cada skill no listada = ~8-28 KB inyectados por turno
- 60 skills = ~900 KB tokens contexto base por turno

### Vector 2 — ¿Hay sesiones JSONL bloated?

```bash
for BOT in moltbot-gateway moltbot-container-bot2 moltbot-gateway-viocon; do
  echo "━━━ $BOT ━━━"
  docker exec "$BOT" sh -c "
    find /home/node/.openclaw/agents/main/sessions/ -name '*.jsonl' -not -name '*.bak*' -not -name '*.archived*' -not -name '*.deleted*' 2>/dev/null \
    | xargs -I{} stat -c '%s %n' {} 2>/dev/null \
    | sort -rn | head -3 \
    | awk '{ printf \"  %d KB  %s\\n\", \$1/1024, \$2 }'
  "
done
```

**INTERPRETACIÓN:**
- Sesión > 50 KB → **VECTOR 2 ACTIVO**
- Sesión > 500 KB → CRÍTICO, archivar inmediatamente
- Cada KB de sesión = 1K tokens de input por turno

### Vector 3 — ¿Heartbeats/crons disparando turnos?

```bash
for BOT in moltbot-gateway moltbot-container-bot2 moltbot-gateway-viocon; do
  echo "━━━ $BOT ━━━"

  # Heartbeat config
  docker exec "$BOT" sh -c "
    cat /home/node/.clawdbot/clawdbot.json | python3 -c '
import sys, json
c = json.load(sys.stdin)
hb = c.get(\"agents\", {}).get(\"defaults\", {}).get(\"heartbeat\", {})
print(f\"  heartbeat.every: {hb.get(\\\"every\\\", \\\"NO definido\\\")}\")
print(f\"  compaction: {c.get(\\\"agents\\\", {}).get(\\\"defaults\\\", {}).get(\\\"compaction\\\", {}).get(\\\"mode\\\", \\\"NO definido\\\")}\")
'
  "

  # HEARTBEAT.md activo
  for HB_PATH in /home/node/.openclaw/workspace/HEARTBEAT.md /home/node/clawd/HEARTBEAT.md; do
    if docker exec "$BOT" test -f "$HB_PATH" 2>/dev/null; then
      LINES=$(docker exec "$BOT" sh -c "grep -v '^#' '$HB_PATH' 2>/dev/null | grep -v '^$' | wc -l")
      echo "  $HB_PATH: $LINES líneas activas"
    fi
  done
done
```

**INTERPRETACIÓN:**
- `heartbeat.every` < 720m → demasiado frecuente
- `compaction.mode` ≠ "safeguard" → sesiones crecerán sin techo
- HEARTBEAT.md con líneas activas (no comentarios) → genera turnos automáticos

### Vector 4 — ¿Discrepancia entre audit interno y facturación externa?

```sql
-- Audit interno últimas 24h
SELECT bot_name, agent_id,
       SUM(turns_in_window) AS total_turns,
       SUM(tokens_estimated_window) AS total_tokens
FROM bot_audit_log
WHERE collected_at > NOW() - INTERVAL '24 hours'
GROUP BY bot_name, agent_id;
```

Comparar con dashboard del proveedor (Mimo en `xiaomimimo.com`, Anthropic console, etc.).

**INTERPRETACIÓN:**
- Si `facturación_proveedor / audit_interno > 5` → **VECTOR 4 ACTIVO** (consumo externo)
- Si tcpdump al endpoint del proveedor reporta 0 paquetes pero hay facturación → CONFIRMADO consumo externo

## 🛠 Acciones por vector

### Acción Vector 1 — `skills: []` allowlist

```bash
BOT="moltbot-gateway-viocon"  # cambiar según bot

# Backup
TS=$(date +%s)
docker exec "$BOT" cp /home/node/.clawdbot/clawdbot.json /home/node/.clawdbot/clawdbot.json.bak.$TS

# Configurar allowlist vacía (ninguna skill auto-cargada)
docker exec "$BOT" node -e "
  const fs = require('fs');
  const path = '/home/node/.clawdbot/clawdbot.json';
  const config = JSON.parse(fs.readFileSync(path, 'utf8'));
  config.agents = config.agents || {};
  config.agents.defaults = config.agents.defaults || {};
  config.agents.defaults.skills = [];   // ← Array vacío = ninguna inyección automática
  delete config.skills;                  // ← Eliminar config legacy si existía
  fs.writeFileSync(path, JSON.stringify(config, null, 2));
  console.log('✓ skills: [] aplicado');
"

# Reiniciar
docker restart "$BOT"
sleep 30

# Verificar arranque sin errores
docker logs --since 30s "$BOT" 2>&1 | grep -iE "config invalid|unrecognized|invalid input" \
  || echo "✓ Sin errores de config"
```

**SI EN EL FUTURO necesitas una skill específica:**
```bash
# Editar el array para añadirla
docker exec "$BOT" node -e "
  const fs = require('fs');
  const c = JSON.parse(fs.readFileSync('/home/node/.clawdbot/clawdbot.json', 'utf8'));
  c.agents.defaults.skills.push('clinic-pdf');  // ← nombre de skill a habilitar
  fs.writeFileSync('/home/node/.clawdbot/clawdbot.json', JSON.stringify(c, null, 2));
"
docker restart "$BOT"
```

### Acción Vector 2 — archivar sesión bloated

```bash
BOT="moltbot-gateway-viocon"
TS=$(date +%s)

# 1. Identificar sesión más grande
LARGEST=$(docker exec "$BOT" sh -c "
  find /home/node/.openclaw/agents/main/sessions/ -name '*.jsonl' \
    -not -name '*.bak*' -not -name '*.archived*' -not -name '*.deleted*' 2>/dev/null \
  | xargs -I{} stat -c '%s %n' {} 2>/dev/null \
  | sort -rn | head -1 | awk '{print \$2}'
")
echo "Sesión a archivar: $LARGEST"

# 2. Backup en HOST (CRÍTICO — no solo dentro del container)
BAK_NAME="/root/${BOT}-session-archive-$TS.jsonl"
docker cp "${BOT}:${LARGEST}" "$BAK_NAME"
ls -la "$BAK_NAME"

# 3. Archivar (rename, no borrar) dentro del container
docker exec "$BOT" mv "$LARGEST" "${LARGEST}.archived-$TS"

# 4. Reiniciar para generar sesión limpia
docker restart "$BOT"
sleep 30

# 5. Verificar sesiones nuevas pequeñas
docker exec "$BOT" sh -c "
  ls -la /home/node/.openclaw/agents/main/sessions/*.jsonl 2>/dev/null \
  | grep -v archived | grep -v bak | grep -v deleted \
  | awk '{print \$5/1024 \" KB  \" \$9}'
"
```

### Acción Vector 3 — vaciar HEARTBEAT.md y configurar safeguard

```bash
BOT="moltbot-gateway-viocon"

# 3.1 — Vaciar HEARTBEAT.md (NO mover, solo vaciar a comentarios)
# OpenClaw regenera el archivo si lo movemos. Vaciarlo sí funciona.
for HB in /home/node/.openclaw/workspace/HEARTBEAT.md /home/node/clawd/HEARTBEAT.md; do
  if docker exec "$BOT" test -f "$HB" 2>/dev/null; then
    docker exec "$BOT" sh -c "echo '# Keep this file empty (or with only comments) to skip heartbeat API calls.' > $HB"
    echo "✓ Vaciado: $HB"
  fi
done

# 3.2 — Configurar heartbeat largo + compaction safeguard
docker exec "$BOT" node -e "
  const fs = require('fs');
  const c = JSON.parse(fs.readFileSync('/home/node/.clawdbot/clawdbot.json', 'utf8'));
  c.agents = c.agents || {};
  c.agents.defaults = c.agents.defaults || {};
  c.agents.defaults.heartbeat = {
    every: '720m',
    activeHours: { start: '08:00', end: '23:59', timezone: 'Europe/Madrid' }
  };
  c.agents.defaults.compaction = { mode: 'safeguard' };
  fs.writeFileSync('/home/node/.clawdbot/clawdbot.json', JSON.stringify(c, null, 2));
  console.log('✓ heartbeat 720m + compaction safeguard');
"

docker restart "$BOT"
```

**IMPORTANTE — `compaction.mode=safeguard` NO ES RETROACTIVO:**
Solo previene crecimiento de sesiones nuevas. Sesiones ya bloated requieren la
acción del Vector 2 (archivar manualmente).

### Acción Vector 4 — rotar API key

```bash
# 4.1 — Buscar la key en TODOS los sistemas del VPS
KEY="tp-..."  # primeros chars de la key sospechosa

echo "━━━ Apariciones de la key en VPS ━━━"
grep -r "$KEY" /etc/dokploy/compose/ 2>/dev/null
grep -r "$KEY" /root/ 2>/dev/null | grep -v "_history\|.archive"
grep -r "$KEY" /tmp/ 2>/dev/null
docker exec -i postgres psql -U usr -d db -c "SELECT id FROM backups WHERE data LIKE '%$KEY%';" 2>/dev/null

echo "━━━ tcpdump 60s al endpoint del proveedor ━━━"
# Si hay 0 paquetes pero el dashboard del proveedor sigue facturando =
# CONFIRMADO consumo externo
PROVIDER_IP="20.157.221.14"  # IP del proveedor LLM (Mimo en este caso)
timeout 60 tcpdump -ni any "host $PROVIDER_IP" 2>/dev/null | wc -l

# 4.2 — Rotar key en dashboard del proveedor (acción manual)
# Generar nueva key, anotar
NEW_KEY="tp-NEW..."

# 4.3 — Actualizar TODOS los containers que la usan
for BOT in moltbot-gateway moltbot-container-bot2 moltbot-gateway-viocon; do
  TS=$(date +%s)
  docker exec "$BOT" cp /home/node/.clawdbot/clawdbot.json /home/node/.clawdbot/clawdbot.json.bak.$TS

  docker exec "$BOT" node -e "
    const fs = require('fs');
    const path = '/home/node/.clawdbot/clawdbot.json';
    let c = JSON.parse(fs.readFileSync(path, 'utf8'));
    // Reemplazo de TODAS las apariciones (env + provider config)
    const json = JSON.stringify(c);
    const updated = json.replace(/$KEY/g, '$NEW_KEY');
    fs.writeFileSync(path, JSON.stringify(JSON.parse(updated), null, 2));
    console.log('✓ Key actualizada en $BOT');
  "
  docker restart "$BOT"
done

# 4.4 — Neutralizar containers externos sospechosos
# Ejemplo: container "miro-fish" que tenía la key en su .env
docker exec miro-fish-container sh -c "
  sed -i 's/^LLM_BOOST_API_KEY=.*/LLM_BOOST_API_KEY=DISABLED_BLEED_PROTECTION/' /app/.env
"
docker restart miro-fish-container
```

## 📊 Casos reales — incidentes documentados

### Incidente 2 mayo 2026 — fix parcial (vector 3 únicamente)

**Síntoma:** 1.6B tokens consumidos en 19 días por 3 bots

**Diagnóstico:**
- 6 memorias venenosas en Yuki ('Envía a Violeta por telegram') indexadas desde JSON de cron jobs
- HEARTBEAT.md disparando heartbeats sin freno

**Acción aplicada:**
- ✓ Memorias venenosas → importance 0.01
- ✓ HEARTBEAT.md → vaciado a comentarios
- ✓ heartbeat.every = 720m
- ✓ compaction.mode = safeguard

**Resultado medido:** 762K → 6K tokens/turn ★

**LO QUE QUEDÓ ACTIVO (no detectado entonces):**
- ✗ Vector 1: 60-145 skills se seguían inyectando en cada turno
- ✗ Vector 2: sesión Nova ff66a1be ya empezaba a inflarse de nuevo
- ✗ Vector 4: key Mimo presente en backups SQL paperclip

**LECCIÓN:** "Resuelto" era apariencia. 4 días después detonó otro incidente.

### Incidente 6 mayo 2026 — fix completo (los 4 vectores)

**Síntoma:** Sangrado de 1.82M cred/min, plan iba a morir en 10h

**Diagnóstico forense:**
- audit_interno: 60K tok/8h
- facturación Mimo: 64M cred/8h
- Discrepancia 533× → consumo externo confirmado
- tcpdump VPS→Mimo IPs (20.157.221.14, 20.47.115.50): **0 paquetes** en 60s
- Key encontrada en .env de MiroFish, backups SQL paperclip, bash_history

**Acciones aplicadas (los 4 vectores):**
- ✓ Vector 1: `agents.defaults.skills = []` en los 3 bots (Maui 60, Nova 145, Yuki 87 skills)
- ✓ Vector 2: sesión Maui 754 KB y Nova 126 KB archivadas con backup en host
- ✓ Vector 3: HEARTBEAT.md vacío + safeguard ya estaban activos del 2-may
- ✓ Vector 4: rotación key Mimo (tp-ec3q... → tp-ee9s...), MiroFish neutralizado

**Resultados medidos:**
- Saludo simple Maui: 931K → **24K credits** (-97%)
- Pregunta con investigación: 687K → **308K credits** (-67%)
- Sangrado externo: 1.82M/min → **0** (-98.29%)
- Plan: 10h de vida → **7-17 meses** según uso

## ⚠ Anti-patrones — qué NO hacer

| Anti-patrón | Por qué falla | Hacer en su lugar |
|-------------|---------------|-------------------|
| `agents.defaults.skills = {autoload: false, lazyLoad: true}` | OpenClaw 2026.4.15 rechaza con `Invalid input: expected array, received object` | `agents.defaults.skills = []` (array vacío) |
| Mover HEARTBEAT.md a otra carpeta | OpenClaw lo regenera con plantilla activa | Vaciar dejando solo comentarios |
| Confiar en `compaction.mode=safeguard` para sesiones existentes | Solo previene crecimiento de NUEVAS sesiones | Archivar manualmente sesiones bloated existentes |
| Borrar archivos sin backup | Sin recuperación posible | Backup en HOST (`docker cp`) ANTES de modificar |
| Suponer que `skills: {}` (vacío) significa "sin skills" | Significa "default = cargar todas" | Declarar explícitamente `skills: []` |
| Buscar bug en métricas cuando hay discrepancia interna/externa | El problema es un tercer actor con tus credenciales | Rotar key + auditar dónde aparece (.env, backups, history) |
| Aplicar fix parcial y declarar "resuelto" | Los otros 3 vectores siguen latentes | Verificar los 4 vectores SIEMPRE |

## ✅ Checklist post-fix

Después de aplicar acciones, validar:

```
VECTOR 1 — Skills
  □ docker exec $BOT cat /home/node/.clawdbot/clawdbot.json | jq '.agents.defaults.skills'
    → debe ser array (vacío o con allowlist explícita)
  □ docker logs --since 30s $BOT | grep -iE "config invalid"
    → debe estar VACÍO

VECTOR 2 — Sesiones
  □ Sesiones JSONL activas todas < 50 KB
  □ Backups archivados (.archived-TS) presentes en /root/

VECTOR 3 — Frecuencia
  □ heartbeat.every = "720m"
  □ compaction.mode = "safeguard"
  □ HEARTBEAT.md solo contiene comentarios

VECTOR 4 — Externo
  □ Key vieja revocada en dashboard del proveedor
  □ grep -r "KEY_VIEJA" /etc/ /root/ /tmp/ → vacío
  □ tcpdump endpoint provider 60s coincide con audit_interno

VALIDACIÓN END-TO-END
  □ Enviar mensaje real al bot, medir Δ del proveedor
  □ Δ < 100K credits/turno saludo simple → OK
  □ Δ < 500K credits/turno con investigación → OK
  □ Esperar 4h sin actividad, Δ = 0 → consumo externo eliminado
```

## 🔐 Backup strategy obligatoria

**ANTES de cualquier acción destructiva:**

```bash
TS=$(date +%s)

# 1. Backup config DENTRO del container
docker exec $BOT cp /home/node/.clawdbot/clawdbot.json /home/node/.clawdbot/clawdbot.json.bak.$TS

# 2. Backup config EN HOST (sobrevive a docker rm)
docker cp $BOT:/home/node/.clawdbot/clawdbot.json /root/${BOT}-config-bak-$TS.json

# 3. Si tocamos sesión, también backup en host
docker cp $BOT:/home/node/.openclaw/agents/main/sessions/SESS.jsonl \
  /root/${BOT}-session-bak-$TS.jsonl
```

## 📈 Monitorización proactiva (pendiente de implementar)

Cron diario en `/opt/bot-cost-monitor.sh`:

```bash
#!/bin/bash
# Cron: 0 8,20 * * *

# 1. Pull facturación dashboard provider (Mimo, Anthropic, etc.)
PROVIDER_USAGE=$(curl -s https://api.provider.com/usage | jq .pct_used)

# 2. Comparar con baseline (lo de ayer)
BASELINE=$(redis-cli GET cost_baseline_yesterday)

# 3. Si delta > 2%/24h, alertar via Telegram
if (( $(echo "$PROVIDER_USAGE - $BASELINE > 2" | bc -l) )); then
  curl -X POST "https://api.telegram.org/bot$TG_TOKEN/sendMessage" \
    -d "chat_id=176195444" \
    -d "text=⚠️ ALERTA: Consumo +$DELTA% en 24h. Ejecutar protocolo 4 vectores."
fi

# 4. Guardar nuevo baseline
redis-cli SET cost_baseline_yesterday "$PROVIDER_USAGE"
```

## 📚 Referencias

- Incidente NextHorizont AI 2-may-2026 (sangrado parcial, fix vector 3)
- Incidente NextHorizont AI 6-may-2026 (sangrado masivo, fix completo 4 vectores)
- OpenClaw docs 2026.4.15: `agents.defaults.skills` schema = `array<string>`
- Mimo provider: `token-plan-ams.xiaomimimo.com`
- VPS Hetzner: `31.97.69.100` (3 bots: Nova, Yuki, Maui)

---

## 💎 Lección destilada (para grabar en piedra)

```
DIAGNÓSTICO LLM = SUMA DE 4 VECTORES, NUNCA UNO SOLO

  Vector 1: ¿Qué se inyecta sin que lo pidas?    (skills, prompts)
  Vector 2: ¿Qué crece sin techo en disco?       (sesión, memoria)
  Vector 3: ¿Quién dispara turnos sin humano?    (cron, heartbeat)
  Vector 4: ¿Quién más usa esta API key?         (backups, .env)

CONFIGURACIÓN VACÍA = PEOR CASO POR DEFAULT, NO INOCUO
  skills: {}  →  cargar TODAS
  RLS sin def →  ABIERTO
  USER sin def → root
  webhook auth sin def → público

DISCREPANCIA = SUPERPODER DE DEBUGGING
  audit_interno ≠ facturación_externa → tercer actor con tus credenciales

COMPACTACIÓN NO ES RETROACTIVA
  safeguard previene → NO repara lo ya bloated
```
