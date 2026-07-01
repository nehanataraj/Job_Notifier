#!/usr/bin/env python3
from playwright.sync_api import sync_playwright
import json
import re

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"

# Wells: capture JSON responses
print("=== Wells Fargo ===")
with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page(user_agent=UA)
    json_caps = []
    def on_resp(resp):
        ct = resp.headers.get("content-type") or ""
        if resp.status == 200 and "json" in ct:
            try:
                body = resp.json()
                json_caps.append((resp.url, body))
            except Exception:
                pass
    page.on("response", on_resp)
    page.goto("https://www.wellsfargojobs.com/en/jobs/search?q=intern", wait_until="networkidle", timeout=120000)
    page.wait_for_timeout(5000)
    print("json captures", len(json_caps))
    for url, body in json_caps[:5]:
        print(" ", url[:90])
        if isinstance(body, dict):
            print("   keys", list(body.keys())[:8])
            for k in ("jobs", "results", "data", "items", "JobSearchResult"):
                if k in body:
                    v = body[k]
                    print(f"   {k} type", type(v).__name__, "len", len(v) if hasattr(v, "__len__") else "")
    browser.close()

# Lockheed: run keyword search
print("\n=== Lockheed BrassRing ===")
with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page(user_agent=UA)
    page.goto(
        "https://sjobs.brassring.com/TGnewUI/Search/Home/Home?partnerid=25037&siteid=5014",
        wait_until="domcontentloaded",
        timeout=120000,
    )
    page.wait_for_timeout(5000)
    # try fill keyword box
    try:
        page.fill('input[id*="keyword"], input[name*="keyword"], input[placeholder*="Keyword" i]', "intern")
        page.keyboard.press("Enter")
        page.wait_for_timeout(6000)
    except Exception as e:
        print("fill err", e)
    rows = page.evaluate("""() => {
        const out = [];
        document.querySelectorAll('a, span, h2, h3').forEach(el => {
            const title = (el.innerText || '').trim();
            const href = el.href || (el.closest('a') ? el.closest('a').href : '');
            if (title && title.length > 10 && title.length < 100 && /intern|engineer|analyst|developer/i.test(title))
                out.push({title, href});
        });
        return out.slice(0, 10);
    }""")
    print("rows", len(rows))
    for r in rows[:5]:
        print(" ", r["title"][:60], r["href"][:70])
    browser.close()

# Delta: try multiple URLs + workday with referer
print("\n=== Delta ===")
import requests
UA2 = "Mozilla/5.0"
for url in [
    "https://delta.com/careers/search",
    "https://www.delta.com/careers/search",
    "https://delta.avature.net/en_US/careers/SearchJobs",
]:
    try:
        r = requests.get(url, headers={"User-Agent": UA2}, timeout=20, allow_redirects=True)
        wd = re.findall(r"([a-z0-9-]+)\.(wd\d+)\.myworkdayjobs\.com(?:/en-US)?/([A-Za-z0-9_]+)", r.text, re.I)
        print(url, r.status_code, "wd", wd[:2], "len", len(r.text))
    except Exception as e:
        print(url, "ERR", e)

# workday with browser-like headers
for host, tenant, site in [
    ("https://delta.wd1.myworkdayjobs.com", "delta", "Delta"),
    ("https://delta.wd1.myworkdayjobs.com", "delta", "deltajobs"),
]:
    r = requests.post(
        f"{host}/wday/cxs/{tenant}/{site}/jobs",
        json={"appliedFacets": {}, "limit": 3, "offset": 0, "searchText": "intern"},
        headers={
            "User-Agent": UA2,
            "Accept": "application/json",
            "Content-Type": "application/json",
            "Origin": host,
            "Referer": f"{host}/en-US/{site}",
        },
        timeout=20,
    )
    print("WD", site, r.status_code, r.text[:100])
