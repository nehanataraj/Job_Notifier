#!/usr/bin/env python3
import re
import requests

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
r = requests.get("https://www.valvesoftware.com/en/jobs", headers={"User-Agent": UA}, timeout=20)
t = r.text
print("status", r.status_code, "len", len(t))
print("intern mentions", len(re.findall("intern", t, re.I)))
print("job links", re.findall(r'href="(/en/jobs/[^"]+)"', t)[:10])
print("h tags", re.findall(r"<h[1-4][^>]*>([^<]+)</h[1-4]>", t, re.I)[:15])
print("json script", "application/json" in t)
for m in re.findall(r"<script[^>]*>(\{.*?\})</script>", t[:50000], re.S)[:2]:
    print("script blob", m[:200])
