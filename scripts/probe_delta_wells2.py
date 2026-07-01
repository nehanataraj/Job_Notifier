#!/usr/bin/env python3
import re
import requests

UA = "Mozilla/5.0"

r = requests.get("https://www.delta.com/careers/search", headers={"User-Agent": UA}, timeout=30)
html = r.text
print("Delta len", len(html))
for pat in ["myworkdayjobs", "workday", "avature", "wd1", "wd5", "jobsearch", "careers"]:
    if pat.lower() in html.lower():
        print(" has", pat)

wd = re.findall(
    r"([a-z0-9-]+)\.(wd\d+)\.myworkdayjobs\.com(?:/en-US)?/([A-Za-z0-9_]+)",
    html,
    re.I,
)
print("wd embeds", wd)

r2 = requests.get(
    "https://www.wellsfargojobs.com/bundles/scripts/ajaxActions.js",
    headers={"User-Agent": UA},
    timeout=30,
)
text = r2.text[:300000]
urls = sorted(set(re.findall(r"/en/[a-zA-Z0-9_/-]+", text)))
print("Wells ajax paths", [u for u in urls if "job" in u.lower()][:20])
