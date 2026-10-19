"""
bikewale_scraper.py
-------------------
One-shot scraper for BikeWale dealer-showroom and service-center counts.

HOW IT WORKS
  For each brand, calls /api/servicecenter/cities/make/{makeId}/ to get
  the list of cities where that brand has a service presence, then fetches:
    /service-centers/{brandMasking}/{cityMasking}/   -> service count
    /dealer-showrooms/{brandMasking}/{cityMasking}/  -> showroom count

  Count is extracted from the h1/h2 heading:
    "31 Royal Enfield service centers in Delhi"  -> 31
    "29 Royal Enfield dealers in Delhi"          -> 29

SNAPSHOT DESIGN
  Every record is stamped with SCRAPE_DATE (set once at run-start).
  A future re-run produces a new snapshot with a new date; the loader
  keeps both — analysis always reads WHERE scrape_date = MAX(scrape_date).

RESUME
  Progress is saved to data/raw/checkpoint.csv after every city.
  If the run is interrupted, just re-run — completed combos are skipped.
  Delete checkpoint.csv manually only if you want a full clean re-run.

Usage:
    python scraper/bikewale_scraper.py
"""

import csv, os, re, sys, time, random, logging, json
from datetime import date

import requests
from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout

# ── path setup ─────────────────────────────────────────────────────────────
SCRIPT_DIR  = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.dirname(SCRIPT_DIR)
sys.path.insert(0, PROJECT_DIR)

from constants import BRAND_LIST, BIKEWALE_BRAND_SLUG, BIKEWALE_MAKE_ID, STATE_TO_ZONE, CITIES

# ── config ─────────────────────────────────────────────────────────────────
SCRAPE_DATE     = date.today().isoformat()
RAW_DIR         = os.path.join(PROJECT_DIR, "data", "raw")
CHECKPOINT_FILE = os.path.join(RAW_DIR, "checkpoint.csv")
OUTPUT_FILE     = os.path.join(RAW_DIR, f"bikewale_raw_{SCRAPE_DATE}.csv")
DEBUG_DIR       = os.path.join(RAW_DIR, "debug")

BASE_URL        = "https://www.bikewale.com"
DELAY_MIN       = 2.5
DELAY_MAX       = 4.0
MAX_RETRIES     = 3
RETRY_BACKOFF   = 6     # seconds; doubles each retry

UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)

os.makedirs(RAW_DIR,   exist_ok=True)
os.makedirs(DEBUG_DIR, exist_ok=True)

# ── logging ────────────────────────────────────────────────────────────────
logging.basicConfig(
    level   = logging.INFO,
    format  = "%(asctime)s  %(levelname)-7s  %(message)s",
    datefmt = "%H:%M:%S",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(
            os.path.join(RAW_DIR, f"scrape_{SCRAPE_DATE}.log"),
            encoding="utf-8",
        ),
    ],
)
log = logging.getLogger(__name__)

# ── URL builders ────────────────────────────────────────────────────────────
def service_url(brand_masking: str, city_masking: str) -> str:
    return f"{BASE_URL}/service-centers/{brand_masking}/{city_masking}/"

def showroom_url(brand_masking: str, city_masking: str) -> str:
    return f"{BASE_URL}/dealer-showrooms/{brand_masking}/{city_masking}/"

def cities_api_url(make_id: str) -> str:
    return f"{BASE_URL}/api/servicecenter/cities/make/{make_id}/"

# ── count extraction ────────────────────────────────────────────────────────
# BikeWale renders the count in the first h1 or h2 on the page:
#   "31 Royal Enfield service centers in Delhi"
#   "29 Royal Enfield dealers in Delhi"
# We match the leading integer.

def extract_count(page) -> int | None:
    for sel in ["h1", "h2"]:
        try:
            for el in page.query_selector_all(sel):
                text = (el.inner_text() or "").strip()
                m = re.match(r"^(\d+)", text)
                if m:
                    return int(m.group(1))
        except Exception:
            pass
    return None

# ── city discovery ──────────────────────────────────────────────────────────
def fetch_brand_cities(brand: str) -> list[dict]:
    """
    Call the BikeWale cities API for a brand. Returns list of:
      {"cityMaskingName": "delhi", "cityName": "Delhi", "cityId": 10}

    Falls back to the hardcoded CITIES list if the API fails.
    """
    make_id = BIKEWALE_MAKE_ID.get(brand)
    if not make_id:
        log.warning("No makeId for brand %s — using hardcoded city list", brand)
        return _cities_from_constants()

    url = cities_api_url(make_id)
    try:
        r = requests.get(url, headers={"User-Agent": UA}, timeout=15)
        if r.status_code == 200:
            data = r.json()
            if isinstance(data, list) and data:
                log.info("  Cities API: %d cities for %s", len(data), brand)
                return data
    except Exception as exc:
        log.warning("  Cities API failed for %s: %s — falling back to constants", brand, exc)

    return _cities_from_constants()

