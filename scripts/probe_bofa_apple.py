#!/usr/bin/env python3
import json
import requests

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"

# BofA servlet
for path in [
    "https://careers.bankofamerica.com/services/jobssearchservlet?start=0&rows=50&search=intern",
    "https://careers.bankofamerica.com/services/jobssearchservlet?start=0&rows=50&search=getAllJobs",
    "https://careers.bankofamerica.com/services/mycareerjobssearchservlet?start=0&rows=50&search=intern",
]:
    r = requests.get(path, headers={"User-Agent": UA, "Accept": "application/json"}, timeout=25)
    print(path, r.status_code)
    if r.ok:
        d = r.json()
        jobs = d.get("jobsList") or []
        print(" total", d.get("totalMatches"), "jobs", len(jobs))
        if jobs:
            print(" sample", jobs[0])

from playwright.sync_api import sync_playwright

for name, url, pattern in [
    ("Tesla", "https://www.tesla.com/careers/search?query=intern", "cua-api"),
    ("Apple", "https://jobs.apple.com/en-us/search?search=intern", "api"),
    ("Meta", "https://www.metacareers.com/jobs?q=intern", "graphql"),
    ("EA", "https://www.ea.com/careers/listings", "api"),
]:
    print(f"\n=== PW {name} ===")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        ctx = browser.new_context(user_agent=UA)
        page = ctx.new_page()
        captured = []
        def on_resp(resp):
            u = resp.url
            if pattern in u and resp.status == 200:
                try:
                    if "json" in (resp.headers.get("content-type") or "").lower() or "graphql" in u:
                        captured.append((u, resp.json()))
                except Exception:
                    pass
        page.on("response", on_resp)
        try:
            page.goto(url, wait_until="domcontentloaded", timeout=45000)
            page.wait_for_timeout(5000)
        except Exception as e:
            print("nav", e)
        print("captured", len(captured))
        for u, data in captured[:3]:
            print(" URL", u[:100])
            if isinstance(data, dict):
                print(" keys", list(data.keys())[:10])
                if "jobsList" in data:
                    print(" jobs", len(data["jobsList"]))
                if "data" in data:
                    print(" data keys", list((data.get("data") or {}).keys())[:6])
                if "posts" in data:
                    print(" posts", len(data["posts"]))
        browser.close()
