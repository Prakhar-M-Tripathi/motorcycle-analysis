**MASTER REFERENCE DOCUMENT**

**Indian Motorcycle Brand**

**Network Bottleneck Analysis**

Project Scope · Technology Stack · Implementation · Formulas · Spatial Analysis

IIM Sirmaur | BMS Batch 2025 | Management Research Project

|  |
| --- |
| **How to use this document**  This is the single source of truth for the entire project. It covers everything from data collection to visualisation in one place. For Claude Code sessions: paste the relevant section heading into your prompt as context. For additions: append to the relevant chapter and update the version note on this page. For cross-referencing: every formula section states which other analyses it depends on. |

| **Document history** | **Detail** |
| --- | --- |
| Version | 1.0 — Initial master document |
| Chapters | 5 (Scope, Data, Stack, Formulas, Spatial Analysis) |
| Brands covered | 11 brands including Jawa |
| Analyses covered | 12 analytical outputs + spatial coverage layer |
| Last updated | June 2026 |

# **Table of Contents**

|  |
| --- |
| **CHAPTER 1**  **Project Scope & Overview** |

# **1.1 Project Question and Hypothesis**

This project investigates whether Indian motorcycle brands have regional imbalances between their showroom (sales) networks and their service center networks — and whether those imbalances correlate with lower regional sales volume and measurable revenue leakage.

|  |
| --- |
| **Central hypothesis**  Zones with fewer service centers relative to showrooms create a customer experience bottleneck that suppresses repeat purchases, reduces brand loyalty, and results in quantifiable lost revenue. Service center density and regional sales volume are positively correlated. |

# **1.2 Brands Covered**

| **#** | **Brand** | **Segment** | **EV Layer** | **Notes** |
| --- | --- | --- | --- | --- |
| 1 | Hero MotoCorp | Commuter / mass market | No | Market leader ~28% share |
| 2 | Honda (HMSI) | Commuter / scooter | No | Second ~25% share |
| 3 | Bajaj Auto | Commuter / performance | Partial (Chetak) | Chetak EV tracked separately |
| 4 | TVS Motor | Commuter / performance | Partial (iQube) | iQube EV tracked separately |
| 5 | Royal Enfield | Mid-size / premium | No | Fastest growing in segment |
| 6 | Yamaha | Performance / scooter | No |  |
| 7 | Suzuki | Commuter / scooter | No |  |
| 8 | KTM | Performance / premium | No | Niche; may have zero coverage in NE |
| 9 | Ola Electric | Electric scooter | Yes (primary) | Own-brand service only |
| 10 | Ather Energy | Electric scooter | Yes (primary) | Own-brand service only |
| 11 | Jawa | Mid-size retro / heritage | No | Classic Legends / Mahindra subsidiary; relaunched 2018 |

# **1.3 Geographic Zones**

| **Zone** | **States Included** | **Notable Characteristic** |
| --- | --- | --- |
| North | Delhi, UP, Haryana, Punjab, Rajasthan, HP, Uttarakhand, J&K | Largest zone by volume; Hero stronghold |
| South | Tamil Nadu, Karnataka, Kerala, Andhra Pradesh, Telangana | TVS and Honda dominant; high service density |
| West | Maharashtra, Gujarat, Goa, MP, Chhattisgarh | Bajaj stronghold; urban concentration |
| East | West Bengal, Odisha, Jharkhand, Bihar | Underserved relative to population |
| Northeast | Assam, Meghalaya, Manipur, Mizoram, Tripura, Nagaland, Arunachal Pradesh, Sikkim | Most isolated; expected worst service ratios |
| Central | Madhya Pradesh (overlap), Chhattisgarh (overlap) | Often merged with West in brand reporting |

|  |
| --- |
| **Critical rule — zone mapping**  The state-to-zone mapping is defined exactly once in constants.py and imported by every script. Never define or hardcode zone assignments inside individual analysis scripts. One file, used everywhere. This is the single most important consistency rule in the project. |

# **1.4 Complete List of Analytical Outputs**

| **#** | **Analysis** | **Type** | **Chapter** |
| --- | --- | --- | --- |
| 1 | Service-to-showroom ratio | Core metric | Ch. 4 |
| 2 | Brand baseline ratio | Normalisation | Ch. 4 |
| 3 | Deviation from brand baseline | Comparative metric | Ch. 4 |
| 4 | Bottleneck severity classification | Classification | Ch. 4 |
| 5 | Revenue leakage estimate | Financial metric | Ch. 4 |
| 6 | Pearson correlation | Statistical test | Ch. 4 |
| 7 | Expansion priority index | Prescriptive | Ch. 4 |
| 8 | HHI clustering analysis | Distribution | Ch. 4 |
| 9 | Brand maturity vs network balance | Structural risk | Ch. 4 |
| 10 | Northeast / hill-state neglect score | Regional equity | Ch. 4 |
| 11 | Competitor advantage map | Competitive | Ch. 4 |
| 12 | Rural vs urban bottleneck split | Tier analysis | Ch. 4 |
| 13 | Radius-based spatial coverage analysis | Spatial / granular | Ch. 5 |

|  |
| --- |
| **CHAPTER 2**  **Data Sources** |

# **2.1 Primary Source — BikeWale Scrape**

BikeWale (bikewale.com) is the primary data source for showroom and service center counts. It aggregates dealer and service data for all major brands across Indian cities and is the most comprehensive publicly accessible source for this purpose.

