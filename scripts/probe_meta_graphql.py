#!/usr/bin/env python3
import json
from playwright.sync_api import sync_playwright

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
captured = []

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page(user_agent=UA)

    def on_request(req):
        if "graphql" in req.url and req.method == "POST":
            try:
                captured.append({"url": req.url, "post": req.post_data_json})
            except Exception:
                pass

    def on_response(resp):
        if "graphql" not in resp.url or resp.status != 200:
            return
        try:
            data = resp.json()
            js = (data.get("data") or {})
            if "job_search" in js or "job_search_with_featured_jobs" in js:
                captured.append({"url": resp.url, "response_keys": list(js.keys()), "body": data})
        except Exception:
            pass

    page.on("request", on_request)
    page.on("response", on_response)
    page.goto("https://www.metacareers.com/jobs?q=intern", wait_until="networkidle", timeout=60000)
    browser.close()

for i, c in enumerate(captured[:6]):
    print(f"\n--- {i} ---")
    if "post" in c:
        print("REQ", json.dumps(c["post"], indent=2)[:1500])
    if "body" in c:
        body = c["body"]
        for key in body.get("data", {}):
            if "job_search" in key:
                val = body["data"][key]
                if isinstance(val, dict):
                    print("RESP", key, "keys", list(val.keys()))
                    listings = val.get("job_listings") or val.get("jobs") or []
                    print(" listings", len(listings))
                    if listings:
                        print(" sample", listings[0])
