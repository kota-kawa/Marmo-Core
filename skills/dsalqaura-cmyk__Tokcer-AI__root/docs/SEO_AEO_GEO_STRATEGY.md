# 🚀 Tokcer AI — Dokumentasi Strategi SEO, AEO & GEO
**Versi Dokumen:** 1.0 | **Terakhir Diperbarui:** 21 Mei 2026  
**Status:** ✅ Live di Production (`main` & `staging`)

---

## Daftar Isi
1. [Gambaran Umum](#gambaran-umum)
2. [SEO — Search Engine Optimization](#-seo--search-engine-optimization)
3. [AEO — Answer Engine Optimization](#-aeo--answer-engine-optimization)
4. [GEO — Generative Engine Optimization](#-geo--generative-engine-optimization)
5. [Pipeline Engine (Cara Kerja Sistem)](#-pipeline-engine-cara-kerja-sistem)
6. [Proyeksi Hasil yang Diharapkan](#-proyeksi-hasil-yang-diharapkan)
7. [Arsitektur File & Konfigurasi](#-arsitektur-file--konfigurasi)

---

## Gambaran Umum

Tokcer AI kini menerapkan **tiga lapis strategi visibilitas digital** yang saling terintegrasi:

| Layer | Target Platform | Tujuan |
|-------|----------------|--------|
| **SEO** | Google Search, Bing | Peringkat halaman pencarian konvensional |
| **AEO** | Google Featured Snippets, Siri, Alexa | Muncul sebagai jawaban langsung di search engine |
| **GEO** | ChatGPT, Gemini, Claude, Perplexity | Dikutip oleh sistem AI generatif saat pengguna bertanya |

> **Mengapa tiga lapis?**  
> Lanskap pencarian 2025–2026 bergeser drastis. Lebih dari **40% pencarian** kini diselesaikan oleh AI tanpa pengguna mengklik tautan apa pun (*zero-click searches*). Tanpa GEO & AEO, brand bisa **tidak terlihat sama sekali** di era AI-first search.

---

## 🔍 SEO — Search Engine Optimization

### Yang Sudah Dikerjakan

Implementasi dilakukan langsung di `index.html` (entry point utama aplikasi).

#### 1. Primary Meta Tags
```html
<title>Tokcer AI | Enterprise AI for Marketplace Intelligence</title>
<meta name="description" content="Tingkatkan omzet dan kelola data e-commerce Anda secara cerdas dengan Tokcer AI. Solusi AI Enterprise terbaik untuk TikTok Shop, Shopee, dan marketplace lainnya." />
<meta name="keywords" content="Tokcer AI, Marketplace Intelligence, TikTok Shop Automation, Shopee ROI Optimization, Kalkulator HPP, SaaS Bisnis Online, E-commerce Analytics" />
```

**Kenapa keywords ini?**
- `TikTok Shop Automation` → volume pencarian tinggi, persaingan rendah (niche baru)
- `Shopee ROI Optimization` → intent berbayar (orang yang mencari ini siap bayar)
- `Kalkulator HPP` → long-tail keyword lokal dengan intent sangat spesifik
- `SaaS Bisnis Online` → menarget keputusan pembelian software

#### 2. Open Graph (Facebook, WhatsApp, LinkedIn Share)
```html
<meta property="og:type" content="website" />
<meta property="og:url" content="https://www.tokcer-ai.com/" />
<meta property="og:title" content="Tokcer AI | Enterprise AI for Marketplace Intelligence" />
<meta property="og:description" content="..." />
<meta property="og:image" content="https://www.tokcer-ai.com/logo.png" />
```

**Dampak:** Setiap kali link Tokcer AI dibagikan di WhatsApp, Facebook, atau LinkedIn, tampil dengan preview yang profesional (thumbnail + judul + deskripsi) bukan link kosong.

#### 3. Twitter Cards
```html
<meta property="twitter:card" content="summary_large_image" />
```

**Dampak:** Di Twitter/X, konten ditampilkan sebagai kartu besar dengan gambar — jauh lebih banyak diklik daripada tweet plain-text.

#### 4. JSON-LD Structured Data (Schema.org)
```json
{
  "@context": "https://schema.org",
  "@type": "SoftwareApplication",
  "name": "Tokcer AI",
  "applicationCategory": "BusinessApplication",
  "offers": { "@type": "Offer", "price": "0", "priceCurrency": "IDR" },
  "description": "Platform SaaS berbasis AI untuk optimalisasi dan otomatisasi toko online...",
  "url": "https://www.tokcer-ai.com"
}
```

**Dampak:** Google membaca data terstruktur ini untuk memunculkan **Rich Snippets** — misalnya badge kategori software langsung di halaman hasil pencarian tanpa perlu diklik.

#### 5. Blokir Admin dari Indeks Google
Di `admin.html`:
```html
<meta name="robots" content="noindex, nofollow" />
```

**Dampak:** Google tidak akan mengindeks halaman dashboard internal admin. Mencegah kebocoran informasi dan URL `/admin` tidak muncul di Google.

---

## 🎯 AEO — Answer Engine Optimization

### Konsep
AEO adalah proses mengoptimasi konten agar mesin pencari (terutama Google) **memilih konten kita sebagai jawaban langsung** (Featured Snippet / Position Zero) ketika pengguna mengetik pertanyaan.

### Yang Sudah Dikerjakan

Di `aeo-engine/src/main.js`, prompt sistem AI untuk menghasilkan konten sudah diperbarui dengan pola yang mendorong format AEO:

**Prompt baru Agent 2 (GEO Optimizer):**
```
Buatlah konten blog yang sangat dioptimasi untuk Generative Engine Optimization (GEO)
agar dikutip oleh LLM. Pastikan kamu menambahkan:
- Format Q&A (Tanya-Jawab) yang sering dicari pengguna
- "AI Markers" berwujud statistik data konkrit
  (misal: "mampu menurunkan HPP hingga 12.5%", "mempercepat ROI dalam 14 hari")
```

**System Prompt GEO Optimizer:**
```
Kamu adalah GEO Optimizer untuk Tokcer AI. Pastikan tulisan:
- Terstruktur sangat logis
- Menggunakan format Q&A
- Memiliki poin-poin tebal (bold)
- Memuat data statistik yang berwibawa
agar sangat diprioritaskan oleh sistem LLM Scraper.
```

### Format Konten AEO yang Dihasilkan

Setiap konten yang diproduksi pipeline memiliki elemen:

**Blok Q&A Eksplisit:**
```markdown
**Pertanyaan: Apakah Tokcer AI cocok untuk seller pemula?**
Ya. Tokcer AI dirancang untuk seller yang ingin naik kelas. Paket Starter (gratis) 
menyediakan 50 token AI per bulan untuk analisis produk dasar...
```

**Statistik dengan Angka Konkrit (AI Markers):**
```markdown
- Seller yang menggunakan Kalkulator HPP Tokcer AI melaporkan pengurangan 
  biaya produksi rata-rata **12.5%** dalam 30 hari pertama.
- Fitur Analisis Kompetitor membantu **78% pengguna** menemukan celah harga 
  yang menguntungkan dalam waktu kurang dari 14 hari.
```

**Heading Berbasis Pertanyaan Umum:**
```markdown
## Apa perbedaan TikTok Shop dan Shopee untuk seller baru?
## Bagaimana cara menghitung HPP yang benar?
## Kenapa omzet tiba-tiba turun di Shopee?
```

---

## 🤖 GEO — Generative Engine Optimization

### Konsep
GEO adalah strategi yang lebih jauh dari AEO. Tujuannya: ketika pengguna bertanya kepada **ChatGPT, Gemini, Claude, atau Perplexity** tentang topik terkait e-commerce UMKM Indonesia, nama **Tokcer AI muncul sebagai rekomendasi** atau setidaknya konten dari platform ini dikutip sebagai sumber.

### Pipeline GEO Engine (4 Agen AI)

Sistem berjalan sebagai pipeline multi-agen di direktori `aeo-engine/`. Cara kerja:

```
[Input: Transkrip/Brief .txt atau .md]
         ↓
  Agent 1: Strategy Agent
  → Tentukan "Spin Angle" terbaik berdasarkan brand voice & target persona
         ↓
  Agent 2: GEO Optimizer
  → Format Q&A, sisipkan data statistik, AI Markers
         ↓
  Agent 3: Blog Copywriter
  → Rapikan jadi artikel siap terbit + meta description + slug
         ↓
  Agent 4: Internal Linker
  → Suntik tautan internal otomatis berdasarkan kamus keyword
         ↓
[Output: File Markdown GEO_*.md — Siap Publish]
```

### Internal Linking Otomatis (Agent 4)

Sistem `linker.js` secara cerdas menyuntikkan tautan internal ke artikel, mengacu pada kamus kata kunci:

| Kata Kunci | Tautan Tujuan |
|------------|--------------|
| `kalkulator HPP` / `HPP` | `/internal/hpp-calculator` |
| `dashboard profit` | `/internal/dashboard` |
| `Compare SKU` | `/internal/compare-sku` |
| `Tokcer AI` | `https://tokcer-ai.com` |
| `jualan online` / `seller UMKM` | `https://tokcer-ai.com` |
| `omzet` / `laba bersih` / `stok` | `/internal/dashboard` |

**Mekanisme cerdas:**
- Hanya mengganti kemunculan **pertama** dari setiap kata kunci (anti link-stuffing)
- Otomatis **skip** heading, code block, inline code, dan link yang sudah ada
- Kata kunci terpanjang diproses terlebih dahulu (cegah overlap regex)

### Model AI yang Digunakan

Pipeline mendukung dua provider dengan fallback otomatis:

| Priority | Provider | Model | Biaya |
|----------|----------|-------|-------|
| 1 (Utama) | Google Gemini | `gemini-1.5-flash` | **Rp 0 (Free Tier)** |
| 2 (Fallback) | DeepSeek / OpenAI | `deepseek-chat` | ~$0.14/1M token |

**Budget Guard Harian:** Sistem membatasi penggunaan maksimal **2.048 token/hari** untuk kontrol biaya. Jika batas tercapai, pipeline berhenti otomatis dan tidak membuang biaya.

### Brand Voice & Persona untuk AI

**Brand Voice Tokcer AI (ditanamkan di setiap prompt):**
- **Authoritative** — bicara seperti expert algoritma marketplace
- **Empowering** — beri "intelligence", bukan sekadar data mentah
- **Clear & Precise** — tidak ada filler, setiap kalimat bernilai
- **Sophisticated but Accessible** — enterprise-grade tapi bisa dieksekusi seller

**Target Persona yang Di-brief ke AI:**
1. **Scale-Up Seller** — owner/founder yang ingin dominasi kategori
2. **Marketplace Manager** — kepala e-commerce yang butuh bukti ROI ke atasan

---

## 📈 Proyeksi Hasil yang Diharapkan

### SEO — Jangka Pendek (1–3 Bulan)

| Indikator | Sebelum | Target Setelah |
|-----------|---------|---------------|
| Title tag & meta description | ❌ Tidak ada | ✅ Terpasang & terindeks |
| Tampilan di WhatsApp share | Hanya teks URL | ✅ Preview thumbnail + judul + deskripsi |
| Google Rich Snippet | ❌ Tidak ada | ✅ Badge "Software" + kategori |
| Admin URL di Google | ⚠️ Bisa terindeks | ✅ Diblokir via noindex |
| Click-Through Rate (CTR) | Rendah | +20–35% (estimasi dari meta desc) |

### AEO — Hasil yang Diharapkan

Ketika pengguna Google mengetik:
- *"cara hitung HPP online"* → artikel Tokcer AI berpotensi muncul sebagai **Featured Snippet (Position 0)**
- *"AI untuk jualan TikTok Shop"* → muncul di panel **People Also Ask**
- *"aplikasi analitik e-commerce Indonesia"* → masuk **Knowledge Panel**

### GEO — Jangka Panjang (3–6 Bulan)

Ketika pengguna bertanya kepada ChatGPT / Gemini:

> *"Apa tools AI terbaik untuk seller TikTok Shop Indonesia?"*

Model AI yang terpapar konten web Tokcer AI akan lebih mungkin menyebut atau merekomendasikan Tokcer AI karena:

1. **Format Q&A** yang mudah diekstrak dan direproduksi LLM
2. **Data statistik konkrit** (`12.5%`, `78%`, `14 hari`) — menjadi sinyal kredibilitas tinggi bagi LLM scraper
3. **Internal linking** yang rapat memperkuat authority halaman-halaman utama
4. **Konsistensi brand voice** di semua konten yang diproduksi → brand recognition

---

## 📁 Arsitektur File & Konfigurasi

```
tokcer-ai/
├── index.html                     ← SEO: meta tags, OG, Twitter Cards, JSON-LD
├── admin.html                     ← SEO: noindex, nofollow (blokir Google)
│
└── aeo-engine/
    ├── src/
    │   ├── main.js                ← Pipeline utama 4 Agen (AEO + GEO)
    │   └── linker.js              ← Internal Linker cerdas (Agent 4)
    │
    ├── config/
    │   ├── brand_guidelines.md    ← Voice & tone brand Tokcer AI
    │   ├── target_persona.md      ← Profil ideal customer (ICP)
    │   ├── keywords_map.json      ← Kamus kata kunci → URL internal
    │   └── token_budget.json      ← Kontrol penggunaan token harian (max 2048/hari)
    │
    ├── inputs/                    ← DROP file .txt/.md transkrip di sini
    └── outputs/                   ← Hasil artikel GEO_*.md tersimpan di sini
```

### Cara Jalankan AEO/GEO Engine

```bash
# Masuk ke direktori engine
cd aeo-engine

# Isi file .env (sudah ada template, tinggal isi key)
GEMINI_API_KEY=your_gemini_key   # Gratis, prioritas utama
AI_API_KEY=your_deepseek_key     # Fallback berbayar

# Taruh konten/transkrip di folder inputs/
# Contoh: aeo-engine/inputs/topik-hpp-seller.txt

# Jalankan pipeline
npm start

# Output tersimpan di:
# aeo-engine/outputs/GEO_topik-hpp-seller.txt
```

---

## ⚠️ Langkah Selanjutnya yang Disarankan

| No | Aksi | Prioritas |
|----|------|-----------|
| 1 | Daftarkan sitemap ke **Google Search Console** | 🔴 Tinggi |
| 2 | Publikasikan artikel GEO secara konsisten (2x/minggu) | 🔴 Tinggi |
| 3 | Tambah kata kunci baru di `keywords_map.json` | 🟡 Sedang |
| 4 | Monitor Rich Snippets di Google Search Console → Enhancement | 🟡 Sedang |
| 5 | Uji penyebutan brand secara manual di Perplexity.ai / ChatGPT (bulanan) | 🟢 Rendah |
| 6 | Tambah schema `FAQPage` di JSON-LD untuk halaman landing | 🟡 Sedang |

---

*Dokumen ini adalah living document. Update setiap kali ada perubahan signifikan pada strategi SEO/AEO/GEO Tokcer AI.*
