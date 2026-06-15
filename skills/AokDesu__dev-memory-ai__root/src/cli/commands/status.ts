import { Command } from 'commander';
import { prisma } from '../../lib/db.js';
import { readConfig } from '../config.js';
import { printError, c } from '../output.js';

export const statusCmd = new Command('status')
  .description('Show indexing status for the current project')
  .option('-p, --project <id>', 'Project ID (auto-detected)')
  .option('--all', 'Show all indexed projects')
  .action(async (opts: { project?: string; all?: boolean }) => {
    try {
      if (opts.all) {
        const repos = await prisma.repository.findMany({ orderBy: { name: 'asc' } });
        if (repos.length === 0) {
          console.log(c.dim('No projects indexed yet. Run: memory-dev init'));
          return;
        }
        for (const r of repos) {
          const statusColor =
            r.status === 'ready' ? c.success(r.status)
            : r.status === 'indexing' ? c.warn(r.status)
            : c.error(r.status);
          console.log(`${c.bold(r.name)} ${statusColor}`);
          console.log(c.dim(`  ${r.id}`));
          console.log(c.dim(`  ${r.path}`));
          if (r.lastIndexed) {
            console.log(c.dim(`  Last indexed: ${r.lastIndexed.toLocaleString()}`));
          }
          console.log('');
        }
        return;
      }

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

      const [files, chunks] = await Promise.all([
        prisma.file.count({ where: { repositoryId: projectId } }),
        prisma.codeChunk.count({ where: { repositoryId: projectId } }),
      ]);

      const statusColor =
        repo.status === 'ready' ? c.success(repo.status)
        : repo.status === 'indexing' ? c.warn(repo.status)
        : c.error(repo.status);

      console.log(`${c.bold(repo.name)} ${statusColor}`);
      console.log(c.dim(`  id:       ${repo.id}`));
      console.log(c.dim(`  path:     ${repo.path}`));
      console.log(c.dim(`  files:    ${files}`));
      console.log(c.dim(`  chunks:   ${chunks}`));
      if (repo.lastIndexed) {
        console.log(c.dim(`  indexed:  ${repo.lastIndexed.toLocaleString()}`));
      }
      if (repo.gitRemote) {
        console.log(c.dim(`  remote:   ${repo.gitRemote}`));
      }
    } finally {
      await prisma.$disconnect();
    }
  });
