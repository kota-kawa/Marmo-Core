@AGENTS.md

# memory-dev — project context for AI coding assistants

## What this is

`memory-dev` is a standalone Node.js CLI tool (not a web app). It indexes git repositories into a local SQLite vector database and lets you query them using RAG (Retrieval-Augmented Generation). The npm binary is `memory-dev`.

## Entry points

| File | Purpose |
|---|---|
| `cli.js` | Bin shim — registers tsx loader, then imports `cli.ts` |
| `cli.ts` | Commander CLI — 6 subcommands; no-arg launches Ink TUI |
| `mcp-server.ts` | MCP server — auto-detects project, exposes 4 tools over stdio |

## Architecture at a glance

```
cli.ts
  ├── commands/init.ts     → src/lib/indexer/file-indexer.ts
  ├── commands/ask.ts      → src/lib/rag/rag-chain.ts
  ├── commands/search.ts   → src/lib/search/vector-search.ts
  ├── commands/watch.ts    → chokidar + indexSingleFile()
  ├── commands/status.ts   → prisma.repository.findUnique
  └── commands/mcp.ts      → mcp-server.ts

src/tui/              Ink v5 (React-in-terminal) TUI dashboard
src/lib/              All shared logic — no Next.js, no HTTP server
prisma/               SQLite schema (Repository, File, CodeChunk)
```

## Key rules for this codebase

- **ESM only** — all local imports need `.js` extension even in `.ts` files
- **No Next.js** — do not suggest `app/`, `pages/`, `next.config`, or Next.js APIs
- **Windows paths** — use `pathToFileURL(resolve(...)).href` for dynamic `import()`
- **Prisma v7** — check `prisma/schema.prisma`; API differs from v5/v6
- **React 18** — Ink v5 is incompatible with React 19 (removed `ReactCurrentOwner`)
- **tsx at runtime** — no build step; `cli.js` loads TypeScript via `tsx/esm/api`
