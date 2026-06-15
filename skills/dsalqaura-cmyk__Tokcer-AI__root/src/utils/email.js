import { supabase } from '../lib/supabase';

/**
 * Utility to send emails via Resend API
 * Fetches API key from ai_configs table
 */
export const sendEmail = async ({ to, subject, html, isPartner = false }) => {
  try {
    // 1. Get Resend API Key from Database (Differentiate between User and Partner if needed)
    const configKey = isPartner ? 'resend_api_key_partner' : 'resend_api_key';
    
    const { data: config, error: configError } = await supabase
      .from('ai_configs')
      .select('value')
      .eq('key', configKey)
      .maybeSingle();

    let apiKey = config?.value;
    
    // Fallback to general key if partner key is missing
    if (!apiKey && isPartner) {
        const { data: generalConfig } = await supabase
          .from('ai_configs')
          .select('value')
          .eq('key', 'resend_api_key')
          .maybeSingle();
        apiKey = generalConfig?.value;
    }

    if (!apiKey || apiKey === '' || apiKey.includes('your_resend') || apiKey.includes('mock')) {
      console.error("❌ Resend API Key tidak ditemukan atau tidak valid di database (ai_configs).");
      throw new Error("Sistem gagal mengirim email karena API Key Resend tidak ditemukan di database (ai_configs).");
    }

    // 2. Send via Resend API (REPLICATING InternalDashboard.jsx logic)
    console.log(`📨 Mengirim email via Resend...`);

    const response = await fetch('https://api.resend.com/emails', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${apiKey}`
      },
      body: JSON.stringify({
        from: 'Tokcer AI <onboarding@tokcer-ai.com>', 
        to: Array.isArray(to) ? to : [to],
        subject: subject,
        html: html
      })
    });

    const result = await response.json();
    
    if (response.ok) {
      console.log("✅ Email Berhasil Terkirim! ID:", result.id);
      return { success: true, id: result.id };
    } else {
      console.error("❌ Resend API Error Details:", result);
      throw new Error(`Resend Error: ${result.message || result.error || 'Gagal mengirim email'}`);
    }
  } catch (err) {
    console.error("❌ Email Sending failed:", err);
    return { success: false, error: err.message };
  }
};

/**
 * Specifically for new registrations from the landing page
 */
export const sendRegistrationConfirmation = async (userData) => {
  const { email, nama, plan } = userData;
  
  const subject = `🏮 Pendaftaran Tokcer AI: Data ${nama} Telah Diterima!`;
  const html = `
    <div style="font-family: 'Inter', sans-serif; max-width: 600px; margin: auto; padding: 40px; border: 1px solid #e5e7eb; border-radius: 24px; color: #111827;">
      <div style="text-align: center; margin-bottom: 30px;">
        <h1 style="color: #ea580c; margin: 0; font-size: 24px;">Tokcer AI</h1>
        <p style="color: #6b7280; font-size: 14px;">Marketplace Solution for Smart Sellers</p>
      </div>
      
      <h2 style="font-size: 20px; margin-bottom: 16px;">Halo, ${nama}!</h2>
      <p style="font-size: 14px; line-height: 1.6; color: #374151;">
        Terima kasih telah mendaftar di <b>Tokcer AI</b>. Kami telah menerima data pendaftaran Anda untuk paket <b style="text-transform: uppercase;">${plan}</b>.
      </p>
      
      <div style="background: #f9fafb; padding: 20px; border-radius: 16px; margin: 24px 0; border: 1px inset #f3f4f6;">
        <p style="margin: 0; font-size: 13px; color: #4b5563;"><b>Apa langkah selanjutnya?</b></p>
        <ol style="font-size: 13px; color: #4b5563; padding-left: 20px; margin-top: 10px;">
          <li>Tim kami akan memverifikasi data dan bukti pembayaran Anda (jika ada).</li>
          <li>Akun Anda akan diaktifkan dalam waktu maksimal 1x24 jam.</li>
          <li>Instruksi login dan password sementara akan dikirimkan ke email ini.</li>
        </ol>
      </div>
      
      <p style="font-size: 14px; line-height: 1.6; color: #374151;">
        Jika Anda memiliki pertanyaan mendesak, silakan hubungi tim support kami via WhatsApp di nomor yang tertera di website.
      </p>
      
      <div style="margin-top: 40px; padding-top: 20px; border-top: 1px solid #e5e7eb; text-align: center;">
        <p style="font-size: 12px; color: #9ca3af;">&copy; 2026 Tokcer AI. All rights reserved.</p>
      </div>
    </div>
  `;

  return sendEmail({ to: email, subject, html });
};

export const sendDemoWelcomeEmail = async (userData) => {
  const { email, name } = userData;
  const subject = `🚀 Pengajuan Demo Tokcer AI Anda Telah Diterima!`;
  const html = `
    <div style="font-family: 'Inter', sans-serif; max-width: 600px; margin: auto; padding: 40px; border: 1px solid #e5e7eb; border-radius: 24px; color: #111827;">
      <div style="text-align: center; margin-bottom: 30px;">
        <h1 style="color: #ea580c; margin: 0; font-size: 24px;">Tokcer AI</h1>
        <p style="color: #6b7280; font-size: 14px;">Marketplace Solution for Smart Sellers</p>
      </div>
      <h2 style="font-size: 20px; margin-bottom: 16px;">Halo, ${name}!</h2>
      <p style="font-size: 14px; line-height: 1.6; color: #374151;">
        Terima kasih atas ketertarikan Anda. Kami telah menerima permohonan akses akun <b>Demo Tokcer AI</b> Anda.
      </p>
      <div style="background: #f9fafb; padding: 20px; border-radius: 16px; margin: 24px 0; border: 1px inset #f3f4f6;">
        <p style="margin: 0; font-size: 13px; color: #4b5563;"><b>Apa langkah selanjutnya?</b></p>
        <ol style="font-size: 13px; color: #4b5563; padding-left: 20px; margin-top: 10px;">
          <li>Tim kami akan meninjau pengajuan demo Anda.</li>
          <li>Apabila disetujui, Anda akan menerima email balasan berupa instruksi login beserta kredensial (Password).</li>
          <li>Proses persetujuan biasanya memakan waktu maksimal 1x24 jam kerja.</li>
        </ol>
      </div>
      <p style="font-size: 14px; line-height: 1.6; color: #374151;">
        Harap bersabar menunggu, kami akan segera menghubungi Anda!
      </p>
    </div>
  `;
  return sendEmail({ to: email, subject, html });
};

export const sendDemoApprovalEmail = async (email, password) => {
  const subject = `🚀 Akses Demo Tokcer AI Anda Aktif!`;
  const html = `
    <div style="font-family:sans-serif; background:#000; color:#fff; padding:40px; border-radius:20px; border:1px solid #333;">
      <img src="https://tokcer-ai.com/logo.png" style="height:40px; margin-bottom:20px;">
      <h2>Selamat! Akun Demo Anda Aktif</h2>
      <p>Anda mendapatkan akses khusus (Plan: Demo) dengan gratis 30 AI Credits.</p>
      <div style="background:#111; padding:20px; border:1px dashed #444; border-radius:12px; margin:20px 0;">
        Email: <b>${email}</b><br>
        Password: <b style="color:#ea580c; font-size:18px;">${password}</b>
      </div>
      <br>
      <a href="https://tokcer-ai.com/login" style="background:#ea580c; color:#fff; padding:14px 28px; text-decoration:none; border-radius:10px; font-weight:bold; display:inline-block;">LOGIN SEKARANG</a>
    </div>
  `;
  return sendEmail({ to: email, subject, html });
};
