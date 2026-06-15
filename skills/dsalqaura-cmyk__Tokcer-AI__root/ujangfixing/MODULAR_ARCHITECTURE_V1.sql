-- =========================================================================
-- ARSITEKTUR MODULAR TOKCER AI - FASE 1
-- Memisahkan Logika Bisnis dari Auth Database Supabase
-- =========================================================================

-- FUNGSI BARU: rpc_setup_client_account
-- Fungsi ini HANYA mengurus: Profiles, Clients, Partners, dan Komisi.
-- Fungsi ini TIDAK AKAN PERNAH menyentuh auth.users atau auth.identities.
CREATE OR REPLACE FUNCTION public.rpc_setup_client_account(
    p_user_id UUID,
    p_email TEXT,
    p_application_id UUID,
    p_full_name TEXT,
    p_plan TEXT,
    p_role TEXT DEFAULT 'user'
)
RETURNS JSON LANGUAGE plpgsql SECURITY DEFINER AS $$
DECLARE
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
    SELECT * INTO v_client_record FROM public.clients WHERE id = p_application_id OR email = p_email LIMIT 1;
    SELECT * INTO v_partner_app_record FROM public.partner_applications WHERE id = p_application_id OR email = p_email LIMIT 1;
    
    v_billing_cycle := COALESCE(v_client_record.billing_cycle, 'Monthly');
    v_plan_key := lower(COALESCE(p_plan, v_client_record.plan, 'starter'));

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

    -- 1. Create/Update Profile with Role
    INSERT INTO public.profiles (id, full_name, email, role, subscription_plan, ai_tokens)
    VALUES (p_user_id, p_full_name, p_email, p_role, v_plan_key, v_tokens)
    ON CONFLICT (id) DO UPDATE 
    SET subscription_plan = v_plan_key,
        ai_tokens = profiles.ai_tokens + v_tokens,
        role = CASE WHEN profiles.role = 'admin' THEN 'admin' ELSE p_role END;

    -- 2. Status & Expiration Updates
    IF v_client_record.id IS NOT NULL THEN
        UPDATE public.clients SET status = 'active', plan = v_plan_key, expires_at = v_expires_at WHERE id = v_client_record.id;
    END IF;
    
    IF v_partner_app_record.id IS NOT NULL THEN
        UPDATE public.partner_applications SET status = 'active' WHERE id = v_partner_app_record.id;
        INSERT INTO public.partners (id, email, full_name, whatsapp, status)
        VALUES (p_user_id, p_email, p_full_name, v_partner_app_record.whatsapp, 'active')
        ON CONFLICT (id) DO UPDATE SET status = 'active';
    END IF;

    -- 3. PARTNER COMMISSION LOGIC
    IF p_role = 'user' AND v_plan_key <> 'starter' THEN
        v_partner_id := v_client_record.partner_id;
        IF v_partner_id IS NULL AND v_client_record.ref IS NOT NULL AND v_client_record.ref <> 'Direct Web' THEN
            SELECT id INTO v_partner_id FROM public.partners WHERE referral_code = v_client_record.ref LIMIT 1;
        END IF;

        IF v_partner_id IS NOT NULL THEN
            UPDATE public.clients SET partner_id = v_partner_id WHERE id = v_client_record.id;

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

    RETURN json_build_object('success', true, 'user_id', p_user_id, 'expires_at', v_expires_at);
END;
$$;
