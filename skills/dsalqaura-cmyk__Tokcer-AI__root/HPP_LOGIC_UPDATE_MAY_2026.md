# 🏮 Dokumentasi Teknis Strategis: Upgrade HPP Calculator Tokcer AI v2.3
**Status:** FULL PRODUCTION & STAGING LIVE
**Terakhir Diperbarui:** 15 Mei 2026
**Tim Pengembang:** Tarjo (Tokcer AI Core Engine)

---

## 🚀 I. Visi & Misi Update v2.3
Update v2.3 dirancang untuk menjadikan Tokcer AI sebagai **Sumber Kebenaran Tunggal (Single Source of Truth)** bagi seller dalam menghadapi turbulensi biaya administrasi marketplace di pertengahan 2026. Fokus utama adalah akurasi perhitungan antara Tokopedia/TikTok Shop dan Shopee yang memiliki skema batas atas (CAP) berbeda.

---

## 🏗️ II. Arsitektur "THE PLAYBOOK" (Layer 1-8)
Sistem menggunakan struktur input 8 lapis untuk eliminasi biaya siluman:

### Layer 1: Fixed Cost (Produksi & Logistik Awal)
- **Komponen:** HPP barang, Biaya Packaging, dan **Ongkir Ditanggung Seller (Subsidi)**.
- **Logic:** Merupakan biaya mati yang dikeluarkan sebelum barang laku.

### Layer 2: Platform Status (Mall vs Regular)
- **Shopee Mall:** Skema biaya admin Mall (Tipe A-E).
- **TikTok/Tokopedia Mall:** Penyesuaian otomatis komisi dasar (Estimasi kenaikan +25% dari tarif regular sesuai standar Mall 2026).

### Layer 3: Per-Order Fixed Fee (Processing Fee)
- **Aturan 2026:** Biaya flat **Rp1.250** per pesanan sukses di Tokopedia & Shopee.

### Layer 4: Marketing Program (Campaign Logic)
- **Shopee:** Gratis Ongkir XTRA (4%) & Cashback XTRA (1.4%).
- **TikTok:** Growth Xtra & Dynamic Commission (Promo Xtra).
- **SMART CAP LOGIC:** 
  - **Shopee:** Maksimal potongan program dibatasi **Rp10.000** per item.
  - **Tokopedia:** Maksimal potongan komisi melonjak ke **Rp650.000** per item (Per 18 Mei).

### Layer 5, 6, 7 & 8: Advanced Operational Fees
- **Layer 5:** Pre-Order Fee (+3%).
- **Layer 6:** Logistics Service Fee (Non-Refundable).
- **Layer 7:** Affiliate Commission (Manual Input).
- **Layer 8:** Ads Budgeting (% Harga Jual).

---

## 📉 III. Simulasi "Burn Cost" & True Net Profit
Inovasi terbesar v2.3 adalah kemampuan simulasi **"Duit Angus"** saat terjadi retur atau gagal kirim.

### Aturan Logistik 1 Mei 2026 (TikTok/Tokopedia):
- Biaya Logistik berstatus **NON-REFUNDABLE** setelah status "Dikirim".
- **Rumus Simulasi Risiko:** 
  > `Expected Loss = (Layer 1 + Layer 3 + Layer 6) * Return Rate %`
- Tokcer AI secara otomatis memasukkan variabel ini untuk memberikan angka **"True Net Profit"** yang sudah ter-adjust dengan risiko lapangan.

---

## ⚡ IV. Detail Teknis Shopee Specialist
Sistem kini menangani variabel spesifik Shopee:
1. **Cashback XTRA Logic:** Persentase 1.4% dengan proteksi CAP Rp10.000.
2. **Program Ekspor:** Input biaya tambahan untuk pesanan luar negeri (SIP - Shopee International Platform).
3. **SPayLater Fee:** Opsi tenor 0% hingga 12 bulan (Biaya layanan 2.5% - 4% dihitung otomatis).

---

## 📂 V. Panduan Deployment
- **Repo:** `src/pages/HppCalculator.jsx`
- **Logic Engine:** Terintegrasi langsung dengan React `useEffect` untuk kalkulasi real-time tanpa delay.
- **Staging Sync:** Branch `staging` dipastikan 100% identik dengan `main` untuk pengujian user baru.

**Laporan ini adalah dokumen resmi untuk audit operasional Tokcer AI.** 🫡🔥🇮🇩✨
