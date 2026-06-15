-- ==============================================================================
-- 🏮 TOKCER AI: SUBSCRIPTION & CRON SYSTEM (SAFE MODE)
-- Penambahan Logic:
-- 1. Perbaikan rpc_activate_account (Menambahkan Update expires_at)
-- 2. Fungsi rpc_daily_subscription_check (Reset kuota Tahunan, Notif H-3 Bulanan)
-- ==============================================================================

-- ------------------------------------------------------------------------------
-- BAGIAN 1: PASTIKAN TABEL PUNYA KOLOM YANG DIBUTUHKAN
-- ------------------------------------------------------------------------------
ALTER TABLE public.clients ADD COLUMN IF NOT EXISTS expires_at TIMESTAMPTZ;

-- Backfill data lama (Jika ada yang kosong)
UPDATE public.clients
SET expires_at = created_at + INTERVAL '30 days'
WHERE status = 'active' AND billing_cycle = 'Monthly' AND expires_at IS NULL;

UPDATE public.clients
SET expires_at = created_at + INTERVAL '365 days'
WHERE status = 'active' AND billing_cycle = 'Yearly' AND expires_at IS NULL;

-- ------------------------------------------------------------------------------
-- BAGIAN 2: PERBAIKAN rpc_activate_account (SET EXPIRES_AT)
-- (Catatan: Ini aman, tidak mengubah logic komisi, hanya menempelkan expires_at)
-- ------------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION public.rpc_activate_account(
    p_email TEXT,
    p_application_id UUID,
    p_full_name TEXT,
    p_plan TEXT,
    p_role TEXT DEFAULT 'user' -- 'user' or 'partner'
)
RETURNS JSON LANGUAGE plpgsql SECURITY DEFINER AS $$
DECLARE
    v_user_id UUID;
    v_partner_id UUID;
    v_client_record RECORD;
    v_partner_app_record RECORD;
    v_plan_key TEXT;
    v_billing_cycle TEXT;
    v_tokens BIGINT;
    v_active_count INT;
    v_elite_count INT;
    v_partner_tier TEXT;
    v_comm_rates JSONB;
    v_annual_bonuses JSONB;
    v_commission BIGINT := 0;
    v_annual_bonus BIGINT := 0;
    v_is_new_period BOOLEAN := FALSE;
    v_expires_at TIMESTAMPTZ;
