#!/usr/bin/env python3
"""One-shot probe for backlog items before adding to config."""

from __future__ import annotations

import json
import re

import requests

UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
)
H = {"User-Agent": UA, "Accept": "application/json"}


def wd(host: str, tenant: str, site: str, q: str = "intern") -> dict:
    r = requests.post(
        f"{host.rstrip('/')}/wday/cxs/{tenant}/{site}/jobs",
        json={"appliedFacets": {}, "limit": 3, "offset": 0, "searchText": q},
        headers={**H, "Content-Type": "application/json"},
        timeout=25,
    )
    ok = r.status_code == 200 and "json" in (r.headers.get("content-type") or "")
    total = int((r.json() or {}).get("total") or 0) if ok else None
    return {"ok": ok, "status": r.status_code, "total": total}


def pcsx(url: str, domain: str) -> dict:
    r = requests.get(
        url,
        params={"domain": domain, "query": "intern", "start": 0, "count": 3},
        headers=H,
        timeout=25,
    )
    count = 0
    if r.ok:
        data = r.json() or {}
        inner = data.get("data") if isinstance(data.get("data"), dict) else data
        count = int(inner.get("count") or len(inner.get("positions") or []))
    return {"status": r.status_code, "count": count, "body": (r.text or "")[:120]}


def phenom(base: str, search_url: str, ref: str | None = None) -> dict:
    r = requests.get(search_url, headers={"User-Agent": UA}, timeout=25)
    if not ref:
        m = re.search(r'"refNum"\s*:\s*"([^"]+)"', r.text or "")
        ref = m.group(1) if m else None
    if not ref:
        return {"ref": None, "jobs": 0}
    payload = {
        "refNum": ref,
        "ddoKey": "refineSearch",
        "pageName": "search-results",
        "size": 5,
        "from": 0,
        "keywords": "intern",
        "siteType": "external",
        "lang": "en_global",
        "deviceType": "desktop",
        "jobs": True,
        "counts": True,
        "global": True,
        "pageId": "page20",
    }
    pr = requests.post(
        f"{base.rstrip('/')}/widgets",
        json=payload,
        headers={**H, "Content-Type": "application/json", "Referer": search_url},
        timeout=25,
    )
    jobs = []
    if pr.ok:
        rs = (pr.json() or {}).get("refineSearch") or {}
        jobs = ((rs.get("data") or {}).get("jobs") or [])
    return {"ref": ref, "status": pr.status_code, "jobs": len(jobs)}


def icims(url: str) -> dict:
    r = requests.get(
        url,
        headers={
            "User-Agent": UA,
            "Accept": "text/html,application/xhtml+xml",
            "Accept-Language": "en-US,en;q=0.9",
        },
        timeout=30,
    )
    ids = set(re.findall(r"/jobs/(\d+)", r.text))
    titles = re.findall(
        r'iCIMS_InfoField_JobTitle.*?<a[^>]+href="([^"]+)"[^>]*>([^<]+)</a>',
        r.text,
        re.S | re.I,
    )
    return {"status": r.status_code, "ids": len(ids), "titles": len(titles)}


def sf_html(base: str, path: str) -> dict:
    url = f"{base.rstrip('/')}/{path.lstrip('/')}"
    r = requests.get(url, headers={"User-Agent": UA}, timeout=30)
    titles = re.findall(r'class="[^"]*jobTitle[^"]*"[^>]*>([^<]+)<', r.text, re.I)
    links = re.findall(r'href="([^"]*job[^"]*)"', r.text, re.I)
    return {"status": r.status_code, "titles": len(titles), "links": links[:3]}


def sr(slug: str) -> dict:
    r = requests.get(
        f"https://api.smartrecruiters.com/v1/companies/{slug}/postings",
        params={"limit": 3},
        timeout=20,
    )
    total = int((r.json() or {}).get("totalFound") or 0) if r.ok else -1
    return {"slug": slug, "status": r.status_code, "total": total}


if __name__ == "__main__":
    out: dict = {}

    out["workday"] = {
        "Dell": wd("https://dell.wd1.myworkdayjobs.com", "dell", "External"),
        "PwC": wd("https://pwc.wd3.myworkdayjobs.com", "pwc", "Global_Experienced_Careers"),
        "Equifax": wd("https://equifax.wd5.myworkdayjobs.com", "equifax", "External"),
    }

    out["eightfold"] = {
        "AmEx aexp.com": pcsx("https://aexp.eightfold.ai/api/pcsx/search", "aexp.com"),
        "Activision careers": pcsx(
            "https://careers.activisionblizzard.com/api/pcsx/search",
            "activisionblizzard.com",
        ),
    }

    out["phenom"] = {
        "Porsche": phenom(
            "https://jobs.porsche.com",
            "https://jobs.porsche.com/index.php?ac=search_result&search_criterion_channel=channel_external&search_keyword=intern",
        ),
    }

    out["icims"] = {
        "AMD page": icims("https://careers.amd.com/careers-home/jobs"),
        "AMD search": icims(
            "https://internal-amd.icims.com/jobs/search?ss=1&searchKeyword=intern"
        ),
        "ICE search": icims("https://careers-ice.icims.com/jobs/search?ss=1&searchKeyword=intern"),
        "CFA search": icims(
            "https://careers-chickfila.icims.com/jobs/search?ss=1&searchKeyword=intern"
        ),
    }

    out["successfactors"] = {
        "EY": sf_html("https://careers.ey.com", "ey/search/?q=intern"),
        "SAP": sf_html("https://jobs.sap.com", "search/?q=intern"),
    }

    out["smartrecruiters"] = {
        s: sr(s)
        for s in [
            "NBCUniversal",
            "ComcastNBCUniversal",
            "NBCU",
            "Comcast",
            "Nbcuniversal",
        ]
    }

    # NBCU slug from page
    r = requests.get("https://www.nbcunicareers.com/", headers={"User-Agent": UA}, timeout=25)
    slugs = re.findall(r"smartrecruiters\.com/([A-Za-z0-9_-]+)", r.text)
    out["nbcu_html_slugs"] = list(dict.fromkeys(slugs))[:10]
    for s in out["nbcu_html_slugs"]:
        out["smartrecruiters"][f"html:{s}"] = sr(s)

    print(json.dumps(out, indent=2))
