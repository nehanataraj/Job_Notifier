#!/usr/bin/env python3
"""Probe APIs for batch-2 parser targets."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import requests

UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
)

TARGETS = {
    "AMD": "https://careers.amd.com/careers-home",
    "ICE": "https://careers.ice.com/",
    "Chick-fil-A": "https://careers.chick-fil-a.com/",
    "American Express": "https://aexp.eightfold.ai/careers",
    "Activision Blizzard": "https://careers.activisionblizzard.com/",
    "EY": "https://careers.ey.com/",
    "SAP": "https://jobs.sap.com/",
    "Porsche": "https://jobs.porsche.com/",
    "NBCUniversal": "https://www.nbcunicareers.com/",
}


def sniff(url: str) -> dict:
    r = requests.get(url, headers={"User-Agent": UA}, timeout=30, allow_redirects=True)
    html = r.text[:300_000]
    out = {"final": r.url, "status": r.status_code}
    patterns = [
        (r"icims\.com", "icims"),
        (r"eightfold\.ai|/api/pcsx/search", "eightfold"),
        (r"successfactors|sapsf", "successfactors"),
        (r"phenompeople|/widgets/", "phenom"),
        (r"smartrecruiters\.com", "smartrecruiters"),
        (r"myworkdayjobs\.com", "workday"),
        (r"boards\.greenhouse\.io/([a-z0-9_-]+)", "greenhouse"),
        (r"jobs\.ashbyhq\.com/([a-z0-9_-]+)", "ashby"),
        (r"jobs\.lever\.co/([a-z0-9_-]+)", "lever"),
    ]
    for pat, name in patterns:
        m = re.search(pat, html, re.I)
        if m:
            out["ats"] = name
            if m.lastindex:
                out["slug"] = m.group(1)
            break
    wd = re.search(
        r"https://([a-z0-9-]+)\.(wd\d+)\.myworkdayjobs\.com(?:/en-US)?/([A-Za-z][A-Za-z0-9_]+)",
        html,
        re.I,
    )
    if wd:
        out["workday"] = {
            "host": f"https://{wd.group(1)}.{wd.group(2)}.myworkdayjobs.com",
            "tenant": wd.group(1),
            "site": wd.group(3),
        }
    icims = re.search(r"https://([a-z0-9-]+)\.icims\.com", html, re.I)
    if icims:
        out["icims_host"] = f"https://{icims.group(1)}.icims.com"
    ref = re.search(r'"refNum"\s*:\s*"([^"]+)"', html)
    if ref:
        out["ref_num"] = ref.group(1)
    sf = re.search(r"(https://[^\"'\s]+sapsf\.com[^\"'\s]*)", html, re.I)
    if sf:
        out["sf_url"] = sf.group(1)
    sr = re.search(r"api\.smartrecruiters\.com/v1/companies/([^/\"'\s]+)", html, re.I)
    if sr:
        out["sr_slug"] = sr.group(1)
    pcsx = re.search(r"(https://[a-z0-9.-]+/api/pcsx/search)", html, re.I)
    if pcsx:
        out["pcsx_url"] = pcsx.group(1)
    return out


def try_icims(host: str) -> dict:
    for path in [
        "/jobs/search?ss=1&searchRelation=keyword_all&searchKeyword=intern&in_iframe=1",
        "/jobs/search?searchKeyword=intern&in_iframe=1",
    ]:
        try:
            r = requests.get(
                f"{host.rstrip('/')}{path}",
                headers={"User-Agent": UA, "Accept": "application/json,text/html"},
                timeout=30,
            )
            ctype = r.headers.get("content-type", "")
            if "json" in ctype:
                data = r.json()
                jobs = data if isinstance(data, list) else data.get("jobs") or data.get("results") or []
                return {"ok": True, "path": path, "count": len(jobs), "sample": str(jobs[:1])[:200]}
        except Exception as e:
            return {"ok": False, "error": str(e)}
    return {"ok": False}


def try_pcsx(url: str, domain: str) -> dict:
    try:
        r = requests.get(
            url,
            params={"domain": domain, "query": "intern", "start": 0, "count": 5},
            headers={"User-Agent": UA},
            timeout=30,
        )
        data = r.json()
        inner = data.get("data") if isinstance(data.get("data"), dict) else data
        pos = inner.get("positions") or []
        return {"ok": r.status_code == 200, "count": len(pos), "total": inner.get("count")}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def try_sf(url: str) -> dict:
    feeds = [
        url.rstrip("/") + "/search/?q=intern&format=rss",
        url.rstrip("/") + "/search/?q=intern",
    ]
    for feed in feeds:
        try:
            r = requests.get(feed, headers={"User-Agent": UA}, timeout=30)
            if r.status_code == 200 and ("rss" in feed or "<item>" in r.text):
                items = r.text.count("<item>")
                return {"ok": True, "url": feed, "items": items}
        except Exception:
            pass
    return {"ok": False}


def main() -> None:
    results = {}
    for name, url in TARGETS.items():
        info = sniff(url)
        if info.get("icims_host"):
            info["icims_probe"] = try_icims(info["icims_host"])
        if info.get("pcsx_url"):
            dom = url.split("//")[1].split("/")[0].replace("careers.", "").replace("www.", "")
            info["pcsx_probe"] = try_pcsx(info["pcsx_url"], dom)
        if info.get("sf_url"):
            info["sf_probe"] = try_sf(info["sf_url"])
        results[name] = info
        print(name, json.dumps(info, indent=2)[:800])
        print("---")

    Path("probe_batch2.json").write_text(json.dumps(results, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
