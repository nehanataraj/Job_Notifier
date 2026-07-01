#!/usr/bin/env python3
"""ATS detect + deep probes for round 3."""
import json, sys, uuid, re, requests
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from batch_detect_misses import MISSED
from ats_detect import detect

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
cfg = json.loads((Path(__file__).resolve().parent.parent / "config.json").read_text())
remaining = sorted(c for c in MISSED if c not in {s["name"] for s in cfg["sources"]})

by_ats = {}
for c in remaining:
    try:
        info = detect(MISSED[c])
        ats = info.get("ats", "?")
        by_ats.setdefault(ats, []).append(c)
        print(f"{c}: {ats}")
    except Exception as e:
        print(f"{c}: ERR {e}")

print("\n--- grouped ---")
for ats, cos in sorted(by_ats.items(), key=lambda x: -len(x[1])):
    print(ats, len(cos), cos)

# Deep probes
print("\n--- deep ---")

# KPMG successfactors RSS?
for url in [
    "https://www.kpmguscareers.com/services/rss/job/?locale=en_US&keywords=(intern)",
    "https://jobs.kpmg.com/services/rss/job/?locale=en_US&keywords=(intern)",
]:
    try:
        r = requests.get(url, headers={"User-Agent": UA}, timeout=20)
        print("KPMG RSS", url.split("/")[2], r.status_code, r.text.count("<item>"))
    except Exception as e:
        print("KPMG RSS err", e)

# McKinsey / Bain eightfold with referer
for label, url, dom in [
    ("McKinsey", "https://mckinsey.eightfold.ai/api/pcsx/search", "mckinsey.com"),
    ("Bain", "https://bain.eightfold.ai/api/pcsx/search", "bain.com"),
    ("KPMG", "https://kpmg.eightfold.ai/api/pcsx/search", "kpmg.com"),
]:
    for hdr in [{"User-Agent": UA}, {"User-Agent": UA, "Referer": f"https://{dom}"}]:
        r = requests.get(url, params={"domain": dom, "query": "intern", "start": 0, "count": 3}, headers=hdr, timeout=20)
        if r.status_code == 200:
            pos = ((r.json() or {}).get("data") or {}).get("positions") or []
            print(label, "pcsx OK", len(pos), hdr.get("Referer", ""))
            break
        print(label, r.status_code)

# Lever slugs batch
for company, slugs in {
    "Atlassian": ["atlassian", "atlassians"],
    "Shopify": ["shopify"],
    "Rippling": ["rippling"],
    "Retool": ["retool"],
    "Snyk": ["snyk"],
    "Intuit": ["intuit"],
}.items():
    for s in slugs:
        r = requests.get(f"https://api.lever.co/v0/postings/{s}?mode=json", timeout=15)
        if r.status_code == 200 and isinstance(r.json(), list) and r.json():
            print(f"Lever {company} {s} = {len(r.json())}")

# Workday GET discover
def wd_sites(label, base):
    try:
        r = requests.get(base, headers={"User-Agent": UA}, timeout=20, allow_redirects=True)
        m = re.search(r"/([A-Za-z][A-Za-z0-9_]+)(?:\?|$)", r.url.replace("/en-US/", "/"))
        if not m: return
        tenant = base.split("//")[1].split(".")[0]
        site = m.group(1)
        if site.lower() in ("en-us", "jobs"): return
        host = "/".join(base.split("/")[:3])
        pr = requests.post(f"{host}/wday/cxs/{tenant}/{site}/jobs",
            json={"appliedFacets": {}, "limit": 1, "offset": 0, "searchText": "intern"},
            headers={"User-Agent": UA, "Accept": "application/json", "Content-Type": "application/json", "Referer": r.url},
            timeout=20)
        if pr.status_code == 200 and "json" in (pr.headers.get("content-type") or ""):
            print(f"WD {label} {tenant}/{site} total={(pr.json() or {}).get('total')}")
    except Exception as e:
        print(f"WD {label} err", e)

for label, base in [
    ("Intuit", "https://intuit.wd1.myworkdayjobs.com/Intuit"),
    ("L3Harris", "https://l3harris.wd1.myworkdayjobs.com/L3Harris"),
    ("SAIC", "https://saic.wd1.myworkdayjobs.com/SAIC"),
    ("GDIT", "https://gdit.wd1.myworkdayjobs.com/External_Career_Site"),
    ("Ford", "https://ford.wd1.myworkdayjobs.com/Ford"),
    ("GM", "https://generalmotors.wd5.myworkdayjobs.com/GM"),
    ("Deere", "https://johndeere.wd5.myworkdayjobs.com/JohnDeere"),
    ("Fidelity", "https://fidelity.wd1.myworkdayjobs.com/FidelityCareers"),
    ("Fortinet", "https://fortinet.wd1.myworkdayjobs.com/Fortinet"),
    ("Dell", "https://dell.wd1.myworkdayjobs.com/External"),
]:
    wd_sites(label, base)
