# Logic Document: Dashboard Admin

Dokumentasi ini menjelaskan logika bisnis, hak akses penuh (Super Power), dan pengelolaan konfigurasi sistem yang berjalan di Dashboard Admin Tokcer AI.

---

## 1. Logika Hak Akses & Sesi (Super Admin)
*   **Pengecekan Role Berlapis:** Sistem membaca data dari tabel `profiles` dan memastikan `role` bernilai `'admin'`. 
*   **Fitur Pengunci Baru:** Untuk keamanan tinggi, pengecekan admin tidak lagi membaca `localStorage` (yang rawan dibobol), melainkan wajib membaca langsung dari database secara real-time.

---

## 2. Logika Pengambilan Data Global (Financial Hub)
*   Sistem menggunakan fungsi tersentralisasi (seperti RPC `rpc_get_global_stats`) untuk menghitung total uang masuk, total pengeluaran komisi, dan jumlah user aktif.
*   **Filter Periode:** Tombol filter waktu (Daily, Weekly, Monthly) bekerja dengan cara menyaring `created_at` pada tabel transaksi/pesanan sesuai dengan rentang waktu yang dipilih admin.

---

## 3. Logika Manajemen Partner (Fitur Baru!)
Admin memiliki kendali penuh atas akun partner melalui pop-up kaca (Glassmorphism) yang baru kita buat:
*   **Ubah Tier Manual:** Saat admin memasukkan nama Tier baru (Bronze, Silver, Gold, Platinum) via prompt, sistem langsung menembak database `update` ke kolom `tier` di tabel `partners`. Ini memotong jalur otomatisasi jika admin ingin memberikan promo khusus pangkat ke partner tertentu.
*   **Suspend / Blokir:** Jika diklik, sistem mengubah status partner menjadi `'suspended'`. Akun tersebut otomatis tidak akan bisa melihat data komisi atau login ke portal partner mereka.

---

## 4. Logika Konfigurasi Sistem (ai_configs)
Ini adalah otak dari fleksibilitas Tokcer AI:
*   Admin dapat mengubah isi tabel `ai_configs` langsung dari antarmuka dashboard (jika fitur UI-nya sudah dihubungkan).
*   Segala aturan angka komisi, bonus tahunan, hingga instruksi prompt AI ditarik dari tabel ini secara dinamis.
*   Perubahan pada tabel ini langsung mengubah cara kerja fungsi pendaftaran (`rpc_activate_account`) saat itu juga tanpa perlu melakukan koding ulang atau deploy server.
