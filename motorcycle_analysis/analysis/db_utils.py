"""
db_utils.py
-----------
Shared database helpers used by every analysis script.
Provides one-call access to the two most common data shapes:
  - city-level pivot table (wide format, one row per city)
  - brand-zone aggregates
"""

import os
import sys
import sqlite3
import pandas as pd

PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_DIR)

from constants import DB_PATH, BRAND_LIST, ZONES

# EV brands whose service-center data is not captured on BikeWale.
# Included in showroom analysis but flagged / excluded from SC-ratio models.
EV_BRANDS_NO_SC = {"ola-electric", "ather"}

SNAPSHOT_DATE = "2026-06-09"


def get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def load_city_pivot(conn: sqlite3.Connection,
                    exclude_ev_sc: bool = True) -> pd.DataFrame:
    """
    Returns a DataFrame with one row per (city_slug, brand) combination.
    Columns: city_slug, city, zone, lat, lon, brand,
             service_count, showroom_count, ratio

    exclude_ev_sc: if True, sets service_count=NaN for EV brands with no SC data.
    """
    df = pd.read_sql_query(
        """
        SELECT
            d.city_slug, d.city, d.zone, d.lat, d.lon,
            d.brand,
            SUM(CASE WHEN d.type='service'  THEN d.count ELSE 0 END) AS service_count,
            SUM(CASE WHEN d.type='showroom' THEN d.count ELSE 0 END) AS showroom_count
        FROM dealers d
        WHERE d.scrape_date = ?
          AND d.zone != 'Unknown'
        GROUP BY d.city_slug, d.brand
        """,
        conn,
        params=(SNAPSHOT_DATE,)
    )

    # Ratio — guard divide-by-zero
    df["ratio"] = df.apply(
        lambda r: round(r.service_count / r.showroom_count, 4)
        if r.showroom_count > 0 else None,
        axis=1,
    )

    if exclude_ev_sc:
        mask = df["brand"].isin(EV_BRANDS_NO_SC)
        df.loc[mask, "service_count"] = float("nan")
        df.loc[mask, "ratio"]         = float("nan")

    return df


def load_brand_zone(conn: sqlite3.Connection) -> pd.DataFrame:
    """
    Returns a DataFrame aggregated at (brand, zone) level.
    Columns: brand, zone, service_total, showroom_total, city_count, ratio
    """
    df = pd.read_sql_query(
        """
        SELECT
            brand, zone,
            COUNT(DISTINCT city_slug)                                   AS city_count,
            SUM(CASE WHEN type='service'  THEN count ELSE 0 END)        AS service_total,
            SUM(CASE WHEN type='showroom' THEN count ELSE 0 END)        AS showroom_total
        FROM dealers
        WHERE scrape_date = ?
          AND zone != 'Unknown'
        GROUP BY brand, zone
        """,
        conn,
        params=(SNAPSHOT_DATE,)
    )
    df["ratio"] = df.apply(
        lambda r: round(r.service_total / r.showroom_total, 4)
        if r.showroom_total > 0 else None,
        axis=1,
    )
    return df


def load_zone_summary(conn: sqlite3.Connection) -> pd.DataFrame:
    """Zone-level aggregation across all brands."""
    df = pd.read_sql_query(
        """
        SELECT
            zone,
            COUNT(DISTINCT city_slug)                              AS city_count,
            SUM(CASE WHEN type='service'  THEN count ELSE 0 END)  AS service_total,
            SUM(CASE WHEN type='showroom' THEN count ELSE 0 END)  AS showroom_total
        FROM dealers
        WHERE scrape_date = ?
          AND zone != 'Unknown'
        GROUP BY zone
        ORDER BY zone
        """,
        conn,
        params=(SNAPSHOT_DATE,)
    )
    df["ratio"] = (df.service_total / df.showroom_total).round(4)
    return df


def save_json(data, filename: str):
    """Write data to data/analysis/{filename}."""
    import json
    out_dir = os.path.join(PROJECT_DIR, "data", "analysis")
    os.makedirs(out_dir, exist_ok=True)
    path = os.path.join(out_dir, filename)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    print(f"  Saved: data/analysis/{filename}")
    return path
