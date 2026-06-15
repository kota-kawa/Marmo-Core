-- ==============================================================================
-- 🏮 TOKCER AI: SEED DATA SAMPEL PRESENTASI REALISTIS UNTUK ms.jennifer1210@gmail.com
-- ==============================================================================

DO $$
DECLARE
    v_user_id UUID;
BEGIN
    -- 1. Cari ID asli user jennifer berdasarkan email di tabel auth
    SELECT id INTO v_user_id FROM auth.users WHERE email = 'ms.jennifer1210@gmail.com' LIMIT 1;

    -- 2. Jika user ditemukan, lakukan penyuplai data (seeding)
    IF v_user_id IS NOT NULL THEN
        
        -- A. Setup Profil agar statusnya Starter Aktif berkuota pas 50
        INSERT INTO public.profiles (id, full_name, email, role, subscription_plan, tokens)
        VALUES (v_user_id, 'Jennifer Shop Owner', 'ms.jennifer1210@gmail.com', 'user', 'starter', 50)
        ON CONFLICT (id) DO UPDATE 
        SET subscription_plan = 'starter', tokens = 50;

        -- B. Integrasikan Toko TikTok & Shopee secara formal ke Database
        DELETE FROM public.marketplace_connections WHERE user_id = v_user_id;
        INSERT INTO public.marketplace_connections (user_id, platform, shop_name, shop_id, sync_status)
        VALUES 
            (v_user_id, 'tiktok', 'Jennifer Glow Beauty', 'TTK-JFN-99', 'active'),
            (v_user_id, 'shopee', 'Jennifer Fashion Wear', 'SHP-JFN-88', 'active');

        -- C. Setup Katalog Produk Estetis di Gudang (Products)
        DELETE FROM public.products WHERE user_id = v_user_id;
        INSERT INTO public.products (user_id, name, sku, stock, price, cost, description)
        VALUES 
            (v_user_id, 'Sunscreen Glowing SPF 50', 'SKIN-001', 120, 85000, 45000, 'Sunscreen pencerah kulit terbaik.'),
            (v_user_id, 'Earbuds Wireless Pro Z', 'GAD-099', 45, 299000, 180000, 'Audio kualitas studio tanpa kabel.'),
            (v_user_id, 'Smartwatch Fit X1', 'GAD-088', 3, 450000, 250000, 'Pelacak kesehatan dan notifikasi pintar. (Stok Kritis)'),
            (v_user_id, 'Moisturizer Hyaluronic Acid', 'SKIN-002', 200, 125000, 60000, 'Melembabkan kulit selama 24 jam.'),
            (v_user_id, 'Kaos Oversize Premium Black', 'FASH-001', 0, 150000, 75000, 'Kaos premium hitam. (Stok Habis)');

        -- D. Setup Data Transaksi Penjualan Dinamis 3 Bulan Terakhir (Orders)
        DELETE FROM public.orders WHERE user_id = v_user_id;
        INSERT INTO public.orders (user_id, order_number, customer_name, platform, total_amount, status, order_date)
        SELECT 
            v_user_id,
            'ORD-JFN-' || to_char(now() - (i || ' days')::interval, 'YYYYMMDD') || '-' || i,
            'Pelanggan Jennifer ' || i,
            (ARRAY['shopee', 'tiktok'])[floor(random() * 2 + 1)],
            floor(random() * (1200000 - 65000 + 1) + 65000),
            'completed',
            now() - (i || ' days')::interval
        FROM generate_series(0, 45) AS i;

        RAISE NOTICE '✅ Berhasil memasukkan data presentasi untuk ms.jennifer1210@gmail.com!';
    ELSE
        RAISE NOTICE '❌ User ms.jennifer1210@gmail.com tidak ditemukan di database. Pastikan email tersebut sudah melakukan register terlebih dahulu!';
    END IF;

END $$;
