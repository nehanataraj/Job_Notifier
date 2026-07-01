#!/usr/bin/env python3
"""Probe HubSpot, Goldman, JPM, Wells, Lockheed, Delta."""

from __future__ import annotations

import json
import re

import requests

UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
)
H = {"User-Agent": UA, "Accept": "application/json"}


def gh(slug: str) -> dict:
    r = requests.get(f"https://boards-api.greenhouse.io/v1/boards/{slug}/jobs", headers=H, timeout=20)
    if r.status_code != 200:
        return {"ok": False, "status": r.status_code}
    jobs = (r.json() or {}).get("jobs") or []
    return {"ok": True, "count": len(jobs), "sample": (jobs[0].get("title") if jobs else "")}


def ash(slug: str) -> dict:
    r = requests.get(f"https://api.ashbyhq.com/posting-api/job-board/{slug}", headers=H, timeout=20)
    if r.status_code != 200:
        return {"ok": False, "status": r.status_code}
    jobs = (r.json() or {}).get("jobs") or []
    return {"ok": True, "count": len(jobs), "sample": (jobs[0].get("title") if jobs else "")}


def wd(host: str, tenant: str, site: str) -> dict:
    try:
        r = requests.post(
            f"{host.rstrip('/')}/wday/cxs/{tenant}/{site}/jobs",
            json={"appliedFacets": {}, "limit": 3, "offset": 0, "searchText": "intern"},
            headers={**H, "Content-Type": "application/json"},
            timeout=20,
        )
        ctype = r.headers.get("content-type") or ""
        if r.status_code == 200 and "json" in ctype:
            data = r.json() or {}
            posts = data.get("jobPostings") or []
            return {
                "ok": True,
                "total": data.get("total"),
                "sample": (posts[0].get("title") if posts else ""),
            }
        return {"ok": False, "status": r.status_code, "ctype": ctype[:40], "head": r.text[:80]}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def sr(slug: str) -> dict:
    r = requests.get(
        f"https://api.smartrecruiters.com/v1/companies/{slug}/postings",
        params={"limit": 3, "q": "intern"},
        headers=H,
        timeout=20,
    )
    if r.status_code != 200:
        return {"ok": False, "status": r.status_code}
    data = r.json() or {}
    content = data.get("content") or []
    return {"ok": True, "total": data.get("totalFound"), "sample": (content[0].get("name") if content else "")}


def sniff(url: str) -> dict:
    r = requests.get(url, headers={"User-Agent": UA}, timeout=30, allow_redirects=True)
    html = r.text[:500_000]
    out = {"final": r.url, "status": r.status_code}
    for pat, key in [
        (r"boards\.greenhouse\.io/([a-z0-9_-]+)", "greenhouse"),
        (r"jobs\.ashbyhq\.com/([a-z0-9_-]+)", "ashby"),
        (r"myworkdayjobs\.com(?:/en-US)?/([A-Za-z0-9_]+)", "wd_site"),
        (r"([a-z0-9-]+)\.(wd\d+)\.myworkdayjobs\.com", "wd_host"),
        (r"smartrecruiters\.com/([A-Za-z0-9_-]+)", "sr"),
        (r"higher\.gs\.com", "gs_higher"),
        (r"oraclecloud\.com", "oracle"),
        (r"api\.greenhouse\.io|grnhse", "gh_embed"),
    ]:
        m = re.search(pat, html, re.I)
        if m:
            out[key] = m.groups()
    return out


def gs_api() -> dict:
    urls = [
        "https://higher.gs.com/api/careers/search?keyword=intern&page=1&pageSize=5",
        "https://higher.gs.com/gateway/api/careers/search?keyword=intern",
        "https://hdpc.fa.us2.oraclecloud.com/hcmRestApi/resources/latest/recruitingCEJobRequisitions?onlyData=true&finder=findReqs;siteNumber=CX_1,keyword=intern&limit=3",
    ]
    results = {}
    for u in urls:
        try:
            r = requests.get(u, headers={**H, "Accept": "application/json"}, timeout=20)
            results[u] = {"status": r.status_code, "head": r.text[:120]}
        except Exception as e:
            results[u] = {"error": str(e)}
    return results


