#!/usr/bin/env python3
"""Playwright-backed fetchers for bot-managed career sites."""

from __future__ import annotations

import re
from typing import Any
from urllib.parse import urljoin

UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
)


def _norm_jobs(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    seen: set[str] = set()
    for row in rows:
        jid = str(row.get("id") or row.get("url") or row.get("title") or "")
        if not jid or jid in seen:
            continue
        seen.add(jid)
        out.append(row)
    return out


def fetch_apple_dom(page_url: str) -> list[dict[str, Any]]:
    from playwright.sync_api import sync_playwright

    jobs: list[dict[str, Any]] = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(user_agent=UA)
        page.goto(page_url, wait_until="networkidle", timeout=90000)
        page.wait_for_timeout(3000)
        rows = page.evaluate("""() => {
            const out = [];
            document.querySelectorAll('a[href*="/details/"]').forEach(el => {
                const title = (el.innerText || '').trim();
                const href = el.href || '';
                if (title && href) out.push({title, href});
            });
            return out;
        }""")
        browser.close()

    for row in rows:
        href = row["href"]
        m = re.search(r"/details/(\d+)/", href)
        jid = m.group(1) if m else href
        jobs.append(
            {
                "id": jid,
                "title": row["title"],
                "url": href,
                "location_hints": [],
            }
        )
    return _norm_jobs(jobs)


def _meta_jobs_from_payload(jobs_raw: list[dict[str, Any]]) -> list[dict[str, Any]]:
    jobs: list[dict[str, Any]] = []
    for j in jobs_raw:
        jid = str(j.get("id") or j.get("job_id") or "")
        title = (j.get("title") or "").strip()
        link = (j.get("url") or j.get("share_url") or "").strip()
        if not link and jid:
            link = f"https://www.metacareers.com/jobs/{jid}"
        hints: list[str] = []
        for loc in j.get("locations") or []:
            if isinstance(loc, dict):
                city = (loc.get("city") or "").strip()
                country = (loc.get("country") or "").strip()
                if city or country:
                    hints.append(", ".join(x for x in (city, country) if x))
        if not jid or not title:
            continue
        jobs.append({"id": jid, "title": title, "url": link, "location_hints": hints})
    return jobs


def fetch_meta_graphql(page_url: str) -> list[dict[str, Any]]:
    from playwright.sync_api import sync_playwright

    captured: list[dict[str, Any]] = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(user_agent=UA)

        def on_response(resp):
            if "graphql" not in resp.url or resp.status != 200:
                return
            try:
                data = resp.json()
                block = (data.get("data") or {}).get("job_search_with_featured_jobs")
                if block and block.get("all_jobs"):
                    captured.extend(block["all_jobs"])
            except Exception:
                pass

        page.on("response", on_response)
        page.goto(page_url, wait_until="domcontentloaded", timeout=120000)
        for _ in range(6):
            page.mouse.wheel(0, 2200)
            page.wait_for_timeout(2000)
        page.wait_for_timeout(5000)

        dom_rows = page.evaluate("""() => {
            const out = [];
            document.querySelectorAll('a[href*="/jobs/"]').forEach(el => {
                const title = (el.innerText || '').trim();
                const href = el.href || '';
                if (title && href && !/apply|log in/i.test(title)) out.push({title, href});
            });
            return out;
        }""")
        browser.close()

    jobs = _meta_jobs_from_payload(captured)
    if jobs:
        return _norm_jobs(jobs)

    fallback: list[dict[str, Any]] = []
    for row in dom_rows or []:
        href = row["href"]
        m = re.search(r"/jobs/(\d+)", href)
        jid = m.group(1) if m else href
        fallback.append(
            {
                "id": jid,
                "title": row["title"],
                "url": href,
                "location_hints": [],
            }
        )
    return _norm_jobs(fallback)


def fetch_tesla_dom(page_url: str) -> list[dict[str, Any]]:
    from playwright.sync_api import sync_playwright

    api_posts: list[dict[str, Any]] = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(user_agent=UA)

        def on_response(resp):
            if "cua-api/apps/careers" not in resp.url or resp.status != 200:
                return
            try:
                posts = (resp.json() or {}).get("posts") or []
                if isinstance(posts, list):
                    api_posts.extend(posts)
            except Exception:
                pass

        page.on("response", on_response)
        try:
            page.goto(page_url, wait_until="domcontentloaded", timeout=120000)
        except Exception:
            page.goto(page_url, wait_until="load", timeout=120000)
        for _ in range(8):
            page.mouse.wheel(0, 2400)
            page.wait_for_timeout(1500)
        page.wait_for_timeout(6000)
        rows = page.evaluate("""() => {
            const out = [];
            document.querySelectorAll('a, [role="link"], tr td a').forEach(el => {
                const title = (el.innerText || '').trim();
                const href = el.href || '';
                if (!title || !href) return;
                if (/intern/i.test(title) || /intern/i.test(href)) out.push({title, href});
            });
            return out;
        }""")
        browser.close()

    jobs: list[dict[str, Any]] = []
    for post in api_posts:
        jid = str(post.get("id") or post.get("jobId") or post.get("title") or "")
        title = (post.get("title") or "").strip()
        link = (post.get("url") or post.get("applyUrl") or "").strip()
        if not title:
            continue
        jobs.append({"id": jid or link or title, "title": title, "url": link, "location_hints": []})
    if jobs:
        return _norm_jobs(jobs)

    for row in rows or []:
        href = row["href"]
        jobs.append(
            {
                "id": href,
                "title": row["title"],
                "url": href,
                "location_hints": [],
            }
        )
    return _norm_jobs(jobs)


_JOB_ID_RE = re.compile(r"/jobs/(\d+)")


def fetch_icims_careers(page_url: str) -> list[dict[str, Any]]:
    from playwright.sync_api import sync_playwright

    jobs: list[dict[str, Any]] = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(user_agent=UA)
        page.goto(page_url, wait_until="domcontentloaded", timeout=120000)
        for _ in range(4):
            page.mouse.wheel(0, 2000)
            page.wait_for_timeout(1200)
        page.wait_for_timeout(3000)
        rows = page.evaluate("""() => {
            const skip = /^(apply now|returning user login|login|sign in)$/i;
            const out = [];
            document.querySelectorAll('a[href*="/jobs/"]').forEach(el => {
                const title = (el.innerText || '').trim();
                const href = el.href || '';
                if (!title || !href || skip.test(title)) return;
                if (/\\/jobs\\/\\d+/.test(href)) out.push({title, href});
            });
            return out;
        }""")
        browser.close()

    for row in rows or []:
        href = row["href"]
        m = _JOB_ID_RE.search(href)
        if not m:
            continue
        jobs.append(
            {
                "id": m.group(1),
                "title": row["title"],
                "url": href,
                "location_hints": [],
            }
        )
    return _norm_jobs(jobs)


def fetch_eightfold_dom(page_url: str) -> list[dict[str, Any]]:
    from playwright.sync_api import sync_playwright

    captured_positions: list[dict[str, Any]] = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(user_agent=UA)

        def on_response(resp):
            if "pcsx/search" not in resp.url or resp.status != 200:
                return
            try:
                data = resp.json() or {}
                inner = data.get("data") if isinstance(data.get("data"), dict) else data
                captured_positions.extend(inner.get("positions") or [])
            except Exception:
                pass

        page.on("response", on_response)
        page.goto(page_url, wait_until="domcontentloaded", timeout=120000)
        page.wait_for_timeout(8000)
        dom_rows = page.evaluate("""() => {
            const skip = /^(about|career|careers|search|login|sign in|apply|home|locations|students|english)/i;
            const out = [];
            document.querySelectorAll('a[href*="job"], a[href*="position"], [class*="position"] a').forEach(el => {
                const title = (el.innerText || '').replace(/\\s+/g, ' ').trim();
                const href = el.href || '';
                if (!title || !href || title.length < 12 || skip.test(title)) return;
                if (/\\/careers\\/|position|job|\\/jobs\\//i.test(href)) out.push({title, href});
            });
            return out.slice(0, 40);
        }""")
        browser.close()

    jobs: list[dict[str, Any]] = []
    for p in captured_positions:
        jid = str(p.get("id") or "")
        title = (p.get("name") or "").strip()
        link = (p.get("canonicalPositionUrl") or p.get("positionUrl") or "").strip()
        if not jid or not title:
            continue
        jobs.append({"id": jid, "title": title, "url": link, "location_hints": []})
    if jobs:
        return _norm_jobs(jobs)

    for row in dom_rows or []:
        href = row["href"]
        jobs.append({"id": href, "title": row["title"], "url": href, "location_hints": []})
    return _norm_jobs(jobs)


def _accept_cookie_banner(page) -> None:
    for sel in (
        '#onetrust-accept-btn-handler',
        'button:has-text("ACCEPT ALL")',
        'button:has-text("Accept All")',
        'button:has-text("Accept")',
        'button:has-text("I Accept")',
    ):
        try:
            page.locator(sel).first.click(timeout=2500)
            page.wait_for_timeout(1500)
            return
        except Exception:
            continue


def fetch_lockheed_jobs(page_url: str) -> list[dict[str, Any]]:
    from playwright.sync_api import sync_playwright

    jobs: list[dict[str, Any]] = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(user_agent=UA)
        page.goto(page_url, wait_until="domcontentloaded", timeout=120000)
        page.wait_for_timeout(10000)
        for _ in range(5):
            page.mouse.wheel(0, 2000)
            page.wait_for_timeout(1200)
        rows = page.evaluate("""() => {
            const out = [];
            document.querySelectorAll('a[href*="/job/"]').forEach(a => {
                const title = (a.innerText || '').trim().replace(/\\s+/g, ' ').split('Date')[0].trim();
                const href = a.href || '';
                if (!title || !href || title.length < 8) return;
                if (/opens in new window|employee focused/i.test(title)) return;
                out.push({title, href});
            });
            return out;
        }""")
        browser.close()

    for row in rows or []:
        href = row["href"]
        m = re.search(r"/job/[^/]+/([^/?#]+)", href)
        jid = m.group(1) if m else href
        jobs.append({"id": jid, "title": row["title"], "url": href, "location_hints": []})
    return _norm_jobs(jobs)


def fetch_avature_search(page_url: str) -> list[dict[str, Any]]:
    from playwright.sync_api import sync_playwright

    jobs: list[dict[str, Any]] = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(user_agent=UA)
        page.goto(page_url, wait_until="domcontentloaded", timeout=120000)
        page.wait_for_timeout(3000)
        _accept_cookie_banner(page)
        page.wait_for_timeout(8000)
        rows = page.evaluate("""() => {
            const out = [];
            document.querySelectorAll('a[href*="/JobDetail/"], a[href*="/job/"]').forEach(a => {
                const title = (a.innerText || '').trim();
                const href = a.href || '';
                if (!title || !href || title.length < 8) return;
                if (/share|linkedin|twitter|facebook|mailto/i.test(href)) return;
                out.push({title, href});
            });
            return out;
        }""")
        browser.close()

    for row in rows or []:
        href = row["href"]
        m = re.search(r"/(?:JobDetail|job)/([^/?#]+)", href, re.I)
        jid = m.group(1) if m else href
        jobs.append({"id": jid, "title": row["title"], "url": href, "location_hints": []})
    return _norm_jobs(jobs)


def fetch_wells_fargo_jobs(page_url: str) -> list[dict[str, Any]]:
    from playwright.sync_api import sync_playwright

    jobs: list[dict[str, Any]] = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(user_agent=UA)
        page.goto(page_url, wait_until="networkidle", timeout=180000)
        page.wait_for_timeout(10000)
        _accept_cookie_banner(page)
        page.wait_for_timeout(5000)
        rows = page.evaluate("""() => {
            const out = [];
            document.querySelectorAll('.card-job, .job-listing').forEach(card => {
                const a = card.querySelector('a[href]');
                const titleEl = card.querySelector('h2, h3, .job-title, [class*="title"]');
                const title = (titleEl ? titleEl.innerText : (a ? a.innerText : '')).trim().replace(/\\s+/g, ' ').split('\\n')[0];
                const href = a ? a.href : '';
                if (title && href) out.push({title, href});
            });
            return out;
        }""")
        browser.close()

    for row in rows or []:
        href = row["href"]
        m = re.search(r"/r-(\d+)/", href)
        jid = m.group(1) if m else href
        jobs.append({"id": jid, "title": row["title"], "url": href, "location_hints": []})
    return _norm_jobs(jobs)


def _pw_eval(
    page_url: str,
    js: str,
    *,
    wait_ms: int = 10000,
    scrolls: int = 4,
    browser_name: str = "chromium",
) -> list[dict[str, Any]]:
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        launcher = getattr(p, browser_name)
        browser = launcher.launch(headless=True)
        page = browser.new_page(user_agent=UA)
        page.goto(page_url, wait_until="domcontentloaded", timeout=120000)
        page.wait_for_timeout(wait_ms)
        for _ in range(scrolls):
            page.mouse.wheel(0, 2000)
            page.wait_for_timeout(1200)
        rows = page.evaluate(js) or []
        browser.close()
    return rows


def fetch_bain_jobs(page_url: str) -> list[dict[str, Any]]:
    rows = _pw_eval(
        page_url,
        """() => {
            const out = [];
            const seen = new Set();
            document.querySelectorAll('a[href*="jobid="]').forEach(a => {
                const href = a.href || '';
                const title = (a.innerText || '').trim().replace(/\\s+/g, ' ').split('\\n')[0].trim();
                if (!href || !title || title.length < 5 || seen.has(href)) return;
                if (/^#|consulting services$/i.test(title)) return;
                seen.add(href);
                out.push({title, href});
            });
            return out;
        }""",
        wait_ms=12000,
    )

    jobs: list[dict[str, Any]] = []
    for row in rows:
        href = row["href"]
        m = re.search(r"jobid=(\d+)", href, re.I)
        jid = m.group(1) if m else href
        jobs.append({"id": jid, "title": row["title"], "url": href, "location_hints": []})
    return _norm_jobs(jobs)


def fetch_shopify_jobs(page_url: str) -> list[dict[str, Any]]:
    rows = _pw_eval(
        page_url,
        """() => {
            const skip = /^(learn more|internship program|careers home|search)$/i;
            const out = [];
            const seen = new Set();
            document.querySelectorAll('a[href*="/careers/"]').forEach(a => {
                const href = a.href || '';
                const title = (a.innerText || '').trim().replace(/\\s+/g, ' ').split('REMOTE')[0].trim();
                if (!href || !title || seen.has(href)) return;
                if (skip.test(title) || /\\/careers\\/?$|search|internships\\.shopify/i.test(href)) return;
                if (!/_[a-f0-9]{6,}/i.test(href) && !/\\/careers\\/[a-z0-9-]+_[a-f0-9]/i.test(href)) return;
                seen.add(href);
                out.push({title, href});
            });
            return out;
        }""",
        wait_ms=8000,
    )

    jobs: list[dict[str, Any]] = []
    for row in rows:
        href = row["href"]
        slug = href.rstrip("/").rsplit("/", 1)[-1]
        jobs.append({"id": slug, "title": row["title"], "url": href, "location_hints": []})
    return _norm_jobs(jobs)


def fetch_rippling_jobs(page_url: str) -> list[dict[str, Any]]:
    rows = _pw_eval(
        page_url,
        """() => {
            const out = [];
            const seen = new Set();
            document.querySelectorAll('a[href*="ats.rippling.com"]').forEach(a => {
                const href = a.href || '';
                const raw = (a.innerText || '').trim();
                const title = raw.split('\\n').map(s => s.trim()).filter(Boolean)[0] || raw;
                if (!href || !title || seen.has(href)) return;
                seen.add(href);
                out.push({title, href});
            });
            return out;
        }""",
        wait_ms=10000,
        scrolls=3,
    )

    jobs: list[dict[str, Any]] = []
    for row in rows:
        href = row["href"]
        m = re.search(r"/jobs/([a-f0-9-]{36})", href, re.I)
        jid = m.group(1) if m else href
        jobs.append({"id": jid, "title": row["title"], "url": href, "location_hints": []})
    return _norm_jobs(jobs)


_MCKINSEY_JS = """() => {
    const out = [];
    const seen = new Set();
    document.querySelectorAll('a[href]').forEach(a => {
        const href = a.href || '';
        const title = (a.innerText || '').trim().replace(/\\s+/g, ' ');
        if (!href || !title || title.length < 8 || seen.has(href)) return;
        if (!/mckinsey\\.com\\/careers/i.test(href)) return;
        if (/search-jobs\\/?$|login|saved|apply\\.mckinsey/i.test(href)) return;
        if (!/job|position|role|intern|program|opening/i.test(href + ' ' + title)) return;
        seen.add(href);
        out.push({title: title.slice(0, 120), href});
    });
    return out;
}"""


def fetch_mckinsey_jobs(page_url: str) -> list[dict[str, Any]]:
    """Best-effort: McKinsey often blocks automation (HTTP/2 errors, timeouts)."""
    fallbacks = [
        page_url,
        "https://www.mckinsey.com/careers/at-mckinsey/internships",
        "https://www.mckinsey.com/careers/search-jobs?countries=United+States&q=intern",
    ]
    rows: list[dict[str, Any]] = []
    for url in fallbacks:
        try:
            rows = _pw_eval(url, _MCKINSEY_JS, wait_ms=12000, scrolls=5)
            if rows:
                break
        except Exception:
            continue

    if not rows:
        return []

    jobs: list[dict[str, Any]] = []
    for row in rows:
        href = row["href"]
        jid = href.rstrip("/").rsplit("/", 1)[-1] or href
        jobs.append({"id": jid, "title": row["title"], "url": href, "location_hints": []})
    return _norm_jobs(jobs)


def fetch_playwright_profile(profile: str, src: dict[str, Any]) -> list[dict[str, Any]]:
    page_url = (src.get("page_url") or "").strip()
    if not page_url:
        raise ValueError("playwright source requires page_url")
    if profile == "apple":
        return fetch_apple_dom(page_url)
    if profile == "meta":
        return fetch_meta_graphql(page_url)
    if profile == "tesla":
        return fetch_tesla_dom(page_url)
    if profile == "icims":
        return fetch_icims_careers(page_url)
    if profile == "eightfold":
        return fetch_eightfold_dom(page_url)
    if profile == "lockheed":
        return fetch_lockheed_jobs(page_url)
    if profile == "avature":
        return fetch_avature_search(page_url)
    if profile == "wells":
        return fetch_wells_fargo_jobs(page_url)
    if profile == "bain":
        return fetch_bain_jobs(page_url)
    if profile == "shopify":
        return fetch_shopify_jobs(page_url)
    if profile == "rippling":
        return fetch_rippling_jobs(page_url)
    if profile == "mckinsey":
        return fetch_mckinsey_jobs(page_url)
    raise ValueError(f"Unknown playwright profile: {profile}")
