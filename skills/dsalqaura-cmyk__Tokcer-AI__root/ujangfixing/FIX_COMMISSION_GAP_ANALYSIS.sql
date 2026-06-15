-- ==============================================================================
-- 🏮 TOKCER AI: PERBAIKAN LOGIKA KOMISI PARTNER (GAP ANALYSIS FIX)
-- Masalah: Jika draf payout bulanan sudah dibuat, komisi partner baru
--          di bulan yang sama tidak pernah ditambahkan ke total_omzet.
-- Solusi: Lacak komisi per client_id secara unik, bukan per bulan.
--         Tambahkan kolom 'commission_paid' di tabel clients sebagai flag
--         agar komisi tidak bisa dihitung dua kali untuk klien yang sama.
-- ==============================================================================
-- JALANKAN DI: Supabase SQL Editor (Production)
-- ==============================================================================

-- LANGKAH 1: Tambahkan flag komisi per klien (idempotent)
ALTER TABLE public.clients 
ADD COLUMN IF NOT EXISTS commission_paid BOOLEAN DEFAULT FALSE;

-- LANGKAH 2: Update fungsi aktivasi dengan logika baru yang aman
CREATE OR REPLACE FUNCTION public.rpc_activate_account(
    p_email TEXT,
    p_application_id UUID,
    p_full_name TEXT,
    p_plan TEXT,
    p_role TEXT DEFAULT 'user'
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
    v_expires_at TIMESTAMPTZ;
BEGIN
    -- 1. Identify context
    SELECT * INTO v_client_record FROM public.clients WHERE id = p_application_id OR email = p_email LIMIT 1;
    SELECT * INTO v_partner_app_record FROM public.partner_applications WHERE id = p_application_id OR email = p_email LIMIT 1;
    
    v_billing_cycle := COALESCE(v_client_record.billing_cycle, 'Monthly');
    v_plan_key := lower(COALESCE(p_plan, v_client_record.plan, 'starter'));

    -- 2. Determine Tokens and Expiration
    v_tokens := CASE 
        WHEN v_plan_key = 'starter' THEN 50
        WHEN v_plan_key = 'pro' THEN 300
        WHEN v_plan_key = 'elite' THEN 1000
        WHEN v_plan_key = 'ultimate' THEN 3000
        ELSE 50
    END;

    v_expires_at := CASE 
        WHEN v_plan_key = 'starter' THEN NULL
        WHEN v_billing_cycle = 'Yearly' THEN NOW() + INTERVAL '365 days'
        ELSE NOW() + INTERVAL '30 days'
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

    -- 6. PARTNER COMMISSION LOGIC
    -- [PERBAIKAN GAP ANALYSIS]: Gunakan flag 'commission_paid' per klien, bukan cek per periode bulan.
    -- Ini memastikan komisi tidak hilang meski draf payout sudah dibuat lebih awal di bulan yang sama.
    IF p_role = 'user' AND v_plan_key <> 'starter' THEN
        -- Hanya proses jika komisi untuk klien ini BELUM PERNAH dibayarkan
        IF v_client_record.id IS NOT NULL AND NOT COALESCE(v_client_record.commission_paid, FALSE) THEN
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

                -- Tambahkan komisi ke total_omzet partner
                UPDATE public.partners 
                SET total_omzet = COALESCE(total_omzet, 0) + v_commission, updated_at = NOW()
                WHERE id = v_partner_id;

                -- Tandai bahwa komisi untuk klien ini sudah dibayarkan (hindari double counting)
                UPDATE public.clients SET commission_paid = TRUE WHERE id = v_client_record.id;
            END IF;
        END IF;
    END IF;

    RETURN json_build_object('success', true, 'user_id', v_user_id, 'expires_at', v_expires_at);
END;
$$;

-- Beri tahu PostgREST untuk reload schema
NOTIFY pgrst, 'reload schema';
