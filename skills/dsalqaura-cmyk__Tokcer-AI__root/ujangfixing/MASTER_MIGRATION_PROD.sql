-- ============================================================
-- 🏮 TOKCER AI: MIDTRANS STANDARDIZATION (v2.1)
-- Penyelarasan skema tabel transaksi dengan Edge Functions
-- ============================================================

-- 1. Buat Tabel Transactions (Sesuai harapan robot midtrans-init/webhook)
CREATE TABLE IF NOT EXISTS public.transactions (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    order_id TEXT UNIQUE NOT NULL,
    user_id UUID REFERENCES auth.users(id) ON DELETE SET NULL,
    plan_name TEXT,
    amount BIGINT,
    tokens_to_add INTEGER DEFAULT 0,
    snap_token TEXT,
    status TEXT DEFAULT 'pending', -- 'pending', 'settlement', 'capture', 'expire', 'deny'
    payment_type TEXT,
    raw_notification JSONB DEFAULT '{}'::jsonb
);

-- Tambahkan kolom jika belum ada (antisipasi tabel sudah ada tapi beda versi)
ALTER TABLE public.transactions ADD COLUMN IF NOT EXISTS order_id TEXT;
ALTER TABLE public.transactions ADD COLUMN IF NOT EXISTS plan_name TEXT;
ALTER TABLE public.transactions ADD COLUMN IF NOT EXISTS amount BIGINT;
ALTER TABLE public.transactions ADD COLUMN IF NOT EXISTS tokens_to_add INTEGER;
ALTER TABLE public.transactions ADD COLUMN IF NOT EXISTS snap_token TEXT;
ALTER TABLE public.transactions ADD COLUMN IF NOT EXISTS payment_type TEXT;
ALTER TABLE public.transactions ADD COLUMN IF NOT EXISTS raw_notification JSONB;

-- 2. Index untuk pencarian cepat
CREATE INDEX IF NOT EXISTS idx_transactions_order_id ON public.transactions(order_id);
CREATE INDEX IF NOT EXISTS idx_transactions_user_id ON public.transactions(user_id);

-- 3. RLS Policies
ALTER TABLE public.transactions ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "Users can view own transactions" ON public.transactions;
CREATE POLICY "Users can view own transactions" ON public.transactions 
FOR SELECT USING (auth.uid() = user_id);

DROP POLICY IF EXISTS "Admins can view all transactions" ON public.transactions;
CREATE POLICY "Admins can view all transactions" ON public.transactions 
FOR ALL USING (EXISTS (SELECT 1 FROM public.profiles WHERE id = auth.uid() AND role = 'admin'));

-- 4. Update tabel clients (Sinkronisasi status)
ALTER TABLE public.clients ADD COLUMN IF NOT EXISTS midtrans_order_id TEXT;
ALTER TABLE public.clients ADD COLUMN IF NOT EXISTS payment_url TEXT;
-- MASTER SQL UPGRADE: EXPIRES_AT SYSTEM FOR SAAS
-- Update: Support automatic subscription expiry date calculation

-- 1. Tambahkan kolom expires_at ke tabel clients jika belum ada
ALTER TABLE public.clients ADD COLUMN IF NOT EXISTS expires_at TIMESTAMPTZ;

-- 2. Update client yang sudah aktif tapi belum punya tanggal expires
UPDATE public.clients 
SET expires_at = created_at + INTERVAL '30 days' 
WHERE status = 'active' AND billing_cycle = 'Monthly' AND expires_at IS NULL;

UPDATE public.clients 
SET expires_at = created_at + INTERVAL '365 days' 
WHERE status = 'active' AND billing_cycle = 'Yearly' AND expires_at IS NULL;

-- 3. Upgrade Fungsi Aktivasi Akun
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
        UPDATE public.clients 
        SET status = 'active', 
            plan = v_plan_key,
            expires_at = NOW() + CASE 
                WHEN v_billing_cycle = 'Yearly' THEN INTERVAL '365 days'
                ELSE INTERVAL '30 days'
            END
        WHERE id = v_client_record.id;
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
                END IF;
            END IF;

            -- Cek Milestone 10
            IF v_active_count >= 10 THEN
                IF NOT EXISTS (SELECT 1 FROM public.ai_usage_logs WHERE user_id = v_partner_id AND feature = 'partner_milestone_bonus' AND prompt LIKE '%Milestone: 10%') THEN
                    v_milestone_bonus := v_milestone_bonus + 350000;
                END IF;
            END IF;

            -- Cek Milestone 15
            IF v_active_count >= 15 THEN
                IF NOT EXISTS (SELECT 1 FROM public.ai_usage_logs WHERE user_id = v_partner_id AND feature = 'partner_milestone_bonus' AND prompt LIKE '%Milestone: 15%') THEN
                    v_milestone_bonus := v_milestone_bonus + 750000;
                END IF;
            END IF;

            -- Tambahkan Bonus ke Komisi
            v_commission := v_commission + v_milestone_bonus;
            -- ====================================================

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
-- SQL Migration: Sistem Akuntansi Internal Tokcer AI
-- Lokasi: ujangfixing/CREATE_ACCOUNTING_SYSTEM.sql

