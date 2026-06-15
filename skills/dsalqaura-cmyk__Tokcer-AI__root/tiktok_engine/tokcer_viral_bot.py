#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
=============================================================================
TOKCER AI — VIRAL BOT ORCHESTRATOR (tokcer_viral_bot.py)
=============================================================================
Bot utama yang menghubungkan seluruh pipeline autoposting TikTok:
  1. Cek stok konten di Supabase (viral_templates)
  2. Auto-replenish jika stok menipis (< 5 konten)
  3. Ambil job dari upload_queue yang sudah jatuh tempo
  4. Render video (TTS + Visual + MoviePy)
  5. Upload ke TikTok via Playwright (stealth mode)
  6. Update status di Supabase
  7. Jika queue kosong: ambil konten baru dari bank & jadwalkan otomatis

Dijalankan oleh macOS LaunchAgent setiap 1 jam.
=============================================================================
"""

import os
import sys
import json
import time
import uuid
import random
import logging
import requests
from datetime import datetime, timedelta, timezone

# ─── Setup path ───────────────────────────────────────────────────────────────
WORKSPACE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TIKTOK_ENGINE_DIR = os.path.join(WORKSPACE, "tiktok_engine")
sys.path.insert(0, WORKSPACE)
sys.path.insert(0, TIKTOK_ENGINE_DIR)

# ─── Setup Logging ────────────────────────────────────────────────────────────
LOG_FILE = os.path.join(TIKTOK_ENGINE_DIR, "autopost_bot.log")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
        logging.StreamHandler(sys.stdout)
    ]
)
log = logging.getLogger("TokceBot")

# ─── Load .env ────────────────────────────────────────────────────────────────
def load_env():
    env_vars = {}
    for path in [".env", ".env.staging"]:
        full = os.path.join(WORKSPACE, path)
        if os.path.exists(full):
            with open(full, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        k, v = line.split("=", 1)
                        env_vars[k.strip()] = v.strip().strip('"').strip("'")
            break
    return env_vars

ENV           = load_env()
SUPABASE_URL  = ENV.get("VITE_SUPABASE_URL", "")
SUPABASE_KEY  = ENV.get("VITE_SUPABASE_ANON_KEY", "")
TIKTOK_USER   = ENV.get("TIKTOK_USERNAME", "@tokcer_ai")

HEADERS = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json",
    "Prefer": "return=representation"
}

# ─── Smart Scheduler V2 — Formasi 3-2-2-1-2-3-1 ──────────────────────────────
# weekday(): 0=Senin, 1=Selasa, ..., 6=Minggu
SCHEDULE_MAP = {
    0: [12, 17, 19],   # Senin  — kuota 3
    1: [12, 19],       # Selasa — kuota 2
    2: [12, 19],       # Rabu   — kuota 2
    3: [19],           # Kamis  — kuota 1
    4: [12, 19],       # Jumat  — kuota 2
    5: [12, 17, 19],   # Sabtu  — kuota 3
    6: [19],           # Minggu — kuota 1
}

# =============================================================================
# BAGIAN 1 — SUPABASE HELPERS
# =============================================================================

def db_get(endpoint, params=""):
    """GET dari Supabase REST API."""
    url = f"{SUPABASE_URL}/rest/v1/{endpoint}{params}"
    try:
        r = requests.get(url, headers=HEADERS, timeout=15)
        if r.status_code == 200:
            return r.json()
        log.warning(f"[DB GET] {endpoint} → HTTP {r.status_code}: {r.text[:200]}")
    except Exception as e:
        log.error(f"[DB GET] Exception: {e}")
    return None

def db_post(endpoint, payload):
    """POST ke Supabase REST API."""
    url = f"{SUPABASE_URL}/rest/v1/{endpoint}"
    try:
        r = requests.post(url, headers=HEADERS, json=payload, timeout=15)
        if r.status_code in [200, 201]:
            return r.json()
        log.warning(f"[DB POST] {endpoint} → HTTP {r.status_code}: {r.text[:200]}")
    except Exception as e:
        log.error(f"[DB POST] Exception: {e}")
    return None

def db_patch(endpoint, match_params, payload):
    """PATCH (update) di Supabase REST API."""
    url = f"{SUPABASE_URL}/rest/v1/{endpoint}{match_params}"
    try:
        r = requests.patch(url, headers=HEADERS, json=payload, timeout=15)
        if r.status_code in [200, 204]:
            return True
        log.warning(f"[DB PATCH] {endpoint} → HTTP {r.status_code}: {r.text[:200]}")
    except Exception as e:
        log.error(f"[DB PATCH] Exception: {e}")
    return False

def get_unused_templates(limit=10):
    """Ambil konten yang belum dipakai dari bank viral_templates."""
    data = db_get("viral_templates", f"?used=eq.false&order=created_at.asc&limit={limit}&select=*")
    return data or []

def get_pending_jobs():
    """Ambil job dari upload_queue yang sudah jatuh tempo dan belum diproses."""
    now_fmt = _fmt_ts(datetime.now(timezone.utc))
    data = db_get(
        "upload_queue",
        f"?status=eq.pending&scheduled_time=lte.{now_fmt}&order=scheduled_time.asc&limit=1&select=*"
    )
    return data or []

def mark_template_used(template_id):
    return db_patch("viral_templates", f"?id=eq.{template_id}", {"used": True})

def update_job_status(job_id, status, video_path=None):
    payload = {
        "status": status,
        "actual_post_time": datetime.now(timezone.utc).isoformat() if status == "posted" else None
    }
    if video_path:
        payload["video_path"] = video_path
    return db_patch("upload_queue", f"?id=eq.{job_id}", payload)

def _fmt_ts(dt):
    """Format datetime ke string ISO 8601 yang diterima Supabase PostgREST."""
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")

def count_pending_today():
    """Hitung berapa job pending yang sudah dijadwalkan hari ini."""
    now = datetime.now(timezone.utc)
    today_start = _fmt_ts(now.replace(hour=0, minute=0, second=0, microsecond=0))
    today_end   = _fmt_ts(now.replace(hour=23, minute=59, second=59, microsecond=0))
    data = db_get(
        "upload_queue",
        f"?status=in.(pending,processing,posted)&scheduled_time=gte.{today_start}&scheduled_time=lte.{today_end}&select=id"
    )
    return len(data) if data else 0

# =============================================================================
# BAGIAN 2 — SMART SCHEDULER
# =============================================================================

def get_next_available_slot():
    """
    Cari slot jadwal berikutnya yang belum terisi berdasarkan formasi 3-2-2-1-2-3-1.
    Menambahkan jitter menit (5-29) dan detik acak agar terlihat organik.
    """
    now = datetime.now(timezone.utc)
    check_date = now.date()

    for _ in range(14):  # Cari hingga 2 minggu ke depan
        weekday = check_date.weekday()
        slots_today = SCHEDULE_MAP.get(weekday, [19])

        # Hitung berapa slot yang sudah terisi di hari ini
        day_start = datetime(check_date.year, check_date.month, check_date.day, 0, 0, 0, tzinfo=timezone.utc)
        day_end   = datetime(check_date.year, check_date.month, check_date.day, 23, 59, 59, tzinfo=timezone.utc)
        data = db_get(
            "upload_queue",
            f"?status=in.(pending,processing,posted)&scheduled_time=gte.{_fmt_ts(day_start)}&scheduled_time=lte.{_fmt_ts(day_end)}&select=id"
        )
        used_slots = len(data) if data else 0

        if used_slots < len(slots_today):
            # Ambil slot jam berikutnya yang belum terisi
            slot_hour = slots_today[used_slots]
            jitter_min = random.randint(5, 29)
            jitter_sec = random.randint(0, 59)
            slot_dt = datetime(
                check_date.year, check_date.month, check_date.day,
                slot_hour, jitter_min, jitter_sec,
                tzinfo=timezone.utc
            )
            # Jika slot sudah lewat hari ini, tetap pakai (anti-nyangkut)
            return slot_dt

        check_date += timedelta(days=1)

    # Fallback: besok jam 19
    tomorrow = now + timedelta(days=1)
    return tomorrow.replace(hour=19, minute=random.randint(5, 29), second=random.randint(0, 59))

def enqueue_new_job(template):
    """
    Buat entry baru di upload_queue dari sebuah template konten.
    Video belum di-render — video_path diisi dengan placeholder UUID.
    """
    job_id    = str(uuid.uuid4())
    slot_time = get_next_available_slot()
    title     = template.get("tips_title", "Tips Tokcer")
    caption   = (
        f"{title} - Tips jualan online UMKM! "
        f"#UMKM #TokcerAI #Fyp #Seller #JualanOnline\n\n"
        f"👉 Cobain GRATIS sekarang di: www.tokcer-ai.com (Klik link di bio profil kita!)"
    )
    video_path = f"tiktok_engine/video_render_{job_id}.mp4"

    payload = {
        "id": job_id,
        "video_path": video_path,
        "caption": caption,
        "account_platform": "tiktok",
        "account_username": TIKTOK_USER,
        "status": "pending",
        "scheduled_time": _fmt_ts(slot_time),
    }

    # Coba insert dengan template_id dulu, fallback tanpa jika kolom belum ada
    payload_with_tid = {**payload, "template_id": template.get("id")}
    result = db_post("upload_queue", payload_with_tid)
    if result is None:
        result = db_post("upload_queue", payload)
    if result:
        log.info(f"[Scheduler] Job baru dijadwalkan: '{title}' → {slot_time.strftime('%A %d %b %Y %H:%M WIB')}")
        mark_template_used(template["id"])
        return job_id, video_path, template
    return None, None, None

# =============================================================================
# BAGIAN 3 — VIDEO RENDERER
# =============================================================================

def upload_video_to_storage(video_path, job_id):
    """
    Upload file video ke Supabase Storage bucket 'tiktok-videos'.
    Mengembalikan public URL jika berhasil, None jika gagal.
    """
    if not os.path.exists(video_path):
        log.error(f"[Storage] File tidak ditemukan: {video_path}")
        return None

    BUCKET      = "tiktok-videos"
    file_name   = f"video_{job_id}.mp4"
    upload_url  = f"{SUPABASE_URL}/storage/v1/object/{BUCKET}/{file_name}"
    public_url  = f"{SUPABASE_URL}/storage/v1/object/public/{BUCKET}/{file_name}"

    try:
        with open(video_path, "rb") as f:
            file_data = f.read()

        headers_storage = {
            "apikey": SUPABASE_KEY,
            "Authorization": f"Bearer {SUPABASE_KEY}",
            "Content-Type": "video/mp4",
            "x-upsert": "true"
        }

        r = requests.post(upload_url, headers=headers_storage, data=file_data, timeout=120)

        if r.status_code in [200, 201]:
            log.info(f"[Storage] ✅ Upload berhasil: {public_url}")
            return public_url
        else:
            log.warning(f"[Storage] Upload gagal HTTP {r.status_code}: {r.text[:300]}")
            return None
    except Exception as e:
        log.error(f"[Storage] Exception saat upload: {e}")
        return None

def render_video(job, template):
    """
    Render video MP4 dari konten template menggunakan video_generator.py.
    Mengembalikan path video yang sudah jadi, atau None jika gagal.
    """
    try:
        from video_generator import build_real_video
    except ImportError:
        try:
            from tiktok_engine.video_generator import build_real_video
        except ImportError:
            log.error("[Render] Gagal import video_generator. Pastikan path benar.")
            return None

    title   = template.get("tips_title", "Tips Tokcer")
    content = template.get("tips_content", "")
    output  = job.get("video_path", f"tiktok_engine/video_render_{job['id']}.mp4")

    # Pastikan path absolut
    if not os.path.isabs(output):
        output = os.path.join(WORKSPACE, output)

    # Pastikan direktori output ada
    os.makedirs(os.path.dirname(output), exist_ok=True)

    log.info(f"[Render] Mulai render video: '{title}'")
    log.info(f"[Render] Output: {output}")

    # Jalankan dari WORKSPACE agar path relatif di video_generator benar
    original_dir = os.getcwd()
    try:
        os.chdir(WORKSPACE)
        success = build_real_video(title, content, output)
    finally:
        os.chdir(original_dir)

    if success and os.path.exists(output):
        size_mb = os.path.getsize(output) / (1024 * 1024)
        log.info(f"[Render] ✅ Video selesai: {output} ({size_mb:.1f} MB)")
        return output
    else:
        log.error(f"[Render] ❌ Render gagal untuk: '{title}'")
        return None

# =============================================================================
# BAGIAN 4 — TIKTOK UPLOADER
# =============================================================================

def upload_to_tiktok(video_path, caption):
    """
    Upload video ke TikTok menggunakan live_tiktok_uploader_staging.py (stealth mode).
    Mengembalikan True jika berhasil.
    """
    try:
        from live_tiktok_uploader_staging import upload_video_live_staging
    except ImportError:
        try:
            from tiktok_engine.live_tiktok_uploader_staging import upload_video_live_staging
        except ImportError:
            log.error("[Upload] Gagal import live_tiktok_uploader_staging.")
            return False

    # Pastikan path absolut
    if not os.path.isabs(video_path):
        video_path = os.path.join(WORKSPACE, video_path)

    if not os.path.exists(video_path):
        log.error(f"[Upload] File video tidak ditemukan: {video_path}")
        return False

    log.info(f"[Upload] Memulai upload ke TikTok...")
    log.info(f"[Upload] Video: {video_path}")
    log.info(f"[Upload] Caption: {caption[:80]}...")

    original_dir = os.getcwd()
    try:
        os.chdir(WORKSPACE)
        # headless=True untuk server/LaunchAgent, False untuk debug manual
        headless_mode = os.environ.get("TOKCER_HEADLESS", "true").lower() == "true"
        success = upload_video_live_staging(video_path, caption, headless=headless_mode)
    finally:
        os.chdir(original_dir)

    return success


def cleanup_video(video_path):
    """Hapus file video setelah berhasil diupload untuk hemat disk."""
    if not os.path.isabs(video_path):
        video_path = os.path.join(WORKSPACE, video_path)
    try:
        if os.path.exists(video_path):
            os.remove(video_path)
            log.info(f"[Cleanup] File video dihapus: {video_path}")
    except Exception as e:
        log.warning(f"[Cleanup] Gagal hapus file: {e}")

# =============================================================================
# BAGIAN 5 — AUTO-REPLENISHER KONTEN
# =============================================================================

def replenish_content_if_needed():
    """
    Cek stok konten di Supabase. Jika < 5, jalankan content generator
    untuk mengisi ulang dari 365 tema + local_premium_tips.json.
    """
    data = db_get("viral_templates", "?used=eq.false&select=id")
    unused_count = len(data) if data else 0
    log.info(f"[Replenish] Stok konten unused: {unused_count}")

    if unused_count < 5:
        log.info("[Replenish] Stok menipis! Menjalankan content generator...")
        try:
            from tokcer_content_generator import replenish_bank_templates
        except ImportError:
            try:
                from tiktok_engine.tokcer_content_generator import replenish_bank_templates
            except ImportError:
                log.error("[Replenish] Gagal import tokcer_content_generator.")
                return

        original_dir = os.getcwd()
        try:
            os.chdir(WORKSPACE)
            replenish_bank_templates()
        finally:
            os.chdir(original_dir)
        log.info("[Replenish] ✅ Konten berhasil diisi ulang.")
    else:
        log.info("[Replenish] Stok konten cukup, tidak perlu replenish.")


def fill_queue_from_bank(max_fill=3):
    """
    Ambil konten dari bank viral_templates, jadwalkan ke upload_queue,
    lalu langsung render + upload ke Supabase Storage.
    Video langsung "Siap Download" tanpa perlu tunggu jadwal.
    Auto-replenish jika pending < 5.
    """
    # Cek total pending yang belum punya storage URL
    all_pending = db_get("upload_queue", "?status=eq.pending&select=id,video_path") or []
    pending_without_storage = [j for j in all_pending if not (j.get("video_path","").startswith("http"))]
    total_pending = len(all_pending)

    log.info(f"[FillQueue] Total pending: {total_pending} | Tanpa storage URL: {len(pending_without_storage)}")

    # Auto-replenish: kalau pending < 5, generate konten baru
    if total_pending < 5:
        log.info(f"[FillQueue] Pending < 5, generate {max_fill} konten baru...")
        templates = get_unused_templates(limit=max_fill)
        if not templates:
            log.warning("[FillQueue] Tidak ada template unused tersedia.")
        else:
            for tmpl in templates:
                job_id, video_path, _ = enqueue_new_job(tmpl)
                if job_id:
                    pending_without_storage.append({"id": job_id, "video_path": video_path})
                time.sleep(0.3)

    # Render + upload storage untuk semua job yang belum punya URL
    rendered_count = 0
    for job_stub in pending_without_storage[:max_fill]:
        job_id = job_stub["id"]
        # Ambil data job lengkap
        job_data = db_get("upload_queue", f"?id=eq.{job_id}&select=*")
        if not job_data:
            continue
        job = job_data[0]

        template = get_template_for_job(job)
        if not template:
            log.warning(f"[FillQueue] Template tidak ditemukan untuk job {job_id}, skip.")
            continue

        log.info(f"[FillQueue] Render: '{template.get('tips_title')}'")
        rendered = render_video(job, template)
        if not rendered:
            log.error(f"[FillQueue] Render gagal untuk job {job_id}")
            update_job_status(job_id, "failed")
            continue

        storage_url = upload_video_to_storage(rendered, job_id)
        if storage_url:
            update_job_status(job_id, "pending", video_path=storage_url)
            log.info(f"[FillQueue] ✅ Siap download: {storage_url}")
            rendered_count += 1
        else:
            log.warning(f"[FillQueue] Storage upload gagal untuk job {job_id}")

        # Hapus file lokal setelah upload
        cleanup_video(rendered)
        time.sleep(0.5)

    log.info(f"[FillQueue] Selesai. {rendered_count} video siap download di dashboard.")
    return rendered_count

# =============================================================================
# BAGIAN 6 — AMBIL TEMPLATE DARI JOB (helper)
# =============================================================================

def get_template_for_job(job):
    """
    Ambil data template konten yang terkait dengan sebuah job.
    Coba via template_id dulu, fallback ke pencarian judul dari caption.
    """
    template_id = job.get("template_id")
    if template_id:
        data = db_get("viral_templates", f"?id=eq.{template_id}&select=*")
        if data and len(data) > 0:
            return data[0]

    # Fallback: cari dari judul di caption
    caption = job.get("caption", "")
    title = caption.split(" - ")[0].strip() if " - " in caption else ""

    if title and len(title) > 5:
        # Encode untuk URL query
        title_search = title[:25].replace(" ", "%20")
        data = db_get("viral_templates", f"?tips_title=ilike.*{title_search}*&select=*&limit=1")
        if data and len(data) > 0:
            return data[0]

    # Fallback: ambil template unused pertama yang tersedia
    data = db_get("viral_templates", "?used=eq.false&select=*&limit=1&order=created_at.asc")
    if data and len(data) > 0:
        log.warning(f"[Template] Menggunakan template fallback: '{data[0].get('tips_title')}'")
        return data[0]

    # Fallback terakhir: buat template dari local_premium_tips.json
    local_json = os.path.join(TIKTOK_ENGINE_DIR, "local_premium_tips.json")
    if os.path.exists(local_json):
        with open(local_json, "r", encoding="utf-8") as f:
            tips = json.load(f)
        if tips:
            log.warning("[Template] Menggunakan local_premium_tips.json sebagai fallback terakhir.")
            return tips[0]

    return None


# =============================================================================
# BAGIAN 7 — MAIN PIPELINE
# =============================================================================

def run_pipeline():
    """
    Pipeline utama yang dijalankan setiap kali bot dipanggil oleh LaunchAgent.
    """
    log.info("=" * 60)
    log.info("   TOKCER AI VIRAL BOT — PIPELINE DIMULAI")
    log.info(f"   Waktu: {datetime.now().strftime('%A, %d %b %Y %H:%M:%S WIB')}")
    log.info("=" * 60)

    if not SUPABASE_URL or not SUPABASE_KEY:
        log.error("[FATAL] SUPABASE_URL atau SUPABASE_ANON_KEY tidak ditemukan di .env!")
        sys.exit(1)

    # ── STEP 1: Replenish konten jika stok menipis ────────────────────────────
    log.info("\n[STEP 1] Cek & replenish stok konten...")
    replenish_content_if_needed()

    # ── STEP 2: Cek apakah ada job pending yang jatuh tempo ───────────────────
    log.info("\n[STEP 2] Cek upload_queue untuk job yang jatuh tempo...")
    pending_jobs = get_pending_jobs()

    if not pending_jobs:
        log.info("[STEP 2] Tidak ada job yang jatuh tempo saat ini.")

        # Cek apakah queue hari ini sudah terisi
        today_count = count_pending_today()
        today_weekday = datetime.now().weekday()
        today_quota = len(SCHEDULE_MAP.get(today_weekday, [19]))
        log.info(f"[STEP 2] Queue hari ini: {today_count}/{today_quota} slot terisi.")

        if today_count < today_quota:
            log.info("[STEP 2] Slot hari ini masih kosong. Mengisi queue dari bank konten...")
            filled = fill_queue_from_bank(max_fill=today_quota - today_count)
            if filled > 0:
                log.info(f"[STEP 2] {filled} job baru dijadwalkan. Bot akan mengeksekusi di jam yang tepat.")
            else:
                log.warning("[STEP 2] Tidak ada konten tersedia untuk dijadwalkan.")
        else:
            log.info("[STEP 2] Semua slot hari ini sudah terisi. Tidak ada aksi.")

        log.info("\n[SELESAI] Bot selesai. Sampai jumpa di run berikutnya!")
        return

    # ── STEP 3: Proses job yang jatuh tempo ───────────────────────────────────
    job = pending_jobs[0]
    job_id     = job["id"]
    video_path = job.get("video_path", "")
    caption    = job.get("caption", "")

    log.info(f"\n[STEP 3] Memproses job: {job_id}")
    log.info(f"[STEP 3] Dijadwalkan: {job.get('scheduled_time', 'N/A')}")
    log.info(f"[STEP 3] Caption: {caption[:80]}...")

    # Tandai sebagai 'processing' agar tidak diambil dua kali
    update_job_status(job_id, "processing")

    # ── STEP 4: Ambil template konten ─────────────────────────────────────────
    log.info("\n[STEP 4] Mengambil data template konten...")
    template = get_template_for_job(job)
    if not template:
        log.error("[STEP 4] ❌ Template konten tidak ditemukan! Job ditandai failed.")
        update_job_status(job_id, "failed")
        return

    log.info(f"[STEP 4] Template: '{template.get('tips_title', 'N/A')}'")

    # ── STEP 5: Render video ──────────────────────────────────────────────────
    log.info("\n[STEP 5] Render video...")
    rendered_path = render_video(job, template)

    if not rendered_path:
        log.error("[STEP 5] ❌ Render video gagal! Job ditandai failed.")
        update_job_status(job_id, "failed")
        return

    # Update video_path di DB dengan path absolut yang sudah dikonfirmasi
    update_job_status(job_id, "processing", video_path=rendered_path)

    # ── STEP 5b: Upload video ke Supabase Storage ─────────────────────────────
    log.info("\n[STEP 5b] Upload video ke Supabase Storage...")
    storage_url = upload_video_to_storage(rendered_path, job_id)

    if storage_url:
        # Update video_path di DB dengan public URL agar bisa didownload dari dashboard
        update_job_status(job_id, "processing", video_path=storage_url)
        log.info(f"[STEP 5b] ✅ video_path diupdate ke storage URL: {storage_url}")
    else:
        log.warning("[STEP 5b] ⚠ Upload ke storage gagal — video_path tetap path lokal.")
        log.warning("[STEP 5b]   Video tidak akan bisa didownload dari dashboard admin.")
        log.warning("[STEP 5b]   Pastikan bucket 'tiktok-videos' sudah dibuat di Supabase Storage.")

    # ── STEP 6: Upload ke TikTok ──────────────────────────────────────────────
    log.info("\n[STEP 6] Upload ke TikTok...")
    upload_success = upload_to_tiktok(rendered_path, caption)

    if upload_success:
        log.info("[STEP 6] ✅ Upload BERHASIL!")
        update_job_status(job_id, "posted")
        cleanup_video(rendered_path)
        log.info(f"\n🎉 VIDEO BERHASIL DIPOSTING KE TIKTOK!")
        log.info(f"   Judul: {template.get('tips_title', 'N/A')}")
        log.info(f"   Waktu: {datetime.now().strftime('%d %b %Y %H:%M:%S')}")
    else:
        log.error("[STEP 6] ❌ Upload GAGAL! Job ditandai failed.")
        update_job_status(job_id, "failed")
        log.warning("[STEP 6] Video tidak dihapus agar bisa dicoba ulang secara manual.")

    log.info("\n[SELESAI] Pipeline selesai dijalankan.")

# =============================================================================
# BAGIAN 8 — ENTRY POINT & MODE KHUSUS
# =============================================================================

def run_fill_only():
    """Mode khusus: hanya isi queue dari bank konten tanpa upload."""
    log.info("[FillOnly] Mengisi queue dari bank konten...")
    replenish_content_if_needed()
    filled = fill_queue_from_bank(max_fill=7)
    log.info(f"[FillOnly] Selesai. {filled} job dijadwalkan.")

def run_force_now(template_index=0):
    """Mode debug: paksa render + upload storage + upload TikTok sekarang tanpa cek jadwal."""
    log.info("[ForceNow] Mode debug: paksa upload sekarang...")
    templates = get_unused_templates(limit=5)
    if not templates:
        log.error("[ForceNow] Tidak ada template tersedia.")
        return
    tmpl = templates[min(template_index, len(templates)-1)]
    job_id = str(uuid.uuid4())
    fake_job = {
        "id": job_id,
        "video_path": f"tiktok_engine/video_render_{job_id}.mp4",
        "caption": (
            f"{tmpl['tips_title']} - Tips jualan online UMKM! "
            f"#UMKM #TokcerAI #Fyp #Seller\n\n"
            f"👉 Cobain GRATIS sekarang di: www.tokcer-ai.com (Klik link di bio profil kita!)"
        ),
        "template_id": tmpl["id"]
    }
    rendered = render_video(fake_job, tmpl)
    if not rendered:
        log.error("[ForceNow] ❌ Render gagal.")
        return

    # Upload ke Supabase Storage
    log.info("[ForceNow] Upload video ke Supabase Storage...")
    storage_url = upload_video_to_storage(rendered, job_id)
    if storage_url:
        log.info(f"[ForceNow] ✅ Storage URL: {storage_url}")
    else:
        log.warning("[ForceNow] ⚠ Upload storage gagal, lanjut upload TikTok dengan file lokal.")

    success = upload_to_tiktok(rendered, fake_job["caption"])
    if success:
        mark_template_used(tmpl["id"])
        cleanup_video(rendered)
        log.info("[ForceNow] ✅ Upload paksa berhasil!")
    else:
        log.error("[ForceNow] ❌ Upload TikTok gagal.")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Tokcer AI Viral Bot")
    parser.add_argument(
        "--mode",
        choices=["auto", "fill", "force", "status"],
        default="auto",
        help=(
            "auto   = pipeline normal (default, dipakai LaunchAgent)\n"
            "fill   = hanya isi queue dari bank konten\n"
            "force  = paksa render+upload 1 video sekarang (debug)\n"
            "status = tampilkan status queue saat ini"
        )
    )
    parser.add_argument("--headless", action="store_true", default=True,
                        help="Jalankan browser headless (default: True)")
    parser.add_argument("--no-headless", dest="headless", action="store_false",
                        help="Tampilkan browser (untuk debug)")
    args = parser.parse_args()

    # Set headless mode via env var agar terbaca di upload_to_tiktok()
    os.environ["TOKCER_HEADLESS"] = "true" if args.headless else "false"

    if args.mode == "auto":
        run_pipeline()
    elif args.mode == "fill":
        run_fill_only()
    elif args.mode == "force":
        os.environ["TOKCER_HEADLESS"] = "false"  # Force mode selalu tampilkan browser
        run_force_now()
    elif args.mode == "status":
        log.info("=== STATUS QUEUE ===")
        for status in ["pending", "processing", "posted", "failed"]:
            data = db_get("upload_queue", f"?status=eq.{status}&select=id,scheduled_time,caption")
            count = len(data) if data else 0
            log.info(f"  {status.upper():12s}: {count} job")
            if data and status == "pending":
                for item in data[:5]:
                    log.info(f"    → {item.get('scheduled_time','?')} | {item.get('caption','?')[:60]}")
        unused = db_get("viral_templates", "?used=eq.false&select=id")
        log.info(f"  BANK KONTEN  : {len(unused) if unused else 0} template unused")
