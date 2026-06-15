import { useState, useEffect } from 'react';
import { getEmbeddings } from '../../lib/llm.js';
import { searchCodeChunks, type SearchResult } from '../../lib/search/vector-search.js';

export function useSearch(projectId: string | null) {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState<SearchResult[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!projectId || query.length < 2) {
      setResults([]);
      return;
    }

    setLoading(true);
    setError(null);

    const t = setTimeout(async () => {
      try {
        const emb = await getEmbeddings(query);
        const res = await searchCodeChunks(projectId, emb, 10);
        setResults(res);
      } catch (err) {
        setError(err instanceof Error ? err.message : String(err));
      } finally {
        setLoading(false);
      }
    }, 400);

    return () => clearTimeout(t);
  }, [query, projectId]);

  return { query, setQuery, results, loading, error };
}
