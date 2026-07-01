#!/usr/bin/env python3
"""
Fingerprint a company's careers page and emit the JSON endpoint.

Usage:
    python scripts/ats_detect.py https://boards.greenhouse.io/figma
    from scripts.ats_detect import detect
    info = detect("https://careers.qualcomm.com/")
"""

from __future__ import annotations

import re
from typing import Any
from urllib.parse import urlparse

import requests

UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
)

HOST_RULES: list[tuple[str, str]] = [
    (r"\.myworkdayjobs\.com$", "workday"),
    (r"\.myworkdaysite\.com$", "workday"),
    (r"(^|\.)boards\.greenhouse\.io$", "greenhouse"),
    (r"(^|\.)job-boards\.greenhouse\.io$", "greenhouse"),
    (r"(^|\.)jobs\.lever\.co$", "lever"),
    (r"(^|\.)jobs\.ashbyhq\.com$", "ashby"),
    (r"smartrecruiters\.com$", "smartrecruiters"),
    (r"(^|\.)apply\.workable\.com$", "workable"),
    (r"\.workable\.com$", "workable"),
    (r"\.recruitee\.com$", "recruitee"),
    (r"\.jobs\.personio\.(com|de)$", "personio"),
    (r"\.teamtailor\.com$", "teamtailor"),
    (r"icims\.com$", "icims"),
    (r"oraclecloud\.com$", "oracle_orc"),
    (r"taleo\.net$", "taleo"),
    (r"(successfactors|sapsf)\.(com|eu)$", "successfactors"),
    (r"\.avature\.net$", "avature"),
    (r"(^|\.)jobs\.jobvite\.com$", "jobvite"),
    (r"usajobs\.gov$", "usajobs"),
    (r"(^|\.)amazon\.jobs$", "amazon"),
    (r"(^|\.)tesla\.com$", "tesla"),
    (r"(^|\.)valvesoftware\.com$", "valve"),
]

HTML_RULES: list[tuple[str, str]] = [
    (r"eightfold\.ai|/api/apply/v2/jobs|/api/pcsx/search", "eightfold"),
    (r"phenompeople|phenom\.com|/widgets/", "phenom"),
    (r"boards\.greenhouse\.io|grnhse", "greenhouse"),
    (r"jobs\.lever\.co", "lever"),
    (r"ashbyhq\.com", "ashby"),
    (r"myworkdayjobs\.com", "workday"),
    (r"smartrecruiters\.com", "smartrecruiters"),
    (r"icims\.com", "icims"),
    (r"avature", "avature"),
    (r"successfactors|sapsf", "successfactors"),
    (r"usajobs\.gov", "usajobs"),
    (r"cua-api/apps/careers", "tesla"),
]


def _workday_from_html(html: str) -> tuple[str, str, str] | None:
    m = re.search(
        r"https://([a-z0-9-]+)\.(wd\d+)\.myworkdayjobs\.com(?:/en-US)?/([A-Za-z][A-Za-z0-9_]+)",
        html,
        re.I,
    )
    if not m:
        return None
    tenant, wd, site = m.group(1), m.group(2), m.group(3)
    host = f"https://{tenant}.{wd}.myworkdayjobs.com"
    return host, tenant, site


def _endpoint(
    ats: str, host: str, path: str, html: str = ""
) -> tuple[str | None, str, str | None, dict[str, Any]]:
    extra: dict[str, Any] = {}
    slug: str | None = None

    if ats == "workday":
        m = re.match(r"([^.]+)\.(wd\d+)\.myworkdayjobs\.com", host)
        site_m = re.search(r"/([^/?#]+)", path.strip("/"))
        if m:
            tenant, wd = m.group(1), m.group(2)
            sitename = site_m.group(1) if site_m else "External"
            if sitename.lower() in ("en-us", "en-gb", "fr-fr", "jobs", "job"):
                wd_html = _workday_from_html(html)
                if wd_html:
                    host, tenant, sitename = wd_html
            extra = {"host": host, "tenant": tenant, "site": sitename}
            ep = f"{host.rstrip('/')}/wday/cxs/{tenant}/{sitename}/jobs"
            if not ep.startswith("http"):
                ep = f"https://{ep.lstrip('/')}"
            return ep, "POST", tenant, extra
        wd_html = _workday_from_html(html)
        if wd_html:
            host, tenant, sitename = wd_html
            extra = {"host": host, "tenant": tenant, "site": sitename}
            ep = f"{host.rstrip('/')}/wday/cxs/{tenant}/{sitename}/jobs"
            return ep, "POST", tenant, extra
        return None, "POST", None, extra

    if ats == "greenhouse":
        slug = path.strip("/").split("/")[0] or None
        if not slug:
            m = re.search(r"boards\.greenhouse\.io/([a-z0-9_-]+)", html, re.I)
            slug = m.group(1) if m else None
        if slug:
            return (
                f"https://boards-api.greenhouse.io/v1/boards/{slug}/jobs",
                "GET",
                slug,
                {"board_token": slug},
            )

    if ats == "lever":
        slug = path.strip("/").split("/")[0] or None
        if not slug:
            m = re.search(r"jobs\.lever\.co/([a-z0-9_-]+)", html, re.I)
            slug = m.group(1) if m else None
        if slug:
            return (
                f"https://api.lever.co/v0/postings/{slug}?mode=json",
                "GET",
                slug,
                {"company_slug": slug},
            )

    if ats == "ashby":
        slug = path.strip("/").split("/")[0] or None
        if not slug:
            m = re.search(r"jobs\.ashbyhq\.com/([a-z0-9_-]+)", html, re.I)
            slug = m.group(1) if m else None
        if slug:
            return (
                f"https://api.ashbyhq.com/posting-api/job-board/{slug}",
                "GET",
                slug,
                {"board_slug": slug},
            )

    if ats == "smartrecruiters":
        slug = path.strip("/").split("/")[0] or None
        if slug:
            return (
                f"https://api.smartrecruiters.com/v1/companies/{slug}/postings",
                "GET",
                slug,
                {"company_id": slug},
            )

    if ats == "amazon":
        return "https://www.amazon.jobs/en/search.json", "GET", "amazon", {}

    if ats == "usajobs":
        return "https://data.usajobs.gov/api/search", "GET", None, {}

    if ats == "tesla":
        return "https://www.tesla.com/cua-api/apps/careers/state", "GET", "tesla", {}

    if ats == "valve":
        return "https://www.valvesoftware.com/en/jobs", "GET", "valve", {}

    if ats == "eightfold":
        m = re.search(r"https://([a-z0-9.-]+)/api/(?:pcsx/search|apply/v2/jobs)", html, re.I)
        api_host = m.group(1) if m else host
        domain_guess = (
            host.replace("careers.", "").replace("jobs.", "").replace("www.", "")
        )
        if "." not in domain_guess:
            domain_guess = f"{domain_guess}.com"
        list_url = f"https://{api_host}/api/pcsx/search"
        extra = {"list_url": list_url, "domain": domain_guess, "query": "intern"}
        return list_url, "GET", domain_guess, extra

    if ats == "oracle_orc":
        m = re.search(r"([a-z0-9.-]+\.oraclecloud\.com)", html + host, re.I)
        if m:
            extra = {"host": m.group(1)}
        return None, "GET", None, extra

    return None, "GET", slug, extra


