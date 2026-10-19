"""
model7_quadrant.py — Portfolio Quadrant Matrix
-----------------------------------------------
Places each brand in one of four strategic quadrants based on two axes:

    X-axis: National SC/SW ratio  (service balance)
    Y-axis: Total network size    (scale = SC + SW across all cities)

Quadrants:
    Q1 — Leaders         high ratio + large network   (balanced at scale)
    Q2 — Overextended    low ratio  + large network   (selling > servicing)
    Q3 — Niche Strong    high ratio + small network   (balanced but limited)
    Q4 — Struggling      low ratio  + small network   (neither scaled nor balanced)

Thresholds are set at the median of each axis across all brands.

Also computes per-brand zone-quadrant placement (how a brand moves
across quadrants when you look zone-by-zone).

Output: data/analysis/quadrant.json
"""

import os, sys
PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_DIR)

import numpy as np
import pandas as pd
from db_utils import get_conn, load_brand_zone, save_json, EV_BRANDS_NO_SC
from constants import BRAND_LIST, ZONES


RATIO_THRESHOLD  = 1.0    # parity line
SIZE_THRESHOLD   = None   # set dynamically to median


def quadrant(ratio, size, ratio_thresh, size_thresh) -> str:
    if ratio is None:
        return "No data"
    high_r = ratio >= ratio_thresh
    high_s = size   >= size_thresh
    if high_r and high_s:   return "Q1 — Leader"
    if not high_r and high_s: return "Q2 — Overextended"
    if high_r and not high_s: return "Q3 — Niche Strong"
    return "Q4 — Struggling"


def run():
    conn = get_conn()
    bz   = load_brand_zone(conn)
    conn.close()

    # National brand-level aggregation
    national = []
    for brand in BRAND_LIST:
        brows  = bz[bz.brand == brand]
        sc     = int(brows["service_total"].sum())
        sw     = int(brows["showroom_total"].sum())
        ratio  = round(sc / sw, 4) if sw > 0 else None
        size   = sc + sw
        national.append({
            "brand": brand,
            "sc":    sc, "sw": sw,
            "ratio": ratio,
            "size":  size,
        })

    # Size threshold = median (exclude EV brands from threshold calc for SC)
    sizes       = [r["size"] for r in national if r["brand"] not in EV_BRANDS_NO_SC]
    size_thresh = float(np.median(sizes))
    ratios_v    = [r["ratio"] for r in national
                   if r["ratio"] is not None and r["brand"] not in EV_BRANDS_NO_SC]
    ratio_thresh = RATIO_THRESHOLD   # keep at 1.0 (parity) for cleaner interpretation

    for r in national:
        r["quadrant"]       = quadrant(r["ratio"], r["size"], ratio_thresh, size_thresh)
        r["ratio_thresh"]   = ratio_thresh
        r["size_thresh"]    = round(size_thresh, 0)

    national.sort(key=lambda x: (-(x["ratio"] or 0), -x["size"]))

    # Zone-level quadrant map per brand
    zone_map = {}
    for brand in BRAND_LIST:
        if brand in EV_BRANDS_NO_SC:
            continue
        zone_map[brand] = {}
        for zone in ZONES:
            cell = bz[(bz.brand==brand)&(bz.zone==zone)]
            if cell.empty:
                zone_map[brand][zone] = "No data"
                continue
            sc   = int(cell["service_total"].values[0])
            sw   = int(cell["showroom_total"].values[0])
            r    = sc/sw if sw>0 else None
            s    = sc+sw
            zone_map[brand][zone] = quadrant(r, s, ratio_thresh, size_thresh)

    save_json({
        "ratio_threshold":  ratio_thresh,
        "size_threshold":   round(size_thresh, 0),
        "national":         national,
        "zone_map":         zone_map,
        "quadrant_defs": {
            "Q1": "Leader — balanced network at scale",
            "Q2": "Overextended — more showrooms than can be serviced",
            "Q3": "Niche Strong — balanced but small footprint",
            "Q4": "Struggling — service-deficient and low scale",
        },
    }, "quadrant.json")

    # ── print ──────────────────────────────────────────────────────────────
    print()
    print(f"  Ratio threshold : {ratio_thresh}  |  Size threshold : {size_thresh:,.0f}")
    print()
    print(f"  {'Brand':<20} {'Ratio':>7} {'Size':>8}  Quadrant")
    print(f"  {'-'*20} {'-'*7} {'-'*8}  {'-'*24}")
    for r in national:
        ratio_str = f"{r['ratio']:.4f}" if r["ratio"] else "  N/A  "
        print(f"  {r['brand']:<20} {ratio_str:>7} {r['size']:>8,}  {r['quadrant']}")


if __name__ == "__main__":
    print("=== Model 7 — Portfolio Quadrant Matrix ===")
    run()
