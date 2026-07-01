#!/usr/bin/env python3
from playwright.sync_api import sync_playwright

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page(user_agent=UA)
    json_hits = []
    page.on("response", lambda r: json_hits.append(r.url) if r.status == 200 and "json" in (r.headers.get("content-type") or "") and "wellsfargo" in r.url else None)
    page.goto("https://www.wellsfargojobs.com/en/jobs/search?q=intern", wait_until="networkidle", timeout=180000)
    page.wait_for_timeout(5000)
    for sel in ['#onetrust-accept-btn-handler', 'button:has-text("Accept")', 'button:has-text("I Accept")']:
        try:
            page.locator(sel).first.click(timeout=3000)
            page.wait_for_timeout(5000)
            break
        except Exception:
            pass
    page.wait_for_timeout(8000)
    rows = page.evaluate("""() => {
        const out = [];
        document.querySelectorAll('a[href*="/job/"], a[href*="jobdetail"], .job-title a, h2 a, h3 a, [data-job-id]').forEach(el => {
            const title = (el.innerText||'').trim().replace(/\\s+/g,' ');
            const href = el.href || (el.closest('a') ? el.closest('a').href : '');
            if (title && title.length > 10 && title.length < 120) out.push({title, href});
        });
        return out.slice(0,15);
    }""")
    print("rows", len(rows))
    for r in rows[:8]:
        print(" ", r["title"][:65])
        print("   ", r["href"][:75])
    print("json", json_hits[:10])
    browser.close()