| **Data point** | **BikeWale URL pattern** | **Update frequency** |
| --- | --- | --- |
| Showroom count per city | bikewale.com/dealer-showrooms/{brand}/{city}/ | Weekly |
| Service center count per city | bikewale.com/service-centers/{brand}/{city}/ | Weekly |
| Service center addresses | Extracted from listing page | As updated by brand |
| City / pincode | Listed in each record | Static |

# **2.2 Brand Official Locators (Cross-validation)**

| **Brand** | **Official locator URL** |
| --- | --- |
| Royal Enfield | dealers.royalenfield.com/{state} |
| Hero MotoCorp | heromotocorp.com/en-in/locate-us.html |
| Bajaj Auto | bajajauto.com/locate-dealer |
| TVS Motor | tvsmotor.com/dealer-locator |
| Honda (HMSI) | honda2wheelersindia.com/service-network |
| Ola Electric | olaelectric.com/service-centres |
| Ather Energy | atherenergy.com/service-center |
| Jawa | jawamotorcycles.com/dealer-locator |

# **2.3 FADA State-wise Retail Data**

The Federation of Automobile Dealers Associations (FADA) publishes monthly state-wise retail registration data for all two-wheeler brands. This is the standard proxy for regional revenue in the absence of brand-disclosed zone-level financials.

|  |
| --- |
| **Why FADA instead of annual reports?**  No Indian two-wheeler brand publicly discloses zone-wise or state-wise revenue breakdowns. FADA retail data (end-customer registrations, not wholesale dispatches) is the accepted industry-standard proxy used by analysts, investment firms, and researchers. Source: fada.in |

|  |
| --- |
| **Caveat**  Jawa data: FADA sometimes lists Jawa under 'Others' or 'Classic Legends' rather than as a standalone brand. Where this occurs, supplement with SIAM (Society of Indian Automobile Manufacturers) monthly data and document the disaggregation method used. |

# **2.4 Supplementary Data Sources**

| **Data** | **Source** | **Used in Analysis** |
| --- | --- | --- |
| Average Selling Price (ASP) per brand | Brand annual reports: Revenue ÷ Units sold. For Jawa (private): weighted average of model prices from official price list. | Analysis 5 (revenue leakage) |
| India Census city population | censusindia.gov.in — free download. Use 2011 data; supplement with 2021 projections where available. | Analysis 10, 12, Ch. 5 spatial |
| India state / district shapefile | gadm.org or data.gov.in — free, GeoPandas-compatible. | All map visualisations |
| India Pincode Database | data.gov.in — CSV of all pincodes with lat/long. Used as geocoding fallback. | Chapter 5 spatial analysis |
| Historical sales & network growth data | Brand annual reports, investor presentations, FADA historical archives. | Analysis 9 (maturity/balance) |

# **2.5 SQLite Database Schema**

All collected and calculated data is stored in a single SQLite file (motorcycle\_analysis.db). The schema is defined once and shared across all scripts.

| **Table** | **Key columns** | **Source / purpose** |
| --- | --- | --- |
| dealers | id, brand, city, state, zone, type (showroom/service), count, lat, lon, scrape\_date | BikeWale scrape — core data table |
| fada\_sales | id, brand, state, zone, year, month, units\_sold | FADA monthly retail data |
| brand\_asp | brand, year, avg\_selling\_price\_inr | Calculated from annual reports |
| city\_tier | city, state, population, tier (1/2/3) | Census population data |
| pincode\_coords | pincode, lat, lon, city, state | India Pincode DB — geocoding fallback |
| analysis\_output | brand, zone, showrooms, service\_centers, ratio, deviation\_pct, severity, est\_revenue\_lost | Final calculated metrics — read by visualisations |

|  |
| --- |
| **CHAPTER 3**  **Technology Stack & Implementation** |

# **3.1 Stack Overview**

| **Phase** | **Task** | **Primary tool** | **Supporting tools** |
| --- | --- | --- | --- |
| 1 — Collection | Scrape showroom & service center data | Python + Playwright | BeautifulSoup, Requests, geopy |
| 2 — Storage | Store and query structured data | SQLite | Python sqlite3 module |
| 3 — Analysis | Clean, aggregate, calculate all metrics | Pandas | NumPy, SciPy, GeoPandas, shapely |
| 4 — Visualisation | Charts, maps, heatmaps | Plotly | GeoPandas, Matplotlib |
| Orchestration | Write, run, debug all scripts | Claude Code | Terminal / bash |

# **3.2 Phase 1 — Data Collection (Playwright)**

Playwright controls a real browser (Chrome or Firefox) to scrape JavaScript-rendered pages. The scraper iterates over all brand-city combinations, reads counts and addresses from BikeWale, then geocodes every location to lat/long for the spatial analysis.

* **Iterates:** Over all 11 brands and all major Indian cities (state capitals + top 50 cities by population).
* **Scrapes:** Showroom count, service center count, addresses, pincodes from BikeWale.
* **Cross-checks:** Against brand official locators for a random 10% sample.
* **Geocodes:** Every city/pincode to lat/lon using geopy (Nominatim). Results cached — never re-geocode.
* **Saves:** All records to SQLite dealers table with scrape\_date stamped.

|  |
| --- |
| **Caveat**  Nominatim rate limit is 1 request/second. With ~500 unique cities, geocoding takes ~10 minutes. Always cache to CSV after first run. Playwright scraper should include 2-3 second delays between requests. Both BikeWale and brand locators are public-facing — no authentication required. |

