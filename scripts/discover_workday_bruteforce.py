#!/usr/bin/env python3
"""Brute-force Workday tenant guesses for unknown companies."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parent))
from batch_detect_misses import MISSED

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"

# slug guesses per company
GUESSES: dict[str, list[tuple[str, str]]] = {
    "Walmart (Tech)": [("walmart", "WalmartExternal"), ("walmart", "External"), ("walmart", "Careers")],
    "Dell Technologies": [("dell", "External"), ("dell", "Dell"), ("delltechnologies", "External")],
    "Wells Fargo": [("wellsfargo", "External"), ("wf", "External"), ("wellsfargojobs", "External")],
    "PwC": [("pwc", "Global_Experienced_Careers"), ("pwc", "External"), ("pwc", "US_Experienced_Careers")],
    "KPMG": [("kpmg", "External"), ("kpmgus", "External"), ("kpmguscareers", "External")],
    "Equifax": [("equifax", "External"), ("equifax", "Careers")],
    "Fidelity": [("fidelity", "External"), ("fmr", "External"), ("fidelityinvestments", "External")],
    "Intuit": [("intuit", "External"), ("intuit", "Intuit")],
    "IBM": [("ibm", "IBM"), ("ibm", "External"), ("ibm", "Search")],
    "L3Harris": [("l3harris", "External"), ("l3harris", "L3Harris")],
    "Lockheed Martin": [("lockheedmartin", "External"), ("lmco", "External")],
    "SAIC": [("saic", "External"), ("saic", "SAIC")],
    "General Dynamics": [("gd", "External"), ("gdit", "External"), ("generaldynamics", "External")],
    "GM / OnStar": [("gm", "External"), ("gm", "Careers"), ("generalmotors", "External")],
    "John Deere (Tech)": [("deere", "External"), ("johndeere", "External")],
    "UnitedHealth / Optum": [("uhg", "External"), ("unitedhealthgroup", "External"), ("optum", "External")],
    "Ford (Tech)": [("ford", "External"), ("ford", "Ford")],
    "HubSpot": [("hubspot", "External")],
    "Atlassian": [("atlassian", "External")],
    "Shopify": [("shopify", "External")],
    "HashiCorp": [("hashicorp", "External")],
    "Retool": [("retool", "External")],
    "Rippling": [("rippling", "External")],
    "SentinelOne": [("sentinelone", "External")],
    "Snyk": [("snyk", "External")],
    "Etsy": [("etsy", "External")],
    "Fortinet": [("fortinet", "External")],
    "Ubisoft": [("ubisoft", "External")],
    "Cox Enterprises": [("cox", "External"), ("coxenterprises", "External")],
    "Cox Automotive": [("cox", "External"), ("coxautoinc", "External")],
}

WD_HOSTS = ["wd1", "wd3", "wd5", "wd12"]


def probe(tenant: str, site: str, wd: str) -> int | None:
    host = f"https://{tenant}.{wd}.myworkdayjobs.com"
    try:
        r = requests.post(
            f"{host}/wday/cxs/{tenant}/{site}/jobs",
            json={"appliedFacets": {}, "limit": 1, "offset": 0, "searchText": "intern"},
            headers={"User-Agent": UA, "Accept": "application/json", "Content-Type": "application/json"},
            timeout=12,
        )
        if r.status_code == 200 and "json" in (r.headers.get("content-type") or ""):
            return int((r.json() or {}).get("total") or 0)
    except Exception:
        pass
    return None


def main() -> None:
    found = []
    companies = list(GUESSES.keys())
    for company in companies:
        if company not in MISSED:
            continue
        for tenant, site in GUESSES[company]:
            for wd in WD_HOSTS:
                total = probe(tenant, site, wd)
                if total is not None:
                    cfg = {
                        "name": company,
                        "type": "workday",
                        "host": f"https://{tenant}.{wd}.myworkdayjobs.com",
                        "tenant": tenant,
                        "site": site,
                        "search_text": "intern",
                        "probe_total": total,
                    }
                    found.append(cfg)
                    print(f"FOUND {company}: {tenant}/{site} on {wd} total={total}")
                    break
            else:
                continue
            break
        else:
            print(f"MISS {company}")

    # GH/ashby slug guesses
    gh_guesses = {
        "Atlassian": "atlassian",
        "HubSpot": "hubspot",
        "Retool": "retool",
        "Rippling": "rippling",
        "SentinelOne": "sentinelone",
        "Snyk": "snyk",
        "HashiCorp": "hashicorp",
        "Etsy": "etsy",
        "Shopify": "shopify",
        "Weights & Biases": "wandb",
    }
    for company, slug in gh_guesses.items():
        for kind, url_tpl, key in [
            ("greenhouse", f"https://boards-api.greenhouse.io/v1/boards/{slug}/jobs", "board_token"),
            ("ashby", f"https://api.ashbyhq.com/posting-api/job-board/{slug}", "board_slug"),
        ]:
            try:
                r = requests.get(url_tpl, headers={"User-Agent": UA}, timeout=12)
                if r.status_code == 200:
                    data = r.json()
                    jobs = data if isinstance(data, list) else (data.get("jobs") or [])
                    if jobs:
                        found.append({"name": company, "type": kind, key: slug, "probe_count": len(jobs)})
                        print(f"FOUND {company}: {kind} {slug} count={len(jobs)}")
                        break
            except Exception:
                pass

    Path("workday_bruteforce.json").write_text(json.dumps(found, indent=2), encoding="utf-8")
    print(f"\nTotal: {len(found)}")


if __name__ == "__main__":
    main()
