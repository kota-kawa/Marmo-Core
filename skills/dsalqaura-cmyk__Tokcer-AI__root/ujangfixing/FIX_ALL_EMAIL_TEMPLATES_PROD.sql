-- =============================================================================
-- 📧 FIX ALL EMAIL TEMPLATES - PRODUCTION
-- Jalankan di: Supabase Production SQL Editor
-- Tujuan: Standardisasi semua template email dengan branding Tokcer AI
-- =============================================================================

-- Definisikan shared HTML template (header + footer) sebagai helper
-- Semua email menggunakan struktur yang sama dan URL production

-- =============================================================================
-- [1] WELCOME EMAIL — Demo User baru mendaftar (belum approved)
-- Dipanggil oleh: DemoRegisterModal.jsx → supabase.rpc('rpc_send_demo_welcome')
-- =============================================================================
CREATE OR REPLACE FUNCTION public.rpc_send_demo_welcome(
    p_email TEXT,
    p_name TEXT
)
RETURNS JSON LANGUAGE plpgsql SECURITY DEFINER AS $$
DECLARE
    v_resend_api_key TEXT;
    v_html TEXT;
BEGIN
    SELECT value INTO v_resend_api_key FROM public.ai_configs WHERE key = 'resend_api_key';

    v_html :=
        '<div style="margin:0;padding:0;background:#09090b;font-family:''Inter'',sans-serif;">' ||
        '<table width="100%" cellpadding="0" cellspacing="0" style="background:#09090b;padding:40px 20px;">' ||
        '<tr><td align="center">' ||
        '<table width="100%" style="max-width:560px;background:#18181b;border:1px solid #27272a;border-radius:20px;overflow:hidden;">' ||
        -- Header
        '<tr><td style="background:linear-gradient(135deg,#4f46e5,#7c3aed);padding:32px 40px;">' ||
        '<h1 style="margin:0;color:#fff;font-size:22px;font-weight:800;letter-spacing:-0.5px;">TOKCER <span style="color:#a5b4fc;">AI</span></h1>' ||
        '<p style="margin:4px 0 0;color:#c4b5fd;font-size:12px;font-weight:500;letter-spacing:2px;text-transform:uppercase;">Marketplace Intelligence</p>' ||
        '</td></tr>' ||
        -- Body
        '<tr><td style="padding:40px;">' ||
        '<h2 style="margin:0 0 16px;color:#fff;font-size:20px;font-weight:700;">Halo, ' || p_name || '! 👋</h2>' ||
        '<p style="margin:0 0 24px;color:#a1a1aa;font-size:14px;line-height:1.7;">Terima kasih telah mendaftar akses <b style="color:#a5b4fc;">Demo Tokcer AI</b>. Permohonan Anda telah kami terima dan sedang dalam antrian review tim kami.</p>' ||
        '<div style="background:#09090b;border:1px solid #3f3f46;border-left:3px solid #6366f1;border-radius:12px;padding:20px 24px;margin:0 0 24px;">' ||
        '<p style="margin:0 0 12px;color:#e4e4e7;font-size:13px;font-weight:700;">📋 Langkah Selanjutnya:</p>' ||
        '<ol style="margin:0;padding-left:20px;color:#a1a1aa;font-size:13px;line-height:2;">' ||
        '<li>Tim kami akan meninjau data pendaftaran Anda</li>' ||
        '<li>Apabila disetujui, Anda akan menerima email dengan kredensial login</li>' ||
        '<li>Proses review maksimal <b style="color:#fff;">1×24 jam kerja</b></li>' ||
        '</ol>' ||
        '</div>' ||
        '<p style="margin:0;color:#71717a;font-size:13px;">Harap bersabar. Kami akan segera menghubungi Anda melalui email ini.</p>' ||
        '</td></tr>' ||
        -- Footer
        '<tr><td style="padding:20px 40px;border-top:1px solid #27272a;">' ||
        '<p style="margin:0;color:#52525b;font-size:11px;text-align:center;">© 2026 Tokcer AI · <a href="https://tokcer-ai.com" style="color:#6366f1;text-decoration:none;">tokcer-ai.com</a></p>' ||
        '</td></tr>' ||
        '</table></td></tr></table></div>';

    IF v_resend_api_key IS NOT NULL AND v_resend_api_key <> '' THEN
        PERFORM net.http_post(
            url := 'https://api.resend.com/emails',
            headers := jsonb_build_object('Content-Type', 'application/json', 'Authorization', 'Bearer ' || v_resend_api_key),
            body := jsonb_build_object(
                'from', 'Tokcer AI <onboarding@tokcer-ai.com>',
                'to', ARRAY[p_email],
                'subject', '🚀 Permohonan Demo Tokcer AI Anda Telah Diterima!',
                'html', v_html
            )
        );
    END IF;

    RETURN json_build_object('success', true);
