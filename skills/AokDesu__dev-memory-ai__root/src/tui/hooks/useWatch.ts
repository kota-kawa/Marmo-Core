import { useState, useEffect, useRef } from 'react';
import path from 'path';
import { indexSingleFile } from '../../lib/indexer/file-indexer.js';
import { prisma } from '../../lib/db.js';

export interface WatchEvent {
  time: string;
  file: string;
  type: 'add' | 'change' | 'unlink';
  status: 'ok' | 'error';
  message?: string;
}

const IGNORED = ['node_modules', '.git', '.next', 'dist', 'build', 'out', 'coverage'];

export function useWatch(projectId: string | null) {
  const [events, setEvents] = useState<WatchEvent[]>([]);
  const [isWatching, setIsWatching] = useState(false);
  const [repoPath, setRepoPath] = useState<string | null>(null);
  const watcherRef = useRef<{ close(): Promise<void> } | null>(null);

  useEffect(() => {
    if (!projectId) return;
    prisma.repository
      .findUnique({ where: { id: projectId } })
      .then((r) => setRepoPath(r?.path ?? null))
      .catch(() => {});
  }, [projectId]);

  useEffect(() => {
    if (!projectId || !repoPath) return;

    let mounted = true;

    (async () => {
      const { default: chokidar } = await import('chokidar');

      const watcher = chokidar.watch(repoPath, {
        ignored: (p: string) =>
          IGNORED.some(
            (d) => p.includes(path.sep + d + path.sep) || p.endsWith(path.sep + d)
          ),
        ignoreInitial: true,
        persistent: true,
      });

      watcherRef.current = watcher;
      if (mounted) setIsWatching(true);

      const push = (evt: WatchEvent) => {
        if (mounted)
          setEvents((prev) => [...prev.slice(-199), evt]);
      };

      const handle = async (filePath: string, type: 'add' | 'change' | 'unlink') => {
        const rel = path.relative(repoPath, filePath);
        const time = new Date().toLocaleTimeString();
        if (type === 'unlink') {
          await prisma.file
            .deleteMany({ where: { repositoryId: projectId, path: rel } })
            .catch(() => {});
          push({ time, file: rel, type, status: 'ok' });
          return;
        }
        try {
          await indexSingleFile(projectId, repoPath, rel);
          push({ time, file: rel, type, status: 'ok' });
        } catch (err) {
          push({
            time,
            file: rel,
            type,
            status: 'error',
            message: err instanceof Error ? err.message : String(err),
          });
        }
      };

      watcher.on('add', (p) => handle(p, 'add'));
      watcher.on('change', (p) => handle(p, 'change'));
      watcher.on('unlink', (p) => handle(p, 'unlink'));
    })();

    return () => {
      mounted = false;
      setIsWatching(false);
      watcherRef.current?.close().catch(() => {});
      watcherRef.current = null;
    };
  }, [projectId, repoPath]);

  return { events, isWatching };
}
