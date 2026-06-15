# Rekap Kerja Ujang - 09 Mei 2026

Berikut adalah daftar perbaikan dan fitur baru yang telah dikerjakan oleh Ujang pada sesi ini untuk menstabilkan Dashboard Partner dan Internal Tokcer AI.

## 1. Perbaikan Tampilan & Form Publik
*   **`src/components/landing/Hero.jsx`**
    *   *Perubahan:* Menghapus elemen dekoratif ikon TikTok melayang di bagian atas halaman depan.
*   **`src/components/modals/RegisterModal.jsx`**
    *   *Perubahan:* Mengubah teks "Tahunan (Save 15%)" menjadi "Tahunan" saja, serta membuat label harga paket dinamis menampilkan nominal Rupiah asli (Pro 499k, Elite 999k, Ultimate 1.999k) berdasarkan database.

## 2. Perbaikan Sistem Auth & Sesi
*   **`src/pages/PartnerDashboard.jsx`**
    *   *Perubahan:* Mengubah fungsi `navigate('/login')` saat logout menjadi `window.location.href = '/login'`. Ini memaksa browser reload total agar sesi lama beneran bersih dan tidak otomatis login kembali.
*   **`src/components/Navbar.jsx`**
    *   *Perubahan:* Menambahkan kondisi `window.location.pathname !== '/'` pada pengecekan user. Jika berada di landing page, tombol "Dashboard" dan angka statistik koin/toko akan disembunyikan agar tampilan depan steril.

## 3. Perbaikan Skema Komisi & Tier
*   **`src/components/partner/tabs/CommissionSchemeTab.jsx`**
    *   *Perubahan:* Menghapus baris Tier "Starter" (≥ 1 closing) pada tabel Kriteria Tier (A.2) karena tidak sesuai dengan skema asli (dimulai dari Bronze).

## 4. Perbaikan Eror Database & Fitur Baru Dashboard Internal
*   **`src/pages/PartnerDashboard.jsx`**
    *   *Perubahan:* Menghapus pengiriman field `metadata` pada fungsi `handleBugSubmit` karena kolom tersebut tidak ada di tabel `support_tickets`. Keterangan dipindahkan ke dalam `description`.
*   **`src/components/internal/sections/IdeasSection.jsx`** (*FILE BARU*)
    *   *Perubahan:* Membuat komponen baru untuk menampilkan saran fitur dari partner (tabel `partner_ideas`) lengkap dengan tombol "Tandai Direview" dan "Abaikan".
*   **`src/pages/InternalDashboard.jsx`**
    *   *Perubahan:* Menambahkan state `ideas`, fungsi `fetchIdeas`, dan memasukkan `IdeasSection` ke dalam switch-case menu.
*   **`src/components/internal/InternalSidebar.jsx`**
    *   *Perubahan:* Menambahkan menu baru "Saran Fitur" di bawah menu Tiket Bantuan, lengkap dengan lencana (badge) jumlah ide baru.

---

## 🛠️ Perintah SQL yang Harus Dijalankan di Supabase
Untuk membuka gembok izin akses tabel `partner_ideas` agar Partner bisa mengirimkan saran fitur:

```sql
ALTER TABLE public.partner_ideas ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "Partners can insert ideas" ON public.partner_ideas;
CREATE POLICY "Partners can insert ideas" ON public.partner_ideas FOR INSERT WITH CHECK (auth.uid() = partner_id OR partner_id IS NULL);
```

*Semua kodingan di atas telah sukses di-push ke branch `staging`.*
