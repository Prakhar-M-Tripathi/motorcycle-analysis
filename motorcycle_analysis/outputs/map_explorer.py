"""
map_explorer.py  —  Interactive India Radius Map
-------------------------------------------------
Exports all city-brand data from the DB, then generates a self-contained
map_explorer.html where the user can click any point on India to instantly
see brand stats (SC, SW, ratio, leaders/trailers) within an adjustable radius.

Run:
    python outputs/map_explorer.py
"""

import json, os, sys, sqlite3, datetime

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH     = os.path.join(PROJECT_DIR, "db", "motorcycle_analysis.db")
OUTPUT_PATH = os.path.join(PROJECT_DIR, "outputs", "map_explorer.html")

BRAND_LIST  = ["hero","honda","bajaj","royal-enfield","yamaha",
               "suzuki","ola-electric","ather","jawa"]
BD = {
    "hero":"Hero","honda":"Honda","bajaj":"Bajaj",
    "royal-enfield":"Royal Enfield","yamaha":"Yamaha","suzuki":"Suzuki",
    "ola-electric":"Ola Electric","ather":"Ather","jawa":"Jawa"
}
BCOL = {
    "hero":"#e74c3c","honda":"#e67e22","bajaj":"#f0c040",
    "royal-enfield":"#3b82f6","yamaha":"#a855f7","suzuki":"#22c55e",
    "ola-electric":"#ff5722","ather":"#607d8b","jawa":"#a07850"
}
EV   = {"ola-electric","ather"}
ZCOL = {
    "North":"#3b82f6","South":"#22c55e","West":"#f59e0b",
    "East":"#a855f7","Central":"#ef4444","Northeast":"#06b6d4","Unknown":"#52525b"
}

# ── 1. Pull data from DB ──────────────────────────────────────────────────────
conn = sqlite3.connect(DB_PATH)
rows = conn.execute("""
    SELECT city_slug, city, lat, lon, zone, state, brand, type,
           SUM(count) as cnt
    FROM dealers
    WHERE scrape_date='2026-06-09'
      AND lat IS NOT NULL AND lon IS NOT NULL
    GROUP BY city_slug, brand, type
    ORDER BY city_slug
""").fetchall()
conn.close()

city_dict = {}
for slug, city, lat, lon, zone, state, brand, typ, cnt in rows:
    if slug not in city_dict:
        city_dict[slug] = {
            "c": city,
            "la": round(lat, 5),
            "lo": round(lon, 5),
            "z": zone,
            "s": state or "",
            "b": {b: [0, 0] for b in BRAND_LIST}   # [sc, sw]
        }
    if brand in BRAND_LIST:
        k = 0 if typ == "service" else 1
        city_dict[slug]["b"][brand][k] += int(cnt)

city_data = [v for v in city_dict.values()
             if any(v["b"][b][0] + v["b"][b][1] > 0 for b in BRAND_LIST)]

print(f"  Cities embedded: {len(city_data)}")

# Compact JSON (no spaces)
CITIES_JSON = json.dumps(city_data, separators=(",", ":"))

# JS arrays for brand names and colours
BRAND_KEYS_JS  = json.dumps(BRAND_LIST)
BRAND_NAMES_JS = json.dumps([BD[b] for b in BRAND_LIST])
BRAND_COLS_JS  = json.dumps([BCOL[b] for b in BRAND_LIST])
ZONE_COLS_JS   = json.dumps(ZCOL)
EV_SET_JS      = json.dumps(list(EV))

GENERATED = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")

# ── 2. Build HTML ─────────────────────────────────────────────────────────────
HTML = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>India Dealer Radius Explorer — Motorcycle Network Analysis</title>
<link rel="stylesheet" href="https://unpkg.com/maplibre-gl@5/dist/maplibre-gl.css"/>
<style>
*{{margin:0;padding:0;box-sizing:border-box}}
:root{{
  --bg:#0f1117;--surface:#1a1d27;--surface2:#252836;--border:#2e3347;
  --text:#e8eaf0;--muted:#8b92a8;--accent:#16a34a;--accent2:#22c55e;
  --warn:#f59e0b;--danger:#ef4444;
  --font:'Segoe UI',system-ui,sans-serif;
}}
body{{background:var(--bg);color:var(--text);font-family:var(--font);height:100vh;display:flex;flex-direction:column}}
#topbar{{
  background:var(--surface);border-bottom:1px solid var(--border);
  padding:10px 18px;display:flex;align-items:center;gap:16px;flex-shrink:0;z-index:1000;
}}
#topbar h1{{font-size:14px;font-weight:600;color:var(--accent2);white-space:nowrap}}
#topbar p{{font-size:11px;color:var(--muted)}}
.controls{{display:flex;align-items:center;gap:12px;margin-left:auto}}
.ctrl-group{{display:flex;align-items:center;gap:8px;background:var(--surface2);
  border:1px solid var(--border);border-radius:8px;padding:6px 12px}}
