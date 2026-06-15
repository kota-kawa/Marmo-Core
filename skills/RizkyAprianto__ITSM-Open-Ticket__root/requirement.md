# ITSM Open Ticket - Requirements Document

## 1. Project Overview
Sistem manajemen tiket IT Support untuk lingkungan kampus (ITSM) yang modern dan efisien, menggunakan Laravel 13 sebagai core framework dan Supabase sebagai backend layanan (DB, Auth, Storage).

## 2. Core Constraints (PENTING)
- **Framework**: Laravel 13 (Latest).
- **Frontend Stack**: Livewire 3 + Tailwind CSS + Alpine.js.
- **Backend Service**: FULL SUPABASE (PostgreSQL, Auth, Storage, Real-time).
- **UI/UX Policy**: NO FILAMENT. Desain harus kustom, premium, modern, dan "Wow".
- **Local Env**: Laragon.
- **Language**: Bahasa Indonesia.

## 3. User Roles & Access
| Role | Auth Type | Capabilities |
| :--- | :--- | :--- |
| **Mahasiswa** | NO LOGIN | Submit tiket via homepage (/), input NIM, Nama, No HP. |
| **Admin** | Supabase Auth | Full Access: Manage Users, Categories, Settings, Reports. |
| **Staff IT** | Supabase Auth | Manage Tickets: Update status, Add comments, WhatsApp student. |
| **Dosen** | Supabase Auth | Submit tickets, View own ticket history. |
| **Rektor/Dekan** | Supabase Auth | View-Only: Executive Dashboard (Charts & Analysts). |

## 4. Key Features
### A. Public Ticket Submission (Mahasiswa)
- Halaman depan (/) wajib bersih dan minimalis.
- Input: NIM, Nama, No HP (Otomatis format link WhatsApp), Kategori, dan Deskripsi Kendala.
- Notifikasi: Email setelah submit sukses.

### B. WhatsApp Integration
- Di dashboard Staff, No HP mahasiswa harus muncul sebagai tombol interaktif `wa.me`.
- Mempermudah koordinasi cepat via WhatsApp.

### C. Executive Dashboard
- Visualisasi data menggunakan ApexCharts.
- Data real-time (tanpa refresh) menggunakan Supabase Real-time.

### D. Clean Code Implementation
- Service Layer Pattern.
- PHP Enums untuk Status & Priority.
- Form Requests untuk validasi.
