# MCP N8N Workflow Builder — Instalación

## Requisitos
- Node.js >= 18
- npm >= 9

## Paso 1: Instalar dependencias y compilar

```bash
cd standalone/
npm install
npm run build
```

## Paso 2: Configurar en Claude Desktop

Edita `claude_desktop_config.json`:

**macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`
**Windows**: `%APPDATA%\Claude\claude_desktop_config.json`
**Linux**: `~/.config/Claude/claude_desktop_config.json`

```json
{
  "mcpServers": {
    "n8n-workflow-builder": {
      "command": "node",
      "args": ["/RUTA/ABSOLUTA/standalone/build/index.js"]
    }
  }
}
```

> Sustituye `/RUTA/ABSOLUTA/` por la ruta real donde clonaste PROYECTO-SKILLS.

## Paso 3: Reiniciar Claude Desktop

Cierra y abre Claude Desktop. El servidor MCP aparecerá como herramienta disponible.

## Paso 4: Verificar

En Claude Desktop, pide:
> "Crea un workflow n8n con un webhook trigger que envíe datos a una API REST"

Claude usará automáticamente la herramienta `create_workflow` del MCP server.

## Configurar en Claude Code CLI

```bash
# Añadir al proyecto
claude mcp add n8n-workflow-builder node /RUTA/ABSOLUTA/standalone/build/index.js
```

## Solución de problemas

**El servidor no aparece**: Verifica que la ruta en `args` es absoluta y correcta.
**Error de compilación**: Asegúrate de tener Node.js >= 18 (`node --version`).
**Permisos**: En Linux/macOS, da permisos de ejecución: `chmod +x build/index.js`
