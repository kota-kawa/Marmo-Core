# ITSM Open Ticket - Implementation Strategy

## 1. Initial Setup
1.  **Framework**: Initialize Laravel 13 (`composer create-project laravel/laravel .`).
2.  **Auth Layer**: Install Laravel Breeze (Livewire).
3.  **Supabase Connection**:
    -   Update `.env` with Supabase host, port, db, user, password.
    -   Test connection with `php artisan db:monitor`.

## 2. Core Development Phases
### Phase 1: Public Interface (Mahasiswa)
-   Create a clean Home page (`/`).
-   Build the Livewire Form: `IssueSubmission` (Fields: NIM, Nama, No HP, Kategori, Deskripsi).
-   Save to `tickets` table (nullable `user_id`).
-   Generate Ticket ID & Link WA for staff.

### Phase 2: Role Management & Middleware
-   Setup Roles table/Enum.
-   Create Laravel Middleware to restrict access based on roles.
-   Integrate Supabase Auth for login-required roles.

### Phase 3: Staff & Admin Dashboard (Custom UI)
-   Build the sidebar layout with Tailwind.
-   Create Ticket Management Table with search/filter (no reload).
-   Add "WhatsApp Contact" button to student phone numbers.

### Phase 4: Executive Insights (Rektor/Dekan)
-   Build `ExecutiveDashboard` Livewire component.
-   Integrate ApexCharts for "Issues by Category" and "Resolution Speed".
-   Use Supabase Real-time to auto-update charts.

## 3. Deployment & Testing
-   **Local**: Laragon.
-   **DB**: Supabase (Production-ready).
-   **Verification**: Test submission flow, staff response flow, and admin reporting.
