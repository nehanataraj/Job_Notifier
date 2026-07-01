#!/usr/bin/env python3
import json
import re

import requests

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"

SITES = {
    "BCG": ("https://careers.bcg.com", "careers.bcg.com/global/en/search-results"),
    "Yelp": ("https://www.yelp.careers", "www.yelp.careers/us/en/search-results"),
    "Cisco": ("https://careers.cisco.com", "careers.cisco.com/global/en/search-results"),
    "BAE Systems": ("https://jobs.baesystems.com", "jobs.baesystems.com/global/en/search-results"),
    "Warner Bros. Discovery": ("https://careers.wbd.com", "careers.wbd.com/global/en/search-results"),
    "Fiserv": ("https://careers.fiserv.com", "careers.fiserv.com/us/en/search-results"),
    "UPS (Tech)": ("https://www.jobs-ups.com", "www.jobs-ups.com/us/en/search-results"),
}


def refnum_from_html(html: str) -> str | None:
    for pat in [
        r'"refNum"\s*:\s*"([^"]+)"',
        r"refNum\s*[:=]\s*['\"]([A-Z0-9_]+)['\"]",
        r'data-refnum="([^"]+)"',
        r'"refnum"\s*:\s*"([^"]+)"',
    ]:
        m = re.search(pat, html, re.I)
        if m:
            return m.group(1)
    return None


def fetch_widgets(base: str, ref: str, keywords: str = "intern") -> tuple[int, int]:
    url = f"{base.rstrip('/')}/widgets"
    payload = {
        "lang": "en_global",
        "deviceType": "desktop",
        "country": "global",
        "pageName": "search-results",
        "size": 20,
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
    r = requests.post(
        url,
        json=payload,
        headers={"User-Agent": UA, "Content-Type": "application/json", "Accept": "application/json"},
        timeout=25,
    )
    if not r.ok:
        return r.status_code, 0
    data = r.json() or {}
    jobs = (
        (data.get("refineSearch") or {}).get("data") or {}
    ).get("jobs") or data.get("jobs") or []
    if not jobs and isinstance(data.get("refineSearch"), dict):
        jobs = data["refineSearch"].get("jobs") or []
    return r.status_code, len(jobs) if isinstance(jobs, list) else 0


for name, (base, search_path) in SITES.items():
    page = f"https://{search_path}"
    r = requests.get(page, headers={"User-Agent": UA}, timeout=25)
    ref = refnum_from_html(r.text or "")
    print(name, "ref", ref)
    if ref:
        code, n = fetch_widgets(base, ref)
        print(" ", code, "jobs", n)
        if n:
            code2, n2 = fetch_widgets(base, ref, "")
            print("  all jobs", code2, n2)
