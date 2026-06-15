# Dokumentasi Flow: Dashboard Partner - Login sampai Ganti Password

Dokumentasi ini menjelaskan alur proses yang dilalui oleh Partner mulai dari masuk ke sistem (Login) hingga melakukan perubahan kata sandi (Ganti Password) di dalam dashboard mereka.

## 1. Diagram Alur (Flowchart)

```text
       ┌───────────────────────────────────────────┐
       │        Mulai: Halaman Login Partner       │
       └─────────────────────┬─────────────────────┘
                             │
                             ▼
       ┌───────────────────────────────────────────┐
       │       Input Email & Password Partner      │
       └─────────────────────┬─────────────────────┘
                             │
                             ▼
                            / \
                          /     \
                        / Valid? \
                        \        /
                          \    /
                            \/
                             │
               ┌─────────────┴─────────────┐
               │                           │
             Gagal                       Sukses
               │                           │
               ▼                           ▼
       ┌───────────────┐           ┌───────────────┐
       │Tampilkan Error│           │ Masuk ke      │
       │Password Salah │           │ Dashboard Part│
       └───────────────┘           └───────┬───────┘
                                           │
                                           ▼
                                   ┌───────────────┐
                                   │ Lihat Komisi, │
                                   │ Link Referral │
                                   └───────┬───────┘
                                           │
                                           ▼
                                   ┌───────────────┐
                                   │ Klik Menu     │
                                   │ Pengaturan /  │
                                   │ Profil        │
                                   └───────┬───────┘
                                           │
                                           ▼
                                   ┌───────────────┐
                                   │ Input Password│
                                   │ Lama & Baru   │
                                   └───────┬───────┘
                                           │
                                           ▼
                                          / \
                                        /     \
                                      / Password\
                                      \  Cocok? /
                                        \     /
                                          \ /
                                           │
                             ┌─────────────┴─────────────┐
                             │                           │
                           Tidak                       Ya
                             │                           │
                             ▼                           ▼
                     ┌───────────────┐           ┌───────────────┐
                     │ Muncul Error  │           │ Update di Auth│
                     │ Password Salah│           │ Password Baru │
                     └───────────────┘           └───────────────┘
```

## 2. Penjelasan Detail Proses

### A. Tahap Login Partner
1. Partner mengakses halaman khusus login partner.
2. Partner memasukkan email dan password yang telah didaftarkan.
3. Supabase Auth memvalidasi data tersebut. Jika sukses, partner masuk ke dashboard khusus mereka.

### B. Tahap Aktivitas di Dashboard
1. Partner dapat melihat statistik jumlah referral yang berhasil mereka bawa.
2. Partner dapat melihat total omzet komisi yang sudah dihasilkan dan mencopy link referral mereka untuk disebarkan.

### C. Tahap Ganti Password
1. Partner mengklik menu "Pengaturan" atau "Profil" di sidebar/navbar.
2. Muncul form untuk mengubah password yang meminta: Password Lama, Password Baru, dan Konfirmasi Password Baru.
3. Sistem mengecek apakah password lama yang dimasukkan sudah benar.
4. Jika benar, sistem menggunakan fungsi `supabase.auth.updateUser` untuk memperbarui kata sandi partner tersebut di database otentikasi.
5. Muncul notifikasi sukses dan password baru sudah bisa digunakan pada login berikutnya.
