#!/usr/bin/env python3
"""Probe Dell, Bain, McKinsey, Shopify, Rippling (+ verify Lockheed)."""

from __future__ import annotations

import json
import re
import uuid

import requests

UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
)
H = {"User-Agent": UA, "Accept": "application/json"}


def wd(host: str, tenant: str, site: str) -> dict:
    try:
        r = requests.post(
            f"{host.rstrip('/')}/wday/cxs/{tenant}/{site}/jobs",
            json={"appliedFacets": {}, "limit": 3, "offset": 0, "searchText": "intern"},
            headers={**H, "Content-Type": "application/json", "Referer": f"{host}/en-US/{site}"},
            timeout=20,
        )
        ctype = r.headers.get("content-type") or ""
        if r.status_code == 200 and "json" in ctype:
            d = r.json() or {}
            posts = d.get("jobPostings") or []
            return {"ok": True, "total": d.get("total"), "sample": (posts[0].get("title") if posts else "")}
        return {"ok": False, "status": r.status_code, "head": r.text[:100]}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def wd_discover(base: str) -> None:
    try:
        r = requests.get(base, headers={"User-Agent": UA}, timeout=20, allow_redirects=True)
        print(f"  GET {r.url}")
        m = re.search(r"([a-z0-9-]+)\.(wd\d+)\.myworkdayjobs\.com(?:/en-US)?/([A-Za-z0-9_]+)", r.url + r.text[:50000], re.I)
        if m:
            host = f"https://{m.group(1)}.{m.group(2)}.myworkdayjobs.com"
            print(f"  embed {host} tenant={m.group(1)} site={m.group(3)} -> {wd(host, m.group(1), m.group(3))}")
    except Exception as e:
        print(f"  discover err {e}")


def sniff(url: str) -> dict:
    r = requests.get(url, headers={"User-Agent": UA}, timeout=30, allow_redirects=True)
    html = r.text[:600_000]
    out = {"final": r.url, "len": len(html)}
    for pat, key in [
        (r"boards\.greenhouse\.io/([a-z0-9_-]+)", "gh"),
        (r"jobs\.ashbyhq\.com/([a-z0-9_-]+)", "ashby"),
        (r"jobs\.lever\.co/([a-z0-9_-]+)", "lever"),
        (r"([a-z0-9-]+)\.(wd\d+)\.myworkdayjobs\.com(?:/en-US)?/([A-Za-z0-9_]+)", "wd"),
        (r"eightfold\.ai|pcsx/search", "eightfold"),
        (r"avature", "avature"),
        (r"smartrecruiters\.com/([A-Za-z0-9_-]+)", "sr"),
        (r"oraclecloud\.com/hcmUI[^\"'\s]+sites/([^/\"'\s]+)", "oracle_site"),
    ]:
        m = re.search(pat, html, re.I)
        if m:
            out[key] = m.groups() if m.lastindex else True
    return out


def oracle(host: str, site: str, kw: str = "intern") -> dict:
    url = f"https://{host}/hcmRestApi/resources/latest/recruitingCEJobRequisitions"
    params = {
        "onlyData": "true",
        "expand": "requisitionList.workLocation",
        "finder": f"findReqs;siteNumber={site},keyword={kw}",
        "limit": 5,
        "offset": 0,
    }
    headers = {
        **H,
        "ora-irc-cx-userid": str(uuid.uuid4()),
        "ora-irc-language": "en",
        "content-type": "application/vnd.oracle.adf.resourceitem+json;charset=utf-8",
    }
    r = requests.get(url, params=params, headers=headers, timeout=25)
    if r.status_code != 200:
        return {"status": r.status_code}
    reqs = (r.json() or {}).get("items", [{}])[0].get("requisitionList") or []
    return {"count": len(reqs), "sample": (reqs[0].get("Title") if reqs else "")}


def gh(slug: str) -> int:
    r = requests.get(f"https://boards-api.greenhouse.io/v1/boards/{slug}/jobs", timeout=15)
    return len((r.json() or {}).get("jobs") or []) if r.status_code == 200 else -1


def ash(slug: str) -> int:
    r = requests.get(f"https://api.ashbyhq.com/posting-api/job-board/{slug}", timeout=15)
    return len((r.json() or {}).get("jobs") or []) if r.status_code == 200 else -1


def lev(slug: str) -> int:
    r = requests.get(f"https://api.lever.co/v0/postings/{slug}?mode=json", timeout=15)
    return len(r.json()) if r.status_code == 200 and isinstance(r.json(), list) else -1


print("=== DELL ===")
print("sniff jobs.dell.com", sniff("https://jobs.dell.com/"))
for host, tenant, site in [
    ("https://dell.wd1.myworkdayjobs.com", "dell", "External"),
    ("https://dell.wd1.myworkdayjobs.com", "dell", "Dell"),
    ("https://dell.wd1.myworkdayjobs.com", "dell", "DellJobs"),
    ("https://dell.wd1.myworkdayjobs.com", "dell", "Careers"),
    ("https://dell.wd5.myworkdayjobs.com", "dell", "External"),
    ("https://delltechnologies.wd1.myworkdayjobs.com", "delltechnologies", "External"),
]:
    print(f"WD {tenant}/{site}", wd(host, tenant, site))
wd_discover("https://dell.wd1.myworkdayjobs.com/Dell")
wd_discover("https://jobs.dell.com/")

print("\n=== BAIN ===")
print("sniff", sniff("https://www.bain.com/careers/"))
for url, dom in [
    ("https://bain.eightfold.ai/api/pcsx/search", "bain.com"),
    ("https://bainuscareers-bain.icims.com/jobs/search?ss=1&searchKeyword=intern", ""),
]:
    if "pcsx" in url:
        for d in ["bain.com", "bain"]:
            r = requests.get(url, params={"domain": d, "query": "intern", "start": 0, "count": 3}, headers={**H, "Referer": "https://www.bain.com/careers/"}, timeout=20)
            print(f"pcsx domain={d}", r.status_code, r.text[:80] if r.status_code != 200 else len((r.json().get("data") or {}).get("positions") or []))

print("\n=== MCKINSEY ===")
print("sniff", sniff("https://www.mckinsey.com/careers/search-jobs"))
for url in [
    "https://www.mckinsey.com/careers/search-jobs?q=intern",
    "https://mckinsey.avature.net/en_US/careers/SearchJobs/feed/?jobRecordsPerPage=10&jobOffset=0",
]:
    try:
        r = requests.get(url, headers={"User-Agent": UA}, timeout=25)
        print(url.split("?")[0][-50:], r.status_code, len(r.text), "items", r.text.count("<item>"))
    except Exception as e:
        print(url, e)

print("\n=== SHOPIFY ===")
for slug in ["shopify", "shopifycareers", "shopifyinc"]:
    print(f"gh {slug}", gh(slug))
    print(f"ash {slug}", ash(slug))
    print(f"lev {slug}", lev(slug))
print("sniff", sniff("https://www.shopify.com/careers"))

print("\n=== RIPPLING ===")
for slug in ["rippling", "ripplinginc"]:
    print(f"gh {slug}", gh(slug))
    print(f"ash {slug}", ash(slug))
    print(f"lev {slug}", lev(slug))
print("sniff", sniff("https://www.rippling.com/careers"))
