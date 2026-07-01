#!/usr/bin/env python3
"""Run ats_detect against all previously-missed companies."""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from ats_detect import detect, probe_endpoint

MISSED: dict[str, str] = {
    "Meta": "https://www.metacareers.com/jobs",
    "Apple": "https://jobs.apple.com/en-us/search",
    "Tesla": "https://www.tesla.com/careers/search",
    "The Boring Company": "https://www.boringcompany.com/careers",
    "Intuit": "https://www.intuit.com/careers/",
    "Qualcomm": "https://careers.qualcomm.com/",
    "AMD": "https://careers.amd.com/careers-home",
    "Yelp": "https://www.yelp.careers/",
    "Atlassian": "https://www.atlassian.com/company/careers/all-jobs",
    "HubSpot": "https://www.hubspot.com/careers",
    "Rippling": "https://www.rippling.com/careers",
    "Retool": "https://retool.com/careers",
    "Weights & Biases": "https://wandb.ai/careers",
    "SentinelOne": "https://www.sentinelone.com/careers/",
    "Fortinet": "https://www.fortinet.com/corporate/careers",
    "Splunk": "https://www.splunk.com/en_us/careers.html",
    "Snyk": "https://snyk.io/careers/",
    "Goldman Sachs": "https://higher.gs.com/campus",
    "JPMorgan Chase": "https://careers.jpmorgan.com/us/en/students/programs",
    "Bank of America": "https://careers.bankofamerica.com/",
    "Citi": "https://jobs.citi.com/",
    "Wells Fargo": "https://www.wellsfargojobs.com/",
    "Citadel": "https://www.citadel.com/careers/",
    "Two Sigma": "https://www.twosigma.com/careers/",
    "D.E. Shaw": "https://www.deshaw.com/careers",
    "Bloomberg": "https://www.bloomberg.com/careers/",
    "Fidelity": "https://jobs.fidelity.com/",
    "American Express": "https://aexp.eightfold.ai/careers",
    "McKinsey & Company": "https://www.mckinsey.com/careers/search-jobs",
    "BCG": "https://careers.bcg.com/",
    "Bain & Company": "https://www.bain.com/careers/",
    "Deloitte": "https://apply.deloitte.com/careers/SearchJobs",
    "PwC": "https://www.pwc.com/us/en/careers.html",
    "EY": "https://careers.ey.com/",
    "KPMG": "https://www.kpmguscareers.com/",
    "Lockheed Martin": "https://www.lockheedmartinjobs.com/search-jobs",
    "General Dynamics": "https://www.gd.com/careers",
    "L3Harris": "https://careers.l3harris.com/",
    "BAE Systems": "https://jobs.baesystems.com/",
    "SAIC": "https://jobs.saic.com/",
    "GE Aerospace": "https://jobs.geaerospace.com/",
    "NASA": "https://www.usajobs.gov/Search/Results?k=NASA",
    "Electronic Arts (EA)": "https://www.ea.com/careers",
    "Activision Blizzard": "https://careers.activisionblizzard.com/",
    "Valve": "https://www.valvesoftware.com/en/jobs",
    "Ubisoft": "https://www.ubisoft.com/en-us/company/careers",
    "Warner Bros. Discovery": "https://careers.wbd.com/",
    "NBCUniversal": "https://www.nbcunicareers.com/",
    "Walmart (Tech)": "https://careers.walmart.com/",
    "Shopify": "https://www.shopify.com/careers",
    "Ford (Tech)": "https://corporate.ford.com/careers.html",
    "GM / OnStar": "https://search-careers.gm.com/",
    "John Deere (Tech)": "https://www.deere.com/en/careers/",
    "UnitedHealth / Optum": "https://careers.unitedhealthgroup.com/",
    "Etsy": "https://careers.etsy.com/",
    "IBM": "https://www.ibm.com/careers/search",
    "Dell Technologies": "https://jobs.dell.com/",
    "Cisco": "https://jobs.cisco.com/",
    "SAP": "https://jobs.sap.com/",
    "HashiCorp": "https://www.hashicorp.com/careers",
    "Delta Air Lines": "https://delta.com/us/en/careers",
    "Cox Enterprises": "https://jobs.coxenterprises.com/",
    "Cox Automotive": "https://jobs.coxautoinc.com/",
    "Fiserv": "https://www.careers.fiserv.com/",
    "Equifax": "https://careers.equifax.com/",
    "Intercontinental Exchange (ICE)": "https://careers.ice.com/",
    "Secureworks": "https://www.secureworks.com/about/careers",
    "UPS (Tech)": "https://www.jobs-ups.com/",
    "Chick-fil-A (Digital)": "https://careers.chick-fil-a.com/",
    "Norfolk Southern": "https://careers.nscorp.com/",
    "Porsche Digital (Atlanta)": "https://jobs.porsche.com/",
}


def main() -> None:
    results: list[dict] = []
    for company, url in MISSED.items():
        info = detect(url)
        info["company"] = company
        info["input_url"] = url
        if info.get("endpoint"):
            info["probe"] = probe_endpoint(info)
        results.append(info)
        probe = info.get("probe") or {}
        status = "OK" if probe.get("ok") else info.get("ats", "?")
        count = probe.get("count", "")
        print(f"{company}: {info.get('ats')} endpoint={bool(info.get('endpoint'))} probe={status} count={count}")

    print("\n--- JSON ---")
    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()
