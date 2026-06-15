# ITSM Open Ticket - Skill/Instruction Guide (Development Rules)

## 1. Development Principles
- **Clean Code First**: Jangan koding sembarangan. Gunakan Service Layer dan Separation of Concerns.
- **Supabase-Native**: Maksimalkan fitur Supabase (PostgreSQL, Real-time, Storage).
- **Premium UI (No Filament)**: Desain harus visual-centric, premium, dan detail. Gunakan Tailwind CSS v4 (Latest) untuk styling.
- **WhatsApp-Centric**: Integrasi `wa.me` harus mulus di dashboard staff.
- **Laravel 13 Style**: Manfaatkan fitur terbaru Laravel 13 seperti PHP Attributes, AI SDK (jika diperlukan), dan Vector Search (jika ada fitur pencarian pintar).

## 2. Forbidden Actions (PANTANGAN!)
- **NO FILAMENT**: Jangan pernah mencoba menggunakan Filament atau admin panel pre-built lainnya.
- **NO COMPLEX JS**: Gunakan Livewire 3 + Alpine.js untuk interaktivitas. Jangan pakai React/Vue kecuali diminta khusus.
- **NO LOCAL DATABASE**: Gunakan Supabase untuk semua environment (Dev, Staging, Prod).
- **NO PLACEHOLDERS**: Gunakan aset visual asli atau hasil generator, jangan pakai gambar placeholder dummy.

## 3. Workflow for Antigravity (Me)
1. **Analyze Design**: Selalu bayangkan desain premium sebelum menulis kode.
2. **Setup Supabase**: Pastikan koneksi DB stabil dan schema sesuai `database.md`.
3. **Role-Based Auth**: Implementasikan Laravel Policies di awal fitur agar aman.
4. **WhatsApp Linker**: Buat helper khusus untuk format `wa.me` internasional (otomatis ganti 0 jadi 62).
5. **Mahasiswa-First**: Dahulukan form pengaduan mahasiswa di halaman depan (`/`).

## 4. Specific Role Logic
- **Admin**: Bisa melihat semua data.
- **Staff**: Cuma bisa lihat tiket yang di-assign ke dia (pakai RLS Supabase & Laravel Policy).
- **Rektor/Dekan**: Dashboard dashboard-only (Visual analytics).
- **Mahasiswa**: Guest access, submit-only.
