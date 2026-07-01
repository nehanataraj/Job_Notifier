#!/usr/bin/env python3
import requests

UA = "Mozilla/5.0"
CANDS = [
    ("Walmart", "https://walmart.wd5.myworkdayjobs.com", "walmart", "WalmartExternal"),
    ("Walmart2", "https://walmart.wd5.myworkdayjobs.com", "walmart", "External"),
    ("IBM", "https://ibm.wd1.myworkdayjobs.com", "ibm", "IBM"),
    ("IBM2", "https://ibm.wd1.myworkdayjobs.com", "ibm", "External"),
    ("Wells", "https://wellsfargo.wd5.myworkdayjobs.com", "wellsfargo", "External"),
    ("Intuit", "https://intuit.wd1.myworkdayjobs.com", "intuit", "External"),
    ("KPMG", "https://kpmg.wd1.myworkdayjobs.com", "kpmg", "External"),
    ("L3Harris", "https://l3harris.wd1.myworkdayjobs.com", "l3harris", "External"),
    ("Lockheed", "https://lockheedmartin.wd1.myworkdayjobs.com", "lockheedmartin", "External"),
    ("SAIC", "https://saic.wd1.myworkdayjobs.com", "saic", "External"),
    ("UHG", "https://uhg.wd1.myworkdayjobs.com", "uhg", "External"),
    ("GM", "https://generalmotors.wd5.myworkdayjobs.com", "gm", "External"),
    ("Deere", "https://johndeere.wd5.myworkdayjobs.com", "johndeere", "External"),
    ("Ford", "https://ford.wd1.myworkdayjobs.com", "ford", "External"),
    ("Fidelity", "https://fidelity.wd1.myworkdayjobs.com", "fidelity", "External"),
    ("PwC", "https://pwc.wd3.myworkdayjobs.com", "pwc", "Global_Experienced_Careers"),
    ("Equifax", "https://equifax.wd5.myworkdayjobs.com", "equifax", "External"),
    ("Dell", "https://dell.wd1.myworkdayjobs.com", "dell", "External"),
]

for label, host, tenant, site in CANDS:
    try:
        r = requests.post(
            f"{host}/wday/cxs/{tenant}/{site}/jobs",
            json={"appliedFacets": {}, "limit": 1, "offset": 0, "searchText": "intern"},
            headers={"User-Agent": UA, "Accept": "application/json", "Content-Type": "application/json"},
            timeout=15,
        )
        total = None
        if r.status_code == 200 and "json" in (r.headers.get("content-type") or ""):
            total = (r.json() or {}).get("total")
        print(f"{label:12} {tenant}/{site:30} {r.status_code} total={total}")
    except Exception as e:
        print(f"{label:12} ERR {e}")
