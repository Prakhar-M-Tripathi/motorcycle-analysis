"""
final_dashboard.py — Full Dashboard: Brand Tabs + Model Explainers
-------------------------------------------------------------------
Outputs a single self-contained HTML file with:
  • Overview tab  — all 7 analysis sections, model explainer buttons
  • Per-brand tabs — zone charts, competitive benchmarking, radar profile
  • Interactive model explainers — plain-English + formula for each model

Usage:
    python outputs/final_dashboard.py
    Open: outputs/final_dashboard.html
"""

import json, os, sys, sqlite3, copy
from html import escape as html_escape

try:
    import plotly
    _plotly_js_path = os.path.join(os.path.dirname(plotly.__file__), "package_data", "plotly.min.js")
    with open(_plotly_js_path, encoding="utf-8") as _plotly_js_file:
        PLOTLY_JS = _plotly_js_file.read().replace("</script", "<\\/script")
except (ImportError, OSError):
    print("Plotly Python package is required to build the standalone HTML. Install it with: pip install plotly")
    sys.exit(1)

MAP_PATH = os.path.join(os.path.dirname(__file__), "map_explorer.html")
if not os.path.exists(MAP_PATH):
    print(f"MISSING: {MAP_PATH}\nRun: python outputs/map_explorer.py")
    sys.exit(1)
with open(MAP_PATH, encoding="utf-8") as _map_file:
    MAP_HTML = _map_file.read()
MAP_HTML = MAP_HTML.replace(
    'href="final_dashboard.html" id="back-link"',
    'href="#" id="back-link" onclick="parent.showTab(&quot;overview&quot;); return false"'
)
MAP_SRCDOC = html_escape(MAP_HTML, quote=True)

PROJECT_DIR  = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ANALYSIS_DIR = os.path.join(PROJECT_DIR, "data", "analysis")
DB_PATH      = os.path.join(PROJECT_DIR, "db", "motorcycle_analysis.db")
OUTPUT_PATH  = os.path.join(PROJECT_DIR, "outputs", "final_dashboard.html")

EV_BRANDS_NO_SC = {"ola-electric", "ather"}
BRAND_LIST = ["hero","honda","bajaj","royal-enfield","yamaha","suzuki",
              "ola-electric","ather","jawa"]
BD = {  # brand display names
    "hero":"Hero","honda":"Honda","bajaj":"Bajaj",
    "royal-enfield":"Royal Enfield","yamaha":"Yamaha",
    "suzuki":"Suzuki","ola-electric":"Ola Electric",
    "ather":"Ather","jawa":"Jawa",
}
ZONES = ["North","South","West","Central","East","Northeast"]
BCOL  = {  # brand accent colours
    "hero":"#e74c3c","honda":"#e67e22","bajaj":"#f1c40f",
    "royal-enfield":"#3498db","yamaha":"#9b59b6","suzuki":"#1abc9c",
    "ola-electric":"#ff5722","ather":"#607d8b","jawa":"#795548",
}
ZCOL = {
    "North":"#3b82f6","South":"#22c55e","West":"#f59e0b",
    "East":"#a855f7","Central":"#ef4444","Northeast":"#06b6d4",
}

# ── data loader ────────────────────────────────────────────────────────────
def load(f):
    p = os.path.join(ANALYSIS_DIR, f)
    if not os.path.exists(p):
        print(f"MISSING: {p}\nRun: python analysis/run_all.py"); sys.exit(1)
    with open(p, encoding="utf-8") as fh: return json.load(fh)

print("Loading analysis data...")
kpis    = load("kpis.json")
zones_d = load("zone_ratios.json")
bz_mat  = load("brand_zone_matrix.json")
tier_d  = load("tier_split.json")
neglect = load("neglect_scores.json")
gini    = load("gini.json")
lq      = load("location_quotients.json")
hhi     = load("hhi.json")
moran   = load("moran.json")
pca     = load("pca.json")
clust   = load("clusters.json")
quad    = load("quadrant.json")
qd      = quad["national"]
print("  All files loaded.")

# ── per-brand zone data from DB ───────────────────────────────────────────
conn = sqlite3.connect(DB_PATH)
bz_rows = conn.execute("""
    SELECT brand, zone,
           SUM(CASE WHEN type='service'  THEN count ELSE 0 END) sc,
           SUM(CASE WHEN type='showroom' THEN count ELSE 0 END) sw
    FROM dealers WHERE scrape_date='2026-06-09' AND zone!='Unknown'
    GROUP BY brand, zone
""").fetchall()
brand_marks = ",".join("?" for _ in BRAND_LIST)
geo_city_cnt = conn.execute(
    f"SELECT COUNT(DISTINCT city_slug) FROM dealers WHERE scrape_date=? AND lat IS NOT NULL AND lon IS NOT NULL AND count>0 AND brand IN ({brand_marks})",
    (kpis.get("scrape_date", "2026-06-09"), *BRAND_LIST)
).fetchone()[0]
conn.close()

brand_zone = {}
for brand, zone, sc, sw in bz_rows:
    brand_zone.setdefault(brand, {})[zone] = {
        "sc": sc, "sw": sw,
        "ratio": round(sc/sw, 4) if sw > 0 else None
    }

# ── pre-compute brand_data ────────────────────────────────────────────────
brand_data = {}
for brand in BRAND_LIST:
    bd = {}
    is_ev = brand in EV_BRANDS_NO_SC
    q = next((r for r in quad["national"]   if r["brand"]==brand), {})
    g = next((r for r in gini["rankings"]   if r["brand"]==brand), {})
    h = next((r for r in hhi["rankings"]    if r["brand"]==brand), {})
    bd.update({"sc":q.get("sc",0),"sw":q.get("sw",0),"ratio":q.get("ratio"),
               "size":q.get("size",0),"quadrant":q.get("quadrant","N/A")})
    bd["gini_sc"] = g.get("gini_sc"); bd["gini_sw"] = g.get("gini_sw",0)
    bd["cities"]  = g.get("cities",0)
    bd["hhi_sc"]  = h.get("hhi_sc");  bd["hhi_sw"]  = h.get("hhi_sw",0)
    bd["lq_sc"] = {}; bd["lq_sw"] = {}; bd["lq_sc_lbl"] = {}; bd["lq_sw_lbl"] = {}
    for rec in lq["records"]:
        if rec["brand"] == brand:
            if rec["metric"]=="service":
                bd["lq_sc"][rec["zone"]] = rec["lq"]
                bd["lq_sc_lbl"][rec["zone"]] = rec["label"]
            else:
                bd["lq_sw"][rec["zone"]] = rec["lq"]
                bd["lq_sw_lbl"][rec["zone"]] = rec["label"]
    bd["zones"]   = brand_zone.get(brand, {})
    bd["neglect"] = sorted([r for r in neglect if r.get("brand")==brand],
                           key=lambda r: -r.get("score",0))
    brand_data[brand] = bd

# Competitive normalisation
max_size   = max((bd["size"]   or 0) for bd in brand_data.values()) or 1
max_cities = max((bd["cities"] or 0) for bd in brand_data.values()) or 1
MAX_RATIO  = 3.2   # Bajaj ceiling
non_ev_ranked = sorted(
    [(b, v["ratio"] or 0) for b, v in brand_data.items()
     if b not in EV_BRANDS_NO_SC and v["ratio"] is not None],
    key=lambda x: -x[1]
)
for brand, bd in brand_data.items():
    is_ev = brand in EV_BRANDS_NO_SC
    r = bd["ratio"] or 0
    lq_present = sum(1 for v in bd["lq_sw"].values() if v and v >= 0.75)
    bd["radar"] = {
        "Service Balance":        round(min(r, MAX_RATIO)/MAX_RATIO, 3) if not is_ev else 0,
        "Network Scale":          round(bd["size"]/max_size, 3),
        "Distribution Equality":  round(1-(bd["gini_sw"] or 0), 3),
        "City Reach":             round(bd["cities"]/max_cities, 3),
        "Zone Coverage":          round(lq_present/6, 3),
    }
    bd["ratio_rank"] = next((i+1 for i,(b,_) in enumerate(non_ev_ranked) if b==brand), None)
    bd["n_ranked"]   = len(non_ev_ranked)

# ── colour helpers ─────────────────────────────────────────────────────────
def rc(r):
    if r is None: return "#52525b"
    if r >= 1.0:  return "#22c55e"
    if r >= 0.70: return "#fbbf24"
    return "#ef4444"

def lq_col(v):
    if v is None: return "#52525b"
    if v > 1.25:  return "#22c55e"
    if v < 0.75:  return "#ef4444"
    return "#fbbf24"

def nc(s):
    if s > 70: return "#ef4444"
    if s > 50: return "#fbbf24"
    return "#22c55e"

def jd(obj): return json.dumps(obj)

BASE_LAYOUT = {
    "paper_bgcolor":"#18181b","plot_bgcolor":"#18181b",
    "font":{"color":"#a1a1aa","family":"Segoe UI, Arial, sans-serif","size":11},
    "showlegend":False,"margin":{"l":10,"r":10,"t":10,"b":10},
}

def bl(**kw):
    lo = copy.deepcopy(BASE_LAYOUT)
    lo.update(kw)
    return lo

def ax(title="", **kw):
    d = {"gridcolor":"#27272a","zerolinecolor":"#27272a","color":"#a1a1aa"}
    if title: d["title"] = {"text":title,"font":{"color":"#71717a","size":10}}
    d.update(kw)
    return d


# ═══════════════════════════════════════════════════════════════════════════
# OVERVIEW CHARTS
# ═══════════════════════════════════════════════════════════════════════════

z_names  = [r["zone"]      for r in zones_d]
z_ratios = [r["avg_ratio"] for r in zones_d]

leakage = load("revenue_leakage.json")
leak_brands = leakage["by_brand"]
leak_zones = leakage["by_zone"]
leak_brand_labels = [BD.get(r["brand"], r["brand"]) for r in leak_brands]
leak_zone_labels = [r["zone"] for r in leak_zones]
C_LEAK_BRAND = jd({"data":[{"type":"bar","orientation":"h",
    "x":[r["leakage_cr"] for r in leak_brands],"y":leak_brand_labels,
    "marker":{"color":"#ef4444"},"text":[f'{r["leakage_cr"]:.1f}' for r in leak_brands],
    "textposition":"outside","cliponaxis":False}],
    "layout":bl(margin={"l":125,"r":40,"t":10,"b":38},
    xaxis=ax("Indicative proxy (Rs. crore)", rangemode="tozero"),yaxis=ax(automargin=True))})
C_LEAK_ZONE = jd({"data":[{"type":"bar","x":leak_zone_labels,
    "y":[r["leakage_cr"] for r in leak_zones],
    "marker":{"color":[ZCOL.get(z,"#71717a") for z in leak_zone_labels]},
    "text":[f'{r["leakage_cr"]:.1f}' for r in leak_zones],
    "textposition":"outside","cliponaxis":False}],
    "layout":bl(margin={"l":45,"r":20,"t":10,"b":42},
    yaxis=ax("Indicative proxy (Rs. crore)", rangemode="tozero"),xaxis=ax())})

# The available correlation.json is a manually populated demonstration, not
# source-backed FADA data. Do not render it as empirical evidence.
brand_ranked = sorted([r for r in qd if r.get("brand") not in EV_BRANDS_NO_SC and r.get("ratio") is not None], key=lambda r:r["ratio"])
C_BRAND_RATIO = jd({"data":[{"type":"bar","orientation":"h",
    "x":[r["ratio"] for r in brand_ranked],
    "y":[BD.get(r["brand"],r["brand"]) for r in brand_ranked],
    "marker":{"color":[rc(r["ratio"]) for r in brand_ranked]},
    "text":[f'{r["ratio"]:.2f}' for r in brand_ranked],
    "textposition":"outside","cliponaxis":False}],
    "layout":bl(margin={"l":120,"r":55,"t":10,"b":38},
    xaxis=ax("National SC / SW Ratio",rangemode="tozero"),yaxis=ax(automargin=True),
    shapes=[{"type":"line","x0":1,"x1":1,"y0":-0.5,"y1":len(brand_ranked)-0.5,
             "line":{"color":"#71717a","dash":"dot"}}])})
C_BRAND_SIZE = jd({"data":[
    {"type":"bar","name":"Service centres","x":[BD.get(r["brand"],r["brand"]) for r in qd],
     "y":[r["sc"] for r in qd],"marker":{"color":"#22c55e"}},
    {"type":"bar","name":"Showrooms","x":[BD.get(r["brand"],r["brand"]) for r in qd],
     "y":[r["sw"] for r in qd],"marker":{"color":"#3b82f6"}}],
    "layout":bl(barmode="group",showlegend=True,margin={"l":55,"r":15,"t":25,"b":65},
    yaxis=ax("Locations"),xaxis=ax(tickangle=-25),
    legend={"orientation":"h","y":1.12,"x":0,"font":{"size":10}})})

