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
    // 1. Verifikasi Auth User (Hanya admin yang boleh akses)
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

    const { partnerEmail, partnerName, clientName } = await req.json()

    if (!partnerEmail || !partnerName) {
        throw new Error('Parameter partner tidak lengkap');
    }

    // 2. Ambil RESEND_API_KEY dari Supabase Secrets
    const RESEND_API_KEY = Deno.env.get('RESEND_API_KEY');
    
    if (!RESEND_API_KEY) {
        throw new Error('Konfigurasi Resend API Key hilang di server');
    }

    // 3. Kirim Email
    const res = await fetch('https://api.resend.com/emails', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${RESEND_API_KEY}`
        },
        body: JSON.stringify({
            from: 'Tokcer AI <onboarding@tokcer-ai.com>',
            to: [partnerEmail],
            subject: 'Notifikasi Partner Tokcer AI - Tindakan Diperlukan',
            html: `
                <!DOCTYPE html>
                <html>
                <body style="margin: 0; padding: 20px; font-family: sans-serif;">
                    <h3>Halo ${partnerName},</h3>
                    <p>Terdapat pendaftaran dari klien Anda (<strong>${clientName || 'Klien Baru'}</strong>) yang membutuhkan follow-up atau tindakan dari Anda.</p>
                    <p>Silakan periksa dashboard Anda segera.</p>
                    <br>
                    <p>Terima kasih,<br>Tim Tokcer AI</p>
                </body>
                </html>
            `
        })
    });

    if (!res.ok) {
        const errData = await res.json().catch(() => ({}));
        throw new Error(errData?.message || 'Gagal mengirim email via Resend');
    }

    return new Response(JSON.stringify({ success: true }), {
      headers: { ...corsHeaders, 'Content-Type': 'application/json' },
      status: 200,
    })

  } catch (error) {
    await reportError(error, { function: 'send-partner-reminder' });
    return new Response(JSON.stringify({ error: error.message }), {
      headers: { ...corsHeaders, 'Content-Type': 'application/json' },
      status: 400,
    })
  }
})
