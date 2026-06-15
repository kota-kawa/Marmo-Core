# PROJECT MANAGEMENT REPORT
## ITSM Open Ticket - Campus IT Service Center

---

### 1. GENERAL PROJECT INFORMATION

| FIELD | DESCRIPTION |
| :--- | :--- |
| **PROJECT NAME** | ITSM Open Ticket - Campus IT Service Center |
| **PROJECT CHAMPION** | Kepala Biro Sistem Informasi (BSI) / Head of IT |
| **PROJECT SPONSOR** | Rektorat & Bidang Administrasi Umum |
| **PROJECT MANAGER** | IT Development Team |
| **STAKEHOLDERS** | Mahasiswa, Dosen, Staff IT, Dekan, Rektor |
| **EXPECTED START DATE** | 2026-04-03 |
| **EXPECTED COMPLETION DATE** | 2026-05-03 |

---

### 2. PROJECT DETAILS

#### EXECUTIVE SUMMARY
Proyek ini bertujuan untuk membangun sistem manajemen tiket IT yang modern dan transparan di lingkungan kampus. Menggunakan teknologi terbaru (Laravel 13 & Supabase), sistem ini akan memangkas birokrasi pengaduan mahasiswa dengan fitur *No-Login Submission* dan mempercepat koordinasi teknisi melalui integrasi WhatsApp. Dashboard analitik disediakan khusus bagi pimpinan untuk memantau performa layanan IT secara *real-time*.

#### AUTHORIZATION
Proyek ini diotorisasi untuk pengembangan menggunakan infrastruktur Cloud Supabase dan Laravel Framework, dengan wewenang penuh pada Tim IT untuk mengelola skema database dan keamanan data pengguna.

#### OBJECTIVES (SMART)
- **Specific**: Membangun aplikasi ITSM dengan 5 role akses (Admin, Staff, Mahasiswa, Dosen, Rektor).
- **Measurable**: Menargetkan 100% pengaduan IT tercatat secara digital (tidak ada lagi via chat personal yang tidak terdata).
- **Achievable**: Implementasi menggunakan Livewire 3 untuk mempercepat pembuatan UI yang responsif.
- **Relevant**: Meningkatkan indeks kepuasan layanan fasilitas kampus bagi mahasiswa.
- **Time-bound**: Proyek diselesaikan dalam jangka waktu 4 minggu (1 bulan).

#### EXPECTED BENEFITS
- **Efisiensi**: Staff IT dapat merespon masalah lebih cepat melalui tombol WhatsApp otomatis.
- **Transparansi**: Mahasiswa dapat memantau status kendala mereka tanpa harus datang ke kantor IT.
- **Decision Making**: Rektorat mendapatkan data akurat mengenai kendala tersering di kampus (misal: sering terjadi masalah WiFi di Lab A).

---

### 3. PROJECT DETAILS (CONT'D)

#### SCOPE
- **INCLUDED**:
    - Form pengaduan publik untuk mahasiswa (NIM, Nama, No HP, Deskripsi).
    - Dashboard operasional Staff IT dengan tombol WhatsApp (`wa.me`).
    - Executive Dashboard dengan grafik analitik (ApexCharts).
    - Integrasi Cloud Storage Supabase untuk lampiran foto kendala.
- **EXCLUDED**:
    - Sistem pembelian perangkat keras (E-Procurement).
    - Manajemen inventaris stok fisik gudang.

#### MILESTONES
- **M1 (Week 1)**: Inisialisasi Laravel 13, Setup Supabase, & Arsitektur Database.
- **M2 (Week 2)**: Pengembangan Form Mahasiswa & Sistem Notifikasi Email.
- **M3 (Week 3)**: Pembuatan Dashboard Staff IT & Integrasi WhatsApp Link.
- **M4 (Week 4)**: Finalisasi Dashboard Rektorat, Security Testing, & Deployment.

#### SUCCESS METRICS
- **Resolution Rate**: Minimal 90% tiket terselesaikan dalam waktu kurang dari 48 jam.
- **User Adoption**: Minimal 500 tiket masuk secara organik dalam bulan pertama.
- **System Uptime**: 99.9% availabilitas pada form pengaduan mahasiswa.

#### ESTIMATED COSTS & RESOURCES (Rencana Anggaran Biaya)

**A. Infrastruktur Cloud (Biaya Bulanan)**
| Komponen | Provider | Tier | Estimasi (USD) | Tujuan |
| :--- | :--- | :--- | :--- | :--- |
| **Application Hosting** | Vercel | Pro Plan | $20.00 | Deployment Laravel (Serverless Runtime). |
| **Database & Real-time** | Supabase | Pro Plan | $25.00 | PostgreSQL, Auth, Real-time, & 100GB Storage. |
| **Domain Name** | Registrar | .ac.id | $1.25 | Identitas institusi (~Rp 175rb/tahun). |
| **Total Bulanan** | | | **$46.25** | **Sekitar Rp 730.000,- / bulan** |

**B. Sumber Daya Manusia (Estimasi Project-Based)**
- **1 Fullstack Developer**: Rp 15.000.000,- 
- **1 System Analyst / QA**: Rp 5.000.000,-

**C. Perangkat Lunak & Tools**
- **Laravel 11/12/13**: $0 (Open Source).
- **Tailwind CSS v4**: $0 (Open Source).
- **GitHub Actions**: $0 (Free for Public/Limited Private).
