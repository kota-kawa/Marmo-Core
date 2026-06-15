import { Command } from 'commander';
import path from 'path';
import { prisma } from '../../lib/db.js';
import { readConfig } from '../config.js';
import { printError, printSuccess, c } from '../output.js';

const IGNORED = ['node_modules', '.git', '.next', 'dist', 'build', 'out', 'coverage', '__pycache__'];

export const watchCmd = new Command('watch')
  .description('Watch for file changes and re-index automatically')
  .option('-p, --project <id>', 'Project ID (auto-detected)')
  .action(async (opts: { project?: string }) => {
    const cfg = readConfig();
    const projectId = opts.project ?? cfg?.projectId;
    if (!projectId) {
      printError('No project found. Run: memory-dev init');
      process.exit(1);
    }

    const repo = await prisma.repository.findUnique({ where: { id: projectId } });
    if (!repo) {
      printError(`Project not found: ${projectId}`);
      process.exit(1);
    }

    // Dynamic import — chokidar is ESM
    const { default: chokidar } = await import('chokidar');
    // Dynamic import of incremental indexer
    const { indexSingleFile } = await import('../../lib/indexer/file-indexer.js');

    const watcher = chokidar.watch(repo.path, {
      ignored: (p: string) => IGNORED.some((d) => p.includes(path.sep + d + path.sep) || p.endsWith(path.sep + d)),
      ignoreInitial: true,
      persistent: true,
    });

    console.log(c.bold(`Watching ${repo.name}`) + c.dim(' (Ctrl+C to stop)'));

    const handle = async (filePath: string) => {
      const rel = path.relative(repo.path, filePath);
      try {
        await indexSingleFile(projectId, repo.path, rel);
        console.log(c.dim('↻ ') + c.accent(rel));
      } catch (err) {
        console.log(c.error('✖ ') + rel + c.dim(' — ' + (err instanceof Error ? err.message : String(err))));
      }
    };

    watcher.on('add', handle);
    watcher.on('change', handle);
    watcher.on('unlink', async (filePath: string) => {
      const rel = path.relative(repo.path, filePath);
      await prisma.file.deleteMany({ where: { repositoryId: projectId, path: rel } }).catch(() => {});
      console.log(c.dim('✗ ') + c.dim(rel));
    });

    // Keep process alive
    await new Promise(() => {});
  });