C_ZONE = jd({"data":[{"type":"bar","orientation":"h","x":z_ratios,"y":z_names,
    "marker":{"color":[rc(r) for r in z_ratios]},
    "text":[f"{r:.2f}" for r in z_ratios],"textposition":"outside","cliponaxis":False}],
    "layout":bl(margin={"l":90,"r":60,"t":10,"b":38},
        xaxis=ax("SC / SW Ratio",range=[0,max(z_ratios)*1.3]),yaxis=ax(automargin=True),
        shapes=[{"type":"line","x0":1,"x1":1,"y0":-0.5,"y1":5.5,
                 "line":{"color":"#52525b","dash":"dot","width":1}}])})

bz_labels = [BD.get(b,b) for b in bz_mat["brands"]]
C_HEAT  = jd({"data":[{"type":"heatmap","z":bz_mat["values"],
    "x":bz_mat["zones"],"y":bz_labels,
    "text":[[f"{v:.2f}" for v in row] for row in bz_mat["values"]],
    "texttemplate":"%{text}","textfont":{"size":9,"color":"#fff"},
    "colorscale":[[0,"#991b1b"],[0.3,"#78350f"],[0.55,"#374151"],[1,"#22c55e"]],
    "zmin":0.2,"zmax":3.5,"showscale":False}],
    "layout":bl(margin={"l":115,"r":12,"t":10,"b":42},
        xaxis=ax(),yaxis=ax(automargin=True))})


g_rnk  = gini["rankings"]
C_GINI = jd({"data":[
    {"type":"bar","orientation":"h","name":"Showroom Gini",
     "x":[r["gini_sw"] for r in g_rnk],
     "y":[BD.get(r["brand"],r["brand"]) for r in g_rnk],
     "marker":{"color":"#3b82f6","opacity":0.85},
     "text":[f"{r['gini_sw']:.3f}" for r in g_rnk],"textposition":"outside","cliponaxis":False},
    {"type":"bar","orientation":"h","name":"Service Ctr Gini",
     "x":[r["gini_sc"] or 0 for r in g_rnk],
     "y":[BD.get(r["brand"],r["brand"]) for r in g_rnk],
     "marker":{"color":"#22c55e","opacity":0.85},
     "text":[f"{r['gini_sc']:.3f}" if r["gini_sc"] else "N/A" for r in g_rnk],
     "textposition":"outside","cliponaxis":False},
  ],"layout":bl(barmode="group",showlegend=True,
    margin={"l":120,"r":68,"t":32,"b":40},
    xaxis=ax("Gini Coefficient",range=[0,1.0]),yaxis=ax(automargin=True),
    legend={"orientation":"h","y":1.1,"x":0,"font":{"size":10},"bgcolor":"rgba(0,0,0,0)"},
    shapes=[{"type":"line","x0":0.4,"x1":0.4,"y0":-0.5,"y1":len(g_rnk)-0.5,
             "line":{"color":"#52525b","dash":"dot","width":1}},
            {"type":"line","x0":0.6,"x1":0.6,"y0":-0.5,"y1":len(g_rnk)-0.5,
             "line":{"color":"#52525b","dash":"dash","width":1}}])})

hhi_r = hhi["rankings"]
C_HHI = jd({"data":[
    {"type":"bar","name":"HHI Showrooms","x":[BD.get(r["brand"],r["brand"]) for r in hhi_r],
     "y":[r["hhi_sw"] for r in hhi_r],"marker":{"color":"#3b82f6","opacity":0.85},
     "text":[str(round(r["hhi_sw"])) for r in hhi_r],"textposition":"outside","cliponaxis":False},
    {"type":"bar","name":"HHI Service Ctrs","x":[BD.get(r["brand"],r["brand"]) for r in hhi_r],
     "y":[r["hhi_sc"] or 0 for r in hhi_r],"marker":{"color":"#22c55e","opacity":0.85},
     "text":[str(round(r["hhi_sc"])) if r["hhi_sc"] else "N/A" for r in hhi_r],
     "textposition":"outside","cliponaxis":False},
  ],"layout":bl(barmode="group",showlegend=True,
    margin={"l":55,"r":20,"t":32,"b":48},
    xaxis=ax(),yaxis=ax("HHI  (lower = more dispersed)",range=[0,max(r["hhi_sw"] for r in hhi_r)*1.3]),
    legend={"orientation":"h","y":1.1,"x":0,"font":{"size":10},"bgcolor":"rgba(0,0,0,0)"},
    shapes=[{"type":"line","x0":-0.5,"x1":len(hhi_r)-0.5,"y0":1500,"y1":1500,
             "line":{"color":"#fbbf24","dash":"dot","width":1}}],
    annotations=[{"x":len(hhi_r)-1,"y":1500,"text":"1,500 moderate threshold",
                  "showarrow":False,"font":{"size":9,"color":"#fbbf24"},
                  "xanchor":"right","yanchor":"bottom"}])})

lq_sc_mat = lq["sc_matrix"]
lq_labels = [BD.get(b,b) for b in lq["brands"]]
C_LQ = jd({"data":[{"type":"heatmap","z":lq_sc_mat,
    "x":lq["zones"],"y":lq_labels,
    "text":[[f"{v:.2f}" for v in row] for row in lq_sc_mat],
    "texttemplate":"%{text}","textfont":{"size":9,"color":"#fff"},
    "colorscale":[[0,"#991b1b"],[0.3,"#b45309"],[0.5,"#374151"],
                  [0.7,"#166534"],[1,"#22c55e"]],
    "zmin":0.3,"zmax":2.0,"showscale":True,
    "colorbar":{"thickness":10,"len":0.8,"tickfont":{"size":9,"color":"#71717a"},
                "title":{"text":"LQ","font":{"size":9,"color":"#71717a"}}}}],
    "layout":bl(margin={"l":115,"r":60,"t":10,"b":42},
        xaxis=ax(),yaxis=ax(automargin=True))})

mz = list(moran["by_zone"].keys())
mv = [moran["by_zone"][z] for z in mz]
C_MORAN = jd({"data":[{"type":"bar","x":mz,"y":mv,
    "marker":{"color":["#22c55e" if v>0.05 else "#fbbf24" if v>0 else "#ef4444" for v in mv]},
    "text":[f"{v:.4f}" for v in mv],"textposition":"outside","cliponaxis":False}],
    "layout":bl(margin={"l":55,"r":20,"t":10,"b":42},
        xaxis=ax(),yaxis=ax("Moran's I",range=[min(mv)*1.4,max(mv)*1.6]),
        shapes=[{"type":"line","x0":-0.5,"x1":len(mz)-0.5,"y0":0,"y1":0,
                 "line":{"color":"#52525b","dash":"dash","width":1}}])})

pca_traces = []
for zone_n, col in ZCOL.items():
    pts = [c for c in pca["cities"] if c["zone"]==zone_n]
    if not pts: continue
    pca_traces.append({"type":"scattergl","mode":"markers","name":zone_n,
        "x":[c["pc1"] for c in pts],"y":[c["pc2"] for c in pts],
        "text":[f"{c['city']} ({c['dom_brand']})" for c in pts],
        "hovertemplate":"%{text}<extra></extra>",
        "marker":{"size":5,"color":col,"opacity":0.55,"line":{"width":0}}})
var1 = round(pca["variance_explained"][0]*100,1)
var2 = round(pca["variance_explained"][1]*100,1)
C_PCA = jd({"data":pca_traces,"layout":bl(showlegend=True,
    margin={"l":55,"r":20,"t":10,"b":90},
    xaxis=ax(f"PC1  ({var1}% variance)"),yaxis=ax(f"PC2  ({var2}% variance)"),
    legend={"orientation":"h","y":-0.2,"x":0,"font":{"size":10},"bgcolor":"rgba(0,0,0,0)"})})

cs = clust["cluster_summary"]
def clbl(s): return f"Mega Hub ({s['n_cities']} cities)" if s["avg_sw"]>50 else f"Regular Market ({s['n_cities']} cities)"
C_CLUST = jd({"data":[
    {"type":"bar","name":"Avg Showrooms","x":[clbl(s) for s in cs],"y":[s["avg_sw"] for s in cs],
     "marker":{"color":"#3b82f6","opacity":0.85},"text":[f"{s['avg_sw']:.1f}" for s in cs],
     "textposition":"outside","cliponaxis":False},
    {"type":"bar","name":"Avg Service Ctrs","x":[clbl(s) for s in cs],"y":[s["avg_sc"] for s in cs],
     "marker":{"color":"#22c55e","opacity":0.85},"text":[f"{s['avg_sc']:.1f}" for s in cs],
     "textposition":"outside","cliponaxis":False},
  ],"layout":bl(barmode="group",showlegend=True,
    margin={"l":55,"r":20,"t":32,"b":90},
    xaxis=ax(tickangle=-10),yaxis=ax("Avg count per city",
        range=[0,max(s["avg_sw"] for s in cs)*1.3]),
    legend={"orientation":"h","y":1.1,"x":0,"font":{"size":10},"bgcolor":"rgba(0,0,0,0)"})})

q_r_thr = quad["ratio_threshold"]
q_s_thr = quad["size_threshold"]
q_max_r = 3.9
q_max_s = max(r["size"] for r in qd)*1.15
QCOL = {"Q1":"#22c55e","Q2":"#f59e0b","Q3":"#3b82f6","Q4":"#ef4444"}
quad_tr_map = {}
for r in qd:
    qk = r["quadrant"][:2]
    if qk not in quad_tr_map:
        quad_tr_map[qk] = {"type":"scatter","mode":"markers+text","name":r["quadrant"],
            "x":[],"y":[],"text":[],"textposition":[],
            "marker":{"size":14,"color":QCOL.get(qk,"#888"),
                      "opacity":0.9,"line":{"color":"#18181b","width":1.5}},
            "textfont":{"size":9,"color":"#e4e4e7"}}
    quad_tr_map[qk]["x"].append(round(min(r["ratio"] or 0, 3.8),3))
    quad_tr_map[qk]["y"].append(r["size"])
    quad_tr_map[qk]["text"].append(BD.get(r["brand"],r["brand"]))
    quad_tr_map[qk]["textposition"].append("top center" if r["size"]>q_s_thr else "bottom center")
C_QUAD = jd({"data":list(quad_tr_map.values()),"layout":bl(showlegend=True,
    margin={"l":65,"r":20,"t":10,"b":90},
    xaxis=ax("SC / SW Ratio  (left = service-deficient)",range=[-0.1,q_max_r]),
    yaxis=ax("Total Network Size (SC + SW)",range=[0,q_max_s]),
    legend={"orientation":"h","y":-0.2,"x":0,"font":{"size":10},"bgcolor":"rgba(0,0,0,0)"},
    shapes=[
        {"type":"line","x0":q_r_thr,"x1":q_r_thr,"y0":0,"y1":q_max_s,
         "line":{"color":"#3f3f46","dash":"dot","width":1.5}},
        {"type":"line","x0":0,"x1":q_max_r,"y0":q_s_thr,"y1":q_s_thr,
         "line":{"color":"#3f3f46","dash":"dot","width":1.5}},
        {"type":"rect","x0":q_r_thr,"x1":q_max_r,"y0":q_s_thr,"y1":q_max_s,
         "fillcolor":"rgba(34,197,94,0.04)","line":{"width":0}},
        {"type":"rect","x0":-0.1,"x1":q_r_thr,"y0":q_s_thr,"y1":q_max_s,
         "fillcolor":"rgba(245,158,11,0.04)","line":{"width":0}},
        {"type":"rect","x0":-0.1,"x1":q_r_thr,"y0":0,"y1":q_s_thr,
         "fillcolor":"rgba(239,68,68,0.04)","line":{"width":0}},
    ],
    annotations=[
        {"x":q_max_r*0.92,"y":q_max_s*0.96,"text":"Q1 Leaders","showarrow":False,
         "font":{"size":9,"color":"rgba(34,197,94,0.55)"}},
        {"x":0.05,"y":q_max_s*0.96,"text":"Q2 Overextended","showarrow":False,
         "font":{"size":9,"color":"rgba(245,158,11,0.55)"},"xanchor":"left"},
        {"x":0.05,"y":q_s_thr*0.12,"text":"Q4 Struggling","showarrow":False,
         "font":{"size":9,"color":"rgba(239,68,68,0.55)"},"xanchor":"left"},
        {"x":q_max_r*0.92,"y":q_s_thr*0.12,"text":"Q3 Niche Strong","showarrow":False,
         "font":{"size":9,"color":"rgba(59,130,246,0.55)"}},
    ])})

neg_top    = sorted(neglect, key=lambda r: r["score"], reverse=True)[:15]
neg_labels = [r["label"] for r in neg_top]
neg_scores = [r["score"] for r in neg_top]
neg_ratios = [r.get("ratio",0) for r in neg_top]
C_NEG = jd({"data":[{"type":"bar","orientation":"h","x":neg_scores,"y":neg_labels,
    "marker":{"color":[nc(s) for s in neg_scores]},
    "text":[f"{s:.0f}  |  ratio {r:.2f}" for s,r in zip(neg_scores,neg_ratios)],
    "textposition":"outside","cliponaxis":False}],
    "layout":bl(margin={"l":145,"r":105,"t":10,"b":38},
        xaxis=ax("Neglect Score",range=[0,max(neg_scores)*1.35 if neg_scores else 100]),
        yaxis=ax(automargin=True))})

