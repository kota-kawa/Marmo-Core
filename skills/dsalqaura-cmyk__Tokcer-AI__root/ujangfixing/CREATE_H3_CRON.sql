-- ==============================================================================
-- TOKCER AI: H-3 SUBSCRIPTION EXPIRY REMINDER SYSTEM (CRON JOB)
-- ==============================================================================
-- Deskripsi:
-- Script ini mengatur pg_cron untuk memanggil Supabase Edge Function
-- 'cron-h3-reminder' setiap hari pada jam 00:00 AM (tengah malam).
-- Edge Function tersebut akan mengirim email tagihan H-3 ke klien.
--
-- Prasyarat:
-- 1. pg_net dan pg_cron extension harus aktif di Supabase.
-- 2. SUPABASE_URL dan SUPABASE_SERVICE_ROLE_KEY di Supabase Edge Functions.
-- ==============================================================================

-- 1. Pastikan extensions aktif (biasanya sudah default di Supabase)
CREATE EXTENSION IF NOT EXISTS pg_net;
CREATE EXTENSION IF NOT EXISTS pg_cron;

-- 2. Hapus job lama jika pernah dibuat (agar tidak duplikat)
SELECT cron.unschedule('daily-h3-reminder-email');

-- 3. Jadwalkan eksekusi Edge Function setiap jam 00:00 setiap hari
SELECT cron.schedule(
  'daily-h3-reminder-email', -- Nama Job
  '0 0 * * *',               -- Cron expression: Setiap menit ke-0, jam ke-0 setiap hari (Midnight)
  $$
    -- Panggil Edge Function menggunakan pg_net
    -- Catatan: Ganti 'https://[PROJECT_REF].supabase.co' dengan URL asli project Supabase
    -- Karena kita tidak tahu URL project dari SQL secara dinamis, disarankan untuk 
    -- memicu cron ini melalui webhook atau pastikan URL di bawah disesuaikan di Production.
    
    -- Contoh dengan URL relatif jika pg_net mendukung panggilan internal (tergantung versi Supabase):
    SELECT net.http_post(
      url:='https://dthzntikshlvyzfxuugc.supabase.co/functions/v1/cron-h3-reminder',
      headers:='{"Content-Type": "application/json", "Authorization": "Bearer YOUR_ANON_OR_SERVICE_KEY"}'::jsonb
    );
  $$
);

-- ==============================================================================
-- PENTING UNTUK ADMIN:
-- Karena pg_net butuh URL absolute, lebih disarankan membuat Scheduled Function
-- melalui Supabase Dashboard -> Edge Functions -> Pilih 'cron-h3-reminder'
-- lalu set Schedule '0 0 * * *'.
-- Script SQL ini adalah fallback/dokumentasi jika ingin diset langsung via Database.
-- ==============================================================================
