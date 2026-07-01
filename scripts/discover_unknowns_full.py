#!/usr/bin/env python3
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from batch_detect_misses import MISSED
from discover_workday import COMPANIES, brute_workday, discover_from_html

UNKNOWN = [
    "Atlassian", "Bain & Company", "Bloomberg", "Citadel", "Cox Automotive",
    "Cox Enterprises", "D.E. Shaw", "Dell Technologies", "Equifax", "Etsy",
    "Fidelity", "Fortinet", "GM / OnStar", "General Dynamics", "Goldman Sachs",
    "HashiCorp", "HubSpot", "IBM", "Intuit", "JPMorgan Chase", "John Deere (Tech)",
    "KPMG", "L3Harris", "Lockheed Martin", "PwC", "Retool", "Rippling", "SAIC",
    "SentinelOne", "Shopify", "Snyk", "The Boring Company", "Two Sigma", "Ubisoft",
    "UnitedHealth / Optum", "Walmart (Tech)", "Weights & Biases", "Wells Fargo",
    "Ford (Tech)", "McKinsey & Company", "GE Aerospace", "Delta Air Lines",
    "Secureworks", "Norfolk Southern", "American Express", "Activision Blizzard",
    "NBCUniversal", "Porsche Digital (Atlanta)", "AMD", "Intercontinental Exchange (ICE)",
    "Chick-fil-A (Digital)",
]

def main():
    found = []
    for company in UNKNOWN:
        if company not in MISSED:
            continue
        row = discover_from_html(company, MISSED[company])
        if not row and company in COMPANIES:
            row = brute_workday(company, COMPANIES[company])
        if row:
            row["name"] = company
            found.append(row)
            print(f"OK {company}: {row.get('type','workday')} {row.get('tenant')}/{row.get('site')} count={row.get('count')}")
        else:
            print(f"MISS {company}")
    Path("unknowns_full.json").write_text(json.dumps(found, indent=2), encoding="utf-8")
    print("total", len(found))

if __name__ == "__main__":
    main()
