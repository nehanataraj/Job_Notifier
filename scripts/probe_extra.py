#!/usr/bin/env python3
"""Second-pass probes: extra slugs + Workday discovery."""

from __future__ import annotations

import json
import re
from typing import Any

import requests

EXTRA_SLUGS: dict[str, list[str]] = {
    "DoorDash": ["doordash", "doordashusa"],
    "Snap": ["snap", "snapinc", "snapchat"],
    "Atlassian": ["atlassian"],
    "Zendesk": ["zendesk"],
    "HubSpot": ["hubspot"],
    "Rippling": ["rippling"],
    "Retool": ["retool"],
    "Weights & Biases": ["wandb", "weightsandbiases"],
    "CrowdStrike": ["crowdstrike"],
    "Palo Alto Networks": ["paloaltonetworks", "paloalto"],
    "SentinelOne": ["sentinelone"],
    "Fortinet": ["fortinet"],
    "Splunk": ["splunk"],
    "Snyk": ["snyk"],
    "Two Sigma": ["twosigma"],
    "Citadel": ["citadel", "citadelsecurities"],
    "HRT": ["hudsonrivertrading"],
    "Bloomberg": ["bloomberg", "bloomberglp"],
    "Shopify": ["shopify"],
    "Unity Technologies": ["unity", "unity3d"],
    "Electronic Arts (EA)": ["ea", "electronicarts"],
    "Activision Blizzard": ["activision", "activisionblizzard"],
    "HashiCorp": ["hashicorp"],
    "Etsy": ["etsy"],
    "Mastercard": ["mastercard"],
    "Nike (Tech)": ["nike"],
    "Walmart (Tech)": ["walmart"],
    "Tesla": ["tesla"],
    "Meta": ["meta", "facebook"],
    "Apple": ["apple"],
    "Zoom": ["zoom", "zoomvideo"],
    "PayPal": ["paypal"],
    "Intuit": ["intuit"],
    "Intel": ["intel"],
    "AMD": ["amd"],
    "Qualcomm": ["qualcomm"],
    "eBay": ["ebay"],
    "Yelp": ["yelp"],
    "Verily": ["verily", "verilylife"],
}

