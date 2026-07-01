#!/usr/bin/env python3
"""Discover Workday tenants by probing careers URLs and common host patterns."""

from __future__ import annotations

import json
import re
from typing import Any

import requests

UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)

COMPANIES: dict[str, list[str]] = {
    "Apple": ["apple"],
    "Tesla": ["tesla"],
    "Meta": ["meta", "metacareers"],
    "Intuit": ["intuit"],
    "Qualcomm": ["qualcomm"],
    "AMD": ["amd"],
    "Yelp": ["yelp"],
    "Atlassian": ["atlassian"],
    "HubSpot": ["hubspot"],
    "Rippling": ["rippling"],
    "Retool": ["retool"],
    "Weights & Biases": ["wandb"],
    "CrowdStrike": ["crowdstrike"],
    "Palo Alto Networks": ["paloaltonetworks"],
    "SentinelOne": ["sentinelone"],
    "Fortinet": ["fortinet"],
    "Splunk": ["splunk"],
    "Snyk": ["snyk"],
    "JPMorgan Chase": ["jpmc", "jpmorganchase"],
    "Bank of America": ["bankofamerica"],
    "Citi": ["citi"],
    "Wells Fargo": ["wellsfargo"],
    "Two Sigma": ["twosigma"],
    "Bloomberg": ["bloomberg"],
    "Fidelity": ["fidelity"],
    "American Express": ["aexp", "americanexpress"],
    "McKinsey & Company": ["mckinsey"],
    "BCG": ["bcg"],
    "Bain & Company": ["bain"],
    "Deloitte": ["deloitte"],
    "PwC": ["pwc"],
    "EY": ["ey"],
    "KPMG": ["kpmg"],
    "Accenture": ["accenture"],
    "Lockheed Martin": ["lockheedmartin"],
    "L3Harris": ["l3harris"],
    "BAE Systems": ["baesystems"],
    "SAIC": ["saic"],
    "GE Aerospace": ["geaerospace", "ge"],
    "NASA": ["nasajobs", "nasa"],
    "Electronic Arts (EA)": ["ea"],
    "Activision Blizzard": ["activision"],
    "Nike (Tech)": ["nike"],
    "Walmart (Tech)": ["walmart"],
    "Mastercard": ["mastercard"],
    "Shopify": ["shopify"],
    "Ford (Tech)": ["ford"],
    "GM / OnStar": ["generalmotors", "gm"],
    "John Deere (Tech)": ["johndeere"],
    "AT&T (Tech)": ["att"],
    "T-Mobile (Tech)": ["tmobile"],
    "UnitedHealth / Optum": ["uhg", "optum", "unitedhealthgroup"],
    "Etsy": ["etsy"],
    "IBM": ["ibm"],
    "Dell Technologies": ["dell"],
    "Cisco": ["cisco"],
    "SAP": ["sap"],
    "HashiCorp": ["hashicorp"],
    "Delta Air Lines": ["delta"],
    "The Home Depot": ["homedepot"],
    "NCR Voyix": ["ncr"],
    "Fiserv": ["fiserv"],
    "Global Payments": ["globalpayments"],
    "Equifax": ["equifax"],
    "Intercontinental Exchange (ICE)": ["ice"],
    "Manhattan Associates": ["manh", "manhattanassociates"],
    "Secureworks": ["secureworks"],
    "Cardlytics": ["cardlytics"],
    "Elevance Health": ["elevancehealth", "elevance"],
    "UPS (Tech)": ["ups"],
    "Norfolk Southern": ["norfolksouthern"],
    "General Dynamics": ["gdit", "generaldynamics"],
    "Verily": ["verily"],
    "Goldman Sachs": ["goldmansachs"],
    "Citadel": ["citadel"],
    "HRT": ["hudsonrivertrading"],
    "Ubisoft": ["ubisoft"],
    "Warner Bros. Discovery": ["wbd", "warnerbrothersdiscovery"],
    "NBCUniversal": ["nbcuniversal"],
    "Cox Enterprises": ["cox"],
    "Cox Automotive": ["coxautomotive"],
    "Chick-fil-A (Digital)": ["chickfila"],
    "Porsche Digital (Atlanta)": ["porsche"],
}

