#!/usr/bin/env python3
"""Final pass: PCSX/Eightfold, SmartRecruiters, Greenhouse extras."""

from __future__ import annotations

import json
from typing import Any

import requests

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"

TARGETS: dict[str, list[tuple[str, str]]] = {
    "American Express": [("pcsx", "aexp"), ("greenhouse", "americanexpress"), ("smartrecruiters", "AmericanExpress")],
    "Shopify": [("greenhouse", "shopify"), ("ashby", "shopify")],
    "Atlassian": [("greenhouse", "atlassian")],
    "HubSpot": [("greenhouse", "hubspot")],
    "Rippling": [("ashby", "rippling"), ("greenhouse", "rippling")],
    "Retool": [("ashby", "retool"), ("greenhouse", "retool")],
    "Splunk": [("greenhouse", "splunk"), ("smartrecruiters", "Splunk")],
    "Snyk": [("greenhouse", "snyk"), ("ashby", "snyk")],
    "HashiCorp": [("greenhouse", "hashicorp")],
    "Fortinet": [("smartrecruiters", "Fortinet"), ("greenhouse", "fortinet")],
    "SentinelOne": [("greenhouse", "sentinelone")],
    "Walmart (Tech)": [("smartrecruiters", "Walmart"), ("greenhouse", "walmart")],
    "IBM": [("smartrecruiters", "IBM"), ("greenhouse", "ibm")],
    "Cisco": [("smartrecruiters", "Cisco"), ("greenhouse", "cisco")],
    "Dell Technologies": [("smartrecruiters", "Dell"), ("greenhouse", "dell")],
    "SAP": [("smartrecruiters", "SAP")],
    "Lockheed Martin": [("smartrecruiters", "LockheedMartin"), ("greenhouse", "lockheedmartin")],
    "L3Harris": [("smartrecruiters", "L3Harris")],
    "SAIC": [("smartrecruiters", "SAIC")],
    "GE Aerospace": [("smartrecruiters", "GEAerospace")],
    "Electronic Arts (EA)": [("greenhouse", "ea"), ("smartrecruiters", "ElectronicArts")],
    "Activision Blizzard": [("greenhouse", "activisionblizzard"), ("smartrecruiters", "ActivisionBlizzard")],
    "Ford (Tech)": [("smartrecruiters", "Ford")],
    "GM / OnStar": [("smartrecruiters", "GeneralMotors")],
    "John Deere (Tech)": [("smartrecruiters", "JohnDeere")],
    "Etsy": [("greenhouse", "etsy")],
    "Delta Air Lines": [("smartrecruiters", "DeltaAirLines")],
    "Fiserv": [("smartrecruiters", "Fiserv")],
    "Equifax": [("smartrecruiters", "Equifax")],
    "UPS (Tech)": [("smartrecruiters", "UPS")],
    "Norfolk Southern": [("smartrecruiters", "NorfolkSouthern")],
    "General Dynamics": [("smartrecruiters", "GeneralDynamics")],
    "Citadel": [("greenhouse", "citadel"), ("greenhouse", "citadelsecurities")],
    "Two Sigma": [("greenhouse", "twosigma")],
    "Bloomberg": [("greenhouse", "bloomberg")],
    "Fidelity": [("smartrecruiters", "FidelityInvestments")],
    "McKinsey & Company": [("pcsx", "mckinsey")],
    "BCG": [("pcsx", "bcg")],
    "Bain & Company": [("pcsx", "bain")],
    "Deloitte": [("pcsx", "deloitte")],
    "PwC": [("pcsx", "pwc")],
    "EY": [("pcsx", "ey")],
    "KPMG": [("pcsx", "kpmg")],
    "JPMorgan Chase": [("oracle", "jpmc")],
    "Goldman Sachs": [("oracle", "goldmansachs")],
    "Bank of America": [("oracle", "bankofamerica")],
    "Citi": [("oracle", "citi")],
    "Wells Fargo": [("oracle", "wellsfargo")],
    "Intuit": [("greenhouse", "intuit")],
    "Qualcomm": [("greenhouse", "qualcomm")],
    "AMD": [("greenhouse", "amd")],
    "Yelp": [("greenhouse", "yelp")],
    "Weights & Biases": [("greenhouse", "wandb"), ("ashby", "wandb")],
    "Ubisoft": [("smartrecruiters", "Ubisoft")],
    "Warner Bros. Discovery": [("smartrecruiters", "WarnerBrosDiscovery")],
    "NBCUniversal": [("smartrecruiters", "NBCUniversal")],
    "Cox Enterprises": [("smartrecruiters", "CoxEnterprises")],
    "Chick-fil-A (Digital)": [("smartrecruiters", "ChickfilA")],
    "Porsche Digital (Atlanta)": [("smartrecruiters", "Porsche")],
    "Secureworks": [("smartrecruiters", "Secureworks")],
    "Intercontinental Exchange (ICE)": [("smartrecruiters", "ICE")],
    "BAE Systems": [("smartrecruiters", "BAESystems")],
}

