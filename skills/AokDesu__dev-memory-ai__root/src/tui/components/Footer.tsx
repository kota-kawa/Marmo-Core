import React from 'react';
import { Box, Text } from 'ink';

interface FooterProps {
  sidebarFocused: boolean;
  activeTab: string;
  inputFocused: boolean;
}

export function Footer({ sidebarFocused, activeTab, inputFocused }: FooterProps) {
  return (
    <Box borderStyle="single" borderColor="gray" paddingX={1} marginTop={0}>
      {inputFocused ? (
        <Text dimColor>[Enter] Submit  [Esc] Release focus  [Ctrl+C] Quit</Text>
      ) : sidebarFocused ? (
        <Text dimColor>[↑↓] Navigate  [Enter] Select  [+] Init new  [→] Pane  [q] Quit</Text>
      ) : (
        <Text dimColor>
          [Tab] Next tab
          {'  '}[←] Sidebar
          {activeTab === 'watch' ? '' : '  [type] Input'}
          {'  '}[q] Quit
        </Text>
      )}
    </Box>
  );
}