CAREERS_PAGES: dict[str, str] = {
    "Apple": "https://jobs.apple.com/",
    "Tesla": "https://www.tesla.com/careers/search",
    "Meta": "https://www.metacareers.com/jobs",
    "CrowdStrike": "https://www.crowdstrike.com/careers/",
    "Shopify": "https://www.shopify.com/careers",
    "McKinsey & Company": "https://www.mckinsey.com/careers/search-jobs",
    "JPMorgan Chase": "https://careers.jpmorgan.com/",
    "Goldman Sachs": "https://www.goldmansachs.com/careers/",
    "Deloitte": "https://apply.deloitte.com/",
    "Walmart (Tech)": "https://careers.walmart.com/",
    "Nike (Tech)": "https://jobs.nike.com/",
    "IBM": "https://www.ibm.com/careers/search",
    "SAP": "https://jobs.sap.com/",
    "Lockheed Martin": "https://www.lockheedmartinjobs.com/",
    "Boeing": "https://jobs.boeing.com/",
}


def test_cxs(host: str, tenant: str, site: str) -> tuple[bool, int]:
    host = host.rstrip("/")
    try:
        r = requests.post(
            f"{host}/wday/cxs/{tenant}/{site}/jobs",
            json={"appliedFacets": {}, "limit": 1, "offset": 0, "searchText": "intern"},
            headers={"User-Agent": UA, "Accept": "application/json", "Content-Type": "application/json"},
            timeout=20,
        )
        if r.status_code != 200:
            return False, 0
        total = int((r.json() or {}).get("total") or 0)
        return total > 0, total
    except Exception:
        return False, 0


def discover_from_html(company: str, url: str) -> dict[str, Any] | None:
    try:
        r = requests.get(url, headers={"User-Agent": UA}, timeout=25, allow_redirects=True)
        text = r.text or ""
        final = r.url
        blob = text + " " + final
        hosts = set(re.findall(r"https://[a-z0-9-]+\.wd\d+\.myworkdayjobs\.com", blob, re.I))
        paths = re.findall(
            r"https://[a-z0-9-]+\.wd\d+\.myworkdayjobs\.com(?:/en-US)?/([a-zA-Z0-9_/-]+)",
            blob,
            re.I,
        )
        for host in hosts:
            tenant = host.split("//")[1].split(".")[0]
            for path in paths:
                site = path.split("/")[0]
                if site.lower() in ("en-us", "en", "fr-fr"):
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
            # probe common site names
            for site in [tenant.title(), tenant.upper(), tenant, "External", "Careers", "Jobs"]:
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
        pass
    return None


def brute_workday(company: str, slugs: list[str]) -> dict[str, Any] | None:
    sites_common = [
        "External", "Careers", "Jobs", "Job_Postings", "Professional",
    ]
    for slug in slugs:
        for wd in (1, 3, 5, 12):
            host = f"https://{slug}.wd{wd}.myworkdayjobs.com"
            try:
                r = requests.get(host, headers={"User-Agent": UA}, timeout=12, allow_redirects=True)
                if r.status_code >= 400:
                    continue
                final = r.url
                m = re.search(
                    r"https://([a-z0-9-]+)\.wd\d+\.myworkdayjobs\.com(?:/en-US)?/([a-zA-Z0-9_]+)",
                    final,
                    re.I,
                )
                if m:
                    tenant = m.group(1)
                    site = m.group(2)
                    ok, count = test_cxs(f"https://{tenant}.wd{wd}.myworkdayjobs.com", tenant, site)
                    if ok:
                        return {
                            "company": company,
                            "type": "workday",
                            "host": f"https://{tenant}.wd{wd}.myworkdayjobs.com",
                            "tenant": tenant,
                            "site": site,
                            "count": count,
                        }
                tenant = slug
                for site in sites_common + [slug.title(), slug.upper(), slug]:
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
    seen: set[str] = set()

    for company, url in CAREERS_PAGES.items():
        row = discover_from_html(company, url)
        if row and company not in seen:
            hits.append(row)
            seen.add(company)
            print(f"HTML {company}: {row['tenant']}/{row['site']} ({row['count']})")

    for company, slugs in COMPANIES.items():
        if company in seen:
            continue
        row = brute_workday(company, slugs)
        if row:
            hits.append(row)
            seen.add(company)
            print(f"BRUT {company}: {row['tenant']}/{row['site']} ({row['count']})")

    print("\n--- JSON ---")
    print(json.dumps(hits, indent=2))


if __name__ == "__main__":
    main()
