#!/usr/bin/env python3
import json
import re
import requests

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"

def phenom_jobs(base, search_url, keywords=""):
    s = requests.Session()
    s.headers.update({"User-Agent": UA})
    r = s.get(search_url, timeout=30)
    ref = re.search(r'"refNum"\s*:\s*"([^"]+)"', r.text or "").group(1)
    payload = {
        "lang": "en_global",
        "deviceType": "desktop",
        "country": "global",
        "pageName": "search-results",
        "size": 50,
        "from": 0,
        "jobs": True,
        "counts": True,
        "all_fields": ["category", "country", "city", "type"],
        "clearAll": False,
        "jdsource": "facets",
        "isSliderEnable": False,
        "pageId": "page20",
        "siteType": "external",
        "keywords": keywords,
        "global": True,
        "selected_fields": {},
        "sort": {"order": "desc", "field": "postedDate"},
        "locationData": {},
        "refNum": ref,
        "ddoKey": "refineSearch",
    }
    pr = s.post(
        f"{base.rstrip('/')}/widgets",
        json=payload,
        headers={"Content-Type": "application/json", "Accept": "application/json", "Referer": r.url},
        timeout=25,
    )
    data = pr.json()
    rs = data.get("refineSearch") or {}
    print("ref", ref, "status", rs.get("status"), "total", rs.get("totalHits") or rs.get("totalCount"))
    jobs = rs.get("data", {}).get("jobs") if isinstance(rs.get("data"), dict) else rs.get("jobs")
    if not jobs:
        # walk structure
        def walk(o, depth=0):
            if depth > 4:
                return
            if isinstance(o, dict):
                if "jobs" in o and isinstance(o["jobs"], list) and o["jobs"]:
                    print(" found jobs at depth", depth, len(o["jobs"]))
                    print(" sample keys", list(o["jobs"][0].keys())[:12])
                    print(" title", o["jobs"][0].get("title"))
                    return True
                for v in o.values():
                    if walk(v, depth + 1):
                        return True
            elif isinstance(o, list):
                for v in o[:3]:
                    if walk(v, depth + 1):
                        return True
        walk(data)
    else:
        print("jobs", len(jobs), jobs[0].get("title"), jobs[0].get("applyUrl") or jobs[0].get("jobUrl"))

for name, base, url, kw in [
    ("Yelp", "https://www.yelp.careers", "https://www.yelp.careers/us/en/search-results", "intern"),
    ("BCG", "https://careers.bcg.com", "https://careers.bcg.com/global/en/search-results", "intern"),
    ("Cisco", "https://careers.cisco.com", "https://careers.cisco.com/global/en/search-results", "intern"),
    ("BAE", "https://jobs.baesystems.com", "https://jobs.baesystems.com/global/en/search-results", ""),
]:
    print(f"\n=== {name} kw={kw!r} ===")
    phenom_jobs(base, url, kw)
