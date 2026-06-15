# memory-dev

AI-powered semantic memory for your codebase. Index any git repository, then ask questions in natural language — answers stream back with cited source locations.

```
$ memory-dev ask "how does the indexing pipeline work?"

The indexing pipeline starts in file-indexer.ts. It walks the git repository
respecting .gitignore, parses each file with Tree-sitter to extract typed chunks
(functions, classes, modules), generates embeddings via the configured provider,
and stores everything in a local SQLite database via Prisma.

Sources:
  1. src/lib/indexer/file-indexer.ts:45–120  (89%)
  2. src/lib/parser/code-parser.ts:12–67     (74%)
  3. prisma/schema.prisma:1–42               (61%)
```

## How it works

`memory-dev init` walks your repo, parses code with Tree-sitter (AST-level chunking), generates vector embeddings, and stores everything in a local SQLite database. When you ask a question, the query is embedded, matched against stored vectors via cosine similarity, and the top results are synthesized into an answer by an LLM.

No cloud database required. Everything runs locally by default.

## Prerequisites

- Node.js 20+
- A git repository to index
- Google AI API key — free tier works ([get one here](https://aistudio.google.com/app/apikey))

## Install

```bash
git clone https://github.com/AokDesu/dev-memory-ai.git
cd dev-memory-ai
npm install --legacy-peer-deps
cp .env.example .env
# add your GOOGLE_API_KEY to .env
npm link        # makes `memory-dev` available globally
```

Or run without installing:
```bash
node /path/to/dev-memory-ai/cli.js init .
```

## Quick start

```bash
# Index your project
memory-dev init /path/to/your/repo

# Ask a question
memory-dev ask "how does authentication work?"

# Launch the interactive TUI dashboard
memory-dev
```

## CLI commands

| Command | Description |
|---|---|
| `memory-dev init [path]` | Index a git repository (defaults to current directory) |
| `memory-dev ask "<question>"` | Ask a question, get a streamed answer with sources |
| `memory-dev search "<query>"` | Semantic search returning raw code chunks |
| `memory-dev status` | Show project status, file counts, chunk counts |
| `memory-dev watch` | Watch for file changes and re-index incrementally |
| `memory-dev mcp` | Start an MCP server for AI assistant integration |

### Options

```bash
memory-dev init --force          # Re-index an already-indexed project
memory-dev ask -n 10 "..."       # Use 10 source chunks (default: 5)
memory-dev search -n 20 "..."    # Return up to 20 results (default: 10)
```

## TUI dashboard

Run `memory-dev` with no arguments to open the interactive dashboard:

```
╭────────────────────────────────────────────────────╮
│  memory-dev  │  my-project (ready · 1051 chunks)   │
╰────────────────────────────────────────────────────╯
╭──────────────┬─────────────────────────────────────╮
│  PROJECTS    │  [Ask]  Search  Status  Watch        │
│  ● my-project│                                     │
│  ○ other-repo│  > how does the RAG pipeline work?  │
│              │                                     │
│  [+] Add new │  ── Answer ─────────────────────    │
│              │  The RAG pipeline is in rag-chain   │
│              │  .ts. It embeds the query, runs     │
│              │  vector search for top-K chunks...  │
│              │                                     │
│              │  ── Sources (3) ─────────────────   │
│              │  1. src/lib/rag/rag-chain.ts:45–90  │
╰──────────────┴─────────────────────────────────────╯
  Tab: switch tab  ←→: sidebar/pane  Esc: release  q: quit
```

**Key bindings:**

| Key | Action |
|---|---|
| `Tab` | Cycle through tabs (Ask / Search / Status / Watch) |
| `→` | Focus the active pane |
| `←` | Focus the project sidebar |
| `↑` / `↓` | Navigate results or project list |
| `Esc` | Release input focus back to global navigation |
| `q` | Quit |

**Tabs:**
- **Ask** — type a question, get a streamed answer with cited sources
- **Search** — live semantic search as you type; arrow keys navigate results
- **Status** — file/chunk counts, last indexed time, git remote
- **Watch** — real-time file change feed with automatic incremental re-index

## MCP integration

`memory-dev mcp` speaks the [Model Context Protocol](https://modelcontextprotocol.io). Add `.mcp.json` to your project root to give Claude Code (or any MCP-compatible assistant) access to your indexed codebase:

```json
{
  "mcpServers": {
    "memory-dev": {
      "command": "memory-dev",
      "args": ["mcp"]
    }
  }
}
```

If running from source instead of a global install:
```json
{
  "mcpServers": {
    "memory-dev": {
      "command": "node",
      "args": ["/path/to/dev-memory-ai/cli.js", "mcp"]
    }
  }
}
```

The MCP server auto-detects the active project via `.memory-dev.json` written by `init`. It exposes four tools:

| Tool | Description |
|---|---|
| `memory_ask` | Ask a question, get a synthesized answer with sources |
| `memory_search` | Return raw code chunks by semantic similarity |
| `memory_projects` | List all indexed projects and their status |
| `memory_file_tree` | Show the file tree for a project |

See [skill.md](./skill.md) for the full integration guide.

## AI providers

Set `AI_PROVIDER` in your `.env`:

| Provider | Value | Env var | Notes |
|---|---|---|---|
| Google Gemini | `gemini` (default) | `GOOGLE_API_KEY` | Free tier: 1,500 req/day |
| OpenAI | `openai` | `OPENAI_API_KEY` | GPT-4o recommended |
| Ollama | `ollama` | `OLLAMA_BASE_URL` | Local, no API key needed |

Set `EMBEDDINGS_PROVIDER` for vector generation:

| Provider | Value | Notes |
|---|---|---|
| Local | `local` (default) | ~80 MB model, offline, no API key |
| Gemini | `gemini` | Requires `GOOGLE_API_KEY` |
| OpenAI | `openai` | Requires `OPENAI_API_KEY` |

> The embeddings provider must be the same at index time and query time. If you change it, re-run `memory-dev init --force`.

## Environment variables

Copy `.env.example` to `.env`:

| Variable | Default | Description |
|---|---|---|
| `DATABASE_URL` | `file:./prisma/dev.db` | SQLite path (local) or Turso URL |
| `DATABASE_AUTH_TOKEN` | — | Required only for Turso cloud DB |
| `GOOGLE_API_KEY` | — | Google AI API key |
| `AI_PROVIDER` | `gemini` | LLM provider: `gemini`, `openai`, `ollama` |
| `GEMINI_MODEL` | `gemini-2.0-flash` | Gemini model name |
| `OPENAI_API_KEY` | — | OpenAI API key |
| `EMBEDDINGS_PROVIDER` | `local` | Embeddings: `local`, `gemini`, `openai` |
| `NODE_ENV` | `development` | `production` enables file logging |
| `LOG_LEVEL` | `info` | `debug`, `info`, `warn`, `error` |
| `LOG_TO_FILE` | `false` | Write logs to `LOG_DIR` |

## Architecture

```
memory-dev init
    └─ file-indexer.ts     walk git repo, respect .gitignore
         └─ code-parser.ts Tree-sitter AST → typed chunks (fn, class, module)
              └─ llm.ts    getEmbeddings() → float32 vectors
                   └─ Prisma  store in SQLite (Repository, File, CodeChunk)

memory-dev ask / search / mcp
    └─ rag-chain.ts        embed query → searchCodeChunks() vector KNN
         └─ vector-search.ts cosine similarity over stored embeddings
              └─ LLM       synthesize streamed answer from top-K chunks

memory-dev watch
    └─ chokidar            file system events
         └─ indexSingleFile() incremental update for changed file

memory-dev mcp
    └─ mcp-server.ts       MCP protocol over stdio
         └─ memory_ask / memory_search / memory_projects / memory_file_tree
```

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for the full walkthrough.

## Docker

For running `memory-dev watch` or `memory-dev mcp` as a persistent service:

```bash
docker build -t memory-dev .

docker run -it --rm \
  -v /path/to/your/repo:/repo \
  -v memory-dev-data:/data \
  -e GOOGLE_API_KEY=your_key \
  -e DATABASE_URL=file:/data/dev.db \
  memory-dev mcp
```

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md).

## License

MIT
