"""
run_all.py — Master Analysis Pipeline Runner
---------------------------------------------
Runs all analysis scripts in dependency order and reports timing.

Order:
    0. base_metrics    — core ratios, dashboard JSON files
    1. model1_gini     — Gini coefficient (network inequality)
    2. model2_lq       — Location quotient (regional over/under-representation)
    3. model3_hhi      — Herfindahl-Hirschman Index (concentration)
    4. model4_moran    — Moran's I (spatial autocorrelation)  [slowest ~2 min]
    5. model5_pca      — Principal Component Analysis
    6. model6_clustering — K-Means city archetypes
    7. model7_quadrant — Portfolio quadrant matrix

Usage:
    python analysis/run_all.py
    python analysis/run_all.py --skip-moran     # skip spatial step if slow
"""

import importlib
import os
import sys
import time
import traceback

# Force UTF-8 on Windows so Unicode chars in model print statements don't crash
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_DIR)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

STEPS = [
    ("base_metrics",      "Base Metrics & Dashboard JSON"),
    ("model1_gini",       "Model 1 — Gini Coefficient"),
    ("model2_lq",         "Model 2 — Location Quotient"),
    ("model3_hhi",        "Model 3 — HHI Concentration"),
    ("model4_moran",      "Model 4 — Moran's I Spatial Autocorrelation"),
    ("model5_pca",        "Model 5 — PCA"),
    ("model6_clustering", "Model 6 — K-Means Clustering"),
    ("model7_quadrant",   "Model 7 — Portfolio Quadrant"),
]

SKIP_MORAN = "--skip-moran" in sys.argv


def run_step(module_name: str, label: str) -> bool:
    if module_name == "model4_moran" and SKIP_MORAN:
        print(f"  SKIPPED (--skip-moran flag)")
        return True
    try:
        mod = importlib.import_module(module_name)
        mod.run()
        return True
    except Exception:
        print(f"\n  ERROR in {module_name}:")
        traceback.print_exc()
        return False


def main():
    print()
    print("=" * 65)
    print("  MOTORCYCLE NETWORK ANALYSIS - FULL PIPELINE")
    print("=" * 65)

    total_start = time.time()
    results = []

    for module_name, label in STEPS:
        print()
        print(f"-- {label} {'-'*(55-len(label))}")
        t0      = time.time()
        success = run_step(module_name, label)
        elapsed = round(time.time() - t0, 1)
        results.append((label, success, elapsed))
        status = "OK" if success else "FAILED"
        print(f"  [{status}] {elapsed}s")

    total = round(time.time() - total_start, 1)

    print()
    print("=" * 65)
    print("  PIPELINE COMPLETE")
    print("=" * 65)
    for label, ok, elapsed in results:
        icon = "OK  " if ok else "FAIL"
        print(f"  {icon}  {elapsed:>6.1f}s   {label}")
    print(f"\n  Total time: {total}s")

    failed = [l for l, ok, _ in results if not ok]
    if failed:
        print(f"\n  FAILED STEPS: {', '.join(failed)}")
        sys.exit(1)

    print()
    print("  Output files written to: data/analysis/")
    print("  Run: python outputs/final_dashboard.py")
    print("=" * 65)


if __name__ == "__main__":
    main()
