# Logic Document: Registrasi & Aktivasi Akun (Landing Page)

Dokumentasi ini menjelaskan logika bisnis, perhitungan matematika, dan aturan database yang berjalan di balik layar saat pengguna melakukan registrasi hingga akun diaktifkan.

---

## 1. Logika Penentuan Harga & Durasi (Frontend)
Saat user memilih paket di `RegisterModal.jsx`, sistem akan menghitung biaya yang harus dibayar ke Midtrans dengan aturan:

| Paket | Siklus (Billing) | Harga | Token AI Didapat |
| :--- | :--- | :--- | :--- |
| **Starter** | Bulanan | Rp 0 (Gratis) | 1,000 |
| **Pro** | Bulanan | Rp 499,000 | 5,000 |
| **Pro** | Tahunan | Rp 5,489,000 | 5,000 |
| **Elite** | Bulanan | Rp 999,000 | 15,000 |
| **Elite** | Tahunan | Rp 10,989,000 | 15,000 |
| **Ultimate** | Bulanan | Rp 1,999,000 | 50,000 |
| **Ultimate** | Tahunan | Rp 21,989,000 | 50,000 |

*Catatan: Jika koneksi ke database gagal saat mengambil harga live, sistem menggunakan harga Fallback (cadangan) di atas yang di-hardcode di frontend.*

---

## 2. Logika Masa Aktif (Expires At) - *SaaS Mahal Mode*
Diatur di dalam database via fungsi `rpc_activate_account` baris 79:
*   Jika `billing_cycle` bernilai **'Yearly'**, maka tanggal kadaluarsa dihitung: `NOW() + INTERVAL '365 days'`.
*   Jika bernilai **'Monthly'** atau kosong, maka dihitung: `NOW() + INTERVAL '30 days'`.

---

## 3. Logika Komisi Partner (Referral)
Jika user mendaftar menggunakan link referral milik Partner, maka sistem akan menjalankan logika bagi hasil di database:

### A. Penentuan Pangkat (Tier) Partner
Sistem menghitung jumlah referral aktif milik partner tersebut untuk menentukan pangkatnya secara dinamis:
*   **Platinum**: Minimal 15 referral aktif DAN minimal 5 di antaranya paket Elite/Ultimate.
*   **Gold**: Minimal 8 referral aktif DAN minimal 2 di antaranya paket Elite/Ultimate.
*   **Silver**: Minimal 5 referral aktif DAN minimal 2 di antaranya paket Elite/Ultimate.
*   **Bronze**: Jika tidak memenuhi syarat di atas (Default).

### B. Perhitungan Nominal Komisi
*   Nilai komisi dasar diambil dari tabel `ai_configs` dengan kunci `commission_rates_v3` berdasarkan kombinasi **Paket yang dibeli user** dan **Tier Partner**.
*   **Aturan Tahunan:** Jika user membeli paket tahunan, rumusnya adalah: `(Komisi Bulanan x 11) + Bonus Tahunan` (Bonus tahunan diambil dari config `annual_plan_bonuses`).

### C. Logika Bonus Performance (Volume Milestone)
Partner mendapatkan bonus tambahan satu kali (One Time) jika mencapai jumlah referral aktif tertentu:
*   Mencapai **5 Referral**: Bonus Rp 150,000.
*   Mencapai **10 Referral**: Bonus Tambahan Rp 350,000.
*   Mencapai **15 Referral**: Bonus Tambahan Rp 750,000.

Sistem mengecek tabel `ai_usage_logs` untuk memastikan partner tersebut belum pernah menerima bonus milestone yang sama sebelumnya.
