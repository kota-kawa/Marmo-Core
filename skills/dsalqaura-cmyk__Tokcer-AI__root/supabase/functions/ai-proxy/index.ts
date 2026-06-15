import { serve } from "https://deno.land/std@0.168.0/http/server.ts"
import { createClient } from 'https://esm.sh/@supabase/supabase-js@2'
import { reportError } from '../_shared/sentry.ts'

const corsHeaders = {
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Allow-Headers': 'authorization, x-client-info, apikey, content-type',
}

serve(async (req) => {
  if (req.method === 'OPTIONS') {
    return new Response('ok', { headers: corsHeaders })
  }

  try {
    // 1. Verifikasi Auth User (Hanya user login Tokcer AI yang boleh akses)
    const authHeader = req.headers.get('Authorization')
    if (!authHeader) throw new Error('Akses ditolak: Tidak ada token otorisasi')

    const supabaseClient = createClient(
      Deno.env.get('SUPABASE_URL') ?? '',
      Deno.env.get('SUPABASE_ANON_KEY') ?? ''
    )

    const { data: { user }, error: authError } = await supabaseClient.auth.getUser(
      authHeader.replace('Bearer ', '')
    )

    if (authError || !user) {
      throw new Error('Akses ditolak: User tidak valid')
    }

    // 2. Ambil parameter dari request
    const { systemPrompt, userMessage, maxTokens = 2048, temperature = 0.8 } = await req.json()

    // 🔒 TARJO SECURITY: Hard limit max tokens untuk mencegah eksploitasi biaya
    const safeMaxTokens = Math.min(maxTokens, 4096);

    // 3. Panggil API Deepseek secara rahasia di server
    const deepseekApiKey = Deno.env.get('DEEPSEEK_API_KEY')
    if (!deepseekApiKey) {
      throw new Error('Konfigurasi server bermasalah: API Key hilang')
    }

    const res = await fetch('https://api.deepseek.com/v1/chat/completions', {
      method: 'POST',
      headers: { 
        'Content-Type': 'application/json', 
        'Authorization': `Bearer ${deepseekApiKey}` 
      },
      body: JSON.stringify({
        model: 'deepseek-chat', // Gunakan model terbaru/sesuai
        messages: [
          { role: 'system', content: systemPrompt },
          { role: 'user', content: userMessage }
        ],
        temperature: temperature,
        max_tokens: safeMaxTokens,
      })
    })

    if (!res.ok) {
      const errData = await res.json().catch(() => ({}))
      throw new Error(errData?.error?.message || `Server AI Tokcer error: ${res.status}`)
    }

    const data = await res.json()

    // 4. Kembalikan hasil ke klien — sertakan usage data agar frontend bisa log token aktual
    return new Response(JSON.stringify(data), {
      headers: { ...corsHeaders, 'Content-Type': 'application/json' },
      status: 200,
    })

  } catch (error) {
    await reportError(error, { function: 'ai-proxy' });
    return new Response(JSON.stringify({ error: error.message }), {
      headers: { ...corsHeaders, 'Content-Type': 'application/json' },
      status: 400,
    })
  }
})
