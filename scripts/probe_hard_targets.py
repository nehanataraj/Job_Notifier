#!/usr/bin/env python3
"""Probe Tesla, Apple, Meta with browser-like sessions."""

from __future__ import annotations

import json
import re

import requests

UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)
SESSION_HEADERS = {
    "User-Agent": UA,
    "Accept-Language": "en-US,en;q=0.9",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}


def probe_tesla() -> None:
    s = requests.Session()
    s.headers.update(SESSION_HEADERS)
    # warm session
    s.get("https://www.tesla.com/careers", timeout=30)
    r = s.get("https://www.tesla.com/cua-api/apps/careers/state", timeout=30)
    print("TESLA", r.status_code, len(r.text))
    if r.ok:
        d = r.json()
        posts = d.get("posts") or []
        print("posts", len(posts))
        if posts:
            print(json.dumps(posts[0], indent=2)[:700])


def probe_apple() -> None:
    s = requests.Session()
    s.headers.update(SESSION_HEADERS)
    home = s.get("https://jobs.apple.com/en-us/search?search=intern", timeout=30)
    print("APPLE home", home.status_code, home.url)
    csrf = None
    for pat in [
        r'"csrfToken"\s*:\s*"([^"]+)"',
        r'name="csrfToken"\s+value="([^"]+)"',
        r'"token"\s*:\s*"([^"]+)"',
    ]:
        m = re.search(pat, home.text or "")
        if m:
            csrf = m.group(1)
            break
    print("csrf", csrf[:40] if csrf else None)
    headers = {
        "User-Agent": UA,
        "Accept": "application/json",
        "Referer": "https://jobs.apple.com/en-us/search",
    }
    if csrf:
        headers["X-Apple-CSRF-Token"] = csrf
        headers["Cookie"] = f"csrfToken={csrf}"
    r = s.get(
        "https://jobs.apple.com/api/v1/search",
        params={"page": 1, "query": "intern"},
        headers=headers,
        timeout=30,
    )
    print("APPLE api", r.status_code)
    if r.ok:
        print(json.dumps(r.json(), indent=2)[:1200])
    else:
        # try alternate endpoints
        for url in [
            "https://jobs.apple.com/api/role/search",
            "https://jobs.apple.com/api/v1/jobSearch",
        ]:
            r2 = s.get(url, params={"page": 1, "query": "intern"}, headers=headers, timeout=20)
            print(" alt", url, r2.status_code)
            if r2.ok:
                print(json.dumps(r2.json(), indent=2)[:800])
                break


def probe_meta() -> None:
    s = requests.Session()
    s.headers.update(SESSION_HEADERS)
    page = s.get("https://www.metacareers.com/jobs?q=intern", timeout=30)
    print("META page", page.status_code)
    # extract persisted query hash if present
    m = re.search(r'"JobSearchResults","queryId":"([^"]+)"', page.text or "")
    print("queryId", m.group(1) if m else None)
    # try common graphql shapes
    payloads = [
        {
            "operationName": "JobSearchResults",
            "variables": {
                "searchInput": {
                    "q": "intern",
                    "divisions": [],
                    "offices": [],
                    "roles": [],
                    "leadership_levels": [],
                    "saved_search_id": None,
                    "sub_team_id": None,
                    "team_id": None,
                    "teams": [],
                    "is_leadership": None,
                    "is_remote_only": None,
                    "cursor": None,
                    "limit": 5,
                }
            },
            "query": (
                "query JobSearchResults($searchInput: JobSearchInput!) {"
                " job_search(search_input: $searchInput) {"
                "  total_count job_listings { id title locations { city country } }"
                " } }"
            ),
        }
    ]
    for body in payloads:
        r = s.post(
            "https://www.metacareers.com/graphql",
            headers={"Content-Type": "application/json", "User-Agent": UA},
            json=body,
            timeout=30,
        )
        print("META gql", r.status_code)
        if r.ok:
            print(json.dumps(r.json(), indent=2)[:1500])
            return
        print(r.text[:300])


if __name__ == "__main__":
    probe_tesla()
    print("---")
    probe_apple()
    print("---")
    probe_meta()