trs = tier_d
C_TIER = jd({"data":[
    {"type":"bar","name":"Service Ctrs","x":[r["tier"] for r in trs],"y":[r["service_count"] for r in trs],
     "marker":{"color":"#22c55e","opacity":0.85},
     "text":[f"{r['service_count']:,}" for r in trs],"textposition":"outside","cliponaxis":False},
    {"type":"bar","name":"Showrooms","x":[r["tier"] for r in trs],"y":[r["showroom_count"] for r in trs],
     "marker":{"color":"#3b82f6","opacity":0.85},
     "text":[f"{r['showroom_count']:,}" for r in trs],"textposition":"outside","cliponaxis":False},
  ],"layout":bl(barmode="group",showlegend=True,
    margin={"l":55,"r":20,"t":32,"b":42},
    xaxis=ax(),yaxis=ax("Count (all brands)"),
    legend={"orientation":"h","y":1.1,"x":0,"font":{"size":10},"bgcolor":"rgba(0,0,0,0)"})})


# ═══════════════════════════════════════════════════════════════════════════
# PER-BRAND CHART BUILDERS
# ═══════════════════════════════════════════════════════════════════════════

brand_charts = {}   # brand -> dict of chart JSON strings

for brand in BRAND_LIST:
    bd    = brand_data[brand]
    is_ev = brand in EV_BRANDS_NO_SC
    col   = BCOL[brand]
    bc    = {}

    # 1. Zone ratio bar (SC/SW per zone for this brand)
    zd    = bd["zones"]
    all_z = ZONES
    z_r   = [zd.get(z,{}).get("ratio") for z in all_z]
    z_sc  = [zd.get(z,{}).get("sc",0)  for z in all_z]
    z_sw  = [zd.get(z,{}).get("sw",0)  for z in all_z]
    hover_t = [f"{z}<br>SC: {sc:,}  SW: {sw:,}" for z,sc,sw in zip(all_z,z_sc,z_sw)]

    bc["zone"] = jd({"data":[
        {"type":"bar","orientation":"h",
         "x":[r if r else 0 for r in z_r],"y":all_z,
         "marker":{"color":[rc(r) for r in z_r],"opacity":0.88},
         "text":[f"{r:.2f}" if r else "N/A" for r in z_r],
         "hovertext":hover_t,"hovertemplate":"%{hovertext}<extra></extra>",
         "textposition":"outside","cliponaxis":False}],
        "layout":bl(margin={"l":85,"r":60,"t":10,"b":38},
            xaxis=ax("SC / SW Ratio",range=[0,(max((r for r in z_r if r), default=1))*1.35]),
            yaxis=ax(automargin=True),
            shapes=[{"type":"line","x0":1,"x1":1,"y0":-0.5,"y1":5.5,
                     "line":{"color":"#52525b","dash":"dot","width":1}}])})

    # 2. Competitive SC/SW ratio bar (all brands, this one highlighted)
    all_r = sorted([(b, brand_data[b]["ratio"] or 0, BCOL[b]) for b in BRAND_LIST
                    if brand_data[b]["ratio"] is not None], key=lambda x: x[1])
    cr_colors = [col if b==brand else "#2d2d30" for b,_,_ in all_r]
    cr_text   = [f"{'→ ' if b==brand else ''}{BD.get(b,b)}" for b,_,_ in all_r]
    bc["comp_ratio"] = jd({"data":[
        {"type":"bar","orientation":"h",
         "x":[v for _,v,_ in all_r],"y":[BD.get(b,b) for b,_,_ in all_r],
         "marker":{"color":cr_colors},
         "text":[f"{v:.2f}" for _,v,_ in all_r],
         "textposition":"outside","cliponaxis":False}],
        "layout":bl(margin={"l":115,"r":58,"t":10,"b":38},
            xaxis=ax("SC / SW Ratio",range=[0,max(v for _,v,_ in all_r)*1.3]),
            yaxis=ax(automargin=True),
            shapes=[{"type":"line","x0":1,"x1":1,"y0":-0.5,"y1":len(all_r)-0.5,
                     "line":{"color":"#52525b","dash":"dot","width":1}}])})

    # 3. LQ by zone (SC for non-EV, SW for EV)
    lq_dict = bd["lq_sc"] if not is_ev else bd["lq_sw"]
    lq_lbl  = bd["lq_sc_lbl"] if not is_ev else bd["lq_sw_lbl"]
    if lq_dict:
        lq_zs = ZONES
        lq_vs = [lq_dict.get(z) for z in lq_zs]
        bc["lq"] = jd({"data":[
            {"type":"bar","x":lq_zs,"y":[v or 0 for v in lq_vs],
             "marker":{"color":[lq_col(v) for v in lq_vs],"opacity":0.88},
             "text":[f"{v:.2f}" if v else "N/A" for v in lq_vs],
             "hovertext":[lq_lbl.get(z,"") for z in lq_zs],
             "hovertemplate":"%{x}: LQ %{y:.2f}<br>%{hovertext}<extra></extra>",
             "textposition":"outside","cliponaxis":False}],
            "layout":bl(margin={"l":55,"r":20,"t":10,"b":42},
                xaxis=ax(),yaxis=ax(f"{'SC' if not is_ev else 'SW'} Location Quotient",
                    range=[0,max(v for v in lq_vs if v)*1.35 if any(lq_vs) else 2]),
                shapes=[
                    {"type":"line","x0":-0.5,"x1":5.5,"y0":1.25,"y1":1.25,
                     "line":{"color":"#22c55e","dash":"dot","width":1}},
                    {"type":"line","x0":-0.5,"x1":5.5,"y0":0.75,"y1":0.75,
                     "line":{"color":"#ef4444","dash":"dot","width":1}},
                    {"type":"line","x0":-0.5,"x1":5.5,"y0":1.0,"y1":1.0,
                     "line":{"color":"#52525b","dash":"dash","width":1}},
                ],
                annotations=[
                    {"x":5.4,"y":1.25,"text":"Over (1.25)","showarrow":False,
                     "font":{"size":9,"color":"#22c55e"},"xanchor":"right","yanchor":"bottom"},
                    {"x":5.4,"y":0.75,"text":"Under (0.75)","showarrow":False,
                     "font":{"size":9,"color":"#ef4444"},"xanchor":"right","yanchor":"top"},
                ])})

    # 4. Competitive network size bar
    all_sizes = sorted([(b, brand_data[b]["size"]) for b in BRAND_LIST], key=lambda x: x[1])
    sz_colors = [col if b==brand else "#2d2d30" for b,_ in all_sizes]
    bc["comp_size"] = jd({"data":[
        {"type":"bar","orientation":"h",
         "x":[s for _,s in all_sizes],"y":[BD.get(b,b) for b,_ in all_sizes],
         "marker":{"color":sz_colors},
         "text":[f"{s:,}" for _,s in all_sizes],
         "textposition":"outside","cliponaxis":False}],
        "layout":bl(margin={"l":115,"r":70,"t":10,"b":38},
            xaxis=ax("Total Network Size (SC + SW)"),yaxis=ax(automargin=True))})

    # 5. Radar chart
    dims = list(bd["radar"].keys())
    vals = list(bd["radar"].values())
    # Build all-brand traces for context (thin grey), then this brand on top
    radar_all_traces = []
    for ob in BRAND_LIST:
        if ob == brand: continue
        ov = list(brand_data[ob]["radar"].values())
        radar_all_traces.append({
            "type":"scatterpolar","mode":"lines",
            "name":BD.get(ob,ob),
            "r": ov + [ov[0]],
            "theta": dims + [dims[0]],
            "line":{"color":"#2d2d30","width":1},
            "fill":"none","showlegend":False,
            "hoverinfo":"skip",
        })
    radar_all_traces.append({
        "type":"scatterpolar","mode":"lines+markers",
        "name":BD.get(brand,brand),
        "r": vals + [vals[0]],
        "theta": dims + [dims[0]],
        "line":{"color":col,"width":2.5},
        "fill":"toself","fillcolor":f"{col}22",
        "marker":{"size":6,"color":col},
        "showlegend":True,
    })
    bc["radar"] = jd({"data":radar_all_traces,"layout":{
        "paper_bgcolor":"#18181b","plot_bgcolor":"#18181b",
        "font":{"color":"#a1a1aa","family":"Segoe UI, Arial, sans-serif","size":10},
        "polar":{
            "bgcolor":"#1c1c1f",
            "radialaxis":{"visible":True,"range":[0,1],"gridcolor":"#2d2d30",
                          "tickfont":{"size":9},"color":"#52525b"},
            "angularaxis":{"gridcolor":"#2d2d30","color":"#71717a","tickfont":{"size":10}},
        },
        "showlegend":True,
        "legend":{"orientation":"h","y":-0.12,"x":0.5,"xanchor":"center",
                  "font":{"size":9},"bgcolor":"rgba(0,0,0,0)"},
        "margin":{"l":50,"r":50,"t":20,"b":60},
    }})

    brand_charts[brand] = bc


# ═══════════════════════════════════════════════════════════════════════════
# MODEL EXPLAINERS  (Python dict → JSON → JS)
# ═══════════════════════════════════════════════════════════════════════════

