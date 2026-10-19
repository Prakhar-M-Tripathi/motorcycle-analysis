"""
model6_clustering.py — K-Means Clustering: City Network Archetypes
-------------------------------------------------------------------
Groups cities into archetypes based on their multi-brand dealer profile.
Uses the same feature matrix as PCA (brand SC + SW counts per city).

Process:
    1. Standardise features (same as PCA).
    2. Run K-Means for k=2..8, pick optimal k via elbow + silhouette score.
    3. Label each cluster with a descriptive archetype name based on its
       mean feature profile.
    4. Compute cluster-level statistics.

Cluster archetypes (labelled after fitting):
    The script auto-labels clusters by inspecting dominant brands and
    overall network density in each cluster's centroid.

Output: data/analysis/clusters.json
"""

import os, sys
PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_DIR)

import numpy as np
import pandas as pd
from sklearn.preprocessing import StandardScaler
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score
from db_utils import get_conn, save_json, SNAPSHOT_DATE, EV_BRANDS_NO_SC
from constants import BRAND_LIST


# Archetype labels assigned after inspecting cluster centroids.
# High network density + multi-brand = Metro Hub
# Mass-market only (hero/honda/bajaj) = Legacy Stronghold
# Low across all = Thin Coverage / Peripheral
# EV-leaning (high ola/ather SW) = EV Pioneer
def label_cluster(centroid: np.ndarray, feature_cols: list) -> str:
    fc   = {c: v for c, v in zip(feature_cols, centroid)}
    total_sw = sum(fc.get(f"{b}_sw", 0) for b in BRAND_LIST)
    total_sc = sum(fc.get(f"{b}_sc", 0) for b in BRAND_LIST if b not in EV_BRANDS_NO_SC)
    mass_sw  = sum(fc.get(f"{b}_sw", 0) for b in ["hero","honda","bajaj"])
    ev_sw    = sum(fc.get(f"{b}_sw", 0) for b in ["ola-electric","ather"])
    prem_sw  = sum(fc.get(f"{b}_sw", 0) for b in ["royal-enfield","jawa"])

    if total_sw > 2.5:     return "Metro / Major Hub"
    if ev_sw > 0.8:        return "EV Pioneer City"
    if prem_sw > 0.8:      return "Premium Brand Stronghold"
    if mass_sw > 1.2:      return "Mass-Market Heartland"
    if total_sw < 0.3:     return "Peripheral / Thin Coverage"
    return "Mid-Tier Balanced"


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

    cities_meta = raw.drop_duplicates("city_slug")[["city_slug","city","zone"]].set_index("city_slug")
    feature_cols, frames = [], []

    for brand in BRAND_LIST:
        bdf = raw[raw["brand"]==brand][["city_slug","sc","sw"]].set_index("city_slug")
        bdf.columns = [f"{brand}_sc", f"{brand}_sw"]
        if brand in EV_BRANDS_NO_SC:
            bdf[f"{brand}_sc"] = 0
        feature_cols += list(bdf.columns)
        frames.append(bdf)

    wide     = cities_meta.join(frames, how="left").fillna(0)
    X_raw    = wide[feature_cols].values.astype(float)
    scaler   = StandardScaler()
    X        = scaler.fit_transform(X_raw)

    # Elbow + silhouette to find optimal k
    inertias, silhouettes = [], []
    K_range = range(2, 9)
    for k in K_range:
        km = KMeans(n_clusters=k, random_state=42, n_init=10)
        km.fit(X)
        inertias.append(float(km.inertia_))
        silhouettes.append(float(silhouette_score(X, km.labels_)))

    best_k = K_range[int(np.argmax(silhouettes))]
    print(f"  Optimal k = {best_k}  (silhouette = {max(silhouettes):.4f})")

    # Final model
    km_final   = KMeans(n_clusters=best_k, random_state=42, n_init=20)
    labels     = km_final.fit_predict(X)
    centroids  = scaler.inverse_transform(km_final.cluster_centers_)

    # Auto-label clusters
    cluster_labels = {i: label_cluster(centroids[i], feature_cols)
                      for i in range(best_k)}

    # City assignments
    city_assignments = []
    for i, (slug, meta) in enumerate(wide.iterrows()):
        city_assignments.append({
            "city_slug": slug,
            "city":      meta["city"],
            "zone":      meta["zone"],
            "cluster":   int(labels[i]),
            "archetype": cluster_labels[int(labels[i])],
        })

    # Cluster summary stats
    cluster_summary = []
    for k in range(best_k):
        mask   = labels == k
        subset = wide[mask]
        avg_sw = float(sum(subset[f"{b}_sw"].mean() for b in BRAND_LIST))
        avg_sc = float(sum(subset[f"{b}_sc"].mean()
                           for b in BRAND_LIST if b not in EV_BRANDS_NO_SC))
        zones  = pd.Series([c["zone"] for c in city_assignments if c["cluster"]==k])
        cluster_summary.append({
            "cluster":    k,
            "archetype":  cluster_labels[k],
            "n_cities":   int(mask.sum()),
            "avg_sw":     round(avg_sw, 2),
            "avg_sc":     round(avg_sc, 2),
            "top_zone":   zones.value_counts().index[0] if len(zones) else "N/A",
        })

    save_json({
        "optimal_k":       best_k,
        "silhouette_score": round(max(silhouettes), 4),
        "elbow": {
            "k_values":   list(K_range),
            "inertias":   [round(v,1) for v in inertias],
            "silhouettes":[round(v,4) for v in silhouettes],
        },
        "cluster_labels":   cluster_labels,
        "cluster_summary":  cluster_summary,
        "city_assignments": city_assignments,
    }, "clusters.json")

    print()
    print(f"  {'Cluster':<4} {'Archetype':<30} {'Cities':>7}  {'Avg SW':>7}  {'Avg SC':>7}")
    print(f"  {'-'*4} {'-'*30} {'-'*7}  {'-'*7}  {'-'*7}")
    for s in cluster_summary:
        print(f"  {s['cluster']:<4} {s['archetype']:<30} {s['n_cities']:>7}  {s['avg_sw']:>7.2f}  {s['avg_sc']:>7.2f}")


if __name__ == "__main__":
    print("=== Model 6 — K-Means Clustering ===")
    run()
