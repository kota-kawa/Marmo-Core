# Architecture

`memory-dev` is a single Node.js CLI process. There is no web server. The same library code powers the CLI commands, the TUI dashboard, and the MCP server.

## Components

```
cli.ts ──────────────────────────────────────────────────────────────────────┐
  commander                                                                   │
  ├── init     ─────────────────────────────── Indexing pipeline             │
  ├── ask      ─────────────────────────────── RAG pipeline                  │
  ├── search   ─────────────────────────────── Vector search                 │
  ├── status   ─────────────────────────────── DB read                       │
  ├── watch    ─────────────────────────────── File watcher                  │
  └── mcp      ─────────────────────────────── MCP server                   │
                                                                              │
  (no-arg) ─── Ink TUI ─────────────────────── same lib functions            │
```

---

## Indexing pipeline (`memory-dev init`)

Entry: `src/lib/indexer/file-indexer.ts` → `indexRepository()`

1. **Walk** — `simple-git` + `fast-glob` enumerate files respecting `.gitignore`
2. **Parse** — `src/lib/parser/code-parser.ts` loads the Tree-sitter WASM grammar for the file's language and extracts typed chunks: functions, classes, modules, with start/end line numbers and optional names
3. **Chunk** — long files are split with overlap (configurable overlap window) to preserve context across chunk boundaries
4. **Embed** — `src/lib/llm.ts` → `getEmbeddings(texts[])` calls the configured provider:
   - `local`: `@xenova/transformers` running `Xenova/all-MiniLM-L6-v2` in Node.js (~80 MB, downloaded once)
   - `gemini`: Gemini `text-embedding-004` API
   - `openai`: OpenAI `text-embedding-3-small` API
5. **Store** — Prisma upserts `Repository`, `File`, and `CodeChunk` records. Embeddings stored as JSON float arrays in SQLite (libsql driver via `@prisma/adapter-libsql`)

Incremental update: `indexSingleFile(repoId, repoPath, relPath)` runs the same pipeline for a single file, deleting stale chunks before re-inserting.

---

## Query pipeline (`memory-dev ask` / `memory-dev search`)

Entry: `src/lib/rag/rag-chain.ts` → `queryRAGStream()` / `queryRAG()`

1. **Embed query** — same `getEmbeddings()` call used at index time
2. **Vector search** — `src/lib/search/vector-search.ts` → `searchCodeChunks()`:
   - Loads all `CodeChunk` embeddings for the project from SQLite
   - Computes cosine similarity between query vector and each chunk vector
   - Returns top-K results sorted by score
3. **Synthesize** — top-K chunks assembled as context, passed to LangChain with a system prompt instructing the model to cite sources
4. **Stream** — `queryRAGStream()` returns `{ stream: AsyncIterable, sources: [] }`. The CLI and TUI both consume the async iterable to render tokens as they arrive

---

## Watch mode (`memory-dev watch`)

Entry: `src/cli/commands/watch.ts` and `src/tui/hooks/useWatch.ts`

- `chokidar` watches the repository path with `persistent: true`
- On `add` / `change`: calls `indexSingleFile()` for the modified file
- On `unlink`: deletes the `File` and its `CodeChunk` records from the DB
- The TUI hook caps the event list at 200 entries and displays the last N rows

---

## MCP server (`memory-dev mcp`)

Entry: `mcp-server.ts`

Speaks the [Model Context Protocol](https://modelcontextprotocol.io) over stdio using `@modelcontextprotocol/sdk`.

**Project auto-detection** (in order):
1. `.memory-dev.json` in `process.cwd()` (written by `memory-dev init`)
2. DB lookup by `gitRemote` matching current repo's remote
3. DB lookup by `path` prefix matching `process.cwd()`

**Tools exposed:**

| Tool | Calls | Description |
|---|---|---|
| `memory_ask` | `queryRAG()` | Synthesized answer with sources |
| `memory_search` | `searchCodeChunks()` | Raw ranked chunks |
| `memory_projects` | `prisma.repository.findMany()` | Indexed project list |
| `memory_file_tree` | `prisma.file.findMany()` | File list for a project |

---

## TUI (`memory-dev` with no arguments)

Entry: `cli.ts` → `src/tui/App.tsx`

Built with [Ink v5](https://github.com/vadimdemedes/ink) (React for CLIs). Ink renders React component trees to the terminal using its own layout engine (no DOM).

All TUI hooks call the same lib functions as the CLI commands:

| Hook | Calls |
|---|---|
| `useAsk` | `queryRAGStream()` |
| `useSearch` | `getEmbeddings()` + `searchCodeChunks()` |
| `useWatch` | `chokidar` + `indexSingleFile()` |
| `useProject` | `prisma.repository.findMany()` |

`console.log` is suppressed before `render()` to prevent stdout corruption; restored after `waitUntilExit()`.

---

## Database schema

`prisma/schema.prisma` — SQLite via `@prisma/adapter-libsql`

```
Repository   id, path, name, gitRemote, status, lastIndexed
  └─ File    id, repositoryId, path, language, size, hash
       └─ CodeChunk  id, fileId, repositoryId, content, embedding (JSON),
                     lineStart, lineEnd, chunkType, name, language
```

`embedding` is stored as a JSON float array. Vector search is done in JavaScript (cosine similarity over all chunks for the project). For projects with millions of chunks a dedicated vector DB would be more efficient, but SQLite is sufficient for codebases up to ~100k lines.
