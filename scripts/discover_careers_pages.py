#!/usr/bin/env python3
"""Scrape careers landing pages for Workday / Greenhouse / Lever embeds."""

from __future__ import annotations

import json
import re
from typing import Any

import requests

UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)

PAGES: dict[str, str] = {
    "Meta": "https://www.metacareers.com/jobs",
    "Apple": "https://jobs.apple.com/",
    "Tesla": "https://www.tesla.com/careers/search",
    "Intuit": "https://www.intuit.com/careers/",
    "Qualcomm": "https://careers.qualcomm.com/",
    "AMD": "https://careers.amd.com/",
    "Yelp": "https://www.yelp.careers/",
    "Atlassian": "https://www.atlassian.com/company/careers",
    "HubSpot": "https://www.hubspot.com/careers",
    "Rippling": "https://www.rippling.com/careers",
    "Retool": "https://retool.com/careers",
    "Weights & Biases": "https://wandb.ai/careers",
    "CrowdStrike": "https://www.crowdstrike.com/careers/",
    "Palo Alto Networks": "https://jobs.paloaltonetworks.com/",
    "SentinelOne": "https://www.sentinelone.com/careers/",
    "Fortinet": "https://www.fortinet.com/corporate/careers",
    "Splunk": "https://www.splunk.com/en_us/careers.html",
    "Snyk": "https://snyk.io/careers/",
    "JPMorgan Chase": "https://careers.jpmorgan.com/",
    "Goldman Sachs": "https://www.goldmansachs.com/careers/",
    "Bank of America": "https://careers.bankofamerica.com/",
    "Citi": "https://jobs.citi.com/",
    "Wells Fargo": "https://www.wellsfargojobs.com/",
    "Two Sigma": "https://www.twosigma.com/careers/",
    "Bloomberg": "https://www.bloomberg.com/careers/",
    "Fidelity": "https://jobs.fidelity.com/",
    "American Express": "https://aexp.eightfold.ai/careers",
    "McKinsey & Company": "https://www.mckinsey.com/careers/search-jobs",
    "BCG": "https://careers.bcg.com/",
    "Bain & Company": "https://www.bain.com/careers/",
    "Deloitte": "https://apply.deloitte.com/",
    "PwC": "https://www.pwc.com/us/en/careers.html",
    "EY": "https://careers.ey.com/",
    "KPMG": "https://www.kpmguscareers.com/",
    "Accenture": "https://www.accenture.com/us-en/careers",
    "Lockheed Martin": "https://www.lockheedmartinjobs.com/",
    "L3Harris": "https://careers.l3harris.com/",
    "BAE Systems": "https://jobs.baesystems.com/",
    "SAIC": "https://jobs.saic.com/",
    "GE Aerospace": "https://jobs.geaerospace.com/",
    "NASA": "https://www.usajobs.gov/Search?k=NASA",
    "Electronic Arts (EA)": "https://www.ea.com/careers",
    "Activision Blizzard": "https://careers.activisionblizzard.com/",
    "Nike (Tech)": "https://jobs.nike.com/",
    "Walmart (Tech)": "https://careers.walmart.com/",
    "Mastercard": "https://careers.mastercard.com/",
    "Shopify": "https://www.shopify.com/careers",
    "Ford (Tech)": "https://corporate.ford.com/careers.html",
    "GM / OnStar": "https://search-careers.gm.com/",
    "John Deere (Tech)": "https://www.deere.com/en/careers/",
    "AT&T (Tech)": "https://www.att.jobs/",
    "T-Mobile (Tech)": "https://careers.t-mobile.com/",
    "Comcast (Tech)": "https://jobs.comcast.com/",
    "UnitedHealth / Optum": "https://careers.unitedhealthgroup.com/",
    "Etsy": "https://careers.etsy.com/",
    "IBM": "https://www.ibm.com/careers/search",
    "Dell Technologies": "https://jobs.dell.com/",
    "Cisco": "https://jobs.cisco.com/",
    "SAP": "https://jobs.sap.com/",
    "HashiCorp": "https://www.hashicorp.com/careers",
    "Delta Air Lines": "https://delta.com/us/en/careers",
    "The Home Depot": "https://careers.homedepot.com/",
    "NCR Voyix": "https://www.ncr.com/careers",
    "Fiserv": "https://www.careers.fiserv.com/",
    "Global Payments": "https://jobs.globalpayments.com/",
    "Equifax": "https://careers.equifax.com/",
    "Intercontinental Exchange (ICE)": "https://careers.ice.com/",
    "Manhattan Associates": "https://www.manh.com/careers",
    "Secureworks": "https://www.secureworks.com/about/careers",
    "Cardlytics": "https://www.cardlytics.com/careers/",
    "Elevance Health": "https://careers.elevancehealth.com/",
    "UPS (Tech)": "https://www.jobs-ups.com/",
    "Norfolk Southern": "https://careers.nscorp.com/",
    "General Dynamics": "https://www.gd.com/careers",
    "Verily": "https://verily.com/careers/",
    "Citadel": "https://www.citadel.com/careers/",
    "HRT": "https://www.hudsonrivertrading.com/careers/",
    "Ubisoft": "https://www.ubisoft.com/en-us/company/careers",
    "Warner Bros. Discovery": "https://careers.wbd.com/",
    "NBCUniversal": "https://www.nbcunicareers.com/",
    "Cox Enterprises": "https://jobs.coxenterprises.com/",
    "Chick-fil-A (Digital)": "https://careers.chick-fil-a.com/",
    "Porsche Digital (Atlanta)": "https://jobs.porsche.com/",
    "Coinbase": "https://www.coinbase.com/careers",
    "Cloudflare": "https://www.cloudflare.com/careers/",
}


