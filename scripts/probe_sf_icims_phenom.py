#!/usr/bin/env python3
"""Probe SuccessFactors JSON, iCIMS HTML scrape, Phenom refs."""

from __future__ import annotations

import json
import re

import requests

UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
)


def amd_scrape() -> None:
    url = "https://careers.amd.com/careers-home/jobs"
    r = requests.get(url, headers={"User-Agent": UA}, timeout=45)
    html = r.text
    # job cards in page
    titles = re.findall(r'class="[^"]*job[^"]*"[^>]*>.*?<a[^>]+href="([^"]+)"[^>]*>([^<]+)</a>', html, re.I | re.S)
    print("AMD title links", len(titles))
    for h, t in titles[:5]:
        print(" ", t.strip()[:60], h[:80])
    # JSON blobs
    for pat in [r"window\.__INITIAL_STATE__\s*=\s*(\{.+?\});", r'"jobs"\s*:\s*(\[.+?\])']:
        m = re.search(pat, html, re.S)
        if m:
            print("AMD json blob", pat.pattern[:30], len(m.group(1)))
    # icims job ids
    ids = re.findall(r"/jobs/(\d+)/", html)
    print("AMD job ids", len(set(ids)), list(set(ids))[:5])


def sf_search(base: str, label: str) -> None:
    urls = [
        f"{base}/services/recruiting/v1/jobs?keyword=intern&limit=5",
        f"{base}/odata/v2/JobRequisition?$format=json&$top=5",
    ]
    for u in urls:
        try:
            r = requests.get(u, headers={"User-Agent": UA, "Accept": "application/json"}, timeout=25)
            print(label, u, r.status_code, (r.headers.get("content-type") or "")[:40], r.text[:200])
        except Exception as e:
            print(label, u, "ERR", e)

    # parse HTML for job links
    search = f"{base}/search/?q=intern" if "sap" in base else f"{base}/ey/search/?q=intern"
    r = requests.get(search, headers={"User-Agent": UA}, timeout=30)
    links = re.findall(r'href="([^"]*job[^"]*)"', r.text, re.I)
    print(label, "html job links", len(links), links[:5])
    titles = re.findall(r'class="[^"]*jobTitle[^"]*"[^>]*>([^<]+)<', r.text, re.I)
    print(label, "jobTitle", len(titles), [t.strip()[:50] for t in titles[:3]])


def phenom(base: str, search_url: str, label: str) -> None:
    r = requests.get(search_url, headers={"User-Agent": UA}, timeout=30)
    ref = re.search(r'"refNum"\s*:\s*"([^"]+)"', r.text)
    print(label, "ref", ref.group(1) if ref else None)
    if not ref:
        return
    payload = {
        "lang": "en_global",
        "deviceType": "desktop",
        "country": "global",
        "pageName": "search-results",
        "size": 5,
        "from": 0,
        "jobs": True,
        "counts": True,
        "keywords": "intern",
        "global": True,
        "refNum": ref.group(1),
        "ddoKey": "refineSearch",
        "siteType": "external",
        "pageId": "page20",
    }
    pr = requests.post(
        f"{base}/widgets",
        json=payload,
        headers={"User-Agent": UA, "Content-Type": "application/json", "Referer": search_url},
        timeout=30,
    )
    print(label, "widgets", pr.status_code)
    if pr.status_code == 200:
        data = pr.json().get("refineSearch") or {}
        jobs = (data.get("data") or {}).get("jobs") or []
        print(label, "jobs", len(jobs), (jobs[0].get("title") if jobs else ""))


def nbcu_sr() -> None:
    r = requests.get("https://www.nbcunicareers.com/", headers={"User-Agent": UA}, timeout=30)
    for pat in [
        r"smartrecruiters\.com/([A-Za-z0-9_-]+)",
        r"companies/([A-Za-z0-9_-]+)/postings",
        r"api\.smartrecruiters\.com[^\"'\s]+",
    ]:
        hits = sorted(set(re.findall(pat, r.text, re.I)))
        if hits:
            print("NBCU", pat[:40], hits[:10])
    for slug in ["NBCUniversal", "ComcastNBCUniversal", "NBCU", "Nbcuniversal", "comcast"]:
        rr = requests.get(
            f"https://api.smartrecruiters.com/v1/companies/{slug}/postings",
            params={"limit": 3, "q": "intern"},
            timeout=20,
        )
        if rr.status_code == 200:
            total = (rr.json() or {}).get("totalFound", 0)
            if total:
                print("NBCU SR", slug, total)


def amex_pcsx() -> None:
    for domain in ["americanexpress.com", "aexp.com", "amex.com"]:
        for headers in [
            {"User-Agent": UA},
            {"User-Agent": UA, "Referer": "https://aexp.eightfold.ai/careers"},
            {"User-Agent": UA, "Origin": "https://aexp.eightfold.ai"},
        ]:
            r = requests.get(
                "https://aexp.eightfold.ai/api/pcsx/search",
                params={"domain": domain, "query": "intern", "start": 0, "count": 3},
                headers=headers,
                timeout=20,
            )
            if r.status_code == 200:
                data = r.json()
                pos = (data.get("data") or data).get("positions") or data.get("positions") or []
                print("AmEx OK", domain, len(pos), headers)
                return
            print("AmEx", domain, r.status_code, headers.get("Referer", ""))


def activision_phenom() -> None:
    phenom("https://careers.activisionblizzard.com", "https://careers.activisionblizzard.com/global/en/search-results", "ATVI")


def main() -> None:
    amd_scrape()
    print()
    sf_search("https://jobs.sap.com", "SAP")
    print()
    sf_search("https://careers.ey.com", "EY")
    print()
    phenom("https://jobs.porsche.com", "https://jobs.porsche.com/index.php?ac=search_result&search_criterion_channel=channel_external&search_keyword=intern", "Porsche")
    print()
    nbcu_sr()
    print()
    amex_pcsx()
    print()
    activision_phenom()


if __name__ == "__main__":
    main()
