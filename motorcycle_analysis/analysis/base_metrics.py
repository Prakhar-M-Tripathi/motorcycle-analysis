"""
base_metrics.py
---------------
Computes core SC/SW ratios and writes the JSON files consumed by the
final dashboard. Must be run first — all other analysis scripts depend
on a consistent set of ratios.

Outputs (data/analysis/):
    kpis.json               — headline KPI card values
    zone_ratios.json        — per-zone avg ratio + totals
    brand_zone_matrix.json  — brands × zones ratio matrix
    revenue_leakage.json    — estimated leakage by brand and zone
    tier_split.json         — ratio + counts by city tier (proxy)
    neglect_scores.json     — composite neglect score per brand-zone

Also writes to analysis_output table in SQLite.
"""

import os, sys
PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_DIR)

import sqlite3
import pandas as pd
import numpy as np
from db_utils import get_conn, load_brand_zone, load_zone_summary, save_json, SNAPSHOT_DATE, EV_BRANDS_NO_SC
from constants import BRAND_LIST, ZONES, ASP_BY_BRAND, DB_PATH

# ── Tier proxy — classify cities by total dealer presence ─────────────────
# Without population data, we use total (SC+SW) count across all brands
# as a proxy for city size:  ≥100 → Tier 1,  20-99 → Tier 2,  <20 → Tier 3
TIER1_MIN = 100
TIER2_MIN = 20

def classify_tier(total_count: int) -> str:
    if total_count >= TIER1_MIN: return "Tier 1"
    if total_count >= TIER2_MIN: return "Tier 2"
    return "Tier 3"

# ── Neglect score weights ─────────────────────────────────────────────────
ZONE_ISOLATION = {
    "Northeast": 1.4, "Central": 1.15, "East": 1.1,
    "North": 1.0, "West": 1.0, "South": 1.0,
}

