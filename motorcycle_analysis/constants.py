# constants.py
# Single source of truth for the entire project.
# Every analysis script imports from here. Nothing is hardcoded elsewhere.
# MRD reference: Section 1.3, 2.4, 3.7, 5.2, 5.6 (golden rule)

# ── Brands ─────────────────────────────────────────────────────────────────

BRAND_LIST = [
    "hero",
    "honda",
    "bajaj",
    "royal-enfield",
    "yamaha",
    "suzuki",
    "ola-electric",
    "ather",
    "jawa",
]
# TVS and KTM excluded: BikeWale's service-center cities API returned only
# 3 cities (TVS) and 5 cities (KTM) — clearly incomplete platform coverage,
# not reflective of real network size. Including them would skew ratio analysis.

# Human-readable display names keyed by slug
BRAND_DISPLAY = {
    "hero":          "Hero MotoCorp",
    "honda":         "Honda (HMSI)",
    "bajaj":         "Bajaj Auto",
    "royal-enfield": "Royal Enfield",
    "yamaha":        "Yamaha",
    "suzuki":        "Suzuki",
    "ola-electric":  "Ola Electric",
    "ather":         "Ather Energy",
    "jawa":          "Jawa",
}

# BikeWale URL maskings — used in both /dealer-showrooms/{masking}/{city}/
# and /service-centers/{masking}/{city}/.
# Also the makeId is used by /api/servicecenter/cities/make/{makeId}/
# to discover which cities a brand has a presence in.
# Source: extracted from BikeWale's own service page dropdown (api_test.py).
BIKEWALE_BRAND_SLUG = {
    "hero":          "hero",
    "honda":         "honda",
    "bajaj":         "bajaj",
    "royal-enfield": "royalenfield",
    "yamaha":        "yamaha",
    "suzuki":        "suzuki",
    "ola-electric":  "ola",
    "ather":         "ather",
    "jawa":          "jawa",
}

# BikeWale internal makeId — used by the cities discovery API
BIKEWALE_MAKE_ID = {
    "hero":          "6",
    "honda":         "7",
    "bajaj":         "1",
    "royal-enfield": "11",
    "yamaha":        "13",
    "suzuki":        "12",
    "ola-electric":  "101",
    "ather":         "79",
    "jawa":          "82",
}

# ── Average Selling Price ─────────────────────────────────────────────────
# Source: FY2024 annual reports — Revenue (INR Cr) ÷ Units sold (domestic 2W)
# For private companies (Yamaha India, Suzuki India, Ola, Ather, Jawa):
#   weighted average of official model prices from brand price lists (June 2024)
# Present revenue leakage as a range ±15% of this estimate (MRD §5, caveat)

ASP_BY_BRAND = {
    "hero":          73_000,   # FY24: ~₹38,896 Cr / ~5.33M units
    "honda":         72_000,   # FY24 estimate (HMSI is unlisted; Honda Motor Co. India segment)
    "bajaj":         97_000,   # FY24: domestic 2W revenue / domestic volumes
    "royal-enfield": 1_80_000, # FY24: ~₹16,100 Cr / ~9.1L units
    "yamaha":        85_000,   # Weighted avg: FZ series, R15, MT-15, Ray-ZR
    "suzuki":        82_000,   # Weighted avg: Access 125, Gixxer, Avenis
    "ola-electric":  1_18_000, # Weighted avg: S1 Air / S1 / S1 Pro (June 2024 prices)
    "ather":         1_45_000, # Weighted avg: 450S / 450X (June 2024 prices)
    "jawa":          1_85_000, # Weighted avg: Jawa 42 / Classic 350 / Perak
}

# ── Geographic Zone Mapping ───────────────────────────────────────────────
# Defined once here; imported by every script that touches zones.
# MRD §1.3 — critical rule: never define zone assignments elsewhere.

STATE_TO_ZONE = {
    # North
    "Delhi":               "North",
    "Uttar Pradesh":       "North",
    "Haryana":             "North",
    "Punjab":              "North",
    "Rajasthan":           "North",
    "Himachal Pradesh":    "North",
    "Uttarakhand":         "North",
    "Jammu & Kashmir":     "North",
    "Ladakh":              "North",
    # South
    "Tamil Nadu":          "South",
    "Karnataka":           "South",
    "Kerala":              "South",
    "Andhra Pradesh":      "South",
    "Telangana":           "South",
    # West
    "Maharashtra":         "West",
    "Gujarat":             "West",
    "Goa":                 "West",
    # Central (tracked separately; sometimes merged with West in brand reporting)
    "Madhya Pradesh":      "Central",
    "Chhattisgarh":        "Central",
    # East
    "West Bengal":         "East",
    "Odisha":              "East",
    "Jharkhand":           "East",
    "Bihar":               "East",
    # Northeast
    "Assam":               "Northeast",
    "Meghalaya":           "Northeast",
    "Manipur":             "Northeast",
    "Mizoram":             "Northeast",
    "Tripura":             "Northeast",
    "Nagaland":            "Northeast",
    "Arunachal Pradesh":   "Northeast",
    "Sikkim":              "Northeast",
}

