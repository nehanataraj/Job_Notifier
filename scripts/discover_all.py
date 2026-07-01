#!/usr/bin/env python3
"""Aggressive ATS discovery for remaining target companies."""

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

# Companies still missing after prior passes
TARGETS: dict[str, list[str]] = {
    "Meta": ["meta", "facebook", "metacareers"],
    "Apple": ["apple", "appleinc"],
    "Tesla": ["tesla", "teslamotors"],
    "The Boring Company": ["boringcompany", "theboringcompany"],
    "Intuit": ["intuit"],
    "Qualcomm": ["qualcomm"],
    "AMD": ["amd"],
    "Yelp": ["yelp"],
    "Atlassian": ["atlassian"],
    "HubSpot": ["hubspot"],
    "Rippling": ["rippling"],
    "Retool": ["retool"],
    "Weights & Biases": ["wandb", "weightsandbiases", "weights-biases"],
    "CrowdStrike": ["crowdstrike"],
    "Palo Alto Networks": ["paloaltonetworks", "paloalto"],
    "SentinelOne": ["sentinelone"],
    "Fortinet": ["fortinet"],
    "Splunk": ["splunk"],
    "Snyk": ["snyk"],
    "Goldman Sachs": ["goldmansachs", "gs"],
    "JPMorgan Chase": ["jpmorgan", "jpmc", "jpmorganchase"],
    "Bank of America": ["bankofamerica", "bofa"],
    "Citi": ["citi", "citigroup"],
    "Wells Fargo": ["wellsfargo"],
    "Citadel": ["citadel", "citadelsecurities"],
    "Two Sigma": ["twosigma"],
    "D.E. Shaw": ["deshaw", "deshawgroup"],
    "HRT": ["hudsonrivertrading", "hrt"],
    "Bloomberg": ["bloomberg", "bloomberglp"],
    "Fidelity": ["fidelity", "fidelityinvestments"],
    "American Express": ["americanexpress", "amex", "aexp"],
    "McKinsey & Company": ["mckinsey"],
    "BCG": ["bcg"],
    "Bain & Company": ["bain", "bainandcompany"],
    "Deloitte": ["deloitte"],
    "PwC": ["pwc"],
    "EY": ["ey", "ernstandyoung"],
    "KPMG": ["kpmg"],
    "Accenture": ["accenture"],
    "Lockheed Martin": ["lockheedmartin", "lockheed"],
    "L3Harris": ["l3harris"],
    "BAE Systems": ["baesystems", "bae"],
    "SAIC": ["saic"],
    "GE Aerospace": ["geaerospace", "ge"],
    "NASA": ["nasa"],
    "Electronic Arts (EA)": ["ea", "electronicarts"],
    "Activision Blizzard": ["activision", "activisionblizzard"],
    "Valve": ["valve", "valvesoftware"],
    "Ubisoft": ["ubisoft"],
    "Warner Bros. Discovery": ["warnerbros", "wbd"],
    "NBCUniversal": ["nbcuniversal", "nbcu"],
    "Nike (Tech)": ["nike"],
    "Walmart (Tech)": ["walmart"],
    "Mastercard": ["mastercard"],
    "Shopify": ["shopify"],
    "Ford (Tech)": ["ford", "fordmotor"],
    "GM / OnStar": ["gm", "generalmotors"],
    "John Deere (Tech)": ["johndeere", "deere"],
    "AT&T (Tech)": ["att"],
    "T-Mobile (Tech)": ["tmobile"],
    "Comcast (Tech)": ["comcast"],
    "UnitedHealth / Optum": ["optum", "uhg", "unitedhealthgroup"],
    "Etsy": ["etsy"],
    "IBM": ["ibm"],
    "Dell Technologies": ["dell"],
    "Cisco": ["cisco"],
    "SAP": ["sap"],
    "HashiCorp": ["hashicorp"],
    "Delta Air Lines": ["delta", "deltaairlines"],
    "The Home Depot": ["homedepot"],
    "NCR Voyix": ["ncr", "ncrvoyix"],
    "Cox Enterprises": ["cox"],
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
    "Chick-fil-A (Digital)": ["chickfila"],
    "Norfolk Southern": ["norfolksouthern"],
    "Porsche Digital (Atlanta)": ["porsche"],
    "Verily": ["verily", "verilylife"],
    "Reality Labs": ["realitylabs"],
    "General Dynamics": ["generaldynamics", "gdit"],
}

