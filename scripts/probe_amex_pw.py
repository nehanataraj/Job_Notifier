#!/usr/bin/env python3
from playwright.sync_api import sync_playwright

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
captured = []

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page(user_agent=UA)

    def on_response(resp):
        if "pcsx" in resp.url and resp.status == 200:
            try:
                data = resp.json()
                pos = (data.get("data") or data).get("positions") or []
                captured.append((resp.url, len(pos)))
            except Exception:
                captured.append((resp.url, "badjson"))

    page.on("response", on_response)
    page.goto("https://aexp.eightfold.ai/careers?query=intern", wait_until="domcontentloaded", timeout=120000)
    page.wait_for_timeout(8000)
    browser.close()

print("captured", captured)
