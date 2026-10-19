"""
Scrape Hero's official dealer network using Playwright (bypasses WAF).
Uses DashLoc sitemap batch files to enumerate all dealer URLs, then
counts dealers per city by parsing URL slugs.

Company IDs (from __NUXT__ config):
  heCompanyId  = 3ad8111e-...  → dealers.heromotocorp.com (showrooms)
  hesCompanyId = f9adb2fa-...  → partsdistributors.heromotocorp.com (parts/SC)

Run: python scraper/hero_scrape_official.py
Output: data/raw/hero_official.json
"""
import sys, re, json, os, time, collections
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_PATH = os.path.join(PROJECT_DIR, 'data', 'raw', 'hero_official.json')

HE  = '3ad8111e-c406-496b-bf95-a582f0a9fbf1'   # showrooms
HES = 'f9adb2fa-40e9-4795-a3ea-b9eafba3048e'   # parts distributors (service proxy)

from playwright.sync_api import sync_playwright

def fetch_via_playwright(urls, label, browser):
    """Fetch a list of URLs via Playwright, return {url: content}."""
    results = {}
    pg = browser.new_page()
    print(f'  Fetching {len(urls)} pages for [{label}]...')
    for i, url in enumerate(urls):
        try:
            resp = pg.goto(url, wait_until='domcontentloaded', timeout=15000)
            if resp and resp.status == 200:
                results[url] = pg.content()
            else:
                results[url] = ''
        except Exception as e:
            results[url] = ''
        if (i+1) % 50 == 0:
            print(f'    {i+1}/{len(urls)} done')
    pg.close()
    return results

def parse_locs(html):
    return [l.replace('&amp;', '&') for l in re.findall(r'<loc>(.*?)</loc>', html)]

def city_from_url(url):
    """Extract city slug from /locator/{city}/... or /location/{city}/..."""
    m = re.search(r'/locator/([a-z0-9\-]+)/', url)
    if not m:
        m = re.search(r'/location/([a-z0-9\-]+)/', url)
    return m.group(1) if m else None

def is_dealer_url(url):
    return '/locator/' in url and '/home' in url

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    pg0 = browser.new_page()

    # ── Step 1: Get master sitemap, extract batch URLs ────────────────────────
    print('Step 1: Fetching master sitemaps...')
    results = {}
    for cid, label, base in [
        (HE,  'showrooms', 'dealers.heromotocorp.com'),
        (HES, 'parts_sc',  'partsdistributors.heromotocorp.com'),
    ]:
        pg0.goto(f'https://{base}/sitemap.xml', wait_until='domcontentloaded', timeout=20000)
        locs = parse_locs(pg0.content())
        # Filter to this company's batch sitemaps
        batch_urls = [l for l in locs if f'cid={cid}' in l and 'bid=cities' not in l]
        city_sm    = [l for l in locs if f'cid={cid}' in l and 'bid=cities' in l]
        print(f'  [{label}] batch sitemaps: {len(batch_urls)}, city sitemaps: {len(city_sm)}')
        results[cid] = {'batch_urls': batch_urls, 'city_sm': city_sm, 'label': label, 'base': base}

    pg0.close()

    # ── Step 2: Fetch all batch sitemaps ──────────────────────────────────────
    all_dealer_urls = {HE: [], HES: []}

    for cid, meta in results.items():
        batch_urls = meta['batch_urls']
        label      = meta['label']
        print(f'\nStep 2: Fetching {len(batch_urls)} batch sitemaps for [{label}]...')
        pg = browser.new_page()
        for i, url in enumerate(batch_urls):
            try:
                resp = pg.goto(url, wait_until='domcontentloaded', timeout=15000)
                if resp and resp.status == 200:
                    locs = parse_locs(pg.content())
                    dealer_urls = [u for u in locs if is_dealer_url(u)]
                    all_dealer_urls[cid].extend(dealer_urls)
            except Exception as e:
                pass
            if (i+1) % 100 == 0:
                print(f'  {i+1}/{len(batch_urls)} batches, {len(all_dealer_urls[cid])} dealers so far')
        pg.close()
        print(f'  [{label}] Total dealer URLs: {len(all_dealer_urls[cid])}')

    browser.close()

# ── Step 3: Count by city ─────────────────────────────────────────────────────
print('\nStep 3: Counting by city...')

def count_by_city(urls):
    c = collections.Counter()
    for url in urls:
        city = city_from_url(url)
        if city: c[city] += 1
    return dict(c)

sw_by_city = count_by_city(all_dealer_urls[HE])
sc_by_city = count_by_city(all_dealer_urls[HES])

all_cities = set(list(sw_by_city) + list(sc_by_city))
by_city = {c: {'sw': sw_by_city.get(c,0), 'sc': sc_by_city.get(c,0)} for c in sorted(all_cities)}

total_sw = sum(sw_by_city.values())
total_sc = sum(sc_by_city.values())

print(f'\n  Showroom cities: {len(sw_by_city)}, total dealers: {total_sw}')
print(f'  Parts/SC cities: {len(sc_by_city)}, total dealers: {total_sc}')
print(f'  Combined unique cities: {len(all_cities)}')

print('\nTop 15 cities by showroom count:')
for city, n in sorted(sw_by_city.items(), key=lambda x:-x[1])[:15]:
    print(f'  {city:<25} SW={n:<5} SC={sc_by_city.get(city,0)}')

out = {
    'source': 'dealers.heromotocorp.com + partsdistributors.heromotocorp.com (DashLoc sitemap)',
    'scraped_date': '2026-06-11',
    'total_sw': total_sw,
    'total_sc': total_sc,
    'sw_cities': len(sw_by_city),
    'sc_cities': len(sc_by_city),
    'showrooms_by_city': sw_by_city,
    'service_by_city': sc_by_city,
    'by_city': by_city,
    'sw_dealer_urls': all_dealer_urls[HE][:50],   # sample only
    'sc_dealer_urls': all_dealer_urls[HES][:50],
}
with open(OUT_PATH, 'w', encoding='utf-8') as f:
    json.dump(out, f, indent=2, ensure_ascii=False)
print(f'\nSaved: {OUT_PATH}')
