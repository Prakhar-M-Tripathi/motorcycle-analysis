"""
click_city_test.py - find correct BikeWale URL and count extraction method.
"""
import os, sys, re, time
from playwright.sync_api import sync_playwright

PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEBUG_DIR   = os.path.join(PROJECT_DIR, "data", "raw", "debug")
os.makedirs(DEBUG_DIR, exist_ok=True)

BASE_URLS = [
    ("service",  "https://www.bikewale.com/service-centers/royal-enfield/"),
    ("showroom", "https://www.bikewale.com/dealer-showrooms/royal-enfield/"),
]

def run():
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        ctx = browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            ),
            viewport={"width": 1280, "height": 800},
        )

        for label, base_url in BASE_URLS:
            print(f"\n{'='*60}")
            print(f"  {label.upper()}: {base_url}")

            page = ctx.new_page()
            api_calls = []
            page.on("response", lambda r: api_calls.append((r.url, r.status))
                    if "bikewale" in r.url and "bhrigu" not in r.url and "imgd" not in r.url
                    else None)

            resp = page.goto(base_url, wait_until="networkidle", timeout=30_000)
            print(f"  HTTP: {resp.status if resp else '?'}  URL: {page.url}")

            # Save base HTML
            html = page.content()
            html_path = os.path.join(DEBUG_DIR, f"base_{label}.html")
            with open(html_path, "w", encoding="utf-8") as fh:
                fh.write(html)
            print(f"  Base HTML saved ({len(html)} chars)")

            # Find city elements
            city_info = page.evaluate("""() => {
                const els = document.querySelectorAll('[data-citymasking], [data-cityname]');
                return Array.from(els).slice(0, 20).map(el => ({
                    tag:      el.tagName,
                    cityId:   el.dataset.cityid,
                    name:     el.dataset.cityname,
                    masking:  el.dataset.citymasking,
                    href:     el.href || el.getAttribute('href') || '',
                    visible:  el.offsetParent !== null,
                    classes:  el.className
                }));
            }""")
            print(f"  City elements: {len(city_info)}")
            for c in city_info[:8]:
                print(f"    {c}")

            # Try JS click on Delhi
            result = page.evaluate("""() => {
                const el = document.querySelector('[data-citymasking="delhi"]')
                         || document.querySelector('[data-cityname="Delhi"]');
                if (!el) return {found: false};
                el.click();
                return {
                    found:    true,
                    tag:      el.tagName,
                    href:     el.href || '',
                    cityId:   el.dataset.cityid,
                    masking:  el.dataset.citymasking,
                };
            }""")
            print(f"\n  JS click result: {result}")

            page.wait_for_timeout(5000)
            print(f"  URL after click: {page.url}")

            # Capture visible text
            body_text = page.inner_text("body")
            print(f"\n  First 2000 chars of page text after click:")
            print(body_text[:2000])

            # Save post-click HTML
            html2 = page.content()
            html2_path = os.path.join(DEBUG_DIR, f"clicked_{label}_delhi.html")
            with open(html2_path, "w", encoding="utf-8") as fh:
                fh.write(html2)
            print(f"\n  Post-click HTML saved ({len(html2)} chars): {html2_path}")

            # Non-analytics API calls
            bw_calls = [(u, s) for u, s in api_calls if "google" not in u and "facebook" not in u]
            print(f"\n  BikeWale requests ({len(bw_calls)}):")
            for u, s in bw_calls[:15]:
                print(f"    [{s}] {u[:100]}")

            page.close()
            time.sleep(2)

        browser.close()

if __name__ == "__main__":
    run()
