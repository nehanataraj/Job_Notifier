#!/usr/bin/env python3
from playwright.sync_api import sync_playwright
import requests
import re

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"

print("=== Delta Avature PW ===")
with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page(user_agent=UA)
    page.goto("https://delta.avature.net/en_US/careers/SearchJobs?keywords=intern", wait_until="domcontentloaded", timeout=120000)
    page.wait_for_timeout(8000)
    rows = page.evaluate("""() => {
        const out = [];
        document.querySelectorAll('a').forEach(a => {
            const t = (a.innerText||'').trim();
            const h = a.href||'';
            if (t && h && t.length > 8 && /intern|job|analyst|developer/i.test(t+' '+h)) out.push({t,h});
        });
        return out.slice(0,12);
    }""")
    print("rows", len(rows))
    for r in rows[:6]:
        print(" ", r["t"][:55], r["h"][:70])
    browser.close()

print("\n=== Wells taleo/workday sniff ===")
r = requests.get("https://www.wellsfargojobs.com/en/jobs/", headers={"User-Agent": UA}, timeout=30)
for pat in ["taleo", "wd1", "wd5", "workday", "phenom", "avature", "eightfold"]:
    print(pat, pat.lower() in r.text.lower())

# Wells redirect to workday?
for url in [
    "https://wellsfargo.wd5.myworkdayjobs.com/WellsFargoJobs",
    "https://wellsfargo.wd1.myworkdayjobs.com/WellsFargoJobs",
]:
    try:
        rr = requests.get(url, headers={"User-Agent": UA}, timeout=20, allow_redirects=True)
        print("GET", url, rr.status_code, rr.url[:80])
        site = re.search(r"/([A-Za-z0-9_]+)(?:\?|$)", rr.url)
        if site:
            tenant = url.split("//")[1].split(".")[0]
            host = "/".join(url.split("/")[:3])
            sitename = site.group(1)
            pr = requests.post(
                f"{host}/wday/cxs/{tenant}/{sitename}/jobs",
                json={"appliedFacets": {}, "limit": 2, "offset": 0, "searchText": "intern"},
                headers={"User-Agent": UA, "Accept": "application/json", "Content-Type": "application/json", "Referer": rr.url},
                timeout=20,
            )
            print("  CXS", sitename, pr.status_code, pr.text[:100])
    except Exception as e:
        print(url, e)
