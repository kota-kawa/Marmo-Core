import { prisma } from '../db';

export interface SearchResult {
  id: string;
  file: string;
  content: string;
  score: number;
  lineStart: number;
  lineEnd: number;
  language: string | null;
  chunkType: string;
  name?: string | null;
  context?: {
    commit?: {
      hash: string;
      author: string;
      message: string;
      date: string;
    };
  };
}

export interface SearchFilters {
  fileType?: string[];
  author?: string;
  dateRange?: {
    from: string;
    to: string;
  };
}

/**
 * Calculate cosine similarity between two vectors
 */
export function cosineSimilarity(vecA: number[], vecB: number[]): number {
  if (vecA.length !== vecB.length) {
    throw new Error('Vectors must have the same length');
  }

  let dotProduct = 0;
  let normA = 0;
  let normB = 0;

  for (let i = 0; i < vecA.length; i++) {
    dotProduct += vecA[i] * vecB[i];
    normA += vecA[i] * vecA[i];
    normB += vecB[i] * vecB[i];
  }

  normA = Math.sqrt(normA);
  normB = Math.sqrt(normB);

  if (normA === 0 || normB === 0) {
    return 0;
  }

  return dotProduct / (normA * normB);
}

/**
 * Search code chunks using vector similarity
 */
export async function searchCodeChunks(
  repositoryId: string,
  queryEmbedding: number[],
  limit: number = 10,
  filters?: SearchFilters
): Promise<SearchResult[]> {
  try {
    // Get all code chunks with embeddings
    const chunks = await prisma.codeChunk.findMany({
      where: {
        repositoryId,
        embedding: {
          not: null,
        },
      },
      include: {
        file: {
          include: {
            repository: true,
          },
        },
      },
    });

    // Calculate similarity scores
    const results: Array<{
      chunk: typeof chunks[0];
      score: number;
    }> = [];

    for (const chunk of chunks) {
      if (!chunk.embedding) continue;

      try {
        const chunkEmbedding = JSON.parse(chunk.embedding) as number[];
        const score = cosineSimilarity(queryEmbedding, chunkEmbedding);

        // Apply filters
        if (filters) {
          // File type filter
          if (filters.fileType && filters.fileType.length > 0) {
            if (!chunk.file.language || !filters.fileType.includes(chunk.file.language)) {
              continue;
            }
          }

          // Author filter
          if (filters.author) {
            if (chunk.file.lastAuthor !== filters.author) {
              continue;
            }
          }

          // Date range filter
          if (filters.dateRange && chunk.file.lastModified) {
            const fileDate = new Date(chunk.file.lastModified);
            const fromDate = new Date(filters.dateRange.from);
            const toDate = new Date(filters.dateRange.to);

            if (fileDate < fromDate || fileDate > toDate) {
              continue;
            }
          }
        }

        results.push({ chunk, score });
      } catch (error) {
        console.error(`Error processing chunk ${chunk.id}:`, error);
      }
    }

    // Sort by score and take top results
    results.sort((a, b) => b.score - a.score);
    const topResults = results.slice(0, limit);

    // Get commit info for results
    const searchResults: SearchResult[] = [];

    for (const { chunk, score } of topResults) {
      // Get the last commit for this file
      const commit = await prisma.commit.findFirst({
        where: {
          repositoryId,
          filesChanged: {
            contains: chunk.file.path,
          },
        },
        orderBy: {
          timestamp: 'desc',
        },
      });

      searchResults.push({
        id: chunk.id,
        file: chunk.file.path,
        content: chunk.content,
        score,
        lineStart: chunk.startLine,
        lineEnd: chunk.endLine,
        language: chunk.file.language,
        chunkType: chunk.chunkType,
        name: chunk.name,
        context: commit
          ? {
              commit: {
                hash: commit.hash,
                author: commit.author,
                message: commit.message,
                date: commit.timestamp.toISOString(),
              },
            }
          : undefined,
      });
    }

    return searchResults;
  } catch (error) {
    console.error('Error searching code chunks:', error);
    return [];
  }
}

/**
 * Search commits using vector similarity
 */
export async function searchCommits(
  repositoryId: string,
  queryEmbedding: number[],
  limit: number = 10
): Promise<Array<{
  hash: string;
  author: string;
  message: string;
  timestamp: Date;
  filesChanged: string[];
  score: number;
}>> {
  try {
    // Get all commits with embeddings
    const commits = await prisma.commit.findMany({
      where: {
        repositoryId,
        embedding: {
          not: null,
        },
      },
    });

    // Calculate similarity scores
    const results: Array<{
      commit: typeof commits[0];
      score: number;
    }> = [];

    for (const commit of commits) {
      if (!commit.embedding) continue;

      try {
        const commitEmbedding = JSON.parse(commit.embedding) as number[];
        const score = cosineSimilarity(queryEmbedding, commitEmbedding);
        results.push({ commit, score });
      } catch (error) {
        console.error(`Error processing commit ${commit.hash}:`, error);
      }
    }

    // Sort by score and take top results
    results.sort((a, b) => b.score - a.score);
    const topResults = results.slice(0, limit);

    return topResults.map(({ commit, score }) => ({
      hash: commit.hash,
      author: commit.author,
      message: commit.message,
      timestamp: commit.timestamp,
      filesChanged: JSON.parse(commit.filesChanged) as string[],
      score,
    }));
  } catch (error) {
    console.error('Error searching commits:', error);
    return [];
  }
}

/**
 * Hybrid search combining code and commit search
 */
export async function hybridSearch(
  repositoryId: string,
  queryEmbedding: number[],
  limit: number = 10,
  filters?: SearchFilters
): Promise<{
  codeResults: SearchResult[];
  commitResults: Array<{
    hash: string;
    author: string;
    message: string;
    timestamp: Date;
    filesChanged: string[];
    score: number;
  }>;
}> {
  const [codeResults, commitResults] = await Promise.all([
    searchCodeChunks(repositoryId, queryEmbedding, limit, filters),
    searchCommits(repositoryId, queryEmbedding, Math.floor(limit / 2)),
  ]);

  return {
    codeResults,
    commitResults,
  };
}

/**
 * Get similar code chunks to a given chunk
 */
export async function findSimilarChunks(
  chunkId: string,
  limit: number = 5
): Promise<SearchResult[]> {
  try {
    // Get the source chunk
    const sourceChunk = await prisma.codeChunk.findUnique({
      where: { id: chunkId },
      include: {
        file: true,
      },
    });

    if (!sourceChunk || !sourceChunk.embedding) {
      return [];
    }

    const sourceEmbedding = JSON.parse(sourceChunk.embedding) as number[];

    // Search for similar chunks
    return searchCodeChunks(
      sourceChunk.repositoryId,
      sourceEmbedding,
      limit + 1 // +1 to exclude the source chunk
    ).then((results) =>
      results.filter((r) => r.id !== chunkId).slice(0, limit)
    );
  } catch (error) {
    console.error('Error finding similar chunks:', error);
    return [];
  }
}

// Made with Bob
