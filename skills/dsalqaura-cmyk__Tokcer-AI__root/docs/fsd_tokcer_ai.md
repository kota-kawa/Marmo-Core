# ⚙️ Functional Specification Document (FSD) - Tokcer AI

## 1. Arsitektur Sistem
Tokcer AI menggunakan arsitektur **Serverless** dengan spesifikasi:
*   **Hosting**: VPS / Static Hosting (Vite Build).
*   **Backend as a Service (BaaS)**: Supabase.
*   **Authentication**: Supabase Auth (Email/Password & Social Login).
*   **Database**: PostgreSQL (Supabase).
*   **Storage**: Supabase Buckets (Bukti Bayar, Foto Profil).

---

## 2. Skema Database (Tabel Utama)

### A. Tabel `profiles`
Menyimpan data identitas user dan role akses.
*   `id`: UUID (Primary Key, Link ke Auth).
*   `full_name`: Nama Lengkap.
*   `role`: 'admin', 'partner', 'user'.
*   `tokens`: Sisa kredit AI.

### B. Tabel `clients`
Menyimpan data seller/toko yang didaftarkan.
*   `id`: UUID.
*   `shop_name`: Nama Toko.
*   `status`: 'pending', 'active', 'suspended'.
*   `plan`: 'starter', 'pro', 'elite', 'ultimate'.
*   `payment_proof_url`: Link ke gambar bukti bayar di Storage.

### C. Tabel `ai_configs`
Penyimpanan kunci API dan instruksi sistem (Guardrails).
*   `key`: 'system_prompt', 'resend_api_key', 'rag_knowledge_base'.
*   `value`: Isi dari konfigurasi tersebut.

---

## 3. Logika Integrasi API

### A. DeepSeek AI (Content Generator)
1.  Frontend mengirimkan `prompt` ke DeepSeek API.
2.  `System Prompt` diambil dari tabel `ai_configs` sebagai instruksi dasar.
3.  `Authorization`: Bearer Token (DeepSeek API Key).
4.  Respon ditampilkan ke user dan dicatat di `ai_usage_logs`.

### B. Resend API (Welcome Email)
1.  Dijalankan secara otomatis saat Admin klik **Approve**.
2.  Fungsi `sendWelcomeEmail` mengambil API Key dari `ai_configs`.
3.  Mengirimkan email HTML berisi detail akun ke alamat email user.

---

## 4. Logika Bisnis Khusus (Custom Logic)

### A. Prosedur Aktivasi Akun (`rpc_activate_account`)
Fungsi ini berjalan di sisi Database (PostgreSQL) untuk menjamin keamanan:
1.  Mengecek apakah user sudah ada di Auth.
2.  Jika belum, membuat akun Auth baru.
3.  Memperbarui status di tabel `clients` menjadi `active`.
4.  Memberikan saldo token awal sesuai paket yang dipilih.

### B. Filter Nama File (Storage Safety)
Mencegah error saat upload gambar dengan cara membersihkan karakter spesial dan spasi dari nama file sebelum masuk ke bucket Supabase.

---

## 5. Keamanan & Akses (RLS)
*   **Row Level Security (RLS)**: Diaktifkan di seluruh tabel.
*   **Admin Policy**: Hanya user dengan `role = 'admin'` yang bisa mengakses tabel `ai_configs` dan melihat data pendaftar partner.
*   **User Policy**: User hanya bisa melihat data toko dan riwayat AI milik mereka sendiri (`auth.uid() = user_id`).

---
**Dibuat Oleh**: Antigravity AI (Siti)
**Tanggal**: 30 April 2026
