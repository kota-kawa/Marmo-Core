import React, { useState, useCallback } from 'react';
import { Box, Text } from 'ink';
import TextInput from 'ink-text-input';
import path from 'path';
import { prisma } from '../../lib/db.js';
import { indexRepository, type IndexingProgress } from '../../lib/indexer/file-indexer.js';
import { isGitRepository, getGitRemote, getRepositoryName } from '../../lib/filesystem.js';
import { writeConfig } from '../../cli/config.js';

interface InitPaneProps {
  onComplete: (projectId: string) => void;
}

type Phase = 'input' | 'indexing' | 'done' | 'error';

function progressBar(pct: number): string {
  const filled = Math.round(pct / 5);
  return '█'.repeat(filled) + '░'.repeat(20 - filled) + ` ${pct.toFixed(0)}%`;
}

export function InitPane({ onComplete }: InitPaneProps) {
  const [repoPath, setRepoPath] = useState(process.cwd());
  const [phase, setPhase] = useState<Phase>('input');
  const [progress, setProgress] = useState<IndexingProgress | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [projectId, setProjectId] = useState<string | null>(null);

  const handleSubmit = useCallback(async (val: string) => {
    const targetPath = path.resolve(val || process.cwd());
    setPhase('indexing');
    setError(null);

    try {
      const isGit = await isGitRepository(targetPath);
      if (!isGit) {
        setError(`Not a git repository: ${targetPath}`);
        setPhase('error');
        return;
      }

      const [gitRemote, name] = await Promise.all([
        getGitRemote(targetPath),
        Promise.resolve(getRepositoryName(targetPath)),
      ]);

      const existing = await prisma.repository.findUnique({ where: { path: targetPath } });
      const repo = existing
        ? await prisma.repository.update({
            where: { id: existing.id },
            data: { name, gitRemote, status: 'pending' },
          })
        : await prisma.repository.create({
            data: { path: targetPath, name, gitRemote, status: 'pending' },
          });

      writeConfig(targetPath, { projectId: repo.id, name, path: targetPath, gitRemote });
      setProjectId(repo.id);

      await indexRepository(repo.id, targetPath, (p) => setProgress({ ...p }));
      setPhase('done');
      setTimeout(() => onComplete(repo.id), 1500);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
      setPhase('error');
    }
  }, [onComplete]);

  return (
    <Box flexDirection="column" flexGrow={1} padding={2} gap={1}>
      <Text bold>Initialize Project</Text>
      <Text dimColor>Index a git repository so AI tools can understand it.</Text>

      {phase === 'input' && (
        <Box borderStyle="round" borderColor="cyan" paddingX={1} marginTop={1}>
          <Text color="cyan">path: </Text>
          <TextInput
            value={repoPath}
            onChange={setRepoPath}
            onSubmit={handleSubmit}
            focus={true}
            placeholder={process.cwd()}
          />
        </Box>
      )}

      {phase === 'indexing' && (
        <Box flexDirection="column" gap={1} marginTop={1}>
          <Box gap={2}>
            <Text color="yellow">⟳ Indexing</Text>
            <Text>{progress?.currentFile ? path.basename(progress.currentFile) : '…'}</Text>
          </Box>
          {progress && (
            <>
              <Text color="yellow">{progressBar(progress.progress)}</Text>
              <Text dimColor>{progress.processedFiles} / {progress.totalFiles} files</Text>
            </>
          )}
        </Box>
      )}

      {phase === 'done' && (
        <Box flexDirection="column" gap={1} marginTop={1}>
          <Text color="green">✔ Indexed successfully</Text>
          {projectId && <Text dimColor>id: {projectId}</Text>}
          <Text dimColor>Switching to Ask tab…</Text>
        </Box>
      )}

      {phase === 'error' && (
        <Box flexDirection="column" gap={1} marginTop={1}>
          <Text color="red">✖ {error}</Text>
          <Text dimColor>Press Enter to try again.</Text>
          <Box borderStyle="round" borderColor="red" paddingX={1}>
            <Text color="cyan">path: </Text>
            <TextInput
              value={repoPath}
              onChange={setRepoPath}
              onSubmit={handleSubmit}
              focus={true}
            />
          </Box>
        </Box>
      )}
    </Box>
  );
}
