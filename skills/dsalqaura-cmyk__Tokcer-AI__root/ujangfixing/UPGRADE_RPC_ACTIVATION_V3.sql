-- MASTER SQL UPGRADE: CENTRALIZED ACTIVATION ENGINE v2.3
-- Update: Support Bronze Default Tier & Volume Milestone Bonus (5, 10, 15)

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
        WHEN v_plan_key = 'starter' THEN 1000
        WHEN v_plan_key = 'pro' THEN 5000
        WHEN v_plan_key = 'elite' THEN 15000
        WHEN v_plan_key = 'ultimate' THEN 50000
        ELSE 1000
    END;

    -- 3. Auth User Management
    SELECT id INTO v_user_id FROM auth.users WHERE email = p_email;

    IF v_user_id IS NULL THEN
        INSERT INTO auth.users (
            instance_id, id, aud, role, email, encrypted_password, 
            email_confirmed_at, recovery_sent_at, last_sign_in_at, 
            raw_app_meta_data, raw_user_meta_data, created_at, updated_at, 
            confirmation_token, email_change, email_change_token_new, recovery_token
        )
        VALUES (
            '00000000-0000-0000-0000-000000000000', gen_random_uuid(), 'authenticated', 'authenticated', 
            p_email, crypt('Tokcer@2026', gen_salt('bf')), 
            now(), now(), now(), 
            '{"provider":"email","providers":["email"]}'::jsonb, 
            jsonb_build_object('full_name', p_full_name), 
            now(), now(), '', '', '', ''
        )
        RETURNING id INTO v_user_id;
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
            SELECT id INTO v_partner_id FROM public.partners WHERE full_name = v_client_record.ref LIMIT 1;
        END IF;

        IF v_partner_id IS NOT NULL THEN
            -- Calculate Dynamic Tier
            SELECT count(*) INTO v_active_count FROM public.clients WHERE (partner_id = v_partner_id OR ref = (SELECT full_name FROM public.partners WHERE id = v_partner_id)) AND status = 'active';
            SELECT count(*) INTO v_elite_count FROM public.clients WHERE (partner_id = v_partner_id OR ref = (SELECT full_name FROM public.partners WHERE id = v_partner_id)) AND status = 'active' AND plan IN ('elite', 'ultimate');

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

            -- ====================================================
            -- LOGIKA BONUS PERFORMANCE (VOLUME MILESTONE)
            -- >=5 -> 150K, >=10 -> 350K, >=15 -> 750K
            
            -- Cek Milestone 5
            IF v_active_count >= 5 THEN
                IF NOT EXISTS (SELECT 1 FROM public.ai_usage_logs WHERE user_id = v_partner_id AND feature = 'partner_milestone_bonus' AND prompt LIKE '%Milestone: 5%') THEN
                    v_milestone_bonus := 150000;
                    -- INSERT INTO public.ai_usage_logs (user_id, feature, prompt, response)
                    -- VALUES (v_partner_id, 'partner_milestone_bonus', 'Milestone: 5 reached!', 'Credited: 150000');
                END IF;
            END IF;

            -- Cek Milestone 10
            IF v_active_count >= 10 THEN
                IF NOT EXISTS (SELECT 1 FROM public.ai_usage_logs WHERE user_id = v_partner_id AND feature = 'partner_milestone_bonus' AND prompt LIKE '%Milestone: 10%') THEN
                    v_milestone_bonus := v_milestone_bonus + 350000;
                    -- INSERT INTO public.ai_usage_logs (user_id, feature, prompt, response)
                    -- VALUES (v_partner_id, 'partner_milestone_bonus', 'Milestone: 10 reached!', 'Credited: 350000');
                END IF;
            END IF;

            -- Cek Milestone 15
            IF v_active_count >= 15 THEN
                IF NOT EXISTS (SELECT 1 FROM public.ai_usage_logs WHERE user_id = v_partner_id AND feature = 'partner_milestone_bonus' AND prompt LIKE '%Milestone: 15%') THEN
                    v_milestone_bonus := v_milestone_bonus + 750000;
                    -- INSERT INTO public.ai_usage_logs (user_id, feature, prompt, response)
                    -- VALUES (v_partner_id, 'partner_milestone_bonus', 'Milestone: 15 reached!', 'Credited: 750000');
                END IF;
            END IF;

            -- Tambahkan Bonus ke Komisi
            v_commission := v_commission + v_milestone_bonus;
            -- ====================================================

            UPDATE public.partners 
            SET total_omzet = total_omzet + v_commission,
                tier = v_partner_tier
            WHERE id = v_partner_id;

            -- INSERT INTO public.ai_usage_logs (user_id, feature, prompt, response)
            -- VALUES (v_partner_id, 'partner_commission_credit', 'Approval of ' || p_email, 'Credited: ' || v_commission::TEXT);
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
