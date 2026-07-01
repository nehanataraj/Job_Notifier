#!/usr/bin/env python3
import json
from playwright.sync_api import sync_playwright

TARGETS = {
    "Meta": "https://www.metacareers.com/jobs?q=intern",
    "Apple": "https://jobs.apple.com/en-us/search?search=intern",
    "Tesla": "https://www.tesla.com/careers/search?query=intern",
}

for name, url in TARGETS.items():
    print(f"\n=== {name} ===")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        try:
            page.goto(url, wait_until="networkidle", timeout=90000)
        except Exception as e:
            print("nav err", e)
        page.wait_for_timeout(5000)
        jobs = page.evaluate("""() => {
            const out = [];
            const selectors = [
                'a[href*="/jobs/"]',
                'a[href*="job_id"]',
                'a[href*="JobDetail"]',
                'a[href*="job-detail"]',
                '.job-title a',
                'tr a',
                '[data-job-id]',
            ];
            for (const sel of selectors) {
                document.querySelectorAll(sel).forEach(el => {
                    const title = (el.innerText || el.textContent || '').trim();
                    const href = el.href || el.getAttribute('href') || '';
                    if (title && href && title.length > 5 && title.length < 200) {
                        out.push({title, href});
                    }
                });
            }
            return out.slice(0, 30);
        }""")
        print("dom jobs", len(jobs))
        for j in jobs[:5]:
            print(" ", j)
        browser.close()
