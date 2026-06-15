#!/usr/bin/env node
/**
 * Memory.dev MCP Server
 *
 * Connects Claude Code to your locally-indexed codebase.
 * Register in .claude/mcp.json:
 *   {
 *     "mcpServers": {
 *       "memory-dev": { "command": "memory-dev", "args": ["mcp"] }
 *     }
 *   }
 */

import { Server } from '@modelcontextprotocol/sdk/server/index.js';
import { StdioServerTransport } from '@modelcontextprotocol/sdk/server/stdio.js';
import {
  CallToolRequestSchema,
  ListToolsRequestSchema,
} from '@modelcontextprotocol/sdk/types.js';
import { readFileSync } from 'fs';
import path from 'path';
import { queryRAG } from './src/lib/rag/rag-chain.js';
import { getEmbeddings } from './src/lib/llm.js';
import { searchCodeChunks } from './src/lib/search/vector-search.js';
import { prisma } from './src/lib/db.js';

let resolvedProjectId: string | null = process.env.MEMORY_PROJECT_ID ?? null;

async function resolveProjectId(): Promise<string> {
  if (resolvedProjectId) return resolvedProjectId;

  // Parse .git/config for origin remote URL (no child_process)
  let gitRemote: string | null = null;
  try {
    const config = readFileSync(path.join(process.cwd(), '.git', 'config'), 'utf-8');
    const m = config.match(/\[remote "origin"\][\s\S]*?\n\s*url\s*=\s*(.+)/);
    if (m) gitRemote = m[1].trim();
  } catch { /* not a git repo */ }

  // Try .memory-dev.json first
  try {
    const cfg = JSON.parse(readFileSync(path.join(process.cwd(), '.memory-dev.json'), 'utf-8'));
    if (cfg?.projectId) {
      resolvedProjectId = cfg.projectId;
      return resolvedProjectId as string;
    }
  } catch { /* no config file */ }

  // Fall back to DB lookup by gitRemote or directory name
  const cwd = process.cwd();
  const dirName = path.basename(cwd);

  let repo = null;
  if (gitRemote) {
    repo = await prisma.repository.findFirst({ where: { gitRemote } });
  }
  if (!repo) {
    const candidates = await prisma.repository.findMany({ where: { name: dirName } });
    repo = candidates[0] ?? null;
  }
  if (!repo) {
    repo = await prisma.repository.findFirst({ where: { path: cwd } });
  }

  if (!repo) {
    throw new Error(
      `Could not auto-detect project for this workspace.\n` +
      `Run: memory-dev init\n` +
      `Or set MEMORY_PROJECT_ID in your MCP config.`
    );
  }

  resolvedProjectId = repo.id;
  return resolvedProjectId;
}

const server = new Server(
  { name: 'memory-dev', version: '1.0.0' },
  { capabilities: { tools: {} } }
);

server.setRequestHandler(ListToolsRequestSchema, async () => ({
  tools: [
    {
      name: 'memory_ask',
      description:
        'Ask a natural-language question about the codebase and get an AI-generated answer with source citations. ' +
        'Use when you need to understand how a feature works, what a function does, or why something is designed a certain way.',
      inputSchema: {
        type: 'object',
        properties: {
          question: { type: 'string', description: 'The question to ask about the codebase' },
          projectId: { type: 'string', description: 'Project ID (auto-detected if omitted)' },
          maxResults: { type: 'number', description: 'Number of source chunks to retrieve (1-20, default 5)' },
        },
        required: ['question'],
      },
    },
    {
      name: 'memory_search',
      description:
        'Semantic search for code chunks related to a concept or keyword. ' +
        'Use when looking for specific implementations, finding where a pattern is used, or locating code related to a concept.',
      inputSchema: {
        type: 'object',
        properties: {
          query: { type: 'string', description: 'Search query (natural language or code fragment)' },
          projectId: { type: 'string', description: 'Project ID (auto-detected if omitted)' },
          maxResults: { type: 'number', description: 'Maximum results to return (1-20, default 5)' },
        },
        required: ['query'],
      },
    },
    {
      name: 'memory_projects',
      description: 'List all indexed projects. Use to discover available projects and their IDs.',
      inputSchema: { type: 'object', properties: {} },
    },
    {
      name: 'memory_file_tree',
      description:
        'Get the directory structure of a project. ' +
        'Use first to understand project layout before diving into specific files.',
      inputSchema: {
        type: 'object',
        properties: {
          projectId: { type: 'string', description: 'Project ID (auto-detected if omitted)' },
        },
      },
    },
  ],
}));

