"""
The DashLoc SSR pages are huge (550KB-1.1MB).
Dealers are likely embedded in the HTML. Let's extract them.
Also use Playwright to interact with search and capture the real API call.
"""
import sys, json, re, urllib.request, ssl
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

HE  = '3ad8111e-c406-496b-bf95-a582f0a9fbf1'
HES = 'f9adb2fa-40e9-4795-a3ea-b9eafba3048e'

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

def get(url):
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 Chrome/120'})
    resp = urllib.request.urlopen(req, timeout=20, context=ctx)
    return resp.read().decode('utf-8', 'replace')

# --- Parse dealer HTML from SSR page ---
print('=== Parsing Delhi SSR page for dealer data ===')
html = get(f'https://dealers.heromotocorp.com/locator/delhi/?companyid={HE}')
print(f'Page size: {len(html):,} bytes')

# Look for dealer cards - try multiple patterns DashLoc uses
# Pattern 1: JSON-LD structured data
for m in re.finditer(r'<script type="application/ld\+json">(.*?)</script>', html, re.S):
    try:
        obj = json.loads(m.group(1))
        t = obj.get('@type', '')
        if t in ('AutoDealer', 'LocalBusiness', 'AutomotiveBusiness', 'ItemList', 'Store'):
            print(f'  JSON-LD: @type={t}, keys={list(obj.keys())}')
            print(f'  Preview: {str(obj)[:500]}')
    except: pass

# Pattern 2: data-location or data-dealer attributes
locs = re.findall(r'data-(?:location|dealer|store|outlet)\s*=\s*["\'](\{[^"\']{10,500}\})["\']', html)
print(f'  data-location attrs: {len(locs)}')
for l in locs[:2]: print(f'    {l[:200]}')

# Pattern 3: __NUXT_DATA__ embedded JSON
nuxt_data = re.search(r'<script type="application/json" id="__NUXT_DATA__">(.*?)</script>', html, re.S)
if nuxt_data:
    raw = nuxt_data.group(1)
    print(f'\n  __NUXT_DATA__ found, len={len(raw)}')
    # Parse it - Nuxt 3 payload is a structured array
    try:
        arr = json.loads(raw)
        # Flatten to find dealer-like objects
        flat = json.dumps(arr)
        names = re.findall(r'"(?:displayName|name|title)"\s*:\s*"([A-Z][A-Za-z ]{5,60})"', flat)
        print(f'  Names found: {names[:10]}')
        lats = re.findall(r'"lat(?:itude)?"\s*:\s*"?([0-9]{2}\.[0-9]+)"?', flat)
        print(f'  Lats found: {lats[:10]}')
        slugs = re.findall(r'"slug"\s*:\s*"([a-z0-9-]+)"', flat)
        print(f'  Slugs (first 10): {slugs[:10]}')
    except Exception as e:
        print(f'  Parse error: {e}')
else:
    print('\n  No __NUXT_DATA__ found')

# Pattern 4: Look for dealer URL slugs in anchor tags
dealer_links = re.findall(r'href="(https://dealers\.heromotocorp\.com/locator/delhi/[^"]+)"', html)
print(f'\n  Dealer links found: {len(dealer_links)}')
for d in dealer_links[:5]: print(f'    {d}')

# Pattern 5: Look for window.__data or similar
win_data = re.findall(r'window\.__(?:data|store|state|dealers)\s*=\s*(\{[^<]{50,})', html)
print(f'\n  window.__data etc: {len(win_data)} matches')

# Pattern 6: Phone numbers (common in dealer listings)
phones = re.findall(r'[+]?91[-\s]?[6-9]\d{9}|0\d{10}', html)
print(f'\n  Phone numbers found: {len(phones)}, first 5: {phones[:5]}')

# Use Playwright to search and capture what actually gets called
print('\n=== Playwright: interact with search and capture real API ===')
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
                        api_log.append({'url': url, 'data': body[:2000].decode('utf-8', 'replace')})
                except: pass

        pg = browser.new_page()
        pg.on('response', capture)

        # Load the national locator (not city-specific) to see if a different search triggers
        pg.goto(f'https://dealers.heromotocorp.com/?companyid={HE}',
                wait_until='domcontentloaded', timeout=30000)
        pg.wait_for_timeout(3000)

        # Try clicking on the search/all-dealers area
        try:
            pg.fill('input[type="text"], input[placeholder*="city"], input[placeholder*="search"]', 'delhi')
            pg.wait_for_timeout(2000)
        except: pass

        # Evaluate JS to see what the Nuxt store holds
        store_data = pg.evaluate("""
            () => {
                // Try Nuxt 3 useNuxtApp / useState
                if (typeof useNuxtApp !== 'undefined') {
                    try {
                        const app = useNuxtApp();
                        return JSON.stringify(Object.keys(app));
                    } catch(e) { return 'useNuxtApp err: ' + e; }
                }
                // Try window.__nuxt
                if (window.__nuxt) return JSON.stringify(Object.keys(window.__nuxt));
                // Try Pinia stores
                if (window.__pinia) return JSON.stringify(Object.keys(window.__pinia.state.value));
                return 'no store found';
            }
        """)
        print(f'  Store data: {store_data}')

        # Fetch full location list from page context with proper auth
        for endpoint in [
            f'https://weblocationapi.dashloc.com/v1/location/?companyId={HE}&limit=100&offset=0',
            f'https://weblocationapi.dashloc.com/v1/location/?company_id={HE}',
            f'https://weblocationapi.dashloc.com/v1/search/?companyId={HE}&q=&limit=100',
            f'https://weblocationapi.dashloc.com/v1/company/{HE}/locations/?limit=50',
        ]:
            result = pg.evaluate(f"""
                async () => {{
                    const r = await fetch('{endpoint}');
                    return r.status + '::' + await r.text();
                }}
            """)
            status, body = result.split('::', 1) if '::' in result else (result, '')
            print(f'  {endpoint[-60:]}: {status}, {body[:200]}')

        browser.close()

    print(f'\nCaptured {len(api_log)} non-empty API responses:')
    for item in api_log:
        print(f'\n  URL: {item["url"]}')
        print(f'  Data: {item["data"][:400]}')

except Exception as e:
    import traceback; traceback.print_exc()
