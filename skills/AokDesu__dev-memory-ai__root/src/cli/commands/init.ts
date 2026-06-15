import { Command } from 'commander';
import path from 'path';
import { prisma } from '../../lib/db.js';
import { indexRepository, type ProgressCallback } from '../../lib/indexer/file-indexer.js';
import { isGitRepository, getGitRemote, getRepositoryName } from '../../lib/filesystem.js';
import { writeConfig } from '../config.js';
import { spinner, printSuccess, printError, c } from '../output.js';

export const initCmd = new Command('init')
  .description('Index a repository so AI tools can understand it')
  .argument('[path]', 'Repository path (defaults to current directory)')
  .option('--name <name>', 'Project name (defaults to directory name)')
  .option('--force', 'Re-index even if already indexed')
  .action(async (repoPath?: string, opts: { name?: string; force?: boolean } = {}) => {
    const targetPath = path.resolve(repoPath ?? process.cwd());

    // Validate git repo
    const isGit = await isGitRepository(targetPath);
    if (!isGit) {
      printError(`Not a git repository: ${targetPath}`);
      process.exit(1);
    }

    const gitRemote = await getGitRemote(targetPath);
    const name = opts.name ?? getRepositoryName(targetPath);

    // Check if already indexed
    const existing = await prisma.repository.findUnique({ where: { path: targetPath } });
    if (existing && existing.status === 'ready' && !opts.force) {
      printSuccess(`Already indexed: ${c.bold(existing.name)} (${existing.id})`);
      console.log(c.dim('  Use --force to re-index'));
      process.exit(0);
    }

    // Upsert repository record
    const repo = existing
      ? await prisma.repository.update({
          where: { id: existing.id },
          data: { name, gitRemote, status: 'pending', lastIndexed: null },
        })
      : await prisma.repository.create({
          data: { path: targetPath, name, gitRemote, status: 'pending' },
        });

    // Write .memory-dev.json
    writeConfig(targetPath, { projectId: repo.id, name, path: targetPath, gitRemote });

    // Start indexing with progress spinner
    const spin = spinner(`Indexing ${c.bold(name)}…`);
    let lastFile = '';

    const onProgress: ProgressCallback = (p) => {
      lastFile = p.currentFile;
      spin.text = `Indexing ${c.bold(name)}… ${c.dim(p.processedFiles + '/' + p.totalFiles)} ${c.dim(path.basename(p.currentFile))}`;
    };

    try {
      await indexRepository(repo.id, targetPath, onProgress);
      spin.succeed(`Indexed ${c.bold(name)}`);

      // Print stats
      const [files, chunks] = await Promise.all([
        prisma.file.count({ where: { repositoryId: repo.id } }),
        prisma.codeChunk.count({ where: { repositoryId: repo.id } }),
      ]);

      console.log(c.dim(`  ${files} files · ${chunks} code chunks · id: ${repo.id}`));
      console.log('');
      console.log(c.bold('Next: connect Claude Code'));
      console.log(c.dim('  Add to .claude/mcp.json:'));
      console.log(c.dim('  { "mcpServers": { "memory-dev": { "command": "memory-dev", "args": ["mcp"] } } }'));
    } catch (err) {
      spin.fail('Indexing failed');
      printError(err instanceof Error ? err.message : String(err));
      process.exit(1);
    } finally {
      await prisma.$disconnect();
    }
  });
