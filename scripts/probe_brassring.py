#!/usr/bin/env python3
"""Probe Lockheed BrassRing job search API."""
import re
import requests

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
BASE = "https://sjobs.brassring.com/TGnewUI/Search/Home/Home"
params = {"partnerid": "25037", "siteid": "5014"}

r = requests.get(BASE, params=params, headers={"User-Agent": UA}, timeout=30)
html = r.text
print("status", r.status_code, "len", len(html))

# Look for AJAX endpoints in page
for pat in [
    r"SearchApi/[^\"'\s]+",
    r"JobDetails[^\"'\s]+",
    r"partnerid=\d+&siteid=\d+",
    r'"JobTitle"\s*:\s*"([^"]+)"',
]:
    hits = re.findall(pat, html, re.I)
    if hits:
        print(pat[:30], hits[:5])

# Common BrassRing JSON search
for path in [
    "/TGnewUI/Search/Ajax/JobSearch",
    "/TGnewUI/Search/Ajax/ProcessSort",
    "/TGnewUI/Search/Ajax/JobSearchResult",
]:
    url = f"https://sjobs.brassring.com{path}"
    try:
        rr = requests.post(
            url,
            params=params,
            json={"Keyword": "intern", "PageNumber": 1},
            headers={"User-Agent": UA, "Content-Type": "application/json", "Accept": "application/json"},
            timeout=20,
        )
        print(path, rr.status_code, (rr.headers.get("content-type") or "")[:40], rr.text[:150])
    except Exception as e:
        print(path, "ERR", e)
