"""Find the exact HTML element containing the service center count."""
import re, os

PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
html_path   = os.path.join(PROJECT_DIR, "data", "raw", "debug", "intercept_service_delhi.html")

with open(html_path, encoding="utf-8") as f:
    html = f.read()

# Find every occurrence of '25' in the HTML and show 300 chars around it
print("=== Occurrences of '25' (candidate count) ===\n")
for i, m in enumerate(re.finditer(r'\b25\b', html)):
    snip = html[max(0, m.start()-200):m.end()+200]
    # Skip if it's clearly a CSS/JS number
    if any(x in snip for x in ["px", "em", "rem", "opacity", "rgba", "setTimeout", "padding", "margin"]):
        continue
    print(f"[Match {i+1} at pos {m.start()}]")
    print(snip)
    print()
    if i > 10:
        break

# Also look for class names around any digit-containing spans/divs
print("\n=== All elements with class containing 'count', 'total', 'result' ===\n")
for m in re.finditer(r'class="[^"]*(?:count|total|result|dealer|service-list)[^"]*"[^>]*>([^<]{1,50})', html, re.IGNORECASE):
    print(f"  class snippet: ...{m.group(0)[:120]}...")

# Find title tag
title = re.search(r'<title>(.*?)</title>', html)
print("\n=== Page title ===")
print(title.group(1) if title else "not found")

# Look for the breadcrumb or heading area
heading_area = re.search(r'<h1[^>]*>(.*?)</h1>', html, re.DOTALL)
print("\n=== H1 content ===")
print(heading_area.group(0)[:300] if heading_area else "not found")
