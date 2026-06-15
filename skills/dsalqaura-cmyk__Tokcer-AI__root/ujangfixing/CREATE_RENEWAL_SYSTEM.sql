-- ==============================================================================
-- 🏮 TOKCER AI: RENEWAL & RECURRING COMMISSION SYSTEM
-- Resolves Gap A (Renewal Logic) and Gap B (Recurring Partner Commission)
-- Dibuat terpisah agar tidak menyenggol logic rpc_activate_account
-- ==============================================================================

CREATE OR REPLACE FUNCTION public.rpc_renew_subscription(
    p_email TEXT,
    p_plan TEXT,
    p_billing_cycle TEXT
)
RETURNS JSON LANGUAGE plpgsql SECURITY DEFINER AS $$
DECLARE
    v_client RECORD;
    v_partner_id UUID;
    v_expires_at TIMESTAMPTZ;
    v_tokens BIGINT;
    v_plan_key TEXT;
    
    -- Variabel Komisi Partner
    v_active_count INT;
    v_elite_count INT;
    v_partner_tier TEXT;
    v_comm_rates JSONB;
    v_annual_bonuses JSONB;
    v_commission BIGINT := 0;
    v_annual_bonus BIGINT := 0;
BEGIN
    v_plan_key := lower(p_plan);

    -- 1. Cari data Client berdasarkan Email (Karena perpanjangan, pasti sudah ada)
    SELECT * INTO v_client FROM public.clients WHERE email = p_email LIMIT 1;
    IF v_client.id IS NULL THEN
        RETURN json_build_object('success', false, 'message', 'Client tidak ditemukan');
    END IF;

    -- 2. Tentukan Kuota Token Baru
    v_tokens := CASE 
        WHEN v_plan_key = 'pro' THEN 300
        WHEN v_plan_key = 'elite' THEN 1000
        WHEN v_plan_key = 'ultimate' THEN 3000
        ELSE 50
    END;

    -- 3. Tentukan Tanggal Kedaluwarsa Baru
    -- Jika dia perpanjang sebelum mati, tambahkan dari sisa harinya. Jika sudah mati, hitung dari HARI INI.
    IF v_client.status = 'active' AND v_client.expires_at > NOW() THEN
        v_expires_at := v_client.expires_at + CASE WHEN p_billing_cycle = 'Yearly' THEN INTERVAL '365 days' ELSE INTERVAL '30 days' END;
    ELSE
        v_expires_at := NOW() + CASE WHEN p_billing_cycle = 'Yearly' THEN INTERVAL '365 days' ELSE INTERVAL '30 days' END;
    END IF;

    -- 4. Update Status Client (Ini sekaligus menghandle UPGRADE/DOWNGRADE Paket!)
    UPDATE public.clients 
    SET status = 'active', 
        plan = v_plan_key, 
        billing_cycle = p_billing_cycle,
        expires_at = v_expires_at,
        updated_at = NOW()
    WHERE id = v_client.id;

    -- 5. Update Profile User (Reset/Tambahkan Token)
    UPDATE public.profiles
    SET subscription_plan = v_plan_key,
        ai_tokens = ai_tokens + v_tokens, -- Kita pakai sistem akumulasi agar adil jika ada sisa token
        updated_at = NOW()
    WHERE email = p_email;

    -- 6. RECURRING COMMISSION LOGIC (Bagi hasil bulanan untuk Partner)
    v_partner_id := v_client.partner_id;
    IF v_partner_id IS NOT NULL AND v_plan_key <> 'starter' THEN
        -- Hitung Ulang Tier Partner saat ini
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
        
        IF p_billing_cycle = 'Yearly' THEN
            v_annual_bonus := (v_annual_bonuses->v_plan_key)::BIGINT;
            v_commission := (v_commission * 11) + v_annual_bonus;
        END IF;

        -- Tambahkan Komisi ke Omzet Partner (Tanpa mempedulikan v_is_new_period, karena ini adalah tagihan bulan baru!)
        UPDATE public.partners 
        SET total_omzet = COALESCE(total_omzet, 0) + v_commission, 
            updated_at = NOW()
        WHERE id = v_partner_id;
    END IF;

    RETURN json_build_object('success', true, 'expires_at', v_expires_at, 'commission_added', v_commission, 'new_plan', v_plan_key);
END;
$$;
