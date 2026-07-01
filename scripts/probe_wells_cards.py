#!/usr/bin/env python3
from playwright.sync_api import sync_playwright

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page(user_agent=UA)
    page.goto("https://www.wellsfargojobs.com/en/jobs/?q=intern", wait_until="networkidle", timeout=180000)
    page.wait_for_timeout(12000)
    rows = page.evaluate("""() => {
        const out = [];
        document.querySelectorAll('.card-job, .job-listing, .js-live-job-results .card').forEach(card => {
            const a = card.querySelector('a[href]');
            const titleEl = card.querySelector('h2, h3, .job-title, [class*="title"]');
            const title = (titleEl ? titleEl.innerText : (a ? a.innerText : card.innerText)).trim().replace(/\\s+/g,' ').split('\\n')[0];
            const href = a ? a.href : '';
            if (title && href) out.push({title, href});
        });
        return out;
    }""")
    print("cards", len(rows))
    for r in rows[:10]:
        print(r)
    browser.close()
