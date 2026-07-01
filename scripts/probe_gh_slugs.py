#!/usr/bin/env python3
import requests

slugs = [
    "snyk", "hashicorp", "retool", "rippling", "shopify", "twosigma",
    "citadel", "citadelsecurities", "wandb", "sentinelone", "fortinet",
    "etsy", "hubspot", "atlassian", "intuit", "yelp", "amd", "qualcomm",
]
for s in slugs:
    r = requests.get(f"https://boards-api.greenhouse.io/v1/boards/{s}/jobs", timeout=12)
    if r.status_code == 200:
        n = len((r.json() or {}).get("jobs") or [])
        if n:
            print(f"greenhouse:{s} -> {n}")
