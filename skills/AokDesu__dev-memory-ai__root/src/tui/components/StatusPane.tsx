import React, { useState, useEffect } from 'react';
import { Box, Text } from 'ink';
import { prisma } from '../../lib/db.js';
import { type ProjectRow } from '../hooks/useProject.js';

interface StatusPaneProps {
  project: ProjectRow | null;
}

interface Stats {
  files: number;
  chunks: number;
  status: string;
  lastIndexed: Date | null;
  indexingProgress: number | null;
}

const statusColor = (s: string) => {
  if (s === 'ready') return 'green';
  if (s === 'indexing') return 'yellow';
  if (s === 'error') return 'red';
  return 'gray';
};

export function StatusPane({ project }: StatusPaneProps) {
  const [stats, setStats] = useState<Stats | null>(null);

  useEffect(() => {
    if (!project) return;

    const load = async () => {
      const [files, chunks, repo, job] = await Promise.all([
        prisma.file.count({ where: { repositoryId: project.id } }),
        prisma.codeChunk.count({ where: { repositoryId: project.id } }),
        prisma.repository.findUnique({ where: { id: project.id } }),
        prisma.indexingJob.findFirst({
          where: { repositoryId: project.id, status: 'running' },
          orderBy: { startedAt: 'desc' },
        }),
      ]);
      setStats({
        files,
        chunks,
        status: repo?.status ?? 'unknown',
        lastIndexed: repo?.lastIndexed ?? null,
        indexingProgress: job?.progress ?? null,
      });
    };

    load().catch(() => {});

    // Poll every 2s when indexing
    const interval = setInterval(() => {
      if (stats?.status === 'indexing') load().catch(() => {});
    }, 2000);

    return () => clearInterval(interval);
  }, [project?.id]);

  if (!project) {
    return (
      <Box flexGrow={1} padding={2}>
        <Text dimColor>No project selected. Use the sidebar to select a project.</Text>
      </Box>
    );
  }

  if (!stats) {
    return (
      <Box flexGrow={1} padding={2}>
        <Text dimColor>Loading…</Text>
      </Box>
    );
  }

  const progressBar = stats.indexingProgress !== null
    ? (() => {
        const pct = Math.round(stats.indexingProgress);
        const filled = Math.round(pct / 5);
        return '█'.repeat(filled) + '░'.repeat(20 - filled) + ` ${pct}%`;
      })()
    : null;

  return (
    <Box flexDirection="column" padding={2} gap={1}>
      <Box gap={2}>
        <Text bold>{project.name}</Text>
        <Text color={statusColor(stats.status)}>{stats.status}</Text>
      </Box>

      {progressBar && (
        <Box>
          <Text color="yellow">{progressBar}</Text>
        </Box>
      )}

      <Box flexDirection="column" gap={0}>
        <Text dimColor>{'─'.repeat(40)}</Text>
        <Box gap={2}>
          <Text dimColor>id:</Text>
          <Text>{project.id}</Text>
        </Box>
        <Box gap={2}>
          <Text dimColor>path:</Text>
          <Text>{project.path}</Text>
        </Box>
        <Box gap={2}>
          <Text dimColor>files:</Text>
          <Text color="cyan">{stats.files}</Text>
        </Box>
        <Box gap={2}>
          <Text dimColor>chunks:</Text>
          <Text color="cyan">{stats.chunks}</Text>
        </Box>
        {stats.lastIndexed && (
          <Box gap={2}>
            <Text dimColor>indexed:</Text>
            <Text>{stats.lastIndexed.toLocaleString()}</Text>
          </Box>
        )}
        {project.gitRemote && (
          <Box gap={2}>
            <Text dimColor>remote:</Text>
            <Text dimColor>{project.gitRemote}</Text>
          </Box>
        )}
      </Box>

      <Box marginTop={1} flexDirection="column">
        <Text dimColor>{'─'.repeat(40)}</Text>
        <Text dimColor>MCP config (.claude/mcp.json):</Text>
        <Text dimColor color="cyan">
          {'{ "mcpServers": { "memory-dev": { "command": "memory-dev", "args": ["mcp"] } } }'}
        </Text>
      </Box>
    </Box>
  );
}
