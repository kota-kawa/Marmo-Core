-- ==============================================================================
-- 🏮 TOKCER AI: FIX ACTIVATION FUNCTIONS (v8) - IDEMPOTENT & AUTO-REPAIR
-- Menyatukan perbaikan untuk Fungsi Otomatis (rpc_activate_account)
-- dan Fungsi Manual (rpc_activate_emergency_user).
-- Dijamin tidak ada lagi eror "Database error querying schema" saat login.
-- ==============================================================================

-- ==============================================================================
-- FASE 2: PERBAIKAN MESIN OTOMATIS (rpc_activate_account)
-- Dipanggil otomatis oleh Webhook Midtrans dan Pendaftaran Partner.
-- ==============================================================================
CREATE OR REPLACE FUNCTION public.rpc_activate_account(
    p_email TEXT,
    p_application_id UUID,
    p_full_name TEXT,
    p_plan TEXT,
    p_role TEXT DEFAULT 'user' -- 'user' or 'partner'
)
RETURNS JSON
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
    v_user_id UUID;
    v_tokens INTEGER;
    v_client_record RECORD;
    v_partner_app_record RECORD;
    v_partner_id UUID;
    v_partner_tier TEXT;
    v_commission BIGINT := 0;
    v_active_count INTEGER;
    v_elite_count INTEGER;
    v_plan_key TEXT;
    v_billing_cycle TEXT;
    v_annual_bonus BIGINT := 0;
    v_comm_rates JSONB;
    v_annual_bonuses JSONB;
    v_milestone_bonus BIGINT := 0;
