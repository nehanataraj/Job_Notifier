#!/usr/bin/env python3
"""Probe public job-board APIs for the user's target company list."""

from __future__ import annotations

import json
import re
import sys
from typing import Any

import requests

COMPANIES: dict[str, list[str]] = {
    "Meta": ["meta", "facebook", "metacareers", "fb"],
    "Apple": ["apple", "appleinc"],
    "Tesla": ["tesla", "teslamotors"],
    "Neuralink": ["neuralink"],
    "The Boring Company": ["boringcompany", "theboringcompany"],
    "Airbnb": ["airbnb"],
    "DoorDash": ["doordash"],
    "Instacart": ["instacart"],
    "Snap": ["snap", "snapchat", "snapinc"],
    "Reddit": ["reddit"],
    "Spotify": ["spotify"],
    "ByteDance / TikTok": ["bytedance", "tiktok", "byteDance"],
    "Intuit": ["intuit"],
    "Qualcomm": ["qualcomm"],
    "Intel": ["intel"],
    "AMD": ["amd"],
    "Zoom": ["zoom", "zoomvideo"],
    "PayPal": ["paypal"],
    "eBay": ["ebay"],
    "Yelp": ["yelp"],
    "Roku": ["roku"],
    "Asana": ["asana"],
    "Box": ["box", "boxinc"],
    "Twilio": ["twilio"],
    "Atlassian": ["atlassian"],
    "Zendesk": ["zendesk"],
    "HubSpot": ["hubspot"],
    "Coinbase": ["coinbase"],
    "Cloudflare": ["cloudflare"],
    "Rippling": ["rippling"],
    "Gusto": ["gusto"],
    "Carta": ["carta"],
    "Retool": ["retool"],
    "Supabase": ["supabase"],
    "Replit": ["replit"],
    "Verkada": ["verkada"],
    "Samsara": ["samsara"],
    "Intercom": ["intercom"],
    "Lattice": ["lattice", "latticehq"],
    "Mixpanel": ["mixpanel"],
    "Modal": ["modal", "modallabs"],
    "Anyscale": ["anyscale"],
    "Weights & Biases": ["wandb", "weightsandbiases", "weights-biases"],
    "Cursor / Anysphere": ["anysphere", "cursor", "cursorai"],
    "Glean": ["glean", "gleanwork"],
    "Harvey AI": ["harvey", "harveyai"],
    "CrowdStrike": ["crowdstrike"],
    "Palo Alto Networks": ["paloaltonetworks", "paloalto"],
    "Okta": ["okta"],
    "Zscaler": ["zscaler"],
    "SentinelOne": ["sentinelone"],
    "Fortinet": ["fortinet"],
    "Splunk": ["splunk"],
    "Snyk": ["snyk"],
    "Rubrik": ["rubrik"],
    "Goldman Sachs": ["goldmansachs", "gs"],
    "JPMorgan Chase": ["jpmorgan", "jpmorganchase", "jpmc"],
    "Bank of America": ["bankofamerica", "bofa"],
    "Citi": ["citi", "citigroup"],
    "Wells Fargo": ["wellsfargo"],
    "Barclays": ["barclays"],
    "Citadel": ["citadel", "citadelsecurities"],
    "Citadel Securities": ["citadelsecurities", "citadel"],
    "Two Sigma": ["twosigma", "twosigmainvestments"],
    "D.E. Shaw": ["deshaw", "deshawgroup"],
    "Jump Trading": ["jumptrading", "jump"],
    "HRT": ["hudsonrivertrading", "hrt"],
    "Akuna Capital": ["akuna", "akunacapital"],
    "Bloomberg": ["bloomberg", "bloomberglp"],
    "Fidelity": ["fidelity", "fidelityinvestments"],
    "American Express": ["americanexpress", "amex"],
    "Point72": ["point72"],
    "McKinsey & Company": ["mckinsey"],
    "BCG": ["bcg", "bostonconsultinggroup"],
    "Bain & Company": ["bain", "bainandcompany"],
    "Deloitte": ["deloitte"],
    "PwC": ["pwc", "pricewaterhousecoopers"],
    "EY": ["ey", "ernstandyoung"],
    "KPMG": ["kpmg", "kpmgus"],
    "Accenture": ["accenture"],
    "Oliver Wyman": ["oliverwyman"],
    "Lockheed Martin": ["lockheedmartin", "lockheed"],
    "Northrop Grumman": ["northropgrumman", "northrop"],
    "Raytheon (RTX)": ["rtx", "raytheon", "raytheontechnologies"],
    "Boeing": ["boeing"],
    "General Dynamics": ["generaldynamics", "gdit"],
    "L3Harris": ["l3harris", "l3harrisinc"],
    "BAE Systems": ["baesystems", "bae"],
    "SAIC": ["saic"],
    "GE Aerospace": ["geaerospace", "ge"],
    "NASA": ["nasa"],
    "Riot Games": ["riotgames", "riot"],
    "Epic Games": ["epicgames", "epic"],
    "Roblox": ["roblox"],
    "Unity Technologies": ["unity", "unitytechnologies"],
    "Electronic Arts (EA)": ["ea", "electronicarts"],
    "Activision Blizzard": ["activision", "activisionblizzard"],
    "Valve": ["valve", "valvesoftware"],
    "Ubisoft": ["ubisoft"],
    "Take-Two Interactive": ["taketwo", "taketwointeractive", "2k"],
    "Disney (Tech)": ["disney", "thewaltdisneycompany"],
    "Warner Bros. Discovery": ["warnerbros", "wbd", "warnerbrothersdiscovery"],
    "NBCUniversal": ["nbcuniversal", "nbcu"],
    "Nike (Tech)": ["nike"],
    "Walmart (Tech)": ["walmart"],
    "Visa": ["visa"],
    "Mastercard": ["mastercard"],
    "Shopify": ["shopify"],
    "Ford (Tech)": ["ford", "fordmotor"],
    "GM / OnStar": ["gm", "generalmotors"],
    "John Deere (Tech)": ["johndeere", "deere"],
    "AT&T (Tech)": ["att", "at&t"],
    "T-Mobile (Tech)": ["tmobile", "t-mobile"],
    "Comcast (Tech)": ["comcast"],
    "UnitedHealth / Optum": ["optum", "unitedhealth", "unitedhealthgroup"],
    "Squarespace": ["squarespace"],
    "Etsy": ["etsy"],
    "Duolingo": ["duolingo"],
    "Braze": ["braze"],
    "MongoDB": ["mongodb"],
    "IBM": ["ibm"],
    "Dell Technologies": ["dell", "delltechnologies"],
    "Cisco": ["cisco"],
    "SAP": ["sap"],
    "Confluent": ["confluent"],
    "HashiCorp": ["hashicorp"],
    "Elastic": ["elastic", "elasticco"],
    "PagerDuty": ["pagerduty"],
    "Delta Air Lines": ["delta", "deltaairlines"],
    "The Home Depot": ["homedepot", "thehomedepot"],
    "NCR Voyix": ["ncr", "ncrvoyix"],
    "Cox Enterprises": ["cox", "coxenterprises"],
    "Cox Automotive": ["coxautomotive"],
    "Fiserv": ["fiserv"],
    "Global Payments": ["globalpayments"],
    "Equifax": ["equifax"],
    "Intercontinental Exchange (ICE)": ["ice", "intercontinentalexchange"],
    "Manhattan Associates": ["manhattanassociates"],
    "Secureworks": ["secureworks"],
    "Cardlytics": ["cardlytics"],
    "Elevance Health": ["elevance", "elevancehealth"],
    "UPS (Tech)": ["ups"],
    "Chick-fil-A (Digital)": ["chickfila", "chick-fil-a"],
    "Norfolk Southern": ["norfolksouthern"],
    "Porsche Digital (Atlanta)": ["porsche", "porschedigital"],
    "SS&C Technologies": ["ssc", "ssctechnologies"],
    "Verily": ["verily", "verilylife"],
    "Wing": ["wing", "wingaviation"],
    "Intrinsic": ["intrinsic", "intrinsicrobotics"],
    "Isomorphic Labs": ["isomorphiclabs", "isomorphic"],
    "Amazon Kuiper": ["amazonkuiper", "kuiper"],
    "Reality Labs": ["realitylabs", "meta"],
}


