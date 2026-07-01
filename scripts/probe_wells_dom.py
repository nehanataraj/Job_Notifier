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
        document.querySelectorAll('a').forEach(a => {
            const t = (a.innerText||'').trim().replace(/\\s+/g,' ');
            const h = a.href||'';
            if (t && /intern/i.test(t) && h.includes('wellsfargojobs')) out.push({t,h});
        });
        return out;
    }""")
    print("links", len(rows))
    for r in rows[:10]:
        print(r)
    # dump classes containing job
    classes = page.evaluate("""() => {
        const s = new Set();
        document.querySelectorAll('[class]').forEach(el => {
            const c = el.className;
            if (typeof c === 'string' && /job/i.test(c)) s.add(c.split(' ').filter(x=>/job/i.test(x)).join(' '));
        });
        return [...s].slice(0,20);
    }""")
    print("job classes", classes)
    browser.close()