BEGIN
    -- 1. Identify context (Is it a Client or a Partner Application?)
    SELECT * INTO v_client_record FROM public.clients WHERE id = p_application_id OR email = p_email LIMIT 1;
    SELECT * INTO v_partner_app_record FROM public.partner_applications WHERE id = p_application_id OR email = p_email LIMIT 1;
    
    v_billing_cycle := COALESCE(v_client_record.billing_cycle, 'Monthly');
    v_plan_key := lower(COALESCE(p_plan, v_client_record.plan, 'starter'));

    -- 2. Determine Tokens and Expiration
    v_tokens := CASE 
        WHEN v_plan_key = 'pro' THEN 300
        WHEN v_plan_key = 'elite' THEN 1000
        WHEN v_plan_key = 'ultimate' THEN 3000
        ELSE 50
    END;

    v_expires_at := NOW() + CASE 
        WHEN v_billing_cycle = 'Yearly' THEN INTERVAL '365 days'
        ELSE INTERVAL '30 days'
    END;

    -- 3. Auth User Management (Idempotent)
    SELECT id INTO v_user_id FROM auth.users WHERE email = p_email;

    IF v_user_id IS NULL THEN
        v_user_id := gen_random_uuid();
        INSERT INTO auth.users (
            instance_id, id, aud, role, email, encrypted_password, 
            email_confirmed_at, raw_app_meta_data, raw_user_meta_data, created_at, updated_at
        )
        VALUES (
            '00000000-0000-0000-0000-000000000000', v_user_id, 'authenticated', 'authenticated', 
            p_email, crypt('Tokcer@2026', gen_salt('bf')), 
            now(), '{"provider":"email","providers":["email"]}'::jsonb, 
            jsonb_build_object('full_name', p_full_name), now(), now()
        );
        
        INSERT INTO auth.identities (id, user_id, identity_data, provider, provider_id, last_sign_in_at, created_at, updated_at)
        VALUES (gen_random_uuid(), v_user_id, jsonb_build_object('sub', v_user_id, 'email', p_email, 'email_verified', true), 'email', p_email, NOW(), NOW(), NOW());
    ELSE
        IF NOT EXISTS (SELECT 1 FROM auth.identities WHERE user_id = v_user_id) THEN
            INSERT INTO auth.identities (id, user_id, identity_data, provider, provider_id, last_sign_in_at, created_at, updated_at)
            VALUES (gen_random_uuid(), v_user_id, jsonb_build_object('sub', v_user_id, 'email', p_email, 'email_verified', true), 'email', p_email, NOW(), NOW(), NOW());
        ELSE
            UPDATE auth.identities SET identity_data = jsonb_set(identity_data, '{email_verified}', 'true'::jsonb), updated_at = NOW() WHERE user_id = v_user_id;
        END IF;
    END IF;

    -- 4. Create/Update Profile with Role
    INSERT INTO public.profiles (id, full_name, email, role, subscription_plan, ai_tokens)
    VALUES (v_user_id, p_full_name, p_email, p_role, v_plan_key, v_tokens)
    ON CONFLICT (id) DO UPDATE 
    SET subscription_plan = v_plan_key,
        ai_tokens = profiles.ai_tokens + v_tokens,
        role = CASE WHEN profiles.role = 'admin' THEN 'admin' ELSE p_role END;

    -- 5. Status & Expiration Updates
    IF v_client_record.id IS NOT NULL THEN
        UPDATE public.clients SET status = 'active', plan = v_plan_key, expires_at = v_expires_at WHERE id = v_client_record.id;
    END IF;
    
    IF v_partner_app_record.id IS NOT NULL THEN
        UPDATE public.partner_applications SET status = 'active' WHERE id = v_partner_app_record.id;
        INSERT INTO public.partners (id, email, full_name, whatsapp, status)
        VALUES (v_user_id, p_email, p_full_name, v_partner_app_record.whatsapp, 'active')
        ON CONFLICT (id) DO UPDATE SET status = 'active';
    END IF;

    -- 6. PARTNER COMMISSION LOGIC (Hanya sekali di periode saat ini)
    IF p_role = 'user' AND v_plan_key <> 'starter' THEN
        v_partner_id := v_client_record.partner_id;
        IF v_partner_id IS NULL AND v_client_record.ref IS NOT NULL AND v_client_record.ref <> 'Direct Web' THEN
            SELECT id INTO v_partner_id FROM public.partners WHERE referral_code = v_client_record.ref LIMIT 1;
        END IF;

        IF v_partner_id IS NOT NULL THEN
            UPDATE public.clients SET partner_id = v_partner_id WHERE id = v_client_record.id;

            -- Calculate Dynamic Tier
            SELECT count(*) INTO v_active_count FROM public.clients WHERE (partner_id = v_partner_id OR ref = (SELECT referral_code FROM public.partners WHERE id = v_partner_id)) AND status = 'active';
            SELECT count(*) INTO v_elite_count FROM public.clients WHERE (partner_id = v_partner_id OR ref = (SELECT referral_code FROM public.partners WHERE id = v_partner_id)) AND status = 'active' AND plan IN ('elite', 'ultimate');

            v_partner_tier := CASE 
                WHEN v_active_count >= 15 AND v_elite_count >= 5 THEN 'platinum'
                WHEN v_active_count >= 8 AND v_elite_count >= 2 THEN 'gold'
                WHEN v_active_count >= 5 AND v_elite_count >= 2 THEN 'silver'
                ELSE 'bronze'
            END;

            SELECT value::JSONB INTO v_comm_rates FROM public.ai_configs WHERE key = 'commission_rates_v3';
            SELECT value::JSONB INTO v_annual_bonuses FROM public.ai_configs WHERE key = 'annual_plan_bonuses';

            v_commission := (v_comm_rates->v_plan_key->v_partner_tier)::BIGINT;
            
            IF v_billing_cycle = 'Yearly' THEN
                v_annual_bonus := (v_annual_bonuses->v_plan_key)::BIGINT;
                v_commission := (v_commission * 11) + v_annual_bonus;
            END IF;

            SELECT (NOT EXISTS (
                SELECT 1 FROM public.partner_payouts 
                WHERE partner_id = v_partner_id 
                AND period_month = date_trunc('month', NOW())::DATE
            )) INTO v_is_new_period;

            IF v_is_new_period THEN
                UPDATE public.partners 
                SET total_omzet = COALESCE(total_omzet, 0) + v_commission, updated_at = NOW()
                WHERE id = v_partner_id;
            END IF;
        END IF;
    END IF;

    RETURN json_build_object('success', true, 'user_id', v_user_id, 'expires_at', v_expires_at);
END;
$$;


