# 🏮 ROOT CAUSE ANALYSIS (RCA) & USE CASE: EROR SCHEMA LOGIN
**Kasus:** User Gagal Login dengan Eror `"Database error querying schema"` setelah Registrasi/Aktivasi Otomatis.

---

## 🚨 1. DESKRIPSI MASALAH
User yang mendaftar via Landing Page (menggunakan link Partner) atau setelah melakukan pembayaran (Midtrans), berhasil menerima email aktivasi dan password. Namun, saat mencoba login di halaman `/login`, sistem menolak dengan pesan eror merah: `"Database error querying schema"`.

---

## 🔍 2. AKAR MASALAH (ROOT CAUSE)
Berdasarkan investigasi mendalam pada file kodingan dan log database (Turn 101 & 102), ada 2 penyebab utama kenapa masalah ini sering terjadi di project kita:

### **Penyebab A: Ketidaksinkronan Tabel `auth.users` dan `auth.identities`**
*   **Mekanisme Supabase:** Saat user login, Supabase tidak hanya memeriksa tabel `auth.users`, tetapi juga memverifikasi tabel `auth.identities` untuk memastikan provider (email) tersebut valid dan terverifikasi (`email_verified: true`).
*   **Kesalahan Sistem Kita:** Fungsi otomatis seperti `rpc_activate_account` (versi lama) melakukan *bypass* dengan langsung memasukkan data ke `auth.users` menggunakan `INSERT INTO`, tetapi **LUPA** (atau tidak lengkap) memasukkan data pasangan identitasnya ke `auth.identities`.
*   **Dampak:** Akun tercipta, tetapi berstatus "cacat" di mata Supabase.

### **Penyebab B: Eror Trigger yang Menggantung (Crash di Tengah Jalan)**
*   **Mekanisme Database:** Kita memiliki trigger global `set_updated_at` yang otomatis berjalan setiap kali ada tabel yang di-update.
*   **Kesalahan Sistem Kita:** Trigger ini dipasang secara masal ke tabel `profiles`, `clients`, dan `partners`. Namun, salah satu tabel tersebut (misal `partners`) sempat tidak memiliki kolom `updated_at`.
*   **Dampak:** Saat fungsi otomatis berjalan dan mencoba meng-update status partner, trigger tersebut melempar eror: `record "new" has no field "updated_at"`. Eror ini membatalkan transaksi database di tengah jalan, membuat data user tersimpan setengah jadi (corrupted).

---

## 📈 3. USE CASE & PENANGANAN USER TERDAMPAK (SOP)
Jika di masa depan ada user yang sudah membayar tetapi terkena kasus ini, **DILARANG KERAS** menyuruh user daftar ulang atau menghapus akun mereka. Gunakan SOP berikut:

### **Langkah 1: Jalankan Script Auto-Repair (Tanpa Hapus Data)**
Jalankan query ini di SQL Editor untuk menyembuhkan akun yang tersangkut dengan cara melengkapi identitasnya yang hilang:

```sql
DO $$
DECLARE
    v_user_id UUID;
    v_email TEXT := 'email_user_yang_error@mailinator.com'; -- Ganti dengan email user
BEGIN
    -- 1. Ambil ID user
    SELECT id INTO v_user_id FROM auth.users WHERE email = v_email;
    
    IF v_user_id IS NOT NULL THEN
        -- 2. Paksa buat identitas jika belum ada
        IF NOT EXISTS (SELECT 1 FROM auth.identities WHERE user_id = v_user_id) THEN
            INSERT INTO auth.identities (id, user_id, identity_data, provider, provider_id, last_sign_in_at, created_at, updated_at)
            VALUES (gen_random_uuid(), v_user_id, jsonb_build_object('sub', v_user_id, 'email', v_email, 'email_verified', true), 'email', v_email, NOW(), NOW(), NOW());
        END IF;
        
        -- 3. Pastikan profile aktif
        UPDATE public.profiles SET subscription_plan = 'ultimate' WHERE id = v_user_id;
    END IF;
END $$;
```

### **Langkah 2: Verifikasi Login**
Minta user untuk mencoba login kembali. Akun dipastikan akan langsung aktif tanpa kehilangan data transaksi.

---

## 🛡️ 4. PENCEGAHAN AGAR TIDAK TERULANG
1.  **Idempotensi Fungsi:** Setiap kali membuat fungsi aktivasi database (RPC), selalu gunakan logika `IF NOT EXISTS` saat melakukan insert data auth.
2.  **Audit Kolom Trigger:** Jika menambahkan trigger `set_updated_at` ke tabel baru, pastikan tabel tersebut SUDAH memiliki kolom `updated_at`.
