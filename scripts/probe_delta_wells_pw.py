#!/usr/bin/env python3
from playwright.sync_api import sync_playwright
import re

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"

CASES = {
    "Delta": "https://www.delta.com/us/en/careers",
    "Wells": "https://www.wellsfargojobs.com/en/jobs/?q=intern",
}

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    for name, url in CASES.items():
        page = browser.new_page(user_agent=UA)
        captured = []
        page.on("response", lambda resp: captured.append((resp.url, resp.status)) if any(x in resp.url for x in ("workday", "wday/cxs", "jobs", "search", "brassring", "taleo")) else None)
        try:
            page.goto(url, wait_until="domcontentloaded", timeout=120000)
            page.wait_for_timeout(6000)
            for _ in range(4):
                page.mouse.wheel(0, 2000)
                page.wait_for_timeout(1500)
            html = page.content()
            wd = re.findall(r"([a-z0-9-]+)\.(wd\d+)\.myworkdayjobs\.com(?:/en-US)?/([A-Za-z0-9_]+)", html, re.I)
            links = page.evaluate("""() => {
                const out = [];
                document.querySelectorAll('a').forEach(a => {
                    const t = (a.innerText||'').trim();
                    const h = a.href||'';
                    if (t && h && (/intern/i.test(t) || /job/i.test(h))) out.push({t,h});
                });
                return out.slice(0,8);
            }""")
            print(name, "wd", wd[:3], "links", len(links))
            for l in links[:4]:
                print(" ", l["t"][:45], l["h"][:70])
            interesting = [u for u,s in captured if s==200][:8]
            for u in interesting:
                if "wday" in u or "workday" in u:
                    print("  CAP", u[:100])
        except Exception as e:
            print(name, "ERR", e)
        page.close()
    browser.close()
