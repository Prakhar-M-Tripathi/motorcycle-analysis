"""
Faster approach: Use the cities sitemap to load each city page,
extract the dealer count from the page DOM/text, and save.

cities sitemap has 9,280 locs — these are state AND city AND locality pages.
We filter to city-level (not state-level) and load each to get dealer counts.
"""
import sys, re, json, os, time, collections
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_PATH    = os.path.join(PROJECT_DIR, 'data', 'raw', 'hero_official.json')

HE  = '3ad8111e-c406-496b-bf95-a582f0a9fbf1'
HES = 'f9adb2fa-40e9-4795-a3ea-b9eafba3048e'

from playwright.sync_api import sync_playwright

def parse_locs(html):
    return [l.replace('&amp;', '&') for l in re.findall(r'<loc>(.*?)</loc>', html)]

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    pg = browser.new_page()

    # ── 1. Inspect sample batch sitemaps to understand URL structure ──────────
    print('=== Step 1: Sample batch sitemaps ===')
    pg.goto(f'https://dealers.heromotocorp.com/sitemap.xml', wait_until='domcontentloaded', timeout=20000)
    master_locs = parse_locs(pg.content())
    batch_locs  = [l for l in master_locs if f'cid={HE}' in l and 'bid=cities' not in l]
    print(f'Total batch sitemaps for showrooms: {len(batch_locs)}')

    # Sample first 5 batch sitemaps
    sample_dealer_urls = []
    for url in batch_locs[:5]:
        pg.goto(url, wait_until='domcontentloaded', timeout=15000)
        locs = parse_locs(pg.content())
        print(f'  Batch locs: {len(locs)}, first: {locs[0] if locs else "empty"}')
        sample_dealer_urls.extend(locs)

    # ── 2. Fetch cities sitemap and inspect URL types ─────────────────────────
    print('\n=== Step 2: Cities sitemap ===')
    cities_sm_url = [l for l in master_locs if f'cid={HE}' in l and 'bid=cities' in l][0]
    print(f'Cities sitemap URL: {cities_sm_url}')
    pg.goto(cities_sm_url, wait_until='domcontentloaded', timeout=30000)
    city_locs = parse_locs(pg.content())
    print(f'Total city locs: {len(city_locs)}')

    # Show first 20 to understand structure
    print('First 20 locs:')
    for l in city_locs[:20]: print(f'  {l}')

    # Count by path depth
    depths = collections.Counter()
    for l in city_locs:
        path = re.sub(r'https?://[^/]+', '', l).rstrip('/')
        depth = path.count('/')
        depths[depth] += 1
    print(f'\nPath depth distribution: {dict(depths)}')

    # Separate state vs city vs locality URLs
    state_urls    = [l for l in city_locs if re.search(r'/location/[a-z0-9\-]+/$', l) or
                     re.search(r'/location/[a-z0-9\-]+/\?', l)]
    # URLs with two path segments after /location/ are city-level
    city_level    = [l for l in city_locs if re.search(r'/location/[a-z0-9\-]+/[a-z0-9\-]+', l)]
    print(f'\nState-level URLs: {len(state_urls)}, city-level: {len(city_level)}')
    print(f'State sample: {state_urls[:3]}')
    print(f'City sample: {city_level[:3]}')

    # ── 3. For a sample of city pages, extract dealer count ───────────────────
    print('\n=== Step 3: Extract dealer count from city pages ===')
    STATES = ['delhi', 'maharashtra', 'uttar-pradesh', 'rajasthan', 'bihar']
    sample_results = {}
    for state in STATES:
        state_url = f'https://dealers.heromotocorp.com/location/{state}/?companyid={HE}'
        resp = pg.goto(state_url, wait_until='networkidle', timeout=30000)
        content = pg.content()
        text = pg.evaluate('() => document.body.innerText')

        # Extract city links from state page
        city_links = re.findall(r'href="(/location/[^"]+)"', content)
        # Count dealers - try to find a number
        count_matches = re.findall(r'(\d+)\s*(?:dealer|outlet|showroom|result)', text, re.I)
        print(f'\n  {state}: status={resp.status}, city_links={len(city_links)}, count_hints={count_matches[:5]}')
        print(f'  Text preview: {text[:300]}')
        if city_links:
            print(f'  First city links: {city_links[:5]}')

    # ── 4. Check parts distributor sitemap structure ──────────────────────────
    print('\n=== Step 4: Parts distributor sitemap ===')
    pg.goto(f'https://partsdistributors.heromotocorp.com/sitemap.xml', wait_until='domcontentloaded', timeout=20000)
    pd_locs = parse_locs(pg.content())
    print(f'Total locs: {len(pd_locs)}')
    print('First 10:')
    for l in pd_locs[:10]: print(f'  {l}')

    # Fetch first batch sitemap for parts distributor
    pd_batches = [l for l in pd_locs if 'bid=' in l and 'bid=cities' not in l]
    print(f'Batch sitemaps: {len(pd_batches)}')
    if pd_batches:
        pg.goto(pd_batches[0], wait_until='domcontentloaded', timeout=15000)
        pd_batch_locs = parse_locs(pg.content())
        print(f'First batch locs: {len(pd_batch_locs)}')
        for l in pd_batch_locs[:5]: print(f'  {l}')

    browser.close()