def gh(slug: str) -> tuple[bool, int]:
    r = requests.get(
        f"https://boards-api.greenhouse.io/v1/boards/{slug}/jobs",
        timeout=20,
    )
    if r.status_code != 200:
        return False, 0
    jobs = (r.json() or {}).get("jobs") or []
    return True, len(jobs)


def lever(slug: str) -> tuple[bool, int]:
    r = requests.get(
        f"https://api.lever.co/v0/postings/{slug}",
        params={"mode": "json"},
        timeout=20,
    )
    if r.status_code != 200:
        return False, 0
    data = r.json()
    if not isinstance(data, list):
        return False, 0
    return True, len(data)


def ashby(slug: str) -> tuple[bool, int]:
    r = requests.get(
        f"https://api.ashbyhq.com/posting-api/job-board/{slug}",
        timeout=20,
    )
    if r.status_code != 200:
        return False, 0
    jobs = (r.json() or {}).get("jobs") or []
    return True, len(jobs)


def sr(slug: str) -> tuple[bool, int]:
    r = requests.get(
        f"https://api.smartrecruiters.com/v1/companies/{slug}/postings",
        params={"limit": 1},
        timeout=20,
    )
    if r.status_code != 200:
        return False, 0
    data = r.json() or {}
    total = int(data.get("totalFound") or 0)
    return True, total


def workable(slug: str) -> tuple[bool, int]:
    r = requests.get(
        f"https://apply.workable.com/{slug}/jobs.md",
        headers={
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            ),
            "Accept": "text/markdown,*/*;q=0.8",
        },
        timeout=20,
    )
    if r.status_code != 200:
        return False, 0
    text = r.text or ""
    n = len(re.findall(r"\[View\]\(https://apply\.workable\.com/[^)]+\)", text))
    return n > 0, n


def main() -> None:
    hits: list[dict[str, Any]] = []
    for company, slugs in COMPANIES.items():
        best: dict[str, Any] | None = None
        for slug in slugs:
            for kind, fn in [
                ("greenhouse", gh),
                ("lever", lever),
                ("ashby", ashby),
                ("smartrecruiters", sr),
                ("workable", workable),
            ]:
                try:
                    ok, count = fn(slug)
                except Exception:
                    continue
                if ok and count > 0:
                    row = {
                        "company": company,
                        "type": kind,
                        "slug": slug,
                        "count": count,
                    }
                    if best is None or count > best["count"]:
                        best = row
        if best:
            hits.append(best)
            print(
                f"OK  {best['company']}: {best['type']}:{best['slug']} ({best['count']})",
                flush=True,
            )
        else:
            print(f"MISS {company}", flush=True)

    print("\n--- JSON ---")
    print(json.dumps(hits, indent=2))


if __name__ == "__main__":
    main()
