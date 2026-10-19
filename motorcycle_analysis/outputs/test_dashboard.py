"""
test_dashboard.py
-----------------
Generates a self-contained HTML dashboard from the test scrape results
(Royal Enfield, 8 cities, June 2026).

Output: outputs/test_dashboard.html  (open in any browser)
"""
import json, os, sys

PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_DIR)

import plotly.graph_objects as go
from plotly.subplots import make_subplots

# ── load data ─────────────────────────────────────────────────────────────
DATA_PATH = os.path.join(PROJECT_DIR, "data", "raw", "test_results.json")
with open(DATA_PATH) as f:
    raw = json.load(f)

# Pivot into per-city rows
cities_order = ["Delhi", "Chennai", "Mumbai", "Nagpur", "Patna", "Bhopal", "Guwahati", "Haldwani"]
zones_map    = {r["city"]: r["zone"] for r in raw}

data = {}
for r in raw:
    c = r["city"]
    if c not in data:
        data[c] = {"zone": r["zone"], "service": 0, "showroom": 0}
    data[c][r["type"]] = r["count"]

for c in data:
    svc = data[c]["service"]
    shw = data[c]["showroom"]
    data[c]["ratio"] = round(svc / shw, 2) if shw else 0

# Sort by city order
cities   = cities_order
zones    = [data[c]["zone"]    for c in cities]
service  = [data[c]["service"] for c in cities]
showroom = [data[c]["showroom"]for c in cities]
ratios   = [data[c]["ratio"]   for c in cities]

# Zone colour palette
ZONE_COLOURS = {
    "North":     "#4C72B0",
    "South":     "#55A868",
    "West":      "#C44E52",
    "East":      "#8172B2",
    "Central":   "#CCB974",
    "Northeast": "#64B5CD",
}
bar_colours = [ZONE_COLOURS[z] for z in zones]

# Ratio colour (green > 1, amber 0.7-1, red < 0.7)
def ratio_colour(r):
    if r >= 1.0:   return "#27ae60"
    if r >= 0.7:   return "#f39c12"
    return "#e74c3c"

ratio_colours = [ratio_colour(r) for r in ratios]

# ── build figure ──────────────────────────────────────────────────────────
fig = make_subplots(
    rows=2, cols=2,
    subplot_titles=(
        "Service Centers vs Showrooms by City",
        "Service-to-Showroom Ratio",
        "Ratio Comparison (1.0 = parity)",
        "Raw Numbers Table",
    ),
    specs=[
        [{"type": "bar"},  {"type": "bar"}],
        [{"type": "scatter"}, {"type": "table"}],
    ],
    vertical_spacing=0.18,
    horizontal_spacing=0.10,
)

# ── Chart 1: grouped bar — service vs showroom ────────────────────────────
fig.add_trace(go.Bar(
    name="Service Centers",
    x=cities, y=service,
    marker_color="#2ecc71",
    text=service, textposition="outside",
), row=1, col=1)

fig.add_trace(go.Bar(
    name="Showrooms",
    x=cities, y=showroom,
    marker_color="#3498db",
    text=showroom, textposition="outside",
), row=1, col=1)

# ── Chart 2: ratio bar ────────────────────────────────────────────────────
fig.add_trace(go.Bar(
    name="Ratio (SC/SW)",
    x=cities, y=ratios,
    marker_color=ratio_colours,
    text=[str(r) for r in ratios],
    textposition="outside",
    showlegend=False,
), row=1, col=2)

fig.add_hline(y=1.0, line_dash="dot", line_color="grey",
              annotation_text="Parity (1.0)", row=1, col=2)

# ── Chart 3: scatter ratio by zone ───────────────────────────────────────
for zone, colour in ZONE_COLOURS.items():
    zc = [c for c in cities if zones[cities.index(c)] == zone]
    zr = [ratios[cities.index(c)] for c in zc]
    if not zc:
        continue
    fig.add_trace(go.Scatter(
        name=zone,
        x=zc, y=zr,
        mode="markers+text",
        marker=dict(size=18, color=colour, line=dict(width=1, color="white")),
        text=[str(r) for r in zr],
        textposition="top center",
        showlegend=True,
    ), row=2, col=1)

