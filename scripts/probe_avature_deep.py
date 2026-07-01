#!/usr/bin/env python3
import json
import re
import requests

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
s = requests.Session()
s.headers.update({"User-Agent": UA})

for name, url in [
    ("Deloitte", "https://apply.deloitte.com/en_US/careers/SearchJobs/?jobRecordsPerPage=20&jobOffset=0"),
    ("Deloitte feed", "https://apply.deloitte.com/en_US/careers/SearchJobs/feed/?jobRecordsPerPage=20&jobOffset=0"),
    ("EA", "https://www.ea.com/careers/listings?type=new-grad"),
]:
    print(f"\n=== {name} ===")
    r = s.get(url, timeout=30)
    ct = r.headers.get("content-type", "")
    print(url, r.status_code, ct[:40], len(r.text))
    if "json" in ct:
        print(r.text[:500])
    elif "xml" in ct or r.text.strip().startswith("<?xml"):
        print(r.text[:400])
    else:
        # count job rows in HTML
        rows = len(re.findall(r"jobTitle|job-title|data-job-id|JobDetail", r.text, re.I))
        print("html job markers", rows)
        links = re.findall(r'href="([^"]*JobDetail[^"]*)"', r.text, re.I)[:5]
        print("links", links)

# Deloitte search with keyword
for url in [
    "https://apply.deloitte.com/en_US/careers/SearchJobs/intern?jobRecordsPerPage=20",
    "https://apply.deloitte.com/en_US/careers/SearchJobs?jobRecordsPerPage=20&searchKeyword=intern",
]:
    r = s.get(url, timeout=25)
    titles = re.findall(r'class="article__header__text__title[^"]*"[^>]*>([^<]+)<', r.text)
    if not titles:
        titles = re.findall(r'<h3[^>]*>([^<]+)</h3>', r.text)[:10]
    print(url, r.status_code, "titles", titles[:5])
