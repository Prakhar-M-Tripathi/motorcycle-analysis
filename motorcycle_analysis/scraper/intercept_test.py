"""
intercept_test.py
-----------------
Captures all XHR/fetch network requests made by BikeWale when loading
a dealer-showrooms and service-centers page. Prints the API endpoints
and any JSON responses containing dealer/count data.

Run this once to identify the correct API pattern, then update the main
scraper to call those endpoints directly instead of parsing page HTML.

Usage:
    python scraper/intercept_test.py
"""
import json, os, sys, time, re
from playwright.sync_api import sync_playwright

PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEBUG_DIR   = os.path.join(PROJECT_DIR, "data", "raw", "debug")
os.makedirs(DEBUG_DIR, exist_ok=True)

TEST_URLS = [
    ("showroom", "https://www.bikewale.com/dealer-showrooms/royal-enfield/delhi/"),
    ("service",  "https://www.bikewale.com/service-centers/royal-enfield/delhi/"),
]

def run():
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        ctx = browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            )
        )

        for label, url in TEST_URLS:
            print(f"\n{'='*60}")
            print(f"  Testing: {label}")
            print(f"  URL: {url}")
            print(f"{'='*60}")

            api_calls = []

            page = ctx.new_page()

            def on_request(req):
                if any(x in req.url for x in ["api", "json", "data", "dealer", "service"]):
                    api_calls.append({"url": req.url, "method": req.method})

            def on_response(resp):
                content_type = resp.headers.get("content-type", "")
                if "json" in content_type:
                    try:
                        body = resp.json()
                        url_snippet = resp.url[:80]
                        if any(k in str(body).lower() for k in ["dealer", "service", "count", "total"]):
                            api_calls.append({
                                "url":  resp.url,
                                "status": resp.status,
                                "json_keys": list(body.keys()) if isinstance(body, dict) else type(body).__name__,
                                "sample": str(body)[:400],
                            })
                    except Exception:
                        pass

            page.on("request",  on_request)
            page.on("response", on_response)

            resp = page.goto(url, wait_until="domcontentloaded", timeout=25_000)
            print(f"  HTTP status: {resp.status if resp else 'unknown'}")

            # Wait for JS to fire its API calls
            page.wait_for_timeout(6000)

            # Also try waiting for networkidle
            try:
                page.wait_for_load_state("networkidle", timeout=8000)
            except Exception:
                pass

            # Save the final rendered HTML
            html_path = os.path.join(DEBUG_DIR, f"intercept_{label}_delhi.html")
            with open(html_path, "w", encoding="utf-8") as fh:
                fh.write(page.content())
            print(f"  Rendered HTML saved: {html_path} ({len(page.content())} chars)")

            # Check rendered text for numbers
            body_text = page.inner_text("body")
            numbers = re.findall(r'\b(\d{1,4})\b', body_text)
            print(f"  Numbers visible on page: {numbers[:30]}")

            # Check for any heading-style count
            for sel in ["h1", "h2", "[class*='count']", "[class*='heading']", "[class*='title']"]:
                try:
                    for el in page.query_selector_all(sel):
                        text = (el.inner_text() or "").strip()
                        if text and re.search(r'\d', text):
                            print(f"  [{sel}] -> {repr(text[:120])}")
                except Exception:
                    pass

            print(f"\n  API calls captured ({len(api_calls)}):")
            for call in api_calls[:20]:
                print(f"    {call}")

            page.close()

        browser.close()

if __name__ == "__main__":
    run()