EXPLAINERS = {
    "ratio": {
        "title": "SC / SW Ratio — Core Metric",
        "icon": "⚖️",
        "plain": (
            "For every showroom a brand opens, how many service centres has it set up? "
            "A ratio of 1.0 means perfect balance — one service centre for every showroom. "
            "A ratio of 0.5 means they have half as many service centres as showrooms: "
            "buyers can easily find a dealer but then struggle to get the bike serviced. "
            "A ratio above 1.0 (like Bajaj's 3.2) means a brand has invested heavily in service — "
            "its after-sales network is stronger than its retail network."
        ),
        "formula": "SC / SW Ratio = Total Service Centres ÷ Total Showrooms",
        "formula_detail": "Computed at national, zone, and city level. For zone-level: sum all SCs in that zone for that brand, divide by sum of all showrooms.",
        "scale": [
            {"range": "≥ 1.0", "label": "Healthy — service-sufficient", "color": "#22c55e"},
            {"range": "0.70 – 1.0", "label": "Mild gap — worth monitoring", "color": "#fbbf24"},
            {"range": "< 0.70", "label": "Serious deficit — customer pain likely", "color": "#ef4444"},
        ],
        "why": "A brand with ratio 0.38 (Hero) is selling 2.6× more bikes than it can service. Customers in under-served cities may face long wait times, switch brands, or travel far — all of which hurt loyalty and repeat purchases."
    },
    "gini": {
        "title": "Gini Coefficient — Network Inequality",
        "icon": "📊",
        "plain": (
            "Borrowed from economics, where it measures income inequality across households, "
            "Gini here tells us how evenly spread a brand's dealers are across all cities. "
            "If Hero had 90% of its service centres in just 5 big cities, that would be a very high Gini "
            "— deeply unfair to the other 700+ cities. "
            "A Gini of 0 = every city gets exactly its fair share. "
            "A Gini of 1 = everything is concentrated in one city."
        ),
        "formula": "G = (2 × Σ i·yᵢ) / (n × Σ yᵢ) − (n+1)/n",
        "formula_detail": "Where yᵢ is the dealer count of city i (sorted ascending, 1-indexed), and n = total number of cities with presence. This is the standard discrete Lorenz curve area method.",
        "scale": [
            {"range": "0.00 – 0.35", "label": "Fairly equal distribution", "color": "#22c55e"},
            {"range": "0.35 – 0.60", "label": "Moderately unequal", "color": "#fbbf24"},
            {"range": "0.60 – 1.00", "label": "Very unequal — metro-heavy", "color": "#ef4444"},
        ],
        "why": "Suzuki's showroom Gini of 0.73 is high — it concentrates showrooms in very few cities. Jawa's service Gini of 0.13 is low but the brand is small overall. Comparing Gini SC vs Gini SW reveals whether a brand is more selective about where it services vs where it sells."
    },
    "lq": {
        "title": "Location Quotient (LQ) — Regional Specialisation",
        "icon": "🗺️",
        "plain": (
            "If Yamaha has 30% of its service centres in North India, but North India accounts for only 25% "
            "of all service centres nationally, then Yamaha is over-concentrated in the North — its LQ = 30/25 = 1.2. "
            "An LQ above 1.25 means a brand disproportionately focuses its network on that zone. "
            "An LQ below 0.75 is a red flag — the brand is structurally absent in that region "
            "relative to what a 'proportional' presence would look like."
        ),
        "formula": "LQ(brand, zone) = (SC_brand_zone / SC_brand_national) ÷ (SC_all_zone / SC_all_national)",
        "formula_detail": "Computes the brand's zone share divided by the industry's zone share. The same formula is applied for showrooms (SW LQ) separately.",
        "scale": [
            {"range": "LQ > 1.25", "label": "Over-concentrated in this zone", "color": "#22c55e"},
            {"range": "0.75 – 1.25", "label": "Proportional presence", "color": "#fbbf24"},
            {"range": "LQ < 0.75", "label": "Under-present — strategic gap", "color": "#ef4444"},
        ],
        "why": "Suzuki's West LQ of 1.56 means it has 56% more service presence in West India than average. Its East LQ of 0.57 means it's barely present there. This asymmetry likely reflects historical distribution strategy and can guide where to invest next."
    },
    "hhi": {
        "title": "HHI — City-Level Network Concentration",
        "icon": "🏙️",
        "plain": (
            "Used by competition regulators to measure market concentration, HHI here checks whether "
            "a brand's dealers are packed into a few large cities. "
            "Each city's share of the brand's total dealer count is squared and then summed up. "
            "Squaring penalises extreme concentrations heavily. "
            "If a brand had ALL dealers in one city, HHI = 10,000 (maximum monopoly). "
            "If spread perfectly across 10,000 equal cities, HHI ≈ 1. "
            "All Indian motorcycle brands score 'Dispersed' (< 1,500), meaning "
            "no brand is dangerously concentrated in just a few cities."
        ),
        "formula": "HHI = Σᵢ (countᵢ / total_count)² × 10,000",
        "formula_detail": "Where countᵢ = number of dealers in city i, total_count = sum across all cities for that brand. Computed separately for service centres and showrooms.",
        "scale": [
            {"range": "HHI < 1,500", "label": "Dispersed — healthy geographic spread", "color": "#22c55e"},
            {"range": "1,500 – 2,500", "label": "Moderately concentrated", "color": "#fbbf24"},
            {"range": "HHI > 2,500", "label": "Highly concentrated — metro-dependent", "color": "#ef4444"},
        ],
        "why": "All brands are dispersed by HHI, which is a good sign — no brand relies on just 2-3 cities for its entire dealer network. However, HHI doesn't capture zone-level imbalances (that's what LQ does). Yamaha's SW HHI of 606 is the highest — more showroom concentration than others despite being dispersed overall."
    },
    "moran": {
        "title": "Moran's I — Spatial Autocorrelation",
        "icon": "🔍",
        "plain": (
            "Asks: are cities with poor SC/SW ratios geographically clustered — i.e., are bad cities "
            "neighbours of other bad cities? "
            "A strong positive Moran's I means the entire North-East corridor (for example) is "
            "underserved as a bloc, which is much more serious than scattered individual bad cities. "
            "A near-zero Moran's I (like our 0.026) means the gaps are essentially random in space — "
            "no systematic regional crisis. "
            "A negative value would mean bad and good cities are interleaved like a chessboard."
        ),
        "formula": "I = (N/W) × [Σᵢ Σⱼ wᵢⱼ(xᵢ−x̄)(xⱼ−x̄)] / Σᵢ(xᵢ−x̄)²",
        "formula_detail": "N = number of cities, W = sum of all spatial weights, wᵢⱼ = 1 if cities i and j are within 150 km (binary contiguity, row-standardised), xᵢ = SC/SW ratio of city i, x̄ = mean ratio. P-value computed via 999-permutation randomisation test.",
        "scale": [
            {"range": "I > 0.30  (p<0.05)", "label": "Strong spatial clustering of gaps", "color": "#ef4444"},
            {"range": "I 0.10–0.30 (p<0.05)", "label": "Moderate geographic clustering", "color": "#fbbf24"},
            {"range": "I < 0.10  or  p≥0.05", "label": "No significant spatial pattern", "color": "#22c55e"},
        ],
        "why": f"Our result: I = {moran['moran_i']:.4f}, p = {moran['p_value']:.3f} — NOT significant. This means network service gaps are randomly scattered geographically, not forming regional blocs. Policy implication: brand-by-brand fixes work better than zone-level interventions."
    },
    "pca": {
        "title": "PCA — Principal Component Analysis",
        "icon": "🔬",
        "plain": (
            "Each of the 774 cities in our dataset has 18 numbers describing it "
            "(service centre count + showroom count for each of the 9 brands). "
            "PCA compresses all 18 numbers into 2 'super-scores' (Principal Components) "
            "that together capture as much variation as possible. "
            "Think of it as finding the best 2D shadow of an 18-dimensional object. "
            "Cities that appear close together in the PCA scatter plot have similar dealer profiles "
            "across all brands — even if their individual brand counts differ."
        ),
        "formula": "Decompose covariance matrix Σ = UΛUᵀ; PC scores = X_standardised × U",
        "formula_detail": f"Explained variance ratio = λₖ / Σλᵢ, where λ = eigenvalues. PC1 captures {var1}% of all variation — mainly driven by Hero, Honda, and Bajaj showroom scale. PC2 captures {var2}% — driven by Bajaj service centres and EV showrooms.",
        "scale": [
            {"range": f"PC1 = {var1}%", "label": "Mass-market brand density axis", "color": "#22c55e"},
            {"range": f"PC2 = {var2}%", "label": "EV vs legacy service axis", "color": "#3b82f6"},
            {"range": "Right in plot = high", "label": "Larger, more complete networks", "color": "#fbbf24"},
        ],
        "why": "The extreme outliers in the PCA scatter (top-right) are the 6 mega-hub cities: Mumbai, Delhi, Bengaluru, etc. The tight cluster bottom-left represents 750+ smaller towns with thin coverage. The zone colouring shows North has the densest cluster — most 'average-sized' cities."
    },
    "kmeans": {
        "title": "K-Means Clustering — City Archetypes",
        "icon": "🗂️",
        "plain": (
            "Groups the 774 cities into clusters so that cities within the same group are "
            "as similar as possible in their full dealer profile across all 9 brands. "
            "Like sorting students into ability groups — the algorithm finds natural groupings. "
            "We tested k=2 to k=8 groups and picked k=2 because it had the best "
            "'silhouette score' (0.89 out of 1.0), meaning the groups are very clearly separated."
        ),
        "formula": "Minimise Σₖ Σᵢ∈Cₖ ‖xᵢ − μₖ‖²   (where μₖ = cluster centroid)",
        "formula_detail": "Silhouette score s(i) = (b(i)−a(i)) / max(a(i), b(i)), where a(i) = mean within-cluster distance, b(i) = mean nearest-cluster distance. Ranges from -1 to +1; > 0.7 = well-separated clusters.",
        "scale": [
            {"range": f"Silhouette = {clust['silhouette_score']:.3f}", "label": "Very strong separation (>0.7 = excellent)", "color": "#22c55e"},
            {"range": "Cluster 0: 763 cities", "label": "Regular market cities (avg ~12 showrooms/brand)", "color": "#3b82f6"},
            {"range": "Cluster 1: 6 cities", "label": "Mega-hub cities (avg ~263 showrooms/brand)", "color": "#fbbf24"},
        ],
        "why": "The extreme bimodal split (6 mega cities vs 763 regular cities) confirms that India's motorcycle dealer network is structurally metro-anchored. Policy implications differ sharply: mega hubs need service capacity upgrades, while regular markets need basic coverage expansion."
    },
    "quadrant": {
        "title": "Portfolio Quadrant Matrix — Brand Strategy Classification",
        "icon": "🎯",
        "plain": (
            "Places each brand in one of four strategic boxes using two simple questions: "
            "(1) Is the brand's SC/SW ratio above 1.0 (balanced or better)? "
            "(2) Is its total network size above the median of all brands? "
            "Leaders win on both. Overextended brands have big showroom networks "
            "but haven't matched them with service capacity. "
            "Niche Strong brands are balanced but smaller. "
            "Struggling brands are both service-deficient and small."
        ),
        "formula": "Q1: ratio≥1.0 AND size≥median  |  Q2: ratio<1.0 AND size≥median\nQ3: ratio≥1.0 AND size<median  |  Q4: ratio<1.0 AND size<median",
        "formula_detail": f"Size threshold = {q_s_thr:,.0f} (median of total SC+SW across all brands). Ratio threshold = 1.0 (service parity). EV brands plotted with ratio=0 since BikeWale SC data is unavailable.",
        "scale": [
            {"range": "Q1 — Leader", "label": "Balanced at scale — both SC and SW healthy", "color": "#22c55e"},
            {"range": "Q2 — Overextended", "label": "Large network but service is falling behind", "color": "#f59e0b"},
            {"range": "Q3 — Niche Strong", "label": "Balanced but small footprint", "color": "#3b82f6"},
            {"range": "Q4 — Struggling", "label": "Service-deficient and below-average scale", "color": "#ef4444"},
        ],
        "why": "Bajaj's extraordinary Q1 position (ratio 3.2) likely reflects a franchise-heavy model — authorised service centres are everywhere. Hero's Q2 position (ratio 0.38) despite being India's largest motorcycle brand is the most striking finding: massive retail reach, severely under-built service backbone."
    },
}

# ═══════════════════════════════════════════════════════════════════════════
# KPI DERIVED VALUES
# ═══════════════════════════════════════════════════════════════════════════

sc_total   = sum(r["service_total"]  for r in zones_d)
sw_total   = sum(r["showroom_total"] for r in zones_d)
n_gap      = sum(1 for r in zones_d if r["avg_ratio"] < 1.0)
scrape_dt  = kpis.get("scrape_date","2026-06-09")
brand_cnt  = kpis["brand_count"]
city_cnt   = kpis["city_count"]

# ── build per-brand insight text ───────────────────────────────────────────
def brand_insight_html(brand, bd):
    is_ev  = brand in EV_BRANDS_NO_SC
    disp   = BD.get(brand, brand)
    col    = BCOL[brand]
    q      = bd["quadrant"]
    ratio  = bd["ratio"]
    sc     = bd["sc"]
    sw     = bd["sw"]
    cities = bd["cities"]
    rank   = bd.get("ratio_rank")
    ntot   = bd.get("n_ranked", 7)
    rk_txt = f"Ranked <strong>#{rank} of {ntot}</strong> on SC/SW ratio among ICE brands." if rank and not is_ev else ""

    if is_ev:
        zone_str = ", ".join(f"{z}: {v['sw']:,} SW" for z,v in sorted(
            bd["zones"].items(), key=lambda x: -x[1]["sw"])[:3])
        return f"""<p>Ola Electric and Ather are <strong>EV brands</strong> using proprietary service channels
        not captured on BikeWale. Their service centres appear as 0 in this dataset — this is <strong>not
        a network gap</strong> but a data coverage difference. Showroom distribution ({sw:,} total across
        {cities} cities) is analysed below. Top zones: {zone_str}.</p>"""

    if ratio is None:
        return "<p>Insufficient data.</p>"

    best_z  = max(bd["zones"].items(), key=lambda x: x[1].get("ratio") or 0)
    worst_z = min((x for x in bd["zones"].items() if x[1].get("ratio")),
                   key=lambda x: x[1]["ratio"], default=(None, {}))

    q_short  = q.split(" — ",1)[-1] if " — " in q else q
    q_color  = {"Leader":"#22c55e","Overextended":"#f59e0b",
                "Niche Strong":"#3b82f6","Struggling":"#ef4444"}.get(q_short,"#888")

    best_str  = f"{best_z[0]} (ratio {best_z[1]['ratio']:.2f})" if best_z[1].get("ratio") else "N/A"
    worst_str = f"{worst_z[0]} (ratio {worst_z[1]['ratio']:.2f})" if worst_z[1].get("ratio") else "N/A"
    gini_str  = f"{bd['gini_sw']:.2f} SW"
    lq_over   = [z for z,v in bd["lq_sc"].items() if v and v > 1.25]
    lq_under  = [z for z,v in bd["lq_sc"].items() if v and v < 0.75]

    return f"""
    <p>Strategically a <span style="color:{q_color};font-weight:700">{q_short}</span> brand.
    {rk_txt}
    SC/SW ratio of <strong>{ratio:.2f}</strong> ({sc:,} service centres, {sw:,} showrooms across {cities} cities).</p>
    <p style="margin-top:8px">
    <strong>Best zone:</strong> {best_str} &nbsp;&middot;&nbsp;
    <strong>Worst zone:</strong> {worst_str}</p>
    <p style="margin-top:8px">
    <strong>Gini:</strong> {gini_str} showroom inequality
    {'&nbsp;&middot;&nbsp;<strong>Over-concentrated zones:</strong> ' + ', '.join(lq_over) if lq_over else ''}
    {'&nbsp;&middot;&nbsp;<strong>Under-present zones:</strong> ' + ', '.join(lq_under) if lq_under else ''}
    </p>"""


# ═══════════════════════════════════════════════════════════════════════════
# HTML ASSEMBLY
# ═══════════════════════════════════════════════════════════════════════════

def model_btn(key, label):
    return f'<button class="info-btn" onclick="showExplainer(\'{key}\')" title="How this model works">ℹ {label}</button>'

def insight_box(content, variant=""):
    cls = f"insight{' ' + variant if variant else ''}"
    return f'<div class="{cls}">{content}</div>'

