"""
model4_moran.py — Moran's I: Spatial Autocorrelation of SC/SW Ratios
---------------------------------------------------------------------
Tests whether cities with poor SC/SW ratios are geographically clustered
(positive Moran's I) or randomly scattered (near zero).

A high positive Moran's I with p < 0.05 means network gaps form contiguous
spatial blocs — structurally worse than scattered gaps because entire
corridors are underserved.

Method:
    1. For each city, compute its aggregate SC/SW ratio across all brands.
    2. Build a spatial weights matrix W where w_ij = 1 if cities i and j
       are within DISTANCE_KM of each other (binary contiguity), else 0.
       Row-standardise: w_ij ← w_ij / Σ_j w_ij.
    3. Moran's I = (N/W) × [Σ_i Σ_j w_ij(x_i−x̄)(x_j−x̄)] / [Σ_i(x_i−x̄)²]
    4. Permutation test (999 random shuffles) gives empirical p-value.

Output: data/analysis/moran.json
"""

import os, sys
PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_DIR)

import numpy as np
import pandas as pd
from db_utils import get_conn, save_json, SNAPSHOT_DATE, EV_BRANDS_NO_SC

DISTANCE_KM  = 150      # threshold for spatial neighbourhood
N_PERMUT     = 999      # permutation test iterations
EARTH_R_KM   = 6371.0


def haversine(lat1, lon1, lat2, lon2) -> float:
    """Haversine great-circle distance in km."""
    lat1, lon1, lat2, lon2 = map(np.radians, [lat1, lon1, lat2, lon2])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = np.sin(dlat/2)**2 + np.cos(lat1)*np.cos(lat2)*np.sin(dlon/2)**2
    return 2 * EARTH_R_KM * np.arcsin(np.sqrt(a))


def morans_i(x: np.ndarray, W: np.ndarray) -> float:
    n    = len(x)
    xm   = x - x.mean()
    W_sum = W.sum()
    if W_sum == 0:
        return 0.0
    num  = (xm[:, None] * xm[None, :] * W).sum()
    den  = (xm ** 2).sum()
    return float((n / W_sum) * (num / den)) if den else 0.0


def run():
    conn = get_conn()

    # City-level SC/SW ratio (aggregate across brands, exclude EV brands for SC)
    rows = conn.execute(
        """
        SELECT city_slug, city, zone, lat, lon,
               SUM(CASE WHEN type='service'  THEN count ELSE 0 END) AS sc,
               SUM(CASE WHEN type='showroom' THEN count ELSE 0 END) AS sw
        FROM dealers
        WHERE scrape_date=?
          AND zone!='Unknown'
          AND brand NOT IN ({})
          AND lat IS NOT NULL
        GROUP BY city_slug
        HAVING sw > 0
        """.format(",".join(f"'{b}'" for b in EV_BRANDS_NO_SC)),
        (SNAPSHOT_DATE,)
    ).fetchall()

    conn.close()

    df = pd.DataFrame(rows, columns=["city_slug","city","zone","lat","lon","sc","sw"])
    df["ratio"] = (df["sc"] / df["sw"]).round(4)
    df = df.dropna(subset=["ratio","lat","lon"])

    n     = len(df)
    lats  = df["lat"].values
    lons  = df["lon"].values
    x     = df["ratio"].values

    print(f"  Cities with valid ratio + coordinates: {n}")

    # Build distance matrix and binary weights
    print(f"  Building {n}×{n} distance matrix (threshold {DISTANCE_KM} km)...")
    W = np.zeros((n, n), dtype=float)
    for i in range(n):
        for j in range(i+1, n):
            d = haversine(lats[i], lons[i], lats[j], lons[j])
            if d <= DISTANCE_KM:
                W[i, j] = W[j, i] = 1.0

    # Row-standardise
    row_sums = W.sum(axis=1, keepdims=True)
    row_sums[row_sums == 0] = 1
    W_std = W / row_sums

    # Observed Moran's I
    I_obs = morans_i(x, W_std)

    # Permutation test for p-value
    print(f"  Running {N_PERMUT} permutations...")
    rng   = np.random.default_rng(42)
    I_perm = np.array([morans_i(rng.permutation(x), W_std) for _ in range(N_PERMUT)])
    p_val  = float((np.abs(I_perm) >= np.abs(I_obs)).sum() + 1) / (N_PERMUT + 1)

    # Zone-level Moran's I
    zone_results = {}
    for zone in df["zone"].unique():
        mask   = df["zone"].values == zone
        idx    = np.where(mask)[0]
        if len(idx) < 5:
            continue
        W_z    = W_std[np.ix_(idx, idx)]
        x_z    = x[idx]
        r_sums = W_z.sum(axis=1, keepdims=True)
        r_sums[r_sums==0] = 1
        W_z    = W_z / r_sums
        zone_results[zone] = round(morans_i(x_z, W_z), 4)

    interpretation = (
        "Strong positive spatial clustering — network gaps form contiguous regions"
        if I_obs > 0.3
        else "Moderate spatial clustering — some geographic patterns in gaps"
        if I_obs > 0.1
        else "Weak / no spatial autocorrelation — gaps are broadly random"
        if I_obs >= -0.1
        else "Negative autocorrelation — gaps and surpluses are dispersed (chess-board pattern)"
    )

    result = {
        "moran_i":         round(I_obs, 4),
        "p_value":         round(p_val, 4),
        "significant":     bool(p_val < 0.05),
        "n_cities":        n,
        "distance_km":     DISTANCE_KM,
        "n_permutations":  N_PERMUT,
        "interpretation":  interpretation,
        "by_zone":         zone_results,
        "expected_i":      round(-1 / (n - 1), 4),
    }

    save_json(result, "moran.json")

    print()
    print(f"  Moran's I        : {I_obs:.4f}")
    print(f"  p-value          : {p_val:.4f}  {'** significant **' if p_val < 0.05 else '(not significant)'}")
    print(f"  Interpretation   : {interpretation}")
    print()
    print("  By zone:")
    for z, i in sorted(zone_results.items(), key=lambda x: -x[1]):
        print(f"    {z:<14} I = {i:.4f}")


if __name__ == "__main__":
    print("=== Model 4 — Moran's I Spatial Autocorrelation ===")
    run()