ZONES = ["North", "South", "West", "Central", "East", "Northeast"]

# Isolated states used in Analysis 10 (neglect score)
ISOLATED_STATES = [
    "Assam", "Meghalaya", "Manipur", "Mizoram", "Tripura",
    "Nagaland", "Arunachal Pradesh", "Sikkim",
    "Himachal Pradesh", "Uttarakhand", "Jammu & Kashmir", "Ladakh",
]

# ── City Tier Thresholds ──────────────────────────────────────────────────
# Population thresholds for city tier classification (MRD §4, Analysis 12)
# Tier 1: metro (≥10 lakh), Tier 2: urban (1–10 lakh), Tier 3: semi-urban/rural (<1 lakh)

TIER_THRESHOLDS = {
    1: 1_000_000,   # ≥ 10 lakh → Tier 1
    2: 100_000,     # 1 lakh to 10 lakh → Tier 2
    # below 1 lakh → Tier 3
}

def get_tier(population: int) -> int:
    if population >= TIER_THRESHOLDS[1]:
        return 1
    elif population >= TIER_THRESHOLDS[2]:
        return 2
    return 3

# ── Spatial Coverage Radii ────────────────────────────────────────────────
# Acceptable travel radius per city tier (km, Haversine / crow-flies)
# Actual road distance ≈ 1.2–2x Haversine; treat these as conservative lower bounds.
# MRD §5.2

RADIUS_BY_TIER = {
    1: 25,   # Tier 1 metro: dense urban, short travel
    2: 50,   # Tier 2 urban: moderate connectivity
    3: 75,   # Tier 3 rural: poor roads, longest acceptable travel
}

# ── Bottleneck Severity Thresholds ───────────────────────────────────────
# Applied to D(b,z) = deviation from brand baseline (Analysis 4)
# Negative means worse than brand average; positive means better.

SEVERITY_THRESHOLDS = {
    "None":     -30,   # D >= -30%  → No bottleneck
    "Mild":     -50,   # -50% <= D < -30%
    "Moderate": -70,   # -70% <= D < -50%
    "Severe":  None,   # D < -70%
}

def classify_severity(deviation_pct: float) -> str:
    if deviation_pct >= -30:
        return "None"
    elif deviation_pct >= -50:
        return "Mild"
    elif deviation_pct >= -70:
        return "Moderate"
    return "Severe"

# ── Database Path ─────────────────────────────────────────────────────────

import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH  = os.path.join(BASE_DIR, "db", "motorcycle_analysis.db")

# ── Cities to Scrape ─────────────────────────────────────────────────────
# State capitals + district HQs + major tier-2/3 towns.
# Covers ~320 cities across all 28 states + 8 UTs in scope.
# Format: (bikewale_url_slug, display_name, state)
# Slugs are lowercase-hyphenated as BikeWale uses them in URLs.

