#!/usr/bin/env python3
from playwright.sync_api import sync_playwright

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page(user_agent=UA)
    page.goto("https://delta.avature.net/en_US/careers/SearchJobs?keywords=intern", wait_until="domcontentloaded", timeout=120000)
    page.wait_for_timeout(3000)
    for sel in ['button:has-text("ACCEPT ALL")', 'button:has-text("Accept All")', '#onetrust-accept-btn-handler']:
        try:
            page.locator(sel).first.click(timeout=3000)
            break
        except Exception:
            pass
    page.wait_for_timeout(8000)
    rows = page.evaluate("""() => {
        const out = [];
        document.querySelectorAll('a[href*="/job/"], a[href*="JobDetail"], .jobTitle a, h3 a').forEach(a => {
            const t = (a.innerText||'').trim();
            const h = a.href||'';
            if (t && h && t.length > 8) out.push({t,h});
        });
        return out.slice(0,15);
    }""")
    print("rows", len(rows))
    for r in rows[:8]:
        print(" ", r["t"][:60])
        print("   ", r["h"][:80])
    browser.close()
