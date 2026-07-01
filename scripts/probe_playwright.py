#!/usr/bin/env python3
"""Probe bot-protected sites via Playwright network capture."""

from __future__ import annotations

import json
import re
from typing import Any

from playwright.sync_api import sync_playwright

TARGETS = {
    "Tesla": "https://www.tesla.com/careers/search?query=intern",
    "Apple": "https://jobs.apple.com/en-us/search?search=intern",
    "Meta": "https://www.metacareers.com/jobs?q=intern",
    "Bank of America": "https://careers.bankofamerica.com/en-us/search-results?keywords=intern",
}


def capture(name: str, url: str) -> dict[str, Any]:
    hits: list[dict[str, Any]] = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        def on_response(resp):
            try:
                ct = (resp.headers.get("content-type") or "").lower()
                u = resp.url
                if resp.status != 200:
                    return
                if not any(k in u for k in ("api", "graphql", "jobs", "search", "wday", "cxs", "careers/state", "role")):
                    return
                if "json" not in ct and "graphql" not in ct:
                    return
                body = resp.json()
                hits.append({"url": u, "keys": list(body.keys())[:8] if isinstance(body, dict) else type(body).__name__})
            except Exception:
                pass
        page.on("response", on_response)
        try:
            page.goto(url, wait_until="networkidle", timeout=60000)
        except Exception as e:
            print(name, "nav error", e)
        browser.close()
    return {"name": name, "hits": hits[:15]}


if __name__ == "__main__":
    for name, url in TARGETS.items():
        result = capture(name, url)
        print(f"\n=== {name} ===")
        for h in result["hits"]:
            print(h["url"][:120], h.get("keys"))
