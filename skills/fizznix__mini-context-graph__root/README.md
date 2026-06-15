# Mini Context Graph Skill

A reusable **mini-context-graph** skill for agents that combines Karpathy's **llm-wiki** pattern with a structured **knowledge graph** to build a persistent, compounding knowledge base from unstructured documents.

Documents are ingested once. The LLM writes wiki pages, extracts entities and relations into a graph, and stores raw content with provenance. On every query, the accumulated wiki is consulted first — answers compound instead of being re-derived from scratch each time.

---

## How It Relates to LLM Wiki

[llm-wiki](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f) describes a three-layer pattern:

> "Instead of just retrieving from raw documents at query time, the LLM incrementally builds and maintains a persistent wiki — a structured, interlinked collection of markdown files that sits between you and the raw sources."

This skill implements that pattern **and extends it with a structured knowledge graph:**

| LLM Wiki (Karpathy) | Mini Context Graph (this skill) |
|---------------------|--------------------------------|
| Raw sources stored as immutable files | Raw sources stored as immutable docs + auto-chunks (`documents_store`) |
| LLM writes a wiki of markdown pages | LLM writes wiki pages AND extracts a typed entity/relation graph |
| Schema file tells LLM wiki conventions | `skill.md`, `ingestion.md`, `ontology.md`, `retrieval.md` are the schema |
| index.md + log.md for navigation/history | Same, auto-managed by `wiki_store` |
| Query: read wiki, synthesize answer | Query: **wiki-first** (fast) → graph BFS (deep) → evidence chain (citations) |
| No structured traversal | BFS over typed, confidence-weighted graph — answers multi-hop questions |
| No provenance on claims | Every graph node + edge links back to source chunk + supporting text |
| Lint: detect orphans, broken links | Same, plus graph-level checks via `wiki_store.lint_wiki()` |

### What the graph layer adds

The LLM Wiki is powerful for reading and synthesis. The graph adds **structural reasoning** that plain wiki pages can't do well:

- **Multi-hop queries** — "What systems does X transitively affect?" traverses the graph in one call instead of reading dozens of pages.
- **Confidence-weighted facts** — Relations are stored with confidence scores; weak inferences are excluded from retrieval automatically.
- **Typed deduplication** — The same entity mentioned across 50 documents is one node, not 50 copies.
- **Evidence chains** — Every answer comes with `supporting_text` from the exact source chunk, not just a page link.
- **Ontology normalization** — "uses", "utilizes", "leverages" all resolve to the same canonical relation type, keeping the graph clean.

---

## Architecture

```
┌─────────────────────────────────────────────────────┐
│                    LLM / Agent                      │
│  Reads .md files → reasons → calls Python methods   │
└───────────┬─────────────────────────────────────────┘
            │
            ▼
┌─────────────────────────────────────────────────────────────────┐
│  LAYER 1 — Raw Sources (immutable)                              │
│  data/documents.json                                            │
│  • Full document text + auto-generated overlapping chunks       │
│  • Ground truth — never modified after ingest                   │
└─────────────────────────┬───────────────────────────────────────┘
                          │  provenance links
            ┌─────────────┴─────────────┐
            ▼                           ▼
┌───────────────────────┐    ┌──────────────────────────────────────┐
│  LAYER 2 — Wiki       │    │  LAYER 3 — Knowledge Graph           │
│  wiki/                │    │  data/graph.json + index.json        │
│  • entities/*.md      │    │  • Typed nodes (entity name + type)  │
│  • summaries/*.md     │    │  • Typed edges (relation + confidence│
│  • topics/*.md        │    │  • Provenance: source_document,      │
│  • index.md (catalog) │    │    source_chunks, supporting_text    │
│  • log.md (history)   │    │  • BFS traversal for multi-hop       │
└───────────────────────┘    └──────────────────────────────────────┘
```

---

## Project Structure

```
mini-context-graph-skill/
│
├── skill.md        # Agent entrypoint — all three operations (Ingest/Query/Lint)
├── ingestion.md    # Entity/relation extraction rules + wiki writing step
├── ontology.md     # Type normalization + synonym maps
├── retrieval.md    # Wiki-first query path + BFS graph traversal strategy
├── lint.md         # Wiki health-check workflow
│
├── scripts/
│   ├── contextgraph.py          # Orchestration interface
│   ├── config.py                # MAX_GRAPH_DEPTH, MIN_CONFIDENCE, MAX_NODES
│   └── tools/
│       ├── graph_store.py       # Node + edge storage with provenance (graph.json)
│       ├── index_store.py       # Entity + keyword index (index.json)
│       ├── ontology_store.py    # Type/relation registry (ontology.json)
│       ├── retrieval_engine.py  # BFS graph traversal
│       ├── documents_store.py   # Raw doc + chunk storage (documents.json)
│       └── wiki_store.py        # Wiki page I/O, index.md, log.md, lint
│
├── wiki/
│   ├── index.md        # Auto-managed page catalog
│   ├── log.md          # Append-only operation history
│   ├── entities/       # One page per entity
│   ├── summaries/      # One page per ingested document
│   └── topics/         # Cross-cutting synthesis pages
│
└── data/
    ├── graph.json       # Nodes + edges with provenance
    ├── documents.json   # Raw docs + chunks
    ├── ontology.json    # Type/relation registry
    └── index.json       # Keyword + entity index
```

