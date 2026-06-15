# Configuración CORRECTA de OpenClaw para MCP Server con SSE

## 🎯 Método Correcto: Configuración via openclaw.json

### Paso 1: Localiza el archivo de configuración

El archivo de configuración de OpenClaw se llama `openclaw.json` y se encuentra en:

**macOS/Linux:**
```bash
~/.openclaw/openclaw.json
```

**Windows:**
```
%USERPROFILE%\.openclaw\openclaw.json
```

### Paso 2: Edita openclaw.json

Abre el archivo con tu editor favorito:

```bash
nano ~/.openclaw/openclaw.json
# o
code ~/.openclaw/openclaw.json
```

### Paso 3: Agrega la configuración del Plugin MCP

Busca la sección `"plugins"` (o créala si no existe) y agrega:

```json
{
  "plugins": {
    "entries": {
      "mcp-integration": {
        "enabled": true,
        "config": {
          "enabled": true,
          "servers": {
            "binance-trading": {
              "enabled": true,
              "transport": "http",
              "url": "http://localhost:8080/sse"
            }
          }
        }
      }
    }
  }
}
```

### Paso 4: Instala el Plugin MCP (si no está instalado)

OpenClaw puede no tener el plugin MCP instalado por defecto. Instálalo así:

```bash
cd ~/.openclaw/extensions/
git clone https://github.com/lunarpulse/openclaw-mcp-plugin.git mcp-integration
cd mcp-integration
npm install
```

### Paso 5: Reinicia OpenClaw Gateway

```bash
openclaw gateway restart
```

### Paso 6: Verifica la conexión

**Método 1: Via logs**
```bash
tail -f /tmp/openclaw/openclaw-*.log | grep -i "mcp\|binance"
```

**Método 2: Via comando**
```bash
openclaw mcp list
```

Deberías ver `binance-trading` en la lista de servidores conectados.

**Método 3: Via chat en OpenClaw**
```
Lista todas las herramientas MCP disponibles
```

Deberías ver las 9 herramientas de tu servidor Binance:
- binance-trading:get_account_balance
- binance-trading:get_market_price
- binance-trading:place_order
- binance-trading:cancel_order
- binance-trading:fetch_chart_data
- binance-trading:calculate_indicators
- binance-trading:adjust_leverage
- binance-trading:read_bot_logs
- binance-trading:update_strategy_parameters

---

## 🔧 Configuración Completa (Ejemplo Real)

Si tu `openclaw.json` está vacío o quieres ver un ejemplo completo, aquí está:

```json
{
  "gateway": {
    "host": "0.0.0.0",
    "port": 18789,
    "token": "tu-gateway-token-aqui"
  },
  "channels": {
    "telegram": {
      "enabled": true,
      "botToken": "tu-telegram-bot-token",
      "dmPolicy": "pairing"
    }
  },
  "provider": {
    "type": "anthropic",
    "apiKey": "tu-anthropic-api-key",
    "model": "claude-sonnet-4-20250514"
  },
  "plugins": {
    "entries": {
      "mcp-integration": {
        "enabled": true,
        "config": {
          "enabled": true,
          "servers": {
            "binance-trading": {
              "enabled": true,
              "transport": "http",
              "url": "http://localhost:8080/sse"
            }
          }
        }
      }
    }
  }
}
```

---

## ✅ Validación Final

Una vez configurado, ejecuta este test en OpenClaw:

```
Usa la herramienta MCP binance-trading:get_account_balance 
con el parámetro asset="USDT" y reporta el resultado.
```

**Respuesta esperada:**
```
He ejecutado binance-trading:get_account_balance(asset="USDT")
Tu balance actual de USDT es: X.XX USDT
```

---

## 🚨 Troubleshooting

### Error: "Plugin mcp-integration not found"

**Solución:**
```bash
# Verifica que el plugin esté instalado
ls ~/.openclaw/extensions/mcp-integration

# Si no existe, instálalo:
cd ~/.openclaw/extensions/
git clone https://github.com/lunarpulse/openclaw-mcp-plugin.git mcp-integration
cd mcp-integration
npm install
```

### Error: "Cannot connect to http://localhost:8080/sse"

**Solución:**
```bash
# Verifica que tu MCP Server esté corriendo:
curl http://localhost:8080/sse

# Si no responde, inicia el servidor:
cd /Users/jorgemacias/jorge/gemini_open_router/MCP
python mcp_server.py
```

