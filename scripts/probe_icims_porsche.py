#!/usr/bin/env python3
import re
import requests

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
H = {
    "User-Agent": UA,
    "Accept": "text/html,application/xhtml+xml",
    "Accept-Language": "en-US,en;q=0.9",
}

for label, url in [
    ("AMD", "https://internal-amd.icims.com/jobs/search?ss=1&searchRelation=keyword_all&searchKeyword=intern"),
    ("ICE", "https://careers-ice.icims.com/jobs/search?ss=1&searchKeyword=intern"),
    ("CFA", "https://careers-chickfila.icims.com/jobs/search?ss=1&searchKeyword=intern"),
]:
    r = requests.get(url, headers=H, timeout=30)
    ids = set(re.findall(r"/jobs/(\d+)", r.text))
    titles = re.findall(r'iCIMS_InfoField_JobTitle.*?<a[^>]+>([^<]+)</a>', r.text, re.S)
    print(label, r.status_code, "ids", len(ids), "titles", len(titles))
    for t in titles[:3]:
        print(" ", t.strip()[:60])

for u in [
    "https://jobs.porsche.com/index.php?ac=search_result&search_criterion_channel=channel_external&search_keyword=intern",
    "https://jobs.porsche.com/global/en/search-results",
]:
    r = requests.get(u, headers=H, timeout=30, allow_redirects=True)
    ref = re.search(r'"refNum"\s*:\s*"([^"]+)"', r.text)
    print("Porsche", r.url, ref.group(1) if ref else "no ref")