# Build per-brand tab HTML
brand_tab_html = {}
for brand in BRAND_LIST:
    bd    = brand_data[brand]
    bc    = brand_charts[brand]
    is_ev = brand in EV_BRANDS_NO_SC
    disp  = BD.get(brand, brand)
    col   = BCOL[brand]
    q     = bd["quadrant"]
    ratio = bd["ratio"]
    qk    = q[:2] if q != "N/A" else "Q4"
    qcol  = QCOL.get(qk, "#888")
    bslug = brand.replace("-","_")

    # KPI values
    kpi1_v = f"{bd['sc']:,}" if not is_ev else "N/A"
    kpi1_l = "Service Centres"
    kpi2_v = f"{bd['sw']:,}"
    kpi2_l = "Showrooms"
    kpi3_v = f"{ratio:.2f}" if ratio else "N/A (EV)"
    kpi3_l = "SC / SW Ratio"
    kpi4_v = f"#{bd['ratio_rank']} / {bd['n_ranked']}" if bd.get("ratio_rank") else "EV Brand"
    kpi4_l = "Ratio Rank"
    kpi5_v = f"{bd['cities']:,}"
    kpi5_l = "Cities Present"

    # Neglect section for this brand
    neg_html = ""
    if bd["neglect"]:
        rows_html = "".join(
            f'<div style="display:flex;justify-content:space-between;align-items:center;'
            f'padding:6px 0;border-bottom:1px solid #27272a;">'
            f'<span style="font-size:12px;color:#a1a1aa">{r["zone"]}</span>'
            f'<span style="font-size:11px;color:#52525b">ratio {r.get("ratio",0):.2f}</span>'
            f'<span style="font-size:13px;font-weight:700;color:{nc(r["score"])}">{r["score"]:.0f}</span>'
            f'</div>'
            for r in bd["neglect"]
        )
        neg_html = f'<div style="margin-top:8px">{rows_html}</div>'

    insight_content = brand_insight_html(brand, bd)

    # Hero-specific data quality warning
    hero_warning = ""
    if brand == "hero":
        hero_warning = """
  <div style="background:#78350f22;border:1px solid #f59e0b55;border-radius:10px;
              padding:14px 16px;margin-bottom:16px">
    <div style="display:flex;gap:12px;align-items:flex-start;margin-bottom:10px">
      <span style="font-size:18px;flex-shrink:0">⚠️</span>
      <div>
        <div style="font-size:13px;font-weight:600;color:#f59e0b;margin-bottom:4px">
          BikeWale captures only ~51% of Hero's actual dealer network
        </div>
        <div style="font-size:12px;color:#a1a1aa;line-height:1.6">
          Cross-referencing Hero's official dealer portal
          (<b style="color:#d4a820">dealers.heromotocorp.com</b>, powered by DashLoc)
          reveals <b style="color:#f59e0b">3,752 showroom entries</b> nationally,
          versus <b style="color:#f59e0b">1,919</b> on BikeWale — a <b style="color:#f59e0b">51% capture rate</b>.
          Hero operates its service network through <b style="color:#d4a820">HeroConnect / Hero Care</b>,
          a proprietary portal not indexed on BikeWale, causing the SC count of 725 to be
          similarly understated. The displayed SC/SW ratio of <b style="color:#f59e0b">0.38</b>
          reflects the BikeWale sample, not Hero's actual network density.
        </div>
      </div>
    </div>
    <div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:8px;margin-top:4px">
      <div style="background:#1a1d27;border:1px solid #2e3347;border-radius:6px;padding:8px 10px">
        <div style="font-size:10px;color:#6b7280;margin-bottom:2px">BikeWale showrooms</div>
        <div style="font-size:16px;font-weight:700;color:#f59e0b">1,919</div>
      </div>
      <div style="background:#1a1d27;border:1px solid #2e3347;border-radius:6px;padding:8px 10px">
        <div style="font-size:10px;color:#6b7280;margin-bottom:2px">Official portal showrooms</div>
        <div style="font-size:16px;font-weight:700;color:#22c55e">3,752</div>
      </div>
      <div style="background:#1a1d27;border:1px solid #2e3347;border-radius:6px;padding:8px 10px">
        <div style="font-size:10px;color:#6b7280;margin-bottom:2px">BikeWale capture rate</div>
        <div style="font-size:16px;font-weight:700;color:#f59e0b">51%</div>
      </div>
    </div>
    <div style="font-size:10px;color:#4b5563;margin-top:8px">
      Source: dealers.heromotocorp.com sitemap enumeration (3,752 batch entries) vs BikeWale scrape — June 2026.
      All Hero metrics in this dashboard are based on the BikeWale sample only.
    </div>
  </div>"""

    brand_tab_html[brand] = f"""
<div id="page-{bslug}" class="page" style="display:none">

  {hero_warning}

  <!-- brand header -->
  <div class="brand-hero" style="border-left:4px solid {col}">
    <div style="display:flex;align-items:center;gap:16px;margin-bottom:16px">
      <div class="brand-dot" style="background:{col}"></div>
      <div>
        <div class="brand-eye" style="color:{col}">{disp.upper()}</div>
        <div class="brand-title">{disp}</div>
        <div class="brand-meta">{bd['sc']:,} service centres &middot; {bd['sw']:,} showrooms &middot; {bd['cities']:,} cities</div>
      </div>
      <div style="margin-left:auto">
        <div class="q-badge" style="background:{qcol}22;color:{qcol};border-color:{qcol}55">{q}</div>
      </div>
    </div>
    <div class="b-insight">{insight_content}</div>
  </div>

  <!-- KPI strip -->
  <div class="b-kstrip">
    <div class="b-kpi">
      <div class="b-kpi-l">{kpi1_l}</div>
      <div class="b-kpi-v" style="color:{'#22c55e' if not is_ev else '#52525b'}">{kpi1_v}</div>
    </div>
    <div class="b-kpi">
      <div class="b-kpi-l">{kpi2_l}</div>
      <div class="b-kpi-v">{kpi2_v}</div>
    </div>
    <div class="b-kpi">
      <div class="b-kpi-l">{kpi3_l}</div>
      <div class="b-kpi-v" style="color:{rc(ratio) if ratio else '#52525b'}">{kpi3_v}</div>
    </div>
    <div class="b-kpi">
      <div class="b-kpi-l">{kpi4_l}</div>
      <div class="b-kpi-v" style="color:{col}">{kpi4_v}</div>
    </div>
    <div class="b-kpi">
      <div class="b-kpi-l">{kpi5_l}</div>
      <div class="b-kpi-v">{kpi5_v}</div>
    </div>
  </div>

  <!-- charts row 1 -->
  <div class="b-section">
    <div class="g2">
      <div class="card">
        <div class="ctitle">Zone SC / SW Ratio
          {model_btn('ratio','SC/SW Ratio')}
        </div>
        <div id="p-zone-{bslug}" class="plot" style="height:280px"></div>
      </div>
      <div class="card">
        <div class="ctitle">Competitive Ratio Ranking — all brands
          {model_btn('quadrant','Quadrant')}
        </div>
        <div id="p-comp-ratio-{bslug}" class="plot" style="height:280px"></div>
      </div>
    </div>
  </div>

  <!-- charts row 2 -->
  <div class="b-section">
    <div class="g2">
      <div class="card">
        <div class="ctitle">Location Quotient by Zone ({'SC LQ' if not is_ev else 'SW LQ'})
          {model_btn('lq','Location Quotient')}
        </div>
        <div id="p-lq-{bslug}" class="plot" style="height:280px"></div>
      </div>
      <div class="card">
        <div class="ctitle">Competitive Network Size Ranking</div>
        <div id="p-size-{bslug}" class="plot" style="height:280px"></div>
      </div>
    </div>
  </div>

  <!-- charts row 3: radar + neglect -->
  <div class="b-section">
    <div class="g2">
      <div class="card">
        <div class="ctitle">Competitive Radar — 5 Dimensions
          {model_btn('gini','Gini + Radar')}
        </div>
        <div id="p-radar-{bslug}" class="plot" style="height:320px"></div>
        <div style="font-size:10px;color:#52525b;margin-top:8px;line-height:1.6">
          Grey lines = all other brands. Coloured = {disp}. All axes normalised 0→1.
          <br>Service Balance capped at Bajaj (3.20). EV brands show 0 for Service Balance.
        </div>
      </div>
      <div class="card">
        <div class="ctitle">Neglect Score by Zone
          {model_btn('ratio','Neglect Score')}
        </div>
        {neg_html if neg_html else '<div style="color:#52525b;font-size:12px;padding:20px">No neglect data available for this brand.</div>'}
        <div style="font-size:10px;color:#52525b;margin-top:12px;line-height:1.6">
          Score 0–100. Combines SC/SW deficit &times; zone isolation &times; scale penalty.
          Red = high priority, Green = low priority.
        </div>
      </div>
    </div>
  </div>

</div>"""

# ── stringify chart dicts for JS ───────────────────────────────────────────
explainers_json = json.dumps(EXPLAINERS, ensure_ascii=False)

# Build JS render-on-demand calls for each brand
brand_render_js = ""
for brand in BRAND_LIST:
    bc    = brand_charts[brand]
    bslug = brand.replace("-","_")
    lines = [f"case '{bslug}':"]
    lines.append(f"  Plotly.newPlot('p-zone-{bslug}',       {bc['zone']},       {{}}, cfg);")
    lines.append(f"  Plotly.newPlot('p-comp-ratio-{bslug}', {bc['comp_ratio']},  {{}}, cfg);")
    if "lq" in bc:
        lines.append(f"  Plotly.newPlot('p-lq-{bslug}',       {bc['lq']},         {{}}, cfg);")
    lines.append(f"  Plotly.newPlot('p-size-{bslug}',       {bc['comp_size']},   {{}}, cfg);")
    lines.append(f"  Plotly.newPlot('p-radar-{bslug}',      {bc['radar']},       {{}}, cfg);")
    lines.append("  break;")
    brand_render_js += "\n".join(lines) + "\n"

all_brand_tabs = "\n".join(brand_tab_html.values())

# ── Tab nav items ──────────────────────────────────────────────────────────
brand_tab_btns = "".join(
    f'<button class="tab-btn" data-tab="{b.replace("-","_")}" onclick="showTab(\'{b.replace("-","_")}\')" style="border-bottom-color:{BCOL[b]}44">{BD[b]}</button>'
    for b in BRAND_LIST
)


