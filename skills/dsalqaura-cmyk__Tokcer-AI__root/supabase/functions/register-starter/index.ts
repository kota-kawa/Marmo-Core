// Supabase Edge Function: register-starter
// Lokasi: supabase/functions/register-starter/index.ts
// Trigger deploy to production - Ujang 🚀

import { serve } from "https://deno.land/std@0.168.0/http/server.ts"
import { createClient } from 'https://esm.sh/@supabase/supabase-js@2'

const corsHeaders = {
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Allow-Headers': 'authorization, x-client-info, apikey, content-type',
}

serve(async (req) => {
  // Handle CORS preflight request
  if (req.method === 'OPTIONS') {
    return new Response('ok', { headers: corsHeaders })
  }

  try {
    const supabaseClient = createClient(
      Deno.env.get('SUPABASE_URL') ?? '',
      Deno.env.get('SUPABASE_SERVICE_ROLE_KEY') ?? ''
    )

    // Ambil Resend API Key dari database (karena konfigurasinya disimpan di DB)
    const { data: resendConfig } = await supabaseClient
      .from('ai_configs')
      .select('value')
      .eq('key', 'resend_api_key')
      .maybeSingle()
    
    const RESEND_API_KEY = resendConfig?.value || Deno.env.get('RESEND_API_KEY')

    const body = await req.json()
    const { nama, email, phone, platforms, storeLinks, affiliateId } = body

    if (!email || !nama || !phone) {
      return new Response(
        JSON.stringify({ success: false, error: "Data pendaftaran tidak lengkap." }),
        { headers: { ...corsHeaders, 'Content-Type': 'application/json' }, status: 400 }
      )
    }

    console.log("Memulai pendaftaran instan akun Starter untuk:", email)
    console.log("[REFERRAL] affiliateId diterima:", affiliateId || 'tidak ada')

    // Resolve affiliateId (referral code) ke partner_id
    let resolvedPartnerId: string | null = null
    if (affiliateId && affiliateId.trim() !== '') {
      const { data: partnerData, error: partnerLookupError } = await supabaseClient
        .from('partners')
        .select('id')
        .or(`ref_code.eq.${affiliateId.trim()},referral_code.eq.${affiliateId.trim()}`)
        .maybeSingle()

      if (partnerLookupError) {
        console.warn("[REFERRAL] Gagal lookup partner:", partnerLookupError.message)
      } else if (partnerData?.id) {
        resolvedPartnerId = partnerData.id
        console.log("[REFERRAL] Partner ditemukan, partner_id:", resolvedPartnerId)
      } else {
        console.warn("[REFERRAL] Kode referral tidak cocok dengan partner manapun:", affiliateId)
      }
    }

    // 1. Cek apakah klien dengan email ini sudah ada di database
    const { data: existingClient } = await supabaseClient
      .from('clients')
      .select('*')
      .eq('email', email)
      .maybeSingle()

    let client = existingClient

    if (existingClient) {
      if (existingClient.status === 'active') {
        console.log("User sudah terdaftar dan aktif:", email)
        return new Response(
          JSON.stringify({ 
            success: false, 
            error: "Email ini sudah terdaftar dan aktif. Silakan langsung login di halaman masuk." 
          }),
          { headers: { ...corsHeaders, 'Content-Type': 'application/json' }, status: 200 }
        )
      }

      // Issue 2: Cooldown check 24 jam — cegah registrasi ulang email yang sama
      const createdAt = new Date(existingClient.created_at)
      const hoursSinceCreation = (Date.now() - createdAt.getTime()) / (1000 * 60 * 60)
      if (hoursSinceCreation < 24) {
        console.warn("[COOLDOWN] Email sudah digunakan dalam 24 jam terakhir:", email)
        return new Response(
          JSON.stringify({ 
            success: false, 
            error: `Email ini sudah digunakan dalam proses registrasi. Silakan tunggu ${Math.ceil(24 - hoursSinceCreation)} jam lagi sebelum mendaftar ulang.`
          }),
          { headers: { ...corsHeaders, 'Content-Type': 'application/json' }, status: 200 }
        )
      }

      // Jika statusnya pending/pending_payment/rejected dan sudah lewat 24 jam, aktifkan kembali
      console.log("Mengaktifkan kembali data klien pending...")
      const { data: updatedClient } = await supabaseClient
        .from('clients')
        .update({ 
          status: 'active', 
          plan: 'starter',
          billing_cycle: 'Monthly',
          shop_name: nama,
          whatsapp: phone,
          partner_id: resolvedPartnerId || existingClient.partner_id, // jaga nilai lama jika tidak ada referral baru
          ref: affiliateId || existingClient.ref || 'Direct',
          metadata: { store_links: storeLinks || {} },
          expires_at: null // Starter is lifetime
        })
        .eq('id', existingClient.id)
        .select()
        .single()
      
      client = updatedClient
    } else {
      // 2. Jika benar-benar baru, buat baris klien baru berstatus aktif
      console.log("Membuat klien baru...")
      const { data: newClient, error: createError } = await supabaseClient
        .from('clients')
        .insert([{
          shop_name: nama,
          email: email,
          whatsapp: phone,
          plan: 'starter',
          billing_cycle: 'Monthly',
          status: 'active',
          partner_id: resolvedPartnerId,          // ← FK ke partners.id
          ref: affiliateId || 'Direct',           // ← tetap simpan string untuk backward compat
          metadata: { store_links: storeLinks || {} },
          expires_at: null // Starter is lifetime
        }])
        .select()
        .maybeSingle()

      if (createError || !newClient) {
        console.error("Gagal membuat klien baru di database:", createError?.message)
        throw new Error(`Gagal membuat data klien: ${createError?.message}`)
      }

      client = newClient
    }

    // 3. Generate password acak yang aman dan dinamis
    const generatedPassword = `Tokcer@${Math.floor(1000 + Math.random() * 9000)}`

    // 4. Buat Akun Autentikasi Supabase Auth secara aman via Admin API
    const { data: authData, error: authError } = await supabaseClient.auth.admin.createUser({
      email: email,
      password: generatedPassword,
      email_confirm: true,
      user_metadata: { 
        full_name: nama,
        platforms: platforms || [],
        store_links: storeLinks || {}
      }
    })

    let targetUserId = authData?.user?.id

    if (authError) {
      console.error("createUser error:", authError.message)
      if (authError.message.includes('already exists') || authError.message.includes('already registered')) {
        // Jika user auth sudah ada, ambil ID-nya dan perbarui passwordnya saja
        const { data: existingUsers } = await supabaseClient.auth.admin.listUsers()
        const existingUser = existingUsers?.users?.find(u => u.email === email)
        if (existingUser) {
          targetUserId = existingUser.id
          await supabaseClient.auth.admin.updateUserById(existingUser.id, { password: generatedPassword })
        } else {
          throw new Error(`User terdeteksi ada tetapi tidak dapat diakses: ${email}`)
        }
      } else {
        throw new Error(`Gagal membuat akun auth: ${authError.message}`)
      }
    }

    if (!targetUserId) {
      throw new Error("Gagal memperoleh User ID untuk akun baru.")
    }

    console.log("Akun Auth siap. User ID:", targetUserId)

    // 5. Panggil RPC Modular untuk mengeset Profile dan memberikan jatah 50 Token
    const { data: rpcData, error: rpcError } = await supabaseClient.rpc('rpc_setup_client_account', {
      p_user_id: targetUserId,
      p_email: email,
      p_application_id: client.id,
      p_full_name: nama,
      p_plan: 'starter',
      p_role: 'user'
    })

    if (rpcError) {
      console.error("Gagal menjalankan rpc_setup_client_account:", rpcError.message)
      throw new Error(`Gagal menyiapkan profil dan token: ${rpcError.message}`)
    }

    console.log("Profil & token 50 Starter berhasil dikonfigurasi.")
    console.log("[REFERRAL] Registrasi selesai. partner_id:", resolvedPartnerId || 'tidak ada (Direct)')

    // 6. Kirim Email Onboarding Premium via Resend API
    if (RESEND_API_KEY && email) {
      try {
        // Pastikan API key bersih dari whitespace/newline
        const cleanApiKey = RESEND_API_KEY.trim().replace(/[\r\n]/g, '')
        
        const emailResponse = await fetch('https://api.resend.com/emails', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${cleanApiKey}`
          },
          body: JSON.stringify({
            from: 'Tokcer AI <onboarding@tokcer-ai.com>',
            to: [email],
            subject: '🏮 Selamat Datang di Tokcer AI - Akun Starter Anda Telah Aktif!',
            html: `
              <!DOCTYPE html>
              <html>
              <head>
                <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;700;900&display=swap" rel="stylesheet">
              </head>
              <body style="margin: 0; padding: 0; background-color: #000; font-family: 'Inter', sans-serif;">
                <table width="100%" border="0" cellspacing="0" cellpadding="0" style="background-color: #000; padding: 40px 20px;">
                  <tr>
                    <td align="center">
                      <table width="100%" border="0" cellspacing="0" cellpadding="0" style="max-width: 600px; background-color: #0a0a0a; border: 1px solid #1a1a1a; border-radius: 24px; overflow: hidden; box-shadow: 0 20px 50px rgba(0,0,0,0.5);">
                        <!-- Header dengan Logo Asli -->
                        <tr>
                          <td align="center" style="padding: 40px 0 20px 0;">
                            <img src="https://staging.tokcer-ai.com/logo.png" alt="Tokcer AI" style="width: 180px; display: block;">
                          </td>
                        </tr>
                        
                        <!-- Body -->
                        <tr>
                          <td style="padding: 20px 40px;">
                            <h2 style="color: #fff; font-size: 24px; font-weight: 900; margin-bottom: 10px; text-align: center;">Selamat Bergabung, ${nama}!</h2>
                            <p style="color: #a1a1aa; font-size: 15px; line-height: 1.6; text-align: center; margin-bottom: 30px;">
                              Pendaftaran paket <span style="color: #f97316;">STARTER (GRATIS)</span> Anda telah berhasil. Nikmati jatah <strong>50 token AI setiap bulan</strong> tanpa kedaluwarsa untuk meningkatkan operasional tokomu!
                            </p>
                            
                            <!-- Akun Box -->
                            <div style="background-color: #111; border: 1px solid #222; border-radius: 16px; padding: 25px; margin-bottom: 30px;">
                              <p style="color: #71717a; font-size: 11px; font-weight: 900; text-transform: uppercase; letter-spacing: 2px; margin-bottom: 15px;">Kredensial Akses Login Anda</p>
                              <table width="100%" border="0" cellspacing="0" cellpadding="0">
                                <tr>
                                  <td style="padding-bottom: 10px;">
                                    <span style="color: #52525b; font-size: 13px;">Email Address:</span><br>
                                    <span style="color: #fff; font-size: 16px; font-weight: 700;">${email}</span>
                                  </td>
                                </tr>
                                <tr>
                                  <td>
                                    <span style="color: #52525b; font-size: 13px;">Password Sementara:</span><br>
                                    <span style="color: #f97316; font-size: 18px; font-weight: 900;">${generatedPassword}</span>
                                  </td>
                                </tr>
                              </table>
                            </div>
                            
                            <!-- CTA Button -->
                            <div style="text-align: center; margin-bottom: 40px;">
                              <a href="https://tokcer-ai.com/login" style="display: inline-block; background-color: #f97316; color: #fff; font-weight: 900; text-decoration: none; padding: 16px 40px; border-radius: 12px; font-size: 16px; box-shadow: 0 10px 20px rgba(249, 115, 22, 0.3);">MASUK SEKARANG</a>
                            </div>
                          </td>
                        </tr>
                        
                        <!-- Footer -->
                        <tr>
                          <td style="background-color: #111; padding: 30px 40px; border-top: 1px solid #1a1a1a; text-align: center;">
                            <p style="color: #52525b; font-size: 12px; line-height: 1.5; margin: 0;">
                              &copy; 2026 Tokcer AI Solutions.<br>
                              Anda menerima email ini karena mendaftar paket Starter di tokcer-ai.com.
                            </p>
                          </td>
                        </tr>
                      </table>
                    </td>
                  </tr>
                </table>
              </body>
              </html>
            `
          })
        })
        // ✅ Cek response Resend secara eksplisit (fetch tidak throw error untuk 4xx/5xx)
        if (!emailResponse.ok) {
          const errBody = await emailResponse.text()
          console.error(`Resend API error ${emailResponse.status}:`, errBody)
          console.error("Kemungkinan penyebab: domain belum verified di Resend, atau API key salah.")
        } else {
          console.log("Email onboarding sukses terkirim ke:", email)
        }
      } catch (emailErr) {
        console.error("Gagal mengirim email welcome (network error):", emailErr.message)
      }
    } else {
      console.warn("RESEND_API_KEY kosong — email tidak dikirim. Cek tabel ai_configs key='resend_api_key'")
    }

    return new Response(
      JSON.stringify({ success: true }),
      { headers: { ...corsHeaders, 'Content-Type': 'application/json' }, status: 200 }
    )

  } catch (error) {
    console.error("Global register-starter error:", error.message)
    return new Response(
      JSON.stringify({ success: false, error: error.message }),
      { headers: { ...corsHeaders, 'Content-Type': 'application/json' }, status: 200 }
    )
  }
})
