#!/usr/bin/env python3
import json
from playwright.sync_api import sync_playwright

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"

for url in [
    "https://www.metacareers.com/jobs",
    "https://www.metacareers.com/jobs?q=internship",
]:
    blocks = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(user_agent=UA)

        def on_response(resp):
            if "graphql" not in resp.url or resp.status != 200:
                return
            try:
                data = resp.json()
                js = data.get("data") or {}
                for key, val in js.items():
                    if isinstance(val, dict) and ("all_jobs" in val or "job_listings" in val):
                        blocks.append((key, val))
            except Exception:
                pass

        page.on("response", on_response)
        page.goto(url, wait_until="networkidle", timeout=90000)
        page.wait_for_timeout(4000)
        browser.close()

    print(f"\nURL {url} blocks {len(blocks)}")
    for key, val in blocks:
        jobs = val.get("all_jobs") or val.get("job_listings") or []
        print(" ", key, "jobs", len(jobs))
        if jobs:
            print("  sample", json.dumps(jobs[0], indent=2)[:600])