server.setRequestHandler(CallToolRequestSchema, async (request) => {
  const { name, arguments: args = {} } = request.params;
  const a = args as Record<string, unknown>;

  try {
    switch (name) {
      case 'memory_ask': {
        const projectId = (a.projectId as string | undefined) ?? await resolveProjectId();
        const result = await queryRAG(projectId, a.question as string, (a.maxResults as number | undefined) ?? 5);

        const sourcesText = result.sources
          .map(
            (s) =>
              `**${s.file}** (lines ${s.lines[0]}–${s.lines[1]}, ${(s.score * 100).toFixed(0)}% match)\n\`\`\`\n${s.content}\n\`\`\``
          )
          .join('\n\n');

        return {
          content: [
            {
              type: 'text',
              text: sourcesText
                ? `${result.answer}\n\n---\n**Sources:**\n\n${sourcesText}`
                : result.answer,
            },
          ],
        };
      }

      case 'memory_search': {
        const projectId = (a.projectId as string | undefined) ?? await resolveProjectId();
        const embedding = await getEmbeddings(a.query as string);
        const results = await searchCodeChunks(projectId, embedding, (a.maxResults as number | undefined) ?? 5);

        if (results.length === 0) {
          return { content: [{ type: 'text', text: 'No results found.' }] };
        }

        const text = results
          .map(
            (r, i) =>
              `**${i + 1}. ${r.file}** (lines ${r.lineStart}–${r.lineEnd}, ${(r.score * 100).toFixed(0)}% match)\n\`\`\`\n${r.content}\n\`\`\``
          )
          .join('\n\n');

        return { content: [{ type: 'text', text }] };
      }

      case 'memory_projects': {
        const repos = await prisma.repository.findMany({ orderBy: { name: 'asc' } });

        const list = repos
          .map(
            (r) =>
              `- **${r.name}** (id: \`${r.id}\`, status: ${r.status}${r.lastIndexed ? `, indexed ${r.lastIndexed.toLocaleDateString()}` : ''})\n  ${r.path}`
          )
          .join('\n');

        return {
          content: [
            {
              type: 'text',
              text: repos.length > 0
                ? `Found ${repos.length} project(s):\n\n${list}`
                : 'No projects indexed yet. Run: memory-dev init',
            },
          ],
        };
      }

      case 'memory_file_tree': {
        const projectId = (a.projectId as string | undefined) ?? await resolveProjectId();
        const files = await prisma.file.findMany({
          where: { repositoryId: projectId },
          select: { path: true },
          orderBy: { path: 'asc' },
        });

        const repo = await prisma.repository.findUnique({ where: { id: projectId } });

        // Build tree structure
        const tree: Record<string, unknown> = {};
        for (const f of files) {
          const parts = f.path.split('/');
          let node = tree;
          for (let i = 0; i < parts.length - 1; i++) {
            if (!node[parts[i]]) node[parts[i]] = {};
            node = node[parts[i]] as Record<string, unknown>;
          }
          node[parts[parts.length - 1]] = null;
        }

        return {
          content: [
            {
              type: 'text',
              text: `**${repo?.name ?? projectId}** — ${files.length} files\n\n\`\`\`json\n${JSON.stringify(tree, null, 2)}\n\`\`\``,
            },
          ],
        };
      }

      default:
        throw new Error(`Unknown tool: ${name}`);
    }
  } catch (error) {
    const msg = error instanceof Error ? error.message : String(error);
    return {
      content: [{ type: 'text', text: `Error: ${msg}` }],
      isError: true,
    };
  }
});

const transport = new StdioServerTransport();
await server.connect(transport);
