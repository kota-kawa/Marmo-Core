import React from 'react';
import { Box, Text } from 'ink';

type Tab = 'ask' | 'search' | 'status' | 'watch' | 'init';

const TABS: Tab[] = ['ask', 'search', 'status', 'watch'];

interface TabBarProps {
  activeTab: Tab | string;
}

export function TabBar({ activeTab }: TabBarProps) {
  return (
    <Box gap={2} paddingX={1} paddingY={0} borderStyle="single" borderColor="gray">
      {TABS.map((tab) => (
        <Text
          key={tab}
          bold={activeTab === tab}
          color={activeTab === tab ? 'cyan' : undefined}
          dimColor={activeTab !== tab}
        >
          {activeTab === tab ? `[${tab}]` : tab}
        </Text>
      ))}
      {activeTab === 'init' && (
        <Text bold color="yellow">[init]</Text>
      )}
    </Box>
  );
}