-- ------------------------------------------------------------------------------
-- BAGIAN 3: FUNGSI ROBOT CRON HARIAN
-- Digunakan untuk: 
-- 1. Me-reset token bulanan untuk paket Tahunan
-- 2. Mengirim Email H-3 untuk paket Bulanan
-- 3. Mengunci akun Bulanan yang sudah lewat masa aktif
-- ------------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION public.rpc_daily_subscription_check()
RETURNS JSON LANGUAGE plpgsql SECURITY DEFINER AS $$
DECLARE
    v_resend_api_key TEXT;
    v_client RECORD;
    v_html TEXT;
    v_base_tokens INT;
    v_updated_yearly INT := 0;
    v_emailed_h3 INT := 0;
    v_expired_monthly INT := 0;
BEGIN
    SELECT value INTO v_resend_api_key FROM public.ai_configs WHERE key = 'resend_api_key';

    -- ========================================================
    -- A. RESET TOKEN UNTUK USER TAHUNAN (Setiap Tanggal Join)
    -- ========================================================
    FOR v_client IN 
        SELECT c.email, p.id as user_id, c.plan
        FROM public.clients c
        JOIN public.profiles p ON c.email = p.email
        WHERE c.status = 'active' AND c.billing_cycle = 'Yearly'
          AND EXTRACT(DAY FROM c.created_at) = EXTRACT(DAY FROM NOW())
    LOOP
        v_base_tokens := CASE 
            WHEN v_client.plan = 'pro' THEN 300
            WHEN v_client.plan = 'elite' THEN 1000
            WHEN v_client.plan = 'ultimate' THEN 3000
            ELSE 50
        END;

        -- Kembalikan kuota ke kondisi penuh
        UPDATE public.profiles SET ai_tokens = v_base_tokens WHERE id = v_client.user_id;
        v_updated_yearly := v_updated_yearly + 1;
    END LOOP;

    -- ========================================================
    -- B. EMAIL H-3 JATUH TEMPO UNTUK USER BULANAN
    -- ========================================================
    FOR v_client IN 
        SELECT email, shop_name, plan, expires_at 
        FROM public.clients 
        WHERE status = 'active' AND billing_cycle = 'Monthly'
          AND DATE_TRUNC('day', expires_at) = DATE_TRUNC('day', NOW() + INTERVAL '3 days')
    LOOP
        IF v_resend_api_key IS NOT NULL AND v_resend_api_key <> '' THEN
            v_html := '<div style="font-family:sans-serif; background:#000; color:#fff; padding:40px; border-radius:20px; border:1px solid #333;">' ||
                      '<img src="https://tokcer-ai.com/logo.png" style="height:40px; margin-bottom:20px;">' ||
                      '<h2>Pemberitahuan Langganan Tokcer AI</h2>' ||
                      '<p>Halo <b>' || v_client.shop_name || '</b>, langganan paket <b>' || upper(v_client.plan) || '</b> Anda akan berakhir dalam 3 hari pada tanggal ' || to_char(v_client.expires_at, 'DD Mon YYYY') || '.</p>' ||
                      '<p>Silakan lakukan perpanjangan agar toko Anda tidak terhenti operasinya.</p>' ||
                      '<br><a href="https://staging.tokcer-ai.com/partner-dashboard" style="background:#ea580c; color:#fff; padding:14px 28px; text-decoration:none; border-radius:10px; font-weight:bold; display:inline-block;">PERPANJANG SEKARANG</a></div>';
            
            PERFORM net.http_post(
                url := 'https://api.resend.com/emails',
                headers := jsonb_build_object('Content-Type', 'application/json', 'Authorization', 'Bearer ' || v_resend_api_key),
                body := jsonb_build_object(
                    'from', 'Tokcer AI <billing@tokcer-ai.com>',
                    'to', ARRAY[v_client.email],
                    'subject', '⚠️ H-3 Jatuh Tempo Langganan Tokcer AI',
                    'html', v_html
                )
            );
            v_emailed_h3 := v_emailed_h3 + 1;
        END IF;
    END LOOP;

    -- ========================================================
    -- C. KUNCI AKUN BULANAN YANG SUDAH LEWAT MASA AKTIF
    -- ========================================================
    FOR v_client IN 
        SELECT id, email, shop_name 
        FROM public.clients 
        WHERE status = 'active' AND billing_cycle = 'Monthly'
          AND expires_at < NOW()
    LOOP
        UPDATE public.clients SET status = 'expired' WHERE id = v_client.id;
        v_expired_monthly := v_expired_monthly + 1;
    END LOOP;

    RETURN json_build_object(
        'success', true, 
        'yearly_tokens_reset', v_updated_yearly,
        'monthly_h3_reminders_sent', v_emailed_h3,
        'monthly_accounts_expired', v_expired_monthly
    );
END;
$$;
