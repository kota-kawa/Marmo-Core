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
-- ==============================================================================
-- TOKCER AI: H-3 SUBSCRIPTION EXPIRY REMINDER SYSTEM (CRON JOB)
-- ==============================================================================
-- Deskripsi:
-- Script ini mengatur pg_cron untuk memanggil Supabase Edge Function
-- 'cron-h3-reminder' setiap hari pada jam 00:00 AM (tengah malam).
-- Edge Function tersebut akan mengirim email tagihan H-3 ke klien.
--
-- Prasyarat:
-- 1. pg_net dan pg_cron extension harus aktif di Supabase.
-- 2. SUPABASE_URL dan SUPABASE_SERVICE_ROLE_KEY di Supabase Edge Functions.
-- ==============================================================================

-- 1. Pastikan extensions aktif (biasanya sudah default di Supabase)
CREATE EXTENSION IF NOT EXISTS pg_net;
CREATE EXTENSION IF NOT EXISTS pg_cron;

-- 2. Hapus job lama jika pernah dibuat (agar tidak duplikat)
SELECT cron.unschedule('daily-h3-reminder-email');

-- 3. Jadwalkan eksekusi Edge Function setiap jam 00:00 setiap hari
SELECT cron.schedule(
  'daily-h3-reminder-email', -- Nama Job
  '0 0 * * *',               -- Cron expression: Setiap menit ke-0, jam ke-0 setiap hari (Midnight)
  $$
    -- Panggil Edge Function menggunakan pg_net
    -- Catatan: Ganti 'https://[PROJECT_REF].supabase.co' dengan URL asli project Supabase
    -- Karena kita tidak tahu URL project dari SQL secara dinamis, disarankan untuk 
    -- memicu cron ini melalui webhook atau pastikan URL di bawah disesuaikan di Production.
    
    -- Contoh dengan URL relatif jika pg_net mendukung panggilan internal (tergantung versi Supabase):
    SELECT net.http_post(
      url:='https://dthzntikshlvyzfxuugc.supabase.co/functions/v1/cron-h3-reminder',
      headers:='{"Content-Type": "application/json", "Authorization": "Bearer YOUR_ANON_OR_SERVICE_KEY"}'::jsonb
    );
  $$
);

-- ==============================================================================
-- PENTING UNTUK ADMIN:
-- Karena pg_net butuh URL absolute, lebih disarankan membuat Scheduled Function
-- melalui Supabase Dashboard -> Edge Functions -> Pilih 'cron-h3-reminder'
-- lalu set Schedule '0 0 * * *'.
-- Script SQL ini adalah fallback/dokumentasi jika ingin diset langsung via Database.
-- ==============================================================================
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
-- ============================================================
-- TAMBAHAN v10: KOREKSI DATA CREDIT (FIX_CREDIT_VALUES)
-- ============================================================

-- Turunkan saldo akun Pro yang terlanjur 5000 menjadi 300
UPDATE public.profiles 
SET ai_tokens = 300 
WHERE subscription_plan = 'pro' AND ai_tokens = 5000;

-- Pastikan kolom expires_at ada (dibutuhkan oleh rpc_renew_subscription)
ALTER TABLE public.clients ADD COLUMN IF NOT EXISTS expires_at TIMESTAMPTZ;
ALTER TABLE public.clients ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ DEFAULT NOW();

-- Backfill data lama yang belum punya expires_at
UPDATE public.clients
SET expires_at = created_at + INTERVAL '30 days'
WHERE status = 'active' AND billing_cycle = 'Monthly' AND expires_at IS NULL;

UPDATE public.clients
SET expires_at = created_at + INTERVAL '365 days'
WHERE status = 'active' AND billing_cycle = 'Yearly' AND expires_at IS NULL;

-- Pastikan kolom referral_code di partners ada
ALTER TABLE public.partners ADD COLUMN IF NOT EXISTS referral_code TEXT;
ALTER TABLE public.partners ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ DEFAULT NOW();
ALTER TABLE public.partners ADD COLUMN IF NOT EXISTS tier TEXT DEFAULT 'bronze';
ALTER TABLE public.partners ADD COLUMN IF NOT EXISTS total_omzet BIGINT DEFAULT 0;

-- Pastikan kolom partner_id di clients ada
ALTER TABLE public.clients ADD COLUMN IF NOT EXISTS partner_id UUID REFERENCES public.partners(id) ON DELETE SET NULL;

-- Pastikan kolom billing_cycle di clients ada
ALTER TABLE public.clients ADD COLUMN IF NOT EXISTS billing_cycle TEXT DEFAULT 'Monthly';

-- Data komisi default (wajib ada agar rpc_activate_account dan rpc_renew_subscription bisa hitung komisi)
INSERT INTO public.ai_configs (key, value) VALUES
  ('commission_rates_v3', '{"pro": {"bronze": 100000, "silver": 120000, "gold": 140000, "platinum": 150000}, "elite": {"bronze": 150000, "silver": 180000, "gold": 220000, "platinum": 270000}, "ultimate": {"bronze": 200000, "silver": 240000, "gold": 300000, "platinum": 360000}, "starter": {"bronze": 0, "silver": 0, "gold": 0, "platinum": 0}}'::jsonb::text),
  ('annual_plan_bonuses', '{"pro": 100000, "elite": 200000, "ultimate": 300000, "starter": 0}'::jsonb::text)
ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value;

-- RLS untuk income_transactions (agar aman dari akses luar)
ALTER TABLE public.income_transactions ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "Admins can manage income" ON public.income_transactions;
CREATE POLICY "Admins can manage income" ON public.income_transactions
  FOR ALL USING (EXISTS (SELECT 1 FROM public.profiles WHERE id = auth.uid() AND role = 'admin'));

-- RLS untuk partner_payouts
ALTER TABLE public.partner_payouts ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "Partners can view own payouts" ON public.partner_payouts;
CREATE POLICY "Partners can view own payouts" ON public.partner_payouts
  FOR SELECT USING (auth.uid() = partner_id);
DROP POLICY IF EXISTS "Admins can manage payouts" ON public.partner_payouts;
CREATE POLICY "Admins can manage payouts" ON public.partner_payouts
  FOR ALL USING (EXISTS (SELECT 1 FROM public.profiles WHERE id = auth.uid() AND role = 'admin'));
