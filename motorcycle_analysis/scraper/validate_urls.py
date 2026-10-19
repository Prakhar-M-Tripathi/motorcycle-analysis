"""Quick validation: test dealer-showroom URL with correct brand masking."""
import re, sys, os, time
from playwright.sync_api import sync_playwright

PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_DIR)

TESTS = [
    ("service",  "https://www.bikewale.com/service-centers/royalenfield/delhi/"),
    ("showroom", "https://www.bikewale.com/dealer-showrooms/royalenfield/delhi/"),
    ("showroom", "https://www.bikewale.com/dealer-showrooms/hero/delhi/"),
    ("showroom", "https://www.bikewale.com/dealer-showrooms/honda/delhi/"),
    ("service",  "https://www.bikewale.com/service-centers/hero/delhi/"),
]

def run():
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        ctx = browser.new_context(user_agent=(
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        ))
        page = ctx.new_page()

        for typ, url in TESTS:
            resp = page.goto(url, wait_until="networkidle", timeout=25_000)
            status = resp.status if resp else "?"
            title = page.title()

            # Extract count from h1/h2
            count = None
            for sel in ["h1", "h2"]:
                for el in page.query_selector_all(sel):
                    text = (el.inner_text() or "").strip()
                    m = re.match(r"^(\d+)", text)
                    if m:
                        count = int(m.group(1))
                        break
                if count is not None:
                    break

            print(f"[{status}] {typ:<10} count={str(count):<6} {url}")
            time.sleep(2)

        browser.close()

if __name__ == "__main__":
    run()
