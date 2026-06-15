import React, { useState } from 'react';
import { Box, Text, useInput } from 'ink';
import TextInput from 'ink-text-input';
import { useAsk } from '../hooks/useAsk.js';

interface AskPaneProps {
  projectId: string | null;
  isFocused: boolean;
  onReleaseFocus: () => void;
}

export function AskPane({ projectId, isFocused, onReleaseFocus }: AskPaneProps) {
  const { query, setQuery, answer, sources, phase, error, submit } = useAsk(projectId);
  const [inputActive, setInputActive] = useState(false);

  // Activate text input when pane gains focus
  useInput(
    (input, key) => {
      if (key.escape) {
        setInputActive(false);
        onReleaseFocus();
        return;
      }
      if (!inputActive && (input || key.return)) {
        setInputActive(true);
      }
    },
    { isActive: isFocused && !inputActive }
  );

  // Catch Escape while typing (TextInput captures keys, this handler stays active)
  useInput(
    (_input, key) => {
      if (key.escape) {
        setInputActive(false);
        onReleaseFocus();
      }
    },
    { isActive: isFocused && inputActive }
  );

  const handleSubmit = (val: string) => {
    if (val.trim()) submit();
    setInputActive(true); // keep input active for follow-up
  };

  const rows = process.stdout.rows ?? 24;
  const answerMaxLines = Math.max(4, rows - 16);
  const answerLines = answer.split('\n').slice(-answerMaxLines);

  return (
    <Box flexDirection="column" flexGrow={1} padding={1} gap={1}>
      {/* Input */}
      <Box borderStyle="round" borderColor={inputActive ? 'cyan' : 'gray'} paddingX={1}>
        <Text color="cyan">&gt; </Text>
        <TextInput
          value={query}
          onChange={(v) => setQuery(v.split(String.fromCharCode(27)).join(''))}
          onSubmit={handleSubmit}
          focus={isFocused && inputActive}
          placeholder="Ask a question about your codebase…"
        />
      </Box>

      {!isFocused && phase === 'idle' && (
        <Text dimColor>Press [→] to focus, then type your question</Text>
      )}

      {/* Thinking indicator */}
      {phase === 'searching' && (
        <Text color="yellow">⟳ Searching codebase…</Text>
      )}

      {/* Answer */}
      {(phase === 'streaming' || phase === 'done') && answer && (
        <Box flexDirection="column" gap={0}>
          <Text dimColor>{'── Answer ' + '─'.repeat(36)}</Text>
          <Text wrap="wrap">{answerLines.join('\n')}</Text>
          {phase === 'streaming' && <Text color="yellow">▌</Text>}
        </Box>
      )}

      {/* Error */}
      {phase === 'error' && error && (
        <Box flexDirection="column">
          <Text dimColor>{'── Error ' + '─'.repeat(37)}</Text>
          <Text color="red">{error}</Text>
        </Box>
      )}

      {/* Sources */}
      {sources.length > 0 && (
        <Box flexDirection="column" gap={0}>
          <Text dimColor>{`── Sources (${sources.length}) ` + '─'.repeat(30)}</Text>
          {sources.map((s, i) => (
            <Box key={i} gap={1}>
              <Text dimColor>{i + 1}.</Text>
              <Text color="magenta">{s.file}</Text>
              <Text dimColor>:{s.lines[0]}–{s.lines[1]}</Text>
              <Text dimColor>({(s.score * 100).toFixed(0)}%)</Text>
            </Box>
          ))}
        </Box>
      )}
    </Box>
  );
}
