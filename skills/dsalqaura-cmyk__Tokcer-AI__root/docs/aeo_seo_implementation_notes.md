# 📝 PANDUAN IMPLEMENTASI & DOKUMENTASI ZERO-COST AEO-SEO

**Tanggal Update**: 20 Mei 2026  
**Status**: Aktif & Teruji  
**Modifikasi Utama**: `aeo-engine/src/main.js`, `aeo-engine/src/linker.js`, `aeo-engine/config/keywords_map.json`

---

## 🚀 1. FITUR YANG TELAH DIIMPLEMENTASIKAN

### **A. Integrasi Google Gemini 1.5 Flash (Free Tier - Rp 0,-)**
* **Logika:** Fungsi `callAI` di `aeo-engine/src/main.js` sekarang secara otomatis mendeteksi variabel `GEMINI_API_KEY` atau `VITE_GEMINI_API_KEY`.
* **Prioritas:** Jika API Key Gemini ditemukan, sistem akan memprioritaskan pemanggilan ke model **Gemini 1.5 Flash** via API REST resmi Google AI Studio (Gratis). Jika tidak ditemukan, sistem akan otomatis melakukan *fallback* ke API DeepSeek/OpenAI yang terkonfigurasi di `AI_API_KEY`.
* **Budget Guard:** Menghitung jumlah kata keluaran secara kasar untuk dicatat ke dalam `token_budget.json` sebagai pembatas agar penggunaan harian tetap terkendali.

### **B. Programmatic Internal Linking (Agent 4 - Rp 0,-)**
* **Logika:** Modul `aeo-engine/src/linker.js` memindai artikel Markdown hasil buatan Agent 3 dan menyuntikkan tautan internal berdasarkan pemetaan di `aeo-engine/config/keywords_map.json`.
* **Fitur Keamanan Teks (Syntax Shield):**
  * **Melindungi Header:** Tidak akan merusak tag `#`, `##` jika kata kunci berada di dalamnya.
  * **Melindungi Code Blocks:** Teks di dalam blok kode ` ``` ` dilewati secara aman.
  * **Melindungi Inline Code:** Kata kunci di dalam tanda backtick `` ` `` tidak akan diberikan tautan.
  * **Melindungi Tautan Aktif:** Tautan Markdown `[text](url)` dan gambar `![alt](url)` yang sudah ada tidak akan ditimpa atau dibungkus ulang (mencegah broken syntax).
  * **Mencegah Link Stuffing:** Hanya kemunculan pertama kata kunci di artikel yang diberikan tautan untuk menjaga kenyamanan pembaca dan kepatuhan SEO.

---

## 🛠️ 2. PETUNJUK KONFIGURASI DI PRODUCTION

Untuk menjalankan AEO Engine secara **100% Gratis**, lakukan langkah berikut pada lingkungan production:

1. **Dapatkan API Key Gemini:**
   * Kunjungi [Google AI Studio](https://aistudio.google.com/) dan buat API Key gratis.
2. **Perbarui file `.env` di folder `aeo-engine/`:**
   Tambahkan variabel berikut:
   ```env
   GEMINI_API_KEY="AIzaSy..."
   ```
   *(Atau Bapak juga bisa menyematkannya langsung di `.env` utama atau `.env.production` dengan nama `VITE_GEMINI_API_KEY`)*.
3. **Jalankan Pipeline:**
   ```bash
   cd aeo-engine
   npm start
   ```
4. **Perbarui Kata Kunci Tautan:**
   Bapak dapat mengedit daftar pemetaan kata kunci dan tautan tujuan kapan saja pada berkas:
   `aeo-engine/config/keywords_map.json`

---
*Seluruh kode di atas terisolasi di dalam modul `aeo-engine/` dan tidak mengubah kode dashboard staging maupun skema database utama sehingga 100% aman.*
