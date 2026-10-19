"""
model3_hhi.py — Herfindahl-Hirschman Index: Network Concentration
-----------------------------------------------------------------
Measures how concentrated each brand's dealer network is across cities.
A high HHI means the brand is packed into a few cities; a low HHI means
it is widely and evenly spread.

Formula (standard HHI × 10,000):
    HHI = Σ ( count_i / total_count )²  × 10,000

Scale (US DOJ guidelines, adapted):
    HHI < 1,500   → Dispersed (good geographic coverage)
    1,500–2,500   → Moderately concentrated
    HHI > 2,500   → Highly concentrated (metro-heavy)

Computed separately for service centres and showrooms.

Output: data/analysis/hhi.json
"""

import os, sys
PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_DIR)

import numpy as np
import pandas as pd
from db_utils import get_conn, load_city_pivot, save_json, EV_BRANDS_NO_SC
from constants import BRAND_LIST


def hhi(counts: np.ndarray) -> float:
    """Return HHI × 10,000 for a 1-D array of counts."""
    c = np.array(counts, dtype=float)
    c = c[c > 0]
    if c.sum() == 0:
        return 0.0
    shares = c / c.sum()
    return float((shares ** 2).sum() * 10_000)


def concentration_label(h: float) -> str:
    if h < 1_500:  return "Dispersed"
    if h < 2_500:  return "Moderate"
    return "Highly concentrated"


def run():
    conn  = get_conn()
    pivot = load_city_pivot(conn, exclude_ev_sc=True)

    results = []

    for brand in BRAND_LIST:
        bdf = pivot[pivot["brand"] == brand]
        sc  = bdf["service_count"].dropna().values
        sw  = bdf["showroom_count"].values

        h_sc = hhi(sc) if brand not in EV_BRANDS_NO_SC else None
        h_sw = hhi(sw)

        results.append({
            "brand":        brand,
            "hhi_sc":       round(h_sc, 1) if h_sc is not None else None,
            "hhi_sw":       round(h_sw, 1),
            "label_sc":     concentration_label(h_sc) if h_sc else "N/A (no SC data)",
            "label_sw":     concentration_label(h_sw),
            "city_count":   int(len(bdf)),
        })

    results.sort(key=lambda x: -(x["hhi_sw"]))

    save_json({
        "rankings":    results,
        "scale":       {"dispersed": 1500, "moderate": 2500},
        "methodology": "HHI = sum((city_share)^2) x 10000. City share = city count / brand total.",
    }, "hhi.json")

    conn.close()

    print()
    print(f"  {'Brand':<20} {'HHI SC':>9} {'HHI SW':>9}  SW Label")
    print(f"  {'-'*20} {'-'*9} {'-'*9}  {'-'*22}")
    for r in sorted(results, key=lambda x: -(x["hhi_sw"])):
        h_sc = f"{r['hhi_sc']:>9.1f}" if r["hhi_sc"] is not None else "      N/A"
        print(f"  {r['brand']:<20} {h_sc} {r['hhi_sw']:>9.1f}  {r['label_sw']}")


if __name__ == "__main__":
    print("=== Model 3 — Herfindahl-Hirschman Index ===")
    run()
