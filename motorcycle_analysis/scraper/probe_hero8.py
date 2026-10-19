"""
Extract Hero dealer data via Playwright:
1. Pull Nuxt _asyncData payload (contains SSR-fetched dealers)
2. Find the exact endpoint that returns dealer records
3. Fetch all cities
"""
import sys, json, re
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

HE  = '3ad8111e-c406-496b-bf95-a582f0a9fbf1'   # showrooms
HES = 'f9adb2fa-40e9-4795-a3ea-b9eafba3048e'   # service centres

try:
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)

        api_log = []
        def capture(resp):
            url = resp.url
            if ('dashloc' in url or 'heromotocorp.com/api' in url) and resp.status == 200:
                try:
                    body = resp.body()
                    if len(body) > 30:
                        api_log.append({'url': url, 'data': body[:5000].decode('utf-8','replace')})
                except: pass

        pg = browser.new_page()
        pg.on('response', capture)

        # Load Delhi city page
        print('Loading Delhi page...')
        pg.goto(f'https://dealers.heromotocorp.com/locator/delhi/?companyid={HE}',
                wait_until='networkidle', timeout=40000)
        pg.wait_for_timeout(3000)

        # Extract Nuxt payload
        print('\nExtracting Nuxt payload...')
        payload = pg.evaluate("""
            () => {
                try {
                    const app = useNuxtApp();
                    // payload contains SSR-fetched data
                    const p = app.payload;
                    return JSON.stringify({
                        payloadKeys: Object.keys(p || {}),
                        asyncDataKeys: Object.keys(p?._asyncData || p?.data || {}),
                        stateKeys: Object.keys(p?.state || {}),
                    });
                } catch(e) { return 'err: ' + e; }
            }
        """)
        print('  Payload structure:', payload)

        # Try to get the actual asyncData values
        async_data = pg.evaluate("""
            () => {
                try {
                    const app = useNuxtApp();
                    const p = app.payload;
                    // Serialize asyncData
                    const ad = p?._asyncData || p?.data || {};
                    const out = {};
                    for (const key of Object.keys(ad)) {
                        const val = ad[key];
                        out[key] = {
                            type: typeof val?.data,
                            len: Array.isArray(val?.data) ? val.data.length : (val?.data ? 1 : 0),
                            preview: JSON.stringify(val?.data)?.substring(0, 300)
                        };
                    }
                    return JSON.stringify(out);
                } catch(e) { return 'err: ' + e; }
            }
        """)
        print('  AsyncData:', async_data[:1000])

        # Get Pinia store state
        pinia = pg.evaluate("""
            () => {
                try {
                    if (window.__pinia) {
                        const state = window.__pinia.state.value;
                        const out = {};
                        for (const [k,v] of Object.entries(state)) {
                            out[k] = {
                                keys: Object.keys(v || {}),
                                preview: JSON.stringify(v)?.substring(0,300)
                            };
                        }
                        return JSON.stringify(out);
                    }
                    return 'no pinia';
                } catch(e) { return 'err: ' + e; }
            }
        """)
        print('\n  Pinia state:', pinia[:1000])

        # Check DOM for dealer cards
        dealer_count = pg.evaluate("""
            () => {
                // DashLoc typically renders dl-location-card or similar
                const selectors = [
                    '[class*="location"]',
                    '[class*="dealer"]',
                    '[class*="store"]',
                    '[class*="outlet"]',
                    '[data-id]',
                    '.dl-card',
                    '.location-card',
                ];
                const counts = {};
                for (const s of selectors) {
                    counts[s] = document.querySelectorAll(s).length;
                }
                return JSON.stringify(counts);
            }
        """)
        print('\n  DOM dealer elements:', dealer_count)

        # Now try to intercept the actual search API by triggering a search
        print('\nTriggering search for "delhi"...')
        try:
            # Find search input
            inputs = pg.query_selector_all('input')
            print(f'  Found {len(inputs)} inputs')
            for inp in inputs[:5]:
                ph = inp.get_attribute('placeholder') or ''
                t  = inp.get_attribute('type') or ''
                print(f'    input type={t} placeholder={ph}')
        except Exception as e:
            print(f'  Error: {e}')

        # Try fetching with the exact headers the page uses
        print('\nFetching location search endpoint with page headers...')
        api_candidates = [
            f'https://weblocationapi.dashloc.com/v1/location/?companyId={HE}&city=delhi&limit=50&offset=0',
            f'https://weblocationapi.dashloc.com/v1/location/?companyId={HE}&city=delhi',
            f'https://weblocationapi.dashloc.com/v1/location/{HE}/delhi/',
            f'https://weblocationapi.dashloc.com/v1/search/?companyId={HE}&query=delhi&limit=50',
            f'https://weblocationapi.dashloc.com/v1/company-location/?companyId={HE}&city=delhi',
        ]
        for url in api_candidates:
            res = pg.evaluate(f"""
                async () => {{
                    const r = await fetch('{url}', {{
                        headers: {{
                            'Accept': 'application/json',
                            'Origin': 'https://dealers.heromotocorp.com',
                            'Referer': 'https://dealers.heromotocorp.com/'
                        }}
                    }});
                    return r.status + '::' + (await r.text()).substring(0, 400);
                }}
            """)
            status, body = res.split('::', 1) if '::' in res else (res, '')
            if body and body != '':
                print(f'  {status} | {url[-60:]}: {body[:300]}')
            else:
                print(f'  {status} | {url[-60:]}: (empty)')

        browser.close()

    print(f'\n=== All captured API responses ({len(api_log)} total) ===')
    for item in api_log:
        print(f'\n  {item["url"]}')
        print(f'  {item["data"][:500]}')

except Exception as e:
    import traceback; traceback.print_exc()