WORKDAY_MATRIX: dict[str, list[tuple[str, str, str]]] = {
    "Meta": [
        ("https://meta.wd1.myworkdayjobs.com", "meta", "External"),
        ("https://meta.wd1.myworkdayjobs.com", "meta", "Facebook"),
        ("https://metacareers.wd1.myworkdayjobs.com", "metacareers", "External"),
    ],
    "Apple": [
        ("https://apple.wd3.myworkdayjobs.com", "apple", "Apple_External_Career_Site"),
        ("https://apple.wd3.myworkdayjobs.com", "apple", "AppleCareerSite"),
    ],
    "Tesla": [
        ("https://tesla.wd3.myworkdayjobs.com", "tesla", "Tesla_External"),
        ("https://tesla.wd3.myworkdayjobs.com", "tesla", "Tesla"),
    ],
    "Intuit": [("https://intuit.wd1.myworkdayjobs.com", "intuit", "Intuit")],
    "Qualcomm": [("https://qualcomm.wd5.myworkdayjobs.com", "qualcomm", "External")],
    "AMD": [
        ("https://amd.wd1.myworkdayjobs.com", "amd", "External"),
        ("https://amd.wd5.myworkdayjobs.com", "amd", "External"),
    ],
    "Yelp": [("https://yelp.wd5.myworkdayjobs.com", "yelp", "Yelp")],
    "Atlassian": [("https://atlassian.wd5.myworkdayjobs.com", "atlassian", "Atlassian")],
    "HubSpot": [("https://hubspot.wd5.myworkdayjobs.com", "hubspot", "HubSpot")],
    "CrowdStrike": [("https://crowdstrike.wd5.myworkdayjobs.com", "crowdstrike", "CrowdStrike")],
    "Palo Alto Networks": [
        ("https://paloaltonetworks.wd1.myworkdayjobs.com", "paloaltonetworks", "PaloAltoNetworks"),
        ("https://paloaltonetworks.wd5.myworkdayjobs.com", "paloaltonetworks", "PaloAltoNetworks"),
    ],
    "SentinelOne": [("https://sentinelone.wd1.myworkdayjobs.com", "sentinelone", "SentinelOne")],
    "Fortinet": [("https://fortinet.wd1.myworkdayjobs.com", "fortinet", "Fortinet")],
    "Splunk": [("https://splunk.wd5.myworkdayjobs.com", "splunk", "Splunk")],
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
    "Citi": [("https://citi.wd5.myworkdayjobs.com", "citi", "Citi")],
    "Wells Fargo": [("https://wellsfargo.wd1.myworkdayjobs.com", "wellsfargo", "WellsFargoJobs")],
    "Two Sigma": [("https://twosigma.wd1.myworkdayjobs.com", "twosigma", "TwoSigma")],
    "Bloomberg": [("https://bloomberg.wd1.myworkdayjobs.com", "bloomberg", "Bloomberg")],
    "Fidelity": [("https://fidelity.wd1.myworkdayjobs.com", "fidelity", "Fidelity")],
    "American Express": [("https://aexp.wd5.myworkdayjobs.com", "aexp", "AmericanExpress")],
    "McKinsey & Company": [("https://mckinsey.wd1.myworkdayjobs.com", "mckinsey", "McKinsey")],
    "BCG": [("https://bcg.wd1.myworkdayjobs.com", "bcg", "BCG")],
    "Bain & Company": [("https://bain.wd1.myworkdayjobs.com", "bain", "Bain")],
    "Deloitte": [("https://deloitte.wd1.myworkdayjobs.com", "deloitte", "Deloitte")],
    "PwC": [("https://pwc.wd3.myworkdayjobs.com", "pwc", "PwC")],
    "EY": [("https://ey.wd1.myworkdayjobs.com", "ey", "EY")],
    "KPMG": [("https://kpmg.wd1.myworkdayjobs.com", "kpmg", "KPMG")],
    "Accenture": [("https://accenture.wd3.myworkdayjobs.com", "accenture", "AccentureCareers")],
    "Lockheed Martin": [
        ("https://lockheedmartin.wd1.myworkdayjobs.com", "lockheedmartin", "LockheedMartin"),
    ],
    "L3Harris": [("https://l3harris.wd1.myworkdayjobs.com", "l3harris", "L3Harris")],
    "BAE Systems": [("https://baesystems.wd1.myworkdayjobs.com", "baesystems", "BAE")],
    "SAIC": [("https://saic.wd1.myworkdayjobs.com", "saic", "SAIC")],
    "GE Aerospace": [("https://geaerospace.wd1.myworkdayjobs.com", "geaerospace", "GE_Aerospace")],
    "NASA": [("https://nasajobs.wd1.myworkdayjobs.com", "nasajobs", "NASA")],
    "Electronic Arts (EA)": [("https://ea.wd1.myworkdayjobs.com", "ea", "EA")],
    "Activision Blizzard": [
        ("https://activision.wd1.myworkdayjobs.com", "activision", "External"),
        ("https://activision.wd5.myworkdayjobs.com", "activision", "External"),
    ],
    "Nike (Tech)": [("https://nike.wd1.myworkdayjobs.com", "nike", "Nike")],
    "Walmart (Tech)": [("https://walmart.wd5.myworkdayjobs.com", "walmart", "WalmartExternal")],
    "Mastercard": [("https://mastercard.wd1.myworkdayjobs.com", "mastercard", "Mastercard")],
    "Shopify": [("https://shopify.wd3.myworkdayjobs.com", "shopify", "Shopify")],
    "Ford (Tech)": [("https://ford.wd1.myworkdayjobs.com", "ford", "Ford")],
    "GM / OnStar": [("https://generalmotors.wd5.myworkdayjobs.com", "generalmotors", "GM")],
    "John Deere (Tech)": [("https://johndeere.wd1.myworkdayjobs.com", "johndeere", "JohnDeere")],
    "AT&T (Tech)": [("https://att.wd1.myworkdayjobs.com", "att", "ATT")],
    "T-Mobile (Tech)": [("https://tmobile.wd1.myworkdayjobs.com", "tmobile", "TMO")],
    "Comcast (Tech)": [("https://comcast.wd5.myworkdayjobs.com", "comcast", "Comcast_Careers")],
    "UnitedHealth / Optum": [
        ("https://uhg.wd1.myworkdayjobs.com", "uhg", "UHG"),
        ("https://optum.wd1.myworkdayjobs.com", "optum", "Optum"),
    ],
    "Etsy": [("https://etsy.wd5.myworkdayjobs.com", "etsy", "Etsy")],
    "IBM": [("https://ibm.wd1.myworkdayjobs.com", "ibm", "IBM")],
    "Dell Technologies": [("https://dell.wd1.myworkdayjobs.com", "dell", "External")],
    "Cisco": [("https://cisco.wd1.myworkdayjobs.com", "cisco", "Cisco")],
    "SAP": [("https://sap.wd3.myworkdayjobs.com", "sap", "SAP")],
    "Delta Air Lines": [("https://delta.wd1.myworkdayjobs.com", "delta", "Delta")],
    "The Home Depot": [("https://homedepot.wd5.myworkdayjobs.com", "homedepot", "HomeDepot")],
    "NCR Voyix": [("https://ncr.wd1.myworkdayjobs.com", "ncr", "NCR")],
    "Fiserv": [("https://fiserv.wd5.myworkdayjobs.com", "fiserv", "Fiserv")],
    "Global Payments": [
        ("https://globalpayments.wd1.myworkdayjobs.com", "globalpayments", "GlobalPayments"),
    ],
    "Equifax": [("https://equifax.wd5.myworkdayjobs.com", "equifax", "Equifax")],
    "Intercontinental Exchange (ICE)": [
        ("https://ice.wd1.myworkdayjobs.com", "ice", "ICE"),
    ],
    "Manhattan Associates": [
        ("https://manh.wd1.myworkdayjobs.com", "manh", "ManhattanAssociates"),
    ],
    "Secureworks": [("https://secureworks.wd1.myworkdayjobs.com", "secureworks", "Secureworks")],
    "Cardlytics": [("https://cardlytics.wd1.myworkdayjobs.com", "cardlytics", "Cardlytics")],
    "Elevance Health": [
        ("https://elevancehealth.wd1.myworkdayjobs.com", "elevancehealth", "ElevanceHealth"),
    ],
    "UPS (Tech)": [("https://ups.wd1.myworkdayjobs.com", "ups", "UPS")],
    "Norfolk Southern": [
        ("https://norfolksouthern.wd1.myworkdayjobs.com", "norfolksouthern", "NorfolkSouthern"),
    ],
    "General Dynamics": [
        ("https://gdit.wd1.myworkdayjobs.com", "gdit", "External_Career_Site"),
    ],
    "Verily": [("https://verily.wd1.myworkdayjobs.com", "verily", "Verily")],
}

