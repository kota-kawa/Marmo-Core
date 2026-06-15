#!/usr/bin/env python3
import os
import json
import time
from playwright.sync_api import sync_playwright

def diagnose_tiktok():
    cookie_path = "ujangfixing/tiktok_cookies.json"
    if not os.path.exists(cookie_path):
        print(f"Error: Cookie file not found.")
        return
        
    with open(cookie_path, "r") as f:
        raw_cookies = json.load(f)
        
    clean_cookies = []
    for c in raw_cookies:
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
        
    print("Launching headless Chromium...")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            viewport={"width": 1280, "height": 800},
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
        )
        context.add_cookies(clean_cookies)
        page = context.new_page()
        
        print("Navigating to upload page...")
        page.goto("https://www.tiktok.com/creator-center/upload?lang=id-ID")
        
        print("Waiting 10 seconds for rendering...")
        time.sleep(10)
        
        print(f"Current URL: {page.url}")
        print(f"Page Title: {page.title()}")
        
        # Take screenshot to diagnose
        screenshot_path = "ujangfixing/diagnose.png"
        page.screenshot(path=screenshot_path)
        print(f"Screenshot saved to: {screenshot_path}")
        
        browser.close()

if __name__ == "__main__":
    diagnose_tiktok()
