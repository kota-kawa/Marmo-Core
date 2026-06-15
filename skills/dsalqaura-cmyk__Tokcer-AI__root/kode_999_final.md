Siap, Pak. Mari kita bedah kebutuhan Backend untuk **User Dashboard** agar sinkron dengan alur bisnis Tokcer AI.

Berdasarkan dokumen alur bisnis dan fitur yang sudah kita bangun di sisi UI, berikut adalah analisa awal saya mengenai skema tabel dan alur data yang diperlukan:

### **1. Analisa Tabel Supabase (Skema Database)**

Untuk mendukung fitur Analytics, AI Generator, dan Multi-platform, kita setidaknya butuh tabel-tabel berikut:

*   **`profiles`**: Menyimpan data dasar user (nama, email, role, dan link ke toko).
*   **`marketplace_connections`**: Tabel krusial untuk menyimpan token OAuth (Shopee, TikTok, Tokopedia).
    *   *Kolom:* `user_id`, `platform`, `shop_id`, `access_token`, `refresh_token`, `token_expiry`, `status`.
*   **`products` / `inventory`**: Menyimpan data produk yang ditarik dari marketplace.
    *   *Kolom:* `shop_id`, `external_id`, `name`, `stock`, `price`, `platform`, `health_score`.
*   **`analytics_daily`**: Menyimpan data performa harian untuk grafik.
<truncated 1936 bytes>