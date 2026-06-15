# Logic Document: Dashboard Partner

Dokumentasi ini menjelaskan logika bisnis, sistem komisi, dan pencatatan referral yang berjalan di Dashboard Partner Tokcer AI.

---

## 1. Logika Hak Akses & Sesi (Authentication)
*   **Pengecekan Role:** Sistem membaca tabel `profiles` dan memastikan `role` user tersebut bernilai `'partner'`.
*   **Pengecekan Status:** Sistem juga mengecek tabel `partners` untuk memastikan status akun partner tersebut adalah `'active'`. Jika berstatus `'suspended'` (diblokir), maka akses ke dashboard akan dikunci.

---

## 2. Sistem Komisi (FLAT RATE)
Mengikuti aturan baku yang tertulis di file perjanjian partner:
*   **Bukan Persentase Langsung:** Komisi partner tidak dihitung dinamis dari persentase saat transaksi, melainkan menggunakan **Angka Tetap (Flat Rate)** yang dihitung dari persentase acuan.
*   **Tabel Komisi (Acuan Ultimate Rp 1.999.000):**

| Plan | Bronze | Silver | Gold | Platinum |
|---|---|---|---|---|
| **Pro** | Rp 100.000 | Rp 100.000 | Rp 100.000 | Rp 100.000 |
| **Elite** | Rp 119.600 | Rp 149.600 | Rp 179.500 | Rp 199.400 |
| **Ultimate** | Rp 200.000 | Rp 240.000 | Rp 300.000 | Rp 360.000 |

*   **Akumulasi Saldo:** Setiap kali ada user referral yang aktif, nominal komisi di atas ditambahkan ke kolom `total_omzet` di tabel `partners`.

---

## 3. Sistem Pelacakan Referral
*   **Link Unik:** Setiap partner memiliki pengenal unik (Bisa berupa ID atau Nama Lengkap).
*   **Pencatatan:** Saat calon pelanggan mengklik link referral dan mengisi form pendaftaran, sistem menyimpan ID Partner tersebut ke dalam kolom `partner_id` di tabel `clients`.
*   **Trigger Cair:** Komisi **BELUM CAIR** saat user baru mendaftar (status: pending). Komisi baru otomatis dihitung dan masuk ke saldo partner saat status user tersebut berubah menjadi `'active'` (setelah sukses bayar di Midtrans).

---

## 4. Sistem Penarikan Dana (Payouts)
*   Partner dapat melihat riwayat pengiriman uang komisi mereka yang ditarik dari tabel `payouts`.
*   Jika admin sudah mentransfer uang dan mengubah status transaksi di tabel `payouts` menjadi `'paid'`, maka data tersebut akan muncul sebagai "Komisi Berhasil Dicairkan" di dashboard partner.
