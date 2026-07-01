#!/usr/bin/env python3
from playwright.sync_api import sync_playwright
import re, requests

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"

PW_TARGETS = {
    "Shopify": "https://www.shopify.com/careers/search?query=intern",
    "Rippling": "https://www.rippling.com/careers?query=intern",
    "Atlassian": "https://www.atlassian.com/company/careers/all-jobs?team=Interns",
    "Intuit": "https://www.intuit.com/careers/search/?query=intern",
    "NBCUniversal": "https://www.nbcunicareers.com/find-a-job",
    "Porsche": "https://jobs.porsche.com/index.php?ac=search_result&search_keyword=intern",
    "Walmart": "https://careers.walmart.com/us/en/results?q=intern",
    "IBM": "https://www.ibm.com/careers/search?field_keyword_05[0]=Intern",
}

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    for name, url in PW_TARGETS.items():
        page = browser.new_page(user_agent=UA)
        caps = []
        page.on("response", lambda r: caps.append(r.url) if r.status == 200 and any(x in r.url for x in ("greenhouse", "lever", "ashby", "workday", "wday", "smartrecruiters", "boards-api", "pcsx", "widgets", "phenom")) else None)
        try:
            page.goto(url, wait_until="domcontentloaded", timeout=120000)
            page.wait_for_timeout(8000)
            rows = page.evaluate("""() => {
                const out = [];
                document.querySelectorAll('a').forEach(a => {
                    const t = (a.innerText||'').trim();
                    const h = a.href||'';
                    if (t && h && t.length > 8 && t.length < 100 && (/intern/i.test(t) || /job/i.test(h))) out.push({t,h});
                });
                return out.slice(0,8);
            }""")
            print(f"\n{name}: {len(rows)} job links")
            for r in rows[:4]:
                print(f"  {r['t'][:50]} | {r['h'][:65]}")
            for u in caps[:5]:
                print(f"  API {u[:90]}")
        except Exception as e:
            print(name, "ERR", e)
        page.close()
    browser.close()

# Porsche phenom ref from HTML
r = requests.get("https://jobs.porsche.com/", headers={"User-Agent": UA}, timeout=20)
ref = re.search(r'"refNum"\s*:\s*"([^"]+)"', r.text)
print("\nPorsche ref", ref.group(1) if ref else None)