# Oracle HCM known hosts
ORACLE_MATRIX: dict[str, list[tuple[str, str, str]]] = {
    "JPMorgan Chase": [
        ("jpmc.fa.oraclecloud.com", "CX_1001", "https://jpmc.fa.oraclecloud.com/hcmUI/CandidateExperience/en/sites/CX_1001/job/{id}"),
    ],
    "Goldman Sachs": [
        ("hdpc.fa.us2.oraclecloud.com", "CX_1", "https://hdpc.fa.us2.oraclecloud.com/hcmUI/CandidateExperience/en/sites/CX_1/job/{id}"),
    ],
}

CAREERS_URLS: dict[str, str] = {
    "Meta": "https://www.metacareers.com/jobs",
    "Apple": "https://jobs.apple.com/en-us/search",
    "Tesla": "https://www.tesla.com/careers/search",
    "JPMorgan Chase": "https://careers.jpmorgan.com/us/en/search-results",
    "Goldman Sachs": "https://higher.goldmansachs.com/careers/index.html",
    "Deloitte": "https://apply.deloitte.com/careers/SearchJobs",
    "Shopify": "https://www.shopify.com/careers",
    "CrowdStrike": "https://crowdstrike.wd5.myworkdayjobs.com/CrowdStrike",
}


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


