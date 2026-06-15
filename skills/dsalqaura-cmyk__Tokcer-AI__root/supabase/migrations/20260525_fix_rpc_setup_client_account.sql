-- Migration: Fix ambiguous rpc_setup_client_account
-- Dibuat: 2026-05-25
-- Masalah: Ada dua versi fungsi dengan signature berbeda (6 param vs 7 param)
--          menyebabkan error "Could not choose the best candidate function"
--          saat user register paket Starter.
-- Fix: Drop semua versi, buat ulang satu versi canonical (6 param, tanpa p_password).

-- ── Step 1: Drop semua versi yang ada ────────────────────────────────────────
DROP FUNCTION IF EXISTS public.rpc_setup_client_account(uuid, text, uuid, text, text, text);
DROP FUNCTION IF EXISTS public.rpc_setup_client_account(uuid, text, uuid, text, text, text, text);

-- ── Step 2: Buat satu versi canonical ────────────────────────────────────────
CREATE OR REPLACE FUNCTION public.rpc_setup_client_account(
  p_user_id        UUID,
  p_email          TEXT,
  p_application_id UUID,
  p_full_name      TEXT,
  p_plan           TEXT,
  p_role           TEXT
)
RETURNS JSON
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
  v_credits INTEGER;
  v_plan    TEXT;
BEGIN
  v_plan := LOWER(COALESCE(p_plan, 'starter'));

  v_credits := CASE v_plan
    WHEN 'pro'      THEN 300
    WHEN 'elite'    THEN 1000
    WHEN 'ultimate' THEN 3000
    ELSE 50  -- starter & default
  END;

  -- Upsert profile — buat baru atau update jika sudah ada
  INSERT INTO public.profiles (
    id, email, full_name, role,
    subscription_plan, ai_tokens, tokens,
    created_at, updated_at
  )
  VALUES (
    p_user_id, p_email, p_full_name, p_role,
    v_plan, v_credits, v_credits,
    NOW(), NOW()
  )
  ON CONFLICT (id) DO UPDATE SET
    email             = EXCLUDED.email,
    full_name         = EXCLUDED.full_name,
    role              = EXCLUDED.role,
    subscription_plan = EXCLUDED.subscription_plan,
    ai_tokens         = EXCLUDED.ai_tokens,
    tokens            = EXCLUDED.tokens,
    updated_at        = NOW();

  -- Aktifkan record di tabel clients
  UPDATE public.clients
  SET status     = 'active',
      updated_at = NOW()
  WHERE id = p_application_id;

  RETURN json_build_object(
    'success',    true,
    'user_id',    p_user_id,
    'plan',       v_plan,
    'ai_credits', v_credits
  );

EXCEPTION WHEN OTHERS THEN
  RETURN json_build_object(
    'success', false,
    'error',   SQLERRM
  );
END;
$$;

-- ── Step 3: Grant akses ───────────────────────────────────────────────────────
GRANT EXECUTE ON FUNCTION public.rpc_setup_client_account(uuid, text, uuid, text, text, text)
  TO service_role, anon, authenticated;