CITIES = [

    # ── DELHI ──────────────────────────────────────────────────────────────
    ("delhi",               "Delhi",               "Delhi"),

    # ── UTTAR PRADESH (75 districts — largest state) ───────────────────────
    ("lucknow",             "Lucknow",             "Uttar Pradesh"),
    ("kanpur",              "Kanpur",              "Uttar Pradesh"),
    ("agra",                "Agra",                "Uttar Pradesh"),
    ("varanasi",            "Varanasi",            "Uttar Pradesh"),
    ("meerut",              "Meerut",              "Uttar Pradesh"),
    ("prayagraj",           "Prayagraj",           "Uttar Pradesh"),
    ("ghaziabad",           "Ghaziabad",           "Uttar Pradesh"),
    ("noida",               "Noida",               "Uttar Pradesh"),
    ("aligarh",             "Aligarh",             "Uttar Pradesh"),
    ("bareilly",            "Bareilly",            "Uttar Pradesh"),
    ("moradabad",           "Moradabad",           "Uttar Pradesh"),
    ("saharanpur",          "Saharanpur",          "Uttar Pradesh"),
    ("gorakhpur",           "Gorakhpur",           "Uttar Pradesh"),
    ("jhansi",              "Jhansi",              "Uttar Pradesh"),
    ("mathura",             "Mathura",             "Uttar Pradesh"),
    ("ayodhya",             "Ayodhya",             "Uttar Pradesh"),
    ("firozabad",           "Firozabad",           "Uttar Pradesh"),
    ("rampur",              "Rampur",              "Uttar Pradesh"),
    ("shahjahanpur",        "Shahjahanpur",        "Uttar Pradesh"),
    ("muzaffarnagar",       "Muzaffarnagar",       "Uttar Pradesh"),
    ("bulandshahr",         "Bulandshahr",         "Uttar Pradesh"),
    ("lakhimpur",           "Lakhimpur",           "Uttar Pradesh"),
    ("sitapur",             "Sitapur",             "Uttar Pradesh"),
    ("hardoi",              "Hardoi",              "Uttar Pradesh"),
    ("unnao",               "Unnao",               "Uttar Pradesh"),
    ("rae-bareli",          "Rae Bareli",          "Uttar Pradesh"),
    ("sultanpur",           "Sultanpur",           "Uttar Pradesh"),
    ("jaunpur",             "Jaunpur",             "Uttar Pradesh"),
    ("mirzapur",            "Mirzapur",            "Uttar Pradesh"),
    ("azamgarh",            "Azamgarh",            "Uttar Pradesh"),
    ("ballia",              "Ballia",              "Uttar Pradesh"),
    ("basti",               "Basti",               "Uttar Pradesh"),
    ("deoria",              "Deoria",              "Uttar Pradesh"),
    ("banda",               "Banda",               "Uttar Pradesh"),
    ("etawah",              "Etawah",              "Uttar Pradesh"),
    ("mainpuri",            "Mainpuri",            "Uttar Pradesh"),
    ("hapur",               "Hapur",               "Uttar Pradesh"),

    # ── RAJASTHAN (33 districts) ───────────────────────────────────────────
    ("jaipur",              "Jaipur",              "Rajasthan"),
    ("jodhpur",             "Jodhpur",             "Rajasthan"),
    ("kota",                "Kota",                "Rajasthan"),
    ("udaipur",             "Udaipur",             "Rajasthan"),
    ("ajmer",               "Ajmer",               "Rajasthan"),
    ("bikaner",             "Bikaner",             "Rajasthan"),
    ("alwar",               "Alwar",               "Rajasthan"),
    ("bharatpur",           "Bharatpur",           "Rajasthan"),
    ("bhilwara",            "Bhilwara",            "Rajasthan"),
    ("sikar",               "Sikar",               "Rajasthan"),
    ("pali",                "Pali",                "Rajasthan"),
    ("chittorgarh",         "Chittorgarh",         "Rajasthan"),
    ("nagaur",              "Nagaur",              "Rajasthan"),
    ("tonk",                "Tonk",                "Rajasthan"),
    ("barmer",              "Barmer",              "Rajasthan"),
    ("jhalawar",            "Jhalawar",            "Rajasthan"),
    ("hanumangarh",         "Hanumangarh",         "Rajasthan"),
    ("ganganagar",          "Ganganagar",          "Rajasthan"),
    ("dausa",               "Dausa",               "Rajasthan"),
    ("sawai-madhopur",      "Sawai Madhopur",      "Rajasthan"),

    # ── HARYANA (22 districts) ─────────────────────────────────────────────
    ("gurugram",            "Gurugram",            "Haryana"),
    ("faridabad",           "Faridabad",           "Haryana"),
    ("rohtak",              "Rohtak",              "Haryana"),
    ("hisar",               "Hisar",               "Haryana"),
    ("panipat",             "Panipat",             "Haryana"),
    ("karnal",              "Karnal",              "Haryana"),
    ("ambala",              "Ambala",              "Haryana"),
    ("yamunanagar",         "Yamunanagar",         "Haryana"),
    ("sirsa",               "Sirsa",               "Haryana"),
    ("bhiwani",             "Bhiwani",             "Haryana"),
    ("sonepat",             "Sonepat",             "Haryana"),
    ("rewari",              "Rewari",              "Haryana"),
    ("jhajjar",             "Jhajjar",             "Haryana"),
    ("kurukshetra",         "Kurukshetra",         "Haryana"),

    # ── PUNJAB (23 districts) ─────────────────────────────────────────────
    ("chandigarh",          "Chandigarh",          "Punjab"),
    ("ludhiana",            "Ludhiana",            "Punjab"),
    ("amritsar",            "Amritsar",            "Punjab"),
    ("patiala",             "Patiala",             "Punjab"),
    ("jalandhar",           "Jalandhar",           "Punjab"),
    ("bathinda",            "Bathinda",            "Punjab"),
    ("mohali",              "Mohali",              "Punjab"),
    ("hoshiarpur",          "Hoshiarpur",          "Punjab"),
    ("pathankot",           "Pathankot",           "Punjab"),
    ("moga",                "Moga",                "Punjab"),
    ("firozpur",            "Firozpur",            "Punjab"),
    ("sangrur",             "Sangrur",             "Punjab"),
    ("gurdaspur",           "Gurdaspur",           "Punjab"),

    # ── HIMACHAL PRADESH (12 districts) ───────────────────────────────────
    ("shimla",              "Shimla",              "Himachal Pradesh"),
    ("dharamsala",          "Dharamsala",          "Himachal Pradesh"),
    ("mandi",               "Mandi",               "Himachal Pradesh"),
    ("solan",               "Solan",               "Himachal Pradesh"),
    ("kullu",               "Kullu",               "Himachal Pradesh"),
    ("hamirpur",            "Hamirpur",            "Himachal Pradesh"),
    ("una",                 "Una",                 "Himachal Pradesh"),
    ("chamba",              "Chamba",              "Himachal Pradesh"),
    ("bilaspur-hp",         "Bilaspur (HP)",       "Himachal Pradesh"),

    # ── UTTARAKHAND (13 districts) ────────────────────────────────────────
    ("dehradun",            "Dehradun",            "Uttarakhand"),
    ("haridwar",            "Haridwar",            "Uttarakhand"),
    ("roorkee",             "Roorkee",             "Uttarakhand"),
    ("rishikesh",           "Rishikesh",           "Uttarakhand"),
    ("haldwani",            "Haldwani",            "Uttarakhand"),
    ("rudrapur",            "Rudrapur",            "Uttarakhand"),
    ("kashipur",            "Kashipur",            "Uttarakhand"),
    ("nainital",            "Nainital",            "Uttarakhand"),
    ("almora",              "Almora",              "Uttarakhand"),
    ("pithoragarh",         "Pithoragarh",         "Uttarakhand"),

    # ── JAMMU & KASHMIR ────────────────────────────────────────────────────
    ("srinagar",            "Srinagar",            "Jammu & Kashmir"),
    ("jammu",               "Jammu",               "Jammu & Kashmir"),
    ("anantnag",            "Anantnag",            "Jammu & Kashmir"),
    ("baramulla",           "Baramulla",           "Jammu & Kashmir"),
    ("udhampur",            "Udhampur",            "Jammu & Kashmir"),
    ("kathua",              "Kathua",              "Jammu & Kashmir"),

    # ── LADAKH ─────────────────────────────────────────────────────────────
    ("leh",                 "Leh",                 "Ladakh"),
    ("kargil",              "Kargil",              "Ladakh"),

    # ── TAMIL NADU (38 districts) ─────────────────────────────────────────
    ("chennai",             "Chennai",             "Tamil Nadu"),
    ("coimbatore",          "Coimbatore",          "Tamil Nadu"),
    ("madurai",             "Madurai",             "Tamil Nadu"),
    ("tiruchirappalli",     "Tiruchirappalli",     "Tamil Nadu"),
    ("salem",               "Salem",               "Tamil Nadu"),
    ("tirunelveli",         "Tirunelveli",         "Tamil Nadu"),
    ("vellore",             "Vellore",             "Tamil Nadu"),
    ("tiruppur",            "Tiruppur",            "Tamil Nadu"),
    ("erode",               "Erode",               "Tamil Nadu"),
    ("thanjavur",           "Thanjavur",           "Tamil Nadu"),
    ("tuticorin",           "Tuticorin",           "Tamil Nadu"),
    ("kancheepuram",        "Kancheepuram",        "Tamil Nadu"),
    ("dindigul",            "Dindigul",            "Tamil Nadu"),
    ("hosur",               "Hosur",               "Tamil Nadu"),
    ("nagercoil",           "Nagercoil",           "Tamil Nadu"),
    ("cuddalore",           "Cuddalore",           "Tamil Nadu"),
    ("karur",               "Karur",               "Tamil Nadu"),
    ("namakkal",            "Namakkal",            "Tamil Nadu"),
    ("pollachi",            "Pollachi",            "Tamil Nadu"),
    ("kumbakonam",          "Kumbakonam",          "Tamil Nadu"),
    ("pudukkottai",         "Pudukkottai",         "Tamil Nadu"),
    ("ramanathapuram",      "Ramanathapuram",      "Tamil Nadu"),
    ("virudhunagar",        "Virudhunagar",        "Tamil Nadu"),
    ("sivakasi",            "Sivakasi",            "Tamil Nadu"),
    ("tiruvannamalai",      "Tiruvannamalai",      "Tamil Nadu"),
    ("krishnagiri",         "Krishnagiri",         "Tamil Nadu"),
    ("dharmapuri",          "Dharmapuri",          "Tamil Nadu"),

    # ── KARNATAKA (31 districts) ──────────────────────────────────────────
    ("bengaluru",           "Bengaluru",           "Karnataka"),
    ("mysuru",              "Mysuru",              "Karnataka"),
    ("mangaluru",           "Mangaluru",           "Karnataka"),
    ("hubli",               "Hubli",               "Karnataka"),
    ("belagavi",            "Belagavi",            "Karnataka"),
    ("davangere",           "Davangere",           "Karnataka"),
    ("shivamogga",          "Shivamogga",          "Karnataka"),
    ("tumkur",              "Tumkur",              "Karnataka"),
    ("kalaburagi",          "Kalaburagi",          "Karnataka"),
    ("bidar",               "Bidar",               "Karnataka"),
    ("ballari",             "Ballari",             "Karnataka"),
    ("raichur",             "Raichur",             "Karnataka"),
    ("udupi",               "Udupi",               "Karnataka"),
    ("hassan",              "Hassan",              "Karnataka"),
    ("chitradurga",         "Chitradurga",         "Karnataka"),
    ("vijayapura",          "Vijayapura",          "Karnataka"),
    ("bagalkot",            "Bagalkot",            "Karnataka"),
    ("koppal",              "Koppal",              "Karnataka"),
    ("gadag",               "Gadag",               "Karnataka"),
    ("dharwad",             "Dharwad",             "Karnataka"),
    ("mandya",              "Mandya",              "Karnataka"),
    ("chamarajanagar",      "Chamarajanagar",      "Karnataka"),
    ("kolar",               "Kolar",               "Karnataka"),
    ("chikballapur",        "Chikballapur",        "Karnataka"),

    # ── KERALA (14 districts) ─────────────────────────────────────────────
    ("thiruvananthapuram",  "Thiruvananthapuram",  "Kerala"),
    ("kochi",               "Kochi",               "Kerala"),
    ("kozhikode",           "Kozhikode",           "Kerala"),
    ("thrissur",            "Thrissur",            "Kerala"),
    ("kollam",              "Kollam",              "Kerala"),
    ("palakkad",            "Palakkad",            "Kerala"),
    ("malappuram",          "Malappuram",          "Kerala"),
    ("kannur",              "Kannur",              "Kerala"),
    ("kottayam",            "Kottayam",            "Kerala"),
    ("alappuzha",           "Alappuzha",           "Kerala"),
    ("idukki",              "Idukki",              "Kerala"),
    ("pathanamthitta",      "Pathanamthitta",      "Kerala"),
    ("kasaragod",           "Kasaragod",           "Kerala"),
    ("wayanad",             "Wayanad",             "Kerala"),

    # ── TELANGANA (33 districts) ──────────────────────────────────────────
    ("hyderabad",           "Hyderabad",           "Telangana"),
    ("warangal",            "Warangal",            "Telangana"),
    ("nizamabad",           "Nizamabad",           "Telangana"),
    ("karimnagar",          "Karimnagar",          "Telangana"),
    ("khammam",             "Khammam",             "Telangana"),
    ("mahbubnagar",         "Mahbubnagar",         "Telangana"),
    ("nalgonda",            "Nalgonda",            "Telangana"),
    ("adilabad",            "Adilabad",            "Telangana"),
    ("ramagundam",          "Ramagundam",          "Telangana"),
    ("sangareddy",          "Sangareddy",          "Telangana"),
    ("siddipet",            "Siddipet",            "Telangana"),
    ("suryapet",            "Suryapet",            "Telangana"),

    # ── ANDHRA PRADESH (13 districts) ─────────────────────────────────────
    ("visakhapatnam",       "Visakhapatnam",       "Andhra Pradesh"),
    ("vijayawada",          "Vijayawada",          "Andhra Pradesh"),
    ("guntur",              "Guntur",              "Andhra Pradesh"),
    ("nellore",             "Nellore",             "Andhra Pradesh"),
    ("kurnool",             "Kurnool",             "Andhra Pradesh"),
    ("kadapa",              "Kadapa",              "Andhra Pradesh"),
    ("anantapur",           "Anantapur",           "Andhra Pradesh"),
    ("tirupati",            "Tirupati",            "Andhra Pradesh"),
    ("rajahmundry",         "Rajahmundry",         "Andhra Pradesh"),
    ("eluru",               "Eluru",               "Andhra Pradesh"),
    ("kakinada",            "Kakinada",            "Andhra Pradesh"),
    ("vizianagaram",        "Vizianagaram",        "Andhra Pradesh"),
    ("ongole",              "Ongole",              "Andhra Pradesh"),

    # ── MAHARASHTRA (36 districts) ────────────────────────────────────────
    ("mumbai",              "Mumbai",              "Maharashtra"),
    ("pune",                "Pune",                "Maharashtra"),
    ("nagpur",              "Nagpur",              "Maharashtra"),
    ("nashik",              "Nashik",              "Maharashtra"),
    ("aurangabad",          "Aurangabad",          "Maharashtra"),
    ("kolhapur",            "Kolhapur",            "Maharashtra"),
    ("solapur",             "Solapur",             "Maharashtra"),
    ("amravati",            "Amravati",            "Maharashtra"),
    ("nanded",              "Nanded",              "Maharashtra"),
    ("akola",               "Akola",               "Maharashtra"),
    ("latur",               "Latur",               "Maharashtra"),
    ("jalgaon",             "Jalgaon",             "Maharashtra"),
    ("dhule",               "Dhule",               "Maharashtra"),
    ("sangli",              "Sangli",              "Maharashtra"),
    ("satara",              "Satara",              "Maharashtra"),
    ("ratnagiri",           "Ratnagiri",           "Maharashtra"),
    ("chandrapur",          "Chandrapur",          "Maharashtra"),
    ("thane",               "Thane",               "Maharashtra"),
    ("navi-mumbai",         "Navi Mumbai",         "Maharashtra"),
    ("vasai",               "Vasai",               "Maharashtra"),
    ("bhiwandi",            "Bhiwandi",            "Maharashtra"),
    ("malegaon",            "Malegaon",            "Maharashtra"),
    ("ahmednagar",          "Ahmednagar",          "Maharashtra"),
    ("parbhani",            "Parbhani",            "Maharashtra"),
    ("osmanabad",           "Osmanabad",           "Maharashtra"),
    ("beed",                "Beed",                "Maharashtra"),
    ("buldhana",            "Buldhana",            "Maharashtra"),
    ("yavatmal",            "Yavatmal",            "Maharashtra"),
    ("wardha",              "Wardha",              "Maharashtra"),
    ("gondia",              "Gondia",              "Maharashtra"),
    ("gadchiroli",          "Gadchiroli",          "Maharashtra"),

    # ── GUJARAT (33 districts) ────────────────────────────────────────────
    ("ahmedabad",           "Ahmedabad",           "Gujarat"),
    ("surat",               "Surat",               "Gujarat"),
    ("vadodara",            "Vadodara",            "Gujarat"),
    ("rajkot",              "Rajkot",              "Gujarat"),
    ("bhavnagar",           "Bhavnagar",           "Gujarat"),
    ("jamnagar",            "Jamnagar",            "Gujarat"),
    ("gandhinagar",         "Gandhinagar",         "Gujarat"),
    ("anand",               "Anand",               "Gujarat"),
    ("nadiad",              "Nadiad",              "Gujarat"),
    ("mehsana",             "Mehsana",             "Gujarat"),
    ("morbi",               "Morbi",               "Gujarat"),
    ("junagadh",            "Junagadh",            "Gujarat"),
    ("bharuch",             "Bharuch",             "Gujarat"),
    ("navsari",             "Navsari",             "Gujarat"),
    ("valsad",              "Valsad",              "Gujarat"),
    ("surendranagar",       "Surendranagar",       "Gujarat"),
    ("amreli",              "Amreli",              "Gujarat"),
    ("porbandar",           "Porbandar",           "Gujarat"),
    ("palanpur",            "Palanpur",            "Gujarat"),
    ("patan",               "Patan",               "Gujarat"),
    ("dahod",               "Dahod",               "Gujarat"),
    ("godhra",              "Godhra",              "Gujarat"),

    # ── GOA ────────────────────────────────────────────────────────────────
    ("panaji",              "Panaji",              "Goa"),
    ("margao",              "Margao",              "Goa"),
    ("vasco-da-gama",       "Vasco da Gama",       "Goa"),

    # ── MADHYA PRADESH (52 districts) ────────────────────────────────────
    ("bhopal",              "Bhopal",              "Madhya Pradesh"),
    ("indore",              "Indore",              "Madhya Pradesh"),
    ("jabalpur",            "Jabalpur",            "Madhya Pradesh"),
    ("gwalior",             "Gwalior",             "Madhya Pradesh"),
    ("ujjain",              "Ujjain",              "Madhya Pradesh"),
    ("sagar",               "Sagar",               "Madhya Pradesh"),
    ("satna",               "Satna",               "Madhya Pradesh"),
    ("rewa",                "Rewa",                "Madhya Pradesh"),
    ("dewas",               "Dewas",               "Madhya Pradesh"),
    ("chhindwara",          "Chhindwara",          "Madhya Pradesh"),
    ("shivpuri",            "Shivpuri",            "Madhya Pradesh"),
    ("bhind",               "Bhind",               "Madhya Pradesh"),
    ("morena",              "Morena",              "Madhya Pradesh"),
    ("mandsaur",            "Mandsaur",            "Madhya Pradesh"),
    ("vidisha",             "Vidisha",             "Madhya Pradesh"),
    ("hoshangabad",         "Hoshangabad",         "Madhya Pradesh"),
    ("khandwa",             "Khandwa",             "Madhya Pradesh"),
    ("khargone",            "Khargone",            "Madhya Pradesh"),
    ("damoh",               "Damoh",               "Madhya Pradesh"),
    ("tikamgarh",           "Tikamgarh",           "Madhya Pradesh"),
    ("shahdol",             "Shahdol",             "Madhya Pradesh"),
    ("balaghat",            "Balaghat",            "Madhya Pradesh"),
    ("seoni",               "Seoni",               "Madhya Pradesh"),
    ("narsinghpur",         "Narsinghpur",         "Madhya Pradesh"),
    ("katni",               "Katni",               "Madhya Pradesh"),
    ("datia",               "Datia",               "Madhya Pradesh"),
    ("ratlam",              "Ratlam",              "Madhya Pradesh"),

    # ── CHHATTISGARH (33 districts) ───────────────────────────────────────
    ("raipur",              "Raipur",              "Chhattisgarh"),
    ("bilaspur",            "Bilaspur",            "Chhattisgarh"),
    ("durg",                "Durg",                "Chhattisgarh"),
    ("bhilai",              "Bhilai",              "Chhattisgarh"),
    ("rajnandgaon",         "Rajnandgaon",         "Chhattisgarh"),
    ("jagdalpur",           "Jagdalpur",           "Chhattisgarh"),
    ("ambikapur",           "Ambikapur",           "Chhattisgarh"),
    ("korba",               "Korba",               "Chhattisgarh"),
    ("raigarh",             "Raigarh",             "Chhattisgarh"),
    ("janjgir",             "Janjgir",             "Chhattisgarh"),
    ("kanker",              "Kanker",              "Chhattisgarh"),
    ("dhamtari",            "Dhamtari",            "Chhattisgarh"),

    # ── WEST BENGAL (23 districts) ────────────────────────────────────────
    ("kolkata",             "Kolkata",             "West Bengal"),
    ("asansol",             "Asansol",             "West Bengal"),
    ("siliguri",            "Siliguri",            "West Bengal"),
    ("durgapur",            "Durgapur",            "West Bengal"),
    ("bardhaman",           "Bardhaman",           "West Bengal"),
    ("howrah",              "Howrah",              "West Bengal"),
    ("kharagpur",           "Kharagpur",           "West Bengal"),
    ("malda",               "Malda",               "West Bengal"),
    ("jalpaiguri",          "Jalpaiguri",          "West Bengal"),
    ("bankura",             "Bankura",             "West Bengal"),
    ("purulia",             "Purulia",             "West Bengal"),
    ("berhampore",          "Berhampore",          "West Bengal"),
    ("cooch-behar",         "Cooch Behar",         "West Bengal"),
    ("darjeeling",          "Darjeeling",          "West Bengal"),
    ("krishnanagar",        "Krishnanagar",        "West Bengal"),
    ("barasat",             "Barasat",             "West Bengal"),
    ("haldia",              "Haldia",              "West Bengal"),
    ("midnapore",           "Midnapore",           "West Bengal"),

    # ── ODISHA (30 districts) ─────────────────────────────────────────────
    ("bhubaneswar",         "Bhubaneswar",         "Odisha"),
    ("cuttack",             "Cuttack",             "Odisha"),
    ("rourkela",            "Rourkela",            "Odisha"),
    ("berhampur",           "Berhampur",           "Odisha"),
    ("sambalpur",           "Sambalpur",           "Odisha"),
    ("balasore",            "Balasore",            "Odisha"),
    ("baripada",            "Baripada",            "Odisha"),
    ("puri",                "Puri",                "Odisha"),
    ("koraput",             "Koraput",             "Odisha"),
    ("jharsuguda",          "Jharsuguda",          "Odisha"),
    ("sundargarh",          "Sundargarh",          "Odisha"),
    ("kendujhar",           "Kendujhar",           "Odisha"),
    ("angul",               "Angul",               "Odisha"),
    ("dhenkanal",           "Dhenkanal",           "Odisha"),
    ("bhadrak",             "Bhadrak",             "Odisha"),
    ("rayagada",            "Rayagada",            "Odisha"),
    ("bolangir",            "Bolangir",            "Odisha"),

    # ── JHARKHAND (24 districts) ──────────────────────────────────────────
    ("ranchi",              "Ranchi",              "Jharkhand"),
    ("jamshedpur",          "Jamshedpur",          "Jharkhand"),
    ("dhanbad",             "Dhanbad",             "Jharkhand"),
    ("bokaro",              "Bokaro",              "Jharkhand"),
    ("hazaribagh",          "Hazaribagh",          "Jharkhand"),
    ("deoghar",             "Deoghar",             "Jharkhand"),
    ("giridih",             "Giridih",             "Jharkhand"),
    ("dumka",               "Dumka",               "Jharkhand"),
    ("chaibasa",            "Chaibasa",            "Jharkhand"),
    ("jamtara",             "Jamtara",             "Jharkhand"),
    ("chatra",              "Chatra",              "Jharkhand"),
    ("lohardaga",           "Lohardaga",           "Jharkhand"),
    ("pakur",               "Pakur",               "Jharkhand"),

    # ── BIHAR (38 districts) ──────────────────────────────────────────────
    ("patna",               "Patna",               "Bihar"),
    ("gaya",                "Gaya",                "Bihar"),
    ("muzaffarpur",         "Muzaffarpur",         "Bihar"),
    ("bhagalpur",           "Bhagalpur",           "Bihar"),
    ("darbhanga",           "Darbhanga",           "Bihar"),
    ("purnia",              "Purnia",              "Bihar"),
    ("arrah",               "Arrah",               "Bihar"),
    ("begusarai",           "Begusarai",           "Bihar"),
    ("sasaram",             "Sasaram",             "Bihar"),
    ("hajipur",             "Hajipur",             "Bihar"),
    ("chapra",              "Chapra",              "Bihar"),
    ("motihari",            "Motihari",            "Bihar"),
    ("samastipur",          "Samastipur",          "Bihar"),
    ("siwan",               "Siwan",               "Bihar"),
    ("munger",              "Munger",              "Bihar"),
    ("katihar",             "Katihar",             "Bihar"),
    ("sitamarhi",           "Sitamarhi",           "Bihar"),
    ("madhubani",           "Madhubani",           "Bihar"),
    ("supaul",              "Supaul",              "Bihar"),
    ("aurangabad-bihar",    "Aurangabad (Bihar)",  "Bihar"),
    ("jehanabad",           "Jehanabad",           "Bihar"),
    ("nalanda",             "Nalanda",             "Bihar"),

    # ── ASSAM (35 districts) ──────────────────────────────────────────────
    ("guwahati",            "Guwahati",            "Assam"),
    ("dibrugarh",           "Dibrugarh",           "Assam"),
    ("silchar",             "Silchar",             "Assam"),
    ("tezpur",              "Tezpur",              "Assam"),
    ("jorhat",              "Jorhat",              "Assam"),
    ("nagaon",              "Nagaon",              "Assam"),
    ("tinsukia",            "Tinsukia",            "Assam"),
    ("bongaigaon",          "Bongaigaon",          "Assam"),
    ("dhubri",              "Dhubri",              "Assam"),
    ("goalpara",            "Goalpara",            "Assam"),
    ("nalbari",             "Nalbari",             "Assam"),
    ("barpeta",             "Barpeta",             "Assam"),
    ("sivasagar",           "Sivasagar",           "Assam"),
    ("karimganj",           "Karimganj",           "Assam"),
    ("hailakandi",          "Hailakandi",          "Assam"),

    # ── MEGHALAYA ─────────────────────────────────────────────────────────
    ("shillong",            "Shillong",            "Meghalaya"),
    ("tura",                "Tura",                "Meghalaya"),
    ("jowai",               "Jowai",               "Meghalaya"),
    ("nongstoin",           "Nongstoin",           "Meghalaya"),

    # ── MANIPUR ───────────────────────────────────────────────────────────
    ("imphal",              "Imphal",              "Manipur"),
    ("churachandpur",       "Churachandpur",       "Manipur"),
    ("thoubal",             "Thoubal",             "Manipur"),
    ("bishnupur",           "Bishnupur",           "Manipur"),

    # ── MIZORAM ───────────────────────────────────────────────────────────
    ("aizawl",              "Aizawl",              "Mizoram"),
    ("lunglei",             "Lunglei",             "Mizoram"),
    ("champhai",            "Champhai",            "Mizoram"),

    # ── TRIPURA ───────────────────────────────────────────────────────────
    ("agartala",            "Agartala",            "Tripura"),
    ("udaipur-tripura",     "Udaipur (Tripura)",   "Tripura"),
    ("dharmanagar",         "Dharmanagar",         "Tripura"),
    ("sabroom",             "Sabroom",             "Tripura"),

    # ── NAGALAND ──────────────────────────────────────────────────────────
    ("kohima",              "Kohima",              "Nagaland"),
    ("dimapur",             "Dimapur",             "Nagaland"),
    ("mokokchung",          "Mokokchung",          "Nagaland"),
    ("wokha",               "Wokha",               "Nagaland"),
    ("tuensang",            "Tuensang",            "Nagaland"),

    # ── ARUNACHAL PRADESH ─────────────────────────────────────────────────
    ("itanagar",            "Itanagar",            "Arunachal Pradesh"),
    ("naharlagun",          "Naharlagun",          "Arunachal Pradesh"),
    ("pasighat",            "Pasighat",            "Arunachal Pradesh"),
    ("tawang",              "Tawang",              "Arunachal Pradesh"),
    ("ziro",                "Ziro",                "Arunachal Pradesh"),

    # ── SIKKIM ────────────────────────────────────────────────────────────
    ("gangtok",             "Gangtok",             "Sikkim"),
    ("namchi",              "Namchi",              "Sikkim"),
    ("gyalshing",           "Gyalshing",           "Sikkim"),
    ("mangan",              "Mangan",              "Sikkim"),
]