.ctrl-group label{{font-size:11px;color:var(--muted);white-space:nowrap}}
#radiusSlider{{
  -webkit-appearance:none;width:110px;height:4px;border-radius:2px;
  background:var(--border);outline:none;
}}
#radiusSlider::-webkit-slider-thumb{{
  -webkit-appearance:none;width:14px;height:14px;border-radius:50%;
  background:var(--accent2);cursor:pointer;
}}
#radiusVal{{font-size:12px;font-weight:600;color:var(--accent2);min-width:48px}}
.toggle-btn{{
  background:var(--surface2);border:1px solid var(--border);color:var(--muted);
  padding:5px 10px;border-radius:6px;cursor:pointer;font-size:11px;
}}
.toggle-btn.active{{background:var(--accent);border-color:var(--accent);color:#fff}}
#back-link{{
  background:var(--surface2);border:1px solid var(--border);color:var(--muted);
  padding:5px 12px;border-radius:6px;cursor:pointer;font-size:11px;text-decoration:none;
  white-space:nowrap;
}}
#back-link:hover{{color:var(--text)}}
#main{{display:flex;flex:1;overflow:hidden}}
#map{{flex:1;z-index:1}}
#panel{{
  width:340px;flex-shrink:0;background:var(--surface);border-left:1px solid var(--border);
  display:flex;flex-direction:column;overflow:hidden;
}}
#panel-header{{
  padding:14px 16px 10px;border-bottom:1px solid var(--border);flex-shrink:0;
}}
#panel-title{{font-size:13px;font-weight:600;color:var(--text)}}
#panel-sub{{font-size:11px;color:var(--muted);margin-top:2px}}
#panel-body{{flex:1;overflow-y:auto;padding:12px}}
#panel-body::-webkit-scrollbar{{width:4px}}
#panel-body::-webkit-scrollbar-track{{background:transparent}}
#panel-body::-webkit-scrollbar-thumb{{background:var(--border);border-radius:2px}}
.placeholder{{
  display:flex;flex-direction:column;align-items:center;justify-content:center;
  height:100%;color:var(--muted);text-align:center;padding:24px;
}}
.placeholder .icon{{font-size:40px;margin-bottom:12px;opacity:.5}}
.placeholder p{{font-size:12px;line-height:1.6}}
.section-label{{font-size:10px;font-weight:700;color:var(--muted);letter-spacing:.08em;
  text-transform:uppercase;margin:12px 0 6px}}
