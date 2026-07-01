#!/usr/bin/env python3
"""Bruteforce Workday for remaining unknown missed companies."""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from discover_workday import COMPANIES, brute_workday, discover_from_html
from batch_detect_misses import MISSED

# Already in build_config — skip
CONFIGURED = {
    "PwC", "Equifax", "Dell Technologies", "PayPal", "Qualcomm", "Citi",
    "BCG", "Yelp", "Cisco", "Splunk", "BAE Systems", "Warner Bros. Discovery",
    "Fiserv", "UPS (Tech)", "Deloitte", "Electronic Arts (EA)", "Bank of America",
    "Apple", "Meta", "Tesla", "EY", "SAP", "Activision Blizzard", "AMD",
    "Intercontinental Exchange (ICE)", "Chick-fil-A (Digital)", "American Express",
    "Valve", "NASA",
}

TARGETS = [
    "Walmart (Tech)", "Wells Fargo", "KPMG", "Fidelity", "Intuit", "IBM",
    "L3Harris", "Lockheed Martin", "SAIC", "General Dynamics", "GM / OnStar",
    "John Deere (Tech)", "UnitedHealth / Optum", "Ford (Tech)", "HubSpot",
    "Shopify", "Atlassian", "Walmart (Tech)", "Etsy", "Fortinet", "Ubisoft",
    "Cox Enterprises", "Cox Automotive", "JPMorgan Chase", "Goldman Sachs",
    "McKinsey & Company", "GE Aerospace", "Norfolk Southern", "Secureworks",
    "Delta Air Lines", "Porsche Digital (Atlanta)", "NBCUniversal",
]

found: list[dict] = []
for company in TARGETS:
    if company in CONFIGURED:
        continue
    url = MISSED.get(company)
    row = None
    if url:
        row = discover_from_html(company, url)
    if not row and company in COMPANIES:
        row = brute_workday(company, COMPANIES[company])
    if row:
        row["name"] = company
        found.append(row)
        print(f"OK {company}: {row.get('tenant')}/{row.get('site')} total={row.get('count')}")
    else:
        print(f"MISS {company}")

Path("workday_backlog_found.json").write_text(json.dumps(found, indent=2), encoding="utf-8")
print("found", len(found))
