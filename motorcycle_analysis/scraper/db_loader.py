"""
db_loader.py
------------
Loads the scraped BikeWale CSV + city coordinates into SQLite.

Steps performed:
  1. Create schema (all tables + indexes) if not already present
  2. Build a city lookup from city_coords.csv (lat, lon, state, zone)
  3. Insert dealer/service rows from bikewale_raw_*.csv
  4. Seed brand_asp from constants.ASP_BY_BRAND
  5. Print a summary

Field mapping (raw CSV → DB):
  city_masking  → city_slug
  city_name     → city
  record_type   → type
  count_found   → count_found (1/0)

Scrape date normalisation:
  The scrape ran across two calendar days (2026-06-07 / 2026-06-08).
  All rows are stored under the single canonical snapshot date SNAPSHOT_DATE
  below so that analysis queries using MAX(scrape_date) work cleanly.

Usage:
    python scraper/db_loader.py          # auto-finds latest bikewale_raw_*.csv
    python scraper/db_loader.py path/to/bikewale_raw_YYYY-MM-DD.csv
"""

import csv
import glob
import os
import re
import sqlite3
import sys

SCRIPT_DIR   = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR  = os.path.dirname(SCRIPT_DIR)
sys.path.insert(0, PROJECT_DIR)

from constants import DB_PATH, STATE_TO_ZONE, ASP_BY_BRAND

RAW_DIR      = os.path.join(PROJECT_DIR, "data", "raw")
COORDS_CSV   = os.path.join(RAW_DIR, "city_coords.csv")

# Canonical snapshot date for the entire scrape run
SNAPSHOT_DATE = "2026-06-09"

# ── schema ────────────────────────────────────────────────────────────────

SCHEMA = """
CREATE TABLE IF NOT EXISTS dealers (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    brand       TEXT    NOT NULL,
    city_slug   TEXT    NOT NULL,
    city        TEXT    NOT NULL,
    state       TEXT    NOT NULL DEFAULT '',
    zone        TEXT    NOT NULL DEFAULT 'Unknown',
    type        TEXT    NOT NULL CHECK(type IN ('showroom','service')),
    count       INTEGER NOT NULL DEFAULT 0,
    count_found INTEGER NOT NULL DEFAULT 1,
    url         TEXT,
    lat         REAL,
    lon         REAL,
    scrape_date TEXT    NOT NULL,
    UNIQUE(brand, city_slug, type, scrape_date)
);

CREATE TABLE IF NOT EXISTS fada_sales (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    brand       TEXT    NOT NULL,
    state       TEXT    NOT NULL,
    zone        TEXT    NOT NULL,
    year        INTEGER NOT NULL,
    month       INTEGER NOT NULL,
    units_sold  INTEGER NOT NULL,
    UNIQUE(brand, state, year, month)
);

CREATE TABLE IF NOT EXISTS brand_asp (
    brand               TEXT    NOT NULL,
    fiscal_year         INTEGER NOT NULL,
    avg_selling_price   INTEGER NOT NULL,
    source_note         TEXT,
    PRIMARY KEY (brand, fiscal_year)
);

CREATE TABLE IF NOT EXISTS city_tier (
    city        TEXT    NOT NULL,
    state       TEXT    NOT NULL,
    population  INTEGER,
    tier        INTEGER NOT NULL CHECK(tier IN (1,2,3)),
    PRIMARY KEY (city, state)
);

CREATE TABLE IF NOT EXISTS analysis_output (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    brand            TEXT    NOT NULL,
    zone             TEXT    NOT NULL,
    showrooms        INTEGER NOT NULL DEFAULT 0,
    service_centers  INTEGER NOT NULL DEFAULT 0,
    ratio            REAL,
    brand_baseline   REAL,
    deviation_pct    REAL,
    severity         TEXT,
    est_revenue_lost REAL,
    scrape_date      TEXT    NOT NULL,
    UNIQUE(brand, zone, scrape_date)
);

CREATE INDEX IF NOT EXISTS idx_dealers_brand_zone   ON dealers(brand, zone, scrape_date);
CREATE INDEX IF NOT EXISTS idx_dealers_city_slug    ON dealers(city_slug);
CREATE INDEX IF NOT EXISTS idx_dealers_scrape_date  ON dealers(scrape_date);
CREATE INDEX IF NOT EXISTS idx_dealers_lat_lon      ON dealers(lat, lon);
CREATE INDEX IF NOT EXISTS idx_fada_brand_state     ON fada_sales(brand, state, year, month);
CREATE INDEX IF NOT EXISTS idx_analysis_scrape      ON analysis_output(scrape_date);
"""

