#!/usr/bin/env python3
import os
import json
import time
from playwright.sync_api import sync_playwright

def inspect_upload_page():
    cookie_path = "ujangfixing/tiktok_cookies.json"
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
        
    print("Launching Chromium...")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            viewport={"width": 1280, "height": 800},
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
        )
        context.add_cookies(clean_cookies)
        page = context.new_page()
        
        page.goto("https://www.tiktok.com/tiktokstudio/upload?lang=id-ID")
        time.sleep(15)
        
        print(f"URL: {page.url}")
        print(f"Title: {page.title()}")
        
        # 1. List all frames
        print("\n=== FRAMES ===")
        for idx, frame in enumerate(page.frames):
            print(f"Frame {idx}: Name='{frame.name}', URL='{frame.url}'")
            
        # 2. Check for input elements in all frames
        print("\n=== INPUTS ===")
        for idx, frame in enumerate(page.frames):
            inputs = frame.locator('input')
            count = inputs.count()
            print(f"Frame {idx} has {count} inputs:")
            for i in range(count):
                inp = inputs.nth(i)
                print(f"  - Input {i}: type='{inp.get_attribute('type')}', id='{inp.get_attribute('id')}', name='{inp.get_attribute('name')}'")
                
        # 3. Check for buttons in all frames
        print("\n=== BUTTONS ===")
        for idx, frame in enumerate(page.frames):
            buttons = frame.locator('button')
            count = buttons.count()
            print(f"Frame {idx} has {count} buttons:")
            for i in range(min(count, 10)):
                btn = buttons.nth(i)
                print(f"  - Button {i}: text='{btn.inner_text()}', class='{btn.get_attribute('class')}'")
                
        browser.close()

if __name__ == "__main__":
    inspect_upload_page()
