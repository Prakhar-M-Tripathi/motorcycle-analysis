"""
Approach: Parse individual dealer pages (which have JSON-LD structured data)
and use Playwright to trigger the search and extract DOM cards.
"""
import sys, json, re, urllib.request, ssl
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

HE  = '3ad8111e-c406-496b-bf95-a582f0a9fbf1'
HES = 'f9adb2fa-40e9-4795-a3ea-b9eafba3048e'

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

def get(url):
    req = urllib.request.Request(url, headers={'User-Agent':'Mozilla/5.0 Chrome/120'})
    return urllib.request.urlopen(req, timeout=20, context=ctx).read().decode('utf-8','replace')

# 1. Check one individual dealer page for JSON-LD
print('=== Individual dealer page JSON-LD ===')
dealer_url = 'https://dealers.heromotocorp.com/locator/kanpur/govind-nagar/swami-automobiles-hero-motocorp-in-govind-nagar-kanpur--2DM25Z/home'
html = get(dealer_url)
print(f'Page size: {len(html):,}')
for m in re.finditer(r'<script type="application/ld\+json">(.*?)</script>', html, re.S):
    try:
        obj = json.loads(m.group(1))
        print(f'\nJSON-LD type: {obj.get("@type")}')
        # Show key fields
        for key in ['name','address','geo','telephone','openingHours','@type','url','priceRange','additionalType','hasOfferCatalog']:
            if key in obj:
                print(f'  {key}: {obj[key]}')
    except Exception as e:
        print(f'  parse error: {e}')

# 2. Use Playwright to trigger search on the locator page and extract DOM
print('\n=== Playwright: Trigger search, extract DOM dealer cards ===')
try:
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        api_log = []

        def capture(resp):
            if ('dashloc' in resp.url or 'heromotocorp.com/api' in resp.url) and resp.status == 200:
                try:
                    body = resp.body()
                    if len(body) > 50:
                        api_log.append({'url': resp.url, 'data': body.decode('utf-8','replace')})
                except: pass

        pg = browser.new_page()
        pg.on('response', capture)

        # Load national page first
        print('Loading national page...')
        pg.goto(f'https://dealers.heromotocorp.com/?companyid={HE}',
                wait_until='domcontentloaded', timeout=30000)
        pg.wait_for_timeout(2000)

        # Find and interact with the search box
        inputs = pg.query_selector_all('input')
        search_input = None
        for inp in inputs:
            t = inp.get_attribute('type') or ''
            if t != 'hidden':
                search_input = inp
                break

        if search_input:
            print('  Typing "Delhi" in search...')
            search_input.click()
            search_input.type('Delhi', delay=100)
            pg.wait_for_timeout(3000)

            # Look for suggestions/autocomplete
            suggestions = pg.evaluate("""
                () => {
                    const items = document.querySelectorAll('[class*="suggest"], [class*="autocomplete"], [class*="dropdown"] li, [class*="result"]');
                    return Array.from(items).slice(0,5).map(el => ({
                        tag: el.tagName,
                        cls: el.className,
                        text: el.textContent.trim().substring(0,60)
                    }));
                }
            """)
            print(f'  Suggestions: {json.dumps(suggestions)}')

            # Press Enter or click first suggestion
            pg.keyboard.press('Enter')
            pg.wait_for_timeout(4000)
        else:
            print('  No search input found')

        # Check DOM for dealer cards now
        dom_info = pg.evaluate("""
            () => {
                // Cast wide net
                const all = document.querySelectorAll('*');
                const classes = new Set();
                for (const el of all) {
                    for (const cls of el.classList) {
                        if (/deal|locat|store|outlet|card|result|item|branch/i.test(cls)) {
                            classes.add(el.tagName + '.' + cls);
                        }
                    }
                }
                return {
                    matchingClasses: Array.from(classes).slice(0,20),
                    bodyText: document.body.innerText.substring(0, 500)
                };
            }
        """)
        print(f'\n  Matching classes: {dom_info["matchingClasses"]}')
        print(f'  Page text: {dom_info["bodyText"][:300]}')

        # Also try fetching the API from inside the page now that we're on national page
        for ep in [
            f'https://weblocationapi.dashloc.com/v1/location/?companyId={HE}&city=delhi&limit=50',
            f'https://weblocationapi.dashloc.com/v1/location/?companyId={HE}&limit=200',
            f'https://weblocationapi.dashloc.com/v1/company-info/{HE}/',
        ]:
            r = pg.evaluate(f"""
                async () => {{
                    const r = await fetch('{ep}');
                    return r.status + '|' + (await r.text()).substring(0, 500);
                }}
            """)
            s, b = r.split('|', 1) if '|' in r else (r, '')
            print(f'  {s} | {ep[-50:]}: {b[:200]}')

        browser.close()

    print(f'\n=== Captured {len(api_log)} API responses ===')
    for item in api_log:
        print(f'\n  {item["url"]}')
        print(f'  {item["data"][:600]}')

except Exception as e:
    import traceback; traceback.print_exc()
