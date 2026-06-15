-- ============================================================
-- 🏮 TOKCER AI: FIX CREDIT VALUES (v1.0)
-- Menyelaraskan nilai aktivasi database dengan konsep Credit Dashboard
-- ============================================================

-- 1. UPDATE FUNGSI AKTIVASI (Ganti ribuan token dengan satuan credit)
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

    -- [PERBAIKAN UJANG]: Gunakan satuan CREDIT bukan TOKEN API
    v_tokens := CASE 
        WHEN v_plan_key = 'starter' THEN 50
        WHEN v_plan_key = 'pro' THEN 300
        WHEN v_plan_key = 'elite' THEN 1000
        WHEN v_plan_key = 'ultimate' THEN 3000
        ELSE 50
    END;

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
        ai_tokens = v_tokens; -- Ganti dengan kuota credit yang benar

    IF v_client_record.id IS NOT NULL THEN
        UPDATE public.clients SET status = 'active', plan = v_plan_key WHERE id = v_client_record.id;
    END IF;
    
    IF v_partner_app_record.id IS NOT NULL THEN
        UPDATE public.partner_applications SET status = 'active' WHERE id = v_partner_app_record.id;
        INSERT INTO public.partners (id, email, full_name, whatsapp, status)
        VALUES (v_user_id, p_email, p_full_name, v_partner_app_record.whatsapp, 'active')
        ON CONFLICT (id) DO UPDATE SET status = 'active';
    END IF;

    RETURN json_build_object(
        'success', true,
        'message', 'Activation successful with ' || v_tokens || ' credits.',
        'user_id', v_user_id
    );
END;
$$;

-- 2. KOREKSI DATA (Turunkan saldo akun yang terlanjur 5000 menjadi 300)
UPDATE public.profiles 
SET ai_tokens = 300 
WHERE subscription_plan = 'pro' AND ai_tokens = 5000;