def detect(url: str, timeout: int = 20) -> dict[str, Any]:
    try:
        r = requests.get(
            url,
            headers={"User-Agent": UA},
            timeout=timeout,
            allow_redirects=True,
        )
        final = r.url
        html = r.text[:200_000]
        status = r.status_code
    except requests.RequestException as e:
        return {"ats": "error", "reason": str(e), "url": url}

    host = urlparse(final).netloc.lower()
    path = urlparse(final).path

    ats: str | None = None
    for pat, name in HOST_RULES:
        if re.search(pat, host):
            ats = name
            break
    if ats is None:
        for pat, name in HTML_RULES:
            if re.search(pat, html, re.I):
                ats = name
                break

    if ats is None:
        return {
            "ats": "unknown",
            "final_url": final,
            "host": host,
            "status": status,
            "hint": "DevTools > Network > Fetch/XHR, reload, Copy as cURL.",
        }

    endpoint, method, slug, extra = _endpoint(ats, host, path, html)
    out: dict[str, Any] = {
        "ats": ats,
        "slug": slug,
        "final_url": final,
        "endpoint": endpoint,
        "method": method,
        "status": status,
        "config": extra,
    }
    return out


def probe_endpoint(info: dict[str, Any], timeout: int = 20) -> dict[str, Any]:
    """Hit detected endpoint; return job count if JSON works."""
    endpoint = info.get("endpoint")
    if not endpoint:
        return {"ok": False, "reason": "no endpoint"}
    method = (info.get("method") or "GET").upper()
    ats = info.get("ats")
    headers = {"User-Agent": UA, "Accept": "application/json"}
    try:
        if method == "POST" and ats == "workday":
            cfg = info.get("config") or {}
            r = requests.post(
                endpoint,
                json={
                    "appliedFacets": {},
                    "limit": 1,
                    "offset": 0,
                    "searchText": "intern",
                },
                headers={**headers, "Content-Type": "application/json"},
                timeout=timeout,
            )
        else:
            r = requests.get(endpoint, headers=headers, timeout=timeout)
        ctype = (r.headers.get("content-type") or "").lower()
        if r.status_code != 200:
            return {"ok": False, "status": r.status_code}
        if "json" not in ctype:
            return {"ok": False, "status": r.status_code, "reason": "not-json", "ctype": ctype}
        data = r.json()
        if ats == "workday":
            count = int(data.get("total") or 0)
        elif ats == "greenhouse":
            count = len((data or {}).get("jobs") or [])
        elif ats == "lever" and isinstance(data, list):
            count = len(data)
        elif ats == "ashby":
            count = len((data or {}).get("jobs") or [])
        elif ats == "smartrecruiters":
            count = int((data or {}).get("totalFound") or 0)
        elif ats == "amazon":
            count = int((data or {}).get("hits") or 0)
        elif ats == "tesla":
            posts = (data or {}).get("posts") or []
            count = len(posts) if isinstance(posts, list) else 0
        elif ats == "eightfold" or ats == "pcsx":
            payload = data or {}
            inner = payload.get("data") if isinstance(payload.get("data"), dict) else payload
            count = int(inner.get("count") or len(inner.get("positions") or []))
        else:
            count = 0
        return {"ok": True, "status": 200, "count": count}
    except Exception as e:
        return {"ok": False, "reason": str(e)}


if __name__ == "__main__":
    import json
    import sys

    for u in sys.argv[1:]:
        info = detect(u)
        if info.get("endpoint"):
            info["probe"] = probe_endpoint(info)
        print(json.dumps(info, indent=2))
