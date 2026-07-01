#!/usr/bin/env python3
"""Deep probe iCIMS + other batch-2 endpoints."""

from __future__ import annotations

import json
import re

import requests

UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
)

CASES = {
    "AMD": "https://careers.amd.com/careers-home/jobs",
    "ICE": "https://careers.ice.com/jobs",
    "Chick-fil-A": "https://careers.chick-fil-a.com/corporate/jobs",
    "AmEx": "https://aexp.eightfold.ai/careers",
    "Activision": "https://careers.activisionblizzard.com/",
    "EY": "https://careers.ey.com/ey/search/?q=intern",
    "SAP": "https://jobs.sap.com/search/?q=intern",
    "Porsche": "https://jobs.porsche.com/",
    "NBCU": "https://www.nbcunicareers.com/",
}


def extract(html: str) -> list[str]:
    pats = [
        r"https://[a-z0-9.-]+\.icims\.com[^\"'\s<>]*",
        r"/api/pcsx/search",
        r"eightfold\.ai[^\"'\s<>]*",
        r"api\.smartrecruiters\.com/v1/companies/([^/\"'\s]+)",
        r'"refNum"\s*:\s*"([^"]+)"',
        r"career\.?sap\.com[^\"'\s<>]*",
        r"successfactors[^\"'\s<>]*",
        r"jobReqId|jobPosting|/jobs/\d+",
        r"icims\.com/jobs/search[^\"'\s<>]*",
        r"jobs\.json[^\"'\s<>]*",
    ]
    hits = []
    for p in pats:
        for m in re.finditer(p, html, re.I):
            hits.append(m.group(0) if m.lastindex is None else m.group(0))
    return sorted(set(hits))[:40]


def try_urls(label: str, urls: list[str]) -> None:
    for url in urls:
        try:
            if url.startswith("/"):
                continue
            r = requests.get(
                url if url.startswith("http") else f"https://{url}",
                headers={"User-Agent": UA, "Accept": "application/json,*/*"},
                timeout=25,
            )
            ctype = r.headers.get("content-type", "")
            print(f"{label} {url[:90]} -> {r.status_code} {ctype[:40]} len={len(r.text)}")
            if r.status_code == 200 and ("json" in ctype or r.text.strip().startswith("{")):
                print(" ", r.text[:300])
        except Exception as e:
            print(f"{label} {url[:60]} ERR {e}")


def main() -> None:
    for name, url in CASES.items():
        print(f"\n=== {name} ===")
        r = requests.get(url, headers={"User-Agent": UA}, timeout=30, allow_redirects=True)
        html = r.text
        print("final", r.url, "len", len(html))
        hits = extract(html)
        for h in hits:
            print(" ", h)

        if name == "AMD":
            try_urls("AMD", [
                "https://careers.amd.com/careers-home/jobs?mobile=false&width=1140&height=500&bga=true&needsRedirect=false",
                "https://internal-amd.icims.com/jobs/search?ss=1&searchRelation=keyword_all&searchKeyword=intern",
                "https://careers-amd.icims.com/jobs/search?ss=1&searchKeyword=intern",
            ])
        if name == "ICE":
            try_urls("ICE", [
                "https://careers-ice.icims.com/jobs/search?ss=1&searchKeyword=intern",
                "https://ice.icims.com/jobs/search?ss=1&searchKeyword=intern",
            ])
        if name == "Chick-fil-A":
            try_urls("CFA", [
                "https://careers-chickfila.icims.com/jobs/search?ss=1&searchKeyword=intern",
                "https://chick-fil-a.icims.com/jobs/search?ss=1&searchKeyword=intern",
            ])
        if name == "AmEx":
            try_urls("AmEx", [
                "https://aexp.eightfold.ai/api/pcsx/search?domain=aexp.com&query=intern&start=0&count=5",
                "https://aexp.eightfold.ai/api/pcsx/search?domain=americanexpress.com&query=intern&start=0&count=5",
            ])
        if name == "Activision":
            try_urls("ATVI", [
                "https://activisionblizzard.eightfold.ai/api/pcsx/search?domain=activisionblizzard.com&query=intern&start=0&count=5",
                "https://careers.activisionblizzard.com/widgets",
            ])
        if name == "EY":
            try_urls("EY", [
                "https://careers.ey.com/ey/search/?q=intern&format=rss",
                "https://careers.ey.com/ey/rss?keyword=intern",
            ])
        if name == "SAP":
            try_urls("SAP", [
                "https://jobs.sap.com/search/?q=intern&format=rss",
                "https://jobs.sap.com/rss",
            ])
        if name == "NBCU":
            try_urls("NBCU", [
                "https://api.smartrecruiters.com/v1/companies/NBCUniversal/postings",
                "https://api.smartrecruiters.com/v1/companies/NBCUniversal2/postings",
                "https://api.smartrecruiters.com/v1/companies/nbcuniversal/postings",
            ])


if __name__ == "__main__":
    main()
