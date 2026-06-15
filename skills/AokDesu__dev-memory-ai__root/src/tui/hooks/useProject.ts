import { useState, useEffect, useCallback } from 'react';
import { prisma } from '../../lib/db.js';

export interface ProjectRow {
  id: string;
  name: string;
  status: string;
  path: string;
  gitRemote: string | null;
  lastIndexed: Date | null;
}

export function useProject() {
  const [projects, setProjects] = useState<ProjectRow[]>([]);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    try {
      const rows = await prisma.repository.findMany({ orderBy: { name: 'asc' } });
      setProjects(rows);
    } catch {
      setProjects([]);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  return { projects, loading, refetch: load };
}
