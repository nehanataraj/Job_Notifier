#!/usr/bin/env python3
import re
import requests

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
r = requests.get(
    "https://apply.deloitte.com/en_US/careers/SearchJobs",
    headers={"User-Agent": UA},
    timeout=25,
)
print("status", r.status_code)
for pat in [
    r"rest/jobboard[^\"']*",
    r"SearchJobs[^\"']*",
    r"avature[^\"']*",
    r"jobRecordsPerPage[^\"']*",
]:
    ms = re.findall(pat, r.text, re.I)[:5]
    if ms:
        print(pat, ms)

# try common avature REST endpoints
for url in [
    "https://apply.deloitte.com/rest/jobboard/searchjobs?jobRecordsPerPage=5&searchText=intern",
    "https://apply.deloitte.com/en_US/careers/SearchJobs/intern?jobRecordsPerPage=5",
]:
    rr = requests.get(url, headers={"User-Agent": UA, "Accept": "application/json"}, timeout=20)
    print(url, rr.status_code, (rr.headers.get("content-type") or "")[:40], rr.text[:150])
