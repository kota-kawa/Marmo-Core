#!/usr/bin/env python3
import os
import sys
import json
import time
from playwright.sync_api import sync_playwright

def upload_video_live(video_path, caption, headless=False):
    cookie_path = "ujangfixing/tiktok_cookies.json"
    if not os.path.exists(cookie_path):
        print(f"Error: Cookie file not found at '{cookie_path}'. Please run decrypt first!")
        return False

    if not os.path.exists(video_path):
        print(f"Error: Video file not found at '{video_path}'!")
        return False

    # 1. Load and clean cookies for Playwright
    with open(cookie_path, "r") as f:
        raw_cookies = json.load(f)
    
    clean_cookies = []
    for c in raw_cookies:
        # Map values to Playwright specifications
        cookie = {
            "name": c["name"],
            "value": c["value"],
            "domain": c["domain"] if c["domain"].startswith('.') else f".{c['domain']}",
            "path": c["path"],
        }
        if "secure" in c:
            cookie["secure"] = c["secure"]
        if "httpOnly" in c:
            cookie["httpOnly"] = c["httpOnly"]
        if "sameSite" in c:
            val = c["sameSite"].lower()
            if val == "no_restriction":
                cookie["sameSite"] = "None"
            elif val in ["lax", "strict"]:
                cookie["sameSite"] = val.capitalize()
        clean_cookies.append(cookie)

    print(f"\n[Playwright] Memulai browser Chromium (headless={headless})...")
    
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=headless,
            args=["--disable-blink-features=AutomationControlled"]
        )
        
        # Create a premium browser context with realistic viewport
        context = browser.new_context(
            viewport={"width": 1280, "height": 800},
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
        )
        
        # Load the decrypted session cookies
        context.add_cookies(clean_cookies)
        
        page = context.new_page()
        
        print("[Playwright] Menavigasi ke halaman Upload TikTok...")
        page.goto("https://www.tiktok.com/tiktokstudio/upload?lang=id-ID", wait_until="domcontentloaded")
        
        print("[Playwright] Menunggu halaman upload termuat...")
        # Wait up to 20 seconds for the file input to appear
        try:
            page.wait_for_selector('input[type="file"]', timeout=30000)
        except Exception:
            print("[WARN] File input tidak langsung terdeteksi. Silakan periksa browser (mungkin ada captcha).")
            # If headed, give user time to solve captcha
            if not headless:
                print("[Playwright] Jeda 30 detik untuk memberikan waktu menyelesaikan Captcha/Login...")
                time.sleep(30)
            else:
                browser.close()
                return False

        # Double check if we are redirected to login
        if "login" in page.url:
            print("[ERROR] Cookie kedaluwarsa atau tidak valid! Silakan lakukan ekspor cookie baru dari Chrome.")
            browser.close()
            return False

        print(f"[Playwright] Memilih berkas video: {video_path}...")
        file_input = page.locator('input[type="file"]')
        file_input.set_input_files(video_path)
        
        print("[Playwright] Berkas berhasil dimasukkan! Menunggu proses upload selesai (10 detik)...")
        time.sleep(10)
        page.screenshot(path="ujangfixing/step1_file_uploaded.png")
        
        # BANYAK SEKALI TUTORIAL / TOUR DI TIKTOK STUDIO (JOYRIDE OVERLAY)
        # Hancurkan secara paksa semua overlay via JavaScript agar tidak menghalangi pointer!
        print("[Playwright] Menyingkirkan semua modal dan joyride tutorial dari DOM...")
        page.evaluate('''() => {
            const joyride = document.getElementById("react-joyride-portal");
            if (joyride) joyride.remove();
            
            const overlays = document.querySelectorAll(".react-joyride__overlay, .react-joyride__tooltip, .TUXModal-overlay, div[data-floating-ui-portal]");
            overlays.forEach(o => o.remove());
            
            // Hapus backdrop modal lain
            const backdrops = document.querySelectorAll(".common-modal-body, [class*='Modal'], [class*='Overlay']");
            backdrops.forEach(b => b.remove());
        }''')
        time.sleep(2)
        page.screenshot(path="ujangfixing/step2_dom_cleaned.png")

        # Type the caption
        print(f"[Playwright] Menulis caption: '{caption}'...")
        try:
            # TikTok caption editor is a contenteditable div inside DraftJS
            caption_editor = page.locator('div[contenteditable="true"]').first
            caption_editor.click()
            
            # Select all existing text and delete it
            page.keyboard.press("Meta+A") # Command + A for Mac
            page.keyboard.press("Backspace")
            
            # Type new caption character by character to look organic
            page.keyboard.type(caption, delay=50)
            time.sleep(2)
        except Exception as e:
            print(f"[WARN] Gagal menulis caption secara otomatis: {e}. Mengabaikan...")
        page.screenshot(path="ujangfixing/step3_caption_typed.png")

        print("[Playwright] Menyiapkan tombol Posting...")
        # Find Post/Bagikan button
        # On Indonesian TikTok, it is "Bagikan" or "Posting". On English, it's "Post".
        post_selectors = [
            'button.Button__root:has-text("Bagikan")',
            'button.Button__root:has-text("Post")',
            'button.Button__root:has-text("Posting")',
            'button:has-text("Bagikan"):not([data-tt])',
            'button:has-text("Post"):not([data-tt])',
            'button:has-text("Posting"):not([data-tt])',
            'div.btn-post button'
        ]
        
        posted = False
        for sel in post_selectors:
            btn = page.locator(sel).first
            if btn.is_visible() and btn.is_enabled():
                print(f"[Playwright] Menekan tombol Posting dengan selector: {sel}...")
                btn.click()
                posted = True
                break
                
        if not posted:
            print("[WARN] Tombol posting otomatis tidak terdeteksi atau belum siap.")
            if not headless:
                print("[INFO] Silakan klik tombol 'Bagikan' / 'Post' secara manual di browser yang terbuka!")
                print("Menunggu 45 detik sebelum menutup browser...")
                time.sleep(45)
                posted = True
            else:
                browser.close()
                return False

        page.screenshot(path="ujangfixing/step4_after_post_click.png")
        
        # PROSES HPP/VERIFIKASI TIKTOK: TAMPILKAN MODAL "Continue to post? / Tetap posting?"
        # Tekan tombol "Post now" / "Posting sekarang" secara otomatis!
        print("[Playwright] Menunggu konfirmasi modal 'Continue to post?'...")
        time.sleep(3)
        page.screenshot(path="ujangfixing/step4b_confirm_modal.png")
        
        post_now_selectors = [
            'button:has-text("Post now")',
            'button:has-text("Posting sekarang")',
            'button:has-text("Tetap posting")',
            'div[role="dialog"] button.Button__root--type-primary',
            'button.Button__root--type-primary:has-text("Post now")',
            'button.Button__root--type-primary:has-text("Posting sekarang")'
        ]
        
        confirmed = False
        for sel in post_now_selectors:
            btn = page.locator(sel).first
            if btn.is_visible() and btn.is_enabled():
                print(f"[Playwright] Menekan tombol konfirmasi posting akhir dengan selector: {sel}...")
                btn.click()
                confirmed = True
                break
                
        if not confirmed:
            print("[WARN] Tombol konfirmasi posting akhir tidak terdeteksi otomatis.")
            if not headless:
                print("[INFO] Silakan klik tombol 'Post now' / 'Posting sekarang' secara manual di browser!")
                time.sleep(10)
            else:
                print("[ERROR] Berjalan di mode headless dan gagal menemukan tombol konfirmasi akhir. Posting dibatalkan untuk mencegah false-positive!")
                browser.close()
                return False

        print("[Playwright] Menunggu 15 detik agar proses upload di latar belakang selesai...")
        time.sleep(15)
        page.screenshot(path="ujangfixing/step5_final_state.png")
        
        print("[Playwright] Pengunggahan selesai sukses!")
        browser.close()
        return True

if __name__ == "__main__":
    video = "ujangfixing/sample.mp4"
    caption = "Pusing hitung untung rugi? Ini trik hitung HPP biar gak boncos! #UMKM #TokcerAI #Fyp"
    caption_outro = "\n\n👉 Cobain GRATIS sekarang di: www.tokcer-ai.com (Klik link di bio profil kita!)"
    
    if "www.tokcer-ai.com" not in caption:
        full_caption = caption + caption_outro
    else:
        full_caption = caption
    upload_video_live(video, full_caption, headless=False)
