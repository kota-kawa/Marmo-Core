# Contributing to memory-dev

## Prerequisites

- Node.js 20+
- npm 10+
- Git

## Setup

```bash
git clone https://github.com/AokDesu/dev-memory-ai.git
cd dev-memory-ai
npm install --legacy-peer-deps
cp .env.example .env
# Add your GOOGLE_API_KEY to .env
```

## Run from source

```bash
# Index the project itself
node cli.js init .

# Ask a question
node cli.js ask "how does indexing work?"

# Launch TUI
node cli.js

# Start MCP server
node cli.js mcp
```

No build step needed. `cli.js` loads TypeScript at runtime via `tsx`.

## Project structure

```
cli.ts                   Commander entry point; no-arg → TUI
cli.js                   Bin shim (tsx loader bootstrap)
mcp-server.ts            MCP server over stdio

src/
  cli/commands/          One file per CLI subcommand
  lib/
    indexer/             File walking + chunking + embedding storage
    parser/              Tree-sitter AST parsing
    rag/                 RAG chain (embed query → search → LLM)
    search/              Vector search over SQLite
    llm.ts               Multi-provider LLM + embeddings
    db.ts                Prisma client singleton
  tui/
    App.tsx              Root Ink component
    components/          Ink panes (Ask, Search, Status, Watch, Init)
    hooks/               React hooks wrapping lib functions

prisma/schema.prisma     DB schema (Repository, File, CodeChunk)
```

## Tests

```bash
npm test              # run once
npm run test:watch    # watch mode
npm run test:coverage # coverage report
```

## Code style

- TypeScript strict mode — no `any` unless unavoidable
- ESM only — `.js` extension on all local imports (even in `.ts` files)
- No build step — never commit compiled `.js` files from `src/`
- No console.log in lib code — use `logger` from `src/lib/logger.ts`

## Pull requests

- One feature or fix per PR
- Include a short description of what and why
- Run `npm test` before submitting
- New dependencies need a clear justification — the dep list is intentionally minimal
