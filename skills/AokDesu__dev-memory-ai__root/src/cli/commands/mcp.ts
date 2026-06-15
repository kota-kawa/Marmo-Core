import { Command } from 'commander';
import { createRequire } from 'module';
import path from 'path';
import { fileURLToPath } from 'url';

export const mcpCmd = new Command('mcp')
  .description('Start the MCP server for Claude Code / AI tool integration')
  .action(async () => {
    // Import and run mcp-server inline (it connects to stdio transport)
    const __dirname = path.dirname(fileURLToPath(import.meta.url));
    const serverPath = path.resolve(__dirname, '../../../mcp-server.ts');
    // Use dynamic import — works with tsx at runtime
    await import(serverPath);
  });
