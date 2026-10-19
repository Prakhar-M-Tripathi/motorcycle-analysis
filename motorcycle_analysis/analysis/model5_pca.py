"""
model5_pca.py — Principal Component Analysis: City Network Profiles
--------------------------------------------------------------------
Reduces the high-dimensional per-brand dealer counts into 2 principal
components, revealing natural groupings of cities by their network
profile across all 9 brands.

Feature vector per city (18 features):
    [hero_sc, hero_sw, honda_sc, honda_sw, ..., jawa_sc, jawa_sw]
    EV brand SC columns are zeroed (no data) and noted as such.

Steps:
    1. Build city × 18-feature matrix (fill missing = 0).
    2. Standardise (mean=0, std=1) using sklearn StandardScaler.
    3. PCA → extract first 2 PCs (and up to 5 for variance table).
    4. Annotate each city with zone, dominant brand (highest showroom count).

Output: data/analysis/pca.json
"""

import os, sys
PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_DIR)

import numpy as np
import pandas as pd
from sklearn.preprocessing import StandardScaler
from sklearn.decomposition import PCA
from db_utils import get_conn, save_json, SNAPSHOT_DATE, EV_BRANDS_NO_SC
from constants import BRAND_LIST


def run():
    conn = get_conn()

    raw = pd.read_sql_query(
        """
        SELECT city_slug, city, zone, brand,
               SUM(CASE WHEN type='service'  THEN count ELSE 0 END) AS sc,
               SUM(CASE WHEN type='showroom' THEN count ELSE 0 END) AS sw
        FROM dealers
        WHERE scrape_date=? AND zone!='Unknown'
        GROUP BY city_slug, brand
        """,
        conn, params=(SNAPSHOT_DATE,)
    )
    conn.close()

    # Pivot to wide format
    cities_meta = raw.drop_duplicates("city_slug")[["city_slug","city","zone"]].set_index("city_slug")

    feature_cols = []
    frames = []

    for brand in BRAND_LIST:
        bdf = raw[raw["brand"]==brand][["city_slug","sc","sw"]].set_index("city_slug")
        bdf.columns = [f"{brand}_sc", f"{brand}_sw"]
        # Zero out SC for EV brands (no meaningful data)
        if brand in EV_BRANDS_NO_SC:
            bdf[f"{brand}_sc"] = 0
        feature_cols += list(bdf.columns)
        frames.append(bdf)

    wide = cities_meta.join(frames, how="left").fillna(0)
    features = wide[feature_cols].values.astype(float)

    # Standardise
    scaler = StandardScaler()
    X      = scaler.fit_transform(features)

    # PCA
    n_comp = min(5, X.shape[1], X.shape[0])
    pca    = PCA(n_components=n_comp, random_state=42)
    scores = pca.fit_transform(X)

    var_explained = [round(float(v), 4) for v in pca.explained_variance_ratio_]
    loadings      = pca.components_.tolist()           # shape: n_comp × n_features

    # Top 3 contributing features per PC
    pc_top_features = []
    for pc_idx in range(min(2, n_comp)):
        loads = np.abs(pca.components_[pc_idx])
        top   = np.argsort(loads)[::-1][:4]
        pc_top_features.append([feature_cols[i] for i in top])

    # City-level output
    city_points = []
    for i, (slug, meta) in enumerate(wide.iterrows()):
        dom_brand = max(
            BRAND_LIST,
            key=lambda b: float(wide.loc[slug, f"{b}_sw"]) if slug in wide.index else 0
        )
        city_points.append({
            "city_slug": slug,
            "city":      meta["city"],
            "zone":      meta["zone"],
            "pc1":       round(float(scores[i, 0]), 4),
            "pc2":       round(float(scores[i, 1]), 4),
            "dom_brand": dom_brand,
        })

    save_json({
        "variance_explained":     var_explained,
        "cumulative_variance":    [round(sum(var_explained[:i+1]),4) for i in range(len(var_explained))],
        "pc1_top_features":       pc_top_features[0] if pc_top_features else [],
        "pc2_top_features":       pc_top_features[1] if len(pc_top_features)>1 else [],
        "feature_names":          feature_cols,
        "cities":                 city_points,
        "n_cities":               len(city_points),
        "ev_note":                "SC columns for ola-electric and ather set to 0 (no BikeWale data)",
    }, "pca.json")

    print()
    print(f"  Features   : {len(feature_cols)}")
    print(f"  Cities     : {len(city_points)}")
    print()
    print("  Variance explained per component:")
    for i, v in enumerate(var_explained):
        bar = "█" * int(v * 40)
        print(f"    PC{i+1}  {v*100:5.1f}%  {bar}")
    print(f"\n  PC1 driven by: {', '.join(pc_top_features[0]) if pc_top_features else 'N/A'}")
    if len(pc_top_features) > 1:
        print(f"  PC2 driven by: {', '.join(pc_top_features[1])}")


if __name__ == "__main__":
    print("=== Model 5 — PCA ===")
    run()
