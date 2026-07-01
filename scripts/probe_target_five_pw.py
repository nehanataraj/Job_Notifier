#!/usr/bin/env python3
"""Playwright probe for Dell, Bain, McKinsey, Shopify, Rippling."""
from playwright.sync_api import sync_playwright
import re

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"

TARGETS = {
    "Dell": "https://jobs.dell.com/en/search-jobs?k=intern",
    "Bain": "https://www.bain.com/careers/find-a-role/?q=intern",
    "McKinsey": "https://www.mckinsey.com/careers/search-jobs?q=intern",
    "Shopify": "https://www.shopify.com/careers/search?query=intern",
    "Rippling": "https://www.rippling.com/careers?query=intern",
}

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    for name, url in TARGETS.items():
        page = browser.new_page(user_agent=UA)
        apis = []
        def on_resp(r):
            u = r.url
            if r.status == 200 and any(x in u for x in ("wday/cxs", "greenhouse", "lever", "ashby", "pcsx", "avature", "graphql", "search", "jobs", "postings", "widgets")):
                apis.append(u)
        page.on("response", on_resp)
        try:
            page.goto(url, wait_until="domcontentloaded", timeout=120000)
            page.wait_for_timeout(8000)
            for _ in range(4):
                page.mouse.wheel(0, 2000)
                page.wait_for_timeout(1200)
            rows = page.evaluate("""() => {
                const out = [];
                document.querySelectorAll('a').forEach(a => {
                    const t = (a.innerText||'').trim().replace(/\\s+/g,' ');
                    const h = a.href||'';
                    if (t && h && t.length > 10 && t.length < 120) out.push({t,h});
                });
                return out.filter(r => /intern|engineer|analyst|developer|consult|associate|internship/i.test(r.t+' '+r.h)).slice(0,10);
            }""")
            html = page.content()
            wd = re.findall(r"([a-z0-9-]+)\.(wd\d+)\.myworkdayjobs\.com(?:/en-US)?/([A-Za-z0-9_]+)", html, re.I)
            print(f"\n{name}: {len(rows)} filtered links, wd={wd[:2]}")
            for r in rows[:5]:
                print(f"  {r['t'][:55]}")
                print(f"   {r['h'][:75]}")
            for u in apis[:8]:
                if "cookie" not in u.lower():
                    print(f"  API {u[:95]}")
        except Exception as e:
            print(name, "ERR", e)
        page.close()
    browser.close()
