import { ChatPromptTemplate } from '@langchain/core/prompts';
import { StringOutputParser } from '@langchain/core/output_parsers';
import { RunnableSequence } from '@langchain/core/runnables';
import { getLLM } from '../llm';
import { searchCodeChunks, SearchResult } from '../search/vector-search';
import { getEmbeddings } from '../llm';

export interface RAGContext {
  query: string;
  results: SearchResult[];
  repositoryId: string;
}

export interface RAGResponse {
  answer: string;
  sources: Array<{
    file: string;
    lines: [number, number];
    content: string;
    score: number;
  }>;
  context: string;
}

/**
 * Format search results into context for the LLM
 */
function formatContext(results: SearchResult[]): string {
  if (results.length === 0) {
    return 'No relevant code found in the repository.';
  }

  const contextParts = results.map((result, index) => {
    const commitInfo = result.context?.commit
      ? `\nLast modified by: ${result.context.commit.author} (${result.context.commit.date})\nCommit: ${result.context.commit.message}`
      : '';

    return `
[Source ${index + 1}] ${result.file} (lines ${result.lineStart}-${result.lineEnd})${commitInfo}
Language: ${result.language || 'unknown'}
Relevance: ${(result.score * 100).toFixed(1)}%

\`\`\`${result.language || ''}
${result.content}
\`\`\`
`;
  });

  return contextParts.join('\n---\n');
}

/**
 * Create RAG prompt template
 */
function createRAGPrompt() {
  const template = `You are an AI assistant helping developers understand their codebase. You have access to the repository's code and commit history.

Context from the repository:
{context}

User Question: {question}

Instructions:
1. Answer the question based ONLY on the provided context
2. If the context doesn't contain enough information, say so clearly
3. Reference specific files and line numbers when relevant
4. Explain code functionality in clear, simple terms
5. If you mention code from the context, cite the source number [Source X]
6. Be concise but thorough

Answer:`;

  return ChatPromptTemplate.fromTemplate(template);
}

/**
 * Build RAG chain for answering questions
 */
export async function createRAGChain() {
  const llm = getLLM({ temperature: 0 });
  const prompt = createRAGPrompt();
  const outputParser = new StringOutputParser();

  const chain = RunnableSequence.from([
    prompt,
    llm,
    outputParser,
  ]);

  return chain;
}

/**
 * Query the RAG system
 */
export async function queryRAG(
  repositoryId: string,
  question: string,
  limit: number = 5
): Promise<RAGResponse> {
  try {
    // Generate embedding for the question
    const queryEmbedding = await getEmbeddings(question);

    // Search for relevant code
    const results = await searchCodeChunks(repositoryId, queryEmbedding, limit);

    // Format context
    const context = formatContext(results);

    // Create and invoke RAG chain
    const chain = await createRAGChain();
    const answer = await chain.invoke({
      context,
      question,
    });

    // Format sources
    const sources = results.map((result) => ({
      file: result.file,
      lines: [result.lineStart, result.lineEnd] as [number, number],
      content: result.content,
      score: result.score,
    }));

    return {
      answer,
      sources,
      context,
    };
  } catch (error) {
    console.error('RAG query error:', error);
    throw new Error(`Failed to query RAG system: ${error instanceof Error ? error.message : 'Unknown error'}`);
  }
}

/**
 * Query RAG with streaming support
 */
export async function queryRAGStream(
  repositoryId: string,
  question: string,
  limit: number = 5
): Promise<{
  stream: AsyncIterable<{ content: unknown } | string>;
  sources: Array<{
    file: string;
    lines: [number, number];
    content: string;
    score: number;
  }>;
}> {
  try {
    // Generate embedding for the question
    const queryEmbedding = await getEmbeddings(question);

    // Search for relevant code
    const results = await searchCodeChunks(repositoryId, queryEmbedding, limit);

    // Format context
    const context = formatContext(results);

    // Create RAG chain with streaming
    const llm = getLLM({ temperature: 0 });
    const prompt = createRAGPrompt();

    const formattedPrompt = await prompt.format({
      context,
      question,
    });

    // Get streaming response
    const stream = await llm.stream(formattedPrompt);

    // Format sources
    const sources = results.map((result) => ({
      file: result.file,
      lines: [result.lineStart, result.lineEnd] as [number, number],
      content: result.content,
      score: result.score,
    }));

    return {
      stream,
      sources,
    };
  } catch (error) {
    console.error('RAG stream error:', error);
    throw new Error(`Failed to stream RAG response: ${error instanceof Error ? error.message : 'Unknown error'}`);
  }
}

/**
 * Generate a summary of the repository
 */
// export async function generateRepositorySummary(
//   repositoryId: string
// ): Promise<string> {
//   try {
//     const llm = getLLM({ temperature: 0.3 });
//
//     const sampleChunks = await searchCodeChunks(
//       repositoryId,
//       await getEmbeddings('main entry point configuration setup'),
//       10
//     );
//
//     const context = formatContext(sampleChunks);
//
//     const prompt = `Based on the following code samples from a repository, provide a concise summary of the project:
//
// ${context}
//
// Provide a summary that includes:
// 1. What the project does (main purpose)
// 2. Key technologies and frameworks used
// 3. Main components or modules
// 4. Architecture overview (if apparent)
//
// Keep the summary concise (3-5 paragraphs).
//
// Summary:`;
//
//     const summary = await llm.invoke(prompt);
//
//     return typeof summary === 'string' ? summary : summary.content.toString();
//   } catch (error) {
//     console.error('Repository summary error:', error);
//     throw new Error(`Failed to generate repository summary: ${error instanceof Error ? error.message : 'Unknown error'}`);
//   }
// }

/**
 * Answer a question with conversation history
 */
export async function queryRAGWithHistory(
  repositoryId: string,
  question: string,
  conversationHistory: Array<{ role: 'user' | 'assistant'; content: string }>,
  limit: number = 5
): Promise<RAGResponse> {
  try {
    // Generate embedding for the question
    const queryEmbedding = await getEmbeddings(question);

    // Search for relevant code
    const results = await searchCodeChunks(repositoryId, queryEmbedding, limit);

    // Format context
    const context = formatContext(results);

    // Format conversation history
    const historyText = conversationHistory
      .map((msg) => `${msg.role === 'user' ? 'User' : 'Assistant'}: ${msg.content}`)
      .join('\n\n');

    // Create prompt with history
    const template = `You are an AI assistant helping developers understand their codebase. You have access to the repository's code and commit history.

Previous conversation:
${historyText}

Context from the repository:
{context}

Current Question: {question}

Instructions:
1. Consider the conversation history when answering
2. Answer based ONLY on the provided context
3. Reference specific files and line numbers when relevant
4. Cite sources using [Source X] notation
5. Be concise but thorough

Answer:`;

    const prompt = ChatPromptTemplate.fromTemplate(template);
    const llm = getLLM({ temperature: 0 });
    const outputParser = new StringOutputParser();

    const chain = RunnableSequence.from([prompt, llm, outputParser]);

    const answer = await chain.invoke({
      context,
      question,
    });

    // Format sources
    const sources = results.map((result) => ({
      file: result.file,
      lines: [result.lineStart, result.lineEnd] as [number, number],
      content: result.content,
      score: result.score,
    }));

    return {
      answer,
      sources,
      context,
    };
  } catch (error) {
    console.error('RAG with history error:', error);
    throw new Error(`Failed to query RAG with history: ${error instanceof Error ? error.message : 'Unknown error'}`);
  }
}

// Made with Bob
