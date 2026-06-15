# 🏮 IMPLEMENTATION BLUEPRINT: REAL-TIME MARKET INTEL ENGINE (OPSI A)
**TOKCERS AI — MARKET INTELLIGENCE SYSTEM**

Cetak biru ini menjelaskan langkah-langkah implementasi terperinci untuk menggantikan mockup statis pada halaman `MarketIntelTab.jsx` dengan data pasar real-time dari API TikTok Shop (Bestsellers) dan Shopee (Top Search), didukung oleh sistem proteksi biaya database caching.

---

## 🧭 1. STRATEGI FILTRASI MULTI-PLATFORM

Sistem harus mematuhi filter platform aktif (`platformFilter`) di header `MarketIntelTab.jsx` dengan aturan bisnis sebagai berikut:

```
                  ┌───────────────────────────────┐
                  │   User Mengubah Dropdown      │
                  │   Platform Filter             │
                  └───────────────┬───────────────┘
                                  │
         ┌────────────────────────┼────────────────────────┐
         ▼                        ▼                        ▼
┌──────────────────┐    ┌──────────────────┐    ┌──────────────────┐
│   TikTok Shop    │    │      Shopee      │    │  Semua Platform  │
└────────┬─────────┘    └────────┬─────────┘    └────────┬─────────┘
         ▼                       ▼                       ▼
   Tarik data dari         Tarik data dari         Gabungkan data dari
   TikTok API Bestseller   Shopee Top Search DB    kedua platform
   (Video, Live, Creator)  (Sales Volume growth)   (Merged Side-by-Side)
```

1.  **TikTok Shop View:**
    *   **Sumber Data:** API Endpoint `/api/tiktok/bestsellers` (menggunakan kredensial dari tabel `marketplace_connections`).
    *   **Visualisasi:** Ikon TikTok (hitam/teal), indikator viralitas berdasarkan metrik *Views* dan *Viewer Count*.
2.  **Shopee View:**
    *   **Sumber Data:** API Endpoint `/api/shopee/trending` (menggunakan scraper/cache global database).
    *   **Visualisasi:** Ikon Shopee (oranye), indikator tren berdasarkan metrik *Sales Volume* dan *Search Growth*.
3.  **Merged View (Semua Platform):**
    *   Menggabungkan kedua data secara proporsional di dalam tabel tren mingguan agar seller dapat membandingkan tren secara langsung.

---

## 🛠️ 2. PERUBAHAN UI & PANDUAN PENGGANTIAN MOCKUP PADA `MarketIntelTab.jsx`

Mockup statis saat ini akan dirombak total menjadi komponen dinamis yang menarik data dari server backend:

### **A. Widget 1: Weekly Viral Topics ➔ Live Viral Feed**
*   **Sebelumnya:** Hardcoded statis `"Old Money Aesthetic"` dan `"Skincare Barrier Repair"`.
*   **Perubahan:** Mengikat state `viralTopics` ke database yang di-update secara otomatis setiap hari.
*   **JSX Structure:**
    ```jsx
    {viralTopics.map((topic, i) => (
      <div key={i} className="flex items-center justify-between p-3 bg-black border border-zinc-800 rounded-xl">
        <div className="flex items-center gap-3">
          <div className={`w-8 h-8 rounded-lg bg-zinc-800 flex items-center justify-center ${topic.platform === 'TikTok' ? 'text-zinc-300' : 'text-orange-500'}`}>
            <iconify-icon icon={topic.platform === 'TikTok' ? 'ri:tiktok-fill' : 'simple-icons:shopee'}></iconify-icon>
          </div>
          <div>
            <div className="text-xs font-bold text-white">{topic.topic}</div>
            <div className="text-[10px] text-zinc-500">{topic.volume} Pencarian</div>
          </div>
        </div>
        <div className="text-xs font-black text-emerald-500">{topic.trend_percent}</div>
      </div>
    ))}
    ```

### **B. Widget 2: Radar Trend AI ➔ Bestselling Products Card**
*   **Sebelumnya:** Menampilkan contoh kategori produk dalam bentuk tombol pil tanpa visualisasi gambar produk riil.
*   **Perubahan:** Menampilkan **Top 5 Bestselling Products** hasil deteksi API TikTok/Shopee lengkap dengan indikator harga, estimasi penjualan bulanan, dan estimasi keuntungan bersih.

### **C. Widget 3: Deep Competitor Insight ➔ Video & Live Streaming Spy**
*   **Sebelumnya:** Teks statis loading *"Menganalisis pergerakan harga..."*.
*   **Perubahan:** Menampilkan daftar 3 video pendek kompetitor terpopuler beserta total views dan taksiran penjualan. Serta daftar Live Streaming yang paling ramai ditonton.

---

## 🧠 3. ARSITEKTUR DATABASE CACHING (PROTEKSI BIAYA API)

Untuk meminimalkan pemanggilan API pihak ketiga dan kuota rate limit, kita akan mengimplementasikan skema tabel `market_intel_cache` pada database Supabase:

```sql
CREATE TABLE public.market_intel_cache (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    category_query VARCHAR NOT NULL,
    platform VARCHAR NOT NULL,
    cached_data JSONB NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL
);

-- Indexing untuk query instan
CREATE INDEX idx_market_intel_query ON public.market_intel_cache (category_query, platform);
```

### **Alur Kerja Cache Engine:**
1.  Seller mencari kategori produk (misal: "Gamis Syar'i").
2.  Sistem melakukan pencarian pada tabel `market_intel_cache` untuk `category_query = 'Gamis Syar\'i'` dan `created_at > now() - interval '24 hours'`.
3.  Jika data ditemukan, sistem langsung menampilkan cache tersebut ke UI (Waktu muat < 0.2 detik, Biaya = Rp 0).
4.  Jika data kedaluwarsa atau tidak ada, sistem baru memicu pemanggilan API TikTok/Shopee, menyimpan hasilnya kembali ke tabel `market_intel_cache`, lalu menampilkannya ke seller.

---

## 🏁 4. TAHAP OPERASIONAL VALIDASI & BUILD

1.  Pembuatan model skema tabel `market_intel_cache` pada Supabase.
2.  Pengembangan API Router `/api/market-intel/fetch` untuk memproses filtrasi platform secara dinamis.
3.  Penyusunan ulang tampilan JSX di `src/components/dashboard/tabs/MarketIntelTab.jsx` untuk mengikat data real-time ke state komponen React.
4.  Menjalankan `npm run build` untuk memverifikasi kestabilan kompilasi aset sebelum perilisan utama.

---
*Dokumen Rencana Kerja Terverifikasi untuk Tim Pengembang Tokcer AI.* 🫡🛡️🏮
