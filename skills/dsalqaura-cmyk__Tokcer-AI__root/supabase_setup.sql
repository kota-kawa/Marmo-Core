-- Phase 1: Tokcer AI Database Schema Migration
-- Execute this in your Supabase SQL Editor

-- 1. Profiles Table Enhancement
CREATE TABLE IF NOT EXISTS public.profiles (
    id UUID REFERENCES auth.users ON DELETE CASCADE PRIMARY KEY,
    full_name TEXT,
    email TEXT,
    role TEXT DEFAULT 'user', -- 'user', 'partner', 'admin'
    subscription_plan TEXT DEFAULT 'free', -- 'free', 'lite', 'pro', 'elite'
    ai_credits_remaining INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Enable RLS for Profiles
ALTER TABLE public.profiles ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Users can view their own profile" ON public.profiles FOR SELECT USING (auth.uid() = id);
CREATE POLICY "Users can update their own profile" ON public.profiles FOR UPDATE USING (auth.uid() = id);

-- 2. Marketplace Connections Table (Multi-shop)
CREATE TABLE IF NOT EXISTS public.marketplace_connections (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    user_id UUID REFERENCES public.profiles(id) ON DELETE CASCADE,
    platform TEXT NOT NULL, -- 'shopee', 'tiktok', 'tokopedia', 'instagram'
    shop_id TEXT,
    shop_name TEXT,
    access_token TEXT,
    refresh_token TEXT,
    token_expiry TIMESTAMPTZ,
    sync_status TEXT DEFAULT 'idle', -- 'idle', 'syncing', 'error'
    last_synced_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

ALTER TABLE public.marketplace_connections ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Users can manage their own connections" ON public.marketplace_connections FOR ALL USING (auth.uid() = user_id);

-- 3. AI Configurations Table (RAG & Guardrails)
CREATE TABLE IF NOT EXISTS public.ai_configs (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    key TEXT UNIQUE NOT NULL, -- example: 'system_prompt', 'rag_knowledge_base'
    value TEXT NOT NULL,
    description TEXT,
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Only Admin can see/edit config
ALTER TABLE public.ai_configs ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Admins can manage ai_configs" ON public.ai_configs FOR ALL USING (
  EXISTS (SELECT 1 FROM public.profiles WHERE id = auth.uid() AND role = 'admin')
);
CREATE POLICY "Users can view public configs" ON public.ai_configs FOR SELECT TO authenticated USING (true);

-- 4. AI Usage Logs Table
CREATE TABLE IF NOT EXISTS public.ai_usage_logs (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    user_id UUID REFERENCES public.profiles(id) ON DELETE CASCADE,
    task_type TEXT, 
    topic TEXT, 
    credits_spent INTEGER DEFAULT 1,
    request_payload JSONB,
    response_payload JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

ALTER TABLE public.ai_usage_logs ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Users can view their own usage logs" ON public.ai_usage_logs FOR SELECT USING (auth.uid() = user_id);

-- 5. Marketplace Data Sync Table
CREATE TABLE IF NOT EXISTS public.marketplace_data (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    connection_id UUID REFERENCES public.marketplace_connections(id) ON DELETE CASCADE,
    data_type TEXT, -- 'product', 'analytics_daily'
    platform_data JSONB,
    health_score INTEGER,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

ALTER TABLE public.marketplace_data ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Users can view their own marketplace data" ON public.marketplace_data FOR SELECT USING (
  EXISTS (SELECT 1 FROM public.marketplace_connections WHERE id = connection_id AND user_id = auth.uid())
);

-- 6. Initial Config Setup
INSERT INTO public.ai_configs (key, value, description)
VALUES 
('system_prompt', 'Kamu adalah asisten ahli e-commerce untuk Tokcer AI. Tugasmu membantu seller meningkatkan jualan di Shopee, TikTok, dan Tokopedia.', 'Instruksi dasar untuk DeepSeek'),
('rag_knowledge_base', 'Tokcer AI membantu optimasi toko, manajemen stok, dan analisis pasar.', 'Basis pengetahuan awal')
ON CONFLICT (key) DO NOTHING;
