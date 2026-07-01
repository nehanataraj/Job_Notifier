#!/usr/bin/env python3
"""Expanded probe for round 3 — more slugs, workday, lever, oracle."""
from __future__ import annotations

import json
import re
import uuid
import requests

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"

def gh(slug):
    r = requests.get(f"https://boards-api.greenhouse.io/v1/boards/{slug}/jobs", timeout=15)
    if r.status_code != 200: return 0
    return len((r.json() or {}).get("jobs") or [])

def ash(slug):
    r = requests.get(f"https://api.ashbyhq.com/posting-api/job-board/{slug}", timeout=15)
    if r.status_code != 200: return 0
    return len((r.json() or {}).get("jobs") or [])

def lev(slug):
    r = requests.get(f"https://api.lever.co/v0/postings/{slug}?mode=json", timeout=15)
    if r.status_code != 200: return 0
    return len(r.json() if isinstance(r.json(), list) else [])

def wd(host, tenant, site):
    try:
        r = requests.post(
            f"{host}/wday/cxs/{tenant}/{site}/jobs",
            json={"appliedFacets": {}, "limit": 1, "offset": 0, "searchText": "intern"},
            headers={"User-Agent": UA, "Accept": "application/json", "Content-Type": "application/json"},
            timeout=15,
        )
        if r.status_code == 200 and "json" in (r.headers.get("content-type") or ""):
            return int((r.json() or {}).get("total") or 0)
    except Exception:
        pass
    return 0

def sr(slug):
    r = requests.get(f"https://api.smartrecruiters.com/v1/companies/{slug}/postings", params={"limit": 1}, timeout=15)
    if r.status_code != 200: return 0
    return int((r.json() or {}).get("totalFound") or 0)

CANDS = {
    "Shopify": [("gh", "shopify"), ("ash", "shopify"), ("lev", "shopify")],
    "Rippling": [("ash", "rippling"), ("gh", "rippling"), ("lev", "rippling")],
    "Retool": [("ash", "retool"), ("gh", "retool"), ("lev", "retool")],
    "Snyk": [("gh", "snyk"), ("ash", "snyk")],
    "SentinelOne": [("gh", "sentinelone")],
    "HashiCorp": [("gh", "hashicorp")],
    "Etsy": [("gh", "etsy")],
    "Atlassian": [("gh", "atlassian"), ("lev", "atlassian")],
    "Intuit": [("gh", "intuit"), ("wd", "https://intuit.wd1.myworkdayjobs.com", "intuit", "Intuit"), ("wd", "https://intuit.wd1.myworkdayjobs.com", "intuit", "External")],
    "IBM": [("gh", "ibm"), ("sr", "IBM"), ("wd", "https://ibm.wd1.myworkdayjobs.com", "ibm", "IBM")],
    "Citadel": [("gh", "citadel"), ("gh", "citadelsecurities")],
    "Two Sigma": [("gh", "twosigma")],
    "Bloomberg": [("gh", "bloomberg")],
    "Weights & Biases": [("gh", "wandb"), ("ash", "wandb")],
    "L3Harris": [("sr", "L3Harris"), ("wd", "https://l3harris.wd1.myworkdayjobs.com", "l3harris", "External")],
    "SAIC": [("sr", "SAIC"), ("wd", "https://saic.wd1.myworkdayjobs.com", "saic", "External")],
    "General Dynamics": [("sr", "GeneralDynamics"), ("wd", "https://gdit.wd1.myworkdayjobs.com", "gdit", "External_Career_Site")],
    "Ford (Tech)": [("sr", "Ford"), ("wd", "https://ford.wd1.myworkdayjobs.com", "ford", "External")],
    "GM / OnStar": [("sr", "GeneralMotors"), ("wd", "https://generalmotors.wd5.myworkdayjobs.com", "gm", "External")],
    "John Deere (Tech)": [("sr", "JohnDeere"), ("wd", "https://johndeere.wd5.myworkdayjobs.com", "johndeere", "External")],
    "UnitedHealth / Optum": [("wd", "https://uhg.wd1.myworkdayjobs.com", "uhg", "External"), ("wd", "https://optum.wd1.myworkdayjobs.com", "optum", "External")],
    "Fidelity": [("sr", "FidelityInvestments"), ("wd", "https://fidelity.wd1.myworkdayjobs.com", "fidelity", "External")],
    "Fortinet": [("sr", "Fortinet"), ("gh", "fortinet"), ("wd", "https://fortinet.wd1.myworkdayjobs.com", "fortinet", "External")],
    "Walmart (Tech)": [("sr", "Walmart"), ("wd", "https://walmart.wd5.myworkdayjobs.com", "walmart", "WalmartExternal")],
    "Dell Technologies": [("sr", "Dell"), ("wd", "https://dell.wd1.myworkdayjobs.com", "dell", "External")],
    "Ubisoft": [("sr", "Ubisoft"), ("gh", "ubisoft")],
    "NBCUniversal": [("sr", "NBCUniversal"), ("sr", "ComcastNBCUniversal")],
    "Norfolk Southern": [("sr", "NorfolkSouthern")],
    "Secureworks": [("sr", "Secureworks")],
    "Cox Enterprises": [("sr", "CoxEnterprises")],
    "Cox Automotive": [("sr", "CoxAutomotive")],
    "Porsche Digital (Atlanta)": [("sr", "Porsche")],
}

found = []
for company, tries in CANDS.items():
    best = None
    for t in tries:
        kind = t[0]
        if kind == "gh":
            n = gh(t[1])
            if n and (not best or n > best[1]):
                best = ("greenhouse", t[1], n)
        elif kind == "ash":
            n = ash(t[1])
            if n and (not best or n > best[1]):
                best = ("ashby", t[1], n)
        elif kind == "lev":
            n = lev(t[1])
            if n and (not best or n > best[1]):
                best = ("lever", t[1], n)
        elif kind == "sr":
            n = sr(t[1])
            if n and (not best or n > best[1]):
                best = ("smartrecruiters", t[1], n)
        elif kind == "wd":
            n = wd(t[1], t[2], t[3])
            if n and (not best or n > best[1]):
                best = ("workday", f"{t[2]}/{t[3]}@{t[1]}", n)
    if best:
        print(f"OK {company}: {best[0]} {best[1]} = {best[2]}")
        found.append({"company": company, "type": best[0], "slug": best[1], "count": best[2]})
    else:
        print(f"MISS {company}")

print("total", len(found))
