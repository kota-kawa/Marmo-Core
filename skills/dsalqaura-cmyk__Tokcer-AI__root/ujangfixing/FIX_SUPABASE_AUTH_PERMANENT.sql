-- =========================================================================================
-- 🏮 THE ULTIMATE PERMANENT FIX FOR SUPABASE GOTRUE "Database error querying schema"
-- =========================================================================================

-- 1. AUTO-REPAIR ALL EXISTING USERS IN AUTH.USERS
UPDATE auth.users 
SET 
    is_super_admin = COALESCE(is_super_admin, false),
    is_sso_user = COALESCE(is_sso_user, false),
    raw_app_meta_data = COALESCE(raw_app_meta_data, '{"provider":"email","providers":["email"]}'::jsonb),
    raw_user_meta_data = COALESCE(raw_user_meta_data, '{}'::jsonb),
    confirmation_token = COALESCE(confirmation_token, ''),
    recovery_token = COALESCE(recovery_token, ''),
    email_change_token_new = COALESCE(email_change_token_new, ''),
    email_change = COALESCE(email_change, '')
WHERE is_super_admin IS NULL 
   OR is_sso_user IS NULL;

-- 2. AUTO-REPAIR IDENTITIES
UPDATE auth.identities
SET provider_id = user_id::text
WHERE provider = 'email' AND provider_id != user_id::text;

UPDATE auth.identities 
SET identity_data = jsonb_build_object('sub', user_id, 'email', (SELECT email FROM auth.users WHERE auth.users.id = auth.identities.user_id), 'email_verified', true)
WHERE provider = 'email' AND (identity_data->>'email_verified' IS NULL OR identity_data->>'sub' IS NULL);


-- =========================================================================================
-- 3. PERMANENT RPC OVERRIDES (100% GOTRUE COMPLIANT)
-- =========================================================================================

-- A. PARTNER ACTIVATION (TANPA MENGGANGGU FUNGSI EMAIL)
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
        )
        VALUES (
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
    v_html := '<div style="font-family:sans-serif; background:#000; color:#fff; padding:40px; border-radius:20px; border:1px solid #333;"><img src="https://tokcer-ai.com/logo.png" style="height:40px; margin-bottom:20px;"><h2>Selamat Bergabung Partner!</h2><p>Akun Partner & User Ultimate (60 Hari) Anda telah aktif.</p><div style="background:#111; padding:20px; border:1px dashed #444; border-radius:12px; margin:20px 0;">Email: <b>' || p_email || '</b><br>Password: <b style="color:#ea580c; font-size:18px;">' || p_password || '</b></div><br><a href="https://staging.tokcer-ai.com/login" style="background:#ea580c; color:#fff; padding:14px 28px; text-decoration:none; border-radius:10px; font-weight:bold; display:inline-block;">LOGIN SEKARANG</a></div>';
    
    IF v_resend_api_key IS NOT NULL AND v_resend_api_key <> '' THEN
        PERFORM net.http_post(url := 'https://api.resend.com/emails', headers := jsonb_build_object('Content-Type', 'application/json', 'Authorization', 'Bearer ' || v_resend_api_key),
        body := jsonb_build_object('from', 'Tokcer AI <onboarding@tokcer-ai.com>', 'to', ARRAY[p_email], 'subject', '🏮 Akses Partner & User Aktif!', 'html', v_html));
    END IF;

    RETURN json_build_object('success', true);
END;
$$;
