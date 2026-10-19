"""
Count Hero service centres and showrooms per city using the DashLoc sitemap.
- heCompanyId  (HE)  = showrooms
- hesCompanyId (HES) = service centres

Strategy:
1. Fetch sitemap.xml for both company IDs
2. Parse city-level and batch sitemaps
3. Count dealers per city → save to data/raw/hero_official.json
"""
import sys, json, re, urllib.request, ssl, time, collections
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

HE  = '3ad8111e-c406-496b-bf95-a582f0a9fbf1'   # showrooms
HES = 'f9adb2fa-40e9-4795-a3ea-b9eafba3048e'   # service centres

def get(url, retries=2):
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 Chrome/120'})
    for attempt in range(retries + 1):
        try:
            resp = urllib.request.urlopen(req, timeout=25, context=ctx)
            return resp.read().decode('utf-8', 'replace')
        except Exception as e:
            if attempt == retries:
                raise
            time.sleep(1)

def parse_locs(xml):
    return re.findall(r'<loc>(.*?)</loc>', xml)

def extract_city_from_url(url):
    """Extract city slug from /locator/{city}/{area}/{dealer}/home"""
    m = re.search(r'/locator/([a-z0-9\-]+)/', url)
    return m.group(1) if m else None

# ── Fetch master sitemap for a company ID ─────────────────────────────────────
def fetch_all_dealer_urls(company_id, label):
    print(f'\n=== {label} ({company_id[:8]}...) ===')
    master_url = f'https://dealers.heromotocorp.com/sitemap.xml?cid={company_id}'
    try:
        xml = get(master_url)
    except Exception as e:
        print(f'  Master sitemap error: {e}')
        return []

    locs = parse_locs(xml)
    print(f'  Master locs: {len(locs)}')

    # Separate cities sitemap from batch sitemaps
    cities_locs = [l for l in locs if 'bid=cities' in l]
    batch_locs  = [l for l in locs if 'bid=' in l and 'bid=cities' not in l]
    print(f'  Cities sitemap entries: {len(cities_locs)}')
    print(f'  Batch sitemaps: {len(batch_locs)}')

    # Show first few locs
    for l in locs[:5]:
        print(f'    {l}')

    # Fetch cities sitemap
    all_dealer_urls = []
    if cities_locs:
        try:
            cities_xml = get(cities_locs[0])
            city_urls = parse_locs(cities_xml)
            print(f'\n  City URLs in cities sitemap: {len(city_urls)}')
            for u in city_urls[:5]: print(f'    {u}')
        except Exception as e:
            print(f'  Cities sitemap error: {e}')

    # Fetch all batch sitemaps to get individual dealer URLs
    print(f'\n  Fetching {len(batch_locs)} batch sitemaps...')
    for i, batch_url in enumerate(batch_locs):
        try:
            batch_xml = get(batch_url)
            urls = parse_locs(batch_xml)
            dealer_urls = [u for u in urls if '/locator/' in u and '/home' in u]
            all_dealer_urls.extend(dealer_urls)
            if i < 3:
                print(f'  Batch {i+1}: {len(dealer_urls)} dealer URLs, e.g. {dealer_urls[0] if dealer_urls else "none"}')
            time.sleep(0.1)
        except Exception as e:
            print(f'  Batch {i+1} error: {e}')

    print(f'\n  Total dealer URLs: {len(all_dealer_urls)}')
    return all_dealer_urls

# ── Run for both company IDs ──────────────────────────────────────────────────
sw_urls = fetch_all_dealer_urls(HE,  'SHOWROOMS (heCompanyId)')
sc_urls = fetch_all_dealer_urls(HES, 'SERVICE CENTRES (hesCompanyId)')

# ── Count by city ─────────────────────────────────────────────────────────────
print('\n=== Counting by city ===')

def count_by_city(urls):
    counts = collections.Counter()
    for url in urls:
        city = extract_city_from_url(url)
        if city:
            counts[city] += 1
    return dict(counts)

sw_by_city = count_by_city(sw_urls)
sc_by_city = count_by_city(sc_urls)

# Merge
all_cities = set(list(sw_by_city.keys()) + list(sc_by_city.keys()))
result = {}
for city in sorted(all_cities):
    result[city] = {
        'sw': sw_by_city.get(city, 0),
        'sc': sc_by_city.get(city, 0),
    }

print(f'Cities with showrooms: {len(sw_by_city)}')
print(f'Cities with service centres: {len(sc_by_city)}')
print(f'Total unique cities: {len(all_cities)}')
print(f'\nTotal showrooms: {sum(sw_by_city.values())}')
print(f'Total service centres: {sum(sc_by_city.values())}')

print('\nTop 15 cities by SC count:')
for city, d in sorted(result.items(), key=lambda x: -x[1]['sc'])[:15]:
    print(f'  {city:<25} SC={d["sc"]:<5} SW={d["sw"]}')

# Save
import os
out_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                        'data', 'raw', 'hero_official.json')
with open(out_path, 'w', encoding='utf-8') as f:
    json.dump({'showrooms': sw_by_city, 'service_centres': sc_by_city,
               'by_city': result, 'total_sw': sum(sw_by_city.values()),
               'total_sc': sum(sc_by_city.values()),
               'source': 'dealers.heromotocorp.com sitemap'}, f, indent=2)
print(f'\nSaved to {out_path}')