---

## The Three Operations

### Ingest

Agent reads a document once and does everything:
1. Extracts entities + relations with `supporting_text` (per `ingestion.md`)
2. Calls `skill.ingest_with_content(...)` — stores raw content, links provenance to graph
3. Writes a **wiki summary page** for the document
4. Writes or updates **entity pages** for every extracted entity
5. Updates **topic pages** if the document touches existing syntheses

```python
from scripts.contextgraph import ContextGraphSkill
from scripts.tools import wiki_store

skill = ContextGraphSkill()

result = skill.ingest_with_content(
    doc_id="doc_001",
    title="System Crash Analysis",
    source="/docs/incident_report.pdf",
    raw_content="System crashes due to memory leaks...",
    entities=[
        {"name": "memory leak",  "type": "issue", "supporting_text": "memory leaks cause crashes"},
        {"name": "system crash", "type": "issue", "supporting_text": "system crashes due to memory leaks"},
    ],
    relations=[
        {"source": "memory leak", "target": "system crash", "type": "causes",
         "confidence": 1.0, "supporting_text": "System crashes due to memory leaks."},
    ],
)
# → {"doc_id": "doc_001", "chunk_count": 1, "nodes_added": 2, "edges_added": 1}
```

### Query

Wiki-first path, then graph, then file the answer back:

```python
# Fast path: check wiki first
pages = wiki_store.search_wiki("memory leak system crash")

# Deep path: graph traversal + evidence
result = skill.query_with_evidence("Why does the system crash?")
# Returns:
# {
#   "subgraph": {"nodes": {...}, "edges": [...]},
#   "supporting_documents": [{"doc_title": ..., "supporting_chunks": [...]}],
#   "evidence_chain": "memory leak --[causes]--> system crash"
# }

# File valuable answers back into the wiki (so future queries hit the fast path)
wiki_store.write_page(category="topic", title="Why System Crashes", content=..., summary=...)
```

### Lint

Periodic health check to keep the wiki accurate:

```python
from scripts.tools import wiki_store

issues = wiki_store.lint_wiki()
# Returns orphan_pages, missing_pages, broken_wikilinks, isolated_pages
```

See `lint.md` for the full workflow including contradiction detection and stale claim review.

---

## Best Use Cases

### Research & Investigation
Feed papers, articles, and reports over weeks. The graph grows with each ingest — by week 3, you can ask "what are all the components that transitively affect response time?" and get a multi-hop answer the wiki alone couldn't give you. The LLM Wiki pattern says knowledge "compiles once" — this skill makes the compiled artifact queryable structurally, not just by reading.

### Incident Management / Post-Mortems
Ingest incident reports, runbooks, and Slack threads. The graph accumulates causal chains across incidents. When a new incident happens, `query_with_evidence("what caused similar crashes before?")` returns connected causal chains with citations to the exact incident reports that support each link.

### Competitive Intelligence / Due Diligence
Ingest press releases, SEC filings, and analyst notes. Entity pages for companies, products, and people accumulate cross-references automatically. The graph finds indirect relationships ("Company A uses Vendor B who supplies Component C") that would require reading 15 documents to discover manually.

### Codebase / Technical Documentation
Ingest API docs, architecture decision records, and design docs. Entity types become `service`, `interface`, `component`, `dependency`. The graph answers "what services does X depend on?" via BFS without re-reading all docs every time. Entity pages in the wiki explain each service in natural language, with links to their dependency graph.

### Personal Knowledge Base
Ingest journal entries, book notes, podcast summaries. The pattern is exactly what Karpathy describes for personal use — the difference is that recurring concepts (people, themes, ideas) become graph nodes that accumulate evidence from every ingest, making the connections between disparate sources explicit and queryable.

### Team Wiki Maintenance
Feed Slack threads, meeting transcripts, and project documents. The LLM maintains the wiki so no human has to. The graph means "what does Team X own that depends on the auth service?" is a graph query, not a wiki reading exercise. The log.md gives a timeline of what changed when.

