#!/usr/bin/env python3
import json
from playwright.sync_api import sync_playwright

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"

for name, url in [
    ("Tesla", "https://www.tesla.com/careers/search?query=intern"),
    ("Apple", "https://jobs.apple.com/en-us/search?search=intern"),
]:
    print(f"\n=== {name} ===")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        ctx = browser.new_context(user_agent=UA)
        page = ctx.new_page()
        reqs, resps = [], []

        def on_request(req):
            u = req.url
            if any(k in u for k in ("api", "search", "careers", "role", "cua-api", "job")):
                entry = {"url": u, "method": req.method}
                if req.method == "POST":
                    try:
                        entry["post"] = req.post_data_json
                    except Exception:
                        pass
                reqs.append(entry)

        def on_response(resp):
            u = resp.url
            if resp.status != 200:
                return
            if not any(k in u for k in ("api", "search", "careers", "role", "cua-api", "job")):
                return
            try:
                ct = resp.headers.get("content-type", "")
                if "json" in ct:
                    resps.append({"url": u, "data": resp.json()})
            except Exception:
                pass

        page.on("request", on_request)
        page.on("response", on_response)
        page.goto(url, wait_until="networkidle", timeout=90000)
        page.wait_for_timeout(3000)
        browser.close()

    for r in resps[:8]:
        print("RESP", r["url"][:110])
        d = r["data"]
        if isinstance(d, dict):
            print(" ", list(d.keys())[:12])
            for k in ("posts", "jobs", "results", "searchResults", "totalRecords", "res"):
                if k in d:
                    v = d[k]
                    print(f"  {k}", len(v) if isinstance(v, list) else v)
    for r in reqs[:8]:
        if r.get("post"):
            print("REQ", r["url"][:110])
            print(" ", json.dumps(r["post"])[:300])
