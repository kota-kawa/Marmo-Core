# memory-dev — Codebase Q&A via MCP

Use this skill to answer questions about any indexed repository without loading source files into context. `memory-dev` performs embedding search and LLM synthesis; you receive a ready answer with cited source locations.

## When to use

- "How does X work in this codebase?"
- "Where is Y implemented?"
- "What files are involved in Z?"

Delegate these questions to memory-dev instead of reading files yourself. Reduces token usage significantly for large codebases.

## Setup

Add `.mcp.json` to your project root to enable the tools in Claude Code (or any MCP-compatible assistant):

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

Then index the project once: `memory-dev init .`

The MCP server auto-detects the active project via `.memory-dev.json` written by `init`.

---

## Available tools

### `memory_ask`

Ask a natural language question. Returns a synthesized answer with source citations.

**Input:**
```json
{ "query": "how does authentication work?", "maxResults": 5 }
```

**Output:**
```json
{
  "answer": "Authentication is handled by...",
  "sources": [
    { "file": "src/lib/auth.ts", "lines": [12, 45], "score": 0.87 }
  ],
  "confidence": 0.72
}
```

Use `confidence` as a quality signal — below ~0.3 means the codebase has little relevant content for the query.

### `memory_search`

Return raw code chunks by semantic similarity. Useful when you want to inspect the actual code rather than a synthesized answer.

**Input:**
```json
{ "query": "database connection pooling", "limit": 10 }
```

### `memory_projects`

List all indexed projects and their status.

**Output:**
```json
{
  "projects": [
    { "id": "...", "name": "my-project", "status": "ready", "lastIndexed": "..." }
  ]
}
```

Only projects with `"status": "ready"` can be queried.

### `memory_file_tree`

Show the file tree for the active project. Useful for orientation before asking questions.

---

## Recommended workflow

```
1. memory_projects        → confirm project is indexed and ready
2. memory_ask             → ask about architecture, logic, or specific behaviour
3. memory_search          → find relevant code when you need to read the source
```

If `memory-dev` is not reachable or the project is not indexed, fall back to reading files directly.