END;
$$;


-- =============================================================================
-- [2] APPROVAL EMAIL — Demo User disetujui oleh Admin
-- Dipanggil oleh: rpc_activate_demo (otomatis saat admin klik Approve)
-- =============================================================================
CREATE OR REPLACE FUNCTION public.rpc_activate_demo(
    p_application_id UUID,
    p_email TEXT,
    p_name TEXT,
    p_password TEXT
)
RETURNS JSON LANGUAGE plpgsql SECURITY DEFINER AS $$
DECLARE
    v_user_id UUID;
    v_resend_api_key TEXT;
    v_html TEXT;
BEGIN
    -- Cek apakah user sudah ada
    SELECT id INTO v_user_id FROM auth.users WHERE email = p_email;

    IF v_user_id IS NULL THEN
        v_user_id := gen_random_uuid();
        INSERT INTO auth.users (
            instance_id, id, aud, role, email, encrypted_password,
            email_confirmed_at, raw_app_meta_data, raw_user_meta_data, created_at, updated_at
        ) VALUES (
            '00000000-0000-0000-0000-000000000000', v_user_id, 'authenticated', 'authenticated',
            p_email, crypt(p_password, gen_salt('bf')),
            now(), '{"provider":"email","providers":["email"]}'::jsonb,
            jsonb_build_object('full_name', p_name), now(), now()
        );
        INSERT INTO auth.identities (id, user_id, identity_data, provider, provider_id, last_sign_in_at, created_at, updated_at)
        VALUES (gen_random_uuid(), v_user_id, jsonb_build_object('sub', v_user_id, 'email', p_email, 'email_verified', true), 'email', v_user_id::text, NOW(), NOW(), NOW());
    ELSE
        UPDATE auth.users SET encrypted_password = crypt(p_password, gen_salt('bf')), updated_at = NOW() WHERE id = v_user_id;
    END IF;

    UPDATE public.demo_applications SET status = 'approved' WHERE id = p_application_id;

    INSERT INTO public.profiles (id, email, full_name, subscription_plan, tokens, created_at)
    VALUES (v_user_id, p_email, p_name, 'demo', 30, NOW())
    ON CONFLICT (id) DO UPDATE SET subscription_plan = 'demo', tokens = 30;

    -- Kirim email approval
    SELECT value INTO v_resend_api_key FROM public.ai_configs WHERE key = 'resend_api_key';

    v_html :=
        '<div style="margin:0;padding:0;background:#09090b;font-family:''Inter'',sans-serif;">' ||
        '<table width="100%" cellpadding="0" cellspacing="0" style="background:#09090b;padding:40px 20px;">' ||
        '<tr><td align="center">' ||
        '<table width="100%" style="max-width:560px;background:#18181b;border:1px solid #27272a;border-radius:20px;overflow:hidden;">' ||
        -- Header
        '<tr><td style="background:linear-gradient(135deg,#059669,#0d9488);padding:32px 40px;">' ||
        '<h1 style="margin:0;color:#fff;font-size:22px;font-weight:800;letter-spacing:-0.5px;">TOKCER <span style="color:#6ee7b7;">AI</span></h1>' ||
        '<p style="margin:4px 0 0;color:#a7f3d0;font-size:12px;font-weight:500;letter-spacing:2px;text-transform:uppercase;">Akun Demo Anda Aktif!</p>' ||
        '</td></tr>' ||
        -- Body
        '<tr><td style="padding:40px;">' ||
        '<h2 style="margin:0 0 8px;color:#fff;font-size:20px;font-weight:700;">Selamat, ' || p_name || '! 🎉</h2>' ||
        '<p style="margin:0 0 24px;color:#a1a1aa;font-size:14px;line-height:1.7;">Permohonan akses Demo Tokcer AI Anda telah <b style="color:#34d399;">disetujui</b>. Berikut adalah kredensial login Anda.</p>' ||
        '<div style="background:#09090b;border:1px solid #3f3f46;border-radius:12px;padding:24px;margin:0 0 24px;">' ||
        '<p style="margin:0 0 16px;color:#71717a;font-size:11px;font-weight:700;letter-spacing:2px;text-transform:uppercase;">Kredensial Login</p>' ||
        '<table width="100%" cellpadding="0" cellspacing="0">' ||
        '<tr><td style="padding:8px 0;color:#a1a1aa;font-size:13px;">Email</td><td style="padding:8px 0;color:#e4e4e7;font-size:13px;font-weight:600;text-align:right;">' || p_email || '</td></tr>' ||
        '<tr style="border-top:1px solid #27272a;"><td style="padding:12px 0 8px;color:#a1a1aa;font-size:13px;">Password</td><td style="padding:12px 0 8px;text-align:right;"><span style="background:#ea580c;color:#fff;font-size:15px;font-weight:800;padding:6px 14px;border-radius:8px;letter-spacing:1px;">' || p_password || '</span></td></tr>' ||
        '</table></div>' ||
        '<div style="background:#1c1917;border:1px solid #292524;border-radius:12px;padding:16px 20px;margin:0 0 28px;">' ||
        '<p style="margin:0 0 8px;color:#e4e4e7;font-size:13px;font-weight:600;">✨ Yang Anda Dapatkan (Plan Demo):</p>' ||
        '<ul style="margin:0;padding-left:20px;color:#a1a1aa;font-size:13px;line-height:2;">' ||
        '<li>HPP + Margin Calculator (Akses Penuh)</li>' ||
        '<li>AI Script Generator (30 Credits)</li>' ||
        '<li>Market Intel Dashboard</li>' ||
        '<li>Masa aktif: <b style="color:#fff;">14 hari</b></li>' ||
        '</ul></div>' ||
        '<a href="https://tokcer-ai.com/login" style="display:block;text-align:center;background:linear-gradient(135deg,#059669,#0d9488);color:#fff;font-size:14px;font-weight:700;padding:14px 28px;border-radius:12px;text-decoration:none;letter-spacing:0.5px;">🚀 Login Sekarang →</a>' ||
        '</td></tr>' ||
        -- Footer
        '<tr><td style="padding:20px 40px;border-top:1px solid #27272a;">' ||
        '<p style="margin:0;color:#52525b;font-size:11px;text-align:center;">© 2026 Tokcer AI · <a href="https://tokcer-ai.com" style="color:#6366f1;text-decoration:none;">tokcer-ai.com</a></p>' ||
        '</td></tr>' ||
        '</table></td></tr></table></div>';

    IF v_resend_api_key IS NOT NULL AND v_resend_api_key <> '' THEN
        PERFORM net.http_post(
            url := 'https://api.resend.com/emails',
            headers := jsonb_build_object('Content-Type', 'application/json', 'Authorization', 'Bearer ' || v_resend_api_key),
            body := jsonb_build_object(
                'from', 'Tokcer AI <onboarding@tokcer-ai.com>',
                'to', ARRAY[p_email],
                'subject', '✅ Akun Demo Tokcer AI Anda Telah Aktif!',
                'html', v_html
            )
        );
    END IF;

    RETURN json_build_object('success', true, 'user_id', v_user_id);
