#!/usr/bin/env node
// Load .env.local then .env from CWD (for API keys)
import { existsSync } from 'fs';
import { resolve } from 'path';
const envFiles = ['.env.local', '.env'];
for (const f of envFiles) {
  const p = resolve(process.cwd(), f);
  if (existsSync(p)) {
    const { config } = await import('dotenv');
    config({ path: p });
    break;
  }
}

import { program } from 'commander';
import { initCmd } from './src/cli/commands/init.js';
import { askCmd } from './src/cli/commands/ask.js';
import { searchCmd } from './src/cli/commands/search.js';
import { watchCmd } from './src/cli/commands/watch.js';
import { statusCmd } from './src/cli/commands/status.js';
import { mcpCmd } from './src/cli/commands/mcp.js';

program
  .name('memory-dev')
  .description('AI-powered semantic memory for your codebase')
  .version('1.0.0');

program.addCommand(initCmd);
program.addCommand(askCmd);
program.addCommand(searchCmd);
program.addCommand(watchCmd);
program.addCommand(statusCmd);
program.addCommand(mcpCmd);

// No subcommand → launch TUI dashboard
const args = process.argv.slice(2);
if (args.length === 0) {
  // Suppress lib-level console output that corrupts TUI rendering
  const origLog = console.log;
  const origError = console.error;
  const origWarn = console.warn;
  console.log = () => {};
  console.error = () => {};
  console.warn = () => {};
  process.env.MEMORY_DEV_TUI = '1';

  const { render, Text } = await import('ink');
  const { createElement } = await import('react');
  const { App } = await import('./src/tui/App.js');

  const { waitUntilExit } = render(createElement(App, {}));
  await waitUntilExit();

  console.log = origLog;
  console.error = origError;
  console.warn = origWarn;
  process.exit(0);
} else {
  program.parse();
}
