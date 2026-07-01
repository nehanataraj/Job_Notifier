#!/usr/bin/env python3
from playwright.sync_api import sync_playwright

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"

for url in [
    "https://www.wellsfargojobs.com/en/jobs/",
    "https://www.wellsfargojobs.com/en/jobs/?q=intern",
]:
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(user_agent=UA)
        page.goto(url, wait_until="networkidle", timeout=180000)
        page.wait_for_timeout(10000)
        text = page.inner_text("body")[:500]
        rows = page.evaluate("""() => {
            const out = [];
            document.querySelectorAll('*').forEach(el => {
                const t = (el.innerText||'').trim();
                if (t && t.length > 15 && t.length < 100 && /intern/i.test(t)) out.push(t);
            });
            return [...new Set(out)].slice(0,10);
        }""")
        print(url, "intern texts", rows)
        print("body snippet", text[:200].replace('\\n',' '))
        browser.close()
