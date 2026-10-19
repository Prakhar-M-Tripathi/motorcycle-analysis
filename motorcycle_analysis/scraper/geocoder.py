"""
geocoder.py
-----------
Geocodes every unique city in the scraped dataset using the OpenStreetMap
Nominatim API (free, no API key required).

HOW IT WORKS
  For each unique (city_masking, city_name) pair in bikewale_raw_*.csv:
    GET https://nominatim.openstreetmap.org/search
        ?q={city_name}, India
        &countrycodes=in
        &format=json
        &limit=1
  Extracts lat/lon from the first result.

RATE LIMIT
  Nominatim's terms require max 1 request per second and a descriptive
  User-Agent header. This script enforces both.

CHECKPOINT / RESUME
  Results are written to data/raw/city_coords.csv after every request.
  Re-running the script skips already-geocoded cities.

OUTPUT
  data/raw/city_coords.csv
  Fields: city_masking, city_name, lat, lon, found, nominatim_display

Usage:
    python scraper/geocoder.py
"""

import csv
import os
import sys
import time
import json
import urllib.request
import urllib.parse

SCRIPT_DIR  = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.dirname(SCRIPT_DIR)
sys.path.insert(0, PROJECT_DIR)

RAW_DIR      = os.path.join(PROJECT_DIR, "data", "raw")
INPUT_CSV    = os.path.join(RAW_DIR, "bikewale_raw_2026-06-09.csv")
COORDS_CSV   = os.path.join(RAW_DIR, "city_coords.csv")

NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
USER_AGENT    = "MotorcycleNetworkAnalysis/1.0 IIMSirmaur-BMS2025 (research project)"
DELAY         = 1.1   # seconds between requests — Nominatim requires >= 1s

FIELDS = ["city_masking", "city_name", "lat", "lon", "found", "nominatim_display"]

# ── load already-geocoded cities ───────────────────────────────────────────
def load_done():
    done = {}
    if not os.path.exists(COORDS_CSV):
        return done
    with open(COORDS_CSV, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            done[row["city_masking"]] = row
    return done

# ── append one result ──────────────────────────────────────────────────────
def append_result(row: dict):
    write_header = not os.path.exists(COORDS_CSV)
    with open(COORDS_CSV, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        if write_header:
            writer.writeheader()
        writer.writerow({k: row.get(k, "") for k in FIELDS})

# ── Nominatim query ────────────────────────────────────────────────────────
def geocode(city_name: str) -> dict | None:
    """
    Returns {"lat": float, "lon": float, "display": str} or None.
    Tries two queries:
      1. "{city_name}, India"
      2. "{city_name}"   (fallback — some older names not found with country tag)
    """
    queries = [
        f"{city_name}, India",
        city_name,
    ]
    for q in queries:
        params = urllib.parse.urlencode({
            "q":            q,
            "countrycodes": "in",
            "format":       "json",
            "limit":        1,
            "addressdetails": 0,
        })
        url = f"{NOMINATIM_URL}?{params}"
        req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read().decode())
            if data:
                return {
                    "lat":     float(data[0]["lat"]),
                    "lon":     float(data[0]["lon"]),
                    "display": data[0].get("display_name", ""),
                }
        except Exception as e:
            print(f"    WARNING: request failed for '{q}': {e}")
        time.sleep(DELAY)
    return None

# ── main ───────────────────────────────────────────────────────────────────
def run():
    # Read all unique (masking, name) pairs from raw CSV
    with open(INPUT_CSV, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    cities = {}
    for r in rows:
        m = r["city_masking"]
        if m not in cities:
            cities[m] = r["city_name"]

    total = len(cities)
    print(f"Unique cities to geocode: {total}")

    done = load_done()
    print(f"Already geocoded        : {len(done)}")
    print(f"Remaining               : {total - len(done)}")
    print()

    found_count = sum(1 for r in done.values() if r["found"] == "1")
    ok = found_count
    nf = len(done) - found_count
    idx = len(done)

    for masking, city_name in cities.items():
        if masking in done:
            continue

        idx += 1
        result = geocode(city_name)

        if result:
            row = {
                "city_masking":      masking,
                "city_name":         city_name,
                "lat":               f"{result['lat']:.6f}",
                "lon":               f"{result['lon']:.6f}",
                "found":             "1",
                "nominatim_display": result["display"][:120],
            }
            ok += 1
            status = f"OK  lat={result['lat']:.4f} lon={result['lon']:.4f}"
        else:
            row = {
                "city_masking":      masking,
                "city_name":         city_name,
                "lat":               "",
                "lon":               "",
                "found":             "0",
                "nominatim_display": "",
            }
            nf += 1
            status = "NOT FOUND"

        append_result(row)
        print(f"  [{idx:>3}/{total}] {city_name:<28} {status}")
        time.sleep(DELAY)

    # ── summary ───────────────────────────────────────────────────────────
    print()
    print("=" * 55)
    print(f"  Geocoding complete")
    print(f"  Found    : {ok} / {total}  ({100*ok/total:.1f}%)")
    print(f"  Not found: {nf} / {total}")
    print(f"  Output   : {COORDS_CSV}")
    print("=" * 55)

    if nf > 0:
        print()
        print("  Cities not found (may need manual coordinates):")
        with open(COORDS_CSV, newline="", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                if row["found"] == "0":
                    print(f"    - {row['city_name']} ({row['city_masking']})")

if __name__ == "__main__":
    print("=== Geocoder — OpenStreetMap Nominatim ===")
    print(f"Input : {INPUT_CSV}")
    print(f"Output: {COORDS_CSV}")
    print()
    run()
