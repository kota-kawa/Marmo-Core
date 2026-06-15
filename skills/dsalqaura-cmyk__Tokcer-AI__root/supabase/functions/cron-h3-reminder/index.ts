import { serve } from "https://deno.land/std@0.168.0/http/server.ts";
import { createClient } from 'https://esm.sh/@supabase/supabase-js@2';
import { reportError } from '../_shared/sentry.ts';

const corsHeaders = {
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Allow-Headers': 'authorization, x-client-info, apikey, content-type',
};

serve(async (req) => {
  // Handle CORS preflight requests
  if (req.method === 'OPTIONS') {
    return new Response('ok', { headers: corsHeaders });
  }

  try {
    const supabaseUrl = Deno.env.get('SUPABASE_URL') || '';
    const supabaseServiceKey = Deno.env.get('SUPABASE_SERVICE_ROLE_KEY') || '';

    // Bypass with Service Role for Admin/Cron bypass
    const supabase = createClient(supabaseUrl, supabaseServiceKey, {
      auth: {
        autoRefreshToken: false,
        persistSession: false
      }
    });

    // 1. Ambil Resend API Key dari Supabase Edge Secrets
    const RESEND_API_KEY = Deno.env.get('RESEND_API_KEY');
    
    if (!RESEND_API_KEY) {
        throw new Error("Resend API Key is missing");
    }

    // 2. Tentukan Tanggal Target H-3
    const today = new Date();
    const targetDate = new Date(today);
    targetDate.setDate(today.getDate() + 3);
    
    // Format to YYYY-MM-DD
    const targetDateString = targetDate.toISOString().split('T')[0];
    
    // 3. Ambil Klien yang expired pada target date
    const { data: clients, error: fetchError } = await supabase
        .from('clients')
        .select('id, email, shop_name, plan, expires_at')
        .eq('status', 'active')
        .gte('expires_at', `${targetDateString}T00:00:00.000Z`)
        .lte('expires_at', `${targetDateString}T23:59:59.999Z`);
        
    if (fetchError) throw fetchError;

    if (!clients || clients.length === 0) {
        return new Response(JSON.stringify({ message: "Tidak ada klien H-3 hari ini." }), {
            headers: { ...corsHeaders, 'Content-Type': 'application/json' },
            status: 200,
        });
    }

    const results = [];

    // 4. Kirim Email ke masing-masing klien
    for (const client of clients) {
        const formattedDate = new Date(client.expires_at).toLocaleDateString('id-ID', {
            day: 'numeric', month: 'long', year: 'numeric'
        });

        const emailHtml = `
            <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px; background-color: #000; color: #fff; border-radius: 12px; border: 1px solid #333;">
                <div style="text-align: center; margin-bottom: 20px;">
                    <img src="https://i.ibb.co.com/8N46HwV/TOKCER-AI-LOGO-NEW-1.png" alt="Tokcer AI" style="height: 40px;" />
                </div>
                <h2 style="color: #f97316;">Pemberitahuan Jatuh Tempo H-3</h2>
                <p>Halo <strong>${client.shop_name}</strong>,</p>
                <p>Masa aktif paket <strong>${client.plan}</strong> Anda akan segera berakhir pada <strong>${formattedDate}</strong>.</p>
                <p>Agar operasional dan fitur AI Anda tidak terhenti, mohon segera lakukan perpanjangan layanan melalui dashboard akun Anda.</p>
                
                <div style="text-align: center; margin: 30px 0;">
                    <a href="https://staging.tokcer-ai.com/dashboard" style="background-color: #f97316; color: white; padding: 12px 24px; text-decoration: none; font-weight: bold; border-radius: 8px;">Perpanjang Langganan</a>
                </div>
                
                <hr style="border-color: #333; margin: 20px 0;" />
                <p style="font-size: 12px; color: #888; text-align: center;">
                    Pesan ini dikirim secara otomatis. Harap tidak membalas email ini.<br>
                    &copy; ${new Date().getFullYear()} Tokcer AI. All rights reserved.
                </p>
            </div>
        `;

        try {
            const emailRes = await fetch('https://api.resend.com/emails', {
                method: 'POST',
                headers: {
                    'Authorization': `Bearer ${RESEND_API_KEY}`,
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    from: "Tokcer AI Billing <no-reply@tokcer-ai.com>",
                    to: client.email,
                    subject: `[REMINDER H-3] Perpanjangan Masa Aktif Tokcer AI - ${client.shop_name}`,
                    html: emailHtml
                })
            });
            
            const resData = await emailRes.json();
            results.push({ email: client.email, status: emailRes.ok ? 'success' : 'failed', details: resData });
        } catch (err) {
            results.push({ email: client.email, status: 'error', error: err.message });
        }
    }

    return new Response(JSON.stringify({ 
        message: "Proses reminder H-3 selesai.", 
        processed: clients.length, 
        results 
    }), {
        headers: { ...corsHeaders, 'Content-Type': 'application/json' },
        status: 200,
    });

  } catch (error) {
    await reportError(error, { function: 'cron-h3-reminder' });
    return new Response(JSON.stringify({ error: error.message }), {
      headers: { ...corsHeaders, 'Content-Type': 'application/json' },
      status: 400,
    });
  }
});