# **3.3 Phase 2 — Storage (SQLite)**

SQLite is a single-file database — no server setup required. Python's built-in sqlite3 module handles all read/write operations. The database lives at db/motorcycle\_analysis.db in the project folder.

# **3.4 Phase 3 — Analysis (Pandas + SciPy)**

| **Script** | **Analyses it runs** | **Key inputs** |
| --- | --- | --- |
| ratio\_calculator.py | 1, 2, 3, 4 | dealers table |
| revenue\_leakage.py | 5 | dealers + fada\_sales + brand\_asp |
| correlation.py | 6 | analysis\_output + fada\_sales |
| expansion\_index.py | 7 | analysis\_output + fada\_sales |
| clustering.py | 8 | dealers (city level, not aggregated) |
| maturity\_balance.py | 9 | fada\_sales (multi-year) + brand disclosures |
| neglect\_score.py | 10 | dealers (state level) + city\_tier |
| competitor\_map.py | 11 | analysis\_output |
| tier\_split.py | 12 | dealers + city\_tier |
| spatial\_analysis.py | 13 | dealers (with lat/lon) + constants.py radii |

# **3.5 Phase 4 — Visualisation (Plotly + GeoPandas)**

| **Output** | **Chart type** | **Tool** | **What it shows** |
| --- | --- | --- | --- |
| Bottleneck map | India choropleth (state) | GeoPandas + Matplotlib | Severity colour per state per brand |
| Brand × zone heatmap | Heatmap grid | Plotly | All brands vs all zones simultaneously |
| Revenue leakage chart | Grouped bar chart | Plotly | Estimated revenue lost per brand per zone |
| Correlation scatter | Scatter + regression line | Plotly | Service ratio vs units sold |
| Expansion priority | Horizontal bar chart | Plotly | Top zones to prioritise per brand |
| Clustering visualisation | Bubble map | GeoPandas | City-level service center concentration |
| Tier split chart | Stacked bar chart | Plotly | Bottleneck distribution by city tier |
| EV comparison | Side-by-side choropleth | GeoPandas | EV vs legacy brand service coverage |
| Coverage gap map | District choropleth | GeoPandas | Which districts are outside service radius (Ch. 5) |

# **3.6 Installation Checklist**

| **Package** | **Purpose** | **Install command** |
| --- | --- | --- |
| playwright | Browser automation for scraping | pip install playwright |
| pandas | Data manipulation and analysis | pip install pandas |
| numpy | Numerical operations | pip install numpy |
| scipy | Statistical tests (Pearson r) + distance matrix | pip install scipy |
| geopandas | Geographic data and map rendering | pip install geopandas |
| plotly | Interactive charts | pip install plotly |
| matplotlib | Static map rendering | pip install matplotlib |
| geopy | Geocode city names/pincodes to lat/lon | pip install geopy |
| shapely | Point-in-polygon and spatial operations | pip install shapely |
| requests | HTTP requests for official locators | pip install requests |
| beautifulsoup4 | HTML parsing fallback | pip install beautifulsoup4 |
| rapidfuzz | Fuzzy city name matching for data joins | pip install rapidfuzz |
| openpyxl | Read FADA Excel files | pip install openpyxl |
| sqlite3 | Database (built into Python — no install) | — built in — |

# **3.7 Project Folder Structure**

motorcycle\_analysis/

├── constants.py # Zone map, radii, tier thresholds, brand list, ASP

├── scraper/ # Playwright scraping scripts

│ ├── bikewale\_scraper.py

│ └── geocoder.py

├── data/

│ ├── raw/ # Raw CSVs from scraper

│ ├── fada/ # FADA monthly retail data

│ ├── supplementary/ # ASP, Census city tiers, shapefiles

│ └── pincode\_db/ # India Pincode Database CSV

├── db/

│ └── motorcycle\_analysis.db

├── analysis/ # One script per analysis (see 3.4)

├── spatial/ # spatial\_analysis.py and haversine utils

├── visualisations/ # Plotly + GeoPandas output scripts

└── outputs/ # Final charts, maps, exported PNGs

# **3.8 Implementation Timeline**

| **Week** | **Phase** | **Deliverable** |
| --- | --- | --- |
| Week 1 | Setup + scraping | Python env, Playwright scraper, raw CSVs, geocoding |
| Week 1-2 | Data validation + FADA ingestion | Cross-check vs 3 brand locators; parse FADA into SQLite |
| Week 2 | Core analysis (Analyses 1-4) | Ratios, baselines, deviations, severity scores |
| Week 2-3 | Financial + statistical (5-7) | Revenue leakage, Pearson correlation, expansion index |
| Week 3 | Advanced analysis (8-12) | HHI clustering, maturity balance, neglect, tier split |
| Week 3-4 | Spatial analysis (Analysis 13) | Haversine distances, CGR per district, coverage gap maps |
| Week 4 | Visualisations + write-up | All 9 chart outputs, findings document, presentation deck |

# **3.9 Known Risks and Mitigations**

