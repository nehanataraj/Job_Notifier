#!/usr/bin/env python3
import json, re, requests
from playwright.sync_api import sync_playwright

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"

# Rippling ashby page
r = requests.get("https://jobs.ashbyhq.com/rippling", headers={"User-Agent": UA}, timeout=20)
print("Rippling ashby page", r.status_code, len(r.text))
for pat in [r"posting-api/job-board/([^\"']+)", r'"jobId"', r"window\.__appData", r"ashby"]:
    if re.search(pat, r.text, re.I):
        print("  has", pat)

# Try ashby graphql or alternate
for slug in ["rippling", "Rippling", "ripplinginc"]:
    url = f"https://jobs.ashbyhq.com/api/non-user-graphql?op=ApiJobBoardWithTeams"
    # skip - try embed in open-roles
    pass

r2 = requests.get("https://www.rippling.com/careers/open-roles", headers={"User-Agent": UA}, timeout=25)
print("Rippling open-roles", r2.status_code)
for pat in [r"ashbyhq", r"greenhouse", r"lever", r"workday", r"/api/"]:
    hits = sorted(set(re.findall(pat, r2.text[:200000], re.I)))
    if hits:
        print(" ", pat, hits[:5])

# McKinsey HTML API sniff
r3 = requests.get("https://www.mckinsey.com/careers/search-jobs", headers={"User-Agent": UA}, timeout=25)
apis = sorted(set(re.findall(r'["\'](/[^"\']*api[^"\']*)["\']', r3.text, re.I)))
print("McKinsey api paths", apis[:15])
yello = re.findall(r"yello\.co[^\"'\s]+", r3.text, re.I)
print("McKinsey yello", yello[:5])

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    for name, url in [
        ("Bain", "https://www.bain.com/careers/find-a-role/?q=intern"),
        ("McKinsey", "https://www.mckinsey.com/careers/search-jobs?q=intern"),
        ("Rippling", "https://www.rippling.com/careers/open-roles"),
        ("RipplingAshby", "https://jobs.ashbyhq.com/rippling"),
        ("Shopify", "https://www.shopify.com/careers/search?query=intern"),
    ]:
        page = browser.new_page(user_agent=UA)
        captured = []
        def on_resp(resp):
            if resp.status == 200 and any(x in resp.url for x in ("jobsearch", "api", "ashby", "posting", "search", "jobs")):
                try:
                    if "json" in (resp.headers.get("content-type") or "") or resp.url.endswith(".json"):
                        captured.append((resp.url, resp.json()))
                    else:
                        captured.append((resp.url, None))
                except Exception:
                    captured.append((resp.url, "nonjson"))
        page.on("response", on_resp)
        try:
            page.goto(url, wait_until="domcontentloaded", timeout=120000)
            page.wait_for_timeout(8000)
            print(f"\n{name} captured {len(captured)}")
            for u, data in captured[:6]:
                print(" ", u[:90])
                if isinstance(data, dict):
                    print("   keys", list(data.keys())[:6])
                    for k in ("results", "jobs", "positions", "data"):
                        if k in data:
                            v = data[k]
                            print(f"   {k} len", len(v) if hasattr(v, "__len__") else type(v))
            rows = page.evaluate("""() => {
                const out = [];
                document.querySelectorAll('a[href]').forEach(a => {
                    const t=(a.innerText||'').trim();
                    const h=a.href||'';
                    if (t && h && t.length>8 && t.length<100) out.push({t,h});
                });
                return out.filter(r => /intern|engineer|analyst|consult|associate|software|developer/i.test(r.t)).slice(0,6);
            }""")
            for row in rows[:4]:
                print(f"  JOB {row['t'][:50]} | {row['h'][:70]}")
        except Exception as e:
            print(name, "ERR", e)
        page.close()
    browser.close()
