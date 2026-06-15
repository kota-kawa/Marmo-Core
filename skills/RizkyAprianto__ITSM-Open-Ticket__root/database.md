# ITSM Open Ticket - Database Schema (Supabase)

## 1. Engine
- **Database**: PostgreSQL (Supabase).
- **Driver**: `pgsql`.
- **Search Path**: `public`, `auth`.

## 2. Table Definitions
### A. `users` (Standard Laravel + Supabase Integration)
- `id`: UUID (Primary Key).
- `name`: String.
- `email`: String (Unique).
- `role`: Enum (admin, staff, rektor, dekan, dosen).
- `password`: String (Hashed).

### B. `categories`
- `id`: BigInt (Primary Key).
- `name`: String (Network, Hardware, Software, E-Learning).
- `slug`: String.
- `description`: Text.

### C. `tickets`
- `id`: BigInt (Primary Key, Auto increment).
- `uuid`: UUID (Unique, for external tracking).
- `user_id`: UUID (Nullable: Required for Dosen/Staff/Admin, NULL for Mahasiswa).
- `category_id`: BigInt (Foreign Key).
- `guest_name`: String (For Mahasiswa).
- `guest_nim`: String (For Mahasiswa).
- `guest_phone`: String (For WhatsApp).
- `title`: String.
- `description`: Text.
- `status`: Enum (open, in_progress, resolved, closed).
- `priority`: Enum (low, medium, high).
- `assigned_to`: UUID (Foreign Key, User ID of Staff).
- `solved_at`: Timestamp.

### D. `ticket_replies`
- `id`: BigInt.
- `ticket_id`: BigInt (Foreign Key).
- `user_id`: UUID (If staff or logged-in user).
- `message`: Text.
- `attachment_url`: String (Supabase Storage link).
- `is_internal`: Boolean (Internal notes for staff).

## 3. Relationships
- **Ticket** belongsTo **User** (Requester).
- **Ticket** belongsTo **Category**.
- **Ticket** belongsTo **Staff** (Assigned Technician).
- **Ticket** hasMany **Replies**.
- **Reply** belongsTo **User**.

## 4. Supabase Specifics
- **Row-Level Security (RLS)**: Diaktifkan untuk membatasi akses Staff hanya ke tiket yang di-assign ke mereka (kecuali Admin).
- **Real-time Engine**: Diaktifkan di tabel `tickets` untuk push notification ke dashboard Admin/Staff.
