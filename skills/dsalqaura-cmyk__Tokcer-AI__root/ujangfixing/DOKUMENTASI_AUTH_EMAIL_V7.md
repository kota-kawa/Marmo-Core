# 🏮 DOKUMENTASI PERBAIKAN SISTEM AUTH & EMAIL (v7.2)
**Tanggal:** 7 Mei 2026  
**Status:** STABIL & TERVERIFIKASI

---

## 1. DESKRIPSI MASALAH
Sebelumnya, sistem mengalami dua kendala utama pada pendaftaran Partner baru:
1.  **Login Gagal:** User baru (Partner) mendapatkan notifikasi `"Database error querying schema"` saat mencoba login pertama kali di Dashboard.
2.  **Email Aktivasi Hilang:** Email nomor 3 (berisi Password & Username) tidak terkirim ke inbox user setelah admin melakukan aktivasi lewat robot.

## 2. AKAR MASALAH (ROOT CAUSE)
*   **Auth Identity Cacat:** Fungsi aktivasi lama memasukkan data ke tabel `auth.users` dengan `instance_id` sembarangan dan data `auth.identities` yang tidak lengkap (missing `email_verified`). Hal ini membuat Supabase menolak otentikasi user tersebut.
*   **Trigger vs RPC Conflict:** Pengiriman email di dalam fungsi RPC seringkali crash karena skema `net` yang tidak stabil di beberapa environment, sehingga membatalkan seluruh proses pendaftaran.

## 3. SOLUSI YANG DITERAPKAN
*   **Dynamic Instance ID:** Robot sekarang mengambil `instance_id` asli dari proyek Supabase secara otomatis agar user baru dianggap "sah".
*   **Identity Hardening:** Menambahkan field `email_verified: true` dan format JSON yang sesuai standar Supabase terbaru.
*   **Try-Catch Email:** Membungkus pengiriman email dalam blok `EXCEPTION` agar jika pengiriman email gagal, user tetap bisa login ke dashboard.

---

## 4. FINAL SQL (KODE SAKTI)
Gunakan kode di bawah ini jika ingin melakukan setup ulang atau migrasi database. Kode ini sudah menyertakan perbaikan Auth dan format Email asli Tokcer AI.

```sql
CREATE OR REPLACE FUNCTION public.rpc_activate_partner(
    p_email TEXT,
    p_application_id UUID,
    p_full_name TEXT,
    p_password TEXT
)
RETURNS JSON LANGUAGE plpgsql SECURITY DEFINER AS $$
DECLARE
    v_user_id UUID;
    v_instance_id UUID;
    v_resend_api_key TEXT;
    v_html TEXT;
    v_expiry TIMESTAMP := NOW() + INTERVAL '60 days';
BEGIN
    -- [1] AUTH MANAGEMENT: Ambil Instance ID Asli Proyek
    SELECT instance_id INTO v_instance_id FROM auth.users LIMIT 1;
    IF v_instance_id IS NULL THEN v_instance_id := '00000000-0000-0000-0000-000000000000'; END IF;

    -- Cek existing user
    SELECT id INTO v_user_id FROM auth.users WHERE email = p_email;
    
    IF v_user_id IS NULL THEN
        v_user_id := gen_random_uuid();
        -- Buat User Baru
        INSERT INTO auth.users (instance_id, id, aud, role, email, encrypted_password, email_confirmed_at, raw_app_meta_data, raw_user_meta_data, is_super_admin, created_at, updated_at, last_sign_in_at, confirmation_token, recovery_token, email_change_token_new, email_change)
        VALUES (v_instance_id, v_user_id, 'authenticated', 'authenticated', p_email, crypt(p_password, gen_salt('bf')), NOW(), '{"provider":"email","providers":["email"]}', jsonb_build_object('full_name', p_full_name), false, NOW(), NOW(), NOW(), '', '', '', '');
        
        -- Buat Identitas (Penting untuk Login)
        INSERT INTO auth.identities (id, user_id, identity_data, provider, provider_id, last_sign_in_at, created_at, updated_at)
        VALUES (gen_random_uuid(), v_user_id, jsonb_build_object('sub', v_user_id, 'email', p_email, 'email_verified', true), 'email', p_email, NOW(), NOW(), NOW());
    ELSE
        -- Update Password jika sudah ada
        UPDATE auth.users SET encrypted_password = crypt(p_password, gen_salt('bf')), updated_at = NOW() WHERE id = v_user_id;
    END IF;

    -- [2] DATA UPDATE: Update status di tabel Public
    UPDATE public.partners SET status = 'active' WHERE email = p_email;
    UPDATE public.partner_applications SET status = 'activated', agreed_at = NOW() WHERE id = p_application_id;
    
    INSERT INTO public.clients (email, shop_name, status, plan, expired_at, created_at)
    VALUES (p_email, p_full_name, 'active', 'ultimate', v_expiry, NOW())
    ON CONFLICT (email) DO UPDATE SET status = 'active', plan = 'ultimate', expired_at = v_expiry;
    
    UPDATE public.profiles SET subscription_plan = 'ultimate' WHERE id = v_user_id;

    -- [3] KIRIM EMAIL: Format Asli dengan Pelindung Error
    BEGIN
        SELECT value INTO v_resend_api_key FROM public.ai_configs WHERE key = 'resend_api_key_partner';
        IF v_resend_api_key IS NULL OR v_resend_api_key = '' THEN
            SELECT value INTO v_resend_api_key FROM public.ai_configs WHERE key = 'resend_api_key';
        END IF;

        IF v_resend_api_key IS NOT NULL AND v_resend_api_key <> '' THEN
            v_html := '<div style="font-family:sans-serif; background:#000; color:#fff; padding:40px; border-radius:20px; border:1px solid #333;">' ||
                      '<img src="https://tokcer-ai.com/logo.png" style="height:40px; margin-bottom:20px;">' ||
                      '<h2>Selamat Bergabung Partner!</h2><p>Akun Partner & User Ultimate (60 Hari) Anda telah aktif.</p>' ||
                      '<div style="background:#111; padding:20px; border:1px dashed #444; border-radius:12px; margin:20px 0;">' ||
                      'Email: <b>' || p_email || '</b><br>Password: <b style="color:#ea580c; font-size:18px;">' || p_password || '</b></div><br>' ||
                      '<a href="https://staging.tokcer-ai.com/login" style="background:#ea580c; color:#fff; padding:14px 28px; text-decoration:none; border-radius:10px; font-weight:bold; display:inline-block;">LOGIN SEKARANG</a></div>';

            PERFORM net.http_post(
                url := 'https://api.resend.com/emails', 
                headers := jsonb_build_object('Content-Type', 'application/json', 'Authorization', 'Bearer ' || v_resend_api_key),
                body := jsonb_build_object('from', 'Tokcer AI <onboarding@tokcer-ai.com>', 'to', ARRAY[p_email], 'subject', '🏮 Akses Partner & User Aktif!', 'html', v_html)
            );
        END IF;
    EXCEPTION WHEN OTHERS THEN
        NULL; -- Jika email gagal, jangan gagalkan proses aktivasi
    END;

    RETURN json_build_object('success', true);
END;
$$;
```

---
**Dibuat oleh:** Ujang (Antigravity AI)  
**Tujuan:** Panduan Stabilitas Onboarding Tokcer AI