| **Risk** | **Likelihood** | **Impact** | **Mitigation** |
| --- | --- | --- | --- |
| BikeWale changes page structure | Low | Scraper breaks | Version-pin scraper; validate weekly |
| FADA PDFs inconsistently formatted | Medium | Manual parsing needed | Claude Code handles PDF text extraction |
| City names inconsistent across sources | High | Merge errors in analysis | Fuzzy matching via rapidfuzz (threshold 85%) |
| Small sample in Northeast zone | High | Low statistical confidence | Flag as observational; report correlation with caution |
| Brand locators block scraping | Medium | Missing data for some brands | Use BikeWale as primary; flag gaps explicitly |
| ASP approximation introduces error | Medium | Revenue estimate imprecise | Report as range, not single figure |
| Jawa listed as 'Others' in FADA | Medium | Sales data missing | Supplement with SIAM data; document disaggregation method |
| Nominatim geocoding ambiguity | Medium | Wrong coordinates for some cities | Spot-check 5% of coordinates; use pincode DB as fallback |

|  |
| --- |
| **CHAPTER 4**  **Formulas, Mathematics & Implementation** |

Every analysis in this chapter follows the same three-part structure: Plain English explanation → Technical formula → Data consistency check and caveats. Variable notation: b = brand, z = zone, i = individual showroom, j = individual service center.

# **Analysis 1: Service-to-Showroom Ratio**

## **Plain English**

For every brand in every zone, divide the number of service centers by the number of showrooms. A ratio of 1.0 means one service center per showroom (parity). A ratio of 0.3 means 3 service centers for every 10 showrooms. This is the foundational metric — every other analysis builds on it.

## **Formula**

|  |
| --- |
| **Service-to-showroom ratio**  **R(b,z) = SC(b,z) / SW(b,z)** |

| **Variable** | **Meaning** | **Source** |
| --- | --- | --- |
| R(b,z) | Ratio for brand b in zone z | Calculated |
| SC(b,z) | Service center count | BikeWale scrape |
| SW(b,z) | Showroom count | BikeWale scrape |

df['ratio'] = df['service\_centers'] / df['showrooms']

|  |
| --- |
| **Data Consistency Check**  Both SC(b,z) and SW(b,z) come from the same BikeWale scrape on the same date, aggregated using the same zone mapping from constants.py. |

|  |
| --- |
| **Caveat**  If SW(b,z) = 0 (brand not present in that zone), ratio is undefined. Filter out these records before analysis. Most common for KTM and Jawa in Northeast. |

# **Analysis 2: Brand Baseline Ratio**

## **Plain English**

Each brand has a different natural ratio shaped by its history and strategy. The baseline is the brand's own national average ratio across all zones it operates in. This allows fair zone-level comparison within a brand rather than comparing Hero's ratio to Royal Enfield's.

## **Formula**

|  |
| --- |
| **Brand baseline (national average ratio)**  **B(b) = (1/Z) \* SUM over all zones z of R(b,z)** |

df['brand\_baseline'] = df.groupby('brand')['ratio'].transform('mean')

|  |
| --- |
| **Data Consistency Check**  B(b) is derived entirely from R(b,z) values computed in Analysis 1 — same dataset, no new sources. |

|  |
| --- |
| **Caveat**  This is an unweighted mean — each zone contributes equally regardless of showroom count. A weighted mean (weighted by SW(b,z)) is more accurate. Run both and compare; report whichever is used and note the choice. |

# **Analysis 3: Deviation from Brand Baseline**

## **Plain English**

How far is each zone from the brand's own average, expressed as a percentage? A deviation of -70% means the zone is 70% worse than the brand's national norm. Percentage framing normalises comparisons across brands with different baseline ratios.

## **Formula**

|  |
| --- |
| **Percentage deviation**  **D(b,z) = ( R(b,z) - B(b) ) / B(b) \* 100** |

df['deviation\_pct'] = (df['ratio'] - df['brand\_baseline']) / df['brand\_baseline'] \* 100

|  |
| --- |
| **Data Consistency Check**  Pure derivation from Analyses 1 and 2. No new data introduced. |

|  |
| --- |
| **Caveat**  Sensitive to outliers in R(b,z). Check for extreme values in any one zone before computing the baseline — a single anomalous zone can skew B(b) and distort all deviations. |

# **Analysis 4: Bottleneck Severity Classification**

## **Plain English**

Convert the continuous deviation score into three severity buckets for map visualisation and presentation. A zone is only flagged if its deviation is negative and crosses a minimum threshold.

## **Formula**

|  |
| --- |
| **Severity classification**  **D(b,z) >= -30% -> No bottleneck -50% <= D(b,z) < -30% -> Mild -70% <= D(b,z) < -50% -> Moderate D(b,z) < -70% -> Severe** |

conditions = [D >= -30, (D >= -50)&(D<-30), (D >= -70)&(D<-50), D < -70]

labels = ['None', 'Mild', 'Moderate', 'Severe']

df['severity'] = np.select(conditions, labels)

|  |
| --- |
| **Data Consistency Check**  Computed directly from D(b,z). No new data. |

|  |
| --- |
| **Caveat**  Thresholds (-30%, -50%, -70%) are modelling choices. Run analysis at three threshold sets and confirm top bottlenecks appear consistently across all three. Only headline zones that are 'Severe' under the most conservative threshold. |

# **Analysis 5: Revenue Leakage Estimate**

## **Plain English**

Compare how many bikes each showroom sells in a healthy zone vs. a bottlenecked zone. Multiply the shortfall by the number of showrooms in the bottlenecked zone and by the average bike price. The result is the estimated annual revenue the brand is not earning due to the service gap.

