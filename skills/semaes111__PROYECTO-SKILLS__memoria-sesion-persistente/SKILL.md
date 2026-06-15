---
name: session-memory
description: >
  Sistema de pseudo-memoria persistente entre sesiones de Cowork.
  Usa un archivo CLAUDE-MEMORY.md en la carpeta del usuario como almacen
  estructurado de hechos, decisiones, proyectos, preferencias y contexto
  acumulado entre sesiones. Cuando el usuario dice "guarda en la memoria",
  Claude escribe/actualiza el archivo. Cuando dice "carga la memoria",
  Claude lo lee y recupera todo el contexto. El archivo actua como
  cerebro externo que persiste en el disco del usuario.
  Usar cuando el usuario mencione: guarda en la memoria, recuerda esto,
  carga la memoria, que sabes de mi, memoria persistente, contexto entre
  sesiones, no te olvides, apunta esto, actualiza la memoria.
triggers:
  - "guarda en la memoria"
  - "carga la memoria"
  - "recuerda esto"
  - "que sabes de mi"
  - "actualiza la memoria"
  - "no te olvides"
  - "apunta esto"
  - "memoria persistente"
  - "borra de la memoria"
  - "busca en la memoria"
---

# Session Memory: Pseudo-Memoria Persistente para Cowork

## Concepto

Claude no tiene memoria entre sesiones. Este skill resuelve esa limitacion
usando un archivo `CLAUDE-MEMORY.md` almacenado en la carpeta seleccionada
por el usuario como **cerebro externo persistente**.

El flujo es:

```
INICIO DE SESION                    FIN DE SESION
      │                                   │
      ▼                                   ▼
"carga la memoria"              "guarda en la memoria"
      │                                   │
      ▼                                   ▼
Read CLAUDE-MEMORY.md           Write/Edit CLAUDE-MEMORY.md
      │                                   │
      ▼                                   ▼
Claude tiene contexto           Contexto persiste en disco
de sesiones anteriores          para la proxima sesion
```

## Comandos del Usuario y Comportamiento Esperado

### 1. "carga la memoria" / "que sabes de mi"

**Accion:** Leer `CLAUDE-MEMORY.md` de la carpeta del usuario.

```
Paso 1: Buscar el archivo en la carpeta montada del usuario
        → Ruta: /sessions/*/mnt/outputs/CLAUDE-MEMORY.md
        → O en la carpeta seleccionada: /sessions/*/mnt/*/CLAUDE-MEMORY.md

Paso 2: Si existe → Read completo del archivo
        Si NO existe → Informar al usuario y ofrecer crear uno nuevo

Paso 3: Parsear las secciones y resumir al usuario:
        "He cargado tu memoria. Conozco X proyectos, Y decisiones
         tecnicas, y Z preferencias. La ultima sesion fue el [fecha]
         donde trabajamos en [tema]."

Paso 4: Mantener el contenido en contexto para toda la sesion
```

### 2. "guarda en la memoria" / "recuerda esto" / "apunta esto"

**Accion:** Actualizar `CLAUDE-MEMORY.md` con informacion de la sesion actual.
