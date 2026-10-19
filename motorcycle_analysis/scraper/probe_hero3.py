"""Dig deeper into Hero dealer API: try per-city SSR pages and JS bundle."""
import urllib.request, ssl, sys, re, json
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120',
    'Accept': 'application/json, text/plain, */*',
    'Origin': 'https://dealers.heromotocorp.com',
    'Referer': 'https://dealers.heromotocorp.com/',
}

def get(url, extra=None):
    h = {**HEADERS, **(extra or {})}
    req = urllib.request.Request(url, headers=h)
    try:
        resp = urllib.request.urlopen(req, timeout=15, context=ctx)
        data = resp.read().decode('utf-8', 'replace')
        return data, resp.status
    except Exception as e:
        return None, str(e)

# 1. Fetch a per-city locator page (SSR) and look for embedded JSON data
print('=== 1. Per-city SSR page: Delhi ===')
data, status = get('https://dealers.heromotocorp.com/locator/delhi/?companyid=3ad8111e-c406-496b-bf95-a582f0a9fbf1')
if data:
    print(f'  Status: {status}, Length: {len(data)}')
    # Look for __NUXT__ or window.__data__ blobs
    nuxt = re.findall(r'__NUXT__\s*=\s*(\{.{0,5000}?\});?\s*</script', data, re.S)
    if nuxt:
        print('  Found __NUXT__ blob:', nuxt[0][:300])
    # Look for latitude/longitude data
    lats = re.findall(r'"lat(?:itude)?"\s*:\s*([0-9.]+)', data)
    lngs = re.findall(r'"lon(?:gitude)?"|"lng"\s*:\s*([0-9.]+)', data)
    print(f'  Lat values found: {lats[:5]}')
    # Look for dealer counts
    types = re.findall(r'"type"\s*:\s*"([^"]+)"', data)
    print(f'  Types found: {set(types)}')
    # Look for dealer names
    names = re.findall(r'"name"\s*:\s*"([^"]{5,60})"', data)
    print(f'  Names (first 5): {names[:5]}')
    # Check for companyLocations or similar
    for kw in ['companyLocations', 'locations', 'dealers', 'outlets', 'dealerList']:
        if kw in data:
            idx = data.index(kw)
            print(f'  Keyword "{kw}" at pos {idx}: ...{data[idx:idx+300]}...')
            break

# 2. Try the DashLoc API with POST and different headers
print('\n=== 2. DashLoc POST attempts ===')
COMPANY_ID = '3ad8111e-c406-496b-bf95-a582f0a9fbf1'
post_attempts = [
    ('https://weblocationapi.dashloc.com/api/location/search',
     json.dumps({'companyId': COMPANY_ID, 'city': 'delhi'}).encode()),
    ('https://weblocationapi.dashloc.com/api/location/list',
     json.dumps({'companyId': COMPANY_ID}).encode()),
]
for url, body in post_attempts:
    h = {**HEADERS, 'Content-Type': 'application/json'}
    req = urllib.request.Request(url, data=body, headers=h, method='POST')
    try:
        resp = urllib.request.urlopen(req, timeout=10, context=ctx)
        d = resp.read().decode('utf-8', 'replace')
        print(f'  POST {url[-40:]}: {resp.status}, len={len(d)}, data={d[:200]}')
    except Exception as e:
        print(f'  POST {url[-40:]}: {type(e).__name__}: {e}')

# 3. Fetch a Nuxt JS chunk and look for API url patterns
print('\n=== 3. Fetch JS bundle for API patterns ===')
data, status = get('https://d2vhxl2zk4x5d.cloudfront.net/_nuxt/LocatorMain.D8qQ3HQw.css')
# Actually look for the main JS bundle on the dealers page
data, status = get('https://dealers.heromotocorp.com/locator/delhi/?companyid=3ad8111e-c406-496b-bf95-a582f0a9fbf1')
if data:
    # Find JS bundle URLs
    js_files = re.findall(r'src="(https://d2vhxl2zk4x5d[^"]+\.js)"', data)
    print(f'  JS bundles: {js_files[:5]}')
    if js_files:
        # Fetch first meaningful JS file
        for js_url in js_files[:3]:
            jdata, _ = get(js_url)
            if jdata:
                # Look for API endpoint patterns
                api_hits = re.findall(r'["\`](/api/[^"\`\s]{5,80})["\`]', jdata)
                wl_hits = re.findall(r'weblocationapi[^"\s\'"]{0,100}', jdata)
                dashloc_hits = re.findall(r'dashloc[^"\s\'"]{0,100}', jdata)
                print(f'  In {js_url[-40:]}:')
                print(f'    /api/ paths: {api_hits[:5]}')
                print(f'    weblocationapi hits: {wl_hits[:3]}')
                print(f'    dashloc hits: {dashloc_hits[:3]}')