## **Formulas**

|  |
| --- |
| **Sales per showroom per zone**  **SPsW(b,z) = UNITS(b,z) / SW(b,z)** |

|  |
| --- |
| **Healthy benchmark**  **H(b) = mean of SPsW(b,z) for all z where severity = 'None'** |

|  |
| --- |
| **Unit gap per showroom**  **GAP(b,z) = H(b) - SPsW(b,z) [calculated only where GAP > 0]** |

|  |
| --- |
| **Revenue leakage estimate**  **LEAK(b,z) = GAP(b,z) \* SW(b,z) \* ASP(b)** |

| **Variable** | **Meaning** | **Source** |
| --- | --- | --- |
| UNITS(b,z) | Annual units sold — brand b, zone z | FADA state-wise data aggregated to zone |
| SW(b,z) | Showroom count | BikeWale scrape (Analysis 1) |
| H(b) | Healthy benchmark: avg sales/showroom in non-bottleneck zones | Calculated |
| ASP(b) | Average selling price (rupees) | Brand annual report: Revenue ÷ Units |
| LEAK(b,z) | Estimated annual revenue lost (₹) | Final output |

|  |
| --- |
| **Data Consistency Check**  SW(b,z) from Analysis 1. UNITS(b,z) from FADA. Critical: both must use identical state-to-zone mapping from constants.py. ASP(b) is a single scalar per brand applied uniformly across zones. |

|  |
| --- |
| **Caveat**  Three embedded assumptions: (1) the healthy benchmark is achievable in bottlenecked zones, (2) service scarcity is the primary reason for underperformance, (3) ASP is uniform across zones. Present LEAK as an upper-bound estimate. For Jawa (private company): estimate ASP as weighted average of official model prices. |

# **Analysis 6: Pearson Correlation**

## **Plain English**

Does a zone with a better service ratio tend to sell more bikes? The Pearson r coefficient measures the strength of this linear relationship. r above +0.6 with p < 0.05 supports the central hypothesis. Run separately for each brand, treating each zone as one data point.

## **Formula**

|  |
| --- |
| **Pearson r**  **r = SUM[(R\_i - R\_mean)(U\_i - U\_mean)] / SQRT[SUM(R\_i-R\_mean)^2 \* SUM(U\_i-U\_mean)^2]** |

from scipy import stats

r, p\_value = stats.pearsonr(df\_brand['ratio'], df\_brand['units\_sold'])

| **Result** | **Interpretation** |
| --- | --- |
| r > 0.6, p < 0.05 | Strong positive correlation — supports hypothesis |
| 0.3 < r < 0.6, p < 0.05 | Moderate — some relationship; other factors also at play |
| r < 0.3 or p >= 0.05 | Weak/insignificant — cannot conclude systematic relationship |
| r < 0 | Negative — investigate for confounders or reverse causality |

|  |
| --- |
| **Data Consistency Check**  R(b,z) from Analysis 1. UNITS(b,z) from FADA. Zone mapping must be identical for both datasets — enforced by constants.py. |

|  |
| --- |
| **Caveat**  With only 6 zones per brand, n=6 requires r > 0.71 for p < 0.05. Results will often be directionally interesting but not statistically significant. Report as 'indicative evidence'. Combine with revenue leakage to build the full argument. |

# **Analysis 7: Expansion Priority Index**

## **Plain English**

Where should a brand open its next service center for maximum strategic impact? Two factors determine priority: how severe the bottleneck is, and how much commercial volume that zone generates. Both factors are normalised to 0-1 and combined with equal weight (adjustable).

## **Formulas**

|  |
| --- |
| **Normalised severity (0 to 1)**  **NSEV(b,z) = |D(b,z)| / max(|D(b,z)|) [only for D(b,z) < 0]** |

|  |
| --- |
| **Normalised volume (0 to 1)**  **NVOL(b,z) = UNITS(b,z) / max(UNITS(b,z))** |

|  |
| --- |
| **Expansion Priority Index**  **EPI(b,z) = w1\*NSEV(b,z) + w2\*NVOL(b,z) where w1+w2=1, default w1=w2=0.5** |

df['nsev'] = df['abs\_dev'] / df.groupby('brand')['abs\_dev'].transform('max')

df['nvol'] = df['units'] / df.groupby('brand')['units'].transform('max')

df['epi'] = 0.5\*df['nsev'] + 0.5\*df['nvol']

|  |
| --- |
| **Data Consistency Check**  NSEV from Analysis 3; NVOL from FADA (same as Analysis 5). Normalised within-brand, so zone definitions must match — guaranteed by constants.py. |

|  |
| --- |
| **Caveat**  Present results at three weight combinations: (70/30), (50/50), (30/70). If rankings change materially, note the sensitivity. A brand in growth phase would weight volume higher; one focused on retention would weight severity higher. |

# **Analysis 8: HHI Clustering Analysis**

## **Plain English**

Two brands can have the same zone ratio but very different geographic spread. HHI (Herfindahl-Hirschman Index) measures whether service centers are concentrated in one or two big cities or spread across many towns. A high HHI means customers outside the main city are effectively unserved — even though the zone count looks fine.

## **Formulas**

|  |
| --- |
| **City's share of zone's service centers**  **s(b,z,c) = SC(b,z,c) / SC(b,z)** |

|  |
| --- |
| **HHI for brand b, zone z**  **HHI(b,z) = SUM over all cities c in zone z of [ s(b,z,c) ]^2** |