def test_cxs(host: str, tenant: str, site: str) -> tuple[bool, int]:
    host = host.rstrip("/")
    try:
        r = requests.post(
            f"{host}/wday/cxs/{tenant}/{site}/jobs",
            json={"appliedFacets": {}, "limit": 1, "offset": 0, "searchText": "intern"},
            headers={"User-Agent": UA, "Accept": "application/json"},
            timeout=20,
        )
        if r.status_code != 200:
            return False, 0
        return True, int((r.json() or {}).get("total") or 0)
    except Exception:
        return False, 0


def gh(slug: str) -> tuple[bool, int]:
    r = requests.get(f"https://boards-api.greenhouse.io/v1/boards/{slug}/jobs", timeout=15)
    if r.status_code != 200:
        return False, 0
    return True, len((r.json() or {}).get("jobs") or [])


def lever(slug: str) -> tuple[bool, int]:
    r = requests.get(f"https://api.lever.co/v0/postings/{slug}", params={"mode": "json"}, timeout=15)
    if r.status_code != 200 or not isinstance(r.json(), list):
        return False, 0
    return True, len(r.json())


def ashby(slug: str) -> tuple[bool, int]:
    r = requests.get(f"https://api.ashbyhq.com/posting-api/job-board/{slug}", timeout=15)
    if r.status_code != 200:
        return False, 0
    return True, len((r.json() or {}).get("jobs") or [])


def pcsx_from_page(text: str, company: str) -> dict[str, Any] | None:
    m = re.search(r"https://([a-z0-9.-]+)/api/(?:pcsx|apply/v2)/", text, re.I)
    if not m:
        return None
    host = m.group(1)
    list_url = f"https://{host}/api/pcsx/search"
    if "eightfold" in host:
        domain = host.split(".")[0] + ".com"
        return {"company": company, "type": "pcsx", "list_url": list_url, "domain": domain, "query": "intern"}
    return None


def scan(company: str, url: str) -> dict[str, Any] | None:
    try:
        r = requests.get(url, headers={"User-Agent": UA}, timeout=25, allow_redirects=True)
        blob = (r.text or "") + " " + r.url
    except Exception:
        return None

    # Greenhouse embed
    for slug in set(re.findall(r"boards\.greenhouse\.io/([a-z0-9_-]+)", blob, re.I)):
        ok, count = gh(slug)
        if ok and count:
            return {"company": company, "type": "greenhouse", "board_token": slug, "count": count}

    for slug in set(re.findall(r"jobs\.lever\.co/([a-z0-9_-]+)", blob, re.I)):
        ok, count = lever(slug)
        if ok and count:
            return {"company": company, "type": "lever", "company_slug": slug, "count": count}

    for slug in set(re.findall(r"jobs\.ashbyhq\.com/([a-z0-9_-]+)", blob, re.I)):
        ok, count = ashby(slug)
        if ok and count:
            return {"company": company, "type": "ashby", "board_slug": slug, "count": count}

    pcsx = pcsx_from_page(blob, company)
    if pcsx:
        return pcsx

    hosts = set(re.findall(r"https://[a-z0-9-]+\.wd\d+\.myworkdayjobs\.com", blob, re.I))
    paths = re.findall(
        r"[a-z0-9-]+\.wd\d+\.myworkdayjobs\.com(?:/en-US)?/([a-zA-Z][a-zA-Z0-9_]+)",
        blob,
        re.I,
    )
    for host in hosts:
        tenant = host.split("//")[1].split(".")[0]
        for site in dict.fromkeys(paths):
            if site.lower() in ("en-us", "job", "jobs"):
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
    return None


def main() -> None:
    hits: list[dict[str, Any]] = []
    for company, url in PAGES.items():
        row = scan(company, url)
        if row:
            hits.append(row)
            print(f"OK  {company}: {row['type']} ({row.get('count', '?')})")
        else:
            print(f"MISS {company}")

    print("\n--- JSON ---")
    print(json.dumps(hits, indent=2))


if __name__ == "__main__":
    main()
