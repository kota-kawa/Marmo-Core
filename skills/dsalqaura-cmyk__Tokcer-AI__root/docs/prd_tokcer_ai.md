# 📦 Product Requirement Document (PRD) - Tokcer AI (Pembaruan Mei 2026)

## 1. Lingkup Produk (Product Scope)
Tokcer AI dirancang sebagai platform optimasi all-in-one bagi online seller/UMKM Indonesia untuk mendongkrak omzet secara cerdas. Sistem ini terdiri dari tiga dashboard utama serta modul otomasi di latar belakang:
1. **Dashboard Partner**: Alat kerja bagi afiliator/partner untuk mengelola registrasi klien dan memantau komisi.
2. **Dashboard User (Seller)**: Pusat kendali optimasi toko, kalkulator finansial, dan pembuat konten cerdas.
3. **Dashboard Internal (Admin)**: Pusat kendali moderasi, konfigurasi AI, serta monitoring kesehatan platform.
4. **Modul Otomasi Latar Belakang (Engine Layer)**:
   * **Zero-Cost AEO-SEO Suite**: Programmatic internal linking & optimalisasi struktur metadata halaman dinamis secara otomatis.
   * **TikTok Viral Autopilot**: Otomatisasi pengisian bank konten, rendering video edukasi premium, dan autoposting terjadwal dengan perlindungan anti-spam (Anti-Bot Jitter).

---

## 2. Fitur Utama Platform

### A. Dashboard Partner
* **Onboarding (Daftarkan Klien)**: 
  * Input data toko baru (Nama Toko, Email, WA).
  * Upload bukti pembayaran pendaftaran/upgrade.
  * Seleksi paket subscription (*Starter*, *Pro*, *Elite*, *Ultimate*).
* **Subscribers (Daftar User)**: Log pemantauan performa retensi seller rujukan dan status kedaluwarsa lisensi mereka.
* **Leaderboard**: Papan peringkat partner berdasarkan total komisi referal.
* **Payment (Komisi)**: Riwayat pencairan dana dan pengaturan rekening bank.
* **Support Center**: Laporan bug atau request fitur prioritas ke tim admin.
* **Academy**: Pusat materi edukasi digital eksklusif partner.

### B. Dashboard User (Seller)
* **Overview**: Ringkasan performa penjualan harian, sisa kuota koin AI, dan status subskripsi.
* **Analytics**: Grafik performa penjualan terintegrasi dari marketplace Shopee dan TikTok Shop.
* **HPP & Price Calculator (SKU Calculator)**: 
  * Perhitungan biaya kemasan, lakban, biaya operasional tersembunyi, komisi marketplace, komisi afiliasi, dan target margin.
  * Rekomendasi harga jual ideal agar terhindar dari kerugian operasional (boncos).
* **AI Content Generator**:
  * Generator deskripsi produk teroptimasi SEO berdasarkan kata kunci target.
  * Generator naskah video pendek terstruktur.
* **Store Connection & Health Check**: 
  * Integrasi resmi via API marketplace untuk sinkronisasi pesanan dan stok.
  * Deteksi parameter kesehatan toko (chat response rate, waktu pengiriman, rating).

### C. Dashboard Internal (Admin)
* **Approval Center**: Moderasi transaksi masuk dari direct web register atau partner referral.
* **User Manager**: Manajemen data komprehensif status akun penjual.
* **Partnership Hub**: Verifikasi pendaftaran partner baru dan konfigurasi bagi hasil.
* **Support Ticket**: Manajemen bantuan tiket keluhan teknis pengguna.
* **AI Strategy Hub**:
  * Konfigurasi API Gateway (DeepSeek API, Gemini API, dll.).
  * RAG Knowledge Base (unggah PDF materi edukasi terbaru untuk melatih kecerdasan AI).
  * Konfigurasi Resend API untuk notifikasi transaksional instan.
* **Supabase Monitor**: Dasbor pemantauan kesehatan koneksi database dan latensi.

### D. Modul Otomasi & Engine Latar Belakang (Baru)
* **Zero-Cost AEO-SEO Suite**:
  * **Programmatic Internal Linking**: Pemindaian otomatis konten artikel/produk menggunakan `keywords_map.json` untuk menyematkan hyperlink berbobot secara cerdas (SEO & AEO Anchor Text).
  * **Gemini Free-Tier Gateway**: Integrasi REST API gratis untuk ekspansi konten secara berkala tanpa menyedot biaya token API.
* **TikTok Viral Autopilot**:
  * **Auto-Replenisher Bank Konten**: Pengisian otomatis draf naskah hingga 10 stok di database, mengikuti panduan voiceover 6 kalimat (Hook, 4 Poin Edukasi Eksplisit, dan CTA).
  * **MoviePy Video Renderer**: Render otomatis dengan template portrait premium 9:16 (Glassmorphism overlay, logo resmi, progressive rendering text, audio suara TTS, dan musik latar belakang).
  * **Cookie-Based Secure Uploader**: Otomatisasi upload via Puppeteer berdasar cookie aktif guna meminimalkan risiko ban akun.
  * **Anti-Bot Jitter Scheduler**: Autoposting pada jam-jam prima (12:XX, 17:XX, 19:XX) dengan menit acak guna menyamarkan aktivitas bot.

---

## 3. Persyaratan Teknis & Arsitektur
* **Frontend**: React (Vite), Vanilla CSS, TailwindCSS (opsional untuk panel sekunder).
* **Backend**: Supabase (PostgreSQL, Realtime, Edge Functions, Storage).
* **Kecerdasan Buatan**: DeepSeek API (Core Generator) & Google Gemini 1.5 Flash REST API (SEO Engine & Auto-Replenisher).
* **Rendering Engine**: Python 3.9 + MoviePy + Pillow + gTTS.
* **Otomasi Browser**: Puppeteer (NodeJS) / Playwright (Python).
* **Keamanan Data**: RLS (Row Level Security) ketat di level PostgreSQL Supabase untuk memisahkan data antarpengguna.

---
**Pembaruan PRD Terakhir**: 20 Mei 2026  
**Oleh**: Antigravity AI (Senior Team)
