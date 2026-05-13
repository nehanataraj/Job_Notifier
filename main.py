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
    if stype == "google_careers":
        return (
            f"google_careers:{src.get('data_key') or 'ds:1'}:"
            f"{src.get('search_url') or 'default'}"
        )
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
