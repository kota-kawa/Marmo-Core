# ITSM Open Ticket - Architecture Document

## 1. Technical Stack
- **Backend Framework**: Laravel 13 (PHP 8.3+).
- **Frontend Engine**: Livewire 3 (Reactive, dynamic components).
- **Styling**: Tailwind CSS (Custom modern designs, no pre-built admin kits).
- **Backend Service (Full Supabase)**:
    - **Database**: PostgreSQL (Supabase).
    - **Auth**: Supabase Auth (Integrate with Laravel Auth).
    - **Storage**: Supabase Storage (File upload bucket for ticket attachments).
    - **Real-time**: Supabase Broadcast/Presence (For status updates).

## 2. Core Principles (Clean Code)
- **Service Layer Pattern**: Semua logika bisnis (seperti `CreateTicket`, `AssignStaff`, `SolveProblem`) berada di folder `app/Services`.
- **Laravel Policy-Based Auth**: Akses kontrol role (Admin, Staff, Rektor, dll) menggunakan Laravel Policies secara ketat.
- **Repository-ish Pattern**: Penggunaan Eloquent Models untuk Querying secara terorganisir.
- **PHP Enums**: Menggunakan Enums untuk membatasi status tiket (Open, In Progress, Resolved) dan prioritas (Low, Medium, High).
- **Trait-Based Uploads**: Penggunaan Trait untuk file upload ke Supabase Storage supaya kodingan bersih.

## 3. Directory Structure (Proposed)
```text
app/
├── Enums/              # Enum classes (Status, Priority, Role)
├── Services/           # Business Logic classes
├── Livewire/           # UI Components (Public Form, Dashboard Widgets)
├── Policies/           # Auth Permissions rules
├── Traits/             # Shared functionality (Image uploads, WhatsApp formatting)
database/
├── migrations/         # Project schema definition
tests/                  # Unit and Feature tests
```

## 4. UI/UX Aesthetics
- Minimalis, premium, dan profesional.
- **Color Scheme**: Deep Blue (#0F172A), Emerald Green for resolution, Amber for urgency.
- **Charts**: Interactive ApexCharts untuk data visualisasi dashboard executive.
- **Typography**: Inter / Outfit (Modern Google Fonts).
