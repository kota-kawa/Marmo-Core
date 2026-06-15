-- ==============================================================================
-- 🏮 TOKCER AI: FIX PRODUCTION BUGS (v11)
-- Penutup Celah Kritis (Gap 1, 2, 8) sesuai instruksi Board Member
-- ==============================================================================

-- ==============================================================================
-- FASE 1: PERBAIKAN MESIN MANUAL (rpc_activate_emergency_user)
-- Fix Gap 1: Mengambil plan dinamis dari tabel clients (tidak hardcode ultimate)
-- Fix Gap 2: Menggunakan link production tokcer-ai.com
-- ==============================================================================
CREATE OR REPLACE FUNCTION public.rpc_activate_emergency_user(
    p_email TEXT,
    p_client_id UUID,
    p_full_name TEXT,
    p_password TEXT
)
RETURNS JSON LANGUAGE plpgsql SECURITY DEFINER AS $$
DECLARE
    v_user_id UUID;
    v_resend_api_key TEXT;
    v_html TEXT;
    v_expiry TIMESTAMP;
    v_plan TEXT;
    v_billing_cycle TEXT;
BEGIN
    -- 1. Ambil plan dan billing cycle asli dari pendaftaran klien
    SELECT plan, billing_cycle INTO v_plan, v_billing_cycle FROM public.clients WHERE id = p_client_id;
    IF v_plan IS NULL THEN v_plan := 'pro'; END IF;

    -- 2. Tentukan expiry berdasarkan billing_cycle
    IF v_billing_cycle = 'Yearly' THEN
        v_expiry := NOW() + INTERVAL '365 days';
    ELSE
        v_expiry := NOW() + INTERVAL '30 days';
    END IF;

    -- 3. Auth User Management (DENGAN IDEMPOTENSI DAN AUTO-REPAIR)
    SELECT id INTO v_user_id FROM auth.users WHERE email = p_email;
    
    IF v_user_id IS NULL THEN
        v_user_id := gen_random_uuid();
        INSERT INTO auth.users (instance_id, id, aud, role, email, encrypted_password, email_confirmed_at, raw_app_meta_data, raw_user_meta_data, is_super_admin, created_at, updated_at, last_sign_in_at, confirmation_token, recovery_token, email_change_token_new, email_change)
        VALUES ('00000000-0000-0000-0000-000000000000', v_user_id, 'authenticated', 'authenticated', p_email, crypt(p_password, gen_salt('bf')), NOW(), '{"provider":"email","providers":["email"]}', jsonb_build_object('full_name', p_full_name), false, NOW(), NOW(), NOW(), '', '', '', '');
        
        INSERT INTO auth.identities (id, user_id, identity_data, provider, provider_id, last_sign_in_at, created_at, updated_at)
        VALUES (gen_random_uuid(), v_user_id, jsonb_build_object('sub', v_user_id, 'email', p_email, 'email_verified', true), 'email', p_email, NOW(), NOW(), NOW());
    ELSE
        UPDATE auth.users SET encrypted_password = crypt(p_password, gen_salt('bf')), updated_at = NOW() WHERE id = v_user_id;
        
        IF NOT EXISTS (SELECT 1 FROM auth.identities WHERE user_id = v_user_id) THEN
            INSERT INTO auth.identities (id, user_id, identity_data, provider, provider_id, last_sign_in_at, created_at, updated_at)
            VALUES (gen_random_uuid(), v_user_id, jsonb_build_object('sub', v_user_id, 'email', p_email, 'email_verified', true), 'email', p_email, NOW(), NOW(), NOW());
        ELSE
            UPDATE auth.identities SET identity_data = jsonb_set(identity_data, '{email_verified}', 'true'::jsonb), updated_at = NOW() WHERE user_id = v_user_id;
        END IF;
    END IF;

    -- 4. Update status klien & profile
    UPDATE public.clients SET status = 'active', plan = v_plan, expired_at = v_expiry WHERE id = p_client_id;
    
    INSERT INTO public.profiles (id, full_name, email, role, subscription_plan)
    VALUES (v_user_id, p_full_name, p_email, 'user', v_plan)
    ON CONFLICT (id) DO UPDATE SET subscription_plan = v_plan;

    -- 5. Kirim Email Notifikasi (Fix Gap 2: Link Staging dihapus, teks bonus Ultimate dihapus)
    SELECT value INTO v_resend_api_key FROM public.ai_configs WHERE key = 'resend_api_key';
    v_html := '<div style="font-family:sans-serif; background:#000; color:#fff; padding:40px; border-radius:20px; border:1px solid #333;">' ||
              '<img src="https://tokcer-ai.com/logo.png" style="height:40px; margin-bottom:20px;">' ||
              '<h2>Akun Tokcer AI Aktif!</h2><p>Pembayaran Anda untuk paket <b>' || upper(v_plan) || '</b> telah diverifikasi admin.</p>' ||
              '<div style="background:#111; padding:20px; border:1px dashed #444; border-radius:12px; margin:20px 0;">' ||
              'Email: <b>' || p_email || '</b><br>Password: <b style="color:#ea580c; font-size:18px;">' || p_password || '</b></div><br>' ||
              '<a href="https://tokcer-ai.com/login" style="background:#ea580c; color:#fff; padding:14px 28px; text-decoration:none; border-radius:10px; font-weight:bold; display:inline-block;">LOGIN SEKARANG</a></div>';
    
    IF v_resend_api_key IS NOT NULL AND v_resend_api_key <> '' THEN
        PERFORM net.http_post(url := 'https://api.resend.com/emails', headers := jsonb_build_object('Content-Type', 'application/json', 'Authorization', 'Bearer ' || v_resend_api_key),
        body := jsonb_build_object('from', 'Tokcer AI <onboarding@tokcer-ai.com>', 'to', ARRAY[p_email], 'subject', '🚀 Akun Anda Telah Aktif!', 'html', v_html));
    END IF;

    RETURN json_build_object('success', true);
