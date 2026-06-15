import React from 'react';
import { Box, Text } from 'ink';
import { useWatch } from '../hooks/useWatch.js';
import { type ProjectRow } from '../hooks/useProject.js';

interface WatchPaneProps {
  project: ProjectRow | null;
}

const typeIcon = (t: string) => {
  if (t === 'change') return { char: '↻', color: 'cyan' as const };
  if (t === 'add') return { char: '+', color: 'green' as const };
  return { char: '✗', color: 'red' as const };
};

export function WatchPane({ project }: WatchPaneProps) {
  const { events, isWatching } = useWatch(project?.id ?? null);

  const rows = process.stdout.rows ?? 24;
  const visible = events.slice(-(rows - 8));

  return (
    <Box flexDirection="column" flexGrow={1} padding={1} gap={1}>
      <Box gap={2}>
        <Text bold>File Watcher</Text>
        {isWatching
          ? <Text color="green">● watching</Text>
          : <Text color="yellow">○ starting…</Text>
        }
        {project && <Text dimColor>{project.path}</Text>}
      </Box>

      {!project && (
        <Text dimColor>No project selected.</Text>
      )}

      {project && events.length === 0 && (
        <Text dimColor>Waiting for file changes…</Text>
      )}

      <Box flexDirection="column">
        {visible.map((evt, i) => {
          const icon = typeIcon(evt.type);
          return (
            <Box key={i} gap={1}>
              <Text dimColor>{evt.time}</Text>
              <Text color={icon.color}>{icon.char}</Text>
              <Text color={evt.status === 'error' ? 'red' : undefined}>{evt.file}</Text>
              {evt.status === 'error' && evt.message && (
                <Text color="red" dimColor>— {evt.message}</Text>
              )}
            </Box>
          );
        })}
      </Box>
    </Box>
  );
}
