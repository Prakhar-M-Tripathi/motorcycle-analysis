"""Extract Hero DashLoc API config and find working endpoint."""
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

def get(url, extra=None):
    h = {**HEADERS, **(extra or {})}
    req = urllib.request.Request(url, headers=h)
    try:
        resp = urllib.request.urlopen(req, timeout=20, context=ctx)
        return resp.read().decode('utf-8', 'replace'), resp.status
    except Exception as e:
        return None, str(e)

# Get full NUXT config
data, _ = get('https://dealers.heromotocorp.com/locator/delhi/?companyid=3ad8111e-c406-496b-bf95-a582f0a9fbf1')
if data:
    nuxt = re.search(r'window\.__NUXT__\.config\s*=\s*(\{[^<]{0,8000})', data, re.S)
    if nuxt:
        raw = nuxt.group(1)
        # Find closing brace
        depth = 0
        end = 0
        for i, c in enumerate(raw):
            if c == '{': depth += 1
            elif c == '}':
                depth -= 1
                if depth == 0:
                    end = i+1
                    break
        config_str = raw[:end]
        print('=== Full NUXT config ===')
        print(config_str)
        print()

# Try various DashLoc API patterns for location search
# The hint was /api/get-custom-json/${e}/
COMPANY_ID = '3ad8111e-c406-496b-bf95-a582f0a9fbf1'
print('=== API endpoint attempts ===')
endpoints = [
    f'https://weblocationapi.dashloc.com/api/get-custom-json/{COMPANY_ID}/',
    f'https://weblocationapi.dashloc.com/api/get-custom-json/{COMPANY_ID}',
    f'https://weblocationapi.dashloc.com/api/v1/get-custom-json/{COMPANY_ID}/',
    f'https://weblocationapi.dashloc.com/api/location/{COMPANY_ID}/',
    f'https://weblocationapi.dashloc.com/api/company/{COMPANY_ID}/locations',
    f'https://weblocationapi.dashloc.com/api/company/{COMPANY_ID}',
    # Try with city slug
    f'https://weblocationapi.dashloc.com/api/location/search/?companyId={COMPANY_ID}&city=delhi',
    f'https://weblocationapi.dashloc.com/api/location/search/?companyId={COMPANY_ID}&slug=delhi',
    f'https://weblocationapi.dashloc.com/api/locations/?companyId={COMPANY_ID}&citySlug=delhi',
]
for url in endpoints:
    d, status = get(url)
    if d and len(d) > 5:
        try:
            j = json.loads(d)
            print(f'  JSON! {url[-60:]}: keys={list(j.keys())[:6] if isinstance(j,dict) else f"list[{len(j)}]"}')
            print(f'    Sample: {str(j)[:300]}')
        except:
            print(f'  Raw {url[-60:]}: status={status}, len={len(d)}, data={d[:150]}')
    else:
        print(f'  {url[-60:]}: status={status}, empty')

# Also try fetching the main JS chunk for API patterns
print('\n=== Scan more JS bundles ===')
js_files = re.findall(r'src="(https://d2vhxl2zk4x5d[^"]+\.js)"', data)
print(f'Found {len(js_files)} JS files')
for js_url in js_files:
    jdata, _ = get(js_url)
    if jdata and len(jdata) > 1000:
        # Search for API endpoint patterns
        api_hits = re.findall(r'[`"\']([^`"\']{0,20}(?:location|dealer|search|city|outlet)[^`"\']{0,60})[`"\']', jdata, re.I)
        wl = re.findall(r'weblocationapi[^\s"\'`]{0,80}', jdata)
        custom = re.findall(r'get-custom-json[^\s"\'`]{0,80}', jdata)
        if wl or custom or api_hits:
            print(f'\n  {js_url[-50:]} (len={len(jdata)}):')
            for h in set(api_hits[:8]): print(f'    api: {h}')
            for h in wl[:3]: print(f'    wl: {h}')
            for h in custom[:3]: print(f'    custom: {h}')
