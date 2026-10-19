"""Probe heromotocorp.com dealer locator for API endpoints."""
import urllib.request, ssl, sys, re, json
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

url = 'https://www.heromotocorp.com/en-in/reach-us/find-hero-bike-dealers.html'
req = urllib.request.Request(url, headers={
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120'
})
resp = urllib.request.urlopen(req, timeout=15, context=ctx)
html = resp.read().decode('utf-8', 'replace')
print('Page length:', len(html))

# Look for API hints
found = set()
patterns = [
    r'https?://[^\s"\'<>]{0,200}(?:dealer|locator|api|search|json)[^\s"\'<>]{0,100}',
    r'/[a-z0-9_/-]{5,120}(?:dealer|api|search|locator|cities|states)[a-z0-9_/-]{0,60}',
    r'fetch\s*\(\s*["\']([^"\']+)["\']',
    r'axios\.[a-z]+\(\s*["\']([^"\']+)["\']',
    r'\.get\(\s*["\']([^"\']+)["\']',
]
for p in patterns:
    for m in re.findall(p, html, re.I):
        if isinstance(m, tuple): m = m[0]
        if m not in found and len(m) > 5:
            found.add(m)
            print(' HINT:', m[:160])

print()
# Check for embedded JSON data
if 'states' in html.lower(): print('Has "states" keyword')
if 'cities' in html.lower(): print('Has "cities" keyword')
if 'latitude' in html.lower(): print('Has "latitude" keyword')
if 'lng' in html.lower(): print('Has "lng" keyword')

print()
print('--- FIRST 4000 chars ---')
print(html[:4000])
