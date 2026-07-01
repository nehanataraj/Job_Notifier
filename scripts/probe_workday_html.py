#!/usr/bin/env python3
"""Extract Workday tenant/site from careers HTML and test CXS."""

from __future__ import annotations

import re

import requests

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"

PAGES = {
    "Wells Fargo": "https://www.wellsfargojobs.com/",
    "Walmart (Tech)": "https://careers.walmart.com/us/en/home",
    "L3Harris": "https://careers.l3harris.com/en",
    "GM / OnStar": "https://search-careers.gm.com/",
    "UnitedHealth / Optum": "https://careers.unitedhealthgroup.com/",
    "Etsy": "https://careers.etsy.com/",
    "Equifax": "https://careers.equifax.com/",
    "Lockheed Martin": "https://www.lockheedmartinjobs.com/search-jobs",
}


def test_cxs(host: str, tenant: str, site: str) -> int | None:
    r = requests.post(
        f"{host.rstrip('/')}/wday/cxs/{tenant}/{site}/jobs",
        json={"appliedFacets": {}, "limit": 1, "offset": 0, "searchText": "intern"},
        headers={"User-Agent": UA, "Accept": "application/json", "Content-Type": "application/json"},
        timeout=20,
    )
    if r.status_code == 200 and "json" in (r.headers.get("content-type") or "").lower():
        return int((r.json() or {}).get("total") or 0)
    return None


for company, url in PAGES.items():
    r = requests.get(url, headers={"User-Agent": UA}, timeout=25, allow_redirects=True)
    blob = (r.text or "") + " " + r.url
    hosts = set(re.findall(r"https://[a-z0-9-]+\.wd\d+\.myworkdayjobs\.com", blob, re.I))
    sites = re.findall(
        r"[a-z0-9-]+\.wd\d+\.myworkdayjobs\.com(?:/en-US)?/([A-Za-z][A-Za-z0-9_]+)",
        blob,
        re.I,
    )
    print(f"\n{company}: final={r.url[:70]} hosts={list(hosts)[:2]} sites={list(dict.fromkeys(sites))[:5]}")
    for host in hosts:
        tenant = host.split("//")[1].split(".")[0]
        for site in dict.fromkeys(sites):
            if site.lower() in ("en-us", "job", "jobs"):
                continue
            total = test_cxs(host, tenant, site)
            if total is not None:
                print(f"  OK {tenant}/{site} total={total}")