def run():
    conn = get_conn()

    bz   = load_brand_zone(conn)
    zone = load_zone_summary(conn)

    # ── KPIs ──────────────────────────────────────────────────────────────
    valid_ratios = bz[~bz["brand"].isin(EV_BRANDS_NO_SC)]["ratio"].dropna()
    avg_ratio    = round(float(valid_ratios.mean()), 3)
    bottleneck   = int((zone["ratio"] < 0.70).sum())

    # Revenue leakage — brand level
    leakage_brand = []
    for brand in BRAND_LIST:
        if brand in EV_BRANDS_NO_SC:
            continue
        brows = bz[bz["brand"] == brand]
        sw    = int(brows["showroom_total"].sum())
        sc    = int(brows["service_total"].sum())
        gap   = max(0, sw - sc)                  # showrooms > SC = gap
        asp   = ASP_BY_BRAND.get(brand, 100_000)
        # Conservative: each gap unit ~ 0.15 lost sales per year
        leakage_cr = round(gap * asp * 0.15 / 1e7, 1)
        leakage_brand.append({"brand": brand, "leakage_cr": leakage_cr})

    leakage_brand.sort(key=lambda x: -x["leakage_cr"])

    # Revenue leakage — zone level
    leakage_zone = []
    for _, zrow in zone.iterrows():
        gap   = max(0, int(zrow.showroom_total) - int(zrow.service_total))
        avg_asp = np.mean([ASP_BY_BRAND[b] for b in BRAND_LIST if b not in EV_BRANDS_NO_SC])
        leakage_cr = round(gap * avg_asp * 0.15 / 1e7, 1)
        leakage_zone.append({"zone": zrow.zone, "leakage_cr": leakage_cr})

    total_leakage = sum(x["leakage_cr"] for x in leakage_brand)

    save_json({
        "brand_count":         len(BRAND_LIST),
        "city_count":          int(conn.execute(
            "SELECT COUNT(DISTINCT city_slug) FROM dealers WHERE scrape_date=?",
            (SNAPSHOT_DATE,)).fetchone()[0]),
        "avg_ratio":           avg_ratio,
        "revenue_leakage_cr":  round(total_leakage, 0),
        "bottleneck_zones":    bottleneck,
        "scrape_date":         SNAPSHOT_DATE,
    }, "kpis.json")

    # ── Zone ratios ───────────────────────────────────────────────────────
    save_json([
        {
            "zone":            row.zone,
            "avg_ratio":       round(float(row.ratio), 3),
            "service_total":   int(row.service_total),
            "showroom_total":  int(row.showroom_total),
            "city_count":      int(row.city_count),
        }
        for _, row in zone.iterrows()
    ], "zone_ratios.json")

    # ── Brand × Zone matrix ───────────────────────────────────────────────
    brands_active = [b for b in BRAND_LIST if b not in EV_BRANDS_NO_SC]
    matrix = []
    for brand in brands_active:
        row_vals = []
        for z in ZONES:
            cell = bz[(bz.brand == brand) & (bz.zone == z)]
            if cell.empty or cell.iloc[0]["ratio"] is None:
                row_vals.append(None)
            else:
                row_vals.append(round(float(cell.iloc[0]["ratio"]), 3))
        matrix.append(row_vals)

    save_json({
        "brands": brands_active,
        "zones":  ZONES,
        "values": matrix,
    }, "brand_zone_matrix.json")

    # ── Revenue leakage ───────────────────────────────────────────────────
    save_json({
        "by_brand": leakage_brand,
        "by_zone":  leakage_zone,
    }, "revenue_leakage.json")

    # ── Tier split (proxy via dealer count) ───────────────────────────────
    city_totals = conn.execute(
        """
        SELECT city_slug,
               SUM(count) AS total_count,
               SUM(CASE WHEN type='service'  THEN count ELSE 0 END) AS sc,
               SUM(CASE WHEN type='showroom' THEN count ELSE 0 END) AS sw
        FROM dealers
        WHERE scrape_date=? AND zone!='Unknown'
        GROUP BY city_slug
        """,
        (SNAPSHOT_DATE,)
    ).fetchall()

    tier_data = {"Tier 1": {"sc":0,"sw":0,"cities":0},
                 "Tier 2": {"sc":0,"sw":0,"cities":0},
                 "Tier 3": {"sc":0,"sw":0,"cities":0}}

    for row in city_totals:
        t = classify_tier(row["total_count"] or 0)
        tier_data[t]["sc"]     += row["sc"] or 0
        tier_data[t]["sw"]     += row["sw"] or 0
        tier_data[t]["cities"] += 1

    tier_out = []
    for tier, vals in tier_data.items():
        ratio = round(vals["sc"] / vals["sw"], 3) if vals["sw"] else 0
        tier_out.append({
            "tier":           tier,
            "avg_ratio":      ratio,
            "service_count":  vals["sc"],
            "showroom_count": vals["sw"],
            "city_count":     vals["cities"],
        })

    save_json(tier_out, "tier_split.json")

    # ── Neglect scores ────────────────────────────────────────────────────
    neglect = []
    for _, row in bz[~bz["brand"].isin(EV_BRANDS_NO_SC)].iterrows():
        if row["ratio"] is None or row["showroom_total"] == 0:
            continue
        deficit   = max(0.0, 1.0 - float(row["ratio"]))     # 0 = at parity
        isolation = ZONE_ISOLATION.get(row["zone"], 1.0)
        scale_pen = min(1.0, float(row["showroom_total"]) / 50)  # bigger presence = higher penalty
        raw       = deficit * isolation * scale_pen * 100
        neglect.append({
            "label": f"{row['brand'].title().replace('-',' ')} / {row['zone']}",
            "brand": row["brand"],
            "zone":  row["zone"],
            "score": round(min(raw, 100), 1),
            "ratio": round(float(row["ratio"]), 3),
        })

    neglect.sort(key=lambda x: -x["score"])
    save_json(neglect[:20], "neglect_scores.json")

    # ── Write to analysis_output ──────────────────────────────────────────
    for _, row in bz.iterrows():
        brand_avg = float(bz[bz.brand == row.brand]["ratio"].mean()) if row.ratio else None
        dev       = round((float(row.ratio) - brand_avg) / brand_avg * 100, 2) \
                    if (row.ratio and brand_avg) else None
        sev       = ("healthy"    if row.ratio and row.ratio >= 1.0
                     else "mild"  if row.ratio and row.ratio >= 0.7
                     else "bottleneck") if row.ratio else "no-data"
        asp       = ASP_BY_BRAND.get(row.brand, 0)
        gap       = max(0, int(row.showroom_total) - int(row.service_total))
        rev_lost  = round(gap * asp * 0.15 / 1e7, 2)

        try:
            conn.execute(
                """
                INSERT OR REPLACE INTO analysis_output
                    (brand, zone, showrooms, service_centers, ratio,
                     brand_baseline, deviation_pct, severity,
                     est_revenue_lost, scrape_date)
                VALUES (?,?,?,?,?,?,?,?,?,?)
                """,
                (row.brand, row.zone,
                 int(row.showroom_total), int(row.service_total),
                 float(row.ratio) if row.ratio else None,
                 brand_avg, dev, sev, rev_lost, SNAPSHOT_DATE)
            )
        except Exception: pass

    conn.commit()
    conn.close()

    print()
    print("Base metrics complete.")
    _print_zone_table(zone)


def _print_zone_table(zone: pd.DataFrame):
    print()
    print(f"  {'Zone':<12} {'SC':>8} {'SW':>8} {'Ratio':>7}  Status")
    print(f"  {'-'*12} {'-'*8} {'-'*8} {'-'*7}  {'-'*12}")
    for _, r in zone.iterrows():
        status = "Healthy" if r.ratio >= 1.0 else "Mild gap" if r.ratio >= 0.70 else "Bottleneck"
        print(f"  {r.zone:<12} {int(r.service_total):>8,} {int(r.showroom_total):>8,} {r.ratio:>7.3f}  {status}")


if __name__ == "__main__":
    print("=== Base Metrics ===")
    run()
