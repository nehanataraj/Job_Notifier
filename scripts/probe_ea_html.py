#!/usr/bin/env python3
import re
import requests

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
for url in [
    "https://www.ea.com/careers",
    "https://www.ea.com/careers/listings",
    "https://ea.avature.net/en_US/careers/SearchJobs",
]:
    try:
        r = requests.get(url, headers={"User-Agent": UA}, timeout=30, allow_redirects=True)
        print(url, "->", r.url, r.status_code, len(r.text))
        titles = re.findall(r'"title"\s*:\s*"([^"]+)"', r.text)[:5]
        links = re.findall(r'href="([^"]*job[^"]*)"', r.text, re.I)[:5]
        print(" titles", titles)
        print(" links", links)
    except Exception as e:
        print(url, e)
