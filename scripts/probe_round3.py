#!/usr/bin/env python3
"""Probe all remaining MISSED companies for working feeds."""

from __future__ import annotations

import json
import re
import sys
import uuid
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parent))
from batch_detect_misses import MISSED
from discover_workday import brute_workday, discover_from_html, COMPANIES

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"

REMAINING = sorted(
    c for c in MISSED
    if c not in {s["name"] for s in json.loads((Path(__file__).resolve().parent.parent / "config.json").read_text(encoding="utf-8"))["sources"]}
)

GH_GUESSES: dict[str, list[str]] = {
    "Atlassian": ["atlassian"],
    "Retool": ["retool"],
    "Rippling": ["rippling"],
    "Weights & Biases": ["wandb", "weightsandbiases"],
    "Snyk": ["snyk"],
    "SentinelOne": ["sentinelone"],
    "HashiCorp": ["hashicorp"],
    "Shopify": ["shopify"],
    "Etsy": ["etsy"],
    "Citadel": ["citadel", "citadelsecurities"],
    "Two Sigma": ["twosigma"],
    "Bloomberg": ["bloomberg"],
    "Intuit": ["intuit"],
    "IBM": ["ibm"],
    "Ubisoft": ["ubisoft"],
    "The Boring Company": ["boringcompany", "theboringcompany"],
}

ASH_GUESSES: dict[str, list[str]] = {
    "Rippling": ["rippling"],
    "Retool": ["retool"],
    "Weights & Biases": ["wandb"],
    "Snyk": ["snyk"],
    "Shopify": ["shopify"],
}

SR_GUESSES: dict[str, list[str]] = {
    "Fortinet": ["Fortinet"],
    "L3Harris": ["L3Harris"],
    "SAIC": ["SAIC"],
    "GE Aerospace": ["GEAerospace"],
    "Ford (Tech)": ["Ford"],
    "GM / OnStar": ["GeneralMotors"],
    "John Deere (Tech)": ["JohnDeere"],
    "UnitedHealth / Optum": ["UnitedHealthGroup", "Optum"],
    "Walmart (Tech)": ["Walmart"],
    "NBCUniversal": ["NBCUniversal", "ComcastNBCUniversal"],
    "Norfolk Southern": ["NorfolkSouthern"],
    "Secureworks": ["Secureworks"],
    "Cox Enterprises": ["CoxEnterprises"],
    "Cox Automotive": ["CoxAutomotive"],
    "General Dynamics": ["GeneralDynamics"],
    "Fidelity": ["FidelityInvestments"],
    "Ubisoft": ["Ubisoft"],
    "Porsche Digital (Atlanta)": ["Porsche"],
    "Dell Technologies": ["Dell"],
    "IBM": ["IBM"],
}

PCSX_GUESSES: dict[str, list[tuple[str, str, str]]] = {
    "McKinsey & Company": ("https://mckinsey.eightfold.ai/api/pcsx/search", "mckinsey.com", "intern"),
    "Bain & Company": ("https://bain.eightfold.ai/api/pcsx/search", "bain.com", "intern"),
    "KPMG": ("https://kpmg.eightfold.ai/api/pcsx/search", "kpmg.com", "intern"),
    "American Express": ("https://aexp.eightfold.ai/api/pcsx/search", "aexp.com", "intern"),
}

ORACLE_GUESSES: dict[str, tuple[str, str]] = {
    "KPMG": ("kpmguscareers", "CX_1"),  # probe
}


def gh(slug: str) -> tuple[bool, int, str]:
    r = requests.get(f"https://boards-api.greenhouse.io/v1/boards/{slug}/jobs", headers={"User-Agent": UA}, timeout=15)
    if r.status_code != 200:
        return False, 0, ""
    jobs = (r.json() or {}).get("jobs") or []
    return len(jobs) > 0, len(jobs), (jobs[0].get("title") or "")[:50]


def ash(slug: str) -> tuple[bool, int, str]:
    r = requests.get(f"https://api.ashbyhq.com/posting-api/job-board/{slug}", headers={"User-Agent": UA}, timeout=15)
    if r.status_code != 200:
        return False, 0, ""
    jobs = (r.json() or {}).get("jobs") or []
    return len(jobs) > 0, len(jobs), (jobs[0].get("title") or "")[:50]