# Known Workday tenants (host, tenant, site guesses)
WORKDAY_CANDIDATES: dict[str, list[tuple[str, str, str]]] = {
    "Meta": [
        ("https://meta.wd1.myworkdayjobs.com", "meta", "External"),
        ("https://meta.wd1.myworkdayjobs.com", "meta", "Facebook"),
    ],
    "Apple": [
        ("https://apple.wd3.myworkdayjobs.com", "apple", "Apple_External_Career_Site"),
        ("https://apple.wd3.myworkdayjobs.com", "apple", "AppleCareerSite"),
    ],
    "Tesla": [
        ("https://tesla.wd3.myworkdayjobs.com", "tesla", "Tesla_External"),
        ("https://tesla.wd3.myworkdayjobs.com", "tesla", "Tesla"),
    ],
    "DoorDash": [
        ("https://doordash.wd5.myworkdayjobs.com", "doordash", "DoorDash"),
    ],
    "Snap": [
        ("https://snap.wd1.myworkdayjobs.com", "snap", "Snap"),
        ("https://snapchat.wd1.myworkdayjobs.com", "snapchat", "Snap"),
    ],
    "Zoom": [
        ("https://zoom.wd5.myworkdayjobs.com", "zoom", "Zoom"),
        ("https://zoom.wd5.myworkdayjobs.com", "zoom", "External"),
    ],
    "PayPal": [
        ("https://paypal.wd1.myworkdayjobs.com", "paypal", "jobs"),
    ],
    "Intuit": [
        ("https://intuit.wd1.myworkdayjobs.com", "intuit", "Intuit"),
    ],
    "Intel": [
        ("https://intel.wd1.myworkdayjobs.com", "intel", "External"),
    ],
    "AMD": [
        ("https://amd.wd1.myworkdayjobs.com", "amd", "External"),
    ],
    "Qualcomm": [
        ("https://qualcomm.wd5.myworkdayjobs.com", "qualcomm", "External"),
    ],
    "eBay": [
        ("https://ebay.wd5.myworkdayjobs.com", "ebay", "apply"),
    ],
    "Yelp": [
        ("https://yelp.wd5.myworkdayjobs.com", "yelp", "Yelp"),
    ],
    "Atlassian": [
        ("https://atlassian.wd5.myworkdayjobs.com", "atlassian", "Atlassian"),
    ],
    "Zendesk": [
        ("https://zendesk.wd1.myworkdayjobs.com", "zendesk", "zendesk"),
    ],
    "HubSpot": [
        ("https://hubspot.wd5.myworkdayjobs.com", "hubspot", "HubSpot"),
    ],
    "Shopify": [
        ("https://shopify.wd3.myworkdayjobs.com", "shopify", "Shopify"),
    ],
    "Goldman Sachs": [
        ("https://goldmansachs.wd1.myworkdayjobs.com", "goldmansachs", "HRSGS"),
        ("https://hdpc.fa.us2.oraclecloud.com", "goldmansachs", "GS"),
    ],
    "JPMorgan Chase": [
        ("https://jpmc.wd1.myworkdayjobs.com", "jpmc", "JPMorganChase"),
        ("https://jpmc.wd5.myworkdayjobs.com", "jpmc", "JPMorganChase"),
    ],
    "Bank of America": [
        ("https://bankofamerica.wd1.myworkdayjobs.com", "bankofamerica", "Bank_of_America_Careers"),
    ],
    "Citi": [
        ("https://citi.wd5.myworkdayjobs.com", "citi", "Citi"),
    ],
    "Wells Fargo": [
        ("https://wellsfargo.wd1.myworkdayjobs.com", "wellsfargo", "WellsFargoJobs"),
    ],
    "Barclays": [
        ("https://barclays.wd3.myworkdayjobs.com", "barclays", "External_Career_Site_Barclays"),
    ],
    "McKinsey & Company": [
        ("https://mckinsey.wd1.myworkdayjobs.com", "mckinsey", "McKinsey"),
    ],
    "BCG": [
        ("https://bcg.wd1.myworkdayjobs.com", "bcg", "BCG"),
    ],
    "Bain & Company": [
        ("https://bain.wd1.myworkdayjobs.com", "bain", "Bain"),
    ],
    "Deloitte": [
        ("https://deloitte.wd1.myworkdayjobs.com", "deloitte", "Deloitte"),
    ],
    "PwC": [
        ("https://pwc.wd3.myworkdayjobs.com", "pwc", "PwC"),
    ],
    "EY": [
        ("https://ey.wd1.myworkdayjobs.com", "ey", "EY"),
    ],
    "KPMG": [
        ("https://kpmg.wd1.myworkdayjobs.com", "kpmg", "KPMG"),
    ],
    "Accenture": [
        ("https://accenture.wd3.myworkdayjobs.com", "accenture", "AccentureCareers"),
    ],
    "Lockheed Martin": [
        ("https://lockheedmartin.wd1.myworkdayjobs.com", "lockheedmartin", "LockheedMartin"),
    ],
    "Northrop Grumman": [
        ("https://ngc.wd1.myworkdayjobs.com", "ngc", "Northrop_Grumman_External_Site"),
    ],
    "Boeing": [
        ("https://boeing.wd1.myworkdayjobs.com", "boeing", "EXTERNAL_CAREERS"),
    ],
    "L3Harris": [
        ("https://l3harris.wd1.myworkdayjobs.com", "l3harris", "L3Harris"),
    ],
    "SAIC": [
        ("https://saic.wd1.myworkdayjobs.com", "saic", "SAIC"),
    ],
    "IBM": [
        ("https://ibm.wd1.myworkdayjobs.com", "ibm", "IBM"),
    ],
    "Dell Technologies": [
        ("https://dell.wd1.myworkdayjobs.com", "dell", "External"),
    ],
    "Cisco": [
        ("https://cisco.wd1.myworkdayjobs.com", "cisco", "Cisco"),
    ],
    "SAP": [
        ("https://sap.wd3.myworkdayjobs.com", "sap", "SAP"),
    ],
    "Delta Air Lines": [
        ("https://delta.wd1.myworkdayjobs.com", "delta", "Delta"),
    ],
    "The Home Depot": [
        ("https://homedepot.wd5.myworkdayjobs.com", "homedepot", "HomeDepot"),
    ],
    "Walmart (Tech)": [
        ("https://walmart.wd5.myworkdayjobs.com", "walmart", "WalmartExternal"),
    ],
    "Nike (Tech)": [
        ("https://nike.wd1.myworkdayjobs.com", "nike", "Nike"),
    ],
    "Ford (Tech)": [
        ("https://ford.wd1.myworkdayjobs.com", "ford", "Ford"),
    ],
    "GM / OnStar": [
        ("https://generalmotors.wd5.myworkdayjobs.com", "generalmotors", "GM"),
    ],
    "UnitedHealth / Optum": [
        ("https://uhg.wd1.myworkdayjobs.com", "uhg", "UHG"),
        ("https://optum.wd1.myworkdayjobs.com", "optum", "Optum"),
    ],
    "Mastercard": [
        ("https://mastercard.wd1.myworkdayjobs.com", "mastercard", "Mastercard"),
    ],
    "Visa": [
        ("https://visa.wd5.myworkdayjobs.com", "visa", "Visa"),
    ],
    "Verily": [
        ("https://verily.wd1.myworkdayjobs.com", "verily", "Verily"),
    ],
    "Electronic Arts (EA)": [
        ("https://ea.wd1.myworkdayjobs.com", "ea", "EA"),
    ],
    "Activision Blizzard": [
        ("https://activision.wd1.myworkdayjobs.com", "activision", "External"),
    ],
    "CrowdStrike": [
        ("https://crowdstrike.wd5.myworkdayjobs.com", "crowdstrike", "CrowdStrike"),
    ],
    "Palo Alto Networks": [
        ("https://paloaltonetworks.wd1.myworkdayjobs.com", "paloaltonetworks", "PaloAltoNetworks"),
    ],
    "Splunk": [
        ("https://splunk.wd5.myworkdayjobs.com", "splunk", "Splunk"),
    ],
    "Fortinet": [
        ("https://fortinet.wd1.myworkdayjobs.com", "fortinet", "Fortinet"),
    ],
    "SentinelOne": [
        ("https://sentinelone.wd1.myworkdayjobs.com", "sentinelone", "SentinelOne"),
    ],
    "Fidelity": [
        ("https://fidelity.wd1.myworkdayjobs.com", "fidelity", "Fidelity"),
    ],
    "American Express": [
        ("https://aexp.wd5.myworkdayjobs.com", "aexp", "AmericanExpress"),
    ],
    "Bloomberg": [
        ("https://bloomberg.wd1.myworkdayjobs.com", "bloomberg", "Bloomberg"),
    ],
    "Two Sigma": [
        ("https://twosigma.wd1.myworkdayjobs.com", "twosigma", "TwoSigma"),
    ],
    "HRT": [
        ("https://hudsonrivertrading.wd1.myworkdayjobs.com", "hudsonrivertrading", "HRT"),
    ],
    "Etsy": [
        ("https://etsy.wd5.myworkdayjobs.com", "etsy", "Etsy"),
    ],
    "UPS (Tech)": [
        ("https://ups.wd1.myworkdayjobs.com", "ups", "UPS"),
    ],
    "Norfolk Southern": [
        ("https://norfolksouthern.wd1.myworkdayjobs.com", "norfolksouthern", "NorfolkSouthern"),
    ],
    "Equifax": [
        ("https://equifax.wd5.myworkdayjobs.com", "equifax", "Equifax"),
    ],
    "Fiserv": [
        ("https://fiserv.wd5.myworkdayjobs.com", "fiserv", "Fiserv"),
    ],
    "SS&C Technologies": [
        ("https://ssctech.wd1.myworkdayjobs.com", "ssctech", "SSCTechnologies"),
    ],
}


