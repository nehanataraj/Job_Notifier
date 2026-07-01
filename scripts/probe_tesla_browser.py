#!/usr/bin/env python3
from playwright.sync_api import sync_playwright

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    ctx = browser.new_context(user_agent=UA)
    page = ctx.new_page()
    page.goto("https://www.tesla.com/careers/search?query=intern", wait_until="networkidle", timeout=90000)
    result = page.evaluate("""async () => {
        const r = await fetch('/cua-api/apps/careers/state');
        return {status: r.status, text: (await r.text()).slice(0, 500)};
    }""")
    print("fetch from page", result)
    # also try full state
    result2 = page.evaluate("""async () => {
        const r = await fetch('https://www.tesla.com/cua-api/apps/careers/state');
        const t = await r.text();
        try { return {status: r.status, json: JSON.parse(t)}; } catch(e) { return {status: r.status, err: t.slice(0,200)}; }
    }""")
    print("full", result2.get("status"))
    if result2.get("json"):
        posts = result2["json"].get("posts") or []
        print("posts", len(posts))
        if posts:
            print("sample", posts[0])
    browser.close()
