# ============================================================
# WealthOS — nse_collector TEST CELL
# Paste this entire cell into Google Colab and run it AFTER:
#   - Cells 1–3 of WealthOS_Setup.ipynb have been run
#   - nse_collector.py is at /content/WealthOS/collectors/
# ============================================================

import sys

if "/content/WealthOS" not in sys.path:
    sys.path.insert(0, "/content/WealthOS")

from collectors.nse_collector import (
    get_shareholding_pattern,
    get_corporate_actions,
    get_governance_flags,
)

print("=" * 55)
print("  nse_collector — Test Suite")
print("=" * 55)

# ------------------------------------------------------------------
# TEST 1 — get_shareholding_pattern for RELIANCE
# ------------------------------------------------------------------
try:
    shp = get_shareholding_pattern("RELIANCE")
    assert isinstance(shp, dict), "Result must be a dict"
    required = ["symbol", "quarter", "promoter_pct", "fii_pct",
                "dii_pct", "public_pct", "pledge_pct", "source"]
    for k in required:
        assert k in shp, f"Missing key: {k}"
    print(f"TEST 1 PASS — shareholding: {shp}")
except AssertionError as e:
    print(f"TEST 1 FAIL — {e}")
except Exception as e:
    print(f"TEST 1 FAIL — unexpected exception: {e}")

# ------------------------------------------------------------------
# TEST 2 — Cache hit on second call
# ------------------------------------------------------------------
try:
    shp2 = get_shareholding_pattern("RELIANCE")
    assert isinstance(shp2, dict)
    print("TEST 2 PASS — second call done (check Cache hit above)")
except AssertionError as e:
    print(f"TEST 2 FAIL — {e}")
except Exception as e:
    print(f"TEST 2 FAIL — unexpected exception: {e}")

# ------------------------------------------------------------------
# TEST 3 — get_corporate_actions returns list
# ------------------------------------------------------------------
try:
    actions = get_corporate_actions("TCS")
    assert isinstance(actions, list), "Result must be a list"
    print(f"TEST 3 PASS — corporate actions: {len(actions)} records")
    if actions:
        print(f"  Sample: {actions[0]}")
except AssertionError as e:
    print(f"TEST 3 FAIL — {e}")
except Exception as e:
    print(f"TEST 3 FAIL — unexpected exception: {e}")

# ------------------------------------------------------------------
# TEST 4 — get_governance_flags returns flags and score
# ------------------------------------------------------------------
try:
    flags = get_governance_flags("HDFCBANK")
    assert isinstance(flags, dict), "Result must be a dict"
    assert "promoter_flag" in flags, "Missing key: promoter_flag"
    assert "pledge_flag" in flags, "Missing key: pledge_flag"
    assert "governance_score" in flags, "Missing key: governance_score"
    assert isinstance(flags["governance_score"], int), \
        f"governance_score must be int, got {type(flags['governance_score'])}"
    print(f"TEST 4 PASS — governance flags: {flags}")
except AssertionError as e:
    print(f"TEST 4 FAIL — {e}")
except Exception as e:
    print(f"TEST 4 FAIL — unexpected exception: {e}")

print("=" * 55)
print("  Test suite complete.")
print("=" * 55)
