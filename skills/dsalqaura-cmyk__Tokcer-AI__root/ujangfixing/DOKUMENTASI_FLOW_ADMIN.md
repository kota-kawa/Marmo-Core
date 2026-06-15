# Dokumentasi Flow: Dashboard Admin - Penarikan Data sampai Konfigurasi AI

Dokumentasi ini menjelaskan alur proses yang dilalui oleh Administrator mulai dari melakukan penarikan data transaksi global hingga melakukan pengubahan konfigurasi kecerdasan buatan (AI) di sistem Tokcer AI.

## 1. Diagram Alur (Flowchart)

```text
       ┌───────────────────────────────────────────┐
       │        Mulai: Masuk Dashboard Admin       │
       └─────────────────────┬─────────────────────┘
                             │
                             ▼
       ┌───────────────────────────────────────────┐
       │        Sistem Tarik Data Global           │
       │      (Omzet, User Aktif, Partner)         │
       └─────────────────────┬─────────────────────┘
                             │
                             ▼
       ┌───────────────────────────────────────────┐
       │       Gunakan Fitur Business Insight      │
       │       (Analisa Data Pakai AI DeepSeek)    │
       └─────────────────────┬─────────────────────┘
                             │
                             ▼
       ┌───────────────────────────────────────────┐
       │       Masuk ke Menu Konfigurasi AI /      │
       │       Pengaturan Sistem                   │
       └─────────────────────┬─────────────────────┘
                             │
                             ▼
       ┌───────────────────────────────────────────┐
       │       Ubah Parameter AI / Rate Komisi /   │
       │       Prompts Template di Form            │
       └─────────────────────┬─────────────────────┘
                             │
                             ▼
                            / \
                          /     \
                        / Simpan? \
                        \        /
                          \    /
                            \/
                             │
               ┌─────────────┴─────────────┐
               │                           │
             Batal                       Simpan
               │                           │
               ▼                           ▼
       ┌───────────────┐           ┌───────────────┐
       │Kembali ke Menu│           │ Update Data ke│
       │Sebelumnya     │           │ Tabel ai_configs│
       └───────────────┘           └───────┬───────┘
                                           │
                                           ▼
                                   ┌───────────────┐
                                   │ Selesai:      │
                                   │ Aturan Sistem │
                                   │ Baru Berlaku  │
                                   └───────────────┘
```

## 2. Penjelasan Detail Proses

### A. Tahap Penarikan Data Global
1. Begitu Admin membuka Dashboard, sistem otomatis memanggil fungsi RPC (seperti `rpc_get_global_stats`) untuk menarik data real-time dari database.
2. Data yang ditarik meliputi: Total Omzet, Jumlah Pelanggan Aktif, Jumlah Partner, dan Total Pembayaran Komisi yang sukses.

### B. Tahap Analisa Business Insight (AI)
1. Admin dapat masuk ke menu Business Insight.
2. Sistem akan mengumpulkan data-data mentah penjualan atau performa SaaS, lalu mengirimkannya ke AI DeepSeek menggunakan prompt khusus yang sudah dirancang.
3. AI memberikan jawaban berupa analisa mendalam mengenai tren bisnis, produk terlaris, atau saran strategi berikutnya.

### C. Tahap Konfigurasi AI & Sistem
1. Admin membuka halaman Pengaturan / Konfigurasi AI.
2. Di halaman ini, Admin dapat mengubah nilai-nilai penting yang disimpan di tabel `public.ai_configs`, seperti:
   * **Commission Rates:** Mengatur berapa rupiah bagi hasil untuk partner per tier.
   * **Prompts:** Mengubah instruksi dasar untuk robot AI.
   * **Annual Bonuses:** Mengatur bonus tahunan untuk partner.
3. Setelah Admin menekan tombol "Simpan", sistem akan melakukan kueri `UPDATE` ke tabel `ai_configs`.
4. Aturan baru tersebut langsung berlaku detik itu juga untuk seluruh sistem tanpa perlu restart server!
