// Supabase Edge Function: midtrans-init
// Lokasi: supabase/functions/midtrans-init/index.ts

import { serve } from "https://deno.land/std@0.168.0/http/server.ts"
import { createClient } from 'https://esm.sh/@supabase/supabase-js@2'
import { reportError } from '../_shared/sentry.ts'

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

    const { plan_name, amount, tokens, is_sandbox, user_data } = await req.json()

    // ==========================================
    // 0. BYPASS UNTUK PAKET GRATIS (STARTER)
    // ==========================================
    if (amount === 0) {
      console.log("Mendeteksi pendaftaran paket GRATIS untuk:", user_data.email);
      const generatedPassword = `Tokcer@${Math.floor(1000 + Math.random() * 9000)}`;

      // A. Buat User via Admin API
      const { data: authData, error: authError } = await supabaseClient.auth.admin.createUser({
          email: user_data.email,
          password: generatedPassword,
          email_confirm: true,
          user_metadata: { full_name: user_data.nama }
      });

      if (authError) {
          if (authError.message.includes('already exists') || authError.message.includes('already registered')) {
               const { data: existingUsers } = await supabaseClient.auth.admin.listUsers();
               const existingUser = existingUsers.users.find(u => u.email === user_data.email);
               if (existingUser) {
                   authData.user = existingUser;
                   await supabaseClient.auth.admin.updateUserById(existingUser.id, { password: generatedPassword });
               } else {
                   throw new Error(`User exists but could not be retrieved: ${user_data.email}`);
               }
          } else {
              throw new Error(`Gagal membuat user: ${authError.message}`);
          }
      }
      
      const targetUserId = authData?.user?.id;
      if (!targetUserId) throw new Error("Gagal mendapatkan User ID");

      // B. Catat ke Tabel Clients
      const { data: client, error: insertError } = await supabaseClient.from('clients').insert([{
          id: targetUserId,
          partner_id: user_data.partner_id || null,
          shop_name: user_data.nama,
          email: user_data.email,
          whatsapp: user_data.phone,
          plan: plan_name,
          billing_cycle: user_data.billing_cycle || 'Monthly',
          payment_method: 'free',
          status: 'active',
          ref: user_data.ref || 'Partner'
      }]).select().single();

      if (insertError) throw new Error(`Gagal mencatat data klien: ${insertError.message}`);

      // C. Panggil RPC Modular
      const { error: rpcError } = await supabaseClient.rpc('rpc_setup_client_account', {
          p_user_id: targetUserId,
          p_email: user_data.email,
          p_application_id: client.id,
          p_full_name: user_data.nama,
          p_plan: plan_name,
          p_role: 'user'
      });

      if (rpcError) throw new Error(`Gagal setup akun (RPC): ${rpcError.message}`);

      // D. Kirim Email Resend
      const { data: resendConfig } = await supabaseClient.from('ai_configs').select('value').eq('key', 'resend_api_key').maybeSingle();
      const RESEND_API_KEY = resendConfig?.value || Deno.env.get('RESEND_API_KEY');

      if (RESEND_API_KEY) {
          try {
              const cleanApiKey = RESEND_API_KEY.trim().replace(/[\r\n]/g, '')
              const emailRes = await fetch('https://api.resend.com/emails', {
                  method: 'POST',
                  headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${cleanApiKey}` },
                  body: JSON.stringify({
                      from: 'Tokcer AI <onboarding@tokcer-ai.com>',
                      to: [user_data.email],
                      subject: '🏮 Selamat Datang di Tokcer AI - Akun Gratis Anda Telah Aktif!',
                      html: `
                          <div style="font-family: sans-serif; background: #000; color: #fff; padding: 40px; border-radius: 24px; border: 1px solid #222;">
                            <img src="https://staging.tokcer-ai.com/logo.png" style="height: 40px; margin-bottom: 30px;">
                            <h2 style="font-weight: 900;">Selamat Datang, ${user_data.nama}!</h2>
                            <p style="color: #888;">Akun Tokcer AI Anda telah aktif dengan paket <span style="color: #f97316;">${plan_name.toUpperCase()}</span>.</p>
                            <div style="background: #111; padding: 25px; border-radius: 16px; margin: 20px 0; border: 1px dashed #333;">
                              <p style="margin: 0; color: #555; font-size: 11px; text-transform: uppercase; letter-spacing: 2px;">Akses Login Anda</p>
                              <p style="font-size: 16px; font-weight: 900; margin: 10px 0; color: #fff;">Email: ${user_data.email}</p>
                              <p style="font-size: 16px; font-weight: 900; margin: 10px 0; color: #fff;">Password: <span style="color: #f97316;">${generatedPassword}</span></p>
                            </div>
                            <a href="https://tokcer-ai.com/login" style="display: inline-block; background: #f97316; color: #fff; padding: 16px 32px; text-decoration: none; border-radius: 12px; font-weight: 900; margin-top: 20px;">MASUK KE DASHBOARD</a>
                          </div>
                      `
                  })
              });
              if (!emailRes.ok) {
                const errBody = await emailRes.text()
                console.error(`Resend error ${emailRes.status} (bypass starter):`, errBody)
              } else {
                console.log("Email bypass starter sukses terkirim ke:", user_data.email)
              }
          } catch (e) { console.error("Email error (bypass):", e.message); }
      } else {
          console.warn("RESEND_API_KEY kosong — email bypass tidak dikirim.")
      }

      return new Response(
        JSON.stringify({ bypass: true, success: true, userId: targetUserId }),
        { headers: { ...corsHeaders, 'Content-Type': 'application/json' }, status: 200 }
      );
    }
    // ==========================================
    
    
    // 1. Determine Environment & Keys
    const serverKey = is_sandbox 
      ? Deno.env.get('MIDTRANS_SERVER_KEY_SANDBOX') 
      : Deno.env.get('MIDTRANS_SERVER_KEY');
    
    const midtransUrl = is_sandbox 
      ? 'https://app.sandbox.midtrans.com/snap/v1/transactions' 
      : 'https://app.midtrans.com/snap/v1/transactions';

    const authString = btoa(`${serverKey}:`)
    const orderId = `TOKCER-${Date.now()}-${user_data.email.slice(0, 3)}`

    // 2. Call Midtrans API
    const midtransResponse = await fetch(midtransUrl, {
      method: 'POST',
      headers: {
        'Accept': 'application/json',
        'Content-Type': 'application/json',
        'Authorization': `Basic ${authString}`
      },
      body: JSON.stringify({
        transaction_details: { order_id: orderId, gross_amount: amount },
        customer_details: {
          email: user_data.email,
          first_name: user_data.nama,
          phone: user_data.phone
        },
        item_details: [{
          id: plan_name,
          price: amount,
          quantity: 1,
          name: `Tokcer AI - Paket ${plan_name.toUpperCase()}`
        }]
      })
    })

    const midtransData = await midtransResponse.json()
    if (!midtransResponse.ok) throw new Error(midtransData.error_messages?.join(', ') || 'Midtrans Error')

    // 3. AGGRESSIVE SAVE: Kita hanya kirim data yang PASTI diperbolehkan database
    const insertData: any = {
      order_id: orderId,
      plan_name: plan_name,
      amount: amount,
      tokens_to_add: tokens,
      snap_token: midtransData.token,
      status: 'pending',
      raw_notification: { user_data }
    };

    // Hanya isi user_id jika datanya ada (User Lama)
    // Jika User Baru, kolom ini tidak akan dikirim sama sekali agar tidak ditolak database
    if (user_data.user_id) {
        insertData.user_id = user_data.user_id;
    }

    const { error: dbError } = await supabaseClient.from('transactions').insert(insertData);
    
    if (dbError) {
        console.error("DB INSERT ERROR:", dbError.message);
        throw new Error(`Gagal mencatat transaksi: ${dbError.message}`);
    }

    // 3b. PRE-INSERT ke clients dengan status pending_payment untuk preserve referral
    // Ini memastikan partner_id tidak hilang jika user switch ke paket lain sebelum bayar
    if (user_data.email && !user_data.user_id) {
      // Resolve affiliateId ke partner_id
      let prePartnerId: string | null = null;
      const affiliateId = user_data.affiliateId;
      if (affiliateId && affiliateId.trim() !== '') {
        const { data: partnerRow } = await supabaseClient
          .from('partners')
          .select('id')
          .or(`ref_code.eq.${affiliateId.trim()},referral_code.eq.${affiliateId.trim()}`)
          .maybeSingle();
        if (partnerRow?.id) prePartnerId = partnerRow.id;
      }

      // Cek apakah sudah ada di clients
      const { data: existingClient } = await supabaseClient
        .from('clients')
        .select('id, status, partner_id')
        .eq('email', user_data.email)
        .maybeSingle();

      if (!existingClient) {
        // Insert baru dengan status pending_payment — relasi partner sudah tersimpan
        const { error: clientInsertError } = await supabaseClient.from('clients').insert([{
          shop_name: user_data.nama,
          email: user_data.email,
          whatsapp: user_data.phone || '',
          plan: plan_name,
          billing_cycle: user_data.billing_cycle || 'Monthly',
          payment_method: 'midtrans',
          status: 'pending_payment',
          partner_id: prePartnerId,
          ref: affiliateId || 'Direct',
          midtrans_order_id: orderId,
        }]);
        if (clientInsertError) {
          // Non-fatal: log saja, jangan gagalkan transaksi
          console.warn("[REFERRAL] Gagal pre-insert clients:", clientInsertError.message);
        } else {
          console.log("[REFERRAL] Pre-insert clients berhasil. partner_id:", prePartnerId);
        }
      } else if (!existingClient.partner_id && prePartnerId) {
        // Update partner_id jika belum ada
        await supabaseClient.from('clients')
          .update({ partner_id: prePartnerId, ref: affiliateId || existingClient.ref })
          .eq('email', user_data.email);
        console.log("[REFERRAL] Update partner_id pada existing client:", prePartnerId);
      }
    }

    // 4. KIRIM EMAIL INSTRUKSI (Pindah ke Server)
    const { data: resendConfig } = await supabaseClient
      .from('ai_configs')
      .select('value')
      .eq('key', 'resend_api_key')
      .maybeSingle();
    
    const RESEND_API_KEY = resendConfig?.value || Deno.env.get('RESEND_API_KEY');
    const paymentUrl = is_sandbox
      ? `https://app.sandbox.midtrans.com/snap/v2/vtweb/${midtransData.token}`
      : `https://app.midtrans.com/snap/v2/vtweb/${midtransData.token}`;

    if (RESEND_API_KEY) {
      try {
        const cleanApiKey = RESEND_API_KEY.trim().replace(/[\r\n]/g, '')
        const emailRes = await fetch('https://api.resend.com/emails', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${cleanApiKey}`
          },
          body: JSON.stringify({
            from: 'Tokcer AI <billing@tokcer-ai.com>',
            to: [user_data.email],
            subject: '🏮 Instruksi Pembayaran Tokcer AI',
            html: `
              <div style="font-family: sans-serif; background: #000; color: #fff; padding: 40px; border-radius: 24px; border: 1px solid #222;">
                <img src="https://staging.tokcer-ai.com/logo.png" style="height: 40px; margin-bottom: 30px;">
                <h2 style="font-weight: 900;">Halo, ${user_data.nama}!</h2>
                <p style="color: #888;">Partner kami telah mendaftarkan toko Anda. Silakan selesaikan pembayaran untuk mengaktifkan akun Anda.</p>
                <div style="background: #111; padding: 25px; border-radius: 16px; margin: 20px 0; border: 1px dashed #333;">
                  <p style="margin: 0; color: #555; font-size: 11px; text-transform: uppercase; letter-spacing: 2px;">Tagihan Anda</p>
                  <p style="font-size: 24px; font-weight: 900; margin: 10px 0; color: #f97316;">Rp ${amount.toLocaleString('id-ID')}</p>
                  <p style="margin: 0; color: #aaa; font-size: 13px;">Paket: ${plan_name.toUpperCase()}</p>
                </div>
                <a href="${paymentUrl}" style="display: inline-block; background: #f97316; color: #fff; padding: 16px 32px; text-decoration: none; border-radius: 12px; font-weight: 900; margin-top: 20px;">BAYAR SEKARANG (QRIS/VA)</a>
                <p style="margin-top: 30px; font-size: 12px; color: #444;">Link ini akan kadaluarsa dalam 24 jam.</p>
              </div>
            `
          })
        });
        if (!emailRes.ok) {
          const errBody = await emailRes.text()
          console.error(`Resend error ${emailRes.status} (instruksi bayar):`, errBody)
        } else {
          console.log("Email instruksi pembayaran sukses terkirim ke:", user_data.email)
        }
      } catch (emailErr) {
        console.error("Gagal kirim email instruksi:", emailErr.message);
        // Tidak throw error agar transaksi tetap berhasil dibuat walau email gagal
      }
    } else {
      console.warn("RESEND_API_KEY kosong — email instruksi tidak dikirim.")
    }

    return new Response(
      JSON.stringify({ token: midtransData.token, orderId }),
      { headers: { ...corsHeaders, 'Content-Type': 'application/json' }, status: 200 }
    )

  } catch (error) {
    console.error("INIT ERROR:", error.message);
    await reportError(error, { function: 'midtrans-init' });
    return new Response(
      JSON.stringify({ error: error.message }),
      { headers: { ...corsHeaders, 'Content-Type': 'application/json' }, status: 400 }
    )
  }
})
