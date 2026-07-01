#!/usr/bin/env python3
import json
import re
import uuid
import requests

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"


def oracle(host, site, keyword="intern"):
    url = f"https://{host}/hcmRestApi/resources/latest/recruitingCEJobRequisitions"
    params = {
        "onlyData": "true",
        "finder": f"findReqs;siteNumber={site},keyword={keyword}",
        "limit": 3,
        "offset": 0,
    }
    headers = {
        "User-Agent": UA,
        "Accept": "application/json",
        "ora-irc-cx-userid": str(uuid.uuid4()),
        "ora-irc-language": "en",
        "content-type": "application/vnd.oracle.adf.resourceitem+json;charset=utf-8",
    }
    r = requests.get(url, params=params, headers=headers, timeout=25)
    out = {"status": r.status_code}
    if r.status_code == 200:
        reqs = (r.json() or {}).get("items", [{}])[0].get("requisitionList") or []
        out["count"] = len(reqs)
        out["sample"] = (reqs[0].get("Title") if reqs else "")
    else:
        out["head"] = r.text[:150]
    return out


def wd(host, tenant, site):
    r = requests.post(
        f"{host}/wday/cxs/{tenant}/{site}/jobs",
        json={"appliedFacets": {}, "limit": 3, "offset": 0, "searchText": "intern"},
        headers={"User-Agent": UA, "Accept": "application/json", "Content-Type": "application/json"},
        timeout=20,
    )
    ctype = r.headers.get("content-type") or ""
    if r.status_code == 200 and "json" in ctype:
        d = r.json() or {}
        posts = d.get("jobPostings") or []
        return {"ok": True, "total": d.get("total"), "sample": posts[0].get("title") if posts else ""}
    return {"ok": False, "status": r.status_code, "head": r.text[:100]}


def sniff_html(url):
    r = requests.get(url, headers={"User-Agent": UA}, timeout=30, allow_redirects=True)
    html = r.text[:600_000]
    hits = {}
    for pat, name in [
        (r"boards\.greenhouse\.io/([a-z0-9_-]+)", "gh"),
        (r"jobs\.lever\.co/([a-z0-9_-]+)", "lever"),
        (r"jobs\.ashbyhq\.com/([a-z0-9_-]+)", "ashby"),
        (r"([a-z0-9-]+)\.(wd\d+)\.myworkdayjobs\.com(?:/en-US)?/([A-Za-z0-9_]+)", "wd"),
        (r"icims\.com", "icims"),
        (r"taleo\.net", "taleo"),
        (r"oraclecloud\.com", "oracle"),
    ]:
        m = re.search(pat, html, re.I)
        if m:
            hits[name] = m.groups()
    job_links = len(re.findall(r"/job[s]?/\d+", html, re.I))
    return {"final": r.url, "hits": hits, "job_link_count": job_links, "len": len(html)}


def gs_higher():
    urls = [
        "https://higher.gs.com/api/v1/search?keyword=intern&page=1&pageSize=10",
        "https://higher.gs.com/gateway/api/v1/search?keyword=intern",
        "https://higher.gs.com/campus/api/search?keyword=intern",
    ]
    for u in urls:
        try:
            r = requests.get(u, headers={"User-Agent": UA, "Accept": "application/json"}, timeout=20)
            print("GS", u, r.status_code, r.text[:200])
        except Exception as e:
            print("GS", u, e)
    # sniff campus page for API paths
    r = requests.get("https://higher.gs.com/campus", headers={"User-Agent": UA}, timeout=30)
    apis = sorted(set(re.findall(r'["\'](/api[^"\']+)["\']', r.text)))
    print("GS api paths", apis[:15])


print("=== Oracle ===")
for label, host, site in [
    ("JPM", "jpmc.fa.oraclecloud.com", "CX_1001"),
    ("JPM2", "jpmc.fa.us2.oraclecloud.com", "CX_1001"),
    ("GS", "hdpc.fa.us2.oraclecloud.com", "CX_1"),
]:
    print(label, oracle(host, site))

print("\n=== Workday direct ===")
for label, h, t, s in [
    ("Delta", "https://delta.wd1.myworkdayjobs.com", "delta", "Delta"),
    ("Delta2", "https://delta.wd1.myworkdayjobs.com", "delta", "External"),
    ("Lockheed", "https://lockheedmartin.wd1.myworkdayjobs.com", "lockheedmartin", "LockheedMartin"),
    ("Wells", "https://wellsfargo.wd1.myworkdayjobs.com", "wellsfargo", "WellsFargoJobs"),
    ("Wells2", "https://wellsfargo.wd5.myworkdayjobs.com", "wellsfargo", "External"),
    ("HubSpot", "https://hubspot.wd5.myworkdayjobs.com", "hubspot", "careers"),
    ("GS-WD", "https://goldmansachs.wd1.myworkdayjobs.com", "goldmansachs", "HRSGS"),
]:
    print(label, wd(h, t, s))

print("\n=== HTML sniff ===")
for label, url in [
    ("HubSpot", "https://www.hubspot.com/careers"),
    ("HubSpot jobs", "https://www.hubspot.com/careers/jobs"),
    ("Lockheed", "https://www.lockheedmartinjobs.com/search-jobs"),
    ("Wells", "https://www.wellsfargojobs.com/en/jobs/"),
    ("JPM", "https://careers.jpmorgan.com/us/en/search-results?keywords=intern"),
    ("Delta", "https://www.delta.com/us/en/careers"),
]:
    try:
        print(label, sniff_html(url))
    except Exception as e:
        print(label, "ERR", e)

print("\n=== Goldman higher ===")
gs_higher()

print("\n=== HubSpot GH slugs ===")
for slug in ["hubspot", "hubspotinc", "hubspotjobs"]:
    r = requests.get(f"https://boards-api.greenhouse.io/v1/boards/{slug}/jobs", timeout=15)
    if r.status_code == 200:
        print(slug, len((r.json() or {}).get("jobs") or []))
