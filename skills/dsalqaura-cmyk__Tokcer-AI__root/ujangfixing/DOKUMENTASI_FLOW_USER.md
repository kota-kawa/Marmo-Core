# Dokumentasi Flow: Dashboard User - Login sampai Penarikan Data

Dokumentasi ini menjelaskan alur proses yang dilalui oleh pengguna (User) mulai dari masuk ke sistem (Login) hingga melakukan penarikan data toko online mereka untuk dianalisa.

## 1. Diagram Alur (Flowchart)

```text
       ┌───────────────────────────────────────────┐
       │            Mulai: Halaman Login           │
       └─────────────────────┬─────────────────────┘
                             │
                             ▼
       ┌───────────────────────────────────────────┐
       │       Input Email & Password User         │
       └─────────────────────┬─────────────────────┘
                             │
                             ▼
                            / \
                          /     \
                        / Valid? \
                        \        /
                          \    /
                            \/
                             │
               ┌─────────────┴─────────────┐
               │                           │
             Gagal                       Sukses
               │                           │
               ▼                           ▼
       ┌───────────────┐           ┌───────────────┐
       │Tampilkan Error│           │ Masuk ke      │
       │Password Salah │           │ Dashboard User│
       └───────────────┘           └───────┬───────┘
                                           │
                                           ▼
                                   ┌───────────────┐
                                   │ Cek Koneksi   │
                                   │ Toko Marketpl │
                                   └───────┬───────┘
                                           │
                                           ▼
                                          / \
                                        /     \
                                      / Terhubung\
                                      \    ?     /
                                        \     /
                                          \ /
                                           │
                             ┌─────────────┴─────────────┐
                             │                           │
                           Belum                       Sudah
                             │                           │
                             ▼                           ▼
                     ┌───────────────┐           ┌───────────────┐
                     │ Hubungkan Toko│           │ Klik Tombol   │
                     │ Shopee/TikTok │           │ Tarik Data    │
                     └───────┬───────┘           └───────┬───────┘
                             │                           │
                             ▼                           ▼
                     ┌───────────────┐           ┌───────────────┐
                     │ Redirect ke   │           │ Sistem Ambil  │
                     │ Otorisasi API │           │ Data Penjualan│
                     └───────┬───────┘           └───────┬───────┘
                             │                           │
                             ▼                           ▼
                     ┌───────────────┐           ┌───────────────┐
                     │ Simpan Token  │           │ Data Masuk ke │
                     │ Akses Toko ke │           │ DB & Siap     │
                     │ Database      │           │ Dianalisa AI  │
                     └───────────────┘           └───────────────┘
```

## 2. Penjelasan Detail Proses

### A. Tahap Login
1. User memasukkan email dan password yang telah didaftarkan pada halaman login.
2. Supabase Auth melakukan verifikasi kredensial.
3. Jika gagal (salah password/email), sistem memunculkan notifikasi error.
4. Jika sukses, user diarahkan masuk ke halaman utama Dashboard User.

### B. Tahap Pengecekan Toko (Marketplace)
1. Di dalam dashboard, sistem otomatis mengecek apakah user sudah menghubungkan toko (Shopee, TikTok, Lazada, dll) di tabel `marketplace_connections`.
2. **Jika Belum:** User diarahkan ke halaman integrasi untuk menekan tombol "Hubungkan Toko". Sistem akan me-redirect user ke halaman resmi marketplace untuk memberikan izin akses API.
3. **Jika Sudah:** User bisa langsung melihat ringkasan performa toko yang ada.

### C. Tahap Penarikan Data (Data Retrieval)
1. User menekan tombol "Tarik Data" atau "Sinkronisasi" untuk mengambil data pesanan dan produk terbaru.
2. Sistem melakukan request ke API Marketplace menggunakan Token Akses yang tersimpan.
3. Data pesanan, omzet, dan produk ditarik lalu disimpan ke database lokal Tokcer AI.
4. Setelah data terkumpul, user dapat menggunakan fitur AI (seperti DeepSeek) untuk menganalisa keuntungan, HPP, maupun strategi penjualan berikutnya.
