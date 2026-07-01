#!/usr/bin/env python3
from playwright.sync_api import sync_playwright
import json

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    context = browser.new_context(user_agent=UA)
    page = context.new_page()
    page.goto("https://www.bain.com/careers/find-a-role/", wait_until="domcontentloaded", timeout=120000)
    page.wait_for_timeout(8000)
    resp = context.request.get(
        "https://www.bain.com/en/api/jobsearch/keyword/get?start=0&results=10&filters=&searchValue=intern"
    )
    print("status", resp.status)
    if resp.ok:
        data = resp.json()
        results = data.get("results") or data.get("jobs") or data.get("data") or []
        print("keys", list(data.keys())[:8])
        print("count", len(results) if isinstance(results, list) else data)
        if isinstance(results, list) and results:
            print("sample", json.dumps(results[0], default=str)[:250])
    else:
        print(resp.text()[:200])
    browser.close()
