#!/usr/bin/env python3
from playwright.sync_api import sync_playwright

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page(user_agent=UA)
    page.goto(
        "https://www.lockheedmartinjobs.com/search-jobs?k=intern",
        wait_until="domcontentloaded",
        timeout=120000,
    )
    page.wait_for_timeout(12000)
    for _ in range(6):
        page.mouse.wheel(0, 2000)
        page.wait_for_timeout(1500)
    rows = page.evaluate("""() => {
        const out = [];
        document.querySelectorAll('a').forEach(a => {
            const title = (a.innerText || '').trim();
            const href = a.href || '';
            if (title && href && title.length > 12 && /intern|engineer|analyst|developer|program/i.test(title))
                out.push({title, href});
        });
        return out.slice(0, 15);
    }""")
    print("rows", len(rows))
    for r in rows[:8]:
        print(" ", r["title"][:60])
        print("   ", r["href"][:80])
    browser.close()