.section-label:first-child{{margin-top:0}}
.summary-grid{{display:grid;grid-template-columns:1fr 1fr;gap:8px;margin-bottom:4px}}
.kpi{{background:var(--surface2);border:1px solid var(--border);border-radius:8px;padding:10px 12px}}
.kpi .val{{font-size:20px;font-weight:700;color:var(--accent2)}}
.kpi .lab{{font-size:10px;color:var(--muted);margin-top:2px}}
.leader-card,.trailer-card{{
  border-radius:8px;padding:10px 12px;margin-bottom:8px;
  display:flex;align-items:center;gap:10px;
}}
.leader-card{{background:#14532d33;border:1px solid #16a34a55}}
.trailer-card{{background:#7f1d1d33;border:1px solid #ef444455}}
.badge{{font-size:10px;font-weight:700;padding:2px 7px;border-radius:4px;white-space:nowrap}}
.badge.leader{{background:#16a34a;color:#fff}}
.badge.trailer{{background:#ef4444;color:#fff}}
.badge.ev{{background:#607d8b;color:#fff}}
.card-brand{{font-size:13px;font-weight:600}}
.card-detail{{font-size:11px;color:var(--muted);margin-top:2px}}
.brand-table{{width:100%;border-collapse:collapse;font-size:12px}}
.brand-table th{{color:var(--muted);font-size:10px;font-weight:600;text-align:left;
  padding:4px 6px;border-bottom:1px solid var(--border)}}
.brand-table td{{padding:5px 6px;border-bottom:1px solid #1e2130;vertical-align:middle}}
.brand-table tr:last-child td{{border-bottom:none}}
.brand-table tr:hover td{{background:#1e2130}}
.brand-dot{{width:8px;height:8px;border-radius:50%;display:inline-block;margin-right:6px}}
.ratio-bar-wrap{{position:relative;background:var(--surface2);border-radius:3px;height:6px;width:70px}}
.ratio-bar{{position:absolute;left:0;top:0;height:100%;border-radius:3px}}
.ratio-good{{color:#22c55e;font-weight:600}}
.ratio-warn{{color:#f59e0b;font-weight:600}}
.ratio-bad{{color:#ef4444;font-weight:600}}
.ratio-na{{color:var(--muted)}}
.zone-row{{display:flex;align-items:center;gap:8px;margin-bottom:5px;font-size:11px}}
.zone-bar-wrap{{flex:1;background:var(--surface2);border-radius:3px;height:8px}}
.zone-bar{{height:100%;border-radius:3px}}
.city-chips{{display:flex;flex-wrap:wrap;gap:4px;margin-top:4px}}
.city-chip{{font-size:10px;background:var(--surface2);border:1px solid var(--border);
  border-radius:4px;padding:2px 7px;color:var(--muted)}}
.maplibregl-map{{background:#0d1117}}
.maplibregl-popup-content{{
  background:var(--surface);border:1px solid var(--border);border-radius:8px;
  color:var(--text);font-family:var(--font);font-size:12px;box-shadow:0 4px 20px #0006;
  padding:10px 14px;line-height:1.5;
}}
.maplibregl-popup-close-button{{color:var(--muted);font-size:16px}}
.maplibregl-ctrl-group{{background:var(--surface);border:1px solid var(--border)}}
.maplibregl-ctrl-group button{{filter:invert(.85)}}
.maplibregl-ctrl-attrib{{background:#111827dd!important;color:#cbd5e1!important}}
.maplibregl-ctrl-attrib a{{color:#cbd5e1!important}}
</style>
</head>
<body>

<div id="topbar">
  <div>
    <h1>India Dealer Radius Explorer</h1>
    <p>Click anywhere on the map to analyse all brands within a chosen radius</p>
  </div>
  <div class="controls">
    <div class="ctrl-group">
      <label>Radius</label>
      <input type="range" id="radiusSlider" min="25" max="200" step="25" value="75">
      <span id="radiusVal">75 km</span>
    </div>
    <button class="toggle-btn active" id="toggleMarkers" onclick="toggleMarkers()">City Dots</button>
    <a href="final_dashboard.html" id="back-link">← Dashboard</a>
  </div>
</div>

<div id="main">
  <div id="map"></div>
  <div id="panel">
    <div id="panel-header">
      <div id="panel-title">Radius Analysis</div>
      <div id="panel-sub">No location selected</div>
    </div>
    <div id="panel-body">
      <div class="placeholder">
        <div class="icon">📍</div>
        <p>Click any point on the map to see which brands have the strongest
        and weakest presence in that area.</p>
        <br>
        <p style="font-size:11px;color:#4a5168">Adjust the radius slider to widen or narrow the search area.</p>
      </div>
    </div>
  </div>
</div>

<script src="https://unpkg.com/maplibre-gl@5/dist/maplibre-gl.js"></script>
<script>
// ── Data ─────────────────────────────────────────────────────────────────────
const CITIES       = {CITIES_JSON};
const BRAND_KEYS   = {BRAND_KEYS_JS};
const BRAND_NAMES  = {BRAND_NAMES_JS};
const BRAND_COLS   = {BRAND_COLS_JS};
const ZONE_COLS    = {ZONE_COLS_JS};
const EV_SET       = new Set({EV_SET_JS});

// ── Map setup ─────────────────────────────────────────────────────────────────
const map = new maplibregl.Map({{
  container: 'map',
  style: 'https://tiles.openfreemap.org/styles/liberty',
  center: [79.5, 20.5], zoom: 4.4,
  attributionControl: false
}});
map.addControl(new maplibregl.NavigationControl({{showCompass:false}}), 'top-left');
map.addControl(new maplibregl.AttributionControl({{compact:false}}), 'bottom-right');

// ── City markers ──────────────────────────────────────────────────────────────
let markersVisible = true;

function totalDealers(b) {{
  return BRAND_KEYS.reduce((s,k)=> s + b[k][0] + b[k][1], 0);
}}

map.on('load', () => {{
  map.addSource('city-points', {{type:'geojson', data:{{
    type:'FeatureCollection', features:CITIES.map(c => ({{
      type:'Feature', geometry:{{type:'Point',coordinates:[c.lo,c.la]}},
      properties:{{name:c.c,state:c.s,zone:c.z,total:totalDealers(c.b)}}
    }}))
  }}}});
  map.addLayer({{id:'city-dots',type:'circle',source:'city-points',paint:{{
    'circle-radius':['interpolate',['linear'],['get','total'],0,3,15,4,50,6],
    'circle-color':['match',['get','zone'],'North','#3b82f6','South','#22c55e','West','#f59e0b','East','#a855f7','Central','#ef4444','Northeast','#06b6d4','#52525b'],
    'circle-opacity':.82,'circle-stroke-width':.7,'circle-stroke-color':'#0f1117'
  }}}});
  map.addSource('analysis-area', {{type:'geojson',data:{{type:'FeatureCollection',features:[]}}}});
  map.addLayer({{id:'analysis-fill',type:'fill',source:'analysis-area',filter:['==',['geometry-type'],'Polygon'],paint:{{'fill-color':'#22c55e','fill-opacity':.08}}}});
  map.addLayer({{id:'analysis-outline',type:'line',source:'analysis-area',filter:['==',['geometry-type'],'Polygon'],paint:{{'line-color':'#22c55e','line-width':2,'line-dasharray':[2,2]}}}});
  map.addLayer({{id:'analysis-point',type:'circle',source:'analysis-area',filter:['==',['geometry-type'],'Point'],paint:{{'circle-radius':6,'circle-color':'#22c55e','circle-stroke-color':'#e8eaf0','circle-stroke-width':2}}}});
  map.on('click','city-dots', e => {{
    const p=e.features[0].properties;
    new maplibregl.Popup({{closeButton:true,offset:8}}).setLngLat(e.lngLat)
      .setHTML(`<b>${{p.name}}</b><br>${{p.state}} · ${{p.zone}} zone<br>${{p.total}} dealer outlets`).addTo(map);
  }});
  map.on('mouseenter','city-dots',()=>map.getCanvas().style.cursor='pointer');
  map.on('mouseleave','city-dots',()=>map.getCanvas().style.cursor='');
}});

function toggleMarkers() {{
  markersVisible = !markersVisible;
  const btn = document.getElementById('toggleMarkers');
  if (map.getLayer('city-dots')) map.setLayoutProperty('city-dots','visibility',markersVisible?'visible':'none');
  if (markersVisible) btn.classList.add('active');
  else btn.classList.remove('active');
}}

// ── Radius circle & click ─────────────────────────────────────────────────────
let radiusKm     = 75;

const slider = document.getElementById('radiusSlider');
const radVal  = document.getElementById('radiusVal');
slider.addEventListener('input', () => {{
  radiusKm = +slider.value;
  radVal.textContent = radiusKm + ' km';
  if (lastClick) analysePoint(lastClick.lat, lastClick.lng);
}});

let lastClick = null;

function haversine(lat1, lon1, lat2, lon2) {{
  const R = 6371,
        dLat = (lat2-lat1)*Math.PI/180,
        dLon = (lon2-lon1)*Math.PI/180,
        a = Math.sin(dLat/2)**2 +
            Math.cos(lat1*Math.PI/180)*Math.cos(lat2*Math.PI/180)*Math.sin(dLon/2)**2;
  return 2*R*Math.asin(Math.sqrt(a));
}}

map.on('click', e => {{
  lastClick = {{lat:e.lngLat.lat,lng:e.lngLat.lng}};
  analysePoint(e.lngLat.lat, e.lngLat.lng);
}});

function radiusPolygon(lat,lon,km) {{
  const R=6371, d=km/R, p1=lat*Math.PI/180, l1=lon*Math.PI/180, ring=[];
  for(let i=0;i<=72;i++) {{
    const b=2*Math.PI*i/72;
    const p2=Math.asin(Math.sin(p1)*Math.cos(d)+Math.cos(p1)*Math.sin(d)*Math.cos(b));
    const l2=l1+Math.atan2(Math.sin(b)*Math.sin(d)*Math.cos(p1),Math.cos(d)-Math.sin(p1)*Math.sin(p2));
    ring.push([l2*180/Math.PI,p2*180/Math.PI]);
  }}
  return {{type:'Feature',geometry:{{type:'Polygon',coordinates:[ring]}},properties:{{}}}};
}}

function analysePoint(lat, lon) {{
  const source=map.getSource('analysis-area');
  if(source) source.setData({{type:'FeatureCollection',features:[radiusPolygon(lat,lon,radiusKm),{{type:'Feature',geometry:{{type:'Point',coordinates:[lon,lat]}},properties:{{}}}}]}});

  // Filter cities within radius
  const nearby = CITIES.filter(c => haversine(lat, lon, c.la, c.lo) <= radiusKm);
  renderPanel(lat, lon, nearby);
}}

// ── Stats panel ───────────────────────────────────────────────────────────────
function renderPanel(lat, lon, nearby) {{
  const sub = document.getElementById('panel-sub');
  sub.textContent = `${{lat.toFixed(3)}}°N ${{lon.toFixed(3)}}°E  ·  ${{radiusKm}} km radius`;

  if (nearby.length === 0) {{
    document.getElementById('panel-body').innerHTML = `
      <div class="placeholder">
        <div class="icon">🔍</div>
        <p>No cities with dealer data within ${{radiusKm}} km of this location.<br>
        Try a larger radius or click closer to a city.</p>
      </div>`;
    document.getElementById('panel-title').textContent = 'No data in range';
    return;
  }}

  document.getElementById('panel-title').textContent = `${{nearby.length}} cit${{nearby.length===1?'y':'ies'}} in range`;

  // Aggregate brand totals
  const agg = {{}};
  BRAND_KEYS.forEach(k => agg[k] = {{sc:0, sw:0}});
  nearby.forEach(c => BRAND_KEYS.forEach(k => {{
    agg[k].sc += c.b[k][0];
    agg[k].sw += c.b[k][1];
  }}));

  // Compute ratios (null for EV)
  const brands = BRAND_KEYS.map((k, i) => {{
    const {{sc, sw}} = agg[k];
    const isEv = EV_SET.has(k);
    const ratio = (!isEv && sw > 0) ? sc/sw : null;
    return {{ key: k, name: BRAND_NAMES[i], col: BRAND_COLS[i],
              sc, sw, ratio, isEv, total: sc+sw }};
  }}).filter(b => b.total > 0)
    .sort((a,b) => (b.ratio ?? -1) - (a.ratio ?? -1));

  const nonEv = brands.filter(b => !b.isEv && b.sw > 0 && b.ratio !== null);
  const leader  = nonEv.length ? nonEv[0]         : null;
  const trailer = nonEv.length ? nonEv[nonEv.length-1] : null;
  const byPresence = [...brands].sort((a,b) => b.sw - a.sw);
  const dominant = byPresence[0];
  const totalSC  = brands.reduce((s,b) => s+b.sc, 0);
  const totalSW  = brands.reduce((s,b) => s+b.sw, 0);

  // Zone breakdown
  const zoneCnt = {{}};
  nearby.forEach(c => zoneCnt[c.z] = (zoneCnt[c.z]||0) + 1);
  const maxZ = Math.max(...Object.values(zoneCnt));

  // City chips (up to 10 nearest)
  const sorted = [...nearby]
    .sort((a,b) => haversine(lastClick.lat,lastClick.lng,a.la,a.lo) -
                   haversine(lastClick.lat,lastClick.lng,b.la,b.lo))
    .slice(0, 12);

  // Max ratio for bar scaling
  const maxRatio = nonEv.length ? Math.max(...nonEv.map(b=>b.ratio), 1) : 1;

  // Build brand rows
  const rows = brands.map(b => {{
    const ratioTxt = b.isEv ? '<span class="ratio-na">—</span>' :
      b.sw === 0 ? '<span class="ratio-na">No SW</span>' :
      `<span class="${{ratioClass(b.ratio)}}">${{b.ratio.toFixed(2)}}</span>`;
    const barW = (b.ratio !== null && !b.isEv)
      ? Math.min(100, (b.ratio / maxRatio) * 100) : 0;
    const barCol = b.ratio >= 1 ? '#22c55e' : b.ratio >= 0.7 ? '#f59e0b' : '#ef4444';
    return `<tr>
      <td><span class="brand-dot" style="background:${{b.col}}"></span>${{b.name}}</td>
      <td style="text-align:right">${{b.sc}}</td>
      <td style="text-align:right">${{b.sw}}</td>
      <td>${{ratioTxt}}</td>
      <td><div class="ratio-bar-wrap"><div class="ratio-bar" style="width:${{barW}}%;background:${{barCol}}"></div></div></td>
    </tr>`;
  }}).join('');

  const leaderCard = leader ? `
    <div class="leader-card">
      <div>
        <span class="badge leader">Leader</span>
        <div class="card-brand" style="color:${{leader.col}};margin-top:4px">${{leader.name}}</div>
        <div class="card-detail">Ratio ${{leader.ratio.toFixed(2)}} · SC ${{leader.sc}} / SW ${{leader.sw}}</div>
      </div>
    </div>` : '';

  const trailerCard = (trailer && trailer !== leader) ? `
    <div class="trailer-card">
      <div>
        <span class="badge trailer">Trailer</span>
        <div class="card-brand" style="color:${{trailer.col}};margin-top:4px">${{trailer.name}}</div>
        <div class="card-detail">Ratio ${{trailer.ratio.toFixed(2)}} · SC ${{trailer.sc}} / SW ${{trailer.sw}}</div>
      </div>
    </div>` : '';

  const zoneHtml = Object.entries(zoneCnt)
    .sort((a,b) => b[1]-a[1])
    .map(([z,n]) => `
      <div class="zone-row">
        <span style="min-width:70px;color:${{ZONE_COLS[z]||'#888'}}">${{z}}</span>
        <div class="zone-bar-wrap"><div class="zone-bar" style="width:${{Math.round(n/maxZ*100)}}%;background:${{ZONE_COLS[z]||'#888'}}"></div></div>
        <span style="color:var(--muted);min-width:28px;text-align:right">${{n}}</span>
      </div>`).join('');

  const chipHtml = sorted.map(c =>
    `<span class="city-chip">${{c.c}}</span>`).join('');

  document.getElementById('panel-body').innerHTML = `
    <div class="summary-grid">
      <div class="kpi"><div class="val">${{nearby.length}}</div><div class="lab">Cities in range</div></div>
      <div class="kpi"><div class="val">${{totalSW}}</div><div class="lab">Total showrooms</div></div>
      <div class="kpi"><div class="val">${{totalSC}}</div><div class="lab">Service centres</div></div>
      <div class="kpi"><div class="val">${{brands.length}}</div><div class="lab">Brands present</div></div>
    </div>

    <div class="section-label">Leaders &amp; Trailers (SC/SW ratio)</div>
    ${{leaderCard}}${{trailerCard}}

    <div class="section-label">All brands — SC / SW / Ratio</div>
    <table class="brand-table">
      <thead><tr>
        <th>Brand</th><th style="text-align:right">SC</th>
        <th style="text-align:right">SW</th><th>Ratio</th><th>Bar</th>
      </tr></thead>
      <tbody>${{rows}}</tbody>
    </table>
    <div style="font-size:10px;color:var(--muted);margin-top:5px">
      Ratio = Service Centres ÷ Showrooms. &ge;1.0 healthy, 0.7–1.0 mild gap, &lt;0.7 deficit. EV brands excluded (no BikeWale SC data).
    </div>

    <div class="section-label">Zone breakdown</div>
    ${{zoneHtml}}

    <div class="section-label">Nearest cities in radius</div>
    <div class="city-chips">${{chipHtml}}</div>
    ${{sorted.length < nearby.length ? `<div style="font-size:10px;color:var(--muted);margin-top:4px">+${{nearby.length-sorted.length}} more cities not shown</div>` : ''}}
  `;
}}

function ratioClass(r) {{
  if (r >= 1.0) return 'ratio-good';
  if (r >= 0.7) return 'ratio-warn';
  return 'ratio-bad';
}}
</script>
</body>
</html>"""

with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
    f.write(HTML)

kb = os.path.getsize(OUTPUT_PATH) // 1024
print(f"  Written: {OUTPUT_PATH}")
print(f"  Size:    {kb} KB")
print(f"  Done — open map_explorer.html in your browser")
