import { Command } from 'commander';
import { getEmbeddings } from '../../lib/llm.js';
import { searchCodeChunks } from '../../lib/search/vector-search.js';
import { prisma } from '../../lib/db.js';
import { readConfig } from '../config.js';
import { spinner, printError, c } from '../output.js';

export const searchCmd = new Command('search')
  .description('Semantic search for code chunks')
  .argument('<query>', 'Search query')
  .option('-n, --results <n>', 'Number of results', '8')
  .option('-p, --project <id>', 'Project ID (auto-detected)')
  .action(async (query: string, opts: { results: string; project?: string }) => {
    const projectId = opts.project ?? readConfig()?.projectId;
    if (!projectId) {
      printError('No project found. Run: memory-dev init');
      process.exit(1);
    }

    const spin = spinner('Searching…');
    try {
      const embedding = await getEmbeddings(query);
      const results = await searchCodeChunks(projectId, embedding, parseInt(opts.results, 10));
      spin.stop();

      if (results.length === 0) {
        console.log(c.dim('No results found.'));
        return;
      }

      console.log('');
      for (const [i, r] of results.entries()) {
        const pct = (r.score * 100).toFixed(0);
        console.log(
          `${c.dim((i + 1) + '.')} ${c.accent(r.file)}${c.dim(':' + r.lineStart + '-' + r.lineEnd)} ${c.dim('(' + pct + '%)')}`
        );
        if (r.name) console.log(`   ${c.bold(r.name)} ${c.dim('[' + r.chunkType + ']')}`);
        const preview = r.content.split('\n').slice(0, 3).join('\n');
        console.log(c.dim(preview.split('\n').map((l) => '   ' + l).join('\n')));
        console.log('');
      }
    } catch (err) {
      spin.fail('Search failed');
      printError(err instanceof Error ? err.message : String(err));
      process.exit(1);
    } finally {
      await prisma.$disconnect();
    }
  });
