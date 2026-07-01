#!/usr/bin/env python3
"""Re-discover Workday/Greenhouse/Ashby embeds for unknown missed companies."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parent))
from batch_detect_misses import MISSED

UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
)

UNKNOWN = [
    "Atlassian", "Bain & Company", "Bloomberg", "Citadel", "Cox Automotive",
    "Cox Enterprises", "D.E. Shaw", "Dell Technologies", "Equifax", "Etsy",
    "Fidelity", "Fortinet", "GM / OnStar", "General Dynamics", "Goldman Sachs",
    "HashiCorp", "HubSpot", "IBM", "Intuit", "JPMorgan Chase", "John Deere (Tech)",
    "KPMG", "L3Harris", "Lockheed Martin", "PwC", "Retool", "Rippling", "SAIC",
    "SentinelOne", "Shopify", "Snyk", "The Boring Company", "Two Sigma", "Ubisoft",
    "UnitedHealth / Optum", "Walmart (Tech)", "Weights & Biases", "Wells Fargo",
]

WD_RE = re.compile(
    r"https://([a-z0-9-]+)\.(wd\d+)\.myworkdayjobs\.com(?:/en-US)?/([A-Za-z][A-Za-z0-9_]+)",
    re.I,
)
GH_RE = re.compile(r"boards\.greenhouse\.io/([a-z0-9_-]+)", re.I)
ASH_RE = re.compile(r"jobs\.ashbyhq\.com/([a-z0-9_-]+)", re.I)
LEV_RE = re.compile(r"jobs\.lever\.co/([a-z0-9_-]+)", re.I)
SR_RE = re.compile(r"smartrecruiters\.com/([A-Za-z0-9_-]+)", re.I)
PCS_RE = re.compile(r"(https://[a-z0-9.-]+/api/pcsx/search)", re.I)
PHENOM_REF = re.compile(r'"refNum"\s*:\s*"([^"]+)"')


def probe_workday(host: str, tenant: str, site: str) -> int | None:
    try:
        r = requests.post(
            f"{host.rstrip('/')}/wday/cxs/{tenant}/{site}/jobs",
            json={"appliedFacets": {}, "limit": 1, "offset": 0, "searchText": "intern"},
            headers={"User-Agent": UA, "Accept": "application/json", "Content-Type": "application/json"},
            timeout=20,
        )
        if r.status_code == 200:
            return int((r.json() or {}).get("total") or 0)
    except Exception:
        pass
    return None


def probe_gh(slug: str) -> int | None:
    try:
        r = requests.get(
            f"https://boards-api.greenhouse.io/v1/boards/{slug}/jobs",
            headers={"User-Agent": UA},
            timeout=20,
        )
        if r.status_code == 200:
            return len((r.json() or {}).get("jobs") or [])
    except Exception:
        pass
    return None


def probe_ash(slug: str) -> int | None:
    try:
        r = requests.get(
            f"https://api.ashbyhq.com/posting-api/job-board/{slug}",
            headers={"User-Agent": UA},
            timeout=20,
        )
        if r.status_code == 200:
            return len((r.json() or {}).get("jobs") or [])
    except Exception:
        pass
    return None


def sniff(company: str, url: str) -> dict:
    out: dict = {"company": company, "url": url}
    try:
        r = requests.get(url, headers={"User-Agent": UA}, timeout=25, allow_redirects=True)
        html = r.text[:400_000]
        out["final_url"] = r.url
    except Exception as e:
        out["error"] = str(e)
        return out

    m = WD_RE.search(html)
    if m:
        host = f"https://{m.group(1)}.{m.group(2)}.myworkdayjobs.com"
        cfg = {"type": "workday", "host": host, "tenant": m.group(1), "site": m.group(3), "search_text": "intern"}
        total = probe_workday(host, m.group(1), m.group(3))
        out["discovery"] = {**cfg, "probe_total": total}
        return out

    for pat, ats, probe_fn, key in [
        (GH_RE, "greenhouse", probe_gh, "board_token"),
        (ASH_RE, "ashby", probe_ash, "board_slug"),
    ]:
        sm = pat.search(html)
        if sm:
            slug = sm.group(1)
            count = probe_fn(slug)
            out["discovery"] = {"type": ats, key: slug, "probe_count": count}
            return out

    sm = SR_RE.search(html)
    if sm:
        slug = sm.group(1)
        out["discovery"] = {"type": "smartrecruiters", "company_id": slug}
        return out

    pm = PCS_RE.search(html)
    if pm:
        dom = urlparse_host(out.get("final_url", url))
        out["discovery"] = {
            "type": "pcsx",
            "list_url": pm.group(1),
            "domain": dom,
            "query": "intern",
        }
        return out

    ref = PHENOM_REF.search(html)
    if ref and "phenom" in html.lower():
        base = re.match(r"(https://[^/]+)", out.get("final_url", url))
        if base:
            out["discovery"] = {
                "type": "phenom",
                "base_url": base.group(1),
                "ref_num": ref.group(1),
                "search_url": out.get("final_url", url),
                "keywords": "intern",
            }
    return out


def urlparse_host(url: str) -> str:
    host = url.split("//", 1)[-1].split("/")[0]
    return host.replace("www.", "").replace("careers.", "")


def main() -> None:
    found = []
    for company in UNKNOWN:
        if company not in MISSED:
            continue
        info = sniff(company, MISSED[company])
        disc = info.get("discovery")
        if disc:
            found.append({**disc, "name": company})
            print(f"FOUND {company}: {disc}")
        else:
            print(f"MISS  {company}: {info.get('error') or info.get('final_url', '')[:60]}")

    Path("workday_unknowns.json").write_text(json.dumps(found, indent=2), encoding="utf-8")
    print(f"\nTotal discoveries: {len(found)}")


if __name__ == "__main__":
    main()
