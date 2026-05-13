#!/usr/bin/env python3
"""Probe public job-board APIs for company slugs (dev helper)."""

from __future__ import annotations

import json
import re
import sys
from typing import Any

import requests

COMPANIES: dict[str, list[str]] = {
    "Google": ["google", "googlellc", "googlecareers", "alphabet"],
    "Meta": ["meta", "facebook", "metacareers", "fb"],
    "Microsoft": ["microsoft"],
    "Amazon": ["amazon", "amazonjobs", "amazonwebservices", "aws"],
    "Apple": ["apple", "appleinc"],
    "NVIDIA": ["nvidia", "nvidiacorporation"],
    "Netflix": ["netflix", "netflixjobs"],
    "Salesforce": ["salesforce", "salesforcecareers"],
    "Adobe": ["adobe", "adobecareers"],
    "LinkedIn": ["linkedin", "linkedininc"],
    "Uber": ["uber", "uberfreight"],
    "Lyft": ["lyft"],
    "Twitter / X": ["twitter", "x", "xcorp"],
    "Snap": ["snap", "snapchat", "snapinc"],
    "Pinterest": ["pinterest", "pinterestinc"],
    "Dropbox": ["dropbox"],
    "Atlassian": ["atlassian"],
    "ServiceNow": ["servicenow", "ServiceNow"],
    "Workday": ["workday", "Workday"],
    "Tesla": ["tesla", "teslamotors"],
    "SpaceX": ["spacex", "SpaceX"],
    "Waymo": ["waymo"],
    "Cruise": ["cruise", "getcruise"],
    "Rivian": ["rivian", "rivianautomotive"],
    "Zoox": ["zoox"],
    "Boston Dynamics": ["bostondynamics", "bostondynamicsinc"],
    "Nuro": ["nuro", "nuroai"],
    "Mobileye": ["mobileye"],
    "Stripe": ["stripe"],
    "Robinhood": ["robinhood", "robinhoodmarkets"],
    "Coinbase": ["coinbase"],
    "Affirm": ["affirm"],
    "Chime": ["chime", "chimefinancial"],
    "Plaid": ["plaid", "plaidinc"],
    "Brex": ["brex", "brexinc"],
    "Bloomberg": ["bloomberg", "bloomberglp"],
    "Ramp": ["ramp", "rampfinancial"],
    "Rippling": ["rippling"],
    "Citadel": ["citadel", "citadelcareers", "citadelsecurities"],
    "Two Sigma": ["twosigma", "twosigmainvestments"],
    "Jane Street": ["janestreet"],
    "D.E. Shaw": ["deshaw", "deshawcareers", "deshawgroup"],
    "Hudson River Trading": ["hudsonrivertrading", "hrt"],
    "Optiver": ["optiver", "optiverus"],
    "Goldman Sachs": ["goldmansachs", "gs"],
    "Morgan Stanley": ["morganstanley"],
    "BlackRock": ["blackrock"],
    "Virtu Financial": ["virtu", "virtufinancial"],
    "Anthropic": ["anthropic"],
    "OpenAI": ["openai", "openaiinc"],
    "Scale AI": ["scaleai", "scale"],
    "Cohere": ["cohere", "cohereai"],
    "Mistral AI": ["mistral", "mistralai"],
    "Perplexity AI": ["perplexity", "perplexityai"],
    "xAI": ["xai", "x-ai"],
    "Codeium / Windsurf": ["codeium", "windsurf", "exafunction"],
    "Hugging Face": ["huggingface", "hugging-face"],
    "Anduril": ["anduril", "andurilindustries"],
    "Palantir": ["palantir", "palantirtechnologies"],
    "L3Harris": ["l3harris", "l3harrisinc"],
    "Leidos": ["leidos"],
    "Booz Allen Hamilton": ["boozallen", "boozallenhamilton"],
    "Notion": ["notion", "notionlabs"],
    "Linear": ["linear", "linearapp"],
    "Vercel": ["vercel"],
    "Airtable": ["airtable"],
    "Figma": ["figma"],
    "Retool": ["retool"],
    "Amplitude": ["amplitude", "amplitudeanalytics"],
    "Datadog": ["datadog"],
    "Snowflake": ["snowflake", "snowflakecomputing"],
    "Databricks": ["databricks"],
}


def gh(slug: str) -> tuple[bool, int]:
    r = requests.get(
        f"https://boards-api.greenhouse.io/v1/boards/{slug}/jobs",
        timeout=20,
    )
    if r.status_code != 200:
        return False, 0
    jobs = (r.json() or {}).get("jobs") or []
    return True, len(jobs)


def lever(slug: str) -> tuple[bool, int]:
    r = requests.get(
        f"https://api.lever.co/v0/postings/{slug}",
        params={"mode": "json"},
        timeout=20,
    )
    if r.status_code != 200:
        return False, 0
    data = r.json()
    if not isinstance(data, list):
        return False, 0
    return True, len(data)


def ashby(slug: str) -> tuple[bool, int]:
    r = requests.get(
        f"https://api.ashbyhq.com/posting-api/job-board/{slug}",
        timeout=20,
    )
    if r.status_code != 200:
        return False, 0
    jobs = (r.json() or {}).get("jobs") or []
    return True, len(jobs)


def sr(slug: str) -> tuple[bool, int]:
    r = requests.get(
        f"https://api.smartrecruiters.com/v1/companies/{slug}/postings",
        params={"limit": 1},
        timeout=20,
    )
    if r.status_code != 200:
        return False, 0
    data = r.json() or {}
    total = int(data.get("totalFound") or 0)
    return True, total


def workable(slug: str) -> tuple[bool, int]:
    r = requests.get(
        f"https://apply.workable.com/{slug}/jobs.md",
        headers={
            "User-Agent": (
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            ),
            "Accept": "text/markdown,*/*;q=0.8",
        },
        timeout=20,
    )
    if r.status_code != 200:
        return False, 0
    ctype = (r.headers.get("content-type") or "").lower()
    text = r.text or ""
    if "markdown" not in ctype and not text.lstrip().startswith("#"):
        return False, 0
    n = len(re.findall(r"\[View\]\(https://apply\.workable\.com/[^)]+\)", text))
    return True, n


def main() -> None:
    hits: list[dict[str, Any]] = []
    for company, slugs in COMPANIES.items():
        best: dict[str, Any] | None = None
        for slug in slugs:
            for kind, fn in [
                ("greenhouse", gh),
                ("lever", lever),
                ("ashby", ashby),
                ("smartrecruiters", sr),
                ("workable", workable),
            ]:
                try:
                    ok, count = fn(slug)
                except Exception:
                    continue
                if ok and count > 0:
                    row = {
                        "company": company,
                        "type": kind,
                        "slug": slug,
                        "count": count,
                    }
                    if best is None or count > best["count"]:
                        best = row
        if best:
            hits.append(best)
            print(
                f"{best['company']}: {best['type']}:{best['slug']} ({best['count']} jobs)",
                flush=True,
            )
        else:
            print(f"{company}: (no public API hit)", flush=True)

    print("\n--- JSON ---")
    print(json.dumps(hits, indent=2))


if __name__ == "__main__":
    main()
