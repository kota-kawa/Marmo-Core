import { ChatOpenAI } from '@langchain/openai';
import { ChatGoogleGenerativeAI } from '@langchain/google-genai';

export type AIProvider = 'openai' | 'gemini' | 'ollama';

interface LLMConfig {
  provider: AIProvider;
  model?: string;
  temperature?: number;
  maxTokens?: number;
}

/**
 * Get LLM instance based on configured provider
 */
export function getLLM(config?: Partial<LLMConfig>) {
  const provider = (config?.provider || process.env.AI_PROVIDER || 'gemini') as AIProvider;
  const temperature = config?.temperature ?? 0;
  const maxTokens = config?.maxTokens;

  switch (provider) {
    case 'gemini':
      return new ChatGoogleGenerativeAI({
        apiKey: process.env.GOOGLE_API_KEY || process.env.GEMINI_API_KEY,
        model: config?.model || process.env.GEMINI_MODEL || 'gemini-2.0-flash',
        temperature,
        maxOutputTokens: maxTokens,
      });

    case 'openai':
      return new ChatOpenAI({
        apiKey: process.env.OPENAI_API_KEY,
        model: config?.model || 'gpt-4-turbo-preview',
        temperature,
        maxTokens,
      });

    case 'ollama':
      // For Ollama, we'll use OpenAI-compatible API
      return new ChatOpenAI({
        configuration: {
          baseURL: process.env.OLLAMA_BASE_URL || 'http://localhost:11434/v1',
        },
        model: config?.model || process.env.OLLAMA_MODEL || 'llama3',
        temperature,
        maxTokens,
      });

    default:
      throw new Error(`Unsupported AI provider: ${provider}`);
  }
}

/**
 * Get embeddings model based on configured provider
 */
export async function getEmbeddings(text: string): Promise<number[]> {
  const provider = process.env.EMBEDDINGS_PROVIDER || 'local';

  switch (provider) {
    case 'local':
      // Use @xenova/transformers for local embeddings
      const { pipeline } = await import('@xenova/transformers');
      const embedder = await pipeline('feature-extraction', 'Xenova/all-MiniLM-L6-v2');
      const output = await embedder(text, { pooling: 'mean', normalize: true });
      return Array.from(output.data);

    case 'gemini':
      // Gemini embeddings
      const { GoogleGenerativeAI } = await import('@google/generative-ai');
      const genAI = new GoogleGenerativeAI(process.env.GEMINI_API_KEY!);
      const model = genAI.getGenerativeModel({ model: 'text-embedding-004' });
      const result = await model.embedContent(text);
      return result.embedding.values;

    case 'openai':
      // OpenAI embeddings
      const { OpenAI } = await import('openai');
      const openai = new OpenAI({ apiKey: process.env.OPENAI_API_KEY });
      const response = await openai.embeddings.create({
        model: 'text-embedding-3-small',
        input: text,
      });
      return response.data[0].embedding;

    default:
      throw new Error(`Unsupported embeddings provider: ${provider}`);
  }
}

/**
 * Check if AI provider is configured
 */
export function isAIConfigured(): boolean {
  const provider = process.env.AI_PROVIDER || 'gemini';
  
  switch (provider) {
    case 'gemini':
      return !!(process.env.GEMINI_API_KEY || process.env.GOOGLE_API_KEY);
    case 'openai':
      return !!process.env.OPENAI_API_KEY;
    case 'ollama':
      return true; // Ollama runs locally, no API key needed
    default:
      return false;
  }
}

/**
 * Get current AI provider info
 */
export function getAIProviderInfo() {
  const provider = process.env.AI_PROVIDER || 'gemini';
  const embeddingsProvider = process.env.EMBEDDINGS_PROVIDER || 'local';
  
  return {
    llm: {
      provider,
      model: provider === 'gemini'
        ? process.env.GEMINI_MODEL || 'gemini-1.5-flash'
        : provider === 'openai'
        ? 'gpt-4-turbo-preview'
        : process.env.OLLAMA_MODEL || 'llama3',
      configured: isAIConfigured(),
    },
    embeddings: {
      provider: embeddingsProvider,
      model: embeddingsProvider === 'local'
        ? 'all-MiniLM-L6-v2'
        : embeddingsProvider === 'gemini'
        ? 'text-embedding-004'
        : 'text-embedding-3-small',
    },
  };
}