def sr(slug: str) -> tuple[bool, int, str]:
    r = requests.get(
        f"https://api.smartrecruiters.com/v1/companies/{slug}/postings",
        params={"limit": 3, "q": "intern"},
        headers={"User-Agent": UA},
        timeout=15,
    )
    if r.status_code != 200:
        return False, 0, ""
    data = r.json() or {}
    content = data.get("content") or []
    total = int(data.get("totalFound") or 0)
    sample = (content[0].get("name") or "")[:50] if content else ""
    return total > 0, total, sample


def pcsx(url: str, domain: str, query: str) -> tuple[bool, int, str]:
    try:
        r = requests.get(url, params={"domain": domain, "query": query, "start": 0, "count": 5}, headers={"User-Agent": UA}, timeout=20)
        if r.status_code != 200:
            return False, 0, ""
        data = r.json() or {}
        inner = data.get("data") if isinstance(data.get("data"), dict) else data
        pos = inner.get("positions") or []
        total = int(inner.get("count") or len(pos))
        sample = (pos[0].get("name") or "")[:50] if pos else ""
        return total > 0 or len(pos) > 0, max(total, len(pos)), sample
    except Exception:
        return False, 0, ""


def phenom_probe(url: str) -> dict | None:
    r = requests.get(url, headers={"User-Agent": UA}, timeout=25, allow_redirects=True)
    ref = re.search(r'"refNum"\s*:\s*"([^"]+)"', r.text)
    if not ref:
        return None
    base = re.match(r"(https://[^/]+)", r.url)
    if not base:
        return None
    base_url = base.group(1)
    payload = {
        "lang": "en_global", "deviceType": "desktop", "country": "global",
        "pageName": "search-results", "size": 3, "from": 0, "jobs": True,
        "keywords": "intern", "global": True, "refNum": ref.group(1),
        "ddoKey": "refineSearch", "siteType": "external", "pageId": "page20",
    }
    pr = requests.post(
        f"{base_url}/widgets", json=payload,
        headers={"User-Agent": UA, "Content-Type": "application/json", "Referer": r.url},
        timeout=25,
    )
    if pr.status_code != 200:
        return None
    jobs = ((pr.json() or {}).get("refineSearch") or {}).get("data", {}).get("jobs") or []
    if not jobs:
        return None
    return {
        "type": "phenom",
        "base_url": base_url,
        "ref_num": ref.group(1),
        "search_url": r.url,
        "keywords": "intern",
        "count": len(jobs),
        "sample": jobs[0].get("title", "")[:50],
    }


def main() -> None:
    found: list[dict] = []
    for company in REMAINING:
        best = None
        url = MISSED.get(company, "")

        # Greenhouse / Ashby
        for slug in GH_GUESSES.get(company, []):
            ok, count, sample = gh(slug)
            if ok and (best is None or count > best.get("count", 0)):
                best = {"name": company, "type": "greenhouse", "board_token": slug, "count": count, "sample": sample}
        for slug in ASH_GUESSES.get(company, []):
            ok, count, sample = ash(slug)
            if ok and (best is None or count > best.get("count", 0)):
                best = {"name": company, "type": "ashby", "board_slug": slug, "count": count, "sample": sample}

        # SmartRecruiters
        for slug in SR_GUESSES.get(company, []):
            ok, count, sample = sr(slug)
            if ok and (best is None or count > best.get("count", 0)):
                best = {"name": company, "type": "smartrecruiters", "company_id": slug, "count": count, "sample": sample}

        # PCSX
        if company in PCSX_GUESSES:
            purl, dom, q = PCSX_GUESSES[company]
            ok, count, sample = pcsx(purl, dom, q)
            if ok and (best is None or count > best.get("count", 0)):
                best = {"name": company, "type": "pcsx", "list_url": purl, "domain": dom, "query": q, "count": count, "sample": sample}

        # Workday HTML + brute
        if not best:
            row = discover_from_html(company, url)
            if row and row.get("count", 0) > 0:
                row["name"] = company
                row["sample"] = ""
                best = row
        if not best and company in COMPANIES:
            row = brute_workday(company, COMPANIES[company])
            if row and row.get("count", 0) > 0:
                row["name"] = company
                best = row

        # Phenom sniff
        if not best:
            p = phenom_probe(url)
            if p:
                p["name"] = company
                best = p

        if best:
            found.append(best)
            print(f"OK  {company}: {best['type']} count={best.get('count')} {best.get('sample','')[:40]}")
        else:
            print(f"MISS {company}")

    Path("round3_found.json").write_text(json.dumps(found, indent=2), encoding="utf-8")
    print(f"\nFound {len(found)} / {len(REMAINING)}")


if __name__ == "__main__":
    main()
