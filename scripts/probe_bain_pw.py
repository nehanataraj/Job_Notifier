#!/usr/bin/env python3
from playwright.sync_api import sync_playwright
import json

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page(user_agent=UA)
    bain_data = []
    def on_resp(resp):
        if "jobsearch" in resp.url and resp.status == 200:
            try:
                bain_data.append(resp.json())
            except Exception:
                pass
    page.on("response", on_resp)
    page.goto("https://www.bain.com/careers/find-a-role/?q=intern", wait_until="networkidle", timeout=120000)
    page.wait_for_timeout(5000)
    print("Bain captures", len(bain_data))
    if bain_data:
        d = bain_data[0]
        print("keys", list(d.keys())[:10])
        results = d.get("results") or d.get("jobs") or []
        print("results", len(results) if isinstance(results, list) else d)
        if isinstance(results, list) and results:
            print("sample", json.dumps(results[0], default=str)[:200])
    browser.close()
