#!/usr/bin/env python3
"""
Poll configured job boards, remember seen postings in SQLite, notify via Telegram.
"""

from __future__ import annotations

import argparse
import codecs
import json
import os
import re
import sqlite3
import sys
import time
import uuid
import xml.etree.ElementTree as ET
from pathlib import Path
from html import escape as html_escape
from typing import Any
from urllib.parse import parse_qs, unquote, urlparse

import requests
from dotenv import load_dotenv

# Load `.env` from this folder when you run locally (never commit `.env`).
load_dotenv(Path(__file__).resolve().parent / ".env")

STATE_DB = os.environ.get("STATE_DB_PATH", "./state.db")
CONFIG_PATH = os.environ.get("CONFIG_PATH", "./config.json")


def load_config(path: str) -> dict[str, Any]:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def get_env(name: str) -> str:
    v = os.environ.get(name, "").strip()
    if not v:
        print(f"Missing required environment variable: {name}", file=sys.stderr)
        sys.exit(1)
    return v


def init_db(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS seen_jobs (
            source_key TEXT NOT NULL,
            job_id TEXT NOT NULL,
            title TEXT,
            url TEXT,
            first_seen REAL NOT NULL,
            PRIMARY KEY (source_key, job_id)
        )
        """
    )
    conn.commit()


def already_seen(conn: sqlite3.Connection, source_key: str, job_id: str) -> bool:
    row = conn.execute(
        "SELECT 1 FROM seen_jobs WHERE source_key = ? AND job_id = ?",
        (source_key, job_id),
    ).fetchone()
    return row is not None


def mark_seen(
    conn: sqlite3.Connection,
    source_key: str,
    job_id: str,
    title: str,
    url: str,
) -> None:
    conn.execute(
        """
        INSERT OR IGNORE INTO seen_jobs (source_key, job_id, title, url, first_seen)
        VALUES (?, ?, ?, ?, ?)
        """,
        (source_key, job_id, title, url, time.time()),
    )
    conn.commit()


def title_matches(title: str, keywords: list[str]) -> bool:
    t = title.lower()
    for k in keywords:
        kl = k.lower()
        if kl == "intern":
            if re.search(r"\bintern\b", t):
                return True
        elif kl in t:
            return True
    return False


# US state / DC codes for "City, ST" style locations (Greenhouse, Lever, etc.).
US_STATE_CODES: set[str] = {
    "AL", "AK", "AZ", "AR", "CA", "CO", "CT", "DE", "DC", "FL", "GA", "HI", "ID",
    "IL", "IN", "IA", "KS", "KY", "LA", "ME", "MD", "MA", "MI", "MN", "MS", "MO",
    "MT", "NE", "NV", "NH", "NJ", "NM", "NY", "NC", "ND", "OH", "OK", "OR", "PA",
    "RI", "SC", "SD", "TN", "TX", "UT", "VT", "VA", "WA", "WV", "WI", "WY", "PR",
}

# Canadian provinces — trailing ", ON" is not a US location.
CA_PROVINCE_CODES: set[str] = {
    "ON", "QC", "BC", "AB", "SK", "MB", "NL", "NS", "NB", "PE", "YT", "NT", "NU",
}

_US_POSITIVE_RE = re.compile(
    r"united states(\s+of\s+america)?|(^|[,;|])\s*us\s*($|[,;|])|\busa\b|\bu\.s\.a\.?\b|"
    r"\bu\.s\.(?![a-z])|\(\s*us\s*\)|\(\s*usa\s*\)|\b(?:us|usa)\s+remote\b|\bremote[^\n,]{0,24}\b(?:us|usa)\b",
    re.I,
)

_NON_US_REGION_RE = re.compile(
    r"\b(?:india|china|canada|ireland|israel|australia|germany|france|japan|"
    r"singapore|mexico|brazil|spain|italy|netherlands|switzerland|sweden|poland|"
    r"belgium|hungary|romania|croatia|serbia|ukraine|russia|philippines|indonesia|"
    r"malaysia|thailand|vietnam|portugal|austria|finland|norway|denmark|greece|"
    r"taiwan|colombia|chile|argentina|peru|south\s+africa|new\s+zealand|hong\s+kong|"
    r"south\s+korea|korea|united\s+kingdom|uk|"
    r"bengaluru|bangalore|hyderabad|pune|mumbai|delhi|chennai|kolkata|noida|"
    r"gurgaon|dubai|tel\s+aviv|zurich|stockholm|amsterdam|munich|frankfurt|"
    r"paris|berlin|tokyo|sydney|melbourne|shanghai|beijing|shenzhen|moscow|"
    r"warsaw|dublin|lisbon|madrid|barcelona|rome|milan|vienna|prague|budapest|"
    r"manila|jakarta|bangkok|ho\s+chi\s+minh|hanoi|kuala\s+lumpur|"
    r"montreal|toronto|vancouver|ottawa|calgary|edmonton|waterloo|"
    r"são\s+paulo|sao\s+paulo|mexico\s+city|buenos\s+aires|bogotá|bogota|"
    r"johannesburg|cape\s+town)\b",
    re.I,
)

_US_STATE_INLINE_RE = re.compile(
    r",\s*(" + "|".join(sorted(US_STATE_CODES)) + r")\b",
    re.I,
)

US_MAJOR_METROS: tuple[str, ...] = (
    "san francisco",
    "new york city",
    "new york",
    "los angeles",
    "chicago",
    "seattle",
    "austin",
    "boston",
    "denver",
    "atlanta",
    "miami",
    "philadelphia",
    "washington",
    "houston",
    "phoenix",
    "dallas",
    "detroit",
    "minneapolis",
    "portland",
    "cupertino",
    "mountain view",
    "palo alto",
    "redmond",
    "sunnyvale",
    "menlo park",
    "san diego",
    "san jose",
    "charlotte",
    "nashville",
    "pittsburgh",
    "salt lake",
)


def location_filter_wants_us_only(config: dict[str, Any]) -> bool:
    lf = config.get("location_filter")
    if not lf or not lf.get("countries"):
        return False
    codes = {str(c).strip().upper() for c in lf["countries"] if str(c).strip()}
    return "US" in codes or "USA" in codes


def job_matches_us_location(job: dict[str, Any], title: str) -> bool:
    """Heuristic: job has a US location signal. False positives/negatives are possible."""
    cc = (job.get("country_code") or "").strip().lower()
    if cc:
        return cc in ("us", "usa")

    gloc = (job.get("google_country") or "").strip().upper()
    if gloc:
        return gloc == "US"

    hints = [str(h).strip() for h in (job.get("location_hints") or []) if str(h).strip()]
    blob = " | ".join(hints + [title]).lower()

    if _US_POSITIVE_RE.search(blob):
        return True

    for h in hints:
        ht = h.strip()
        if re.match(r"^US\s*,", ht, re.I):
            return True
        if re.search(r",\s*US\s*$", ht, re.I):
            return True

    for h in hints:
        m = re.search(r",\s*([A-Za-z]{2})\s*$", h.strip())
        if not m:
            continue
        code = m.group(1).upper()
        if code in CA_PROVINCE_CODES:
            continue
        if code in US_STATE_CODES:
            return True

    has_neg = bool(_NON_US_REGION_RE.search(blob))
    if not has_neg:
        for m in _US_STATE_INLINE_RE.finditer(blob):
            code = m.group(1).upper()
            if code in CA_PROVINCE_CODES:
                continue
            if code in US_STATE_CODES:
                return True
        metro_hits = sum(1 for m in US_MAJOR_METROS if m in blob)
        if metro_hits >= 2:
            return True

    return False


def _unicode_unescape(s: str) -> str:
    try:
        return codecs.decode(s, "unicode_escape")
    except UnicodeDecodeError:
        return s


def fetch_google_careers(src: dict[str, Any]) -> list[dict[str, Any]]:
    """
    Parse job rows embedded in Google careers HTML (AF_initDataCallback / ds:1 blob).
    Matches the public search results page; no official JSON API.
    """
    search_url = (
        src.get("search_url")
        or "https://www.google.com/about/careers/applications/jobs/results/?q=intern"
    ).strip()
    data_key = (src.get("data_key") or "ds:1").strip()
    r = requests.get(
        search_url,
        timeout=45,
        headers={
            "User-Agent": (
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            ),
            "Accept-Language": "en-US,en;q=0.9",
        },
    )
    r.raise_for_status()
    t = r.text
    key_marker = f"key: '{data_key}'"
    if key_marker not in t:
        raise RuntimeError(
            f"Google careers page missing data key {data_key!r}; page layout may have changed."
        )
    pat = re.compile(
        r'\["(\d{10,})","((?:\\.|[^"\\])*)","(https://www\.google\.com/about/careers[^"]+)"'
    )
    out: list[dict[str, Any]] = []
    for jid, title, url in pat.findall(t):
        title = _unicode_unescape(title).strip()
        link = _unicode_unescape(url).strip()
        if not jid:
            continue
        q = parse_qs(urlparse(unquote(link)).query)
        gl = (q.get("loc") or [""])[0].upper()
        hints: list[str] = [gl] if gl else []
        out.append(
            {
                "id": jid,
                "title": title,
                "url": link,
                "location_hints": hints,
                "google_country": gl,
            }
        )
    return out


def fetch_greenhouse(board_token: str) -> list[dict[str, Any]]:
    url = f"https://boards-api.greenhouse.io/v1/boards/{board_token}/jobs"
    r = requests.get(url, timeout=45)
    r.raise_for_status()
    data = r.json()
    jobs = data.get("jobs") or []
    out: list[dict[str, Any]] = []
    for j in jobs:
        jid = str(j.get("id") or "")
        title = (j.get("title") or "").strip()
        link = (j.get("absolute_url") or "").strip()
        if not jid:
            continue
        hints: list[str] = []
        loc = j.get("location")
        if isinstance(loc, dict):
            name = (loc.get("name") or "").strip()
            if name:
                hints.append(name)
        for o in j.get("offices") or []:
            if not isinstance(o, dict):
                continue
            ol = o.get("location")
            if isinstance(ol, dict):
                on = (ol.get("name") or "").strip()
                if on:
                    hints.append(on)
            else:
                on2 = (o.get("name") or "").strip()
                if on2:
                    hints.append(on2)
        out.append({"id": jid, "title": title, "url": link, "location_hints": hints})
    return out


def fetch_lever(company_slug: str) -> list[dict[str, Any]]:
    r = requests.get(
        f"https://api.lever.co/v0/postings/{company_slug}",
        params={"mode": "json"},
        timeout=45,
    )
    r.raise_for_status()
    data = r.json()
    if not isinstance(data, list):
        return []
    out: list[dict[str, Any]] = []
    for j in data:
        jid = str(j.get("id") or "")
        title = (j.get("text") or "").strip()
        link = (j.get("hostedUrl") or j.get("applyUrl") or "").strip()
        if not jid:
            continue
        cats = j.get("categories") or {}
        hints: list[str] = []
        if isinstance(cats, dict):
            loc = (cats.get("location") or "").strip()
            if loc:
                hints.append(loc)
            for al in cats.get("allLocations") or []:
                s = str(al).strip()
                if s:
                    hints.append(s)
        out.append({"id": jid, "title": title, "url": link, "location_hints": hints})
    return out


def fetch_ashby(board_slug: str) -> list[dict[str, Any]]:
    r = requests.get(
        f"https://api.ashbyhq.com/posting-api/job-board/{board_slug}",
        timeout=45,
    )
    r.raise_for_status()
    jobs = (r.json() or {}).get("jobs") or []
    out: list[dict[str, Any]] = []
    for j in jobs:
        jid = str(j.get("id") or "")
        title = (j.get("title") or "").strip()
        link = (j.get("jobUrl") or j.get("applyUrl") or "").strip()
        if not jid:
            continue
        hints: list[str] = []
        loc = (j.get("location") or "").strip()
        if loc:
            hints.append(loc)
        for sl in j.get("secondaryLocations") or []:
            s = str(sl).strip()
            if s:
                hints.append(s)
        out.append({"id": jid, "title": title, "url": link, "location_hints": hints})
    return out


def fetch_smartrecruiters(company_id: str) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    offset = 0
    page_size = 100
    total: int | None = None

    while True:
        r = requests.get(
            f"https://api.smartrecruiters.com/v1/companies/{company_id}/postings",
            params={"limit": page_size, "offset": offset},
            timeout=45,
        )
        r.raise_for_status()
        data = r.json() or {}
        if total is None:
            total = int(data.get("totalFound") or 0)
        postings = data.get("content") or []
        if not postings:
            break

        for p in postings:
            jid = str(p.get("id") or p.get("uuid") or "")
            title = (p.get("name") or "").strip()
            company = (p.get("company") or {}).get("identifier") or company_id
            uuid = (p.get("uuid") or "").strip()
            if uuid:
                link = f"https://jobs.smartrecruiters.com/{company}/{uuid}"
            else:
                link = (p.get("ref") or "").strip()
            if not jid:
                continue
            loc = p.get("location") or {}
            hints: list[str] = []
            cc = ""
            if isinstance(loc, dict):
                cc = (loc.get("country") or "").strip().lower()
                for key in ("fullLocation", "city", "region", "country"):
                    v = loc.get(key)
                    if isinstance(v, str) and v.strip():
                        hints.append(v.strip())
            row: dict[str, Any] = {
                "id": jid,
                "title": title,
                "url": link,
                "location_hints": hints,
            }
            if cc:
                row["country_code"] = cc
            out.append(row)

        offset += len(postings)
        if total and offset >= total:
            break
        if len(postings) < page_size:
            break

    return out


def fetch_recruitee(src: dict[str, Any]) -> list[dict[str, Any]]:
    slug = (src.get("company_slug") or src.get("board_slug") or "").strip()
    if not slug:
        raise ValueError("recruitee source requires company_slug")
    r = requests.get(f"https://{slug}.recruitee.com/api/offers/", timeout=45)
    r.raise_for_status()
    offers = (r.json() or {}).get("offers") or []
    out: list[dict[str, Any]] = []
    for o in offers:
        jid = str(o.get("id") or o.get("slug") or "")
        title = (o.get("title") or "").strip()
        link = (o.get("careers_url") or o.get("url") or "").strip()
        if not link and o.get("slug"):
            link = f"https://{slug}.recruitee.com/o/{o['slug']}"
        if not jid or not title:
            continue
        hints: list[str] = []
        for key in ("city", "state", "country", "location"):
            v = (o.get(key) or "").strip()
            if v:
                hints.append(v)
        cc = (o.get("country_code") or "").strip().lower()
        row: dict[str, Any] = {"id": jid, "title": title, "url": link, "location_hints": hints}
        if cc:
            row["country_code"] = cc
        out.append(row)
    return out


_PHENOM_REF_RE = re.compile(r'"refNum"\s*:\s*"([^"]+)"')


def fetch_phenom(src: dict[str, Any]) -> list[dict[str, Any]]:
    base_url = (src.get("base_url") or "").strip().rstrip("/")
    search_url = (src.get("search_url") or f"{base_url}/search-results").strip()
    ref_num = (src.get("ref_num") or "").strip()
    keywords = (src.get("keywords") or "intern").strip()
    page_size = int(src.get("page_size") or 50)
    if not base_url:
        raise ValueError("phenom source requires base_url")

    if not ref_num:
        warm = requests.get(
            search_url,
            timeout=45,
            headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"},
        )
        warm.raise_for_status()
        m = _PHENOM_REF_RE.search(warm.text or "")
        if not m:
            raise RuntimeError(f"phenom: could not find refNum on {search_url}")
        ref_num = m.group(1)

    out: list[dict[str, Any]] = []
    offset = 0
    total_hits: int | None = None
    while True:
        payload = {
            "lang": "en_global",
            "deviceType": "desktop",
            "country": "global",
            "pageName": "search-results",
            "size": page_size,
            "from": offset,
            "jobs": True,
            "counts": True,
            "all_fields": ["category", "country", "city", "type"],
            "clearAll": False,
            "jdsource": "facets",
            "isSliderEnable": False,
            "pageId": "page20",
            "siteType": "external",
            "keywords": keywords,
            "global": True,
            "selected_fields": {},
            "sort": {"order": "desc", "field": "postedDate"},
            "locationData": {},
            "refNum": ref_num,
            "ddoKey": "refineSearch",
        }
        r = requests.post(
            f"{base_url}/widgets",
            json=payload,
            timeout=45,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Content-Type": "application/json",
                "Accept": "application/json",
                "Referer": search_url,
            },
        )
        r.raise_for_status()
        refine = (r.json() or {}).get("refineSearch") or {}
        if total_hits is None:
            total_hits = int(refine.get("totalHits") or refine.get("totalCount") or 0)
        data = refine.get("data") or {}
        jobs = data.get("jobs") or []
        if not jobs:
            break
        for j in jobs:
            jid = str(j.get("jobId") or j.get("reqId") or j.get("jobSeqNo") or "")
            title = (j.get("title") or "").strip()
            link = (j.get("applyUrl") or "").strip()
            if not jid or not title:
                continue
            hints: list[str] = []
            for key in ("location", "cityStateCountry", "multi_location"):
                val = j.get(key)
                if isinstance(val, str) and val.strip():
                    hints.append(val.strip())
                elif isinstance(val, list):
                    hints.extend(str(x).strip() for x in val if str(x).strip())
            cc = (j.get("country") or "").strip().lower()
            row: dict[str, Any] = {"id": jid, "title": title, "url": link, "location_hints": hints}
            if cc in ("us", "usa", "united states"):
                row["country_code"] = "us"
            out.append(row)
        offset += len(jobs)
        if total_hits and offset >= total_hits:
            break
        if len(jobs) < page_size:
            break
    return out


def fetch_successfactors(src: dict[str, Any]) -> list[dict[str, Any]]:
    feed_url = (src.get("feed_url") or "").strip()
    if not feed_url:
        raise ValueError("successfactors source requires feed_url")
    r = requests.get(feed_url, timeout=45, headers={"User-Agent": "Mozilla/5.0"})
    r.raise_for_status()
    out: list[dict[str, Any]] = []
    seen: set[str] = set()
    _sf_id_re = re.compile(r"/(\d{6,})(?:/|\?|$)")
    for item in ET.fromstring(r.text).findall("./channel/item"):
        title = (item.findtext("title") or "").strip()
        link = (item.findtext("link") or "").strip()
        m = _sf_id_re.search(link)
        jid = m.group(1) if m else (item.findtext("guid") or link or "").strip()
        if not title or not link or jid in seen:
            continue
        seen.add(jid)
        out.append({"id": jid, "title": title, "url": link, "location_hints": []})
    return out


def fetch_avature(src: dict[str, Any]) -> list[dict[str, Any]]:
    feed_url = (src.get("feed_url") or "").strip()
    if not feed_url:
        raise ValueError("avature source requires feed_url")
    page_size = int(src.get("page_size") or 100)
    max_pages = int(src.get("max_pages") or 10)
    out: list[dict[str, Any]] = []
    for page in range(max_pages):
        sep = "&" if "?" in feed_url else "?"
        url = f"{feed_url}{sep}jobRecordsPerPage={page_size}&jobOffset={page * page_size}"
        r = requests.get(url, timeout=45, headers={"User-Agent": "Mozilla/5.0"})
        r.raise_for_status()
        root = ET.fromstring(r.text)
        items = root.findall("./channel/item")
        if not items:
            break
        for item in items:
            title = (item.findtext("title") or "").strip()
            link = (item.findtext("link") or "").strip()
            guid = (item.findtext("guid") or link or "").strip()
            jid = guid.rsplit("/", 1)[-1] if guid else link
            if not title or not link:
                continue
            out.append({"id": jid, "title": title, "url": link, "location_hints": []})
        if len(items) < page_size:
            break
    return out


def fetch_bofa(src: dict[str, Any]) -> list[dict[str, Any]]:
    search = (src.get("search") or "getAllJobs").strip()
    page_size = int(src.get("page_size") or 100)
    max_pages = int(src.get("max_pages") or 20)
    out: list[dict[str, Any]] = []
    for page in range(max_pages):
        start = page * page_size
        r = requests.get(
            "https://careers.bankofamerica.com/services/jobssearchservlet",
            params={"start": start, "rows": page_size, "search": search},
            timeout=45,
            headers={"User-Agent": "Mozilla/5.0", "Accept": "application/json"},
        )
        r.raise_for_status()
        data = r.json() or {}
        jobs = data.get("jobsList") or []
        if not jobs:
            break
        for j in jobs:
            jid = str(j.get("jobRequisitionId") or "")
            title = (j.get("postingTitle") or "").strip()
            path = (j.get("jcrURL") or "").strip()
            link = f"https://careers.bankofamerica.com{path}" if path.startswith("/") else path
            if not jid or not title:
                continue
            hints = [
                x
                for x in (
                    j.get("primaryLocation"),
                    j.get("location"),
                    j.get("city"),
                    j.get("state"),
                    j.get("country"),
                )
                if isinstance(x, str) and x.strip()
            ]
            cc = (j.get("country") or "").strip().lower()
            row: dict[str, Any] = {"id": jid, "title": title, "url": link, "location_hints": hints}
            if cc == "united states":
                row["country_code"] = "us"
            out.append(row)
        total = int(data.get("totalMatches") or 0)
        if start + len(jobs) >= total:
            break
    return out


def fetch_playwright(src: dict[str, Any]) -> list[dict[str, Any]]:
    profile = (src.get("profile") or "").strip()
    if not profile:
        raise ValueError("playwright source requires profile")
    scripts_dir = Path(__file__).resolve().parent / "scripts"
    if str(scripts_dir) not in sys.path:
        sys.path.insert(0, str(scripts_dir))
    from playwright_fetch import fetch_playwright_profile

    return fetch_playwright_profile(profile, src)


_VALVE_JOB_RE = re.compile(
    r'<a href="([^"]+job_id=\d+)"[^>]*>\s*<h5 class="job_title">\s*([^<]+?)\s*</h5>',
    re.I | re.S,
)


def fetch_valve(src: dict[str, Any]) -> list[dict[str, Any]]:
    url = (src.get("jobs_url") or "https://www.valvesoftware.com/en/jobs").strip()
    r = requests.get(
        url,
        timeout=45,
        headers={
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
            ),
        },
    )
    r.raise_for_status()
    out: list[dict[str, Any]] = []
    for link, title in _VALVE_JOB_RE.findall(r.text or ""):
        title = re.sub(r"\s+", " ", title).strip()
        m = re.search(r"job_id=(\d+)", link)
        jid = m.group(1) if m else link
        if not title:
            continue
        if link.startswith("/"):
            link = f"https://www.valvesoftware.com{link}"
        out.append({"id": jid, "title": title, "url": link, "location_hints": ["Bellevue, WA"]})
    return out


def fetch_usajobs(src: dict[str, Any]) -> list[dict[str, Any]]:
    """
    USAJOBS public API — free key from https://developer.usajobs.gov/
    Set USAJOBS_API_KEY and USAJOBS_USER_AGENT (your email) in .env
    """
    api_key = os.environ.get("USAJOBS_API_KEY", "").strip()
    user_agent = os.environ.get("USAJOBS_USER_AGENT", "").strip()
    if not api_key or not user_agent:
        raise RuntimeError(
            "USAJOBS_API_KEY and USAJOBS_USER_AGENT (email) required in .env — "
            "see https://developer.usajobs.gov/"
        )
    org = (src.get("org_keyword") or "NASA").strip()
    query = (src.get("search_keyword") or "intern").strip()
    keyword = f"{org} {query}".strip()
    out: list[dict[str, Any]] = []
    page = 1
    while page <= 5:
        r = requests.get(
            "https://data.usajobs.gov/api/search",
            params={
                "Keyword": keyword,
                "LocationName": "United States",
                "Page": page,
                "ResultsPerPage": 100,
            },
            headers={
                "Host": "data.usajobs.gov",
                "User-Agent": user_agent,
                "Authorization-Key": api_key,
            },
            timeout=45,
        )
        r.raise_for_status()
        data = r.json() or {}
        items = (
            (data.get("SearchResult") or {}).get("SearchResultItems") or []
        )
        if not items:
            break
        for item in items:
            md = (item.get("MatchedObjectDescriptor") or {})
            jid = str(md.get("PositionID") or md.get("MatchedObjectId") or "")
            title = (md.get("PositionTitle") or "").strip()
            link = (md.get("PositionURI") or "").strip()
            if not jid or not title:
                continue
            locs = md.get("PositionLocation") or []
            hints: list[str] = []
            for loc in locs:
                if isinstance(loc, dict):
                    name = (loc.get("LocationName") or "").strip()
                    if name:
                        hints.append(name)
            cc = ""
            if locs and isinstance(locs[0], dict):
                cc = (locs[0].get("CountryCode") or "").strip().lower()
            row: dict[str, Any] = {
                "id": jid,
                "title": title,
                "url": link,
                "location_hints": hints,
            }
            if cc:
                row["country_code"] = cc
            out.append(row)
        if len(items) < 100:
            break
        page += 1
    return out


def fetch_amazon(src: dict[str, Any]) -> list[dict[str, Any]]:
    query = (src.get("query") or "intern").strip()
    out: list[dict[str, Any]] = []
    offset = 0
    page_size = 100
    total: int | None = None

    while True:
        r = requests.get(
            "https://amazon.jobs/en/search.json",
            params={
                "base_query": query,
                "offset": offset,
                "result_limit": page_size,
            },
            timeout=45,
        )
        r.raise_for_status()
        data = r.json() or {}
        if total is None:
            total = int(data.get("hits") or 0)
        jobs = data.get("jobs") or []
        if not jobs:
            break

        for j in jobs:
            jid = str(j.get("id") or j.get("job_id") or "")
            title = (j.get("title") or "").strip()
            path = (j.get("job_path") or "").strip()
            if path.startswith("/"):
                link = f"https://amazon.jobs{path}"
            else:
                link = path
            if not jid:
                continue
            loc = (j.get("location") or "").strip()
            hints = [loc] if loc else []
            cc = ""
            if loc:
                first = loc.split(",")[0].strip().upper()
                if len(first) == 2 and first.isalpha():
                    cc = first.lower()
            row: dict[str, Any] = {"id": jid, "title": title, "url": link, "location_hints": hints}
            if cc:
                row["country_code"] = cc
            out.append(row)

        offset += len(jobs)
        if total and offset >= total:
            break
        if len(jobs) < page_size:
            break

    return out


def fetch_workday(src: dict[str, Any]) -> list[dict[str, Any]]:
    host = (src.get("host") or "").strip().rstrip("/")
    tenant = (src.get("tenant") or "").strip()
    site = (src.get("site") or "").strip()
    locale = (src.get("locale") or "en-US").strip()
    search_text = (src.get("search_text") or "intern").strip()
    out: list[dict[str, Any]] = []
    offset = 0
    page_size = 20
    total: int | None = None

    while True:
        r = requests.post(
            f"{host}/wday/cxs/{tenant}/{site}/jobs",
            json={
                "appliedFacets": {},
                "limit": page_size,
                "offset": offset,
                "searchText": search_text,
            },
            timeout=45,
        )
        r.raise_for_status()
        data = r.json() or {}
        if total is None:
            total = int(data.get("total") or 0)
        postings = data.get("jobPostings") or []
        if not postings:
            break

        for p in postings:
            path = (p.get("externalPath") or "").strip()
            bullets = p.get("bulletFields") or []
            jid = str(bullets[0] if bullets else path or p.get("title") or "")
            title = (p.get("title") or "").strip()
            if path:
                link = f"{host}/{locale}/{site}{path}"
            else:
                link = ""
            if not jid:
                continue
            loc_txt = (p.get("locationsText") or "").strip()
            hints = [loc_txt] if loc_txt else []
            out.append({"id": jid, "title": title, "url": link, "location_hints": hints})

        offset += len(postings)
        if total and offset >= total:
            break
        if len(postings) < page_size:
            break

    return out


def fetch_pcsx(src: dict[str, Any]) -> list[dict[str, Any]]:
    list_url = (src.get("list_url") or "").strip()
    domain = (src.get("domain") or "").strip()
    query = (src.get("query") or "intern").strip()
    start_param = (src.get("start_param") or "start").strip()
    page_size_param = (src.get("page_size_param") or "count").strip()
    page_size = int(src.get("page_size") or 10)
    out: list[dict[str, Any]] = []
    start = 0
    total: int | None = None
    origin = "/".join(list_url.split("/")[:3])

    while True:
        params: dict[str, Any] = {
            "domain": domain,
            "query": query,
            start_param: start,
            page_size_param: page_size,
        }
        if page_size_param == "count":
            params["sort_by"] = "relevance"

        r = requests.get(list_url, params=params, timeout=45)
        r.raise_for_status()
        payload = r.json() or {}
        data = payload.get("data") if isinstance(payload.get("data"), dict) else payload
        if total is None:
            total = int(data.get("count") or payload.get("count") or 0)
        positions = data.get("positions") or []
        if not positions:
            break

        for p in positions:
            jid = str(p.get("id") or "")
            title = (p.get("name") or "").strip()
            link = (p.get("canonicalPositionUrl") or "").strip()
            if not link:
                path = (p.get("positionUrl") or "").strip()
                if path.startswith("/"):
                    link = f"{origin}{path}"
                else:
                    link = path
            if not jid:
                continue
            hints: list[str] = []
            for key in ("standardizedLocations", "locations"):
                for x in p.get(key) or []:
                    s = str(x).strip()
                    if s:
                        hints.append(s)
            out.append({"id": jid, "title": title, "url": link, "location_hints": hints})

        start += len(positions)
        if total and start >= total:
            break
        if len(positions) < page_size:
            break

    return out


_VIEW_LINK_RE = re.compile(r"\[View\]\((https://apply\.workable\.com/[^)]+)\)")


def fetch_workable(src: dict[str, Any]) -> list[dict[str, Any]]:
    """
    Workable-hosted careers: public markdown feed per shortcode.
    See https://apply.workable.com/{shortcode}/jobs.md (Accept: text/markdown).
    """
    shortcode = (src.get("shortcode") or "").strip()
    if not shortcode:
        raise ValueError("workable source requires non-empty shortcode")
    url = f"https://apply.workable.com/{shortcode}/jobs.md"
    r = requests.get(
        url,
        timeout=45,
        headers={
            "User-Agent": (
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            ),
            "Accept": "text/markdown,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
        },
    )
    r.raise_for_status()
    ctype = (r.headers.get("content-type") or "").lower()
    text = r.text or ""
    if "markdown" not in ctype and not text.lstrip().startswith("#"):
        raise RuntimeError(
            f"Workable {shortcode!r}: expected markdown feed from {url!r}, "
            f"got content-type {ctype!r} ({len(text)} bytes)."
        )

    out: list[dict[str, Any]] = []
    for m in _VIEW_LINK_RE.finditer(text):
        raw_url = m.group(1).strip()
        line_start = text.rfind("\n", 0, m.start()) + 1
        line_end = text.find("\n", m.end())
        line = text[line_start : line_end if line_end != -1 else len(text)]
        parts = [p.strip() for p in line.strip().strip("|").split("|")]
        title = parts[0] if parts else ""
        loc = parts[2] if len(parts) > 2 else ""
        hints = [loc] if loc else []
        link = raw_url.removesuffix(".md")
        id_m = re.search(r"/jobs/view/([^/.?#]+)", raw_url, re.I)
        jid = (id_m.group(1) if id_m else "") or raw_url
        if not title or not jid:
            continue
        out.append({"id": jid, "title": title, "url": link, "location_hints": hints})

    return out


def fetch_oracle_careers(src: dict[str, Any]) -> list[dict[str, Any]]:
    """
    Oracle Cloud HCM careers (careers.oracle.com).
    Uses the public recruitingCEJobRequisitions REST API.
    """
    host = (src.get("host") or "eeho.fa.us2.oraclecloud.com").strip().rstrip("/")
    site_number = (src.get("site_number") or "CX_45001").strip()
    keyword = (src.get("search_keyword") or "intern").strip()
    job_url_tmpl = (
        src.get("job_url")
        or "https://careers.oracle.com/en/sites/jobsearch/job/{id}"
    ).strip()
    page_size = int(src.get("page_size") or 100)
    out: list[dict[str, Any]] = []
    offset = 0
    list_url = f"https://{host}/hcmRestApi/resources/latest/recruitingCEJobRequisitions"

    while True:
        params = {
            "onlyData": "true",
            "expand": (
                "requisitionList.workLocation,"
                "requisitionList.otherWorkLocations,"
                "requisitionList.secondaryLocations"
            ),
            "finder": f"findReqs;siteNumber={site_number},keyword={keyword}",
            "limit": page_size,
            "offset": offset,
        }
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            ),
            "Accept": "application/json",
            "ora-irc-cx-userid": str(uuid.uuid4()),
            "ora-irc-language": "en",
            "content-type": "application/vnd.oracle.adf.resourceitem+json;charset=utf-8",
        }
        r = requests.get(list_url, params=params, headers=headers, timeout=45)
        r.raise_for_status()
        payload = r.json() or {}
        postings = (payload.get("items") or [{}])[0].get("requisitionList") or []
        if not postings:
            break

        for p in postings:
            jid = str(p.get("Id") or "")
            title = (p.get("Title") or "").strip()
            if not jid or not title:
                continue
            link = job_url_tmpl.format(id=jid)
            hints: list[str] = []
            primary_loc = (p.get("PrimaryLocation") or "").strip()
            if primary_loc:
                hints.append(primary_loc)
            for key in ("secondaryLocations", "otherWorkLocations", "workLocation"):
                for loc in p.get(key) or []:
                    if isinstance(loc, dict):
                        for field in ("Name", "TownOrCity", "CountryCode"):
                            val = (loc.get(field) or "").strip()
                            if val:
                                hints.append(val)
                    elif isinstance(loc, str) and loc.strip():
                        hints.append(loc.strip())
            cc = (p.get("PrimaryLocationCountry") or "").strip().lower()
            row: dict[str, Any] = {
                "id": jid,
                "title": title,
                "url": link,
                "location_hints": hints,
            }
            if cc:
                row["country_code"] = cc
            out.append(row)

        if not payload.get("hasMore"):
            break
        offset += len(postings)
        if len(postings) < page_size:
            break

    return out


def fetch_microsoft(src: dict[str, Any]) -> list[dict[str, Any]]:
    merged = {
        "list_url": "https://apply.careers.microsoft.com/api/pcsx/search",
        "domain": src.get("domain") or "microsoft.com",
        "query": src.get("query") or "intern",
        "page_size_param": "count",
        "page_size": 10,
        "start_param": "start",
    }
    return fetch_pcsx(merged)


def source_key(src: dict[str, Any]) -> str:
    stype = src.get("type") or "unknown"
    if stype == "greenhouse":
        return f"{stype}:{src.get('board_token') or src.get('name') or 'unknown'}"
    if stype == "lever":
        return f"{stype}:{src.get('company_slug') or src.get('name') or 'unknown'}"
    if stype == "ashby":
        return f"{stype}:{src.get('board_slug') or src.get('name') or 'unknown'}"
    if stype == "smartrecruiters":
        return f"{stype}:{src.get('company_id') or src.get('name') or 'unknown'}"
    if stype == "amazon":
        return f"{stype}:{src.get('query') or 'intern'}"
    if stype == "workday":
        return (
            f"{stype}:{src.get('tenant') or 'unknown'}:"
            f"{src.get('site') or 'unknown'}:{src.get('search_text') or 'intern'}"
        )
    if stype in {"microsoft", "pcsx"}:
        return (
            f"pcsx:{src.get('domain') or 'unknown'}:"
            f"{src.get('query') or 'intern'}:{src.get('list_url') or 'microsoft'}"
        )
    if stype == "workable":
        return f"workable:{src.get('shortcode') or src.get('name') or 'unknown'}"
    if stype == "recruitee":
        return f"recruitee:{src.get('company_slug') or src.get('board_slug') or src.get('name') or 'unknown'}"
    if stype == "oracle_careers":
        return (
            f"oracle_careers:{src.get('host') or 'eeho.fa.us2.oraclecloud.com'}:"
            f"{src.get('site_number') or 'CX_45001'}:"
            f"{src.get('search_keyword') or 'intern'}"
        )
    if stype == "google_careers":
        return (
            f"google_careers:{src.get('data_key') or 'ds:1'}:"
            f"{src.get('search_url') or 'default'}"
        )
    if stype == "valve":
        return f"valve:{src.get('jobs_url') or 'default'}"
    if stype == "usajobs":
        return (
            f"usajobs:{src.get('org_keyword') or 'NASA'}:"
            f"{src.get('search_keyword') or 'intern'}"
        )
    if stype == "phenom":
        return (
            f"phenom:{src.get('ref_num') or src.get('base_url') or 'unknown'}:"
            f"{src.get('keywords') or 'intern'}"
        )
    if stype == "avature":
        return f"avature:{src.get('feed_url') or src.get('name') or 'unknown'}"
    if stype == "successfactors":
        return f"successfactors:{src.get('feed_url') or src.get('name') or 'unknown'}"
    if stype == "bofa":
        return f"bofa:{src.get('search') or 'getAllJobs'}"
    if stype == "playwright":
        return f"playwright:{src.get('profile') or 'unknown'}:{src.get('page_url') or 'unknown'}"
    return f"{stype}:{src.get('name') or 'unknown'}"


FETCHERS = {
    "greenhouse": lambda src: fetch_greenhouse(src["board_token"]),
    "lever": lambda src: fetch_lever(src["company_slug"]),
    "ashby": lambda src: fetch_ashby(src["board_slug"]),
    "smartrecruiters": lambda src: fetch_smartrecruiters(src["company_id"]),
    "amazon": fetch_amazon,
    "workday": fetch_workday,
    "pcsx": fetch_pcsx,
    "microsoft": fetch_microsoft,
    "google_careers": fetch_google_careers,
    "workable": fetch_workable,
    "oracle_careers": fetch_oracle_careers,
    "recruitee": fetch_recruitee,
    "valve": fetch_valve,
    "usajobs": fetch_usajobs,
    "phenom": fetch_phenom,
    "successfactors": fetch_successfactors,
    "avature": fetch_avature,
    "bofa": fetch_bofa,
    "playwright": fetch_playwright,
}


def telegram_send_html(token: str, chat_id: str, text: str) -> None:
    r = requests.post(
        f"https://api.telegram.org/bot{token}/sendMessage",
        json={
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "HTML",
            "disable_web_page_preview": False,
        },
        timeout=30,
    )
    if not r.ok:
        raise RuntimeError(f"Telegram API error {r.status_code}: {r.text}")


def escape_html(s: str) -> str:
    return (
        s.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


JTRACK_MARKER = "JTRACK::"
JTRACK_PREFIX = "Internship tracker data — do not unpin or delete\n"


def slugify_company(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")


def _tg_api(token: str, method: str, payload: dict[str, Any]) -> dict[str, Any]:
    r = requests.post(
        f"https://api.telegram.org/bot{token}/{method}",
        json=payload,
        timeout=30,
    )
    body = r.json()
    if not body.get("ok"):
        raise RuntimeError(f"Telegram {method}: {body}")
    return body["result"]


def _decode_tracker(text: str) -> dict[str, Any] | None:
    idx = text.find(JTRACK_MARKER)
    if idx == -1:
        return None
    try:
        return json.loads(text[idx + len(JTRACK_MARKER) :])
    except json.JSONDecodeError:
        return None


def _encode_tracker(data: dict[str, Any]) -> str:
    return JTRACK_PREFIX + JTRACK_MARKER + json.dumps(data, separators=(",", ":"))


def _load_pinned_tracker(token: str, chat_id: str) -> tuple[dict[str, Any], int | None]:
    chat = _tg_api(token, "getChat", {"chat_id": chat_id})
    pm = chat.get("pinned_message") or {}
    text = pm.get("text") or ""
    msg_id = pm.get("message_id")
    decoded = _decode_tracker(text)
    if decoded is None:
        return {"applied": {}, "deadlines": [], "notified": {}, "updatedAt": 0}, msg_id
    decoded.setdefault("applied", {})
    decoded.setdefault("deadlines", [])
    decoded.setdefault("notified", {})
    return decoded, msg_id


def _save_pinned_tracker(
    token: str, chat_id: str, data: dict[str, Any], msg_id: int | None
) -> int | None:
    text = _encode_tracker(data)
    if msg_id:
        try:
            _tg_api(
                token,
                "editMessageText",
                {"chat_id": chat_id, "message_id": msg_id, "text": text},
            )
            return msg_id
        except RuntimeError as e:
            if "exactly the same" not in str(e).lower():
                msg_id = None
    msg = _tg_api(
        token,
        "sendMessage",
        {"chat_id": chat_id, "text": text, "disable_notification": True},
    )
    new_id = msg["message_id"]
    _tg_api(
        token,
        "pinChatMessage",
        {"chat_id": chat_id, "message_id": new_id, "disable_notification": True},
    )
    return new_id


def mark_company_notified(token: str, chat_id: str, company_name: str) -> None:
    """Record a new job alert in the pinned webapp sync message."""
    slug = slugify_company(company_name)
    if not slug:
        return
    try:
        data, msg_id = _load_pinned_tracker(token, chat_id)
        notified = data.setdefault("notified", {})
        notified[slug] = int(time.time() * 1000)
        data["updatedAt"] = notified[slug]
        _save_pinned_tracker(token, chat_id, data, msg_id)
    except Exception as e:
        print(f"[warn] Could not update tracker highlight for {company_name}: {e}")


def poll_once(config: dict[str, Any]) -> int:
    token = get_env("TELEGRAM_BOT_TOKEN")
    chat_id = get_env("TELEGRAM_CHAT_ID")
    keywords = config.get("title_keywords") or ["intern", "internship"]
    us_only = location_filter_wants_us_only(config)

    conn = sqlite3.connect(STATE_DB)
    init_db(conn)

    new_count = 0
    for src in config.get("sources") or []:
        name = src.get("name") or "unknown"
        stype = src.get("type")
        if stype not in FETCHERS:
            print(f"Skip unknown source type: {stype} ({name})")
            continue
        sk = source_key(src)
        try:
            jobs = FETCHERS[stype](src)
        except Exception as e:
            print(f"[error] {name}: {e}")
            continue

        for job in jobs:
            jid = job["id"]
            title = job["title"]
            url = job["url"]
            if not title_matches(title, keywords):
                continue
            if us_only and not job_matches_us_location(job, title):
                continue
            if already_seen(conn, sk, jid):
                continue
            mark_seen(conn, sk, jid, title, url)
            new_count += 1
            safe_title = escape_html(title)
            safe_name = escape_html(name)
            link = url or ""
            if link:
                safe_href = html_escape(link, quote=True)
                body = (
                    f"<b>New internship match</b>\n"
                    f"{safe_name}\n"
                    f'<a href="{safe_href}">{safe_title}</a>'
                )
            else:
                body = f"<b>New internship match</b>\n{safe_name}\n{safe_title}"
            telegram_send_html(token, chat_id, body)
            mark_company_notified(token, chat_id, name)
            print(f"Notified: {name} — {title}")

    conn.close()
    return new_count


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--once",
        action="store_true",
        help="Run a single poll and exit (good for cron / scheduled jobs).",
    )
    args = parser.parse_args()

    if not Path(CONFIG_PATH).is_file():
        print(f"Config not found: {CONFIG_PATH}", file=sys.stderr)
        sys.exit(1)

    config = load_config(CONFIG_PATH)
    interval = int(config.get("poll_interval_seconds") or 120)

    if args.once:
        n = poll_once(config)
        print(f"Done. New postings notified: {n}")
        return

    print(f"Looping every {interval}s. SQLite: {STATE_DB}")
    while True:
        try:
            poll_once(config)
        except KeyboardInterrupt:
            raise
        except Exception as e:
            print(f"[fatal loop error] {e}")
        time.sleep(interval)


if __name__ == "__main__":
    main()
