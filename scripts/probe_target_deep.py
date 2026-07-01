#!/usr/bin/env python3
import json
import uuid
import requests

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"

def oracle(host, site, kw="intern"):
    url = f"https://{host}/hcmRestApi/resources/latest/recruitingCEJobRequisitions"
    params = {
        "onlyData": "true",
        "expand": "requisitionList.workLocation",
        "finder": f"findReqs;siteNumber={site},keyword={kw}",
        "limit": 5,
        "offset": 0,
    }
    headers = {
        "User-Agent": UA,
        "Accept": "application/json",
        "ora-irc-cx-userid": str(uuid.uuid4()),
        "ora-irc-language": "en",
        "content-type": "application/vnd.oracle.adf.resourceitem+json;charset=utf-8",
        "Referer": f"https://{host}/hcmUI/CandidateExperience/en/sites/{site}/",
    }
    r = requests.get(url, params=params, headers=headers, timeout=25)
    if r.status_code != 200:
        return site, r.status_code, 0, ""
    reqs = (r.json() or {}).get("items", [{}])[0].get("requisitionList") or []
    return site, r.status_code, len(reqs), (reqs[0].get("Title") if reqs else "")

print("=== DELL Oracle ===")
host = "iawmqy.fa.ocs.oraclecloud.com"
for site in ["careers", "CX_1", "CX_1001", "CX_2001", "Dell", "External"]:
    print(oracle(host, site))

# also try without keyword
for finder in ["findReqs;siteNumber=careers", "findReqs;siteNumber=careers,keyword=intern"]:
    url = f"https://{host}/hcmRestApi/resources/latest/recruitingCEJobRequisitions"
    params = {"onlyData": "true", "expand": "requisitionList.workLocation", "finder": finder, "limit": 5, "offset": 0}
    headers = {"User-Agent": UA, "Accept": "application/json", "ora-irc-cx-userid": str(uuid.uuid4()), "ora-irc-language": "en", "content-type": "application/vnd.oracle.adf.resourceitem+json;charset=utf-8"}
    r = requests.get(url, params=params, headers=headers, timeout=25)
    reqs = (r.json() or {}).get("items", [{}])[0].get("requisitionList") or [] if r.status_code == 200 else []
    print("finder", finder, r.status_code, len(reqs))

print("\n=== BAIN API ===")
for path in [
    "https://www.bain.com/en/api/jobsearch/keyword/get?start=0&results=10&filters=&searchValue=intern",
    "https://www.bain.com/en/api/jobsearch/keyword/get?start=0&results=10&filters=&searchValue=",
]:
    r = requests.get(path, headers={"User-Agent": UA, "Accept": "application/json"}, timeout=25)
    print(path[-60:], r.status_code)
    if r.status_code == 200:
        try:
            d = r.json()
            print(" keys", list(d.keys())[:8])
            jobs = d.get("results") or d.get("jobs") or d.get("data") or []
            if isinstance(jobs, dict):
                jobs = jobs.get("results") or []
            print(" count", len(jobs) if isinstance(jobs, list) else d)
            if isinstance(jobs, list) and jobs:
                print(" sample", str(jobs[0])[:120])
        except Exception:
            print(" ", r.text[:200])

print("\n=== MCKINSEY ===")
for url in [
    "https://www.mckinsey.com/careers/search-jobs",
    "https://mckinsey.avature.net/en_US/careers/SearchJobs/feed/?jobRecordsPerPage=10&jobOffset=0",
    "https://eyglobal.yello.co/job_boards/c1riT--B2O-KySgYWsZO1Q?format=rss",
]:
    try:
        r = requests.get(url, headers={"User-Agent": UA}, timeout=25, allow_redirects=True)
        print(url[:70], r.status_code, len(r.text), "items", r.text.count("<item>"))
    except Exception as e:
        print(url[:50], e)

print("\n=== SHOPIFY ===")
for url in [
    "https://www.shopify.com/careers/search?query=intern",
    "https://www.shopify.com/careers/search.json?query=intern",
]:
    r = requests.get(url, headers={"User-Agent": UA, "Accept": "application/json"}, timeout=25)
    print(url, r.status_code, (r.headers.get("content-type") or "")[:40], r.text[:150])

print("\n=== RIPPLING ===")
for url in [
    "https://api.ashbyhq.com/posting-api/job-board/rippling",
    "https://boards-api.greenhouse.io/v1/boards/rippling/jobs",
    "https://api.lever.co/v0/postings/rippling?mode=json",
    "https://jobs.ashbyhq.com/rippling",
    "https://www.rippling.com/careers/open-roles",
]:
    try:
        r = requests.get(url, headers={"User-Agent": UA}, timeout=20, allow_redirects=True)
        print(url[:60], r.status_code, len(r.text))
    except Exception as e:
        print(url[:40], e)
