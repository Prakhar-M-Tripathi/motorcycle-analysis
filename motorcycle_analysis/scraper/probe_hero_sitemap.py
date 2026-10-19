"""
Check Hero dealer sitemap for all dealer URLs + individual page JSON-LD.
"""
import sys, json, re, urllib.request, ssl, gzip, io
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

def get(url):
    req = urllib.request.Request(url, headers={'User-Agent':'Mozilla/5.0 Chrome/120', 'Accept-Encoding':'gzip'})
    resp = urllib.request.urlopen(req, timeout=20, context=ctx)
    raw = resp.read()
    try:
        raw = gzip.decompress(raw)
    except: pass
    return raw.decode('utf-8', 'replace')

# 1. Robots.txt
print('=== robots.txt ===')
for host in ['https://dealers.heromotocorp.com', 'https://www.heromotocorp.com']:
    try:
        data = get(f'{host}/robots.txt')
        print(f'{host}: {data[:1000]}')
    except Exception as e:
        print(f'{host}: {e}')

# 2. Sitemap
print('\n=== Sitemaps ===')
for url in [
    'https://dealers.heromotocorp.com/sitemap.xml',
    'https://dealers.heromotocorp.com/sitemap_index.xml',
    'https://dealers.heromotocorp.com/sitemap-0.xml',
    'https://www.heromotocorp.com/sitemap.xml',
]:
    try:
        data = get(url)
        print(f'\n{url}: len={len(data)}')
        # Show loc URLs
        locs = re.findall(r'<loc>(.*?)</loc>', data)
        print(f'  Locs: {len(locs)}')
        for l in locs[:10]: print(f'    {l}')
    except Exception as e:
        print(f'{url}: {e}')

# 3. Individual dealer page - look for JSON-LD and dealer type
print('\n=== Individual dealer page structure ===')
url = 'https://dealers.heromotocorp.com/locator/kanpur/govind-nagar/swami-automobiles-hero-motocorp-in-govind-nagar-kanpur--2DM25Z/home'
data = get(url)
print(f'Page size: {len(data):,}')

# JSON-LD
print('\nJSON-LD blocks:')
for m in re.finditer(r'<script type="application/ld\+json">(.*?)</script>', data, re.S):
    try:
        obj = json.loads(m.group(1))
        print(f'  @type={obj.get("@type")}, keys={list(obj.keys())}')
        for key in ['name','address','geo','telephone','openingHoursSpecification','@type','additionalType','priceRange','hasMap','sameAs']:
            if key in obj:
                v = obj[key]
                print(f'    {key}: {str(v)[:200]}')
    except: pass

# Look for type indicators (3S/2S/service) in page
type_hits = re.findall(r'(?:3S|2S|service.?only|showroom|authorized.?service|ASC)[^\n<]{0,80}', data, re.I)
print(f'\nDealer type mentions: {len(type_hits)}')
for h in type_hits[:5]: print(f'  {h[:120]}')

# Look for other dealer pages linked on this page (related dealers)
related = re.findall(r'href="(https://dealers\.heromotocorp\.com/locator/[^"]+/home)"', data)
print(f'\nRelated dealer links: {len(related)}')
for r in related[:5]: print(f'  {r}')

# Look for any data about services offered (to categorize as service center or showroom)
services = re.findall(r'(?:service|repair|showroom|spare|parts|sales)[^<\n]{0,100}', data, re.I)
print(f'\nService mentions (first 5): {len(services)}')
for s in services[:5]: print(f'  {s[:100]}')
