#!/usr/bin/env python3
"""Quick GH/Ashby/Lever slug probe for unknown missed companies."""
import requests

SLUGS = {
    "Retool": ["retool"],
    "Rippling": ["rippling"],
    "Weights & Biases": ["wandb", "weightsandbiases"],
    "Snyk": ["snyk"],
    "SentinelOne": ["sentinelone"],
    "HashiCorp": ["hashicorp"],
    "Shopify": ["shopify"],
    "Atlassian": ["atlassian"],
    "HubSpot": ["hubspot"],
    "Intuit": ["intuit"],
    "Fortinet": ["fortinet"],
    "Etsy": ["etsy"],
    "Two Sigma": ["twosigma"],
    "Citadel": ["citadel", "citadelsecurities"],
    "Ubisoft": ["ubisoft"],
    "The Boring Company": ["theboringcompany", "boringcompany"],
}

for company, slugs in SLUGS.items():
    for s in slugs:
        for kind, url in [
            ("gh", f"https://boards-api.greenhouse.io/v1/boards/{s}/jobs"),
            ("ash", f"https://api.ashbyhq.com/posting-api/job-board/{s}"),
            ("lev", f"https://api.lever.co/v0/postings/{s}?mode=json"),
        ]:
            try:
                r = requests.get(url, timeout=12)
                if r.status_code != 200:
                    continue
                if kind == "gh":
                    n = len((r.json() or {}).get("jobs") or [])
                elif kind == "ash":
                    n = len((r.json() or {}).get("jobs") or [])
                else:
                    n = len(r.json()) if isinstance(r.json(), list) else 0
                if n:
                    print(f"{company}: {kind}:{s} -> {n}")
            except Exception:
                pass
