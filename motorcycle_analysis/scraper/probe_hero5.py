"""
Find actual dealer data in Hero's SSR page and intercept DashLoc API calls via Playwright.
Also test hesCompanyId (Hero service centres).
"""
import urllib.request, ssl, sys, re, json
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120',
    'Accept': '*/*',
    'Origin': 'https://dealers.heromotocorp.com',
    'Referer': 'https://dealers.heromotocorp.com/',
}

HE_COMPANY  = '3ad8111e-c406-496b-bf95-a582f0a9fbf1'   # showrooms
HES_COMPANY = 'f9adb2fa-40e9-4795-a3ea-b9eafba3048e'   # service centres

def get(url, extra=None):
    h = {**HEADERS, **(extra or {})}
    req = urllib.request.Request(url, headers=h)
    try:
        resp = urllib.request.urlopen(req, timeout=20, context=ctx)
        return resp.read().decode('utf-8', 'replace'), resp.status
    except Exception as e:
        return None, str(e)

# 1. Mine the Delhi SSR page for embedded dealer objects
print('=== Mining SSR page for embedded dealer data ===')
data, _ = get(f'https://dealers.heromotocorp.com/locator/delhi/?companyid={HE_COMPANY}')
if data:
    # Look for JSON blobs containing dealer info
    # DashLoc pages embed dealer lists as window.__data or as JSON-LD
    json_ld = re.findall(r'<script type="application/ld\+json">(.*?)</script>', data, re.S)
    for i, jl in enumerate(json_ld[:3]):
        try:
            obj = json.loads(jl)
            print(f'  JSON-LD {i}: type={obj.get("@type","?")} keys={list(obj.keys())[:6]}')
            # If it's a list of local businesses
            if obj.get('@type') == 'ItemList':
                items = obj.get('itemListElement', [])
                print(f'  Items: {len(items)}')
                if items:
                    print(f'  First item: {str(items[0])[:300]}')
        except Exception as e:
            print(f'  JSON-LD {i} parse error: {e}')

    # Look for Nuxt payload data
    payload = re.findall(r'<script type="application/json" id="__NUXT_DATA__">(.*?)</script>', data, re.S)
    if payload:
        print(f'\n  Found __NUXT_DATA__ blob, length={len(payload[0])}')
        try:
            j = json.loads(payload[0])
            print(f'  Type: {type(j).__name__}')
            raw = json.dumps(j)
            # Search for latitude/longitude
            lats = re.findall(r'"lat(?:itude)?"\s*:\s*([0-9]+\.[0-9]+)', raw)
            print(f'  Lat values: {lats[:10]}')
            # search for dealer count
            names_raw = re.findall(r'"(?:name|title)"\s*:\s*"([A-Z][^"]{5,60})"', raw)
            print(f'  Names (first 10): {names_raw[:10]}')
        except Exception as e:
            print(f'  Parse error: {e}')

# 2. Try API with hesCompanyId (Hero service)
print('\n=== Testing hesCompanyId (Hero Service) ===')
for url in [
    f'https://dealers.heromotocorp.com/locator/delhi/?companyid={HES_COMPANY}',
    f'https://dealers.heromotocorp.com/locator/mumbai/?companyid={HES_COMPANY}',
]:
    d, status = get(url)
    if d:
        print(f'\n  URL: {url[-60:]} -> {status}, len={len(d)}')
        jl = re.findall(r'<script type="application/ld\+json">(.*?)</script>', d, re.S)
        for j in jl[:2]:
            try:
                obj = json.loads(j)
                items = obj.get('itemListElement', [])
                print(f'  JSON-LD type={obj.get("@type")} items={len(items)}')
                if items:
                    print(f'  First: {str(items[0])[:400]}')
            except: pass
        # check name/address patterns
        names = re.findall(r'"(?:name|title)"\s*:\s*"([A-Z][^"]{5,60} Hero[^"]{0,30})"', d)
        print(f'  Hero names: {names[:5]}')
        # latitude
        lats = re.findall(r'latitude.*?([0-9]{2}\.[0-9]+)', d[:50000])
        print(f'  Lats: {lats[:5]}')

# 3. Use Playwright to intercept actual API calls
print('\n=== Playwright network intercept ===')
try:
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        api_calls = []

        def on_request(req):
            if 'dashloc' in req.url or 'api' in req.url.lower():
                api_calls.append(req.url)

        def on_response(resp):
            if 'dashloc' in resp.url and resp.status == 200:
                try:
                    body = resp.body()
                    api_calls.append(f'RESPONSE {resp.url}: {body[:500]}')
                except: pass

        page = browser.new_page()
        page.on('request', on_request)
        page.on('response', on_response)

        print('  Loading Delhi dealer page...')
        page.goto(f'https://dealers.heromotocorp.com/locator/delhi/?companyid={HE_COMPANY}',
                  wait_until='networkidle', timeout=30000)
        page.wait_for_timeout(3000)

        print(f'  Intercepted {len(api_calls)} API calls:')
        for c in api_calls[:20]:
            print(f'    {c[:200]}')

        browser.close()
except ImportError:
    print('  Playwright not installed, skipping.')
except Exception as e:
    print(f'  Playwright error: {e}')
