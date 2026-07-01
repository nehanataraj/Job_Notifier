#!/usr/bin/env python3
import re
import requests

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"

SITES = {
    "BAE Systems": ("https://jobs.baesystems.com", "https://jobs.baesystems.com/global/en/search-results"),
    "Warner Bros. Discovery": ("https://careers.wbd.com", "https://careers.wbd.com/global/en/search-results"),
    "Fiserv": ("https://careers.fiserv.com", "https://careers.fiserv.com/us/en/search-results"),
    "UPS (Tech)": ("https://www.jobs-ups.com", "https://www.jobs-ups.com/us/en/search-results"),
    "Splunk": ("https://careers.cisco.com", "https://careers.cisco.com/global/en/splunk"),
}

for name, (base, url) in SITES.items():
    r = requests.get(url, headers={"User-Agent": UA}, timeout=25)
    ref = re.search(r'"refNum"\s*:\s*"([^"]+)"', r.text or "")
    ref = ref.group(1) if ref else None
    print(name, ref, "->", requests.utils.urlparse(r.url).netloc)
