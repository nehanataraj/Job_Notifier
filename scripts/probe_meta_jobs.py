#!/usr/bin/env python3
import json
from playwright.sync_api import sync_playwright

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
jobs_data = None


def on_response(resp):
    global jobs_data
    if "graphql" not in resp.url or resp.status != 200:
        return
    try:
        data = resp.json()
        js = data.get("data") or {}
        block = js.get("job_search_with_featured_jobs") or js.get("job_search")
        if block and block.get("all_jobs"):
            jobs_data = block
    except Exception:
        pass


with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page(user_agent=UA)
    page.on("response", on_response)
    page.goto("https://www.metacareers.com/jobs?q=intern", wait_until="networkidle", timeout=90000)
    page.wait_for_timeout(3000)
    browser.close()

if jobs_data:
    all_jobs = jobs_data.get("all_jobs") or []
    print("all_jobs", len(all_jobs))
    if all_jobs:
        print("sample keys", list(all_jobs[0].keys())[:15])
        print("sample", json.dumps(all_jobs[0], indent=2)[:1000])
else:
    print("no jobs captured")