def sr(slug: str) -> tuple[bool, int]:
    r = requests.get(
        f"https://api.smartrecruiters.com/v1/companies/{slug}/postings",
        params={"limit": 1},
        timeout=15,
    )
    if r.status_code != 200:
        return False, 0
    return True, int((r.json() or {}).get("totalFound") or 0)


def workable(slug: str) -> tuple[bool, int]:
    r = requests.get(
        f"https://apply.workable.com/{slug}/jobs.md",
        headers={"User-Agent": UA, "Accept": "text/markdown,*/*;q=0.8"},
        timeout=15,
    )
    if r.status_code != 200:
        return False, 0
    n = len(re.findall(r"\[View\]\(https://apply\.workable\.com/[^)]+\)", r.text or ""))
    return n > 0, n


def recruitee(slug: str) -> tuple[bool, int]:
    r = requests.get(f"https://{slug}.recruitee.com/api/offers/", timeout=15)
    if r.status_code != 200:
        return False, 0
    offers = (r.json() or {}).get("offers") or []
    return len(offers) > 0, len(offers)


def workday(host: str, tenant: str, site: str) -> tuple[bool, int]:
    host = host.rstrip("/")
    if "oraclecloud" in host:
        return False, 0
    try:
        r = requests.post(
            f"{host}/wday/cxs/{tenant}/{site}/jobs",
            json={"appliedFacets": {}, "limit": 1, "offset": 0, "searchText": "intern"},
            headers={"User-Agent": UA, "Accept": "application/json"},
            timeout=15,
        )
        if r.status_code != 200:
            return False, 0
        total = int((r.json() or {}).get("total") or 0)
        return total > 0, total
    except Exception:
        return False, 0


def oracle(host: str, site_number: str) -> tuple[bool, int]:
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
        "finder": f"findReqs;siteNumber={site_number},keyword=intern",
        "limit": 1,
        "offset": 0,
    }
    try:
        r = requests.get(url, params=params, headers=headers, timeout=15)
        if r.status_code != 200:
            return False, 0
        postings = (r.json() or {}).get("items") or [{}]
        lst = postings[0].get("requisitionList") or []
        return len(lst) > 0, len(lst)
    except Exception:
        return False, 0


