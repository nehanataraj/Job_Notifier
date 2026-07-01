#!/usr/bin/env python3
import json
import re

import requests

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"


def wd(host, tenant, site):
    r = requests.post(
        f"{host}/wday/cxs/{tenant}/{site}/jobs",
        json={"appliedFacets": {}, "limit": 1, "offset": 0, "searchText": "intern"},
        headers={"User-Agent": UA, "Accept": "application/json", "Content-Type": "application/json"},
        timeout=20,
    )
    ok = r.status_code == 200 and "json" in (r.headers.get("content-type") or "")
    total = r.json().get("total") if ok else None
    print(f"WD {tenant}/{site}", r.status_code, total)
    return ok, total


host = "https://ghr.wd1.myworkdayjobs.com"
for site in [
    "lateral",
    "Bank_of_America_Careers",
    "External",
    "Campus",
    "Students",
    "BOA",
    "GHRCareers",
    "Global",
    "Early_Career",
]:
    wd(host, "ghr", site)

r = requests.get("https://careers.qualcomm.com/careers", headers={"User-Agent": UA}, timeout=25)
print("QCOM html", len(r.text))
for url, domain in [
    ("https://qualcomm.eightfold.ai/api/pcsx/search", "qualcomm.com"),
    ("https://careers.qualcomm.com/api/pcsx/search", "qualcomm.com"),
]:
    rr = requests.get(url, params={"domain": domain, "query": "intern", "start": 0, "count": 3}, timeout=15)
    print("EF", url, rr.status_code, rr.text[:120])

r = requests.get("https://www.valvesoftware.com/en/jobs", headers={"User-Agent": UA}, timeout=20)
print("Valve", r.status_code, len(r.text))
titles = re.findall(r"<h[23][^>]*>([^<]+)</h[23]>", r.text, re.I)
print("valve headings", titles[:10])

r = requests.get(
    "https://apply.deloitte.com/en_US/careers/SearchJobs",
    headers={"User-Agent": UA},
    timeout=25,
)
print("Deloitte", r.status_code)
print("avature", re.findall(r"https://[^\"']*avature[^\"']*", r.text, re.I)[:3])

r = requests.get("https://www.nbcunicareers.com/", headers={"User-Agent": UA}, timeout=20)
for slug in ["NBCUniversal", "nbcuniversal", "NBCU", "nbcu"]:
    rr = requests.get(
        f"https://api.smartrecruiters.com/v1/companies/{slug}/postings",
        params={"limit": 1},
        timeout=15,
    )
    total = rr.json().get("totalFound") if rr.ok else None
    print("SR", slug, rr.status_code, total)

# scrape BofA page for workday
r = requests.get("https://careers.bankofamerica.com/en-us", headers={"User-Agent": UA}, timeout=25)
wd_sites = re.findall(
    r"myworkdayjobs\.com(?:/en-US)?/([A-Za-z][A-Za-z0-9_]+)",
    r.text,
    re.I,
)
print("BofA wd sites in html", list(dict.fromkeys(wd_sites))[:10])

# Activision eightfold
r = requests.get("https://careers.activisionblizzard.com/", headers={"User-Agent": UA}, timeout=25)
for m in re.findall(r"https://[a-z0-9.-]+/api/[^\"'\s]+", r.text, re.I)[:8]:
    print("AB api", m)