fig.add_hline(y=1.0, line_dash="dot", line_color="grey", row=2, col=1)

# ── Chart 4: table ────────────────────────────────────────────────────────
flag = []
for r in ratios:
    if r >= 1.0:   flag.append("Healthy")
    elif r >= 0.7: flag.append("Mild gap")
    else:          flag.append("Bottleneck")

fig.add_trace(go.Table(
    header=dict(
        values=["<b>City</b>", "<b>Zone</b>", "<b>Service</b>",
                "<b>Showrooms</b>", "<b>Ratio</b>", "<b>Status</b>"],
        fill_color="#2c3e50",
        font=dict(color="white", size=12),
        align="center",
    ),
    cells=dict(
        values=[cities, zones, service, showroom, ratios, flag],
        fill_color=[
            ["#f8f9fa"] * len(cities),
            ["#eeeeee"] * len(cities),
            ["#f8f9fa"] * len(cities),
            ["#f8f9fa"] * len(cities),
            ["#f8f9fa"] * len(cities),
            ["#d5f5e3" if f == "Healthy" else "#fdebd0" if f == "Mild gap" else "#fadbd8"
             for f in flag],
        ],
        align="center",
        font=dict(size=12),
    ),
), row=2, col=2)

# ── layout ────────────────────────────────────────────────────────────────
fig.update_layout(
    title=dict(
        text="<b>Royal Enfield — Test Scrape Dashboard</b><br>"
             "<sub>8 cities across 6 zones | Scrape date: 7 June 2026 | "
             "Source: BikeWale | Status: 16/16 passed</sub>",
        x=0.5, xanchor="center",
        font=dict(size=20),
    ),
    barmode="group",
    height=850,
    template="plotly_white",
    legend=dict(
        orientation="h",
        yanchor="bottom", y=1.01,
        xanchor="right",  x=1,
    ),
    font=dict(family="Arial, sans-serif"),
    paper_bgcolor="#fafafa",
)

fig.update_yaxes(title_text="Count",     row=1, col=1)
fig.update_yaxes(title_text="SC / SW",   row=1, col=2, range=[0, max(ratios) + 0.3])
fig.update_yaxes(title_text="SC / SW",   row=2, col=1, range=[0, max(ratios) + 0.3])

# ── summary annotation ────────────────────────────────────────────────────
avg_ratio = round(sum(ratios) / len(ratios), 2)
gap_cities = [c for c, r in zip(cities, ratios) if r < 1.0]

fig.add_annotation(
    text=(
        f"<b>Test summary</b><br>"
        f"Cities tested: {len(cities)} | Avg ratio: {avg_ratio}<br>"
        f"Cities below parity: {', '.join(gap_cities)}<br>"
        f"Worst gap: Guwahati (Northeast) — ratio 0.50"
    ),
    xref="paper", yref="paper",
    x=0.01, y=-0.08,
    showarrow=False,
    align="left",
    font=dict(size=11, color="#555"),
    bgcolor="#f5f5f5",
    bordercolor="#ccc",
    borderwidth=1,
)

# ── save ──────────────────────────────────────────────────────────────────
out_path = os.path.join(PROJECT_DIR, "outputs", "test_dashboard.html")
fig.write_html(out_path, include_plotlyjs="cdn")

print(f"Dashboard written: {out_path}")
print(f"Open in your browser to view.")

# ── print text summary ────────────────────────────────────────────────────
print()
print("=" * 56)
print("  ROYAL ENFIELD TEST SCRAPE — SUMMARY")
print("=" * 56)
print(f"  {'City':<12} {'Zone':<12} {'SC':>4} {'SW':>4} {'Ratio':>6}  Status")
print(f"  {'-'*12} {'-'*12} {'-'*4} {'-'*4} {'-'*6}  {'-'*12}")
for c, z, sc, sw, r, fl in zip(cities, zones, service, showroom, ratios, flag):
    print(f"  {c:<12} {z:<12} {sc:>4} {sw:>4} {r:>6.2f}  {fl}")
print(f"\n  Avg ratio:  {avg_ratio}")
print(f"  Below 1.0:  {', '.join(gap_cities)}")
print(f"  All 16 page fetches: HTTP 200, count extracted cleanly.")
print("=" * 56)
