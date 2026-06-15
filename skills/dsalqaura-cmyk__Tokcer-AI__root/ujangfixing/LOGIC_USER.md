# Logic Document: Dashboard User

Dokumentasi ini menjelaskan logika bisnis, validasi hak akses, dan sistem kuota yang berjalan di Dashboard User Tokcer AI.

---

## 1. Logika Hak Akses & Sesi (Authentication)
*   **Pengecekan Role:** Begitu user berhasil login, sistem akan membaca data dari tabel `public.profiles`. Sistem memastikan bahwa kolom `role` bernilai `'user'`. Jika bernilai `'admin'` atau `'partner'`, user akan diarahkan ke dashboard masing-masing.
*   **Pengecekan Paket:** Sistem membaca `subscription_plan` untuk menampilkan badge paket (Starter, Pro, Elite, Ultimate) dan membatasi akses ke fitur-fitur tertentu berdasarkan kasta paket yang dibeli.

---

## 2. Logika Kuota Token AI (Credits)
Sistem Tokcer AI menggunakan sistem kuota berbasis Token untuk membatasi penggunaan fitur kecerdasan buatan:
*   **Saldo Token:** Jumlah saldo tersimpan di kolom `profiles.ai_tokens`.
*   **Pemotongan Token:** Setiap kali user menggunakan fitur AI (misalnya membuat analisa kompetitor atau deskripsi produk otomatis), sistem akan menghitung jumlah kata (Token) yang digunakan dan memotong saldo di database.
*   **Kondisi Habis:** Jika saldo token mencapai `0`, sistem akan memunculkan pop-up yang mengunci fitur AI dan menyarankan user untuk melakukan Upgrade Paket atau Top Up.

---

## 3. Logika Integrasi Marketplace
Untuk menarik data penjualan, user harus menghubungkan toko online mereka:
*   **Penyimpanan Token:** Saat otorisasi sukses, sistem menyimpan data API Key, Refresh Token, dan Expiry Date di tabel `marketplace_connections`.
*   **Keamanan:** Data koneksi ini diikat dengan `user_id` agar tidak bisa diakses oleh pengguna lain.
*   **Penarikan Data:** Saat tombol "Tarik Data" ditekan, sistem menggunakan token tersebut untuk menembak API Shopee/TikTok dan memasukkan data pesanan ke database lokal untuk siap dianalisa oleh AI.