| **HHI range** | **Interpretation** |
| --- | --- |
| Below 0.15 | Well dispersed across many cities |
| 0.15 to 0.25 | Moderately concentrated — a few cities dominate |
| Above 0.25 | Highly concentrated — rural customers effectively unserved |

df['share'] = df['sc\_count'] / df.groupby(['brand','zone'])['sc\_count'].transform('sum')

hhi = df.groupby(['brand','zone'])['share'].apply(lambda x: (x\*\*2).sum()).reset\_index(name='hhi')

|  |
| --- |
| **Data Consistency Check**  Uses city-level BikeWale scrape data — same source as Analysis 1, not aggregated to zone level. City field must be consistent. |

|  |
| --- |
| **Caveat**  City name normalisation is critical before this calculation. BikeWale may list 'Mumbai', 'Mumbai Suburbs', and 'Navi Mumbai' as separate entries, artificially lowering HHI for Mumbai. Apply fuzzy matching (rapidfuzz, threshold 85%) and manual review before running HHI. |

# **Analysis 9: Brand Maturity vs Network Balance**

## **Plain English**

Some brands are growing sales faster than they are building service infrastructure. The gap between sales CAGR and service network CAGR flags brands that are structurally outrunning their own service capacity — a risk that compounds over time.

## **Formulas**

|  |
| --- |
| **Sales CAGR**  **CAGR\_sales(b) = (UNITS(b,n) / UNITS(b,0))^(1/n) - 1** |

|  |
| --- |
| **Service network CAGR**  **CAGR\_sc(b) = (SC\_total(b,n) / SC\_total(b,0))^(1/n) - 1** |

|  |
| --- |
| **Network balance gap**  **GAP\_maturity(b) = CAGR\_sales(b) - CAGR\_sc(b)** |

Positive GAP\_maturity = sales growing faster than service capacity (risk signal). Negative = service expanding ahead of sales (healthy).

| **Variable** | **Source** |
| --- | --- |
| UNITS(b,0) and UNITS(b,n) | FADA annual retail data or brand annual reports — national totals |
| SC\_total(b,0) | Brand annual reports / investor presentations for historical SC count. If unavailable, estimate from archived press releases. |
| SC\_total(b,n) | Current count from BikeWale scrape |
| n | Number of years in CAGR window (recommend 3-5 years) |

|  |
| --- |
| **Data Consistency Check**  UNITS data from FADA — same source as Analyses 5, 6, 7. SC\_total for year 0 may come from a different source (historical brand disclosures) than the current BikeWale scrape. Scrape date and historical disclosure date must both be documented in the methodology. |

|  |
| --- |
| **Caveat**  Historical service center counts are not consistently publicly available. Royal Enfield and Hero MotoCorp include network growth in investor presentations; others may not. Where historical counts are unavailable, mark that brand's Analysis 9 result as approximate or omit it entirely. |

# **Analysis 10: Northeast and Hill-State Neglect Score**

## **Plain English**

Northeast India and mountain states (Himachal Pradesh, Uttarakhand, J&K) are geographically isolated and historically underserved by consumer industries. This analysis produces a single per-brand neglect score weighted by state population — a larger neglected population means a higher neglect score.

## **Formula**

|  |
| --- |
| **Population-weighted neglect score**  **NEGLECT(b) = SUM over isolated states s of [ D(b,s) \* POP(s) ] / SUM of POP(s)** |

D(b,s) is computed at state level — same deviation formula as Analysis 3 but using state-level R(b,s) and a state-level brand baseline.

| **Variable** | **Source** |
| --- | --- |
| D(b,s) | State-level deviation — from BikeWale state-level data and same formula as Analysis 3 |
| POP(s) | State population from Census of India (censusindia.gov.in) |

|  |
| --- |
| **Data Consistency Check**  D(b,s) uses BikeWale data at state granularity — not aggregated to zone. POP(s) is a new supplementary source introduced here and in Analysis 12. |

|  |
| --- |
| **Caveat**  Population weighting reduces apparent severity of neglect in smaller NE states (Mizoram, Nagaland) relative to Assam. Run both weighted and unweighted versions. Also consider whether to use 2011 Census or 2021 projections — document which is used. |

# **Analysis 11: Competitor Advantage Map**

## **Plain English**

When Brand A has a bottleneck in a zone, which competitor is best positioned to capture dissatisfied customers? For each bottlenecked brand-zone pair, rank all other brands by their R(b,z) in that same zone. The brand with the highest ratio is the biggest competitive beneficiary.

## **Formula**

|  |
| --- |
| **Competitor advantage in zone z for bottlenecked brand b\_A**  **COMP\_ADV(z, b\_A) = argmax over all b != b\_A of [ R(b, z) ]** |

pivot = df.pivot\_table(index='zone', columns='brand', values='ratio')

# For each bottlenecked (brand, zone):

competitor = pivot.loc[zone].drop(brand).idxmax()

Jawa's inclusion makes this analysis particularly relevant in the mid-size retro segment, where Royal Enfield and Jawa directly compete and each other's bottlenecks represent mutual opportunity.

|  |
| --- |
| **Data Consistency Check**  Uses only R(b,z) from Analysis 1 and severity from Analysis 4. All brands must be scraped on the same date to ensure the R values are comparable. No new data introduced. |