BEGIN
    -- 1. Identify context (Is it a Client or a Partner Application?)
    SELECT * INTO v_client_record FROM public.clients WHERE id = p_application_id OR email = p_email LIMIT 1;
    SELECT * INTO v_partner_app_record FROM public.partner_applications WHERE id = p_application_id OR email = p_email LIMIT 1;

    v_billing_cycle := COALESCE(v_client_record.billing_cycle, 'Monthly');
    v_plan_key := lower(COALESCE(p_plan, v_client_record.plan, 'starter'));

    -- 2. Determine Tokens (Credits)
    v_tokens := CASE 
        WHEN v_plan_key = 'starter' THEN 50
        WHEN v_plan_key = 'pro' THEN 300
        WHEN v_plan_key = 'elite' THEN 1000
        WHEN v_plan_key = 'ultimate' THEN 3000
        ELSE 50
    END;

    -- 3. Auth User Management (DENGAN IDEMPOTENSI DAN AUTO-REPAIR)
    SELECT id INTO v_user_id FROM auth.users WHERE email = p_email;

    IF v_user_id IS NULL THEN
        -- A. User benar-benar baru, buat dari awal
        v_user_id := gen_random_uuid();
        INSERT INTO auth.users (
            instance_id, id, aud, role, email, encrypted_password, 
            email_confirmed_at, recovery_sent_at, last_sign_in_at, 
            raw_app_meta_data, raw_user_meta_data, created_at, updated_at, 
            confirmation_token, email_change, email_change_token_new, recovery_token
        )
        VALUES (
            '00000000-0000-0000-0000-000000000000', v_user_id, 'authenticated', 'authenticated', 
            p_email, crypt('Tokcer@2026', gen_salt('bf')), 
            now(), now(), now(), 
            '{"provider":"email","providers":["email"]}'::jsonb, 
            jsonb_build_object('full_name', p_full_name), 
            now(), now(), '', '', '', ''
        );
        
        -- WAJIB: Buat Identitas agar bisa login
        INSERT INTO auth.identities (id, user_id, identity_data, provider, provider_id, last_sign_in_at, created_at, updated_at)
        VALUES (gen_random_uuid(), v_user_id, jsonb_build_object('sub', v_user_id, 'email', p_email, 'email_verified', true), 'email', p_email, NOW(), NOW(), NOW());
    ELSE
        -- B. User sudah ada, pastikan identitasnya sempurna (AUTO-REPAIR)
        IF NOT EXISTS (SELECT 1 FROM auth.identities WHERE user_id = v_user_id) THEN
            -- Identitas hilang (akibat eror masa lalu), buatkan sekarang
            INSERT INTO auth.identities (id, user_id, identity_data, provider, provider_id, last_sign_in_at, created_at, updated_at)
            VALUES (gen_random_uuid(), v_user_id, jsonb_build_object('sub', v_user_id, 'email', p_email, 'email_verified', true), 'email', p_email, NOW(), NOW(), NOW());
        ELSE
            -- Identitas ada tapi mungkin email_verified false, paksa perbarui
            UPDATE auth.identities 
            SET identity_data = jsonb_set(identity_data, '{email_verified}', 'true'::jsonb), updated_at = NOW() 
            WHERE user_id = v_user_id;
        END IF;
    END IF;

    -- 4. Create/Update Profile with Role
    INSERT INTO public.profiles (id, full_name, email, role, subscription_plan, ai_tokens)
    VALUES (v_user_id, p_full_name, p_email, p_role, v_plan_key, v_tokens)
    ON CONFLICT (id) DO UPDATE 
    SET subscription_plan = v_plan_key,
        ai_tokens = profiles.ai_tokens + v_tokens,
        role = CASE WHEN profiles.role = 'admin' THEN 'admin' ELSE p_role END;

    -- 5. Status Updates
    IF v_client_record.id IS NOT NULL THEN
        UPDATE public.clients SET status = 'active', plan = v_plan_key WHERE id = v_client_record.id;
    END IF;
    
    IF v_partner_app_record.id IS NOT NULL THEN
        UPDATE public.partner_applications SET status = 'active' WHERE id = v_partner_app_record.id;
        
        -- SYNC PARTNER RECORD
        INSERT INTO public.partners (id, email, full_name, whatsapp, status)
        VALUES (v_user_id, p_email, p_full_name, v_partner_app_record.whatsapp, 'active')
        ON CONFLICT (id) DO UPDATE SET status = 'active';
    END IF;

    -- 6. PARTNER COMMISSION LOGIC
    IF p_role = 'user' AND v_plan_key <> 'starter' THEN
        -- Find Referrer Partner
        v_partner_id := v_client_record.partner_id;
        IF v_partner_id IS NULL AND v_client_record.ref IS NOT NULL AND v_client_record.ref <> 'Direct Web' THEN
            SELECT id INTO v_partner_id FROM public.partners WHERE referral_code = v_client_record.ref LIMIT 1;
        END IF;

        IF v_partner_id IS NOT NULL THEN
            -- [PERBAIKAN UJANG]: Sync partner_id ke tabel clients agar hitungan valid
            UPDATE public.clients SET partner_id = v_partner_id WHERE id = v_client_record.id;

            -- Calculate Dynamic Tier
            SELECT count(*) INTO v_active_count FROM public.clients WHERE (partner_id = v_partner_id OR ref = (SELECT referral_code FROM public.partners WHERE id = v_partner_id)) AND status = 'active';
            SELECT count(*) INTO v_elite_count FROM public.clients WHERE (partner_id = v_partner_id OR ref = (SELECT referral_code FROM public.partners WHERE id = v_partner_id)) AND status = 'active' AND plan IN ('elite', 'ultimate');

            -- Tier Logic (Min Bronze)
            v_partner_tier := CASE 
                WHEN v_active_count >= 15 AND v_elite_count >= 5 THEN 'platinum'
                WHEN v_active_count >= 8 AND v_elite_count >= 2 THEN 'gold'
                WHEN v_active_count >= 5 AND v_elite_count >= 2 THEN 'silver'
                ELSE 'bronze'
            END;

            SELECT value::JSONB INTO v_comm_rates FROM public.ai_configs WHERE key = 'commission_rates_v3';
            SELECT value::JSONB INTO v_annual_bonuses FROM public.ai_configs WHERE key = 'annual_plan_bonuses';

            -- Hitung Komisi Dasar
            v_commission := (v_comm_rates->v_plan_key->v_partner_tier)::BIGINT;
            
            IF v_billing_cycle = 'Yearly' THEN
                v_annual_bonus := (v_annual_bonuses->v_plan_key)::BIGINT;
                v_commission := (v_commission * 11) + v_annual_bonus;
            END IF;

            -- LOGIKA BONUS PERFORMANCE (VOLUME MILESTONE)
            -- [PERBAIKAN UJANG]: Tambahkan INSERT ke ai_usage_logs agar tidak double bonus
            IF v_active_count >= 5 THEN
                IF NOT EXISTS (SELECT 1 FROM public.ai_usage_logs WHERE user_id = v_partner_id AND feature = 'partner_milestone_bonus' AND prompt LIKE '%Milestone: 5%') THEN
                    v_milestone_bonus := 150000;
                    INSERT INTO public.ai_usage_logs (user_id, feature, prompt) VALUES (v_partner_id, 'partner_milestone_bonus', 'Achieved Milestone: 5 clients');
                END IF;
            END IF;

            IF v_active_count >= 10 THEN
                IF NOT EXISTS (SELECT 1 FROM public.ai_usage_logs WHERE user_id = v_partner_id AND feature = 'partner_milestone_bonus' AND prompt LIKE '%Milestone: 10%') THEN
                    v_milestone_bonus := v_milestone_bonus + 350000;
                    INSERT INTO public.ai_usage_logs (user_id, feature, prompt) VALUES (v_partner_id, 'partner_milestone_bonus', 'Achieved Milestone: 10 clients');
                END IF;
            END IF;

            IF v_active_count >= 15 THEN
                IF NOT EXISTS (SELECT 1 FROM public.ai_usage_logs WHERE user_id = v_partner_id AND feature = 'partner_milestone_bonus' AND prompt LIKE '%Milestone: 15%') THEN
                    v_milestone_bonus := v_milestone_bonus + 750000;
                    INSERT INTO public.ai_usage_logs (user_id, feature, prompt) VALUES (v_partner_id, 'partner_milestone_bonus', 'Achieved Milestone: 15 clients');
                END IF;
            END IF;

            -- Tambahkan Bonus ke Komisi
            v_commission := v_commission + v_milestone_bonus;

            UPDATE public.partners 
            SET total_omzet = total_omzet + v_commission,
                tier = v_partner_tier
            WHERE id = v_partner_id;
        END IF;
    END IF;

    RETURN json_build_object(
        'success', true,
        'message', 'Activation successful for ' || p_role || '.',
        'user_id', v_user_id,
        'commission_credited', v_commission,
        'milestone_bonus_credited', v_milestone_bonus
    );
