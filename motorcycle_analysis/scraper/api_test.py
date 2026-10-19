"""
api_test.py
-----------
Tests BikeWale's internal APIs directly (no browser needed):
  1. /api/servicecenter/cities/make/{makeId}/ -- cities for a brand
  2. The rendered page at /service-centers/{brand}/{city}/
  3. Dealer-showroom equivalent

This tells us: (a) what makeId Royal Enfield has, (b) what city data
the API returns, (c) whether /service-centers/ page renders the count
server-side when called directly, and (d) the dealer-showrooms structure.
"""
import os, sys, re, json, time
import requests
from playwright.sync_api import sync_playwright

PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEBUG_DIR   = os.path.join(PROJECT_DIR, "data", "raw", "debug")
os.makedirs(DEBUG_DIR, exist_ok=True)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json, text/javascript, */*; q=0.01",
    "X-Requested-With": "XMLHttpRequest",
    "Referer": "https://www.bikewale.com/service-centers/",
}
BASE = "https://www.bikewale.com"

# ── Step 1: Find all makes and their IDs ─────────────────────────────────
# The ddlMakes dropdown on the service page has all makes. Scrape it.
def get_make_ids():
    print("=== Step 1: Discovering makeIds from service page ===")
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(f"{BASE}/service-centers/", wait_until="networkidle", timeout=25_000)

        makes = page.evaluate("""() => {
            const sel = document.querySelector('#ddlMakes');
            if (!sel) return [];
            return Array.from(sel.options).map(o => ({
                value: o.value,
                text:  o.text.trim(),
                masking: o.getAttribute('maskingName') || ''
            }));
        }""")
        browser.close()

    print(f"  Found {len(makes)} makes in dropdown:")
    for m in makes:
        print(f"    {m}")
    return makes

# ── Step 2: Call the cities API for Royal Enfield ─────────────────────────
def get_cities_for_make(make_id: str, make_name: str):
    url = f"{BASE}/api/servicecenter/cities/make/{make_id}/"
    print(f"\n=== Step 2: Cities API for {make_name} (makeId={make_id}) ===")
    print(f"  GET {url}")

    r = requests.get(url, headers=HEADERS, timeout=15)
    print(f"  HTTP {r.status_code}  ({len(r.text)} chars)")

    path = os.path.join(DEBUG_DIR, f"cities_{make_id}.json")
    with open(path, "w", encoding="utf-8") as f:
        f.write(r.text)
    print(f"  Response saved: {path}")

    try:
        data = r.json()
        print(f"  Response type: {type(data).__name__}")
        if isinstance(data, list):
            print(f"  Cities count: {len(data)}")
            print(f"  First 5: {data[:5]}")
        elif isinstance(data, dict):
            print(f"  Keys: {list(data.keys())}")
        return data
    except Exception as e:
        print(f"  JSON parse failed: {e}")
        print(f"  Raw text: {r.text[:500]}")
        return None

# ── Step 3: Check service-center rendered page with correct city ───────────
def check_service_page_rendered(brand_masking: str, city_masking: str):
    url = f"{BASE}/service-centers/{brand_masking}/{city_masking}/"
    print(f"\n=== Step 3: Rendered service page {brand_masking}/{city_masking} ===")

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        ctx = browser.new_context(user_agent=HEADERS["User-Agent"])
        page = ctx.new_page()

        resp = page.goto(url, wait_until="networkidle", timeout=25_000)
        print(f"  HTTP {resp.status}  URL: {page.url}")

        # Save HTML
        html = page.content()
        path = os.path.join(DEBUG_DIR, f"service_{brand_masking}_{city_masking}.html")
        with open(path, "w", encoding="utf-8") as f:
            f.write(html)
        print(f"  HTML saved: {path} ({len(html)} chars)")

        # Try all headings
        for sel in ["h1", "h2", "[class*='count']", "[class*='heading']", "[class*='dealer']"]:
            try:
                for el in page.query_selector_all(sel):
                    text = (el.inner_text() or "").strip()
                    if text and re.search(r'\d', text):
                        print(f"  [{sel}] -> {repr(text[:150])}")
            except Exception:
                pass

        # Page title
        title = page.title()
        print(f"  Page title: {title}")

        # Page data attribute
        pd = page.evaluate("""() => {
            const el = document.querySelector('#page-data');
            return el ? {...el.dataset} : null;
        }""")
        print(f"  #page-data attrs: {pd}")

        browser.close()

# ── Step 4: Check dealer-showrooms page structure ────────────────────────
def check_dealer_page():
    print(f"\n=== Step 4: Dealer-showrooms page structure ===")
    url = f"{BASE}/dealer-showrooms/"

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        ctx = browser.new_context(user_agent=HEADERS["User-Agent"])
        page = ctx.new_page()

        resp = page.goto(url, wait_until="networkidle", timeout=25_000)
        print(f"  Base dealer URL HTTP {resp.status}  URL: {page.url}")

        # Check what makes are in the dropdown
        makes = page.evaluate("""() => {
            const sel = document.querySelector('#ddlMakes, select[name*=make], select[id*=make]');
            if (!sel) return {found: false, allSelects: Array.from(document.querySelectorAll('select')).map(s => s.id || s.name)};
            return {
                found: true,
                id: sel.id,
                options: Array.from(sel.options).slice(0,5).map(o => ({v: o.value, t: o.text, m: o.getAttribute('maskingName')}))
            };
        }""")
        print(f"  Make dropdown: {makes}")

        # Find any API endpoints in page JS
        scripts = page.evaluate("""() => {
            return Array.from(document.querySelectorAll('script[src]')).map(s => s.src);
        }""")
        print(f"  Script tags: {[s for s in scripts if 'bikewale' in s][:5]}")

        html = page.content()
        path = os.path.join(DEBUG_DIR, "dealer_base.html")
        with open(path, "w", encoding="utf-8") as f:
            f.write(html)
        print(f"  HTML saved: {path} ({len(html)} chars)")

        # Look for API patterns in inline JS
        api_hits = re.findall(r'"/api/[a-zA-Z0-9/_-]{5,60}"', html)
        print(f"  API paths in inline JS: {api_hits[:10]}")

        browser.close()

if __name__ == "__main__":
    makes = get_make_ids()

    # Find Royal Enfield
    re_make = next((m for m in makes if "royal" in m["text"].lower() or "enfield" in m["text"].lower()), None)
    if re_make:
        cities = get_cities_for_make(re_make["value"], re_make["text"])

        # Find Delhi in the cities list
        if isinstance(cities, list):
            delhi = next((c for c in cities if "delhi" in str(c).lower()), None)
            print(f"\n  Delhi in cities API: {delhi}")
            if delhi:
                city_masking = delhi.get("cityMaskingName", "delhi")
                check_service_page_rendered(re_make["masking"], city_masking)
    else:
        print("  Royal Enfield not found in makes dropdown")

    check_dealer_page()
