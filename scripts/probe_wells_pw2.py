#!/usr/bin/env python3
from playwright.sync_api import sync_playwright

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page(user_agent=UA)
    caps = []
    page.on("response", lambda r: caps.append((r.url, r.status)) if r.status == 200 and "wellsfargojobs" in r.url and "json" in (r.headers.get("content-type") or "") else None)
    page.goto("https://www.wellsfargojobs.com/en/jobs/search?q=intern", wait_until="networkidle", timeout=180000)
    page.wait_for_timeout(10000)
    rows = page.evaluate("""() => {
        const out = [];
        document.querySelectorAll('a, h2, h3, [class*="job"], [class*="title"]').forEach(el => {
            const title = (el.innerText || '').trim().replace(/\\s+/g, ' ');
            const href = el.href || (el.closest('a') ? el.closest('a').href : '');
            if (title && title.length > 12 && title.length < 120 && (/intern/i.test(title) || /job/i.test(href)))
                out.push({title, href});
        });
        return out.slice(0, 15);
    }""")
    print("rows", len(rows))
    for r in rows[:8]:
        print(" ", r["title"][:65])
        print("   ", r["href"][:75])
    print("json caps", caps[:8])
    browser.close()