html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Indian Motorcycle Network Analysis</title>
<script>{PLOTLY_JS}</script>
<style>
*,*::before,*::after{{box-sizing:border-box;margin:0;padding:0}}
html{{scroll-behavior:smooth}}
body{{font-family:'Segoe UI',Arial,sans-serif;background:#111113;color:#e4e4e7}}

/* ── TAB BAR ──────────────────────────────────────────── */
.tab-bar{{
  position:sticky;top:0;z-index:100;
  background:#0d0d0f;border-bottom:1px solid #222225;
  display:flex;align-items:stretch;overflow-x:auto;
  scrollbar-width:none;
}}
.tab-bar::-webkit-scrollbar{{display:none}}
.tab-btn{{
  flex-shrink:0;padding:13px 18px;
  font-size:11px;letter-spacing:0.8px;text-transform:uppercase;
  color:#52525b;background:transparent;border:none;cursor:pointer;
  border-bottom:2px solid transparent;transition:all 0.2s;white-space:nowrap;
}}
.tab-btn:hover{{color:#a1a1aa}}
.tab-btn.active{{color:#fafafa;border-bottom-color:#22c55e!important}}
.tab-overview-btn{{border-bottom-color:#22c55e!important}}

/* ── OVERVIEW LAYOUT ──────────────────────────────────── */
.hero{{background:#111113;padding:48px 56px 36px;border-bottom:1px solid #222225}}
.hero-eye{{font-size:10px;letter-spacing:2px;text-transform:uppercase;color:#22c55e;margin-bottom:11px}}
.hero-title{{font-size:32px;font-weight:700;line-height:1.2;color:#fafafa;margin-bottom:5px}}
.hero-meta{{font-size:12px;color:#52525b;margin-bottom:28px}}
.kstrip{{display:grid;grid-template-columns:repeat(5,1fr);gap:1px;background:#27272a;border:1px solid #27272a}}
.kpi{{background:#18181b;padding:16px 18px}}
.kpi-l{{font-size:9px;letter-spacing:1.5px;text-transform:uppercase;color:#52525b;margin-bottom:6px}}
.kpi-v{{font-size:24px;font-weight:700;line-height:1;color:#fafafa}}
.kpi-v.g{{color:#22c55e}} .kpi-v.r{{color:#ef4444}} .kpi-v.y{{color:#fbbf24}}
.kpi-s{{font-size:10px;color:#52525b;margin-top:3px}}
.section{{padding:38px 52px;border-bottom:1px solid #1a1a1c}}
.s-eye{{font-size:9px;letter-spacing:2px;text-transform:uppercase;color:#3f3f46;margin-bottom:5px}}
.s-title{{font-size:18px;font-weight:600;color:#fafafa;margin-bottom:4px}}
.s-desc{{font-size:12px;color:#52525b;line-height:1.75;margin-bottom:18px;max-width:820px}}

/* ── BRAND PAGE LAYOUT ────────────────────────────────── */
.brand-hero{{background:#18181b;padding:32px 52px 24px;border-bottom:1px solid #27272a}}
.brand-dot{{width:18px;height:18px;border-radius:50%;flex-shrink:0}}
.brand-eye{{font-size:9px;letter-spacing:2px;text-transform:uppercase;margin-bottom:2px}}
.brand-title{{font-size:28px;font-weight:700;color:#fafafa;line-height:1.15}}
.brand-meta{{font-size:12px;color:#52525b;margin-top:3px}}
.b-insight{{font-size:13px;line-height:1.75;color:#a1a1aa;margin-top:0;max-width:800px}}
.q-badge{{display:inline-block;padding:5px 12px;border:1px solid;border-radius:4px;
  font-size:10px;letter-spacing:1px;text-transform:uppercase;font-weight:600}}
.b-kstrip{{display:grid;grid-template-columns:repeat(5,1fr);gap:1px;
  background:#27272a;border-bottom:1px solid #27272a}}
.b-kpi{{background:#18181b;padding:14px 18px}}
.b-kpi-l{{font-size:9px;letter-spacing:1.5px;text-transform:uppercase;color:#52525b;margin-bottom:5px}}
.b-kpi-v{{font-size:22px;font-weight:700;color:#fafafa}}
.b-section{{padding:28px 52px;border-bottom:1px solid #1a1a1c}}

/* ── SHARED COMPONENTS ────────────────────────────────── */
.g2{{display:grid;grid-template-columns:1fr 1fr;gap:14px}}
.full{{width:100%}}
.card{{background:#18181b;border:1px solid #27272a;border-radius:6px;padding:18px}}
.ctitle{{font-size:9px;letter-spacing:1px;text-transform:uppercase;color:#3f3f46;
  margin-bottom:12px;display:flex;align-items:center;gap:8px;flex-wrap:wrap}}
.insight{{margin-top:12px;padding:11px 14px;background:#0d1f12;
  border-left:3px solid #22c55e;border-radius:0 4px 4px 0;
  font-size:12px;line-height:1.7;color:#86efac}}
.insight strong{{color:#4ade80}}
.insight.warn{{background:#1f1107;border-color:#f59e0b;color:#fcd34d}}
.insight.warn strong{{color:#fbbf24}}
.insight.info{{background:#0a1628;border-color:#3b82f6;color:#93c5fd}}
.insight.info strong{{color:#60a5fa}}
.plot{{width:100%}}
.footer{{padding:22px 56px;font-size:11px;color:#3f3f46;border-top:1px solid #1a1a1c;line-height:1.8}}

/* ── MODEL INFO BUTTON ────────────────────────────────── */
.info-btn{{
  display:inline-flex;align-items:center;gap:4px;
  font-size:9px;letter-spacing:0.5px;text-transform:uppercase;
  color:#3b82f6;background:#0a1628;border:1px solid #1e3a5f;
  border-radius:3px;padding:2px 7px;cursor:pointer;transition:all 0.2s;
  white-space:nowrap;
}}
.info-btn:hover{{background:#1e3a5f;color:#93c5fd}}

/* ── EXPLAINER DRAWER ─────────────────────────────────── */
.explainer-overlay{{
  display:none;position:fixed;inset:0;background:rgba(0,0,0,0.6);z-index:200;
}}
.explainer-drawer{{
  position:fixed;right:0;top:0;bottom:0;width:480px;max-width:100%;
  background:#111113;border-left:1px solid #27272a;
  overflow-y:auto;z-index:201;padding:0;
  transform:translateX(100%);transition:transform 0.3s ease;
}}
.explainer-drawer.open{{transform:translateX(0)}}
.explainer-overlay.open{{display:block}}
.exp-header{{
  padding:24px 24px 20px;
  border-bottom:1px solid #27272a;
  display:flex;align-items:flex-start;justify-content:space-between;gap:12px;
  background:#0d0d0f;position:sticky;top:0;z-index:10;
}}
.exp-icon{{font-size:24px;flex-shrink:0;margin-top:2px}}
.exp-title{{font-size:16px;font-weight:700;color:#fafafa;line-height:1.3}}
.exp-close{{
  background:none;border:1px solid #3f3f46;color:#71717a;
  border-radius:4px;padding:4px 10px;cursor:pointer;font-size:12px;
  flex-shrink:0;
}}
.exp-close:hover{{color:#fafafa;border-color:#71717a}}
.exp-body{{padding:24px}}
.exp-section{{margin-bottom:22px}}
.exp-label{{
  font-size:9px;letter-spacing:2px;text-transform:uppercase;
  color:#3f3f46;margin-bottom:8px;
}}
.exp-plain{{font-size:13px;line-height:1.8;color:#a1a1aa}}
.exp-formula{{
  background:#0d0d0f;border:1px solid #27272a;border-radius:5px;
  padding:14px 16px;margin:10px 0;
  font-family:'Courier New',monospace;font-size:12px;color:#22c55e;
  line-height:1.6;white-space:pre-wrap;overflow-x:auto;
}}
.exp-formula-detail{{font-size:11px;color:#52525b;line-height:1.6;margin-top:6px}}
.scale-rows{{display:flex;flex-direction:column;gap:6px;margin-top:8px}}
.scale-row{{display:flex;align-items:center;gap:10px;padding:7px 10px;
  background:#18181b;border-radius:4px;}}
.scale-dot{{width:10px;height:10px;border-radius:50%;flex-shrink:0}}
.scale-range{{font-size:11px;font-family:'Courier New',monospace;color:#a1a1aa;flex-shrink:0;min-width:130px}}
.scale-label{{font-size:11px;color:#71717a}}
.exp-why{{font-size:12px;line-height:1.7;color:#71717a;
  border-top:1px solid #1a1a1c;padding-top:16px;margin-top:4px}}
@keyframes fade-up{{from{{opacity:0;transform:translateY(8px)}}to{{opacity:1;transform:translateY(0)}}}}
.hero,.card,.brand-hero{{animation:fade-up .45s ease both}}
@media(prefers-reduced-motion:reduce){{*,*::before,*::after{{animation-duration:.01ms!important;animation-iteration-count:1!important;scroll-behavior:auto!important;transition-duration:.01ms!important}}}}
</style>
</head>
<body>

<!-- MODEL EXPLAINER DRAWER -->
<div class="explainer-overlay" id="exp-overlay" onclick="closeExplainer()"></div>
<div class="explainer-drawer" id="exp-drawer">
  <div class="exp-header">
    <div style="display:flex;gap:12px;align-items:flex-start">
      <div class="exp-icon" id="exp-icon">📊</div>
      <div class="exp-title" id="exp-title">Model</div>
    </div>
    <button class="exp-close" onclick="closeExplainer()">Close ✕</button>
  </div>
  <div class="exp-body" id="exp-body"></div>
</div>

<!-- TAB BAR -->
<div class="tab-bar">
  <button class="tab-btn active" data-tab="about" onclick="showTab('about')" style="border-bottom-color:#22c55e">Research Scope</button>
  <button class="tab-btn" data-tab="overview" onclick="showTab('overview')" style="border-bottom-color:#22c55e44">Overview</button>
  {brand_tab_btns}
  <button class="tab-btn" data-tab="radius" onclick="showTab('radius')" style="margin-left:auto;border-bottom-color:#3b82f6">Radius Explorer</button>
</div>

<!-- ══════════════════════════════════════════════════════════
     ABOUT / SCOPE PAGE  (landing page)
══════════════════════════════════════════════════════════ -->
<div id="page-about" class="page">

<div style="padding:52px 56px 36px;border-bottom:1px solid #222225;background:#111113">
  <div style="font-size:10px;letter-spacing:2px;text-transform:uppercase;color:#22c55e;margin-bottom:12px">IIM Sirmaur &middot; BMS Batch 2025 &middot; Management Research Project</div>
  <div style="font-size:32px;font-weight:700;color:#fafafa;line-height:1.2;margin-bottom:8px">Indian Motorcycle Brand<br>Network Bottleneck Analysis</div>
  <div style="font-size:14px;color:#71717a;max-width:720px;line-height:1.8;margin-bottom:28px">
    A data-driven study of the structural imbalance between showroom (retail) and service centre networks
    across India&apos;s nine major motorcycle brands — and what that imbalance means for regional market access.
  </div>
  <button onclick="showTab('overview')" style="background:#22c55e;color:#0d0d0f;border:none;
    padding:11px 28px;border-radius:4px;font-size:12px;font-weight:700;cursor:pointer;
    letter-spacing:0.5px;text-transform:uppercase;">
    Enter Dashboard &rarr;
  </button>
</div>

<!-- Three cards: Question | Data | Models -->
<div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:1px;background:#27272a;
            border-bottom:1px solid #27272a">

  <div style="background:#18181b;padding:28px 32px">
    <div style="font-size:9px;letter-spacing:2px;text-transform:uppercase;color:#3f3f46;margin-bottom:12px">Research Question</div>
    <div style="font-size:15px;font-weight:600;color:#fafafa;margin-bottom:14px;line-height:1.4">
      Do Indian motorcycle brands systematically under-invest in service networks in certain regions?
    </div>
    <p style="font-size:12px;color:#71717a;line-height:1.8;margin-bottom:10px">
      The core hypothesis: brands that open showrooms faster than service centres create a
      <strong style="color:#a1a1aa">post-sale access gap</strong> — customers can buy a bike but struggle to get it serviced locally.
    </p>
    <p style="font-size:12px;color:#71717a;line-height:1.8">
      We test this across <strong style="color:#a1a1aa">6 geographic zones</strong>,
      <strong style="color:#a1a1aa">9 brands</strong>, and
      <strong style="color:#a1a1aa">{city_cnt:,} cities in the scrape</strong> using eight quantitative models.
    </p>
  </div>

  <div style="background:#18181b;padding:28px 32px;border-left:1px solid #27272a">
    <div style="font-size:9px;letter-spacing:2px;text-transform:uppercase;color:#3f3f46;margin-bottom:12px">Data Source</div>
    <div style="font-size:15px;font-weight:600;color:#fafafa;margin-bottom:14px;line-height:1.4">
      BikeWale.com — scraped June 9, 2026
    </div>
    <div style="display:flex;flex-direction:column;gap:8px">
      {"".join(f'<div style="display:flex;gap:10px;font-size:12px"><span style="color:#22c55e;flex-shrink:0">+</span><span style="color:#71717a;line-height:1.6">{t}</span></div>' for t in [
        f"6,944 dealer records across {city_cnt:,} cities in the snapshot",
        "9 brands: Hero, Honda, Bajaj, Royal Enfield, Yamaha, Suzuki, Ola Electric, Ather, Jawa",
        "Two record types: Authorised Service Centres and Dealer Showrooms",
        "Playwright headless-browser scrape (JavaScript-rendered pages)",
        f"{geo_city_cnt:,} cities have coordinates for the radius explorer",
      ])}
      {"".join(f'<div style="display:flex;gap:10px;font-size:12px"><span style="color:#ef4444;flex-shrink:0">&minus;</span><span style="color:#71717a;line-height:1.6">{t}</span></div>' for t in [
        "TVS excluded: only 3 cities on BikeWale (insufficient)",
        "KTM excluded: only 5 cities on BikeWale (insufficient)",
        "No FADA sales volume data in this version",
      ])}
    </div>
  </div>

  <div style="background:#18181b;padding:28px 32px;border-left:1px solid #27272a">
    <div style="font-size:9px;letter-spacing:2px;text-transform:uppercase;color:#3f3f46;margin-bottom:12px">Analytical Models</div>
    <div style="font-size:15px;font-weight:600;color:#fafafa;margin-bottom:14px;line-height:1.4">
      Seven models, each answering a different question
    </div>
    <div style="display:flex;flex-direction:column;gap:7px">
      {"".join(f'<div style="display:flex;gap:10px;align-items:flex-start;font-size:12px"><span style="color:#22c55e;flex-shrink:0;font-family:monospace;font-size:10px;margin-top:2px">{n}</span><div><span style="color:#a1a1aa">{m}</span> <span style="color:#52525b">{d}</span></div></div>' for n,m,d in [
        ("01","SC/SW Ratio","Are there more showrooms than service centres?"),
        ("02","Gini Coefficient","How unequally are dealers spread across cities?"),
        ("03","Location Quotient","Is a brand over- or under-present in each zone?"),
        ("04","HHI","Are dealers dangerously concentrated in a few cities?"),
        ("05","Moran&#39;s I","Are service gaps geographically clustered?"),
        ("06","PCA","What are the key dimensions of city network profiles?"),
        ("07","K-Means","What types of cities exist by network density?"),
        ("08","Quadrant Matrix","Where does each brand sit strategically?"),
      ])}
    </div>
    <div style="margin-top:12px;font-size:11px;color:#3f3f46">
      Click any <span style="color:#3b82f6;background:#0a1628;border:1px solid #1e3a5f;padding:1px 5px;border-radius:2px;font-size:9px">ℹ model name</span> button in the dashboard for a plain-English explanation with formulas.
    </div>
  </div>
</div>

<!-- Limitations: two columns -->
<div style="padding:40px 52px;border-bottom:1px solid #1a1a1c">
  <div style="font-size:9px;letter-spacing:2px;text-transform:uppercase;color:#3f3f46;margin-bottom:6px">Limitations &amp; Disclaimers</div>
  <div style="font-size:18px;font-weight:600;color:#fafafa;margin-bottom:18px">
    What this analysis can — and cannot — claim
  </div>
  <div style="background:#1f1107;border-left:3px solid #f59e0b;border-radius:0 4px 4px 0;
              padding:12px 16px;margin-bottom:24px;font-size:13px;color:#fcd34d;line-height:1.7">
    <strong style="color:#fbbf24">Important:</strong>
    This is a <strong>descriptive and exploratory</strong> study.
    It identifies patterns in dealer network structure but does <strong>not</strong> establish causal links
    between network gaps and sales performance. Revenue impact figures have been removed as they
    require sales data (FADA) that was not available in this version. Treat all findings as
    hypotheses to be tested with primary data, not as established facts.
  </div>
  <div style="display:grid;grid-template-columns:1fr 1fr;gap:20px">

    <!-- Data limitations -->
    <div style="background:#18181b;border:1px solid #27272a;border-radius:6px;padding:22px">
      <div style="font-size:10px;letter-spacing:1.5px;text-transform:uppercase;
                  color:#ef4444;margin-bottom:14px;display:flex;align-items:center;gap:8px">
        <span style="width:8px;height:8px;border-radius:50%;background:#ef4444;display:inline-block"></span>
        Data Limitations
      </div>
      {"".join(f'<div style="margin-bottom:14px"><div style="font-size:12px;font-weight:600;color:#a1a1aa;margin-bottom:3px">{h}</div><div style="font-size:11px;color:#52525b;line-height:1.7">{b}</div></div>' for h,b in [
        ("BikeWale coverage is not exhaustive",
         "Not every dealer in India lists on BikeWale. Brands with stronger digital presence may appear to have more dealers than they truly do relative to others."),
        ("EV brand service data is absent",
         "Ola Electric and Ather use proprietary service apps and home-service models not listed on BikeWale. Their SC count = 0 is a platform gap, not a true service gap. Their analysis is showroom-only."),
        ("Single-source, single-snapshot",
         "Data was scraped on June 9, 2026. Dealer networks change constantly. No cross-validation against SIAM, manufacturer, or FADA data was performed."),
        ("No population or demand weighting",
         "A city with 1 million residents and 1 service centre is treated identically to a city with 50,000 residents and 1 service centre. Equal-count analysis obscures per-capita access."),
        ("No quality or capacity data",
         "We count dealers, not their size or throughput. A single multi-bay service centre may outperform five small ones — this dataset cannot distinguish between them."),
      ])}
    </div>

    <!-- Mathematical limitations -->
    <div style="background:#18181b;border:1px solid #27272a;border-radius:6px;padding:22px">
      <div style="font-size:10px;letter-spacing:1.5px;text-transform:uppercase;
                  color:#fbbf24;margin-bottom:14px;display:flex;align-items:center;gap:8px">
        <span style="width:8px;height:8px;border-radius:50%;background:#fbbf24;display:inline-block"></span>
        Mathematical Limitations
      </div>
      {"".join(f'<div style="margin-bottom:14px"><div style="font-size:12px;font-weight:600;color:#a1a1aa;margin-bottom:3px">{h}</div><div style="font-size:11px;color:#52525b;line-height:1.7">{b}</div></div>' for h,b in [
        ("SC/SW ratio assumes equal weight per city",
         "The ratio treats Mumbai and a small town identically. Aggregating at zone level masks within-zone variation. A single metro with a good ratio can mask 50 small towns with poor ratios."),
        ("Gini ignores population distribution",
         "An equal Gini does not mean equal customer access. The formula is borrowed from income inequality analysis and works best when units (cities) are comparable in size — which Indian cities are not."),
        ("Location Quotient assumes proportional fairness",
         "LQ assumes the &ldquo;fair&rdquo; distribution mirrors the overall industry average. However, some zones may naturally have fewer vehicles on road (e.g. Northeast) and thus organically warrant fewer service centres."),
        ("Moran&#39;s I is sensitive to neighbourhood threshold",
         "We used 150 km as the spatial neighbourhood cutoff. This parameter significantly affects the result. Different thresholds (100 km, 200 km) would yield different Moran&#39;s I values and p-values."),
        ("Neglect Score uses researcher-defined weights",
         "The composite score penalises deficit &times; zone isolation &times; scale. These weights are not empirically validated. Small changes in weighting change which brand-zone pairs appear most critical."),
        ("Quadrant thresholds are arbitrary",
         "Ratio = 1.0 and size = median are clean researcher choices, not industry standards. A brand sitting just below 1.0 and a brand at 0.99 are structurally similar but appear in different quadrants."),
        ("PCA and K-Means are exploratory only",
         "These are pattern-finding tools, not predictive models. Cluster assignments and PC scores change with different feature sets, scaling, or random seeds. They describe, not explain."),
      ])}
    </div>
  </div>
</div>

<!-- How to navigate -->
<div style="padding:36px 52px 40px;border-bottom:1px solid #1a1a1c">
  <div style="font-size:9px;letter-spacing:2px;text-transform:uppercase;color:#3f3f46;margin-bottom:6px">Navigation Guide</div>
  <div style="font-size:16px;font-weight:600;color:#fafafa;margin-bottom:18px">How to use this dashboard</div>
  <div style="display:grid;grid-template-columns:repeat(4,1fr);gap:12px">
    {"".join(f'<div style="background:#18181b;border:1px solid #27272a;border-radius:6px;padding:16px"><div style="font-size:10px;letter-spacing:1px;text-transform:uppercase;color:#3f3f46;margin-bottom:8px">{step}</div><div style="font-size:12px;color:#71717a;line-height:1.7">{desc}</div></div>' for step, desc in [
      ("Step 1 &mdash; Overview tab",
       "See all six analytical sections in sequence. Each section shows zone-level and brand-level charts with interpretation notes."),
      ("Step 2 &mdash; Brand tabs",
       "Click any brand name in the tab bar to see that brand&apos;s individual analysis: zone ratios, LQ, competitive radar, and neglect scores."),
      ("Step 3 &mdash; Model explainers",
       'Any button labelled <span style="color:#3b82f6;background:#0a1628;border:1px solid #1e3a5f;padding:1px 5px;border-radius:2px;font-size:9px">ℹ Model Name</span> opens a side panel with the formula, plain-English explanation, and interpretation guide.'),
      ("Step 4 &mdash; Hover for detail",
       "All Plotly charts are interactive. Hover over any bar, point, or heatmap cell for exact values. Charts resize automatically with the browser window."),
    ])}
  </div>
</div>

<div style="padding:22px 56px;font-size:11px;color:#3f3f46;line-height:1.8">
  Indian Motorcycle Brand Network Bottleneck Analysis &nbsp;&middot;&nbsp; IIM Sirmaur BMS 2025 &nbsp;&middot;&nbsp;
  Data: BikeWale.com (scraped {scrape_dt}) &nbsp;&middot;&nbsp; Built with Python &middot; SQLite &middot; Plotly.js
</div>

</div><!-- /page-about -->


<!-- ══════════════════════════════════════════════════════════
     OVERVIEW PAGE
══════════════════════════════════════════════════════════ -->
<div id="page-overview" class="page" style="display:none">

<div class="hero">
  <div class="hero-eye">IIM Sirmaur &middot; BMS Batch 2025 &middot; Management Research Project</div>
  <div class="hero-title">Indian Motorcycle Brand<br>Network Bottleneck Analysis</div>
  <div class="hero-meta">
    {brand_cnt} brands &nbsp;&middot;&nbsp; {city_cnt} cities &nbsp;&middot;&nbsp; 6 zones &nbsp;&middot;&nbsp;
    7 analytical models &nbsp;&middot;&nbsp; Scraped {scrape_dt}
  </div>
  <div class="kstrip">
    <div class="kpi"><div class="kpi-l">Brands Covered</div>
      <div class="kpi-v g">{brand_cnt}</div><div class="kpi-s">Hero to Ather</div></div>
    <div class="kpi"><div class="kpi-l">Cities in Snapshot</div>
      <div class="kpi-v">{city_cnt:,}</div><div class="kpi-s">{geo_city_cnt:,} with map coordinates</div></div>
    <div class="kpi"><div class="kpi-l">Mean Brand-Zone Ratio</div>
      <div class="kpi-v {'g' if kpis['avg_ratio'] >= 1 else 'r'}">{kpis['avg_ratio']:.2f}</div><div class="kpi-s">Non-EV pairs; unweighted mean</div></div>
    <div class="kpi"><div class="kpi-l">Network Gap Proxy</div>
      <div class="kpi-v y">₹{kpis['revenue_leakage_cr']:.0f} cr</div><div class="kpi-s">Indicative; not observed revenue</div></div>
    <div class="kpi"><div class="kpi-l">Zones Below Parity</div>
      <div class="kpi-v {'r' if n_gap>0 else 'g'}">{n_gap} / 6</div>
      <div class="kpi-s">SC/SW ratio &lt; 1.0</div></div>
  </div>
</div>

<!-- S1 Zone Health -->
<div class="section">
  <div class="s-eye">01 &mdash; Zone Health</div>
  <div class="s-title">Geographic Network Balance
    {model_btn('ratio','SC/SW Ratio')}
  </div>
  <div class="s-desc">
    Average service-to-showroom ratio per zone. Below 1.0 = more showrooms than service centres.
    East (0.75) and South (0.76) are the most service-deficient zones.
    The heatmap breaks this down brand-by-brand — red cells are bottlenecks.
  </div>
  <div class="g2">
    <div class="card"><div class="ctitle">Avg SC / SW Ratio by Zone</div>
      <div id="p-zone"  class="plot" style="height:280px"></div></div>
    <div class="card"><div class="ctitle">Brand &times; Zone Ratio Heatmap</div>
      <div id="p-heat"  class="plot" style="height:280px"></div></div>
  </div>
  <div class="insight">
    <strong>Key finding:</strong> Hero shows the worst individual ratios across almost every zone —
    East (0.33), South (0.35), North (0.41). Bajaj dominates everywhere with ratios 3–5x above parity.
  </div>
</div>

<div class="section">
  <div class="s-eye">02 &mdash; Brand Footprint</div>
  <div class="s-title">National Network Balance</div>
  <div class="s-desc">National service-centre to showroom ratios alongside observed network counts. EV brands are excluded from ratio ranking because BikeWale does not provide comparable service-centre counts for them.</div>
  <div class="g2">
    <div class="card"><div class="ctitle">National SC / SW Ratio</div><div id="p-brand-ratio" class="plot" style="height:330px"></div></div>
    <div class="card"><div class="ctitle">Service Centres and Showrooms</div><div id="p-brand-size" class="plot" style="height:330px"></div></div>
  </div>
</div>

<!-- S2 Inequality -->
<div class="section">
  <div class="s-eye">02 &mdash; Models 1 &amp; 3 &mdash; Inequality</div>
  <div class="s-title">Distribution Inequality
    {model_btn('gini','Gini Coefficient')}
    {model_btn('hhi','HHI')}
  </div>
  <div class="s-desc">
    <strong>Gini Coefficient:</strong> How evenly does each brand spread dealers across cities?
    0 = perfectly equal, 1 = everything in one city.
    A higher SW Gini than SC Gini means the brand is more selective about where it opens showrooms vs service centres.
    <br><br>
    <strong>HHI:</strong> Are dealers concentrated in just a few big cities?
    All brands score below 1,500 = dispersed (no brand is dangerously metro-dependent).
  </div>
  <div class="g2">
    <div class="card"><div class="ctitle">Gini Coefficient per Brand</div>
      <div id="p-gini" class="plot" style="height:330px"></div></div>
    <div class="card"><div class="ctitle">HHI per Brand — all below 1,500 = dispersed</div>
      <div id="p-hhi" class="plot" style="height:330px"></div></div>
  </div>
  <div class="insight">
    <strong>Inequality:</strong> Suzuki SW Gini = 0.73 (most unequal showroom distribution).
    Jawa SC Gini = 0.13 (most equal service distribution, though small footprint).
    Royal Enfield is uniquely balanced — near-identical SC and SW Gini scores.
  </div>
</div>

<!-- S4 Geography -->
<div class="section">
  <div class="s-eye">03 &mdash; Models 2 &amp; 4 &mdash; Geography</div>
  <div class="s-title">Regional Concentration &amp; Spatial Patterns
    {model_btn('lq','Location Quotient')}
    {model_btn('moran','Moran\'s I')}
  </div>
  <div class="s-desc">
    <strong>Location Quotient (LQ):</strong> Is a brand over- or under-present in each zone relative to the national average?
    LQ &gt;1.25 = over-concentrated. &lt;0.75 = structural gap.
    <br><br>
    <strong>Moran's I:</strong> Are cities with poor ratios geographically clustered?
    Our result: I = {moran['moran_i']:.4f}, p = {moran['p_value']:.3f} — <em>not significant</em>.
    Network gaps are random in space, not forming regional blocs.
  </div>
  <div class="g2">
    <div class="card"><div class="ctitle">Service Centre LQ — brand &times; zone</div>
      <div id="p-lq"    class="plot" style="height:290px"></div></div>
    <div class="card"><div class="ctitle">Moran's I by Zone</div>
      <div id="p-moran" class="plot" style="height:290px"></div>
      <div class="insight info">
        <strong>Spatial finding:</strong> No significant geographic clustering of network gaps.
        West zone shows the highest local I (0.10). Brands can fix gaps city-by-city
        rather than requiring zone-wide programs.
      </div>
    </div>
  </div>
</div>

<!-- S5 Cities -->
<div class="section">
  <div class="s-eye">04 &mdash; Models 5 &amp; 6 &mdash; City Profiles</div>
  <div class="s-title">City Network Segmentation
    {model_btn('pca','PCA')}
    {model_btn('kmeans','K-Means')}
  </div>
  <div class="s-desc">
    <strong>PCA</strong> reduces the 18-feature city dealer profile to 2 dimensions.
    PC1 ({var1}% variance) = mass-market brand scale. Cities further right have larger, more complete networks.
    <br><br>
    <strong>K-Means</strong> found k=2 optimal clusters (silhouette {clust['silhouette_score']:.3f}).
    Only 6 cities operate at mega-hub scale vs 763 regular-market cities.
  </div>
  <div class="g2">
    <div class="card"><div class="ctitle">PCA — City Network Profiles ({len([c for c in pca['cities'] if c['zone']!='Unknown']):,} cities, coloured by zone)</div>
      <div id="p-pca"   class="plot" style="height:360px"></div></div>
    <div class="card"><div class="ctitle">K-Means Cluster Comparison</div>
      <div id="p-clust" class="plot" style="height:360px"></div>
      <div class="insight"><strong>Scale gap:</strong>
        6 mega-hub cities average {next(s['avg_sw'] for s in cs if s['avg_sw']>50):.0f} showrooms/brand.
        The other {next(s['n_cities'] for s in cs if s['avg_sw']<50):,} cities average
        only {next(s['avg_sw'] for s in cs if s['avg_sw']<50):.1f} showrooms/brand.
        This 21× gap is the structural reality of India's dealer network.
      </div>
    </div>
  </div>
</div>

<!-- S6 Brand Portfolio -->
<div class="section">
  <div class="s-eye">05 &mdash; Model 7 &mdash; Brand Portfolio</div>
  <div class="s-title">Strategic Quadrant Analysis
    {model_btn('quadrant','Quadrant Matrix')}
  </div>
  <div class="s-desc">
    X = national SC/SW ratio (service balance). Y = total network size (SC + SW).
    Threshold: ratio = 1.0 (parity), size = {q_s_thr:,.0f} (median).
    Bajaj leads with a ratio of 3.2 — 3× more service centres than showrooms.
    Hero is the most overextended: India's largest dealer network but severely under-serviced.
  </div>
  <div class="card full">
    <div class="ctitle">SC/SW Ratio vs Total Network Size</div>
    <div id="p-quad" class="plot" style="height:450px"></div>
  </div>
  <div class="insight">
    <strong>Insight:</strong> Only Bajaj and Honda are above parity at national scale.
    Yamaha and Hero are both Q2 Overextended — strong retail presence without matching service backbone.
    EV brands (Ola Electric, Ather) show ratio=0 since BikeWale carries no service centre data for them.
  </div>
</div>

<!-- S7 Priority -->
<div class="section">
  <div class="s-eye">06 &mdash; Action Priority</div>
  <div class="s-title">Neglect Score &amp; Expansion Priority</div>
  <div class="s-desc">
    Composite neglect score (0–100) = SC/SW deficit &times; zone isolation penalty &times; scale factor.
    Higher = more urgently underserved. Treat this researcher-weighted score as a screening aid for expansion discussions.
  </div>
  <div class="g2">
    <div class="card"><div class="ctitle">Top {len(neg_labels)} Brand-Zone Combinations</div>
      <div id="p-neg"  class="plot" style="height:{max(320,len(neg_labels)*28+60)}px"></div></div>
    <div class="card"><div class="ctitle">SC vs Showrooms by City Tier</div>
      <div id="p-tier" class="plot" style="height:{max(320,len(neg_labels)*28+60)}px"></div>
      <div class="insight">City tiers are proxied from total dealer presence (Tier 1: 100+, Tier 2: 20–99, Tier 3: under 20), not Census population. Hero dominates the neglect list — its East, Central, South and North
        zone scores are all in the top 5. Fixing Hero's service network in these 4 zones alone
        would address the majority of the national SC gap.</div>
    </div>
  </div>
</div>

<div class="section">
  <div class="s-eye">07 &mdash; Indicative Financial Proxy</div>
  <div class="s-title">Network Gap Translation</div>
  <div class="s-desc">The source output estimates a proxy by multiplying positive showroom-minus-service-centre gaps by an assumed brand ASP and a 15% factor. This is not FADA-based lost revenue, does not establish customer diversion, and should be treated only as a scenario indicator.</div>
  <div class="g2">
    <div class="card"><div class="ctitle">Proxy by Brand (Rs. crore)</div><div id="p-leak-brand" class="plot" style="height:300px"></div></div>
    <div class="card"><div class="ctitle">Proxy by Zone (Rs. crore)</div><div id="p-leak-zone" class="plot" style="height:300px"></div></div>
  </div>
  <div class="insight warn"><strong>Interpretation:</strong> The project documents describe a FADA sales counterfactual, but no FADA input data is present. These plotted values reflect the current simplified network-gap proxy only.</div>
</div>

<div class="section">
  <div class="s-eye">08 &mdash; Hypothesis Evidence</div>
  <div class="s-title">Service Balance vs Regional Sales</div>
  <div class="card" style="padding:22px">
    <div style="font-size:14px;font-weight:600;color:#fafafa;margin-bottom:8px">Sales correlation is not yet supported by source data</div>
    <div style="font-size:12px;color:#71717a;line-height:1.8">The project database contains no FADA sales records. The available <code>correlation.json</code> contains manually populated demonstration indices, so it is excluded from the evidence charts. Add validated brand-by-state FADA retail units mapped through the shared zone definitions to calculate Pearson r, p-values, and the planned brand-zone scatter plot.</div>
  </div>
</div>

<div class="footer">
  Indian Motorcycle Brand Network Bottleneck Analysis &nbsp;&middot;&nbsp; IIM Sirmaur BMS 2025<br>
  Data: BikeWale.com (scraped {scrape_dt}) &nbsp;&middot;&nbsp;
  Models: SC/SW Ratio · Gini · Location Quotient · HHI · Moran's I · PCA · K-Means · Portfolio Quadrant<br>
  {brand_cnt} brands &nbsp;&middot;&nbsp; {city_cnt} cities &nbsp;&middot;&nbsp; 6 zones &nbsp;&middot;&nbsp;
  Built with Python · SQLite · Plotly.js
</div>

</div><!-- /page-overview -->

<div id="page-radius" class="page" style="display:none;padding:18px 24px">
  <div style="display:flex;justify-content:space-between;align-items:center;gap:12px;margin-bottom:12px">
    <div><div class="s-eye">09 &mdash; Spatial Coverage</div><div class="s-title">Interactive City Radius Explorer</div></div>
    <span style="color:#52525b;font-size:11px">All map data is embedded in this file</span>
  </div>
  <div style="font-size:12px;color:#71717a;margin-bottom:12px">Click the map to inspect brand network counts within 50 km or 75 km. This is a city-point radius map; no state boundary shapefile is present for a state choropleth. Map tiles require an internet connection.</div>
  <iframe title="Motorcycle dealer radius explorer" srcdoc="{MAP_SRCDOC}" style="width:100%;height:calc(100vh - 150px);min-height:620px;border:1px solid #27272a;border-radius:6px;background:#111113"></iframe>
</div>

{all_brand_tabs}

<!-- ══════════════════════════════════════════════════════════
     JAVASCRIPT
══════════════════════════════════════════════════════════ -->
<script>
const cfg = {{responsive:true, displayModeBar:false}};
const rendered = new Set();
const EXPLAINERS = {explainers_json};

// ── Tab system ──────────────────────────────────────────────
function showTab(tabId) {{
  document.querySelectorAll('.page').forEach(p => p.style.display = 'none');
  document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
  const page = document.getElementById('page-' + tabId);
  if (page) page.style.display = 'block';
  const btn = document.querySelector('[data-tab="' + tabId + '"]');
  if (btn) btn.classList.add('active');
  if (tabId === 'radius') {{
    const mapFrame = document.querySelector('#page-radius iframe');
    if (mapFrame && mapFrame.contentWindow) mapFrame.contentWindow.dispatchEvent(new Event('resize'));
  }}
  if (!rendered.has(tabId)) {{ renderCharts(tabId); rendered.add(tabId); }}
}}

function renderCharts(tabId) {{
  if (tabId === 'about') {{ return; }}
  if (tabId === 'overview') {{
    Plotly.newPlot('p-zone',       {C_ZONE},     {{}}, cfg);
    Plotly.newPlot('p-brand-ratio',{C_BRAND_RATIO},{{}},cfg);
    Plotly.newPlot('p-brand-size', {C_BRAND_SIZE},{{}},cfg);
    Plotly.newPlot('p-heat',       {C_HEAT},     {{}}, cfg);
    Plotly.newPlot('p-gini',       {C_GINI},     {{}}, cfg);
    Plotly.newPlot('p-hhi',        {C_HHI},      {{}}, cfg);
    Plotly.newPlot('p-lq',         {C_LQ},       {{}}, cfg);
    Plotly.newPlot('p-moran',      {C_MORAN},    {{}}, cfg);
    Plotly.newPlot('p-pca',        {C_PCA},      {{}}, cfg);
    Plotly.newPlot('p-clust',      {C_CLUST},    {{}}, cfg);
    Plotly.newPlot('p-quad',       {C_QUAD},     {{}}, cfg);
    Plotly.newPlot('p-neg',        {C_NEG},      {{}}, cfg);
    Plotly.newPlot('p-tier',       {C_TIER},     {{}}, cfg);
    Plotly.newPlot('p-leak-brand', {C_LEAK_BRAND},{{}},cfg);
    Plotly.newPlot('p-leak-zone',  {C_LEAK_ZONE},{{}},cfg);
    return;
  }}
  switch(tabId) {{
{brand_render_js}
  }}
}}

// Show about on load (no charts to render)
rendered.add('about');

// ── Model explainer system ─────────────────────────────────
function showExplainer(key) {{
  const e = EXPLAINERS[key];
  if (!e) return;
  document.getElementById('exp-icon').textContent  = e.icon || '📊';
  document.getElementById('exp-title').textContent = e.title;
  let html = '';
  html += `<div class="exp-section"><div class="exp-label">What it measures</div>
    <p class="exp-plain">${{e.plain}}</p></div>`;
  html += `<div class="exp-section"><div class="exp-label">Formula</div>
    <div class="exp-formula">${{e.formula}}</div>
    <div class="exp-formula-detail">${{e.formula_detail}}</div></div>`;
  html += `<div class="exp-section"><div class="exp-label">How to read the output</div>
    <div class="scale-rows">`;
  e.scale.forEach(s => {{
    html += `<div class="scale-row">
      <div class="scale-dot" style="background:${{s.color}}"></div>
      <div class="scale-range">${{s.range}}</div>
      <div class="scale-label">${{s.label}}</div>
    </div>`;
  }});
  html += `</div></div>`;
  html += `<div class="exp-why"><strong>Why it matters for this project:</strong><br>${{e.why}}</div>`;
  document.getElementById('exp-body').innerHTML = html;
  document.getElementById('exp-drawer').classList.add('open');
  document.getElementById('exp-overlay').classList.add('open');
}}

function closeExplainer() {{
  document.getElementById('exp-drawer').classList.remove('open');
  document.getElementById('exp-overlay').classList.remove('open');
}}

document.addEventListener('keydown', e => {{ if (e.key === 'Escape') closeExplainer(); }});
</script>
</body>
</html>"""

with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
    f.write(html)
print(f"Dashboard written: {OUTPUT_PATH}")
print(f"Charts: 15 overview + {5 * len(BRAND_LIST)} brand = {15 + 5 * len(BRAND_LIST)} total")
print(f"File size: {os.path.getsize(OUTPUT_PATH) / 1024:.0f} KB")
