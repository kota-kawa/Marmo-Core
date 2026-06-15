# 📊 Flowchart 2: Operasi Dasbor User / Seller (End-to-End)

Dokumen ini menjelaskan alur navigasi dan logika kerja ketika pengguna (Seller) yang sudah aktif masuk ke dalam Dashboard User untuk menggunakan perkakas optimasi.

---

## 1. Visualisasi Alur (Mermaid Flowchart)

```mermaid
flowchart TD
    Start([User Login]) --> Dashboard[Dashboard Overview]
    Dashboard --> Route{Pilih Fitur?}
    
    %% Alur 1: Marketplace Integration
    Route -- Marketplace Connection --> CheckConnected{Sudah Terhubung?}
    CheckConnected -- No --> OAuth[Inisiasi OAuth Shopee / TikTok]
    OAuth --> CallBack[Simpan Access & Refresh Token ke marketplace_connections]
    CheckConnected -- Ya --> SyncStore[Jalankan Sync Worker]
    CallBack --> SyncStore
    SyncStore --> SyncDB[(Update tabel orders & products)]
    SyncDB --> DisplayOverview[Tampilkan Ringkasan Penjualan & Kesehatan Toko]
    
    %% Alur 2: Kalkulator HPP
    Route -- Kalkulator HPP SKU --> InputHPP[Input Modal Beli, Dus/Kemasan, Operasional, Komisi Platform]
    InputHPP --> CalcHPP[Hitung Rekomendasi Harga Jual Aktual & Margin Bersih]
    CalcHPP --> SaveCalc[(Simpan ke sku_calculations)]
    SaveCalc --> DisplayHPP[Tampilkan Detail Rekomendasi Margin Aman / Boncos]
    
    %% Alur 3: AI Toolkits (DeepSeek API)
    Route -- AI Generator --> SelectAI{Pilih Fitur AI?}
    SelectAI -- Generator Deskripsi / Naskah --> InputPrompt[Masukkan Nama Produk / Tema]
    InputPrompt --> TokenCheck{Token AI > 0 / Ultimate?}
    TokenCheck -- Tidak Cukup --> ShowAlert[Tampilkan Modal Top-up / Upgrade Paket]
    TokenCheck -- Ya --> CallDeepSeek[Kirim Prompt + RAG Context ke DeepSeek API]
    CallDeepSeek --> DeductToken[(Potong Saldo Token User)]
    DeductToken --> LogUsage[(Catat audit log di ai_usage_logs)]
    LogUsage --> RenderAIOutput[Tampilkan Teks Generator & Tombol Salin]
    
    %% Alur 4: Video Autopilot Staging
    Route -- Autopilot Video (Staging) --> QueueCheck{Ada Antrean Pending?}
    QueueCheck -- No --> BotIdle[Bot Tidur / Menunggu Konten Baru disetujui]
    QueueCheck -- Ya --> RenderVideo[MoviePy: Gabung Gambar, Teks Poin Visual 1-4, gTTS Voiceover & Backsound]
    RenderVideo --> SafeJitter[Terapkan Jeda Waktu Jitter Acak Menit Aman]
    SafeJitter --> SecureUpload[Browser Cookies: Login & Posting ke TikTok]
    SecureUpload --> MarkPosted[(Ubah status antrean menjadi posted)]
```

---

## 2. Rincian Logika & Aturan Sistem (Jika-Maka)

### 📊 1. Sinkronisasi Data Marketplace
* **Jika** token koneksi API marketplace kadaluwarsa (`expires_at < NOW()`):
  * **Maka** sistem otomatis mengirimkan *request* pembaruan menggunakan `refresh_token`.
  * Jika refresh token gagal, sistem menandai `sync_status = 'error'` dan meminta pengguna untuk re-otentikasi.

### 💰 2. Logika Penghitungan HPP
* Rumus Kalkulator HPP:
  $$\text{Total HPP} = \text{Modal Beli} + \text{Biaya Kemasan} + \text{Biaya Operasional} + \text{Ongkir Inbound}$$
  $$\text{Harga Jual Aktual} = \text{Harga Jual Marketplace} - \text{Diskon Voucher}$$
  $$\text{Komisi Platform} = \text{Harga Jual Aktual} \times \text{Persentase Komisi Platform}$$
  $$\text{Margin Bersih} = \text{Harga Jual Aktual} - \text{Total HPP} - \text{Komisi Platform} - \text{Biaya Admin Flat}$$
* **Jika** Margin Bersih bernilai negatif (< 0) atau di bawah target margin user:
  * **Maka** aplikasi menampilkan visualisasi status merah (**Boncos/Rugi**) dan merekomendasikan kenaikan harga jual minimum yang disarankan.

### 🤖 3. Validasi Gerbang Token AI
* **Jika** pengguna terdaftar dalam paket `ultimate`:
  * **Maka** pengecekan saldo token diabaikan (dianggap tak terbatas), namun volume token yang dikonsumsi tetap dicatat di tabel audit usage demi memonitor biaya pemakaian API.
* **Jika** pengguna bukan tipe `ultimate` dan saldo tokennya lebih kecil dari perkiraan penggunaan token:
  * **Maka** tombol 'Generate' dinonaktifkan secara dinamis dan modal pemberitahuan sisa koin muncul di layar.

---
*Dibuat oleh Antigravity Senior Team - Dokumentasi Resmi Tokcer AI*