def _cities_from_constants() -> list[dict]:
    """Convert the CITIES tuple list to the same dict format as the API."""
    return [
        {"cityMaskingName": slug, "cityName": name, "cityId": None}
        for slug, name, _ in CITIES
    ]

# ── checkpoint helpers ──────────────────────────────────────────────────────
CHECKPOINT_FIELDS = [
    "brand", "city_masking", "city_name", "record_type",
    "count", "count_found", "url", "scrape_date",
]

def load_checkpoint() -> set:
    done = set()
    if not os.path.exists(CHECKPOINT_FILE):
        return done
    with open(CHECKPOINT_FILE, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            done.add((row["brand"], row["city_masking"], row["record_type"]))
    return done

def append_checkpoint(row: dict):
    # Retry up to 8 times with short sleeps — guards against Windows file locks
    # (Defender, Explorer, or antivirus briefly locking the file mid-write).
    write_header = not os.path.exists(CHECKPOINT_FILE)
    for attempt in range(8):
        try:
            with open(CHECKPOINT_FILE, "a", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=CHECKPOINT_FIELDS)
                if write_header:
                    writer.writeheader()
                writer.writerow({k: row.get(k, "") for k in CHECKPOINT_FIELDS})
            return   # success
        except PermissionError:
            if attempt == 7:
                raise   # give up after 8 attempts
            wait = 2 * (attempt + 1)
            log.warning("  Checkpoint write locked (attempt %d/8) — retrying in %ds", attempt + 1, wait)
            time.sleep(wait)

# ── single-page fetch with retry ────────────────────────────────────────────
def fetch_count(page, url: str, brand: str, city: str, rec_type: str) -> int | None:
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            resp = page.goto(url, wait_until="networkidle", timeout=25_000)
            if resp and resp.status == 404:
                return 0     # brand not present in this city → count = 0

            count = extract_count(page)
            if count is not None:
                return count

            # Page loaded but count not in h1/h2 — save for inspection
            debug_path = os.path.join(
                DEBUG_DIR, f"{brand}_{city}_{rec_type}_a{attempt}.html"
            )
            with open(debug_path, "w", encoding="utf-8") as fh:
                fh.write(page.content())
            log.warning("  Count not found — debug HTML: %s", debug_path)
            return None

        except PWTimeout:
            log.warning("  Timeout attempt %d/%d: %s", attempt, MAX_RETRIES, url)
        except Exception as exc:
            log.warning("  Error attempt %d/%d: %s — %s", attempt, MAX_RETRIES, url, exc)

        if attempt < MAX_RETRIES:
            wait = RETRY_BACKOFF * (2 ** (attempt - 1))
            log.info("  Retrying in %ds ...", wait)
            time.sleep(wait)

    return None

# ── main ────────────────────────────────────────────────────────────────────
def run():
    done = load_checkpoint()
    log.info("Already completed: %d combos", len(done))

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        ctx     = browser.new_context(user_agent=UA)
        page    = ctx.new_page()

        for brand in BRAND_LIST:
            masking = BIKEWALE_BRAND_SLUG[brand]
            log.info("=== Brand: %s (masking=%s) ===", brand, masking)

            cities = fetch_brand_cities(brand)
            log.info("  %d cities to scrape", len(cities))

            for city_data in cities:
                city_masking = city_data.get("cityMaskingName", "")
                city_name    = city_data.get("cityName", city_masking)

                for rec_type in ("service", "showroom"):
                    key = (brand, city_masking, rec_type)
                    if key in done:
                        continue

                    if rec_type == "service":
                        url = service_url(masking, city_masking)
                    else:
                        url = showroom_url(masking, city_masking)

                    log.info("  [%s] %s / %s", rec_type, brand, city_masking)

                    count = fetch_count(page, url, brand, city_masking, rec_type)

                    row = {
                        "brand":        brand,
                        "city_masking": city_masking,
                        "city_name":    city_name,
                        "record_type":  rec_type,
                        "count":        count if count is not None else 0,
                        "count_found":  1 if count is not None else 0,
                        "url":          url,
                        "scrape_date":  SCRAPE_DATE,
                    }
                    append_checkpoint(row)
                    done.add(key)

                    time.sleep(random.uniform(DELAY_MIN, DELAY_MAX))

        browser.close()

    _write_output()

def _write_output():
    if not os.path.exists(CHECKPOINT_FILE):
        log.warning("No checkpoint file found — nothing to write.")
        return

    rows = []
    with open(CHECKPOINT_FILE, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    with open(OUTPUT_FILE, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=CHECKPOINT_FIELDS)
        writer.writeheader()
        writer.writerows(rows)

    log.info("Output: %s  (%d rows, scrape_date=%s)", OUTPUT_FILE, len(rows), SCRAPE_DATE)
    log.info("Next: python scraper/db_loader.py")

if __name__ == "__main__":
    log.info("=== BikeWale scraper — snapshot date: %s ===", SCRAPE_DATE)
    run()
    log.info("=== Done ===")
