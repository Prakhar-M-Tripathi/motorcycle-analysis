"""
Use Playwright to:
1. Capture the session cookies/tokens from heromotocorp dealer locator
2. Fetch v1/localities API with those headers
3. Also check dealers.heromotocorp.com/api/get-custom-json/
"""
import sys, json, re
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

HE  = '3ad8111e-c406-496b-bf95-a582f0a9fbf1'   # showrooms
HES = 'f9adb2fa-40e9-4795-a3ea-b9eafba3048e'   # service centres

try:
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        captured = {}

        def on_response(resp):
            url = resp.url
            if 'dashloc' in url or 'get-custom-json' in url:
                try:
                    body = resp.body()
                    captured[url] = body.decode('utf-8', 'replace')
                    print(f'  CAPTURED: {url}\n    len={len(body)}, preview={body[:300]}')
                except Exception as e:
                    print(f'  CAPTURE ERR {url}: {e}')

        # === Page 1: Delhi showrooms ===
        page = browser.new_page()
        page.on('response', on_response)
        print('Loading Delhi showrooms page...')
        page.goto(f'https://dealers.heromotocorp.com/locator/delhi/?companyid={HE}',
                  wait_until='networkidle', timeout=30000)
        page.wait_for_timeout(2000)

        # Get cookies + headers from the context
        cookies = page.context.cookies()
        cookie_str = '; '.join(f'{c["name"]}={c["value"]}' for c in cookies)
        print(f'\nCookies: {cookie_str[:300]}')

        # Now try API directly from within the page context (bypasses CORS)
        print('\nFetching v1/localities from page context...')
        result = page.evaluate(f"""
            async () => {{
                const r = await fetch('https://weblocationapi.dashloc.com/v1/localities/{HE}/?city=all');
                const t = await r.text();
                return t;
            }}
        """)
        print(f'  localities/{HE}/?city=all: {result[:500]}')

        # Try /api/get-custom-json/
        result2 = page.evaluate(f"""
            async () => {{
                const r = await fetch('https://dealers.heromotocorp.com/api/get-custom-json/{HE}/');
                const t = await r.text();
                return t;
            }}
        """)
        print(f'\n  get-custom-json/{HE}/: len={len(result2)}, data={result2[:500]}')

        # Try the service company ID localities
        print('\nFetching localities for HES (service) company...')
        result3 = page.evaluate(f"""
            async () => {{
                const r = await fetch('https://weblocationapi.dashloc.com/v1/localities/{HES}/?city=all');
                const t = await r.text();
                return t;
            }}
        """)
        print(f'  localities/{HES}/?city=all: {result3[:500]}')

        # Try fetching locations for a specific city
        result4 = page.evaluate(f"""
            async () => {{
                const r = await fetch('https://weblocationapi.dashloc.com/v1/localities/{HE}/?city=delhi');
                const t = await r.text();
                return t;
            }}
        """)
        print(f'\n  localities with city=delhi: {result4[:500]}')

        # Navigate to a page where dealers actually show and intercept the XHR
        print('\nNavigating and waiting for dealer list to load...')
        page2 = browser.new_page()
        page2.on('response', on_response)
        page2.goto(f'https://dealers.heromotocorp.com/locator/delhi/?companyid={HE}',
                  wait_until='domcontentloaded', timeout=30000)
        page2.wait_for_timeout(5000)   # wait for lazy XHRs

        browser.close()

    # Summarise captures
    print(f'\n=== Captured {len(captured)} API responses ===')
    for url, body in captured.items():
        print(f'\n  URL: {url}')
        print(f'  Body (first 600): {body[:600]}')

except ImportError:
    print('Playwright not installed.')
except Exception as e:
    import traceback; traceback.print_exc()
