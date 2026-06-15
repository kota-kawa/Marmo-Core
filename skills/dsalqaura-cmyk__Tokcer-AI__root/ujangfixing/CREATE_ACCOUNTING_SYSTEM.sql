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
