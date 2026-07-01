#!/usr/bin/env python3
import json
import re

import requests

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"

def probe(name, search_url):
    print(f"\n=== {name} ===")
    s = requests.Session()
    s.headers.update({"User-Agent": UA, "Accept": "text/html,application/json"})
    r = s.get(search_url, timeout=30)
    html = r.text or ""
    ref = None
    for pat in [r'"refNum"\s*:\s*"([^"]+)"', r"refNum:\s*'([^']+)'"]:
        m = re.search(pat, html)
        if m:
            ref = m.group(1)
            break
    print("ref", ref, "host", requests.utils.urlparse(r.url).netloc)

    api_paths = set(re.findall(r'"(/api/[^"]+)"', html))
    api_paths |= set(re.findall(r"'(/api/[^']+)'", html))
    print("api paths", list(api_paths)[:12])

    base = f"https://{requests.utils.urlparse(r.url).netloc}"
    locale = "/".join(requests.utils.urlparse(r.url).path.split("/")[:3])  # /global/en or /us/en

    widget_paths = [
        f"{base}/widgets",
        f"{base}{locale}/widgets",
        f"{base}/api/apply/v2/jobs",
        f"{base}{locale}/api/apply/v2/jobs",
    ]
    payload = {
        "refNum": ref,
        "ddoKey": "refineSearch",
        "pageName": "search-results",
        "size": 10,
        "from": 0,
        "keywords": "intern",
        "siteType": "external",
        "lang": "en_global",
        "deviceType": "desktop",
    }
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "ph-refnum": ref or "",
        "Referer": r.url,
    }
    for wp in widget_paths:
        try:
            pr = s.post(wp, json=payload, headers=headers, timeout=20)
            ct = pr.headers.get("content-type", "")
            print(" POST", wp, pr.status_code, ct[:30])
            if "json" in ct:
                d = pr.json()
                print("  keys", list(d.keys())[:8])
                rs = d.get("refineSearch") or d.get("data") or d
                if isinstance(rs, dict):
                    jobs = rs.get("data", {}).get("jobs") if isinstance(rs.get("data"), dict) else rs.get("jobs")
                    if jobs:
                        print("  jobs", len(jobs), jobs[0].get("title") if jobs else "")
        except Exception as e:
            print(" POST err", wp, e)

        try:
            gr = s.get(wp, params={"domain": requests.utils.urlparse(r.url).netloc, "query": "intern", "start": 0, "num": 5}, timeout=20)
            if gr.ok and "json" in (gr.headers.get("content-type") or ""):
                print(" GET ok", wp, gr.text[:100])
        except Exception:
            pass

probe("Yelp", "https://www.yelp.careers/us/en/search-results")
probe("BCG", "https://careers.bcg.com/global/en/search-results")
probe("Cisco", "https://careers.cisco.com/global/en/search-results")
