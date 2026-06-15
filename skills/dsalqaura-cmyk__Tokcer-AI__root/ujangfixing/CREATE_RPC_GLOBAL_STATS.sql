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
