#!/usr/bin/env python3
import json
import re
import requests

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"


def sniff(url, label):
    r = requests.get(url, headers={"User-Agent": UA}, timeout=30, allow_redirects=True)
    html = r.text[:800_000]
    print(f"\n{label} final={r.url}")
    for pat in [
        r"https://[a-z0-9-]+\.wd\d+\.myworkdayjobs\.com[^\"'\s<>]*",
        r"brassring[^\"'\s<>]*",
        r"oraclecloud\.com[^\"'\s<>]*",
        r"boards\.greenhouse\.io/([a-z0-9_-]+)",
        r"jobs\.lever\.co/([a-z0-9_-]+)",
        r"taleo\.net[^\"'\s<>]*",
        r"icims\.com[^\"'\s<>]*",
        r"/api/[a-zA-Z0-9_/-]+",
    ]:
        hits = sorted(set(re.findall(pat, html, re.I)))
        if hits:
            print(f"  {pat[:40]} -> {hits[:6]}")


sniff("https://careers.jpmorgan.com/us/en/search-results?keywords=intern", "JPM careers")
sniff("https://higher.gs.com/campus", "GS campus")
sniff("https://www.wellsfargojobs.com/en/jobs/?q=intern", "Wells search")
sniff("https://www.lockheedmartinjobs.com/search-jobs?k=intern", "Lockheed search")

# BrassRing common endpoint pattern
for url in [
    "https://sjobs.brassring.com/TGnewUI/Search/Home/Home?partnerid=25037&siteid=5014",
    "https://sjobs.brassring.com/TGnewUI/Search/Home/Home?partnerid=25037&siteid=5014&keyword=intern",
]:
    try:
        r = requests.get(url, headers={"User-Agent": UA}, timeout=25)
        print("BR", url[-30:], r.status_code, len(r.text))
        if "intern" in r.text.lower():
            print("  has intern mentions", r.text.lower().count("intern"))
    except Exception as e:
        print("BR ERR", e)

# Try JPM on careers.jpmorgan.com oracle embed
import uuid
for host, site in [
    ("jpmc.fa.oraclecloud.com", "CX_1001"),
    ("jpmc.fa.oraclecloud.com", "CX_1"),
    ("jpmc.fa.oraclecloud.com", "CX"),
]:
    url = f"https://{host}/hcmRestApi/resources/latest/recruitingCEJobRequisitions"
    params = {"onlyData": "true", "finder": f"findReqs;siteNumber={site}", "limit": 5, "offset": 0}
    headers = {
        "User-Agent": UA,
        "Accept": "application/json",
        "ora-irc-cx-userid": str(uuid.uuid4()),
        "ora-irc-language": "en",
        "content-type": "application/vnd.oracle.adf.resourceitem+json;charset=utf-8",
        "Referer": "https://careers.jpmorgan.com/",
    }
    r = requests.get(url, params=params, headers=headers, timeout=25)
    if r.status_code == 200:
        reqs = (r.json() or {}).get("items", [{}])[0].get("requisitionList") or []
        print(f"JPM oracle {site} count={len(reqs)} sample={(reqs[0].get('Title') if reqs else '')}")

# Wells workday - probe HTML for site id in script
r = requests.get("https://www.wellsfargojobs.com/", headers={"User-Agent": UA}, timeout=30)
wd = re.findall(r"([a-z0-9-]+)\.(wd\d+)\.myworkdayjobs\.com(?:/en-US)?/([A-Za-z0-9_]+)", r.text, re.I)
print("Wells WD embeds", wd[:5])

# Delta workday from careers page
r = requests.get("https://www.delta.com/us/en/careers", headers={"User-Agent": UA}, timeout=30)
wd = re.findall(r"([a-z0-9-]+)\.(wd\d+)\.myworkdayjobs\.com(?:/en-US)?/([A-Za-z0-9_]+)", r.text, re.I)
print("Delta WD embeds", wd[:5])
print("Delta len", len(r.text))
