#!/usr/bin/env python3
import re
from playwright.sync_api import sync_playwright

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
TARGETS = {
    "AMD": "https://careers.amd.com/careers-home/jobs",
    "ICE": "https://careers.ice.com/jobs",
    "CFA": "https://careers.chick-fil-a.com/corporate/jobs",
    "Porsche": "https://jobs.porsche.com/index.php?ac=search_result&search_keyword=intern",
}

for name, url in TARGETS.items():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(user_agent=UA)
        page.goto(url, wait_until="networkidle", timeout=90000)
        page.wait_for_timeout(5000)
        html = page.content()
        ids = set(re.findall(r"/jobs/(\d+)", html))
        refs = re.findall(r'"refNum"\s*:\s*"([^"]+)"', html)
        rows = page.evaluate(
            """() => {
            const out = [];
            document.querySelectorAll('a').forEach(el => {
                const t = (el.innerText || '').trim();
                const h = el.href || '';
                if (t && h && /job|career|intern/i.test(h + t) && t.length > 5 && t.length < 200)
                    out.push({t, h});
            });
            return out.slice(0, 10);
        }"""
        )
        print(name, "ids", len(ids), "refNum", refs[:2], "rows", len(rows))
        for x in rows[:4]:
            print(" ", x["t"][:55], x["h"][:75])
        browser.close()
