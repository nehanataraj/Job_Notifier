#!/usr/bin/env python3
import json
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()
    captured = []

    def on_response(resp):
        if "graphql" not in resp.url or resp.status != 200:
            return
        try:
            data = resp.json()
            block = (data.get("data") or {}).get("job_search_with_featured_jobs")
            if block and block.get("all_jobs"):
                captured.append(block)
        except Exception:
            pass

    page.on("response", on_response)
    page.goto("https://www.metacareers.com/jobs?q=intern", wait_until="networkidle", timeout=90000)
    page.wait_for_timeout(3000)
    browser.close()

print("blocks", len(captured))
if captured:
    jobs = captured[0].get("all_jobs") or []
    print("all_jobs", len(jobs))
    if jobs:
        print(json.dumps(jobs[0], indent=2)[:900])