END;
$$;


-- ==============================================================================
-- FASE 3: PERBAIKAN MESIN MANUAL (rpc_activate_emergency_user)
-- Dipanggil saat Admin mengklik "Approve" untuk klien di Dashboard Internal.
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
    v_expiry TIMESTAMP := NOW() + INTERVAL '60 days';
BEGIN
    -- [1] Auth User Management (DENGAN IDEMPOTENSI DAN AUTO-REPAIR)
    SELECT id INTO v_user_id FROM auth.users WHERE email = p_email;
    
    IF v_user_id IS NULL THEN
        -- A. Jika BELUM ADA, buat user baru lengkap dengan identitas
        v_user_id := gen_random_uuid();
        INSERT INTO auth.users (instance_id, id, aud, role, email, encrypted_password, email_confirmed_at, raw_app_meta_data, raw_user_meta_data, is_super_admin, created_at, updated_at, last_sign_in_at, confirmation_token, recovery_token, email_change_token_new, email_change)
        VALUES ('00000000-0000-0000-0000-000000000000', v_user_id, 'authenticated', 'authenticated', p_email, crypt(p_password, gen_salt('bf')), NOW(), '{"provider":"email","providers":["email"]}', jsonb_build_object('full_name', p_full_name), false, NOW(), NOW(), NOW(), '', '', '', '');
        
        INSERT INTO auth.identities (id, user_id, identity_data, provider, provider_id, last_sign_in_at, created_at, updated_at)
        VALUES (gen_random_uuid(), v_user_id, jsonb_build_object('sub', v_user_id, 'email', p_email, 'email_verified', true), 'email', p_email, NOW(), NOW(), NOW());
    ELSE
        -- B. Jika SUDAH ADA, update password dan paksa perbaiki identitasnya
        UPDATE auth.users SET encrypted_password = crypt(p_password, gen_salt('bf')), updated_at = NOW() WHERE id = v_user_id;
        
        IF NOT EXISTS (SELECT 1 FROM auth.identities WHERE user_id = v_user_id) THEN
            INSERT INTO auth.identities (id, user_id, identity_data, provider, provider_id, last_sign_in_at, created_at, updated_at)
            VALUES (gen_random_uuid(), v_user_id, jsonb_build_object('sub', v_user_id, 'email', p_email, 'email_verified', true), 'email', p_email, NOW(), NOW(), NOW());
        ELSE
            UPDATE auth.identities SET identity_data = jsonb_set(identity_data, '{email_verified}', 'true'::jsonb), updated_at = NOW() WHERE user_id = v_user_id;
        END IF;
    END IF;

    -- [2] Update status klien & profile
    UPDATE public.clients SET status = 'active', plan = 'ultimate', expired_at = v_expiry WHERE id = p_client_id;
    UPDATE public.profiles SET subscription_plan = 'ultimate' WHERE id = v_user_id;

    -- [3] Kirim Email
    SELECT value INTO v_resend_api_key FROM public.ai_configs WHERE key = 'resend_api_key';
    v_html := '<div style="font-family:sans-serif; background:#000; color:#fff; padding:40px; border-radius:20px; border:1px solid #333;">' ||
              '<img src="https://tokcer-ai.com/logo.png" style="height:40px; margin-bottom:20px;">' ||
              '<h2>Akun Tokcer AI Aktif (Emergency)!</h2><p>Pembayaran Anda telah diverifikasi manual. Kami berikan bonus Ultimate 60 Hari.</p>' ||
              '<div style="background:#111; padding:20px; border:1px dashed #444; border-radius:12px; margin:20px 0;">' ||
              'Email: <b>' || p_email || '</b><br>Password: <b style="color:#ea580c; font-size:18px;">' || p_password || '</b></div><br>' ||
              '<a href="https://staging.tokcer-ai.com/login" style="background:#ea580c; color:#fff; padding:14px 28px; text-decoration:none; border-radius:10px; font-weight:bold; display:inline-block;">LOGIN SEKARANG</a></div>';
    
    IF v_resend_api_key IS NOT NULL AND v_resend_api_key <> '' THEN
        PERFORM net.http_post(url := 'https://api.resend.com/emails', headers := jsonb_build_object('Content-Type', 'application/json', 'Authorization', 'Bearer ' || v_resend_api_key),
        body := jsonb_build_object('from', 'Tokcer AI <onboarding@tokcer-ai.com>', 'to', ARRAY[p_email], 'subject', '🚀 Akun Emergency Aktif!', 'html', v_html));
    END IF;

    RETURN json_build_object('success', true);
END;
$$;
