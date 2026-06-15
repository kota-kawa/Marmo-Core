-- ==============================================================================
-- 🏮 TOKCER AI: PENYIAPAN KREDENSIAL & SKEMA API PRODUCTION (iogxyohoexfkpugdtymu)
-- ==============================================================================

-- 1. PENYELARASAN KOLOM TABEL (SINKRONISASI BLUEPRINT RESMI)
ALTER TABLE public.marketplace_connections ADD COLUMN IF NOT EXISTS token_expiry TIMESTAMPTZ;
ALTER TABLE public.marketplace_connections ADD COLUMN IF NOT EXISTS sync_status TEXT DEFAULT 'idle';

-- 2. MASUKKAN KREDENSIAL API RESMI TIKTOK, SHOPEE, & RESEND
INSERT INTO public.ai_configs (key, value)
VALUES 
    ('tiktok_app_id', '6jvo03ggb4cbo'),
    ('tiktok_app_secret', '265a120f8a3485fd562970a653d252111329d33e'),
    ('tiktok_service_id', '7638757935900280584'),
    ('shopee_partner_id', '882291'),
    ('shopee_partner_key', '8a2b3c4d5e6f7g8h9i0j1k2l3m4n5o6p'),
    ('resend_api_key', 're_inXLuJdr_3P4EsTZHxK4kn5PQ5rs4FbnB')
ON CONFLICT (key) DO UPDATE 
SET value = EXCLUDED.value;

-- 3. REFRESH SCHEMA CACHE SECARA INSTAN
NOTIFY pgrst, 'reload schema';
