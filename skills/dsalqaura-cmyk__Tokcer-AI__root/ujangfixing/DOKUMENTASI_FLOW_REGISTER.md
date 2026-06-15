# Dokumentasi Flow: Landing Page - Register sampai Account Created

Dokumentasi ini menjelaskan alur proses pendaftaran pengguna di Tokcer AI, mulai dari pengisian form di Landing Page hingga akun berhasil dibuat dan diaktifkan.

## 1. Diagram Alur (Flowchart)

```text
       ┌───────────────────────────────────────────┐
       │        Mulai: User di Landing Page        │
       └─────────────────────┬─────────────────────┘
                             │
                             ▼
       ┌───────────────────────────────────────────┐
       │          Pilih Paket & Isi Form           │
       └─────────────────────┬─────────────────────┘
                             │
                             ▼
                            / \
                          /     \
                        /  Paket  \
                        \  Apa?   /
                          \     /
                            \ /
                             │
               ┌─────────────┴─────────────┐
               │                           │
       Starter (Gratis)             Berbayar (Pro/Elite)
               │                           │
               ▼                           ▼
       ┌───────────────┐           ┌───────────────┐
       │ Simpan ke DB  │           │ Panggil API   │
       │ Status:Pending│           │ midtrans-init │
       └───────┬───────┘           └───────┬───────┘
               │                           │
               ▼                           ▼
       ┌───────────────┐           ┌───────────────┐
       │   Selesai:    │           │ Buka Popup    │
       │ Menunggu      │           │ Midtrans Snap │
       │ Aktivasi      │           └───────┬───────┘
       └───────────────┘                   │
                                           ▼
                                   ┌───────────────┐
                                   │  User Bayar   │
                                   └───────┬───────┘
                                           │
                                           ▼
                                   ┌───────────────┐
                                   │Midtrans Kirim │
                                   │Webhook Notif  │
                                   └───────┬───────┘
                                           │
                                           ▼
                                   ┌───────────────┐
                                   │ Jalankan RPC  │
                                   │ Akun Aktif!   │
                                   └───────┬───────┘
                                           │
                                           ▼
                                   ┌───────────────┐
                                   │ Akun Dibuat & │
                                   │ Email Sukses  │
                                   └───────────────┘
```



## 2. Penjelasan Detail Proses

### A. Tahap Pengisian Form (Frontend)
1. User mengunjungi Landing Page dan memilih salah satu paket (Starter, Pro, Elite, Ultimate).
2. Muncul `RegisterModal` yang meminta data: Nama Toko, Email, WhatsApp, Platform Jualan, dan Kode Affiliate (jika ada).
3. Sistem melakukan validasi dasar (misalnya: memastikan email valid dan platform jualan sudah dipilih).

### B. Cabang Alur Berdasarkan Paket

#### 1. Paket Starter (Gratis)
* Data langsung dikirim ke tabel `clients` dengan kueri `insert`.
* Status awal diset sebagai `'pending'`.
* Tidak ada proses pembayaran. Akun biasanya diaktifkan manual oleh admin atau sistem otomatis lain.

#### 2. Paket Berbayar (Pro / Elite / Ultimate)
* Sistem menghitung jumlah biaya berdasarkan `billing_cycle` (Bulanan/Tahunan) dan mencari harga asli dari tabel `ai_configs` (dengan fallback harga keras jika gagal).
* Frontend memanggil Supabase Edge Function bernama `midtrans-init`.
* Edge function tersebut mendaftarkan transaksi ke Midtrans untuk mendapatkan **Snap Token**.
* Frontend membuka jendela pop-up Midtrans Snap agar user bisa membayar menggunakan QRIS, Bank Transfer, dll.

### C. Tahap Aktivasi (Backend)
1. Setelah user sukses membayar, Midtrans mengirimkan sinyal (Webhook) ke Edge Function `midtrans-webhook`.
2. Webhook memanggil fungsi database (RPC) bernama **`rpc_activate_account`**.
3. Fungsi tersebut melakukan:
   * Mendaftarkan email user ke sistem autentikasi (`auth.users`) jika belum ada.
   * Membuat/mengupdate profil di `public.profiles` dan memberikan jatah token AI.
   * Mengubah status di `public.clients` menjadi `'active'`.
   * Menghitung tanggal kadaluarsa (`expires_at`) 30 atau 365 hari ke depan (Fitur Baru).
   * Menghitung dan membagikan komisi ke partner jika user tersebut mendaftar menggunakan link referral.
