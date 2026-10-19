"""
model2_lq.py — Location Quotient: Regional Over/Under-Representation
---------------------------------------------------------------------
Measures whether a brand is over- or under-represented in a zone
relative to its own national footprint.

Formula:
    LQ(brand, zone) = (SC_brand_zone / SC_brand_national)
                    / (SC_all_zone   / SC_all_national)

Interpretation:
    LQ > 1.25 → brand concentrates service infra here more than average
    0.75–1.25 → broadly proportional presence
    LQ < 0.75 → brand structurally under-present in this zone

Output: data/analysis/location_quotients.json
"""

import os, sys
PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_DIR)

import pandas as pd
from db_utils import get_conn, load_brand_zone, save_json, EV_BRANDS_NO_SC
from constants import BRAND_LIST, ZONES


def run():
    conn = get_conn()
    bz   = load_brand_zone(conn)

    # Use showroom counts (complete for all brands including EVs)
    # and service counts (excluding EV brands)
    records = []

    for metric, col, label in [
        ("showroom", "showroom_total", "Showroom LQ"),
        ("service",  "service_total",  "Service LQ"),
    ]:
        if metric == "service":
            bz_use = bz[~bz["brand"].isin(EV_BRANDS_NO_SC)].copy()
        else:
            bz_use = bz.copy()

        national_by_brand = bz_use.groupby("brand")[col].sum()
        national_by_zone  = bz_use.groupby("zone")[col].sum()
        national_total    = bz_use[col].sum()

        for brand in BRAND_LIST:
            if metric == "service" and brand in EV_BRANDS_NO_SC:
                continue
            nat_brand = national_by_brand.get(brand, 0)
            if nat_brand == 0:
                continue

            for zone in ZONES:
                cell = bz_use[(bz_use.brand == brand) & (bz_use.zone == zone)]
                val_bz  = int(cell[col].values[0]) if not cell.empty else 0
                nat_zone = int(national_by_zone.get(zone, 0))

                if national_total == 0 or nat_zone == 0:
                    lq = None
                else:
                    lq = round(
                        (val_bz / nat_brand) / (nat_zone / national_total), 3
                    )

                records.append({
                    "brand":  brand,
                    "zone":   zone,
                    "metric": metric,
                    "lq":     lq,
                    "label":  ("Over-concentrated" if lq and lq > 1.25
                               else "Proportional"   if lq and lq >= 0.75
                               else "Under-present"  if lq else "No data"),
                })

    df = pd.DataFrame(records)

    # Build matrix for JSON output
    sc_matrix, sw_matrix = [], []
    brands_use = [b for b in BRAND_LIST if b not in EV_BRANDS_NO_SC]

    for brand in brands_use:
        sc_row, sw_row = [], []
        for zone in ZONES:
            sc_val = df[(df.brand==brand)&(df.zone==zone)&(df.metric=="service")]["lq"]
            sw_val = df[(df.brand==brand)&(df.zone==zone)&(df.metric=="showroom")]["lq"]
            sc_row.append(float(sc_val.values[0]) if not sc_val.empty else None)
            sw_row.append(float(sw_val.values[0]) if not sw_val.empty else None)
        sc_matrix.append(sc_row)
        sw_matrix.append(sw_row)

    save_json({
        "brands":     brands_use,
        "zones":      ZONES,
        "sc_matrix":  sc_matrix,
        "sw_matrix":  sw_matrix,
        "records":    records,
        "thresholds": {"over_concentrated": 1.25, "under_present": 0.75},
    }, "location_quotients.json")

    conn.close()

    # ── print SC LQ matrix ─────────────────────────────────────────────────
    print()
    print("  Service Centre Location Quotients (>1.25=over, <0.75=under)")
    print(f"  {'Brand':<20} " + "  ".join(f"{z[:5]:>7}" for z in ZONES))
    print(f"  {'-'*20} " + "  ".join(["-"*7]*len(ZONES)))
    for brand, row in zip(brands_use, sc_matrix):
        vals = "  ".join(
            f"{v:>7.3f}" if v is not None else "    N/A" for v in row
        )
        print(f"  {brand:<20} {vals}")


if __name__ == "__main__":
    print("=== Model 2 — Location Quotient ===")
    run()
