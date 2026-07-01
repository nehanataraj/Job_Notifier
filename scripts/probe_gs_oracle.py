#!/usr/bin/env python3
import re
import uuid
import requests

UA = "Mozilla/5.0"
r = requests.get("https://higher.gs.com/campus", headers={"User-Agent": UA}, timeout=30)
sites = sorted(set(re.findall(r"CX_\d+", r.text)))
print("CX sites in HTML", sites)
oracle_urls = sorted(set(re.findall(r"oraclecloud\.com/hcmUI[^\"'\s<>]+", r.text, re.I)))
print("oracle urls", oracle_urls[:5])

for site in sites + ["CX_1", "CX_1001", "CX_2001"]:
    url = "https://hdpc.fa.us2.oraclecloud.com/hcmRestApi/resources/latest/recruitingCEJobRequisitions"
    params = {
        "onlyData": "true",
        "finder": f"findReqs;siteNumber={site},keyword=intern",
        "limit": 5,
        "offset": 0,
        "expand": "requisitionList.workLocation",
    }
    headers = {
        "User-Agent": UA,
        "Accept": "application/json",
        "ora-irc-cx-userid": str(uuid.uuid4()),
        "ora-irc-language": "en",
        "content-type": "application/vnd.oracle.adf.resourceitem+json;charset=utf-8",
        "Referer": "https://higher.gs.com/",
    }
    rr = requests.get(url, params=params, headers=headers, timeout=25)
    if rr.status_code == 200:
        reqs = (rr.json() or {}).get("items", [{}])[0].get("requisitionList") or []
        if reqs:
            print(f"OK {site} count={len(reqs)} sample={reqs[0].get('Title','')[:50]}")