|  |
| --- |
| **Caveat**  A high R(b,z) means a competitor is better positioned — not that customer poaching is confirmed. Frame findings as 'competitive exposure' or 'zone vulnerability', not as measured customer loss. |

# **Analysis 12: Rural vs Urban Bottleneck Split**

## **Plain English**

Even within a zone, service centers may cluster in metros while smaller towns are unserved. Since Hero and Bajaj derive more than half their volume from tier 2/3 markets, a bottleneck concentrated in smaller towns is commercially more damaging than a metro gap. This analysis computes separate ratios for each city tier.

## **Formulas**

|  |
| --- |
| **City tier classification**  **TIER(c) = 1 if POP(c) >= 1,000,000 = 2 if 100,000 <= POP(c) < 1,000,000 = 3 if POP(c) < 100,000** |

|  |
| --- |
| **Tier-level ratio**  **R\_tier(b,t) = SUM of SC(b,c) for TIER(c)=t / SUM of SW(b,c) for same cities** |

df = df.merge(city\_tier\_df, on='city', how='left')

tier = df.groupby(['brand','tier'])[['service\_centers','showrooms']].sum()

tier['ratio'] = tier['service\_centers'] / tier['showrooms']

|  |
| --- |
| **Data Consistency Check**  City tier lookup from Census population data — same source as Analysis 10. Joined to BikeWale scrape using city name as key. Tier thresholds defined in constants.py. |

|  |
| --- |
| **Caveat**  City name join between BikeWale and Census is a fuzzy match (rapidfuzz, threshold 85%). Review all unmatched cities manually before including results. Some cities may have grown past their Census-tier since 2011 — note the data vintage. |

|  |
| --- |
| **CHAPTER 5**  **Radius-Based Spatial Coverage Analysis** |

# **5.1 Why Zone-Level Analysis is Insufficient**

Zone-level ratios mask intra-zone distribution problems. A brand could have a healthy zone ratio while all its service centers are concentrated in one or two large cities — leaving the rest of the zone effectively uncovered.

|  |
| --- |
| **Illustrative example**  Maharashtra (West zone) might show a healthy ratio of 0.52. But if all 40 service centers are in Mumbai and Pune, a customer in Nagpur, Aurangabad, or Kolhapur has no practical access. The zone ratio looks fine; the ground reality is not. |

Radius-based coverage analysis asks a geographically precise question: for each showroom, is there at least one same-brand service center within an acceptable travel distance? A showroom with no nearby service center represents a genuine coverage gap regardless of the zone-level ratio.

The three analysis levels are cumulative, not mutually exclusive:

| **Level** | **Granularity** | **Analysis** |
| --- | --- | --- |
| Zone | 6 macro regions | Broad imbalances — headline numbers for presentation (Analyses 1-12) |
| State | 36 states/UTs | Which specific states within a zone have worst ratios |
| Spatial | City / district | Exactly which areas are outside service radius — most visually compelling (Analysis 13) |

# **5.2 Context-Sensitive Radius Tiers**

A single radius would be inappropriate across India's diverse geography. Three tiers based on city type and road connectivity:

| **City tier** | **Population** | **Service radius** | **Rationale** |
| --- | --- | --- | --- |
| Tier 1 (Metro) | Above 10 lakh | 25 km | Dense urban areas; short travel; public transport available |
| Tier 2 (Urban) | 1 lakh to 10 lakh | 50 km | Moderate connectivity; customers willing to travel further |
| Tier 3 (Semi-urban/Rural) | Below 1 lakh | 75 km | Poor road infrastructure; longest acceptable travel; few alternatives |

Radius thresholds are defined in constants.py: RADIUS\_BY\_TIER = {1: 25, 2: 50, 3: 75}. The city tier of each showroom (from Analysis 12 tier classification) determines which threshold applies to it.

|  |
| --- |
| **Caveat**  Haversine distance (used in Analysis 13) gives straight-line crow-flies distance, not road distance. Actual travel distance is typically 1.2x-1.5x Haversine in urban areas and up to 2x in hilly terrain (Northeast, Himachal, Uttarakhand). The methodology must explicitly state that Haversine is a conservative lower-bound approximation. A future refinement would use the Google Maps Distance Matrix API for road distances. |

# **5.3 Geocoding**

## **Process**

* **Primary:** geopy library with Nominatim geocoder (OpenStreetMap-based, free, no API key). Converts city names / pincodes to lat/lon.
* **Fallback:** India Pincode Database (data.gov.in) — CSV with lat/lon for all Indian pincodes. Use when Nominatim fails.
* **Validation:** Spot-check 5% of coordinates on a map. Nominatim occasionally misreads ambiguous city names.
* **Caching:** Save geocoded results to CSV after first run. Never re-geocode in a loop — Nominatim rate limit is 1 request/second.

from geopy.geocoders import Nominatim

geolocator = Nominatim(user\_agent='moto\_analysis')

location = geolocator.geocode('Nagpur, Maharashtra, India')

lat, lon = location.latitude, location.longitude

# **5.4 Haversine Distance Formula**

## **Plain English**

Given two points on Earth — a showroom and a service center — Haversine computes the straight-line surface distance between them in kilometres. It accounts for Earth's curvature, unlike flat Euclidean distance which becomes inaccurate over long distances.

## **Formula**

|  |
| --- |
| **Haversine great-circle distance**  **a = sin^2((lat2-lat1)/2) + cos(lat1)\*cos(lat2)\*sin^2((lon2-lon1)/2) d = 2 \* R\_earth \* arcsin(sqrt(a)) R\_earth = 6371 km | all angles in radians** |

