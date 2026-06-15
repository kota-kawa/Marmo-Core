-- ==========================================================
-- SCRIPT PENAMBAHAN FITUR DEMO USER TOKCER AI
-- ==========================================================

-- 1. Buat tabel demo_applications
CREATE TABLE IF NOT EXISTS public.demo_applications (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    name TEXT NOT NULL,
    phone TEXT NOT NULL,
    email TEXT NOT NULL,
    marketplace TEXT NOT NULL,
    status TEXT DEFAULT 'pending',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Tambahkan RLS bypass untuk insert dari anon
ALTER TABLE public.demo_applications ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Enable insert for anon" ON public.demo_applications FOR INSERT WITH CHECK (true);
CREATE POLICY "Enable select for all" ON public.demo_applications FOR SELECT USING (true);
CREATE POLICY "Enable update for all" ON public.demo_applications FOR UPDATE USING (true);


-- 2. Buat RPC untuk approval demo user
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
        
        -- Insert ke auth.users
        INSERT INTO auth.users (
            instance_id, id, aud, role, email, encrypted_password, 
            email_confirmed_at, raw_app_meta_data, raw_user_meta_data, created_at, updated_at
        )
        VALUES (
            '00000000-0000-0000-0000-000000000000', v_user_id, 'authenticated', 'authenticated', 
            p_email, crypt(p_password, gen_salt('bf')), 
            now(), '{"provider":"email","providers":["email"]}'::jsonb, 
            jsonb_build_object('full_name', p_name), now(), now()
        );
        
        -- Insert ke auth.identities
        INSERT INTO auth.identities (id, user_id, identity_data, provider, provider_id, last_sign_in_at, created_at, updated_at)
        VALUES (gen_random_uuid(), v_user_id, jsonb_build_object('sub', v_user_id, 'email', p_email, 'email_verified', true), 'email', v_user_id::text, NOW(), NOW(), NOW());
    ELSE
        -- Update password jika sudah ada
        UPDATE auth.users SET encrypted_password = crypt(p_password, gen_salt('bf')), updated_at = NOW() WHERE id = v_user_id;
    END IF;

    -- Update tabel demo_applications menjadi approved
    UPDATE public.demo_applications SET status = 'approved' WHERE id = p_application_id;

    -- Buat/Update profile dengan plan demo dan 30 tokens
    INSERT INTO public.profiles (id, email, full_name, subscription_plan, tokens, created_at)
    VALUES (v_user_id, p_email, p_name, 'demo', 30, NOW())
    ON CONFLICT (id) DO UPDATE SET subscription_plan = 'demo', tokens = 30;

    -- Kirim Email
    SELECT value INTO v_resend_api_key FROM public.ai_configs WHERE key = 'resend_api_key';
    v_html := '<div style="font-family:sans-serif; background:#000; color:#fff; padding:40px; border-radius:20px; border:1px solid #333;"><img src="https://tokcer-ai.com/logo.png" style="height:40px; margin-bottom:20px;"><h2>Selamat! Akun Demo Anda Aktif</h2><p>Anda mendapatkan akses khusus (Plan: Demo) dengan gratis 30 AI Credits.</p><div style="background:#111; padding:20px; border:1px dashed #444; border-radius:12px; margin:20px 0;">Email: <b>' || p_email || '</b><br>Password: <b style="color:#ea580c; font-size:18px;">' || p_password || '</b></div><br><a href="https://staging.tokcer-ai.com/login" style="background:#ea580c; color:#fff; padding:14px 28px; text-decoration:none; border-radius:10px; font-weight:bold; display:inline-block;">LOGIN SEKARANG</a></div>';
    
    IF v_resend_api_key IS NOT NULL AND v_resend_api_key <> '' THEN
        PERFORM net.http_post(
            url := 'https://api.resend.com/emails', 
            headers := jsonb_build_object('Content-Type', 'application/json', 'Authorization', 'Bearer ' || v_resend_api_key),
            body := jsonb_build_object('from', 'Tokcer AI <onboarding@tokcer-ai.com>', 'to', ARRAY[p_email], 'subject', '🚀 Akses Demo Tokcer AI Anda Aktif!', 'html', v_html)
        );
    END IF;

    RETURN json_build_object('success', true, 'user_id', v_user_id);
END;
$$;