END;
$$;


-- =============================================================================
-- [3] PARTNER ACTIVATION EMAIL — Partner disetujui
-- Dipanggil oleh: rpc_activate_partner
-- =============================================================================
CREATE OR REPLACE FUNCTION public.rpc_activate_partner(
    p_email TEXT,
    p_application_id UUID,
    p_full_name TEXT,
    p_password TEXT
)
RETURNS JSON LANGUAGE plpgsql SECURITY DEFINER AS $$
DECLARE
    v_user_id UUID;
    v_resend_api_key TEXT;
    v_html TEXT;
    v_expiry TIMESTAMP := NOW() + INTERVAL '60 days';
BEGIN
    SELECT id INTO v_user_id FROM auth.users WHERE email = p_email;
    IF v_user_id IS NULL THEN
        v_user_id := gen_random_uuid();
        INSERT INTO auth.users (
            instance_id, id, aud, role, email, encrypted_password,
            email_confirmed_at, raw_app_meta_data, raw_user_meta_data, created_at, updated_at
        ) VALUES (
            '00000000-0000-0000-0000-000000000000', v_user_id, 'authenticated', 'authenticated',
            p_email, crypt(p_password, gen_salt('bf')),
            now(), '{"provider":"email","providers":["email"]}'::jsonb,
            jsonb_build_object('full_name', p_full_name), now(), now()
        );
        INSERT INTO auth.identities (id, user_id, identity_data, provider, provider_id, last_sign_in_at, created_at, updated_at)
        VALUES (gen_random_uuid(), v_user_id, jsonb_build_object('sub', v_user_id, 'email', p_email, 'email_verified', true), 'email', v_user_id::text, NOW(), NOW(), NOW());
    ELSE
        UPDATE auth.users SET encrypted_password = crypt(p_password, gen_salt('bf')), updated_at = NOW() WHERE id = v_user_id;
        IF NOT EXISTS (SELECT 1 FROM auth.identities WHERE user_id = v_user_id AND provider = 'email') THEN
            INSERT INTO auth.identities (id, user_id, identity_data, provider, provider_id, last_sign_in_at, created_at, updated_at)
            VALUES (gen_random_uuid(), v_user_id, jsonb_build_object('sub', v_user_id, 'email', p_email, 'email_verified', true), 'email', v_user_id::text, NOW(), NOW(), NOW());
        ELSE
            UPDATE auth.identities SET provider_id = v_user_id::text, identity_data = jsonb_build_object('sub', v_user_id, 'email', p_email, 'email_verified', true) WHERE user_id = v_user_id AND provider = 'email';
        END IF;
    END IF;

    UPDATE public.partners SET id = v_user_id, status = 'active' WHERE email = p_email;
    UPDATE public.partner_applications SET status = 'activated', agreed_at = NOW() WHERE id = p_application_id;

    INSERT INTO public.clients (email, shop_name, status, plan, expired_at, created_at)
    VALUES (p_email, p_full_name, 'active', 'ultimate', v_expiry, NOW())
    ON CONFLICT (email) DO UPDATE SET status = 'active', plan = 'ultimate', expired_at = v_expiry;

    UPDATE public.profiles SET subscription_plan = 'ultimate' WHERE id = v_user_id;

    SELECT value INTO v_resend_api_key FROM public.ai_configs WHERE key = 'resend_api_key';

    v_html :=
        '<div style="margin:0;padding:0;background:#09090b;font-family:''Inter'',sans-serif;">' ||
        '<table width="100%" cellpadding="0" cellspacing="0" style="background:#09090b;padding:40px 20px;">' ||
        '<tr><td align="center">' ||
        '<table width="100%" style="max-width:560px;background:#18181b;border:1px solid #27272a;border-radius:20px;overflow:hidden;">' ||
        -- Header
        '<tr><td style="background:linear-gradient(135deg,#d97706,#ea580c);padding:32px 40px;">' ||
        '<h1 style="margin:0;color:#fff;font-size:22px;font-weight:800;letter-spacing:-0.5px;">TOKCER <span style="color:#fde68a;">AI</span></h1>' ||
        '<p style="margin:4px 0 0;color:#fef3c7;font-size:12px;font-weight:500;letter-spacing:2px;text-transform:uppercase;">Partner · Ultimate Plan</p>' ||
        '</td></tr>' ||
        -- Body
        '<tr><td style="padding:40px;">' ||
        '<h2 style="margin:0 0 8px;color:#fff;font-size:20px;font-weight:700;">Selamat Bergabung, ' || p_full_name || '! 🏆</h2>' ||
        '<p style="margin:0 0 24px;color:#a1a1aa;font-size:14px;line-height:1.7;">Akun <b style="color:#fbbf24;">Partner</b> Anda telah aktif. Anda kini memiliki akses penuh ke semua fitur Tokcer AI dengan <b style="color:#fff;">Plan Ultimate selama 60 hari</b>.</p>' ||
        '<div style="background:#09090b;border:1px solid #3f3f46;border-radius:12px;padding:24px;margin:0 0 24px;">' ||
        '<p style="margin:0 0 16px;color:#71717a;font-size:11px;font-weight:700;letter-spacing:2px;text-transform:uppercase;">Kredensial Login</p>' ||
        '<table width="100%" cellpadding="0" cellspacing="0">' ||
        '<tr><td style="padding:8px 0;color:#a1a1aa;font-size:13px;">Email</td><td style="padding:8px 0;color:#e4e4e7;font-size:13px;font-weight:600;text-align:right;">' || p_email || '</td></tr>' ||
        '<tr style="border-top:1px solid #27272a;"><td style="padding:12px 0 8px;color:#a1a1aa;font-size:13px;">Password</td><td style="padding:12px 0 8px;text-align:right;"><span style="background:#ea580c;color:#fff;font-size:15px;font-weight:800;padding:6px 14px;border-radius:8px;letter-spacing:1px;">' || p_password || '</span></td></tr>' ||
        '</table></div>' ||
        '<a href="https://tokcer-ai.com/login" style="display:block;text-align:center;background:linear-gradient(135deg,#d97706,#ea580c);color:#fff;font-size:14px;font-weight:700;padding:14px 28px;border-radius:12px;text-decoration:none;letter-spacing:0.5px;">🚀 Mulai Sekarang →</a>' ||
        '</td></tr>' ||
        -- Footer
        '<tr><td style="padding:20px 40px;border-top:1px solid #27272a;">' ||
        '<p style="margin:0;color:#52525b;font-size:11px;text-align:center;">© 2026 Tokcer AI · <a href="https://tokcer-ai.com" style="color:#6366f1;text-decoration:none;">tokcer-ai.com</a></p>' ||
        '</td></tr>' ||
        '</table></td></tr></table></div>';

    IF v_resend_api_key IS NOT NULL AND v_resend_api_key <> '' THEN
        PERFORM net.http_post(
            url := 'https://api.resend.com/emails',
            headers := jsonb_build_object('Content-Type', 'application/json', 'Authorization', 'Bearer ' || v_resend_api_key),
            body := jsonb_build_object(
                'from', 'Tokcer AI <onboarding@tokcer-ai.com>',
                'to', ARRAY[p_email],
                'subject', '🏆 Akun Partner Tokcer AI Anda Telah Aktif!',
                'html', v_html
            )
        );
    END IF;

    RETURN json_build_object('success', true);
END;
$$;
