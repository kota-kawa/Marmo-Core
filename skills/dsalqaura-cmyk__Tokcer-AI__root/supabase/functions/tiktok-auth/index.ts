import { serve } from "https://deno.land/std@0.168.0/http/server.ts"
import { createClient } from 'https://esm.sh/@supabase/supabase-js@2'

const corsHeaders = {
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Allow-Headers': 'authorization, x-client-info, apikey, content-type',
}

serve(async (req) => {
  if (req.method === 'OPTIONS') return new Response('ok', { headers: corsHeaders })

  try {
    const supabaseClient = createClient(
      Deno.env.get('SUPABASE_URL') ?? '',
      Deno.env.get('SUPABASE_SERVICE_ROLE_KEY') ?? ''
    )

    const { auth_code, user_id } = await req.json()
    if (!auth_code || !user_id) throw new Error("Missing auth_code or user_id")

    // 1. Get TikTok App Credentials from Database
    const { data: configs, error: configError } = await supabaseClient
      .from('ai_configs')
      .select('key, value')
      .in('key', ['tiktok_app_id', 'tiktok_app_secret'])

    if (configError) throw new Error("Gagal mengambil konfigurasi TikTok")
    
    let appKey = null;
    let appSecret = null;
    configs.forEach(c => {
        if (c.key === 'tiktok_app_id') appKey = c.value;
        if (c.key === 'tiktok_app_secret') appSecret = c.value;
    });

    if (!appKey || !appSecret) {
         throw new Error("TikTok App ID atau Secret belum dikonfigurasi di Admin.");
    }

    // 2. Exchange auth_code for Access Token
    const url = `https://auth.tiktok-shops.com/api/v2/token/get?app_key=${appKey}&app_secret=${appSecret}&auth_code=${auth_code}&grant_type=authorized_code`;
    
    const response = await fetch(url);
    const data = await response.json();

    if (data.code !== 0) {
        throw new Error(data.message || 'Gagal menukar token dengan TikTok');
    }

    const { access_token, refresh_token, access_token_expire_in, seller_name, open_id } = data.data;

    // 3. Save to database (Idempotent: check for existing connection for this specific shop first)
    const targetShopId = open_id || '';
    
    let existingConnection = null;
    if (targetShopId) {
        const { data: existing, error: findError } = await supabaseClient
            .from('marketplace_connections')
            .select('id')
            .eq('user_id', user_id)
            .eq('platform', 'tiktok')
            .eq('shop_id', targetShopId)
            .maybeSingle();

        if (findError) throw new Error("Gagal mencari koneksi lama: " + findError.message);
        existingConnection = existing;
    }

    let dbResult;
    const tokenExpiryDate = new Date(Date.now() + (access_token_expire_in || 0) * 1000).toISOString();

    if (existingConnection?.id) {
        dbResult = await supabaseClient
            .from('marketplace_connections')
            .update({
                shop_name: seller_name || 'TikTok Shop',
                access_token: access_token,
                refresh_token: refresh_token,
                token_expiry: tokenExpiryDate,
                sync_status: 'active'
            })
            .eq('id', existingConnection.id);
    } else {
        dbResult = await supabaseClient
            .from('marketplace_connections')
            .insert({
                user_id: user_id,
                platform: 'tiktok',
                shop_name: seller_name || 'TikTok Shop',
                shop_id: targetShopId || 'TTK' + Math.floor(1000 + Math.random() * 9000),
                access_token: access_token,
                refresh_token: refresh_token,
                token_expiry: tokenExpiryDate,
                sync_status: 'active'
            });
    }

    if (dbResult.error) throw new Error("Gagal menyimpan token ke database: " + dbResult.error.message);

    return new Response(
      JSON.stringify({ success: true, store_name: seller_name }),
      { headers: { ...corsHeaders, 'Content-Type': 'application/json' }, status: 200 }
    )

  } catch (error) {
    console.error("TikTok Auth Error:", error.message);
    return new Response(
      JSON.stringify({ success: false, error: error.message }),
      { headers: { ...corsHeaders, 'Content-Type': 'application/json' }, status: 200 }
    )
  }
})