# ── state extraction from Nominatim display_name ──────────────────────────

# Nominatim display format (India):
#   "City, District, State, Pincode, India"   OR
#   "City, State, India"                       OR
#   "City, India"
# We walk backwards: skip "India", skip anything that looks like a pincode,
# take the first remaining token as state.

# Map Nominatim state spellings → our STATE_TO_ZONE keys
_STATE_ALIASES = {
    "Jammu and Kashmir":   "Jammu & Kashmir",
    "Andaman and Nicobar Islands": "Unknown",
    "Lakshadweep":         "Unknown",
    "Dadra and Nagar Haveli and Daman and Diu": "Unknown",
    "Chandigarh":          "Punjab",        # UT, treat as Punjab zone
    "Puducherry":          "Tamil Nadu",    # UT, treat as South
    "Daman and Diu":       "Unknown",
    "Dadra and Nagar Haveli": "Unknown",
}

def _parse_state(display_name: str) -> str:
    """Extract best-guess Indian state from a Nominatim display_name string."""
    if not display_name:
        return ""
    parts = [p.strip() for p in display_name.split(",")]
    # Remove trailing "India"
    if parts and parts[-1].strip().lower() == "india":
        parts = parts[:-1]
    # Remove pincodes (purely numeric tokens)
    parts = [p for p in parts if not re.fullmatch(r"\d{6}", p)]
    if not parts:
        return ""
    # The state is typically the last remaining token
    candidate = parts[-1].strip()
    # Apply alias map
    candidate = _STATE_ALIASES.get(candidate, candidate)
    return candidate

# ── city coords lookup ────────────────────────────────────────────────────

