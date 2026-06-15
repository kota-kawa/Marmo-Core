import React, { useState } from 'react';
import { Box, Text, useInput } from 'ink';
import TextInput from 'ink-text-input';
import { useSearch } from '../hooks/useSearch.js';

interface SearchPaneProps {
  projectId: string | null;
  isFocused: boolean;
  onReleaseFocus: () => void;
}

// ink-text-input inserts the raw ESC byte (charCode 27) into the value when Escape
// is pressed. Strip it at the onChange boundary so the query stays clean.
function stripEsc(s: string): string {
  return s.split(String.fromCharCode(27)).join('');
}

export function SearchPane({ projectId, isFocused, onReleaseFocus }: SearchPaneProps) {
  const { query, setQuery, results, loading, error } = useSearch(projectId);
  const [selected, setSelected] = useState(0);

  useInput(
    (_input, key) => {
      if (key.escape) {
        onReleaseFocus();
        return;
      }
      if (key.upArrow) {
        setSelected((s) => Math.max(0, s - 1));
        return;
      }
      if (key.downArrow) {
        setSelected((s) => Math.min(Math.max(0, results.length - 1), s + 1));
        return;
      }
    },
    { isActive: isFocused }
  );

  const rows = process.stdout.rows ?? 24;
  const maxResults = Math.max(3, rows - 14);
  const visible = results.slice(0, maxResults);
  const sel = Math.min(selected, Math.max(0, results.length - 1));

  return (
    <Box flexDirection="column" flexGrow={1} padding={1} gap={1}>
      <Box borderStyle="round" borderColor={isFocused ? 'cyan' : 'gray'} paddingX={1}>
        <Text color="cyan">/ </Text>
        <TextInput
          value={query}
          onChange={(v) => { setQuery(stripEsc(v)); setSelected(0); }}
          onSubmit={() => {}}
          focus={isFocused}
          placeholder="Search code semantically…"
        />
        {loading && <Text color="yellow"> ⟳</Text>}
      </Box>

      {!isFocused && (
        <Text dimColor>Press [→] to focus · type to search</Text>
      )}
      {isFocused && (
        <Text dimColor>Type to search · ↑↓ navigate · Esc release</Text>
      )}

      {error && <Text color="red">{error}</Text>}

      {query.length >= 2 && results.length === 0 && !loading && (
        <Text dimColor>No results.</Text>
      )}

      <Box flexDirection="column">
        {visible.map((r, i) => {
          const isSelected = i === sel;
          const pct = (r.score * 100).toFixed(0);
          return (
            <Box key={r.id} flexDirection="column">
              <Box gap={1}>
                <Text color={isSelected ? 'cyan' : 'gray'}>{isSelected ? '▶' : ' '}</Text>
                <Text color="magenta" bold={isSelected}>{r.file}</Text>
                <Text dimColor>:{r.lineStart}–{r.lineEnd}</Text>
                <Text color={isSelected ? 'cyan' : undefined} dimColor={!isSelected}>({pct}%)</Text>
                {r.name && <Text dimColor>[{r.name}]</Text>}
              </Box>
              {isSelected && r.content && (
                <Box marginLeft={3}>
                  <Text dimColor>
                    {r.content.split('\n').slice(0, 4).join('\n')}
                  </Text>
                </Box>
              )}
            </Box>
          );
        })}
      </Box>
    </Box>
  );
}
