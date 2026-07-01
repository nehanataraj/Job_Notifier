#!/usr/bin/env python3
import requests

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"

CANDIDATES = [
    ("Qualcomm", "https://careers.qualcomm.com/api/pcsx/search", "qualcomm.com"),
    ("Citi", "https://jobs.citi.com/api/pcsx/search", "citi.com"),
    ("Citi", "https://citi.eightfold.ai/api/pcsx/search", "citi.com"),
    ("American Express", "https://aexp.eightfold.ai/api/pcsx/search", "americanexpress.com"),
    ("American Express", "https://aexp.eightfold.ai/api/pcsx/search", "aexp.com"),
    ("Activision Blizzard", "https://activision.eightfold.ai/api/pcsx/search", "activisionblizzard.com"),
    ("Activision Blizzard", "https://careers.activisionblizzard.com/api/pcsx/search", "activisionblizzard.com"),
]

for name, url, domain in CANDIDATES:
    try:
        r = requests.get(
            url,
            params={"domain": domain, "query": "intern", "start": 0, "count": 3},
            headers={"User-Agent": UA},
            timeout=20,
        )
        count = 0
        if r.ok:
            data = r.json() or {}
            inner = data.get("data") if isinstance(data.get("data"), dict) else data
            count = int(inner.get("count") or len(inner.get("positions") or []))
        print(f"{name}: {url} domain={domain} -> {r.status_code} count={count}")
    except Exception as e:
        print(f"{name}: {url} ERR {e}")
