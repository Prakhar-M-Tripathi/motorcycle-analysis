"""
find_api.py
-----------
Fetches the BikeWale landing JS file and looks for the API endpoint
called when a city is selected on the service/dealer pages.
Also fires a city click and captures XHR calls.
"""
import os, sys, re, time, json
from playwright.sync_api import sync_playwright

PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEBUG_DIR   = os.path.join(PROJECT_DIR, "data", "raw", "debug")
os.makedirs(DEBUG_DIR, exist_ok=True)

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
        page = ctx.new_page()

        # Capture ALL requests/responses after the city click
        xhr_log = []

        def on_request(req):
            xhr_log.append({"event": "req", "url": req.url, "method": req.method})

        def on_response(resp):
            ct = resp.headers.get("content-type", "")
            if "json" in ct or "bikewale" in resp.url:
                try:
                    body = resp.json()
                    xhr_log.append({
                        "event":   "json",
                        "url":     resp.url,
                        "status":  resp.status,
                        "keys":    list(body.keys()) if isinstance(body, dict) else type(body).__name__,
                        "body":    body,
                    })
                except Exception:
                    if "bikewale" in resp.url and "imgd" not in resp.url:
                        xhr_log.append({"event": "non-json", "url": resp.url, "status": resp.status})

        page.on("request",  on_request)
        page.on("response", on_response)

        # Load the service page
        url = "https://www.bikewale.com/service-centers/royal-enfield/"
        page.goto(url, wait_until="networkidle", timeout=30_000)

        # Clear the log so far (only capture post-click events)
        pre_click_count = len(xhr_log)
        xhr_log.clear()

        # JS click on Delhi
        page.evaluate("""() => {
            const el = document.querySelector('[data-citymasking="delhi"]');
            if (el) el.click();
        }""")

        # Wait generously for any AJAX
        page.wait_for_timeout(6000)
        try:
            page.wait_for_load_state("networkidle", timeout=8000)
        except Exception:
            pass

        # Save page state to file (avoid console encoding issue)
        result_path = os.path.join(DEBUG_DIR, "find_api_result.txt")
        lines = []
        lines.append(f"URL: {page.url}")
        lines.append(f"XHR log entries after click: {len(xhr_log)}")
        lines.append("")

        for entry in xhr_log:
            if entry["event"] == "json":
                lines.append(f"[JSON] {entry['url'][:120]}")
                lines.append(f"  status: {entry['status']}")
                lines.append(f"  keys: {entry['keys']}")
                body_str = json.dumps(entry["body"])[:800]
                lines.append(f"  body: {body_str}")
            elif entry["event"] == "non-json":
                if "google" not in entry["url"] and "facebook" not in entry["url"] and "bhrigu" not in entry["url"]:
                    lines.append(f"[NON-JSON] [{entry['status']}] {entry['url'][:120]}")
            elif entry["event"] == "req":
                u = entry["url"]
                if "bikewale" in u and "google" not in u and "imgd" not in u and "stb.aep" not in u:
                    lines.append(f"[REQ] {entry['method']} {u[:120]}")

        # Save page text to file
        try:
            body_text = page.inner_text("body")
            lines.append("")
            lines.append("=== PAGE TEXT (first 3000 chars) ===")
            lines.append(body_text[:3000])
        except Exception as e:
            lines.append(f"Could not get body text: {e}")

        # Save H1/H2
        for sel in ["h1", "h2"]:
            for el in page.query_selector_all(sel):
                text = (el.inner_text() or "").strip()
                if text:
                    lines.append(f"[{sel}] {text[:200]}")

        with open(result_path, "w", encoding="utf-8") as fh:
            fh.write("\n".join(lines))

        print(f"Results written to: {result_path}")
        print(f"XHR entries captured: {len(xhr_log)}")
        for e in xhr_log[:5]:
            print(f"  {e.get('event')} | {e.get('url','')[:80]}")

        # Also fetch the landing JS and look for API patterns
        js_url = "https://stb.aeplcdn.com/bikewale/min/ui/src/service/landing-3b7be49836.js"
        page.goto(js_url, wait_until="domcontentloaded", timeout=20_000)
        js_content = page.inner_text("body")

        js_path = os.path.join(DEBUG_DIR, "landing.js")
        with open(js_path, "w", encoding="utf-8") as fh:
            fh.write(js_content)
        print(f"JS saved ({len(js_content)} chars): {js_path}")

        # Look for API endpoint patterns
        patterns = re.findall(r'["\'](?:/[a-zA-Z0-9/_-]{5,60})["\']', js_content)
        api_pats  = [p for p in patterns if any(x in p.lower() for x in ["api", "service", "dealer", "city", "count", "locate"])]
        print(f"API-like paths in JS: {api_pats[:20]}")

        browser.close()

if __name__ == "__main__":
    run()