EIGHTFOLD_HOSTS = {
    "aexp": "https://aexp.eightfold.ai/api/pcsx/search",
    "mckinsey": "https://mckinsey.eightfold.ai/api/pcsx/search",
    "bcg": "https://bcg.eightfold.ai/api/pcsx/search",
    "bain": "https://bain.eightfold.ai/api/pcsx/search",
    "deloitte": "https://deloitte.eightfold.ai/api/pcsx/search",
    "pwc": "https://pwc.eightfold.ai/api/pcsx/search",
    "ey": "https://ey.eightfold.ai/api/pcsx/search",
    "kpmg": "https://kpmg.eightfold.ai/api/pcsx/search",
}

ORACLE_HOSTS = {
    "jpmc": ("jpmc.fa.oraclecloud.com", "CX_1001"),
    "goldmansachs": ("hdpc.fa.us2.oraclecloud.com", "CX_1"),
    "bankofamerica": ("bankofamerica.taleo.net", None),
    "citi": ("citi.taleo.net", None),
    "wellsfargo": ("wellsfargo.taleo.net", None),
}


def gh(slug: str) -> tuple[bool, int]:
    r = requests.get(f"https://boards-api.greenhouse.io/v1/boards/{slug}/jobs", timeout=15)
    if r.status_code != 200:
        return False, 0
    return True, len((r.json() or {}).get("jobs") or [])


def ashby(slug: str) -> tuple[bool, int]:
    r = requests.get(f"https://api.ashbyhq.com/posting-api/job-board/{slug}", timeout=15)
    if r.status_code != 200:
        return False, 0
    return True, len((r.json() or {}).get("jobs") or [])


def sr(slug: str) -> tuple[bool, int]:
    r = requests.get(
        f"https://api.smartrecruiters.com/v1/companies/{slug}/postings",
        params={"limit": 1},
        timeout=15,
    )
    if r.status_code != 200:
        return False, 0
    return True, int((r.json() or {}).get("totalFound") or 0)


def pcsx(slug: str) -> tuple[bool, int]:
    url = EIGHTFOLD_HOSTS.get(slug)
    if not url:
        return False, 0
    domain = slug + ".com" if slug != "aexp" else "americanexpress.com"
    try:
        r = requests.get(url, params={"domain": domain, "query": "intern", "start": 0, "count": 1}, timeout=20)
        if r.status_code != 200:
            return False, 0
        data = r.json() or {}
        positions = data.get("positions") or data.get("data", {}).get("positions") or []
        total = int(data.get("count") or len(positions) or 0)
        return total > 0 or len(positions) > 0, max(total, len(positions))
    except Exception:
        return False, 0


def oracle(slug: str) -> tuple[bool, int]:
    info = ORACLE_HOSTS.get(slug)
    if not info or not info[1]:
        return False, 0
    host, site = info
    url = f"https://{host}/hcmRestApi/resources/latest/recruitingCEJobRequisitions"
    headers = {
        "User-Agent": UA,
        "Accept": "application/json",
        "ora-irc-cx-userid": "probe",
        "ora-irc-language": "en",
        "content-type": "application/vnd.oracle.adf.resourceitem+json;charset=utf-8",
    }
    params = {
        "onlyData": "true",
        "finder": f"findReqs;siteNumber={site},keyword=intern",
        "limit": 1,
        "offset": 0,
    }
    try:
        r = requests.get(url, params=params, headers=headers, timeout=20)
        if r.status_code != 200:
            return False, 0
        lst = (r.json() or {}).get("items") or [{}]
        reqs = lst[0].get("requisitionList") or []
        return len(reqs) > 0, len(reqs)
    except Exception:
        return False, 0


def main() -> None:
    hits: list[dict[str, Any]] = []
    for company, attempts in TARGETS.items():
        best = None
        for kind, slug in attempts:
            if kind == "greenhouse":
                ok, count = gh(slug)
                row = {"company": company, "type": "greenhouse", "board_token": slug, "count": count}
            elif kind == "ashby":
                ok, count = ashby(slug)
                row = {"company": company, "type": "ashby", "board_slug": slug, "count": count}
            elif kind == "smartrecruiters":
                ok, count = sr(slug)
                row = {"company": company, "type": "smartrecruiters", "company_id": slug, "count": count}
            elif kind == "pcsx":
                ok, count = pcsx(slug)
                if ok:
                    domain = "americanexpress.com" if slug == "aexp" else f"{slug}.com"
                    row = {
                        "company": company,
                        "type": "pcsx",
                        "list_url": EIGHTFOLD_HOSTS[slug],
                        "domain": domain,
                        "query": "intern",
                        "count": count,
                    }
                else:
                    ok = False
                    row = {}
            elif kind == "oracle":
                ok, count = oracle(slug)
                if ok:
                    host, site = ORACLE_HOSTS[slug]
                    row = {
                        "company": company,
                        "type": "oracle_careers",
                        "host": host,
                        "site_number": site,
                        "count": count,
                    }
                else:
                    ok = False
                    row = {}
            else:
                continue
            if ok and count > 0 and (best is None or count > best["count"]):
                best = row
        if best:
            hits.append(best)
            print(f"OK  {company}: {best['type']} ({best['count']})")

    print("\n--- JSON ---")
    print(json.dumps(hits, indent=2))


if __name__ == "__main__":
    main()
