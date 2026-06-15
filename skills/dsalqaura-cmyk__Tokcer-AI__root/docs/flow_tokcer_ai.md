# 📊 Flowchart & Business Flow - Tokcer AI

## 1. Alur Pendaftaran & Approval (User Flow)
Berikut adalah perjalanan seorang Seller mulai dari mendaftar hingga akun aktif.

```mermaid
graph TD
    A[Pengunjung Website] --> B{Klik Register?}
    B -- Ya --> C[Isi Form & Pilih Paket]
    C --> D[Simpan ke Tabel Clients 'Pending']
    D --> E[Admin Cek Approval Center]
    E -- Verifikasi Pembayaran --> F{Approve?}
    F -- Ya --> G[Trigger rpc_activate_account]
    G --> H[Kirim Welcome Email via Resend]
    H --> I[User Login ke Dashboard User]
    F -- Tidak --> J[Status Rejected]
```

---

## 2. Alur Kerja Partner (Partner Flow)
Bagaimana seorang Partner membawa klien masuk.

```mermaid
graph LR
    P[Partner Login] --> Q[Menu Onboarding]
    Q --> R[Daftarkan Data Seller]
    R --> S[Upload Bukti Bayar]
    S --> T[Admin Review]
    T --> U[User Aktif]
    U --> V[Komisi Masuk ke Saldo Partner]
    V --> W[Leaderboard Update]
```

---

## 3. Siklus Bisnis (Business Lifecycle)
Tahapan pertumbuhan ekosistem Tokcer AI:

1.  **Acquisition (Akuisisi)**:
    *   Visitor datang melalui iklan atau referral Partner.
    *   Pendaftaran via Landing Page atau Partner Dashboard.
2.  **Validation (Validasi)**:
    *   Admin memverifikasi bukti transfer dan jenis bisnis.
    *   Sistem otomatis menyiapkan kredensial akses.
3.  **Activation (Aktivasi)**:
    *   User menerima email akses.
    *   User mengoneksikan toko marketplace mereka.
4.  **Usage (Penggunaan)**:
    *   User menggunakan AI Generator untuk membuat konten harian.
    *   User memantau grafik analitik untuk strategi jualan.
5.  **Retention & Growth (Retensi & Pertumbuhan)**:
    *   Partner mendapatkan komisi berulang (recurring) jika user upgrade.
    *   Partner bersaing di Leaderboard untuk mendapatkan bonus tambahan.

---

## 4. Alur Integrasi AI (AI Generation Flow)
Bagaimana AI memberikan jawaban yang cerdas.

```mermaid
sequenceDiagram
    User->>Frontend: Input Topik Produk
    Frontend->>Supabase: Ambil AI Config & Knowledge Base
    Supabase-->>Frontend: Kirim System Prompt & RAG Data
    Frontend->>DeepSeek API: Kirim Full Context (Prompt + Data)
    DeepSeek API-->>Frontend: Kirim Respon Kreatif
    Frontend->>User: Tampilkan Naskah/Deskripsi
    Frontend->>Supabase: Catat Penggunaan Token (Logs)
```

---
**Dibuat Oleh**: Antigravity AI (Siti)
**Tanggal**: 30 April 2026
