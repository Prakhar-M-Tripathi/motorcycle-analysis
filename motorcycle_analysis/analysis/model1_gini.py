"""
model1_gini.py — Gini Coefficient: Network Inequality
------------------------------------------------------
Measures how unequally each brand distributes its service centres
across its cities. A Gini of 0 means perfectly equal distribution;
1 means all service centres are in a single city.

Formula (discrete Lorenz curve area method):
    Sort cities by SC count ascending.
    Gini = 1 − 2 × (area under Lorenz curve)
         = (2 × Σ i·y_i) / (n × Σ y_i) − (n+1)/n
    where y_i is the SC count of the i-th city (1-indexed, sorted asc).

Output: data/analysis/gini.json
"""

import os, sys
PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_DIR)

import numpy as np
import pandas as pd
from db_utils import get_conn, load_city_pivot, save_json, EV_BRANDS_NO_SC
from constants import BRAND_LIST


def gini_coefficient(values: np.ndarray) -> float:
    """Compute Gini coefficient for a 1-D array of non-negative values."""
    v = np.array(values, dtype=float)
    v = v[v >= 0]
    if v.sum() == 0 or len(v) < 2:
        return 0.0
    v_sorted = np.sort(v)
    n = len(v_sorted)
    idx = np.arange(1, n + 1)
    return float((2 * (idx * v_sorted).sum()) / (n * v_sorted.sum()) - (n + 1) / n)


def lorenz_curve(values: np.ndarray):
    """Return (cumulative population share, cumulative value share) for plotting."""
    v = np.sort(np.array(values, dtype=float))
    v = np.maximum(v, 0)
    cum_v   = np.cumsum(v)
    cum_pop = np.arange(1, len(v) + 1)
    return (cum_pop / cum_pop[-1]).tolist(), (cum_v / cum_v[-1]).tolist()


def run():
    conn  = get_conn()
    pivot = load_city_pivot(conn, exclude_ev_sc=True)

    results = []
    lorenz_data = {}

    for brand in BRAND_LIST:
        bdf = pivot[pivot["brand"] == brand].copy()
        sc  = bdf["service_count"].dropna().values
        sw  = bdf["showroom_count"].values

        g_sc = gini_coefficient(sc) if brand not in EV_BRANDS_NO_SC else None
        g_sw = gini_coefficient(sw)

        lc_x, lc_y = lorenz_curve(sw)
        lorenz_data[brand] = {"x": lc_x[::10], "y": lc_y[::10]}  # downsample for JSON

        results.append({
            "brand":      brand,
            "gini_sc":    round(g_sc, 4) if g_sc is not None else None,
            "gini_sw":    round(g_sw, 4),
            "cities":     int(len(bdf)),
            "note":       "SC data not captured on BikeWale"
                          if brand in EV_BRANDS_NO_SC else "",
        })

    results.sort(key=lambda x: -(x["gini_sw"]))

    save_json({"rankings": results, "lorenz": lorenz_data}, "gini.json")
    conn.close()

    # ── print ──────────────────────────────────────────────────────────────
    print()
    print(f"  {'Brand':<20} {'Gini SC':>9} {'Gini SW':>9}  Interpretation")
    print(f"  {'-'*20} {'-'*9} {'-'*9}  {'-'*30}")
    for r in sorted(results, key=lambda x: -(x["gini_sw"])):
        g_sc = f"{r['gini_sc']:.4f}" if r["gini_sc"] is not None else "  N/A  "
        interp = ("Very unequal" if r["gini_sw"] > 0.6
                  else "Moderately unequal" if r["gini_sw"] > 0.4
                  else "Fairly equal")
        print(f"  {r['brand']:<20} {g_sc:>9} {r['gini_sw']:>9.4f}  {interp}")


if __name__ == "__main__":
    print("=== Model 1 — Gini Coefficient ===")
    run()