### Error: "No MCP tools available"

**Solución:**
```bash
# Revisa los logs:
tail -f /tmp/openclaw/openclaw-*.log

# Verifica que el servidor MCP esté exponiendo las herramientas correctamente:
curl -H "Accept: text/event-stream" http://localhost:8080/sse
```

---

## 📋 Checklist de Configuración

- [ ] Archivo `openclaw.json` editado con la sección `plugins`
- [ ] Plugin `mcp-integration` instalado en `~/.openclaw/extensions/`
- [ ] MCP Server corriendo en `http://localhost:8080/sse`
- [ ] OpenClaw Gateway reiniciado
- [ ] Comando `openclaw mcp list` muestra `binance-trading`
- [ ] Test de `get_account_balance` exitoso

---

## 🚀 Operación de Trading con OpenClaw

Con las herramientas que ya has implementado en tu servidor MCP, tienes el motor necesario para replicar el flujo de trabajo de OpenClaw que se muestra en el video. Aquí tienes los pasos exactos que debes seguir, basándote en la metodología de Michael Automates, para que tu agente comience a operar de forma autónoma:

### 1. La "Prueba de Fuego" (Test de Integración)

Antes de realizar cualquier operación real, el video sugiere validar que la IA tiene control sobre tu cuenta de Binance sin arriesgar capital.

- **Instrucción a la IA:** Pídele que use tu herramienta `adjust_leverage` para cambiar el apalancamiento de un par (por ejemplo, BTCUSDT) a un número específico, como 7x.
- **Verificación:** Si la IA logra cambiar el apalancamiento con éxito, habrás confirmado que la conexión es correcta.

### 2. Creación de la Estrategia y Backtesting Obligatorio

El video es muy enfático en un punto: "No permitas que la IA te diga que es una gran estrategia sin números".

- **Solicitud de estrategia:** Pide a la IA que cree una estrategia específica (ej. "Trend Following") para un par en un gráfico de 4 horas.
- **Backtest:** Dile que use sus herramientas `fetch_chart_data` y `calculate_indicators` para realizar un backtest sobre datos históricos.
- **Análisis colaborativo:** Pídele que te muestre los KPIs (indicadores de rendimiento) del backtest. Como OpenClaw puede ver múltiples puntos de datos a la vez, pídele su opinión técnica sobre los pros y contras de la estrategia comparándola con otras (ej. Trending vs. Ranging).

### 3. Escritura del Archivo de Estrategia (.js)

Una vez que estés satisfecho con los resultados del backtest, el siguiente paso es la persistencia.

- **Generación del archivo:** La IA debe escribir el código de la lógica de trading en un archivo físico dentro de su espacio de trabajo, por ejemplo: `binance_trend_strategy.js`.
- **Contenido del archivo:** Este archivo debe llamar a tus herramientas de MCP para consultar precios y ejecutar órdenes cuando se cumplan las condiciones.

### 4. Automatización mediante Cron Jobs (El "Despertador")

Para que el bot sea autónomo y no dependa de que tú estés chateando con él, debe ser capaz de autoejecutarse.

- **Programación:** Pide a la IA (aprovechando que tiene acceso a tu terminal) que configure un cron job en Linux.
- **Frecuencia:** Si la estrategia es de 4 horas, el cron job debe "despertar" al script cada 4 horas.
- **Ciclo de vida:** En cada ejecución, el script debe: despertarse, analizar el mercado, decidir si entrar (long/short), salir o no hacer nada, y volver a dormir hasta la siguiente sesión.

### 5. Reflexión y Mejora Continua

El video destaca que lo que hace especial a este sistema es que no es solo transaccional; puede "reflexionar sobre sus acciones".

- **Reporte de actividad:** Cada cierto tiempo, entra al chat y pide un reporte de lo que ha hecho el bot.
- **Adaptación:** Si el rendimiento no es el esperado, el video sugiere pedirle a la IA que use `read_bot_logs` para reflexionar sobre su desempeño pasado y adapte el plan o modifique el archivo `.js` para ajustarse a las nuevas condiciones del mercado.

### Resumen del siguiente paso inmediato

Pide a tu agente que use `fetch_chart_data` para hacer un backtest de una estrategia de tendencia en BTC y que te presente los resultados con números antes de proceder a programar el cron job.