def build_coords_lookup() -> dict:
    """
    Returns dict keyed by city_masking:
      { "delhi": {"lat":28.61, "lon":77.21, "state":"Delhi", "zone":"North"}, ... }
    """
    lookup = {}
    if not os.path.exists(COORDS_CSV):
        print(f"  WARNING: {COORDS_CSV} not found — lat/lon/state will be empty.")
        return lookup

    with open(COORDS_CSV, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            state = _parse_state(row.get("nominatim_display", ""))
            zone  = STATE_TO_ZONE.get(state, "Unknown")
            lookup[row["city_masking"]] = {
                "lat":   float(row["lat"])  if row.get("lat")  else None,
                "lon":   float(row["lon"])  if row.get("lon")  else None,
                "state": state,
                "zone":  zone,
            }
    print(f"  Coords loaded: {len(lookup)} cities")
    return lookup

# ── CSV loader ────────────────────────────────────────────────────────────

def latest_csv() -> str | None:
    files = sorted(glob.glob(os.path.join(RAW_DIR, "bikewale_raw_*.csv")), reverse=True)
    return files[0] if files else None

def load_csv(conn: sqlite3.Connection, csv_path: str, coords: dict):
    print(f"Loading: {csv_path}")
    inserted = skipped = errors = 0

    with open(csv_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            masking = row.get("city_masking", row.get("city_slug", ""))
            geo     = coords.get(masking, {})

            state = geo.get("state", "")
            zone  = geo.get("zone",  "Unknown")
            lat   = geo.get("lat")
            lon   = geo.get("lon")

            try:
                conn.execute(
                    """
                    INSERT OR IGNORE INTO dealers
                        (brand, city_slug, city, state, zone, type,
                         count, count_found, url, lat, lon, scrape_date)
                    VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
                    """,
                    (
                        row["brand"],
                        masking,
                        row.get("city_name", row.get("city", masking)),
                        state,
                        zone,
                        row["record_type"],
                        int(row.get("count", 0) or 0),
                        1 if str(row.get("count_found", "1")) in ("1", "True", "true") else 0,
                        row.get("url", ""),
                        lat,
                        lon,
                        SNAPSHOT_DATE,        # normalise both dates to single snapshot
                    )
                )
                if conn.execute("SELECT changes()").fetchone()[0]:
                    inserted += 1
                else:
                    skipped += 1
            except Exception as exc:
                errors += 1
                print(f"  Row error ({row.get('brand')} / {masking}): {exc}")

    conn.commit()
    print(f"  Inserted : {inserted}")
    print(f"  Skipped  : {skipped}  (duplicates)")
    print(f"  Errors   : {errors}")

# ── ASP seed ─────────────────────────────────────────────────────────────

def seed_asp(conn: sqlite3.Connection):
    for brand, asp in ASP_BY_BRAND.items():
        conn.execute(
            """INSERT OR IGNORE INTO brand_asp
               (brand, fiscal_year, avg_selling_price, source_note)
               VALUES (?,?,?,?)""",
            (brand, 2024, asp,
             "FY2024 annual report or model-weighted avg — see constants.py")
        )
    conn.commit()
    print(f"brand_asp seeded: {len(ASP_BY_BRAND)} brands.")

# ── summary ───────────────────────────────────────────────────────────────

def summary(conn: sqlite3.Connection):
    print()
    print("=" * 60)
    print("  DATABASE SUMMARY")
    print("=" * 60)

    total, = conn.execute("SELECT COUNT(*) FROM dealers").fetchone()
    print(f"  Total dealer rows : {total:,}")

    snap_date, = conn.execute("SELECT MAX(scrape_date) FROM dealers").fetchone()
    print(f"  Snapshot date     : {snap_date}")

    with_coords, = conn.execute(
        "SELECT COUNT(*) FROM dealers WHERE lat IS NOT NULL"
    ).fetchone()
    print(f"  Rows with lat/lon : {with_coords:,}  ({100*with_coords/total:.1f}%)")

    print()
    print(f"  {'Brand':<20} {'Type':<10} {'Cities':>7}  {'Total count':>12}  {'Found':>6}")
    print(f"  {'-'*20} {'-'*10} {'-'*7}  {'-'*12}  {'-'*6}")

    rows = conn.execute(
        """
        SELECT brand, type,
               COUNT(DISTINCT city_slug) AS cities,
               SUM(count)               AS total_count,
               SUM(count_found)         AS found_rows
        FROM dealers
        WHERE scrape_date = ?
        GROUP BY brand, type
        ORDER BY brand, type
        """,
        (snap_date,)
    ).fetchall()

    for brand, typ, cities, total_count, found in rows:
        print(f"  {brand:<20} {typ:<10} {cities:>7}  {total_count:>12,}  {found:>6}")

    # Zone coverage
    print()
    print(f"  {'Zone':<12} {'Cities':>7}  {'SC total':>10}  {'SW total':>10}  {'Ratio':>7}")
    print(f"  {'-'*12} {'-'*7}  {'-'*10}  {'-'*10}  {'-'*7}")
    zone_rows = conn.execute(
        """
        SELECT zone,
               COUNT(DISTINCT city_slug) AS cities,
               SUM(CASE WHEN type='service'  THEN count ELSE 0 END) AS sc,
               SUM(CASE WHEN type='showroom' THEN count ELSE 0 END) AS sw
        FROM dealers
        WHERE scrape_date = ? AND zone != 'Unknown'
        GROUP BY zone
        ORDER BY zone
        """,
        (snap_date,)
    ).fetchall()

    for zone, cities, sc, sw in zone_rows:
        ratio = round(sc / sw, 2) if sw else 0
        print(f"  {zone:<12} {cities:>7}  {sc:>10,}  {sw:>10,}  {ratio:>7.2f}")

    print("=" * 60)
    print(f"  DB path: {DB_PATH}")
    print("=" * 60)

# ── main ──────────────────────────────────────────────────────────────────

def main():
    csv_path = sys.argv[1] if len(sys.argv) > 1 else latest_csv()
    if not csv_path or not os.path.exists(csv_path):
        print("No raw CSV found. Run bikewale_scraper.py first.")
        sys.exit(1)

    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")

    print("=== db_loader — BikeWale snapshot loader ===")
    print()

    print("Step 1: Schema")
    conn.executescript(SCHEMA)
    conn.commit()
    print("  Schema created / verified.")
    print()

    print("Step 2: City coordinates")
    coords = build_coords_lookup()
    print()

    print("Step 3: Dealer / service rows")
    load_csv(conn, csv_path, coords)
    print()

    print("Step 4: Brand ASP")
    seed_asp(conn)
    print()

    print("Step 5: Summary")
    summary(conn)

    conn.close()

if __name__ == "__main__":
    main()
