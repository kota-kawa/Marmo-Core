# 🏮 MANUAL BOOK: EXPLORER HPP & MARGIN TOKCER AI (V1.0 - MEI 2026)
**Panduan Lengkap Penggunaan Alat Simulasi Profitabilitas & Struktur Biaya Marketplace Ter-update (Mei & Juni 2026)**

---

## 📌 DAFTAR ISI
1. [PENDAHULUAN & PRINSIP MULTI-LAYER COST](#1-pendahuluan--prinsip-multi-layer-cost)
2. [SISTEM BATASAN PAKET KALKULATOR](#2-sistem-batasan-paket-kalkulator)
3. [BAGIAN 1: INPUT LAYER BIAYA (STEP-BY-STEP)](#3-bagian-1-input-layer-biaya-step-by-step)
4. [BAGIAN 2: HASIL KALKULASI & METRIK KUNCI](#4-bagian-2-hasil-kalkulasi--metrik-kunci)
5. [BAGIAN 3: ANALISIS RISIKO RETUR & COD (ATURAN JUNI 2026)](#5-bagian-3-analisis-risiko-retur--cod-aturan-juni-2026)
6. [BAGIAN 4: PENGATURAN KHUSUS TIAP PLATFORM (SHOPEE vs TOKOPEDIA/TIKTOK)](#6-bagian-4-pengaturan-khusus-tiap-platform-shopee-vs-tokopediatiktok)
7. [BAGIAN 5: OPERASI LANJUTAN (SIMPAN, BANDINGKAN & BULK IMPORT)](#7-bagian-5-operasi-lanjutan-simpan-bandingkan--bulk-import)

---

## 1. PENDAHULUAN & PRINSIP MULTI-LAYER COST
Kalkulator HPP & Margin Tokcer AI dirancang khusus untuk membantu seller e-commerce menemukan **Harga Jual Sebenarnya (True Profitability Price)** dengan memecah biaya ke dalam 8 Layer Biaya terstruktur.

Alat ini sangat krusial karena biaya jualan di e-commerce saat ini tidak lagi hanya sekadar komisi dasar, melainkan terdiri atas biaya logistik, program promosi, retur COD, hingga bunga cicilan pembeli.

---

## 2. SISTEM BATASAN PAKET KALKULATOR
Fitur-fitur lanjutan kalkulator dikunci berdasarkan kasta akun pengguna:

- **Starter (Gratis):** Hanya bisa menghitung simulasi instan di tempat. Tidak bisa menyimpan SKU ke database.
- **Pro Edition:**
  - Maksimal simpan **10 SKU**.
  - Bisa menggunakan fitur **Export CSV** untuk mengunduh rincian kalkulasi SKU.
- **Elite Edition:**
  - Penyimpanan SKU **Tanpa Batas**.
  - Akses penuh **Compare Mode** (Analisis komparatif berdampingan hingga 4 SKU sekaligus).
- **Ultimate Edition:**
  - Otorisasi penuh **Bulk Import CSV** (Mengunggah ratusan SKU sekaligus dari file excel/CSV).

---

## 3. BAGIAN 1: INPUT LAYER BIAYA (STEP-BY-STEP)
Kalkulator dibagi menjadi beberapa blok panel input terstruktur yang mewakili **8 Layer Biaya** secara akurat:

### 📦 Layer 1: Fixed Cost (Produksi & Logistik Awal)
Blok input ini menentukan HPP dasar produk Anda sebelum masuk ke marketplace:
1. **Nama SKU:** Nama atau kode produk Anda (Cth: `Kaos Polos Cotton 30s`).
2. **HPP / Modal Beli (Rp):** Harga pokok pembelian barang dari supplier atau biaya produksi bahan baku per unit.
3. **Packaging (Rp):** Biaya pembungkus, bubble wrap, kardus, lakban, dan stiker per unit produk.
4. **Ongkir Ditanggung Seller (Subsidi Rp):** Jika Anda menawarkan subsidi ongkos kirim manual atau flat kepada pembeli.
5. **Biaya Lain-lain / Inbound (Rp):** Biaya pengiriman barang dari pabrik ke gudang Anda, atau upah admin packing per unit.

> [!TIP]
> **Total HPP per Unit** akan otomatis terhitung di bagian bawah box ini:
> $$\text{Total HPP} = \text{Modal Beli} + \text{Packaging} + \text{Ongkir Ditanggung Seller} + \text{Biaya Lain-lain}$$

---

### 🏪 Layer 2: Platform Commission & Status Fee
Komisi dasar platform e-commerce dan tambahan komisi berdasarkan reputasi/tipe seller:
1. **Pilih Platform:** Tokopedia, TikTok Shop, Shopee, atau Website (Masing-masing mengaktifkan aturan potongan unik).
2. **Kategori Produk:** Fashion, Elektronik, atau Umum (Sistem akan otomatis merekomendasikan komisi standar platform).
3. **Platform Commission (%):** Potongan biaya admin komisi dasar platform.
4. **MALL Status (+25%):** Centang jika toko Anda adalah Toko Mall resmi. Sistem akan menaikkan komisi dasar sebesar **25%** (Faktor pengali: `1.25`).
5. **Star / Star+ Seller Fee (+1%):** Eksklusif di Shopee, menambah biaya admin 1% untuk seller bereputasi bintang.

---

### 🔑 Layer 3: Per-Order Fixed Fee (Rp)
Biaya penanganan tetap (*flat*) yang dikenakan per transaksi sukses oleh platform:
* *Rekomendasi default sistem tahun 2026:* **Rp 1.250** per transaksi sukses.

---

### 📣 Layer 4: Platform Programs, Marketing Fees & Dynamic Commission
Biaya keikutsertaan program pemasaran platform dan potongan dinamis:
1. **GMV Max & Growth Xtra (Discount Multiplier):** 
   - Jika keduanya aktif, Anda mendapat potongan admin khusus hingga **8.18%** (Faktor pengali: `0.9182`).
   - Jika salah satu aktif, Anda mendapat potongan admin sekitar **5%** (Faktor pengali: `0.95`).
2. **Gratis Ongkir Xtra (GOX) (Shopee):** Biaya komisi **4%** dengan batas maksimal (CAP) **Rp 10.000** per unit.
3. **Cashback Xtra (CBX) (Shopee):** Biaya komisi **1.4%** dengan batas maksimal (CAP) **Rp 10.000** per unit.
4. **Voucher Promo Xtra (Shopee):** Potongan tambahan **2%** dengan CAP **Rp 10.000**.
5. **Komisi Dinamis (%):** Biaya administrasi opsional untuk mitigasi risiko transaksi yang berubah secara berkala.

---

### ⏳ Layer 5: Pre-Order (PO) Addon (+3%)
Aktifkan jika produk dibuat dengan sistem Pre-Order. Sistem otomatis menambahkan beban biaya admin 3% sesuai dengan ketentuan resmi regulasi e-commerce terbaru.

---

### 🚚 Layer 6: Logistics Service Fee (Rp)
Biaya penanganan pengiriman dan logistik yang dibebankan per pesanan, digunakan untuk menghitung kerugian jika barang diretur pembeli.

---

### 🤝 Layer 7: Affiliate Commission (%)
Jatah komisi yang diberikan kepada kreator affiliator jika produk terjual lewat jaringan afiliasi (Cth: TikTok Affiliate Creator).

---

### 🎯 Layer 8: Ads Budget (% Harga)
Anggaran iklan berbayar (iklan produk, kata kunci, pencarian) yang dibebankan per unit produk terjual.

---

## 4. BAGIAN 2: HASIL KALKULASI & METRIK KUNCI
Begitu Anda memasukkan angka-angka di atas, panel **Calculated Results** di sisi kanan akan memperbarui hasil analisis keuangan secara instan:

1. **HPP Riil per Unit:** Beban biaya bersih awal Anda.
2. **BEP Price (Break-Even Point):** Harga jual minimal agar Anda tidak rugi sepeser pun setelah dipotong semua komisi dan biaya admin.
3. **Recommended Price:** Harga jual yang direkomendasikan agar Anda bisa mengamankan **Target Margin %** yang Anda masukkan.
4. **Net Profit per Unit:** Keuntungan bersih yang masuk ke kantong Anda dari harga jual aktual setelah dipotong HPP dan seluruh potongan biaya marketplace.
5. **Margin Bersih (%) & ROI Modal (%):**
   - **Margin Bersih:** Persentase profit bersih dari total harga jual.
   - **ROI Modal:** Persentase pengembalian modal dari uang yang Anda keluarkan untuk HPP.

---

## 5. ANALISIS RISIKO RETUR & COD (ATURAN JUNI 2026)
*Penting: Aturan Baru Penanganan COD & Pengembalian Barang*

Tokcer AI adalah satu-satunya kalkulator HPP yang sudah mengintegrasikan **Return Risk Simulation** untuk mengantisipasi COD fiktif atau retur barang:

### ⚠️ Komponen Pengurang Profit (Lost Per Return):
Jika barang diretas/retur oleh pembeli setelah berhasil dikirim:
- Biaya logistik pengiriman (Layer 6) tetap ditagih oleh kurir.
- Biaya komisi dinamis (Layer 4) dan admin flat (Layer 3) **tidak dapat dikembalikan** (*non-refundable*).
- **Failed Delivery Fee (Aturan 1 Juni 2026):** Dikenakan biaya penanganan pengembalian COD fiktif hingga **Rp 5.000** per paket gagal kirim.

### 🧠 Rumus Return Risk Cost:
Sistem akan memotong profit kotor Anda secara otomatis menggunakan tingkat return rate Anda:
$$\text{Return Risk Cost} = \text{Return Rate (\%)} \times (\text{Admin Flat} + \text{Logistics Service Fee} + \text{Komisi Dinamis} + \text{Biaya Packaging} + \text{Failed Delivery Fee})$$

---

## 6. PENGATURAN KHUSUS TIAP PLATFORM (SHOPEE vs TOKOPEDIA/TIKTOK)

### 🟢 Tokopedia & TikTok Shop (Sistem CAP Rp 650.000):
Untuk produk bernilai jutaan rupiah (premium), biaya komisi platform dasar dibatasi maksimal **Rp 650.000** per barang. Kalkulator Tokcer secara otomatis memotong biaya admin jika harga jual aktual Anda melewati batas CAP ini.

### 🟠 Shopee (Program Fees & CAP Rp 10.000):
Jika Anda memilih platform Shopee, panel input khusus program Shopee akan muncul:
- **Gratis Ongkir Xtra (GOX):** Memotong biaya komisi **4%** dengan batas maksimal (CAP) **Rp 10.000** per unit produk.
- **Cashback Xtra (CBX):** Memotong biaya komisi **1.4%** dengan batas maksimal (CAP) **Rp 10.000** per unit produk.
- **Voucher Promo Xtra:** Potongan tambahan **2%** dengan CAP **Rp 10.000**.
- **Tenor SPayLater:** Potongan bunga cicilan yang dibebankan ke seller jika pembeli membayar menggunakan SPayLater (Pilihan: 2.5% atau 4%).
- **Star / Star+ Seller Fee:** Tambahan potongan komisi admin sekitar **1%** untuk seller dengan reputasi bintang.

---

## 7. BAGIAN 5: OPERASI LANJUTAN (SIMPAN, BANDINGKAN & BULK IMPORT)

### 💾 Cara Menyimpan SKU ke Database:
1. Masukkan semua data input produk Anda secara lengkap.
2. Klik tombol **SIMPAN SKU** di bagian kanan atas.
3. Data akan disimpan di Supabase secara otomatis, dan sistem akan mengunduh file `.csv` ringkasan SKU tersebut ke komputer Anda untuk arsip offline.

### 🔀 Cara Menggunakan Compare Mode (Bandingkan SKU):
*Eksklusif (Elite & Ultimate)*
1. Klik tombol **COMPARE MODE** di bagian atas.
2. Centang maksimal **4 SKU** yang sudah pernah Anda simpan sebelumnya.
3. Sistem akan menyajikan tabel analisis komparasi berdampingan:
   - Membandingkan HPP, Profit Bersih, ROI, dan Margin % antar produk.
   - Berguna untuk menentukan produk mana yang paling mendatangkan keuntungan terbesar bagi bisnis Anda.

### 📥 Cara Menggunakan Bulk Import CSV:
*Eksklusif (Ultimate)*
1. Klik tombol **Bulk Import**.
2. Pilih file CSV berisi daftar SKU massal dari komputer Anda.
3. Pastikan kolom urutan data CSV sesuai dengan format standar:
   `sku_name`, `platform`, `modal_beli`, `biaya_packaging`, `biaya_lain_lain`, `biaya_ongkir_inbound`.
4. Ratusan SKU Anda akan langsung masuk ke database kalkulator secara instan tanpa perlu input manual satu per satu.

---
*Gunakan Kalkulator HPP & Margin Tokcer AI secara disiplin sebelum meluncurkan kampanye diskon massal atau menetapkan harga jual di marketplace Anda!* 🚀🏆💎🔥
