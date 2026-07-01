#!/usr/bin/env python3
import re
import uuid
import requests

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"


def wd_discover(label, base):
    r = requests.get(base, headers={"User-Agent": UA}, timeout=20, allow_redirects=True)
    m = re.search(r"/([A-Za-z][A-Za-z0-9_]+)(?:\?|$)", r.url.replace("/en-US/", "/"))
    site = m.group(1) if m else None
    tenant = base.split("//")[1].split(".")[0]
    host = "/".join(base.split("/")[:3])
    print(f"{label} redirect {r.url} site={site}")
    if site and site not in ("en-US", "jobs"):
        rr = requests.post(
            f"{host}/wday/cxs/{tenant}/{site}/jobs",
            json={"appliedFacets": {}, "limit": 2, "offset": 0, "searchText": "intern"},
            headers={"User-Agent": UA, "Accept": "application/json", "Content-Type": "application/json"},
            timeout=20,
        )
        ctype = rr.headers.get("content-type") or ""
        if rr.status_code == 200 and "json" in ctype:
            d = rr.json() or {}
            posts = d.get("jobPostings") or []
            print(f"  OK total={d.get('total')} sample={(posts[0].get('title') if posts else '')}")
        else:
            print(f"  FAIL {rr.status_code} {rr.text[:80]}")


def oracle_kw(host, site, kw):
    url = f"https://{host}/hcmRestApi/resources/latest/recruitingCEJobRequisitions"
    params = {
        "onlyData": "true",
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
    }
    r = requests.get(url, params=params, headers=headers, timeout=25)
    if r.status_code != 200:
        return kw, r.status_code, 0, ""
    reqs = (r.json() or {}).get("items", [{}])[0].get("requisitionList") or []
    return kw, r.status_code, len(reqs), (reqs[0].get("Title") if reqs else "")


print("=== WD discover ===")
for label, base in [
    ("Delta", "https://delta.wd1.myworkdayjobs.com"),
    ("Lockheed", "https://lockheedmartin.wd1.myworkdayjobs.com"),
    ("Wells", "https://wellsfargo.wd1.myworkdayjobs.com"),
    ("Wells5", "https://wellsfargo.wd5.myworkdayjobs.com"),
    ("HubSpot", "https://hubspot.wd5.myworkdayjobs.com"),
    ("GS", "https://goldmansachs.wd1.myworkdayjobs.com"),
    ("JPM", "https://jpmc.wd1.myworkdayjobs.com"),
]:
    wd_discover(label, base)

print("\n=== Oracle keywords ===")
for host, site in [("jpmc.fa.oraclecloud.com", "CX_1001"), ("hdpc.fa.us2.oraclecloud.com", "CX_1")]:
    for kw in ["intern", "", "summer", "analyst"]:
        print(host, oracle_kw(host, site, kw))

print("\n=== Lockheed BrassRing / custom ===")
r = requests.get(
    "https://www.lockheedmartinjobs.com/search-jobs",
    headers={"User-Agent": UA},
    timeout=30,
)
for pat in [r"brassring", r"icims", r"jobId", r"/job/", r"api[^\"'\s]+job"]:
    ms = re.findall(pat, r.text[:300000], re.I)
    if ms:
        print(pat, len(ms))

print("\n=== Wells taleo ===")
r = requests.get("https://www.wellsfargojobs.com/en/jobs/", headers={"User-Agent": UA}, timeout=30)
for pat in [r"taleo", r"workday", r"icims", r"jobdetails", r"gh_jid"]:
    ms = re.findall(pat, r.text, re.I)
    if ms:
        print(pat, len(ms))

print("\n=== HubSpot GH hubspotjobs sample ===")
r = requests.get("https://boards-api.greenhouse.io/v1/boards/hubspotjobs/jobs", timeout=20)
jobs = (r.json() or {}).get("jobs") or []
intern = [j for j in jobs if "intern" in (j.get("title") or "").lower()]
print("total", len(jobs), "intern", len(intern))
if intern:
    print("sample", intern[0]["title"])
