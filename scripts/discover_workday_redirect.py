#!/usr/bin/env python3
"""Discover Workday site names via redirect URL parsing."""

from __future__ import annotations

import json
import re
from typing import Any
from urllib.parse import urlparse

import requests

UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)

# slug -> display name
TARGETS: dict[str, str] = {
    "meta": "Meta",
    "apple": "Apple",
    "tesla": "Tesla",
    "intuit": "Intuit",
    "qualcomm": "Qualcomm",
    "amd": "AMD",
    "yelp": "Yelp",
    "atlassian": "Atlassian",
    "hubspot": "HubSpot",
    "rippling": "Rippling",
    "retool": "Retool",
    "wandb": "Weights & Biases",
    "sentinelone": "SentinelOne",
    "fortinet": "Fortinet",
    "splunk": "Splunk",
    "snyk": "Snyk",
    "jpmc": "JPMorgan Chase",
    "goldmansachs": "Goldman Sachs",
    "bankofamerica": "Bank of America",
    "citi": "Citi",
    "wellsfargo": "Wells Fargo",
    "twosigma": "Two Sigma",
    "bloomberg": "Bloomberg",
    "fidelity": "Fidelity",
    "aexp": "American Express",
    "mckinsey": "McKinsey & Company",
    "bcg": "BCG",
    "bain": "Bain & Company",
    "deloitte": "Deloitte",
    "pwc": "PwC",
    "ey": "EY",
    "kpmg": "KPMG",
    "lockheedmartin": "Lockheed Martin",
    "l3harris": "L3Harris",
    "baesystems": "BAE Systems",
    "saic": "SAIC",
    "geaerospace": "GE Aerospace",
    "ea": "Electronic Arts (EA)",
    "activision": "Activision Blizzard",
    "walmart": "Walmart (Tech)",
    "shopify": "Shopify",
    "ford": "Ford (Tech)",
    "generalmotors": "GM / OnStar",
    "johndeere": "John Deere (Tech)",
    "uhg": "UnitedHealth / Optum",
    "optum": "UnitedHealth / Optum",
    "etsy": "Etsy",
    "ibm": "IBM",
    "dell": "Dell Technologies",
    "cisco": "Cisco",
    "sap": "SAP",
    "hashicorp": "HashiCorp",
    "delta": "Delta Air Lines",
    "fiserv": "Fiserv",
    "equifax": "Equifax",
    "ice": "Intercontinental Exchange (ICE)",
    "secureworks": "Secureworks",
    "ups": "UPS (Tech)",
    "norfolksouthern": "Norfolk Southern",
    "gdit": "General Dynamics",
    "citadel": "Citadel",
    "ubisoft": "Ubisoft",
    "wbd": "Warner Bros. Discovery",
    "nbcuniversal": "NBCUniversal",
    "cox": "Cox Enterprises",
    "chickfila": "Chick-fil-A (Digital)",
    "porsche": "Porsche Digital (Atlanta)",
}


def test_cxs(host: str, tenant: str, site: str) -> tuple[bool, int]:
    try:
        r = requests.post(
            f"{host.rstrip('/')}/wday/cxs/{tenant}/{site}/jobs",
            json={"appliedFacets": {}, "limit": 1, "offset": 0, "searchText": "intern"},
            headers={"User-Agent": UA, "Accept": "application/json"},
            timeout=20,
        )
        if r.status_code != 200:
            return False, 0
        return True, int((r.json() or {}).get("total") or 0)
    except Exception:
        return False, 0


def discover(slug: str, company: str) -> dict[str, Any] | None:
    for wd in (1, 3, 5, 12, 103):
        host = f"https://{slug}.wd{wd}.myworkdayjobs.com"
        try:
            r = requests.get(host, headers={"User-Agent": UA}, timeout=15, allow_redirects=True)
            if r.status_code >= 400:
                continue
            parsed = urlparse(r.url)
            if "myworkdayjobs.com" not in parsed.netloc:
                continue
            host = f"{parsed.scheme}://{parsed.netloc}"
            tenant = parsed.netloc.split(".")[0]
            parts = [p for p in parsed.path.split("/") if p]
            # /en-US/tenant/SiteName/...
            site = None
            for i, p in enumerate(parts):
                if p.lower() in ("en-us", "en-gb", "fr-fr") and i + 1 < len(parts):
                    site = parts[i + 1]
                    break
            if not site and len(parts) >= 1 and parts[0] not in ("en-us", "job", "jobs"):
                site = parts[0]
            if not site:
                continue
            ok, count = test_cxs(host, tenant, site)
            if ok:
                return {
                    "company": company,
                    "type": "workday",
                    "host": host,
                    "tenant": tenant,
                    "site": site,
                    "count": count,
                }
        except Exception:
            continue
    return None


def main() -> None:
    hits: list[dict[str, Any]] = []
    for slug, company in TARGETS.items():
        row = discover(slug, company)
        if row:
            hits.append(row)
            print(f"OK  {company}: {row['site']} ({row['count']}) @ {row['host']}")
        else:
            print(f"MISS {company}")

    print("\n--- JSON ---")
    print(json.dumps(hits, indent=2))


if __name__ == "__main__":
    main()
