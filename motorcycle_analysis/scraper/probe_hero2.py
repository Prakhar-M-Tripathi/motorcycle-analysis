"""Probe DashLoc API used by heromotocorp.com dealer locator."""
import urllib.request, ssl, sys, re, json
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

COMPANY_ID = "3ad8111e-c406-496b-bf95-a582f0a9fbf1"
BASE_HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120',
    'Accept': 'application/json, text/plain, */*',
    'Origin': 'https://www.heromotocorp.com',
    'Referer': 'https://www.heromotocorp.com/',
}

def get(url, extra_headers=None):
    h = {**BASE_HEADERS, **(extra_headers or {})}
    req = urllib.request.Request(url, headers=h)
    try:
        resp = urllib.request.urlopen(req, timeout=15, context=ctx)
        data = resp.read().decode('utf-8', 'replace')
        print(f'  OK ({resp.status}) len={len(data)}')
        return data
    except Exception as e:
        print(f'  ERR {type(e).__name__}: {e}')
        return None

# Try common DashLoc API patterns
tests = [
    f'https://weblocationapi.dashloc.com/api/location?companyId={COMPANY_ID}',
    f'https://weblocationapi.dashloc.com/api/location/all?companyId={COMPANY_ID}',
    f'https://weblocationapi.dashloc.com/api/cities?companyId={COMPANY_ID}',
    f'https://weblocationapi.dashloc.com/api/search?companyId={COMPANY_ID}&city=delhi',
    f'https://weblocationapi.dashloc.com/api/dealer?companyId={COMPANY_ID}&city=delhi',
    f'https://weblocationapi.dashloc.com/api/v1/location?companyId={COMPANY_ID}',
    f'https://weblocationapi.dashloc.com/locations?companyId={COMPANY_ID}',
    f'https://weblocationapi.dashloc.com/api/location/search?companyId={COMPANY_ID}&query=delhi',
    # Try the dealers subdomain directly
    f'https://dealers.heromotocorp.com/api/location?companyId={COMPANY_ID}',
    f'https://dealers.heromotocorp.com/api/v1/locations?companyId={COMPANY_ID}',
]

for url in tests:
    print(f'\nTesting: {url[:90]}')
    data = get(url)
    if data and len(data) > 20:
        try:
            j = json.loads(data)
            print(f'  JSON keys: {list(j.keys())[:10] if isinstance(j, dict) else type(j).__name__}')
            if isinstance(j, list) and len(j) > 0:
                print(f'  List of {len(j)}, first item keys: {list(j[0].keys())[:8]}')
        except:
            print(f'  Raw (first 200): {data[:200]}')

# Also extract all city slugs from the main page
print('\n\n=== Extracting city list from main page ===')
url = 'https://www.heromotocorp.com/en-in/reach-us/find-hero-bike-dealers.html'
req = urllib.request.Request(url, headers=BASE_HEADERS)
resp = urllib.request.urlopen(req, timeout=15, context=ctx)
html = resp.read().decode('utf-8', 'replace')

# Find all /locator/{city}/ patterns
city_pattern = re.findall(r'/locator/([a-z0-9\-]+)/\?companyid=' + COMPANY_ID, html)
cities = sorted(set(city_pattern))
print(f'Cities found in page: {len(cities)}')
print('First 30:', cities[:30])

# Save city list
with open('data/raw/hero_cities.txt', 'w', encoding='utf-8') as f:
    f.write('\n'.join(cities))
print(f'Saved to data/raw/hero_cities.txt')
