# 🏮 TOKCER AI: MASTER SYSTEM BLUEPRINT 🏮
## DO NOT DELETE OR MODIFY WITHOUT ADMIN APPROVAL

Dokumen ini adalah referensi utama untuk seluruh pengembang AI (Antigravity/Ucup) agar tidak merusak logika sistem yang sudah ada. **WAJIB DIBACA SEBELUM MEMULAI CHAT BARU.**

---

### 🏮 DAFTAR LINK RESMI (OFFICIAL LINKS)
- **User Landing (Staging)**: `https://staging.tokcer-ai.com`
- **User Login (Staging)**: `https://staging.tokcer-ai.com/login`
- **Admin Dashboard (Staging)**: `https://dashboardstaging.tokcer-ai.com`
- **User Landing (Production)**: `https://tokcer-ai.com`
- **Admin Dashboard (Production)**: `https://dashboard.tokcer-ai.com`
- **Official Logo Asset**: `https://dashboardstaging.tokcer-ai.com/logo.png`

---

### 🛡️ ATURAN HARAM (CRITICAL RULES)
- **Logo Integrity**: SELALU gunakan URL `https://dashboardstaging.tokcer-ai.com/logo.png`. Jangan ganti ke teks atau URL lain.
- **Visual Aesthetic**: Tema WAJIB **Premium Dark Mode** (Zinc-900, Black, Orange-600). Jangan gunakan warna-warna basic (Red, Blue, Green murni).
- **Hardcoded Links**: Jangan hardcode link login di dalam file `.jsx` jika berhubungan dengan email. Gunakan Database Trigger SQL agar link tetap konsisten (`staging.tokcer-ai.com/login`).
- **Database Trigger**: Seluruh aktivasi akun harus melalui fungsi `rpc_activate_account` untuk memastikan integrasi Auth, Profile, dan Komisi Partner sinkron.

---

### 2. 🗺️ PETA LOGIKA (LOGIC FLOW)

#### A. Alur Registrasi & Aktivasi
1. **User/Client** mendaftar via `RegisterModal.jsx` -> Masuk ke tabel `clients` (Status: `pending`).
2. **Partner** mendaftarkan klien -> Masuk ke tabel `clients` + `partner_id`.
3. **Admin** klik **Approve** di Dashboard Internal -> Menjalankan logic:
   - Buat Akun Supabase Auth.
   - Buat Profile di tabel `profiles` (Set `subscription_plan`).
   - Tambah `total_omzet` ke Partner terkait.
   - Kirim email Welcome otomatis via Database Trigger `tr_send_welcome_email`.

#### B. Alur Dashboard User
- **Data Source**: Saat ini masih berbasis **CSV Import** (Tabel `orders` & `products`).
- **AI Credits**: 
  - Potong 1 Token per **Topik Baru** di Generator.
  - Potong 1 Token per **Akses Harian** di Analytics & Market Intel.
- **Redirection**: User login harus dilempar ke `/dashboard`.

#### C. Alur Dashboard Partner
- **Komisi**: Berdasarkan `total_omzet` di tabel `partners`.
- **Leaderboard**: Diurutkan berdasarkan `total_omzet` secara Real-time.
- **Redirection**: Partner login harus dilempar ke `/partner-dashboard`.

---

### 3. ⚙️ TEKNOLOGI & KONFIGURASI
- **Frontend**: Vite + React + Tailwind CSS.
- **Backend**: Supabase (Auth, DB, Storage).
- **AI**: DeepSeek API (diakses via `utils/ai.js`).
- **Configs**: Seluruh API Key (Shopee, TikTok, Resend) disimpan di tabel `public.ai_configs`.

---

### 🏮 STATUS SISTEM & PRIORITAS DEVELOPMENT (Update: 4 Mei 2026)

#### ✅ PEKERJAAN SELESAI (DONE):
1.  **Komisi Sync**: Logika 26-25, Kriteria Tier (Min Elite), dan Rate Ultimate (Rp 249.7K - Rp 449.5K) telah sinkron di Dashboard Partner & Admin.
2.  **Harga Real**: Paket Ultimate dikoreksi ke Rp 1.999.000 (Monthly) & Rp 21.989.000 (Yearly) di Landing Page & Dashboard.
3.  **Onboarding V2**: Form pendaftaran sudah mendukung opsi Yearly dan menampilkan "Total Bayar" secara real-time.
4.  **Support Separation**: Form Lapor Bug (support_tickets) dan Saran Fitur (partner_ideas) sudah dipisah secara logika dan UI.

#### 🛠️ PRIORITAS DEVELOPMENT BERIKUTNYA (BACKLOG):
1.  **Real Leaderboard Logic**: Implementasi filter data untuk dropdown "Minggu Ini" dan "Bulan Ini" di Leaderboard (saat ini masih menampilkan All-Time).
2.  **Payment Tab Sync**: Menyelaraskan estimasi payout di tab Payment agar menggunakan jendela perhitungan yang sama (26 - 25).
3.  **Bank Data Integration**: Memastikan Admin dapat melihat data bank partner secara langsung di Dashboard Internal untuk mempermudah proses transfer komisi.
4.  **Tier Upgrade UX**: Menambahkan notifikasi/animasi saat partner berhasil naik Tier (misal: dari Bronze ke Silver) agar lebih memotivasi.
5.  **Weekly Top 1 Validation**: Menyiapkan filter global untuk admin guna memvalidasi syarat "Minimal 5 Closing Platform" sebelum mencairkan bonus mingguan.

---

### 🏮 PESAN UNTUK AI:
*Jangan pernah mengubah struktur CSS Global di `index.css` tanpa izin. Selalu gunakan angka dari tabel komisi di `SubscribersTab.jsx` sebagai referensi utama. Pastikan setiap fitur baru selalu mengecek `subscription_plan` milik User.*

**STATUS SISTEM: 90% - FOKUS BERIKUTNYA: PAYMENT SYNC & LEADERBOARD FILTER.**
