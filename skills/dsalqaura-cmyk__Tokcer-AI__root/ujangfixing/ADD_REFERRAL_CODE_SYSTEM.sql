-- ============================================================
-- 🏮 TOKCER AI: ADD REFERRAL CODE SYSTEM (v1.0)
-- Menambahkan sistem kode unik partner agar pencatatan tidak tertukar
-- ============================================================

-- 1. Tambah kolom referral_code di tabel partners (jika belum ada)
ALTER TABLE public.partners ADD COLUMN IF NOT EXISTS referral_code TEXT;

-- 2. Koreksi data untuk partner Kodrat (sesuai kasus Gambar 3)
UPDATE public.partners 
SET referral_code = 'TKC-AGR-537572' 
WHERE email = 'kodrat@mailinator.com';

-- 3. UPDATE FUNGSI AKTIVASI (Agar mencari berdasarkan referral_code)
CREATE OR REPLACE FUNCTION public.rpc_activate_account(
    p_email TEXT,
    p_application_id UUID,
    p_full_name TEXT,
    p_plan TEXT,
    p_role TEXT DEFAULT 'user'
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
    SELECT * INTO v_client_record FROM public.clients WHERE id = p_application_id OR email = p_email LIMIT 1;
    SELECT * INTO v_partner_app_record FROM public.partner_applications WHERE id = p_application_id OR email = p_email LIMIT 1;

    v_billing_cycle := COALESCE(v_client_record.billing_cycle, 'Monthly');
    v_plan_key := lower(COALESCE(p_plan, v_client_record.plan, 'starter'));

    -- Gunakan satuan CREDIT bukan TOKEN API
    v_tokens := CASE 
        WHEN v_plan_key = 'starter' THEN 50
        WHEN v_plan_key = 'pro' THEN 300
        WHEN v_plan_key = 'elite' THEN 1000
        WHEN v_plan_key = 'ultimate' THEN 3000
        ELSE 50
    END;

    -- [PERBAIKAN UJANG]: Ambil Partner ID berdasarkan referral_code di kolom 'ref'
    v_partner_id := v_client_record.partner_id;
    
    IF v_partner_id IS NULL AND v_client_record.ref IS NOT NULL AND v_client_record.ref NOT IN ('Direct', 'Direct Web') THEN
        -- Cari berdasarkan referral_code dulu
        SELECT id INTO v_partner_id FROM public.partners WHERE referral_code = v_client_record.ref LIMIT 1;
        
        -- Fallback: Jika tidak ketemu, cari berdasarkan nama (untuk data lama)
        IF v_partner_id IS NULL THEN
            SELECT id INTO v_partner_id FROM public.partners WHERE full_name = v_client_record.ref LIMIT 1;
        END IF;
    END IF;

    SELECT id INTO v_user_id FROM auth.users WHERE email = p_email;

    IF v_user_id IS NULL THEN
        INSERT INTO auth.users (instance_id, id, aud, role, email, encrypted_password, email_confirmed_at, created_at, updated_at)
        VALUES ('00000000-0000-0000-0000-000000000000', gen_random_uuid(), 'authenticated', 'authenticated', p_email, crypt('Tokcer@2026', gen_salt('bf')), now(), now(), now())
        RETURNING id INTO v_user_id;
    END IF;

    INSERT INTO public.profiles (id, full_name, email, role, subscription_plan, ai_tokens)
    VALUES (v_user_id, p_full_name, p_email, p_role, v_plan_key, v_tokens)
    ON CONFLICT (id) DO UPDATE 
    SET subscription_plan = v_plan_key,
        ai_tokens = v_tokens;

    IF v_client_record.id IS NOT NULL THEN
        UPDATE public.clients SET status = 'active', plan = v_plan_key, partner_id = v_partner_id WHERE id = v_client_record.id;
    END IF;
    
    IF v_partner_app_record.id IS NOT NULL THEN
        UPDATE public.partner_applications SET status = 'active' WHERE id = v_partner_app_record.id;
        INSERT INTO public.partners (id, email, full_name, whatsapp, status)
        VALUES (v_user_id, p_email, p_full_name, v_partner_app_record.whatsapp, 'active')
        ON CONFLICT (id) DO UPDATE SET status = 'active';
    END IF;

    -- Hitung Komisi (Logika tetap sama seperti V3)
    IF v_partner_id IS NOT NULL THEN
        SELECT tier INTO v_partner_tier FROM public.partners WHERE id = v_partner_id;
        v_partner_tier := COALESCE(v_partner_tier, 'bronze');

        SELECT count(*) INTO v_active_count FROM public.clients WHERE partner_id = v_partner_id AND status = 'active';
        SELECT count(*) INTO v_elite_count FROM public.clients WHERE partner_id = v_partner_id AND status = 'active' AND plan IN ('elite', 'ultimate');

        v_comm_rates := '{
            "starter": {"bronze": 100000, "silver": 120000, "gold": 140000, "platinum": 150000},
            "pro": {"bronze": 100000, "silver": 120000, "gold": 140000, "platinum": 150000},
            "elite": {"bronze": 100000, "silver": 120000, "gold": 140000, "platinum": 150000},
            "ultimate": {"bronze": 200000, "silver": 240000, "gold": 300000, "platinum": 360000}
        }'::jsonb;

        v_commission := (v_comm_rates->v_plan_key->v_partner_tier)::bigint;
        IF v_commission IS NULL THEN v_commission := 100000; END IF;

        IF v_billing_cycle = 'Yearly' THEN
            v_commission := v_commission * 11;
            v_annual_bonuses := '{"starter": 50000, "pro": 100000, "elite": 200000, "ultimate": 300000}'::jsonb;
            v_annual_bonus := (v_annual_bonuses->v_plan_key)::bigint;
            IF v_annual_bonus IS NOT NULL THEN
                v_commission := v_commission + v_annual_bonus;
            END IF;
        END IF;

        IF v_active_count = 5 THEN v_milestone_bonus := 150000; END IF;
        IF v_active_count = 10 THEN v_milestone_bonus := 300000; END IF;
        IF v_active_count = 20 THEN v_milestone_bonus := 500000; END IF;
        IF v_active_count = 50 THEN v_milestone_bonus := 1000000; END IF;
        IF v_active_count = 100 THEN v_milestone_bonus := 2500000; END IF;

        IF v_milestone_bonus > 0 THEN
            v_commission := v_commission + v_milestone_bonus;
        END IF;

        UPDATE public.partners 
        SET total_omzet = COALESCE(total_omzet, 0) + v_commission,
            tier = CASE 
                WHEN v_elite_count >= 10 THEN 'platinum'
                WHEN v_elite_count >= 5 THEN 'gold'
                WHEN v_elite_count >= 2 THEN 'silver'
                ELSE 'bronze'
            END
        WHERE id = v_partner_id;

        INSERT INTO public.income_transactions (partner_id, client_name, plan, amount, commission_amount, status)
        VALUES (v_partner_id, p_full_name, v_plan_key, 
                CASE WHEN v_plan_key = 'starter' THEN 499000 WHEN v_plan_key = 'pro' THEN 999000 WHEN v_plan_key = 'elite' THEN 1999000 ELSE 2999000 END,
                v_commission, 'settlement');
    END IF;

    RETURN json_build_object(
        'success', true,
        'message', 'Account activated, partner tracked, and commission added.',
        'user_id', v_user_id
    );
END;
$$;
