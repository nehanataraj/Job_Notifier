#!/usr/bin/env python3
"""Generate webapp/companies.json from config.json (name, ATS label, careers link)."""

import json
import re
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]

ATS_LABELS = {
    "workday": "Workday",
    "greenhouse": "Greenhouse",
    "lever": "Lever",
    "ashby": "Ashby",
    "smartrecruiters": "SmartRecruiters",
    "oracle_careers": "Oracle HCM",
    "phenom": "Phenom",
    "avature": "Avature",
    "successfactors": "SuccessFactors",
    "pcsx": "Phenom CSX",
    "playwright": "Direct site",
    "google_careers": "Direct site",
    "amazon": "Amazon Jobs",
    "bofa": "Direct site",
    "usajobs": "USAJobs",
    "valve": "Direct site",
    "workable": "Workable",
}


def host_root(url: str) -> str:
    p = urlsplit(url)
    return f"{p.scheme}://{p.netloc}"


def careers_url(src: dict) -> str:
    t = src["type"]
    if t == "workday":
        return f"{src['host'].rstrip('/')}/{src['site']}"
    if t == "greenhouse":
        return f"https://boards.greenhouse.io/{src['board_token']}"
    if t == "lever":
        return f"https://jobs.lever.co/{src['company_slug']}"
    if t == "ashby":
        return f"https://jobs.ashbyhq.com/{src['board_slug']}"
    if t == "smartrecruiters":
        return f"https://careers.smartrecruiters.com/{src['company_id']}"
    if t == "oracle_careers":
        return f"https://{src['host']}/hcmUI/CandidateExperience/en/sites/{src['site_number']}"
    if t == "playwright":
        return src["page_url"]
    if t == "phenom":
        return src.get("search_url") or src.get("base_url", "")
    if t in ("avature", "successfactors"):
        return host_root(src["feed_url"])
    if t == "pcsx":
        return host_root(src["list_url"])
    if t == "google_careers":
        return src["search_url"]
    if t == "amazon":
        return "https://www.amazon.jobs/en/search?base_query=intern"
    if t == "bofa":
        return "https://careers.bankofamerica.com/en-us/job-search?searchKeyword=intern"
    if t == "usajobs":
        return "https://www.usajobs.gov/Search/Results?k=intern"
    if t == "valve":
        return "https://www.valvesoftware.com/en/jobs"
    if t == "workable":
        return f"https://apply.workable.com/{src['shortcode']}"
    return ""


def slugify(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")


def main() -> None:
    cfg = json.loads((ROOT / "config.json").read_text(encoding="utf-8"))
    out = []
    seen = set()
    for src in cfg["sources"]:
        slug = slugify(src["name"])
        if slug in seen:
            continue
        seen.add(slug)
        out.append(
            {
                "slug": slug,
                "name": src["name"],
                "ats": ATS_LABELS.get(src["type"], src["type"]),
                "url": careers_url(src),
            }
        )
    out.sort(key=lambda c: c["name"].lower())
    dest = ROOT / "webapp" / "companies.json"
    dest.parent.mkdir(exist_ok=True)
    dest.write_text(json.dumps(out, indent=1), encoding="utf-8")
    print(f"Wrote {len(out)} companies to {dest}")


if __name__ == "__main__":
    main()
