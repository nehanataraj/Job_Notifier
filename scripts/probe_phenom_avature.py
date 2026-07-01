#!/usr/bin/env python3
"""Probe Phenom and Avature JSON endpoints from careers HTML."""

from __future__ import annotations

import json
import re

import requests

UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
)

PAGES = {
    "BCG": "https://careers.bcg.com/global/en/search-results",
    "Yelp": "https://www.yelp.careers/us/en/search-results",
    "Cisco": "https://careers.cisco.com/global/en/search-results",
    "BAE": "https://jobs.baesystems.com/global/en/search-results",
    "WBD": "https://careers.wbd.com/global/en/search-results",
    "Fiserv": "https://careers.fiserv.com/us/en/search-results",
    "UPS": "https://www.jobs-ups.com/us/en/search-results",
    "Porsche": "https://jobs.porsche.com/index.php?ac=search_result&search_criterion_channel=channel_intern",
    "Deloitte": "https://apply.deloitte.com/en_US/careers/SearchJobs/?jobRecordsPerPage=10&jobOffset=0",
    "EA": "https://www.ea.com/careers/listings",
}


def sniff_phenom(html: str, final_url: str) -> list[str]:
    urls: list[str] = []
    for pat in [
        r"https://content-[a-z]+\\.phenompeople\\.com[^\"'\\s]+",
        r"https://cdn\\.phenompeople\\.com[^\"'\\s]+",
        r"/api/[^\"'\\s]+",
        r"phApp\\.refNum\s*=\s*['\"]([^'\"]+)['\"]",
        r"refNum[\"']?\s*[:=]\s*['\"]([A-Z0-9]+)['\"]",
        r"tenantAlias[\"']?\s*[:=]\s*['\"]([^'\"]+)['\"]",
    ]:
        urls.extend(re.findall(pat, html, re.I))
    return urls[:15]


def sniff_avature(html: str) -> list[str]:
    out: list[str] = []
    for pat in [
        r"avature\\.portal\\.id[\"']?\s*[:=]\s*['\"]?(\d+)",
        r"SearchJobs/[^\"'\\s]+",
        r"rest/jobboard[^\"'\\s]+",
    ]:
        out.extend(re.findall(pat, html, re.I))
    return out[:10]


for name, url in PAGES.items():
    print(f"\n=== {name} ===")
    r = requests.get(url, headers={"User-Agent": UA}, timeout=30, allow_redirects=True)
    html = r.text or ""
    print("final", r.url[:90], "status", r.status_code, "len", len(html))
    if "phenom" in html.lower() or "search-results" in r.url:
        sn = sniff_phenom(html, r.url)
        print("phenom hints", sn[:8])
        # common phenom job search API
        ref = None
        for pat in [
            r'"refNum"\s*:\s*"([^"]+)"',
            r"refNum\s*=\s*'([^']+)'",
            r'data-refnum="([^"]+)"',
        ]:
            m = re.search(pat, html, re.I)
            if m:
                ref = m.group(1)
                break
        print("refNum", ref)
        if ref:
            api = (
                "https://careers.bcg.com/api/apply/v2/jobs"
                if "bcg" in r.url
                else None
            )
            candidates = [
                f"https://{requests.utils.urlparse(r.url).netloc}/api/apply/v2/jobs",
                f"https://{requests.utils.urlparse(r.url).netloc}/widgets",
            ]
            for c in candidates:
                try:
                    rr = requests.get(
                        c,
                        params={"domain": requests.utils.urlparse(r.url).netloc, "query": "intern", "location": "United States", "start": 0, "num": 5},
                        headers={"User-Agent": UA, "Accept": "application/json"},
                        timeout=20,
                    )
                    print(" try", c, rr.status_code, (rr.text or "")[:120])
                except Exception as e:
                    print(" try err", c, e)
    if "avature" in html.lower() or "deloitte" in name.lower() or name == "EA":
        print("avature hints", sniff_avature(html))
