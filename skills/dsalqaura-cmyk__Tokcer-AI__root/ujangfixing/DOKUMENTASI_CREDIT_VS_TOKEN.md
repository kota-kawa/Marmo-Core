# 🏮 TOKCER AI: STANDARISASI KONSEP (CREDIT VS TOKEN)

Dokumen ini dibuat oleh Ujang untuk menyamakan persepsi antara Developer, QA, dan Tim Bisnis mengenai perbedaan istilah "Credit" dan "Token" di dalam ekosistem Tokcer AI.

---

## 📊 1. CREDIT (Tampilan Dashboard User)
**Definisi:** Satuan kuota pemakaian fitur yang dipahami oleh pengguna.
*   **Aturan Main:** 1x Generate Konten / 1x Aksi = Mengurangi **1 Credit**.
*   **Lokasi Tampil:** Sidebar Dashboard Pojok Kiri Bawah (Kuota AI).
*   **Batas Kuota Berdasarkan Paket (quotaMap):**
    *   **Starter:** 50 Credit
    *   **Pro:** 300 Credit
    *   **Elite:** 1000 Credit
    *   **Ultimate:** 3000 Credit (Di UI ditampilkan sebagai "Unlimited").

> ⚠️ **Catatan Penting:** Robot Aktivasi di database (`rpc_activate_account`) HARUS memasukkan angka-angka ini ke kolom saldo user, BUKAN ribuan token API.

---

## 🤖 2. TOKEN (Konsumsi API AI / Deepseek)
**Definisi:** Satuan panjang karakter teks yang diproses oleh server AI (Deepseek/OpenAI).
*   **Aturan Main:** 1 kata rata-rata mengonsumsi 1.3 Token API. Satu kali generate bisa menghabiskan 500 - 2000 Token API tergantung panjang prompt.
*   **Lokasi Tampil:** **TIDAK DITAMPILKAN KE USER**. Ini hanya untuk monitoring biaya server oleh tim internal.
*   **Tujuan:** Mencegah user pusing melihat angka kuota yang berkurang ribuan dalam sekali klik.

---

## 🛠️ Rencana Tindakan (Action Plan)
1.  Mengubah nilai variabel `v_tokens` di dalam fungsi SQL `rpc_activate_account` agar menggunakan nilai **Credit** di atas.
2.  Melakukan koreksi data pada akun-akun yang terlanjur mendapatkan ribuan credit (seperti kasus 5000/300 tadi).
