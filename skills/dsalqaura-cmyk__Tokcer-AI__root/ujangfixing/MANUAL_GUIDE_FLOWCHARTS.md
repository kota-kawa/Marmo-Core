# 📊 Manual Guide & Flowchart Dashboard Tokcer AI

Dokumen ini berisi panduan alur kerja (flowchart) untuk **Dashboard User** dan **Dashboard Partner** di Tokcer AI. Dokumen ini dibuat untuk membantu tim dalam menyusun manual detail (Buku Panduan) untuk pengguna.

---

## 👤 1. Alur Dashboard User (Klien)

Dashboard User digunakan oleh para penjual online (online sellers) untuk mengelola toko, menghitung HPP, dan membuat konten AI.

### 📍 Flowchart Alur Registrasi & Aktivasi User
```mermaid
graph TD
    A[Landing Page] -->|Klik Daftar| B(Form Pendaftaran)
    B -->|Isi Data & Pilih Paket| C{Pilih Pembayaran}
    C -->|Midtrans / Otomatis| D[Bayar via Snap]
    C -->|Transfer Manual| E[Upload Bukti Transfer]
    D -->|Sukses| F[Auto-Approve / Active]
    E -->|Dicek Admin| G{Disetujui?}
    G -->|Ya| F
    G -->|Tidak| H[Ditolak]
    F -->|Kirim Email| I[User Terima Password]
    I -->|Login| J[Dashboard User]
    
    subgraph Fitur Dashboard User
    J --> K[Integrasi Toko]
    J --> L[HPP Calculator]
    J --> M[AI Content Generator]
    J --> N[Sistem Kredit/Koin]
    end
```

### 📝 Penjelasan Alur User:
1.  **Pendaftaran**: User mendaftar di landing page, mengisi data diri, memilih paket (Pro/Elite/Ultimate), dan memilih platform jualan.
2.  **Validasi Bisnis**: User **wajib** mencentang bahwa akun marketplace mereka sudah terverifikasi bisnis agar tombol bayar menyala.
3.  **Pembayaran**: Jika sukses bayar via Midtrans, akun langsung aktif. Jika manual, menunggu approval admin.
4.  **Akses**: User menerima email berisi password default untuk login ke Dashboard User.

---

## 🤝 2. Alur Dashboard Partner (Affiliator)

Dashboard Partner digunakan oleh para affiliator untuk menyebarkan link referral, mendaftarkan klien secara manual, dan memantau komisi.

### 📍 Flowchart Alur Registrasi Partner
```mermaid
graph TD
    A[Landing Page] -->|Klik Daftar Partner| B(Form Pendaftaran Partner)
    B -->|Kirim Data| C[Robot Kirim Email Link PKS]
    C -->|Klik Link| D[Halaman Tanda Tangan PKS]
    D -->|Klik Saya Setuju| E[Layar Sukses + Kode Referral]
    E -->|Menunggu| F[Approval Admin di Internal]
    F -->|Disetujui| G[Robot Kirim Email Password]
    G -->|Login| H[Dashboard Partner]
```

### 📍 Flowchart Bisnis Partner (Diambil dari docs)
```mermaid
graph TD
    A[Partner Login] --> B{Punya Klien Baru?}
    B -- Ya --> C[Menu Onboard: Isi Data & Upload Bukti Bayar]
    C --> D[Status Klien: Pending]
    D --> E[Internal Admin Verifikasi Pembayaran]
    E -- Disetujui --> F[Status Klien: Active]
    F --> G[Komisi Cair & Muncul di Menu Payment]
    G --> H[Update MTD Pace & Leaderboard]
    B -- Tidak --> I[Pantau Dashboard & Leaderboard]
```

### 📍 Flowchart Menu Onboard (Registrasi Klien oleh Partner)
```mermaid
sequenceDiagram
    Partner->>Form: Isi Nama Toko, Email, WhatsApp
    Partner->>Form: Pilih Paket & Upload Bukti Transfer
    Form->>Supabase Storage: Upload Gambar
    Supabase Storage-->>Form: Berikan URL Gambar
    Form->>Supabase DB: Simpan Data Klien (Status: Pending)
    Supabase DB-->>Partner: Alert: "Data Berhasil Dikirim"
```

---

## 🛠️ Catatan untuk Pembuatan Manual Detail:
*   Pastikan mencantumkan bahwa **Sandi Default** untuk Partner baru adalah `Tokcer@2026`.
*   Ingatkan seller/partner bahwa **Verifikasi Bisnis** di marketplace adalah syarat mutlak agar fitur otomatisasi Tokcer AI berjalan lancar.

---
*Dibuat oleh Ujang untuk kemudahan tim Tokcer AI.* 🫡🛡️🏮🔥