from math import radians, sin, cos, sqrt, atan2

def haversine(lat1, lon1, lat2, lon2):

R = 6371

dlat = radians(lat2-lat1); dlon = radians(lon2-lon1)

a = sin(dlat/2)\*\*2 + cos(radians(lat1))\*cos(radians(lat2))\*sin(dlon/2)\*\*2

return 2\*R\*atan2(sqrt(a), sqrt(1-a))

For batch computation across all showroom-service center pairs, use scipy.spatial.distance.cdist with haversine metric — far faster than Python loops.

from scipy.spatial.distance import cdist

# coords in radians for scipy

sw\_coords = np.radians(showrooms[['lat','lon']].values)

sc\_coords = np.radians(service\_centers[['lat','lon']].values)

dist\_km = cdist(sw\_coords, sc\_coords, metric='haversine') \* 6371

# **5.5 Coverage Gap Rate (CGR)**

## **Plain English**

For each showroom, find the nearest same-brand service center. If that distance exceeds the radius threshold for the showroom's city tier, the showroom is 'uncovered'. The CGR for a district or state is the proportion of showrooms that are uncovered.

## **Formulas**

|  |
| --- |
| **Minimum distance to nearest service center**  **MIN\_DIST(b,i) = min over all j in SC(b) of [ haversine(lat\_i, lon\_i, lat\_j, lon\_j) ]** |

|  |
| --- |
| **Coverage flag**  **COVERED(b,i) = 1 if MIN\_DIST(b,i) <= RADIUS(TIER(i)) = 0 otherwise** |

|  |
| --- |
| **Coverage Gap Rate per region**  **CGR(b, region) = COUNT(COVERED=0 in region) / COUNT(all showrooms in region)** |

CGR = 0 means full coverage. CGR = 1 means no showroom has a nearby service center. In Pandas:

df['min\_dist'] = dist\_km.min(axis=1) # min across all service centers

df['covered'] = (df['min\_dist'] <= df['radius']).astype(int)

cgr = df.groupby(['brand','state']).apply(lambda x: 1 - x['covered'].mean())

|  |
| --- |
| **Data Consistency Check**  Showroom and service center coordinates both geocoded from the BikeWale scrape — same source as all other analyses. TIER per showroom from city\_tier table (same as Analysis 12). RADIUS thresholds from constants.py. CGR is computed at state level and can be joined to the India district shapefile for map rendering. |

|  |
| --- |
| **Caveat**  The distance matrix for a brand with 500 showrooms and 200 service centers is 100,000 entries. Use scipy cdist — never Python loops. Memory is manageable (~0.8 MB for float64 at this scale). Geocoding errors will produce incorrect distances — validate geocoded coordinates before running CGR. |

# **5.6 Cross-Analysis Consistency Summary**

| **Analysis** | **Data sources** | **Shared variables** | **Key consistency requirement** |
| --- | --- | --- | --- |
| 1-4 | BikeWale scrape | SC(b,z), SW(b,z), R(b,z), D(b,z) | Same scrape date; zone map from constants.py |
| 5 | BikeWale + FADA + ASP | SW(b,z), UNITS(b,z), ASP(b) | Zone mapping identical across BikeWale and FADA |
| 6 | BikeWale + FADA | R(b,z), UNITS(b,z) | Same zone mapping |
| 7 | Analyses 3 + 5 | D(b,z), UNITS(b,z) | Inherits consistency from parent analyses |
| 8 | BikeWale (city level) | SC(b,z,c) | City name normalisation before HHI |
| 9 | FADA (multi-year) + brand disclosures | CAGR inputs | Document dates of both historical and current data |
| 10 | BikeWale (state) + Census POP | D(b,s), POP(s) | State-level zone map consistent with constants.py |
| 11 | Analyses 1 + 4 | R(b,z), severity | All brands scraped on same date |
| 12 | BikeWale + Census city population | SC(b,c), SW(b,c), TIER(c) | Fuzzy city match; review unmatched cities |
| 13 | BikeWale (lat/lon) + constants.py radii | MIN\_DIST, COVERED, CGR | Validate geocoded coordinates; radii in constants.py |

|  |
| --- |
| **The golden rule of this project**  constants.py is the single source of truth. It contains: state\_to\_zone dictionary, RADIUS\_BY\_TIER dictionary, tier population thresholds, brand\_list (all 11 brands), asp\_by\_brand dictionary. Every script imports from this file. No analysis script defines any of these values independently. |

# **5.7 Visualisation: Coverage Gap Map**

The CGR output is joined to the India district shapefile (GADM, gadm.org) using district/state name as the key. GeoPandas renders a choropleth where colour intensity represents CGR — the darker the district, the higher the proportion of showrooms outside service radius.

* **Light colour (CGR < 0.2):** Most showrooms are well-covered — acceptable.
* **Medium colour (CGR 0.2-0.5):** Significant minority of showrooms are uncovered — watch zone.
* **Dark colour (CGR > 0.5):** Majority of showrooms have no nearby service center — severe gap.

This map is the most visually compelling output in the project. A brand's regional sales manager can immediately point to uncovered districts on the map and understand the specific geographic gap — far more actionable than a zone-level ratio number.

*— End of Master Reference Document | Version 1.0 | June 2026 —*