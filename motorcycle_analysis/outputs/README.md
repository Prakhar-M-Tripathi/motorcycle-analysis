# Motorcycle network dashboard

## Open the dashboard

Open `final_dashboard.html` in a modern browser. This is the single publishable file: it embeds the analysis, Plotly library, radius explorer, and radius-map data. Use the top navigation to switch between the overview, brand profiles, and the interactive radius explorer. The map loads Leaflet and OpenStreetMap basemap tiles from the internet, so the map needs a network connection; the dashboard charts and analysis are embedded. OpenStreetMap tiles are best-effort and subject to the OSM tile usage policy; for high-traffic publishing, select a hosted tile provider or run your own tiles.

## Regenerate the outputs

From the `motorcycle_analysis` folder, run:

```powershell
python outputs/map_explorer.py
python outputs/final_dashboard.py
```

The map is generated first because the dashboard embeds its generated HTML. The builder also embeds Plotly from the installed Python package. The dashboard reads the SQLite snapshot and JSON analysis outputs under `data/analysis/`.

## Reading the findings

- The network snapshot is from BikeWale, scraped on June 9, 2026. It contains 9 brands and 774 city records; the radius map displays only cities with usable coordinates and matching brand network data.
- Ola Electric and Ather have no comparable BikeWale service-centre counts. Their service ratios are therefore omitted from brand ratio rankings.
- City tiers use total dealer presence as a size proxy, not Census population.
- Revenue figures are the current simple network-gap proxy from `revenue_leakage.json` (positive showroom minus service counts, brand ASP, and a 15% assumption). They are not measured or FADA-based lost revenue.
- The available `correlation.json` contains demonstration sales indices. It is not used as evidence. A validated FADA sales dataset is needed for the planned correlation analysis.
- No state-boundary shapefile is present, so geographic exploration uses city coordinates and radius queries rather than a state choropleth.
- Geographic patterns are descriptive and exploratory. The metrics do not establish that service coverage causes sales outcomes.

The dashboard design and research framing follow `stitch_brief.md`, `mrd.md`, `mrd.docx`, `Maths.docx`, `Implementation.docx`, and the root `implementation,md`; scraper-specific caveats are documented in `scraping_problems_note.md`.