def jpm_oracle() -> dict:
    hosts = [
        ("jpmc.fa.oraclecloud.com", "CX_1001"),
        ("jpmc.fa.us2.oraclecloud.com", "CX_1001"),
    ]
    out = {}
    for host, site in hosts:
        url = f"https://{host}/hcmRestApi/resources/latest/recruitingCEJobRequisitions"
        params = {
            "onlyData": "true",
            "finder": f"findReqs;siteNumber={site},keyword=intern",
            "limit": 3,
            "offset": 0,
        }
        headers = {
            **H,
            "ora-irc-cx-userid": "probe",
            "ora-irc-language": "en",
            "content-type": "application/vnd.oracle.adf.resourceitem+json;charset=utf-8",
        }
        try:
            r = requests.get(url, params=params, headers=headers, timeout=20)
            out[host] = {"status": r.status_code, "head": r.text[:200]}
        except Exception as e:
            out[host] = {"error": str(e)}
    return out


TARGETS = {
    "HubSpot": {
        "url": "https://www.hubspot.com/careers",
        "tries": [
            ("gh", "hubspot"),
            ("ash", "hubspot"),
            ("wd", ("https://hubspot.wd5.myworkdayjobs.com", "hubspot", "HubSpot")),
            ("wd", ("https://hubspot.wd5.myworkdayjobs.com", "hubspot", "External")),
        ],
    },
    "Goldman Sachs": {
        "url": "https://higher.gs.com/campus",
        "tries": [],
    },
    "JPMorgan Chase": {
        "url": "https://careers.jpmorgan.com/us/en/students/programs",
        "tries": [
            ("wd", ("https://jpmc.wd1.myworkdayjobs.com", "jpmc", "JPMorganChase")),
            ("wd", ("https://jpmc.wd5.myworkdayjobs.com", "jpmc", "JPMorganChase")),
            ("wd", ("https://jpmc.wd1.myworkdayjobs.com", "jpmc", "External")),
        ],
    },
    "Wells Fargo": {
        "url": "https://www.wellsfargojobs.com/",
        "tries": [
            ("wd", ("https://wellsfargo.wd5.myworkdayjobs.com", "wellsfargo", "External")),
            ("wd", ("https://wellsfargo.wd1.myworkdayjobs.com", "wellsfargo", "WellsFargoJobs")),
            ("wd", ("https://wf.wd1.myworkdayjobs.com", "wf", "External")),
            ("sr", "WellsFargo"),
        ],
    },
    "Lockheed Martin": {
        "url": "https://www.lockheedmartinjobs.com/search-jobs",
        "tries": [
            ("wd", ("https://lockheedmartin.wd1.myworkdayjobs.com", "lockheedmartin", "LockheedMartin")),
            ("wd", ("https://lockheedmartin.wd1.myworkdayjobs.com", "lockheedmartin", "External")),
            ("wd", ("https://lmco.wd1.myworkdayjobs.com", "lmco", "External")),
            ("sr", "LockheedMartin"),
            ("gh", "lockheedmartin"),
        ],
    },
    "Delta Air Lines": {
        "url": "https://delta.com/us/en/careers",
        "tries": [
            ("wd", ("https://delta.wd1.myworkdayjobs.com", "delta", "Delta")),
            ("wd", ("https://delta.wd1.myworkdayjobs.com", "delta", "External")),
            ("sr", "DeltaAirLines"),
            ("gh", "delta"),
        ],
    },
}


def main() -> None:
    results = {}
    for company, cfg in TARGETS.items():
        print(f"\n=== {company} ===")
        info = {"sniff": sniff(cfg["url"])}
        print("sniff", json.dumps(info["sniff"], default=str)[:300])
        hits = []
        for kind, arg in cfg["tries"]:
            if kind == "gh":
                res = gh(arg)
                label = f"greenhouse:{arg}"
            elif kind == "ash":
                res = ash(arg)
                label = f"ashby:{arg}"
            elif kind == "wd":
                res = wd(*arg)
                label = f"workday:{arg[1]}/{arg[2]}"
            elif kind == "sr":
                res = sr(arg)
                label = f"smartrecruiters:{arg}"
            else:
                continue
            print(f"  {label} -> {res}")
            if res.get("ok"):
                hits.append({"type": kind, "arg": arg, **res})
        info["hits"] = hits
        results[company] = info

    print("\n=== Goldman API ===")
    gs = gs_api()
    print(json.dumps(gs, indent=2)[:1500])
    results["Goldman Sachs"]["gs_api"] = gs

    print("\n=== JPM Oracle ===")
    jpm = jpm_oracle()
    print(json.dumps(jpm, indent=2)[:1500])
    results["JPMorgan Chase"]["oracle"] = jpm


if __name__ == "__main__":
    main()
