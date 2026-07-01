#!/usr/bin/env python3
from playwright.sync_api import sync_playwright
import re

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"

CASES = [
    ("Lockheed BR", "https://sjobs.brassring.com/TGnewUI/Search/Home/Home?partnerid=25037&siteid=5014#home"),
    ("Wells", "https://www.wellsfargojobs.com/en/jobs/search?q=intern"),
    ("Delta careers", "https://www.delta.com/us/en/careers/search-jobs"),
    ("Delta WD", "https://delta.wd1.myworkdayjobs.com/Delta"),
    ("GS campus", "https://higher.gs.com/campus"),
]

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    for name, url in CASES:
        page = browser.new_page(user_agent=UA)
        api_hits = []
        def on_resp(resp):
            u = resp.url
            if resp.status == 200 and any(x in u for x in ("graphql", "search", "job", "requisition", "wday", "brassring", "Ajax")):
                api_hits.append(u)
        page.on("response", on_resp)
        try:
            page.goto(url, wait_until="domcontentloaded", timeout=120000)
            page.wait_for_timeout(8000)
            for _ in range(5):
                page.mouse.wheel(0, 2500)
                page.wait_for_timeout(1200)
            rows = page.evaluate("""() => {
                const out = [];
                document.querySelectorAll('a, [data-automation-id="jobTitle"], .jobTitle, h3, h2').forEach(el => {
                    const title = (el.innerText || '').trim();
                    let href = '';
                    if (el.tagName === 'A') href = el.href || '';
                    else { const a = el.closest('a') || el.querySelector('a'); href = a ? a.href : ''; }
                    if (title && title.length > 8 && title.length < 120) out.push({title, href});
                });
                return out.slice(0, 12);
            }""")
            print(f"\n{name} rows={len(rows)}")
            for r in rows[:5]:
                print(f"  {r['title'][:55]} | {r['href'][:65]}")
            for u in api_hits[:6]:
                print(f"  API {u[:95]}")
        except Exception as e:
            print(name, "ERR", e)
        page.close()
    browser.close()
