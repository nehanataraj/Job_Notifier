#!/usr/bin/env python3
import re
import requests

UA = "Mozilla/5.0"
r = requests.get("https://www.delta.com/careers/search", headers={"User-Agent": UA}, timeout=30, allow_redirects=True)
html = r.text
feeds = sorted(set(re.findall(r"https?://[^\"'\s<>]+avature[^\"'\s<>]*", html, re.I)))
print("avature urls", feeds[:10])
jobs = sorted(set(re.findall(r"/job/[^\"'\s<>]+", html, re.I)))
print("job paths", jobs[:8])

# Wells: try search results HTML endpoint
for url in [
    "https://www.wellsfargojobs.com/en/jobs/search-results?q=intern",
    "https://www.wellsfargojobs.com/api/jobs/search?q=intern",
    "https://www.wellsfargojobs.com/en/jobs/search?search=intern&page=1",
]:
    try:
        rr = requests.get(url, headers={"User-Agent": UA, "Accept": "application/json,text/html"}, timeout=25)
        print(url, rr.status_code, (rr.headers.get("content-type") or "")[:40], len(rr.text))
        if "json" in (rr.headers.get("content-type") or ""):
            print(" ", rr.text[:200])
    except Exception as e:
        print(url, e)
