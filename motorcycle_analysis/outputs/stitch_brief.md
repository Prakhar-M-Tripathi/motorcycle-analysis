# UI Design Brief — Indian Motorcycle Network Bottleneck Dashboard
**Prepared for:** Google Stitch (UI ideation)
**Project:** IIM Sirmaur · BMS Batch 2025 · Management Research Project

---

## 1. Project Context

This is a **management research dashboard** built as part of a post-graduate business program at IIM Sirmaur. The research investigates a specific structural problem in the Indian two-wheeler industry:

> **Core question:** Do Indian motorcycle brands have a measurable imbalance between where they sell bikes (showrooms) and where they service them (service centres) — and does that imbalance directly suppress regional sales and create revenue leakage?

The dataset covers **9 motorcycle and electric scooter brands** (Hero MotoCorp, Honda, Bajaj, Royal Enfield, Yamaha, Suzuki, Jawa, Ola Electric, Ather Energy), **778 cities across India**, and **6 geographic zones** (North, South, West, East, Central, Northeast). The data was scraped from BikeWale, India's largest automotive listing platform, and cross-referenced with FADA (Federation of Automobile Dealers Associations) monthly retail sales data.

The central metric is the **Service-to-Showroom Ratio (SC/SW)** — the number of service centres divided by the number of showrooms in a given geography. A ratio below 1.0 means a brand sells more aggressively than it can service, which the research hypothesises leads to customer dissatisfaction, lost repeat purchases, and measurable revenue leakage.

---

## 2. Audience

- **Primary:** The researcher (student) presenting findings to faculty and peer reviewers
- **Secondary:** Industry professionals, brand network planning teams, automotive policy researchers
- **Tone:** Rigorous and data-forward, but visually approachable — not a spreadsheet, not a marketing deck

---

## 3. Design Direction

- **Theme:** Dark, minimal, data-forward. Think Bloomberg Terminal meets a modern SaaS analytics product.
- **Colour palette:** Near-black background (`#111113`), dark charcoal cards (`#18181b`), **green accent** (`#22c55e`) for healthy/positive values, **amber** (`#fbbf24`) for moderate gaps, **red** (`#ef4444`) for bottlenecks. Muted grey text for labels and metadata.
- **Typography:** Clean sans-serif (Segoe UI or Inter). Large numbers for KPIs, small uppercase tracking for section labels.
- **Density:** Medium-high information density — this is a research tool, not a consumer product. Users are expected to read carefully.
- **Layout:** Single scrollable page, divided into clearly numbered sections with a persistent left sidebar navigation for quick jumping.

---

## 4. Page Structure & Section Descriptions

### Header / Hero

A full-width top section establishing context. Contains:
- Project title and institutional byline
- Data provenance line (source, scrape date, brand and city counts)
- A **strip of 5 KPI cards** showing the most critical headline numbers:
  - Total brands analysed
  - Total cities covered
  - National average SC/SW ratio (with a coloured indicator — green if ≥1.0, red if below)
  - Total estimated revenue leakage in Rs. Crore
  - Number of zones classified as bottlenecks (ratio < 0.70)

The KPI strip should feel like a status bar — numbers are large, labels are tiny and uppercase, cards are separated by thin dividers.

---

### Section 01 — Zone-Level Network Health Map

The most visually prominent section. Two panels side by side:

**Left panel — India Choropleth Map**
A map of India where each state is coloured by its zone's average SC/SW ratio. The colour ramp goes from deep red (ratio ~0.5, severe bottleneck) through amber to green (ratio ≥1.0, healthy). Zone boundaries are overlaid as subtle thick lines. State names appear on hover.

This is the emotional centrepiece of the dashboard — it immediately shows that certain parts of India (Northeast, Central) are deeply underserved while others (West, North) are better balanced. The visual should feel like a heat scan of India's motorcycle infrastructure.

**Right panel — Zone Bar Chart**
A horizontal bar chart ranking all 6 zones by their average SC/SW ratio, colour-coded on the same green-amber-red scale. A vertical dotted line at x=1.0 marks parity. Each bar has the ratio value labelled at its end.

> **Interactive:** Clicking a zone on either the map or the bar chart highlights that zone across the entire dashboard — all subsequent charts dim other zones and emphasise the selected one.

---

### Section 02 — Brand × Zone Heatmap

A full-width matrix — brands on the Y-axis (9 rows), zones on the X-axis (6 columns). Each cell shows the SC/SW ratio for that brand in that zone, coloured on the same red-to-green scale. The ratio number is printed inside each cell in white.

This is the most analytically dense visual in the dashboard. It lets a viewer immediately identify:
- Which brands are consistently poor across all zones (entire row is red)
- Which zones are consistently underserved across all brands (entire column is red)
- Specific outlier cells (one brand doing well in one zone but badly elsewhere)

The header row and column should be sticky on scroll if the table is large enough to require it.

> **Interactive:** Clicking any cell opens a drill-down panel showing the individual city-level breakdown for that brand-zone combination — a list of cities, their counts, and individual ratios.

---

### Section 03 — Brand Ratio Rankings

Two panels:

**Left — National Ratio Ranking**
Horizontal bar chart of all 9 brands sorted by their national average SC/SW ratio. Colour-coded green/amber/red. The parity line at 1.0 is marked.

**Right — Absolute Network Size**
Grouped bar chart showing total service centre count vs total showroom count per brand. This provides the raw scale context — a brand with 5,000 showrooms and a ratio of 0.9 is a very different problem from a brand with 50 showrooms and a ratio of 0.9.