END;
$$;


-- ==============================================================================
-- FASE 2: PERBAIKAN MESIN PENYIAPAN KLIENT (rpc_setup_client_account)
-- Fix Gap 8: Menerima password dari luar (Edge Function) agar dinamis & aman.
-- ==============================================================================
CREATE OR REPLACE FUNCTION public.rpc_setup_client_account(
    p_user_id UUID,
    p_email TEXT,
    p_application_id UUID,
    p_full_name TEXT,
    p_plan TEXT,
    p_role TEXT DEFAULT 'user',
    p_password TEXT DEFAULT 'Tokcer@2026'
)
RETURNS JSON LANGUAGE plpgsql SECURITY DEFINER AS $$
DECLARE
    v_user_id UUID := p_user_id;
    v_client_record RECORD;
    v_plan_key TEXT;
    v_billing_cycle TEXT;
    v_tokens BIGINT;
    v_partner_id UUID;
    v_partner_tier TEXT;
    v_commission BIGINT := 0;
    v_annual_bonus BIGINT := 0;
    v_active_count INT;
    v_elite_count INT;
    v_comm_rates JSONB;
    v_annual_bonuses JSONB;
BEGIN
    SELECT * INTO v_client_record FROM public.clients WHERE id = p_application_id OR email = p_email LIMIT 1;
    v_billing_cycle := COALESCE(v_client_record.billing_cycle, 'Monthly');
    v_plan_key := lower(COALESCE(p_plan, v_client_record.plan, 'starter'));

    v_tokens := CASE 
        WHEN v_plan_key = 'pro' THEN 300
        WHEN v_plan_key = 'elite' THEN 1000
        WHEN v_plan_key = 'ultimate' THEN 3000
        ELSE 50
    END;

    -- [1] User Creation
    IF v_user_id IS NULL THEN
        SELECT id INTO v_user_id FROM auth.users WHERE email = p_email;
    END IF;

    IF v_user_id IS NULL THEN
        v_user_id := gen_random_uuid();
        INSERT INTO auth.users (instance_id, id, aud, role, email, encrypted_password, email_confirmed_at, raw_app_meta_data, raw_user_meta_data, created_at, updated_at)
        VALUES ('00000000-0000-0000-0000-000000000000', v_user_id, 'authenticated', 'authenticated', p_email, crypt(p_password, gen_salt('bf')), now(), '{"provider":"email","providers":["email"]}'::jsonb, jsonb_build_object('full_name', p_full_name), now(), now());
        
        INSERT INTO auth.identities (id, user_id, identity_data, provider, provider_id, last_sign_in_at, created_at, updated_at)
        VALUES (gen_random_uuid(), v_user_id, jsonb_build_object('sub', v_user_id, 'email', p_email, 'email_verified', true), 'email', p_email, NOW(), NOW(), NOW());
    ELSE
        -- Update password if exists
        UPDATE auth.users SET encrypted_password = crypt(p_password, gen_salt('bf')), updated_at = NOW() WHERE id = v_user_id;
        
        IF NOT EXISTS (SELECT 1 FROM auth.identities WHERE user_id = v_user_id) THEN
            INSERT INTO auth.identities (id, user_id, identity_data, provider, provider_id, last_sign_in_at, created_at, updated_at)
            VALUES (gen_random_uuid(), v_user_id, jsonb_build_object('sub', v_user_id, 'email', p_email, 'email_verified', true), 'email', p_email, NOW(), NOW(), NOW());
        END IF;
    END IF;

    -- [2] Profile Creation
    INSERT INTO public.profiles (id, full_name, email, role, subscription_plan, ai_tokens)
    VALUES (v_user_id, p_full_name, p_email, p_role, v_plan_key, v_tokens)
    ON CONFLICT (id) DO UPDATE SET subscription_plan = v_plan_key, ai_tokens = profiles.ai_tokens + v_tokens;

    -- [3] Update Client Status & Expiry
    IF v_client_record.id IS NOT NULL THEN
        UPDATE public.clients SET 
            status = 'active', 
            plan = v_plan_key, 
            expires_at = NOW() + CASE WHEN v_billing_cycle = 'Yearly' THEN INTERVAL '365 days' ELSE INTERVAL '30 days' END 
        WHERE id = v_client_record.id;

        -- [4] Partner Commission Logic
        IF v_plan_key <> 'starter' THEN
            v_partner_id := v_client_record.partner_id;
            IF v_partner_id IS NOT NULL THEN
                SELECT tier INTO v_partner_tier FROM public.partners WHERE id = v_partner_id;
                v_partner_tier := COALESCE(v_partner_tier, 'bronze');

                SELECT value::JSONB INTO v_comm_rates FROM public.ai_configs WHERE key = 'commission_rates_v3';
                SELECT value::JSONB INTO v_annual_bonuses FROM public.ai_configs WHERE key = 'annual_plan_bonuses';

                IF v_comm_rates IS NOT NULL THEN
                    v_commission := (v_comm_rates->v_plan_key->v_partner_tier)::BIGINT;
                    IF v_billing_cycle = 'Yearly' AND v_annual_bonuses IS NOT NULL THEN
                        v_annual_bonus := (v_annual_bonuses->v_plan_key)::BIGINT;
                        v_commission := (v_commission * 11) + v_annual_bonus;
                    END IF;

                    UPDATE public.partners SET total_omzet = COALESCE(total_omzet, 0) + v_commission WHERE id = v_partner_id;
                END IF;
            END IF;
        END IF;
    END IF;

    RETURN json_build_object('success', true, 'user_id', v_user_id);
END;
$$;
