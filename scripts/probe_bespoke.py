#!/usr/bin/env python3
import json
import requests

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"

# Tesla
r = requests.get(
    "https://www.tesla.com/cua-api/apps/careers/state",
    headers={"User-Agent": UA},
    timeout=30,
)
print("TESLA", r.status_code)
if r.ok:
    d = r.json()
    print("keys", list(d.keys())[:10])
    posts = d.get("posts") or d.get("jobs") or []
    print("posts", len(posts) if isinstance(posts, list) else type(posts))
    if posts:
        print("sample", json.dumps(posts[0], indent=2)[:600])

# Apple
r2 = requests.get(
    "https://jobs.apple.com/api/role/search",
    params={"page": 1, "query": "intern"},
    headers={"User-Agent": UA, "Accept": "application/json"},
    timeout=30,
)
print("APPLE", r2.status_code)
if r2.ok:
    print(json.dumps(r2.json(), indent=2)[:1000])
else:
    print(r2.text[:400])

# Meta
query = (
    "query JobSearchResults($searchInput: JobSearchInput!) {"
    "  job_search(search_input: $searchInput) {"
    "    total_count"
    "    job_listings { id title locations { city country } }"
    "  }"
    "}"
)
r3 = requests.post(
    "https://www.metacareers.com/graphql",
    headers={"User-Agent": UA, "Content-Type": "application/json"},
    json={
        "operationName": "JobSearchResults",
        "variables": {"searchInput": {"query": "intern", "limit": 2}},
        "query": query,
    },
    timeout=30,
)
print("META", r3.status_code)
if r3.ok:
    print(json.dumps(r3.json(), indent=2)[:1500])
else:
    print(r3.text[:400])
