import { useState, useCallback } from 'react';
import { queryRAGStream } from '../../lib/rag/rag-chain.js';

interface Source {
  file: string;
  lines: [number, number];
  content: string;
  score: number;
}

type Phase = 'idle' | 'searching' | 'streaming' | 'done' | 'error';

export function useAsk(projectId: string | null) {
  const [query, setQuery] = useState('');
  const [answer, setAnswer] = useState('');
  const [sources, setSources] = useState<Source[]>([]);
  const [phase, setPhase] = useState<Phase>('idle');
  const [error, setError] = useState<string | null>(null);

  const submit = useCallback(async () => {
    if (!projectId || !query.trim()) return;

    setPhase('searching');
    setAnswer('');
    setSources([]);
    setError(null);

    try {
      const { stream, sources: srcs } = await queryRAGStream(projectId, query.trim(), 5);
      setSources(srcs);
      setPhase('streaming');

      for await (const chunk of stream) {
        const text =
          typeof chunk === 'string'
            ? chunk
            : String((chunk as { content?: unknown }).content ?? '');
        if (text) setAnswer((prev) => prev + text);
      }
      setPhase('done');
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
      setPhase('error');
    }
  }, [projectId, query]);

  const reset = useCallback(() => {
    setAnswer('');
    setSources([]);
    setPhase('idle');
    setError(null);
    setQuery('');
  }, []);

  return { query, setQuery, answer, sources, phase, error, submit, reset };
}
