import React, { useState } from 'react';
import { Box, Text, useInput } from 'ink';
import { type ProjectRow } from '../hooks/useProject.js';

interface ProjectSidebarProps {
  projects: ProjectRow[];
  activeProjectId: string | null;
  isFocused: boolean;
  onSelectProject: (id: string) => void;
  onInitNew: () => void;
}

const statusDot = (s: string) => {
  if (s === 'ready') return { char: '●', color: 'green' as const };
  if (s === 'indexing') return { char: '◌', color: 'yellow' as const };
  return { char: '○', color: 'gray' as const };
};

export function ProjectSidebar({
  projects,
  activeProjectId,
  isFocused,
  onSelectProject,
  onInitNew,
}: ProjectSidebarProps) {
  const [cursor, setCursor] = useState(0);

  useInput(
    (input, key) => {
      if (key.upArrow) setCursor((c) => Math.max(0, c - 1));
      if (key.downArrow) setCursor((c) => Math.min(projects.length - 1, c + 1));
      if (key.return && projects[cursor]) onSelectProject(projects[cursor].id);
      if (input === '+' || input === 'n') onInitNew();
    },
    { isActive: isFocused }
  );

  return (
    <Box
      flexDirection="column"
      width={20}
      borderStyle="round"
      borderColor={isFocused ? 'cyan' : 'gray'}
      paddingX={1}
    >
      <Text bold dimColor={!isFocused}>PROJECTS</Text>
      <Text dimColor>{'─'.repeat(16)}</Text>
      {projects.length === 0 && (
        <Text dimColor>{'\n'}No projects.{'\n'}Press [+] to init</Text>
      )}
      {projects.map((p, i) => {
        const isActive = p.id === activeProjectId;
        const isCursor = isFocused && i === cursor;
        const dot = statusDot(p.status);
        const displayName = p.name.length > 14 ? p.name.slice(0, 13) + '…' : p.name;
        return (
          <Box key={p.id} flexDirection="column">
            <Text
              bold={isActive}
              color={isCursor ? 'cyan' : undefined}
              inverse={isCursor}
            >
              <Text color={dot.color}>{dot.char} </Text>
              {displayName}
            </Text>
          </Box>
        );
      })}
      <Box marginTop={1}>
        <Text dimColor>[+] init new</Text>
      </Box>
    </Box>
  );
}
