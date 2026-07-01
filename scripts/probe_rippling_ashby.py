#!/usr/bin/env python3
from playwright.sync_api import sync_playwright
import json, re, requests

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"

# Ashby hosted job board graphql (known pattern)
payload = {
    "operationName": "ApiJobBoardWithTeams",
    "variables": {"organizationHostedJobsPageName": "rippling"},
    "query": """query ApiJobBoardWithTeams($organizationHostedJobsPageName: String!) {
      jobBoard: jobBoardWithTeams(organizationHostedJobsPageName: $organizationHostedJobsPageName) {
        teams { id name parentTeamId }
        jobPostings {
          id title teamId locationName employmentType isListed
          secondaryLocations { locationName }
          compensationTierSummary
        }
      }
    }"""
}
r = requests.post(
    "https://jobs.ashbyhq.com/api/non-user-graphql?op=ApiJobBoardWithTeams",
    json=payload,
    headers={"User-Agent": UA, "Content-Type": "application/json"},
    timeout=25,
)
print("Ashby GQL status", r.status_code)
if r.status_code == 200:
    data = r.json()
    jb = ((data.get("data") or {}).get("jobBoard")) or {}
    posts = jb.get("jobPostings") or []
    print("jobs", len(posts))
    if posts:
        print("sample", posts[0].get("title"))

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page(user_agent=UA)
    caps = []
    page.on("response", lambda r: caps.append((r.url, r.status)) if "ashby" in r.url or "graphql" in r.url else None)
    page.goto("https://www.rippling.com/careers/open-roles", wait_until="domcontentloaded", timeout=120000)
    page.wait_for_timeout(10000)
    rows = page.evaluate("""() => {
        const out = [];
        document.querySelectorAll('a').forEach(a => {
            const t=(a.innerText||'').trim();
            const h=a.href||'';
            if (t && h && /ashbyhq|careers|job/i.test(h) && t.length>5) out.push({t,h});
        });
        return out.slice(0,10);
    }""")
    print("open-roles links", rows)
    for u,s in caps[:8]:
        print(" cap", s, u[:90])
    browser.close()
