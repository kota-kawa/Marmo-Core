-- Migration: Add rpc_refund_token for AI credit rollback on failure
-- Dibuat: 2026-05-26
-- Tujuan: Kembalikan 1 credit ke user jika AI call gagal (edge function error)

CREATE OR REPLACE FUNCTION public.rpc_refund_token(
  p_user_id UUID,
  p_feature TEXT DEFAULT 'ai_refund',
  p_amount  INTEGER DEFAULT 1
)
RETURNS JSON
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
  v_new_balance INTEGER;
BEGIN
  -- Tambah token kembali ke profiles
  UPDATE public.profiles
  SET
    tokens    = COALESCE(tokens, 0) + p_amount,
    ai_tokens = COALESCE(ai_tokens, 0) + p_amount,
    updated_at = NOW()
  WHERE id = p_user_id
  RETURNING tokens INTO v_new_balance;

  IF NOT FOUND THEN
    RETURN json_build_object('success', false, 'error', 'User not found');
  END IF;

  -- Log refund
  INSERT INTO public.ai_usage_logs (user_id, feature, tokens_used, created_at)
  VALUES (p_user_id, p_feature || '_refund', -p_amount, NOW())
  ON CONFLICT DO NOTHING;

  RETURN json_build_object(
    'success',     true,
    'new_balance', v_new_balance,
    'refunded',    p_amount
  );

EXCEPTION WHEN OTHERS THEN
  RETURN json_build_object('success', false, 'error', SQLERRM);
END;
$$;

GRANT EXECUTE ON FUNCTION public.rpc_refund_token(uuid, text, integer)
  TO service_role, anon, authenticated;
