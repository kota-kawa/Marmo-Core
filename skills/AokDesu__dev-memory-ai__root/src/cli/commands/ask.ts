import { Command } from 'commander';
import { queryRAG } from '../../lib/rag/rag-chain.js';
import { prisma } from '../../lib/db.js';
import { readConfig } from '../config.js';
import { spinner, printSources, printError, c } from '../output.js';

export const askCmd = new Command('ask')
  .description('Ask a question about your codebase')
  .argument('<question>', 'Question to ask')
  .option('-n, --results <n>', 'Number of sources to retrieve', '5')
  .option('-p, --project <id>', 'Project ID (auto-detected from .memory-dev.json)')
  .action(async (question: string, opts: { results: string; project?: string }) => {
    const projectId = opts.project ?? readConfig()?.projectId;
    if (!projectId) {
      printError('No project found. Run: memory-dev init');
      process.exit(1);
    }

    const repo = await prisma.repository.findUnique({ where: { id: projectId } });
    if (!repo) {
      printError(`Project not found: ${projectId}`);
      process.exit(1);
    }
    if (repo.status !== 'ready') {
      printError(`Project not ready (status: ${repo.status}). Run: memory-dev init`);
      process.exit(1);
    }

    const spin = spinner('Thinking…');
    try {
      const result = await queryRAG(projectId, question, parseInt(opts.results, 10));
      spin.stop();

      console.log('');
      console.log(result.answer);
      printSources(
        result.sources.map((s) => ({
          file: s.file,
          lines: s.lines as [number, number],
          content: s.content,
          score: s.score,
        }))
      );
    } catch (err) {
      spin.fail('Query failed');
      printError(err instanceof Error ? err.message : String(err));
      process.exit(1);
    } finally {
      await prisma.$disconnect();
    }
  });
