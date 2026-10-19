"""
test_scraper.py
---------------
Validates the scraper against Royal Enfield across 8 cities spanning
all 6 zones before committing to the full 9,000-request run.

Usage:
    python scraper/test_scraper.py
"""
import os, sys, re, time, json, random
from playwright.sync_api import sync_playwright

SCRIPT_DIR  = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.dirname(SCRIPT_DIR)
sys.path.insert(0, PROJECT_DIR)

from constants import BIKEWALE_BRAND_SLUG, STATE_TO_ZONE

TEST_BRAND = "royal-enfield"

TEST_CITIES = [
    ("delhi",     "Delhi",     "North"),
    ("mumbai",    "Mumbai",    "West"),
    ("chennai",   "Chennai",   "South"),
    ("patna",     "Patna",     "East"),
    ("bhopal",    "Bhopal",    "Central"),
    ("guwahati",  "Guwahati",  "Northeast"),
    ("nagpur",    "Nagpur",    "West"),
    ("haldwani",  "Haldwani",  "North"),
]

BASE = "https://www.bikewale.com"

def service_url(masking, city):
    return f"{BASE}/service-centers/{masking}/{city}/"

def showroom_url(masking, city):
    return f"{BASE}/dealer-showrooms/{masking}/{city}/"

def extract_count(page):
    for sel in ["h1", "h2"]:
        for el in page.query_selector_all(sel):
            text = (el.inner_text() or "").strip()
            m = re.match(r"^(\d+)", text)
            if m:
                return int(m.group(1))
    return None

def run():
    masking = BIKEWALE_BRAND_SLUG[TEST_BRAND]
    results = []

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        ctx = browser.new_context(user_agent=(
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        ))
        page = ctx.new_page()

        for city_slug, display, zone in TEST_CITIES:
            for rec_type, url_fn in [("service", service_url), ("showroom", showroom_url)]:
                url  = url_fn(masking, city_slug)
                resp = page.goto(url, wait_until="networkidle", timeout=25_000)
                status = resp.status if resp else "?"

                if status == 404:
                    count = 0
                    note  = "404-not-present"
                else:
                    count = extract_count(page)
                    note  = "ok" if count is not None else "EXTRACT-FAILED"

                results.append({
                    "city": display, "zone": zone,
                    "type": rec_type, "count": count,
                    "http": status, "note": note, "url": url,
                })

                c_str = str(count) if count is not None else "?"
                print(f"  [{status}] {display:<12} {rec_type:<10} count={c_str}")
                time.sleep(random.uniform(2.0, 3.0))

        browser.close()

    # Summary
    print(f"\n{'='*60}")
    print(f"  RESULTS - Royal Enfield (masking={masking})")
    print(f"{'='*60}")
    print(f"  {'City':<14} {'Zone':<12} {'Type':<10} {'HTTP':>4}  {'Count':>6}  Note")
    print(f"  {'-'*14} {'-'*12} {'-'*10} {'-'*4}  {'-'*6}  {'-'*15}")
    for r in results:
        c_str = str(r["count"]) if r["count"] is not None else "FAILED"
        print(f"  {r['city']:<14} {r['zone']:<12} {r['type']:<10} {str(r['http']):>4}  {c_str:>6}  {r['note']}")

    ok     = sum(1 for r in results if r["count"] is not None)
    failed = sum(1 for r in results if r["count"] is None)
    print(f"\n  Passed: {ok}/{len(results)}  |  Failed: {failed}/{len(results)}")

    out = os.path.join(PROJECT_DIR, "data", "raw", "test_results.json")
    with open(out, "w") as f:
        json.dump(results, f, indent=2)
    print(f"  Results saved: {out}")

if __name__ == "__main__":
    print("=== BikeWale test - Royal Enfield, 8 cities ===")
    run()