---

### Section 04 — Revenue Leakage Estimate

Two panels:

**Left — Leakage by Brand**
Horizontal bar chart showing estimated revenue lost per brand due to service gaps, in Rs. Crore. Bars are red. Values are labelled. A brief methodology note below the chart explains the calculation (ASP × estimated diverted units).

**Right — Leakage by Zone**
Vertical bar chart showing the same metric broken down geographically. Each bar is coloured by zone. An insight callout box below highlights the key finding — that peripheral zones have disproportionately high per-city leakage despite lower absolute volumes.

---

### Section 05 — Core Hypothesis: Network Gap vs Sales Correlation

A single wide scatter plot — the most statistically significant chart in the dashboard.

- X-axis: SC/SW Ratio (lower = more service-deficient)
- Y-axis: Regional Sales Index from FADA data (normalised to 100 = national average)
- Each dot = one brand in one zone (54 data points total)
- Dots are coloured by brand, with a legend
- A trend line (dashed green) is overlaid
- The Pearson r and p-value are displayed in a small annotation box in the corner

If the trend line slopes upward (higher ratio → higher sales), the central hypothesis is confirmed. This is the chart the researcher will spend the most time explaining.

> **Interactive:** Hovering over any dot shows a tooltip with the brand name, zone, exact ratio, sales index, and whether it's classified as healthy, mild gap, or bottleneck.

---

### Section 06 — City Tier Split

Two panels examining whether the network gap problem is worse in smaller cities.

**Left — Ratio by City Tier**
Three bars: Tier 1 (metro cities, population > 4M), Tier 2 (large cities), Tier 3 (smaller towns). The expected finding is that Tier 3 cities have the worst ratios — brands open showrooms to capture aspirational demand but don't follow with service infrastructure.

**Right — Absolute SC vs SW Count by Tier**
Grouped bars showing total service centres vs total showrooms across all brands per tier. Visually illustrates the growing gap as city size decreases.

An insight callout box states the key finding in plain language.

---

### Section 07 — Interactive Radius Map

The most technically novel section. A full-width interactive map of India showing city-level data points.

**Default state:**
Every city in the dataset is plotted as a dot. Dot size = total network presence (SC + SW count). Dot colour = SC/SW ratio (red/amber/green scale). Cities with zero service centres but non-zero showrooms are marked with a distinct icon (open circle or hollow dot).

**On click:**
When a user clicks anywhere on the map, a radius circle (default 75 km, adjustable to 50 km via a toggle) is drawn around that point. A panel slides in from the right side showing:
- All cities within that radius
- For each of the 9 brands: their service centre count and showroom count within the radius
- The combined SC/SW ratio for that radius
- A mini bar chart comparing brands within the radius
- A severity label (Healthy / Mild Gap / Bottleneck) for the area

This feature is intended to simulate what a brand network planner would want to know: "if I'm standing in this part of India, which brands are well-served here and which are not?"

> **Interactive elements on this map:**
> - Click anywhere → draw radius, open brand stats panel
> - Radius slider: toggle between 50 km and 75 km
> - Brand filter: toggle individual brands on/off
> - Layer toggle: show only service centres, only showrooms, or both
> - Hover over a city dot → tooltip showing city name, zone, and per-brand counts

---

### Section 08 — Neglect Score & Expansion Priority

The actionable output section — intended to be readable as a priority brief.

**Left — Neglect Score Leaderboard**
A horizontal bar chart of the top 15 brand-zone combinations ranked by a composite neglect score (0–100). Score combines: SC/SW deficit magnitude, city tier weights, and zone isolation penalty. Higher = more urgently underserved. Red bars for score > 85, amber for 70–85, green for below 70.

**Right — Expansion Priority Table**
A clean data table (not a chart) listing the top 15 brand-zone combinations with columns: Brand, Zone, Current SC count, Current SW count, Ratio, SC centres needed to reach parity, and Priority rank. This table is the most "boardroom-ready" element of the dashboard — a manager could print it and hand it to a network planning team.

> **Interactive:** Clicking a row in the expansion table highlights that brand-zone combination on the heatmap in Section 02 and zooms the map in Section 07 to that zone.

---

## 5. Persistent UI Elements

**Left Sidebar Navigation**
A thin vertical strip (≈50px wide) on the left edge containing section numbers/labels rotated vertically. Clicking jumps to that section. The active section is highlighted with the green accent.

**Scroll Progress Indicator**
A thin line at the very top of the page (below the fixed nav bar, if any) showing scroll progress through the document — a subtle signal to the user how far through the analysis they are.

---

## 6. Tone Summary for the Designer

Imagine this dashboard is being projected in a seminar room at a business school — it needs to be legible from the back row, visually credible to an academic audience, and dense enough that a domain expert finds it genuinely informative rather than decorative. It should feel like a serious research instrument, not a product landing page. The dark theme is a deliberate choice — it reduces visual fatigue during a long presentation and makes the colour-coded data (red/amber/green) pop without feeling garish.

The interactivity is not decoration — every interactive element either lets the user drill deeper into the data or narrows the geographic/brand focus to answer a specific question. The map radius tool in particular is the "wow" moment — the feature that makes the audience lean forward.

---

*Dataset: BikeWale (scraped June 2026) + FADA monthly retail data · 9 brands · 778 cities · 6 zones · 6,944 records*