def gh(slug: str) -> tuple[bool, int]:
    r = requests.get(f"https://boards-api.greenhouse.io/v1/boards/{slug}/jobs", timeout=20)
    if r.status_code != 200:
        return False, 0
    return True, len((r.json() or {}).get("jobs") or [])


def lever(slug: str) -> tuple[bool, int]:
    r = requests.get(f"https://api.lever.co/v0/postings/{slug}", params={"mode": "json"}, timeout=20)
    if r.status_code != 200 or not isinstance(r.json(), list):
        return False, 0
    return True, len(r.json())


def ashby(slug: str) -> tuple[bool, int]:
    r = requests.get(f"https://api.ashbyhq.com/posting-api/job-board/{slug}", timeout=20)
    if r.status_code != 200:
        return False, 0
    return True, len((r.json() or {}).get("jobs") or [])


def sr(slug: str) -> tuple[bool, int]:
    r = requests.get(
        f"https://api.smartrecruiters.com/v1/companies/{slug}/postings",
        params={"limit": 1},
        timeout=20,
    )
    if r.status_code != 200:
        return False, 0
    return True, int((r.json() or {}).get("totalFound") or 0)


def workday(host: str, tenant: str, site: str) -> tuple[bool, int]:
    host = host.rstrip("/")
    url = f"{host}/wday/cxs/{tenant}/{site}/jobs"
    try:
        r = requests.post(url, json={"appliedFacets": {}, "limit": 1, "offset": 0, "searchText": "intern"}, timeout=20)
        if r.status_code != 200:
            return False, 0
        data = r.json() or {}
        total = int(data.get("total") or 0)
        return total > 0, total
    except Exception:
        return False, 0


def main() -> None:
    hits: list[dict[str, Any]] = []

    for company, slugs in EXTRA_SLUGS.items():
        best = None
        for slug in slugs:
            for kind, fn in [("greenhouse", gh), ("lever", lever), ("ashby", ashby), ("smartrecruiters", sr)]:
                try:
                    ok, count = fn(slug)
                except Exception:
                    continue
                if ok and count > 0:
                    row = {"company": company, "type": kind, "slug": slug, "count": count}
                    if best is None or count > best["count"]:
                        best = row
        if best:
            hits.append(best)
            print(f"API  {best['company']}: {best['type']}:{best['slug']} ({best['count']})")

    for company, candidates in WORKDAY_CANDIDATES.items():
        for host, tenant, site in candidates:
            ok, count = workday(host, tenant, site)
            if ok:
                row = {
                    "company": company,
                    "type": "workday",
                    "host": host,
                    "tenant": tenant,
                    "site": site,
                    "count": count,
                }
                hits.append(row)
                print(f"WD   {company}: {host} tenant={tenant} site={site} ({count})")
                break

    print("\n--- JSON ---")
    print(json.dumps(hits, indent=2))


if __name__ == "__main__":
    main()
