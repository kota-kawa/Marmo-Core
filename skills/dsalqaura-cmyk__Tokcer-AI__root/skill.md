# 📜 TOKCER AI: STAGING RULES & WORKFLOW (KITAB SUCI UCUP)

File ini adalah PANDUAN MUTLAK yang wajib dibaca oleh Ucup (Antigravity) sebelum melakukan perubahan apapun. Pelanggaran terhadap file ini adalah kesalahan fatal.

---

## 🛡️ WORKFLOW PATEN (ALUR KERJA)

### 1. Jalur User (Klien)
*   **Register**: `pending` -> `User Modal` (Landing Page).
*   **Payment**: User bayar & upload bukti (Opsional).
*   **Approval**: Admin cek Dashboard Internal -> Klik **Approve**.
*   **Active**: Status jadi `active` -> Robot kirim email akses.

### 2. Jalur Partner (RESIKO TINGGI)
1.  **Register**: `pending` -> `Partner Modal` (Landing Page).
2.  **Robot 1**: Database Trigger `send_agreement_email` nembak email pendaftaran.
3.  **Signing**: Partner klik link -> Halaman `PartnerAgreement.jsx` -> Klik "Saya Setuju".
4.  **Agreed State**: Status berubah jadi `agreed`. Muncul di Dashboard Bapak (Tab Approval).
5.  **Success Screen**: Partner melihat overlay "Welcome, Partner!" (REF Code).
6.  **Auto-Redirect**: Setelah 5 detik di layar sukses, Partner DILEMPAR ke `https://staging.tokcer-ai.com`.
7.  **Admin Action**: Bapak klik **Approve** di Dashboard Internal.
8.  **Robot 2**: Database Trigger `fn_send_partner_welcome_email` nembak email berisi Password (`Tokcer@2026`).

---

## 🏮 ATURAN CODING (STRICT RULES)

1.  **DILARANG SOK IDE**: Jangan menambah redirect, timer, atau flow baru tanpa izin tertulis dari Bapak.
2.  **LINK PATEN**: 
    *   Gunakan `https://staging.tokcer-ai.com/partner-agreement?id=...` (TANPA PAGAR `#`).
    *   Jika landing page butuh `#`, konfirmasi dulu.
3.  **VISUAL PREMIUM**:
    *   Gunakan Logo PNG: `https://dashboardstaging.tokcer-ai.com/logo.png`.
    *   Hapus semua teks WhatsApp, ganti dengan Email.
4.  **DATABASE TRIGGERS**:
    *   `send_agreement_email`: Handle email pendaftaran (Logo PNG + Link Staging).
    *   `fn_send_partner_welcome_email`: Handle email aktivasi/password (HANYA saat status = 'active').

---

## 🗣️ KOMUNIKASI (GOLDEN RULE)

*   **TANYA DULU BARU JALAN**: Jika ada keraguan sedikitpun soal domain atau alur, WAJIB konfirmasi ke Bapak.
*   **FOKUS ISSUE**: Jangan memperbaiki hal yang tidak rusak. Fokus pada apa yang Bapak perintahkan.
*   **NO HALLUCINATION**: Jangan menebak-nebak domain atau password. Baca file `.env` atau tanya Bapak.

---

**DITETAPKAN PADA: 2026-05-04**
*Ucup berjanji akan mematuhi Kitab Suci ini demi kelancaran Tokcer AI.* 🫡🚀🛡️
