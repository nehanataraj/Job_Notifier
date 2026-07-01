#!/usr/bin/env python3
import json
from playwright.sync_api import sync_playwright

UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    ctx = browser.new_context(user_agent=UA)
    page = ctx.new_page()
    captured = []

    def on_response(resp):
        if resp.status != 200 or "json" not in (resp.headers.get("content-type") or ""):
            return
        if "jobs.apple.com" not in resp.url and "apple.com/api" not in resp.url:
            return
        try:
            captured.append((resp.url, resp.json()))
        except Exception:
            pass

    page.on("response", on_response)
    page.goto("https://jobs.apple.com/en-us/search?search=intern", wait_until="networkidle", timeout=90000)
    page.wait_for_timeout(3000)
    # in-page fetch attempts
    for path in ["/api/v1/search?page=1&query=intern", "/api/role/search?page=1&query=intern"]:
        res = page.evaluate(
            """async (path) => {
                const r = await fetch(path, {headers: {Accept: 'application/json'}});
                const t = await r.text();
                return {status: r.status, body: t.slice(0, 400)};
            }""",
            path,
        )
        print("eval", path, res)
    print("captured", len(captured))
    for u, d in captured:
        print(u[:100], list(d.keys())[:10] if isinstance(d, dict) else d)
    browser.close()
