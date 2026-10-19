"""Quick inspection of the captured debug HTML to find API patterns."""
import re, json, os, sys

PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
html_path = os.path.join(PROJECT_DIR, "data", "raw", "debug", "re_delhi_service.html")

with open(html_path, encoding="utf-8") as f:
    html = f.read()

print("File size:", len(html), "chars")
print()

# 1. Next.js __NEXT_DATA__
m = re.search(r'id="__NEXT_DATA__"[^>]*>({.*?})</script>', html, re.DOTALL)
if m:
    try:
        data = json.loads(m.group(1))
        print("Found __NEXT_DATA__, top keys:", list(data.keys()))
    except Exception as e:
        print("__NEXT_DATA__ found but JSON parse failed:", e)
else:
    print("No __NEXT_DATA__ found")

# 2. Count-like JSON values
count_vals = re.findall(r'"(?:count|total|serviceCount|dealerCount|totalCount)[^"]*"\s*:\s*(\d+)', html, re.IGNORECASE)
print("Count-like JSON values:", count_vals[:20])

# 3. API base URLs in scripts
api_hits = re.findall(r'https://[a-zA-Z0-9._-]+\.bikewale\.com/[a-zA-Z0-9/_-]{5,60}', html)
unique_apis = sorted(set(api_hits))
print("\nBikeWale API URLs found:")
for u in unique_apis[:20]:
    print(" ", u)

# 4. Any /api/ or /webapi/ patterns
webapi = re.findall(r'["\'](/(?:api|webapi|v\d)[/a-zA-Z0-9_-]{3,60})["\']', html)
print("\n/api/ paths:", sorted(set(webapi))[:20])

# 5. Dealer page URL pattern clues
dealer_urls = re.findall(r'href=["\']([^"\']*dealer[^"\']{3,60})["\']', html, re.IGNORECASE)
print("\nDealer hrefs found:")
for u in dealer_urls[:15]:
    print(" ", u)
