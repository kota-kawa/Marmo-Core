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
