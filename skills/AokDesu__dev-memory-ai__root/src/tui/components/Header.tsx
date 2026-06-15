import React from 'react';
import { Box, Text } from 'ink';

interface HeaderProps {
  projectName: string | null;
  projectStatus: string | null;
  chunkCount: number | null;
}

const statusColor = (s: string | null) => {
  if (s === 'ready') return 'green';
  if (s === 'indexing') return 'yellow';
  if (s === 'error') return 'red';
  return 'gray';
};

export function Header({ projectName, projectStatus, chunkCount }: HeaderProps) {
  return (
    <Box borderStyle="round" borderColor="cyan" paddingX={1} marginBottom={0}>
      <Text bold color="cyan">memory-dev</Text>
      {projectName && (
        <>
          <Text dimColor>  │  </Text>
          <Text bold>{projectName}</Text>
          <Text dimColor>  </Text>
          <Text color={statusColor(projectStatus)}>
            {projectStatus ?? 'unknown'}
          </Text>
          {chunkCount !== null && (
            <Text dimColor>  ·  {chunkCount} chunks</Text>
          )}
        </>
      )}
      {!projectName && (
        <Text dimColor>  no project selected</Text>
      )}
    </Box>
  );
}