-- ===========================================================================
-- 1. TABEL: income_transactions
-- ===========================================================================
CREATE TABLE IF NOT EXISTS income_transactions (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    date DATE NOT NULL DEFAULT CURRENT_DATE,
    source TEXT NOT NULL CHECK (source IN ('partner', 'organic')),
    partner_id UUID REFERENCES partners(id) ON DELETE SET NULL,
    plan TEXT NOT NULL CHECK (plan IN ('pro', 'elite', 'ultimate')),
    plan_type TEXT NOT NULL CHECK (plan_type IN ('monthly', 'annual')),
    gross_amount INTEGER NOT NULL,
    period_start DATE NOT NULL,
    period_end DATE NOT NULL,
    midtrans_fee INTEGER DEFAULT 0,
    net_after_cogs INTEGER GENERATED ALWAYS AS (gross_amount - midtrans_fee) STORED,
    notes TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Index untuk mempercepat pencarian berdasarkan tanggal dan partner
CREATE INDEX IF NOT EXISTS idx_income_date ON income_transactions(date);
CREATE INDEX IF NOT EXISTS idx_income_partner ON income_transactions(partner_id);

-- ===========================================================================
-- 2. TABEL: partner_payouts
-- ===========================================================================
CREATE TABLE IF NOT EXISTS partner_payouts (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    partner_id UUID REFERENCES partners(id) ON DELETE CASCADE,
    period_month DATE NOT NULL, -- Disimpan sebagai tanggal 1 (YYYY-MM-01)
    payout_date DATE DEFAULT CURRENT_DATE,
    rev_share_amount INTEGER NOT NULL DEFAULT 0,
    performance_bonus INTEGER NOT NULL DEFAULT 0,
    bonus_breakdown JSONB, -- Detail rincian bonus yang didapat
    total_payout INTEGER GENERATED ALWAYS AS (rev_share_amount + performance_bonus) STORED,
    status TEXT NOT NULL CHECK (status IN ('pending', 'paid')) DEFAULT 'pending',
    paid_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_payout_month ON partner_payouts(period_month);
CREATE INDEX IF NOT EXISTS idx_payout_partner ON partner_payouts(partner_id);

-- ===========================================================================
-- 3. TABEL: infra_costs
-- ===========================================================================
CREATE TABLE IF NOT EXISTS infra_costs (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    date DATE NOT NULL DEFAULT CURRENT_DATE,
    category TEXT NOT NULL CHECK (category IN ('web_hosting', 'ai_credit', 'database', 'email_service')),
    vendor TEXT NOT NULL,
    amount_idr INTEGER NOT NULL,
    amount_usd DECIMAL(10,2),
    usd_idr_rate INTEGER,
    billing_cycle TEXT NOT NULL CHECK (billing_cycle IN ('one-time', 'monthly', 'annual', 'usage-based')),
    notes TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_infra_date ON infra_costs(date);

-- ===========================================================================
-- 4. INSERT DEFAULT CONFIG (Optional - Jika belum ada)
-- ===========================================================================
-- Menambahkan kurs USD default jika belum ada di ai_configs
-- INSERT INTO ai_configs (key, value) 
-- VALUES ('USD_IDR_RATE', '{"rate": 17300}')
-- ON CONFLICT (key) DO NOTHING;
-- =======================================================
-- 1. FUNGSI UNTUK MENGAMBIL STATISTIK GLOBAL DASHBOARD ADMIN
-- =======================================================

CREATE OR REPLACE FUNCTION public.rpc_get_global_stats()
RETURNS JSON
LANGUAGE plpgsql
SECURITY DEFINER 
AS $$
DECLARE
    v_total_revenue BIGINT := 0;
    v_active_users BIGINT := 0;
    v_active_partners BIGINT := 0;
    v_total_orders BIGINT := 0;
    v_pending_payouts BIGINT := 0;
BEGIN
    -- A. Hitung Total Revenue Riil (Pakai % di depan belakang agar super fleksibel)
    SELECT COALESCE(SUM(
        CASE 
            WHEN LOWER(plan::text) LIKE '%ultimate%' THEN 1999000
            WHEN LOWER(plan::text) LIKE '%elite%' THEN 999000
            WHEN LOWER(plan::text) LIKE '%pro%' THEN 499000
            ELSE 0 
        END
    ), 0) INTO v_total_revenue
    FROM public.clients
    WHERE status = 'active';

    -- B. Hitung Active Users
    SELECT COUNT(*) INTO v_active_users FROM public.clients WHERE status = 'active';

    -- C. Hitung Active Partners
    SELECT COUNT(*) INTO v_active_partners FROM public.partners;

    -- D. Hitung Total Orders
    v_total_orders := v_active_users;

    -- E. Hitung Pembayaran Menunggu (Dari Total Omzet/Saldo semua Partner)
    SELECT COALESCE(SUM(total_omzet), 0) INTO v_pending_payouts FROM public.partners;

    RETURN json_build_object(
        'totalRevenue', v_total_revenue,
        'activeUsers', v_active_users,
        'activePartners', v_active_partners,
        'totalOrders', v_total_orders,
        'pendingPayouts', v_pending_payouts
    );
END;
$$;


-- =======================================================
-- 2. FUNGSI UNTUK MENGAMBIL AKTIVITAS TERBARU (RECENT ACTIVITY)
-- =======================================================

CREATE OR REPLACE FUNCTION public.rpc_get_recent_clients()
RETURNS JSON
LANGUAGE plpgsql
SECURITY DEFINER 
AS $$
DECLARE
    v_result JSON;
BEGIN
    SELECT json_agg(t) INTO v_result
    FROM (
        SELECT 
            'user' as type,
            shop_name as user,
            'Pendaftaran Baru' as action,
            created_at as time,
            COALESCE(plan, 'Starter') as status
        FROM public.clients
        ORDER BY created_at DESC
        LIMIT 5
    ) t;

    RETURN COALESCE(v_result, '[]'::json);
END;
$$;