---

## Configuration

```python
# scripts/config.py
MAX_GRAPH_DEPTH = 2    # BFS depth during retrieval
MIN_CONFIDENCE  = 0.6  # Minimum edge confidence included in retrieval
MAX_NODES       = 50   # Max nodes returned in a subgraph
```

### Data directory

`data/` and `wiki/` are **not included in this repo**. The skill creates them on first write, in the directory you configure. They belong to the consuming project, not to the skill package.

| Env var | Default | Purpose |
|---------|---------|---------|
| `MINI_CONTEXT_GRAPH_BASE` | `cwd` | Base directory; sets both `data/` and `wiki/` relative to it |
| `MINI_CONTEXT_GRAPH_DATA_DIR` | `$BASE/data` | Override `data/` location specifically |
| `MINI_CONTEXT_GRAPH_WIKI_DIR` | `$BASE/wiki` | Override `wiki/` location specifically |

```bash
# Example: keep data in your project root, not wherever you invoke Python from
export MINI_CONTEXT_GRAPH_BASE=/path/to/my-project
python3.13 my_agent.py
```

If no env vars are set, data lands in `{cwd}/data` and `{cwd}/wiki` — whichever directory your agent runs from.

---

## Requirements

- Python 3.13
- No external dependencies (stdlib only: `json`, `uuid`, `re`, `collections`, `pathlib`, `datetime`)

---

## Design Rules

- **LLM reasons; Python executes.** No LLM logic in Python. All extraction, synthesis, and wiki writing is guided by the `.md` files.
- **Raw sources are immutable.** `documents.json` is append-only. The ground truth never changes.
- **The wiki compiles once.** Cross-references, contradictions, and syntheses are written during ingest, not re-derived at query time.
- **The graph is incremental.** Append-only, deduplicated by normalized entity name, confidence-filtered.
- **Provenance is mandatory.** Every graph node and edge links back to the source chunk. Answers can always be traced to their evidence.
- **Answers compound.** Valuable query results are filed back into the wiki as topic pages. Future queries hit the wiki fast path.

---

## Current Limitations

### Storage & Scale
- **JSON files only.** All data is stored in flat JSON files. Performance degrades above ~5,000 nodes or ~50,000 edges. For larger corpora, replace `graph_store` with a real graph database (Neo4j, Kuzu).
- **No concurrent writes.** File I/O is not thread-safe. Running two ingests simultaneously will corrupt the JSON. Fine for single-agent use; add file locking for concurrent agents.
- **No delete or update.** The graph and document store are append-only. Correcting a wrong entity or relation requires manually editing the JSON. There is no `remove_node()` or `update_edge()` API yet.

### Search & Retrieval
- **Keyword search only.** Both `index_store.search` and `wiki_store.search_wiki` use token overlap scoring — no embeddings, no semantic similarity. "memory issue" will not match "RAM leak" unless the ontology normalizes them.
- **Entity deduplication is exact-name-only.** "memory leak" and "memory leaks" are treated as two different nodes. Fuzzy or embedding-based deduplication is not implemented.
- **BFS depth is capped at 2.** Relationships more than 2 hops away are invisible to retrieval. Raising `MAX_GRAPH_DEPTH` helps but increases response size; there is no smarter path-scoring.
- **Undirected traversal.** BFS follows edges in both directions regardless of the semantic direction of the relation. "A causes B" and "B causes A" are traversed the same way.

### Ingestion
- **No built-in LLM calls.** `ingest_with_content()` requires the agent to pre-extract entities and relations and pass them in. There is no automatic extraction pipeline — the agent must drive it following `ingestion.md`.
- **Confidence scoring is manual.** The agent assigns confidence scores. There is no automated heuristic or model to validate or calibrate them.
- **Chunk boundaries are character-based.** `documents_store` splits on character count with overlap, not sentence or paragraph boundaries. Chunks may cut mid-sentence.
- **No image or binary support.** Only plain text content can be stored and chunked. PDFs, images, and structured data must be pre-converted to text before ingestion.

### Wiki
- **No cross-reference symmetry enforcement.** If page A links to page B, `lint_wiki` does not verify that page B links back to A. This was noted as a best practice in community implementations of llm-wiki but is not yet implemented.
- **No staleness detection.** There is no automatic check for pages that reference outdated claims from superseded documents. Lint passes rely on the agent to identify stale content manually.
- **`wiki_store.search_wiki` is not used at query time automatically.** The wiki-first retrieval path described in `retrieval.md` must be followed by the agent; nothing enforces it in the Python layer.