def discover_workday_from_url(url: str) -> dict[str, str] | None:
    try:
        r = requests.get(url, headers={"User-Agent": UA}, timeout=20, allow_redirects=True)
        final = r.url
        if "myworkdayjobs.com" not in final:
            html = r.text or ""
            m = re.search(r"https://[a-z0-9.-]+\.wd\d+\.myworkdayjobs\.com/[a-zA-Z0-9_/-]+", html)
            if m:
                final = m.group(0)
            else:
                return None
        parsed = urlparse(final)
        host = f"{parsed.scheme}://{parsed.netloc}"
        parts = [p for p in parsed.path.split("/") if p]
        if len(parts) < 1:
            return None
        tenant = parts[0].split(".")[0] if "." in parts[0] else host.split("//")[1].split(".")[0]
        # tenant from subdomain: crowdstrike.wd5.myworkdayjobs.com
        sub = parsed.netloc.split(".")[0]
        tenant = sub
        site = parts[0] if parts else ""
        if workday(host, tenant, site)[0]:
            return {"host": host, "tenant": tenant, "site": site}
    except Exception:
        return None
    return None


def probe_bespoke() -> list[dict[str, Any]]:
    hits: list[dict[str, Any]] = []

    # Tesla
    try:
        r = requests.get(
            "https://www.tesla.com/cua-api/apps/careers/state",
            headers={"User-Agent": UA},
            timeout=20,
        )
        if r.ok:
            data = r.json() or {}
            posts = data.get("posts") or data.get("jobs") or []
            if isinstance(posts, list) and posts:
                hits.append({"company": "Tesla", "type": "tesla", "count": len(posts)})
    except Exception:
        pass

    # Apple search API (no CSRF first try)
    try:
        r = requests.get(
            "https://jobs.apple.com/api/role/search",
            params={"page": 1, "query": "intern"},
            headers={"User-Agent": UA, "Accept": "application/json"},
            timeout=20,
        )
        if r.ok:
            data = r.json() or {}
            total = int(data.get("totalRecords") or data.get("total") or 0)
            if total > 0:
                hits.append({"company": "Apple", "type": "apple", "count": total})
    except Exception:
        pass

    # Meta GraphQL
    try:
        r = requests.post(
            "https://www.metacareers.com/graphql",
            headers={"User-Agent": UA, "Content-Type": "application/json"},
            json={
                "operationName": "JobSearchResults",
                "variables": {"searchInput": {"query": "intern", "limit": 1}},
                "query": (
                    "query JobSearchResults($searchInput: JobSearchInput!) {"
                    "  job_search(search_input: $searchInput) { total_count } }"
                ),
            },
            timeout=20,
        )
        if r.ok:
            total = (
                (r.json() or {})
                .get("data", {})
                .get("job_search", {})
                .get("total_count", 0)
            )
            if total:
                hits.append({"company": "Meta", "type": "meta", "count": total})
    except Exception:
        pass

    return hits


def main() -> None:
    hits: list[dict[str, Any]] = []

    for company, slugs in TARGETS.items():
        best = None
        for slug in slugs:
            for kind, fn in [
                ("greenhouse", gh),
                ("lever", lever),
                ("ashby", ashby),
                ("smartrecruiters", sr),
                ("workable", workable),
                ("recruitee", recruitee),
            ]:
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
            print(f"API  {company}: {best['type']}:{best['slug']} ({best['count']})")

    for company, candidates in WORKDAY_MATRIX.items():
        if any(h["company"] == company for h in hits):
            continue
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
                print(f"WD   {company}: {tenant}/{site} ({count})")
                break

    for company, candidates in ORACLE_MATRIX.items():
        if any(h["company"] == company for h in hits):
            continue
        for host, site_number, job_url in candidates:
            ok, count = oracle(host, site_number)
            if ok:
                row = {
                    "company": company,
                    "type": "oracle_careers",
                    "host": host,
                    "site_number": site_number,
                    "job_url": job_url,
                    "count": count,
                }
                hits.append(row)
                print(f"ORA  {company}: {host} {site_number} ({count})")
                break

    for company, url in CAREERS_URLS.items():
        if any(h["company"] == company for h in hits):
            continue
        wd = discover_workday_from_url(url)
        if wd:
            ok, count = workday(wd["host"], wd["tenant"], wd["site"])
            if ok:
                row = {"company": company, "type": "workday", **wd, "count": count}
                hits.append(row)
                print(f"URL  {company}: {wd['tenant']}/{wd['site']} ({count})")

    for row in probe_bespoke():
        if not any(h["company"] == row["company"] for h in hits):
            hits.append(row)
            print(f"BES  {row['company']}: {row['type']} ({row['count']})")

    print("\n--- JSON ---")
    print(json.dumps(hits, indent=2))


if __name__ == "__main__":
    main()
