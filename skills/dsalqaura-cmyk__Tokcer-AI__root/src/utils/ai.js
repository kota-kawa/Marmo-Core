import { supabase } from '../lib/supabase.js';

export const callAiEngine = async (systemPrompt, userMessage, maxTokens = 2048, temperature = 0.8) => {
  // Panggil Edge Function 'ai-proxy' secara aman (API Key disembunyikan di server)
  const { data, error } = await supabase.functions.invoke('ai-proxy', {
    body: {
      systemPrompt,
      userMessage,
      maxTokens,
      temperature
    }
  });

  if (error || data?.error) {
    throw new Error(data?.error || error?.message || 'Gagal terhubung ke server AI Tokcer.');
  }

  return {
    text: data.choices?.[0]?.message?.content || 'AI tidak memberikan respons.',
    usage: data.usage || { prompt_tokens: 0, completion_tokens: 0, total_tokens: 0 }
  };
};
