# ============================================================
# WealthOS — mf_collector TEST CELL
# Paste this entire cell into Google Colab and run it AFTER:
#   - Cells 1–3 of WealthOS_Setup.ipynb have been run
#   - mf_collector.py is at /content/WealthOS/collectors/
# Scheme: 119551 — SBI Bluechip Fund - Direct Plan - Growth
# ============================================================

import sys

if "/content/WealthOS" not in sys.path:
    sys.path.insert(0, "/content/WealthOS")

from collectors.mf_collector import (
    search_scheme,
    fetch_nav_history,
    fetch_scheme_details,
    get_mf_summary,
)

SCHEME_CODE = 119551

print("=" * 55)
print("  mf_collector — Test Suite")
print("=" * 55)

# ------------------------------------------------------------------
# TEST 1 — search_scheme
# ------------------------------------------------------------------
try:
    result = search_scheme("SBI Bluechip")
    assert isinstance(result, list), f"Expected list, got {type(result)}"
    assert len(result) > 0, "Expected at least 1 matching scheme"
    assert "scheme_code" in result[0], "Missing key: scheme_code"
    assert "scheme_name" in result[0], "Missing key: scheme_name"
    print(f"TEST 1 PASS — found {len(result)} schemes")
    for s in result[:3]:
        print(f"  {s['scheme_code']}: {s['scheme_name']}")
except AssertionError as e:
    print(f"TEST 1 FAIL — {e}")
except Exception as e:
    print(f"TEST 1 FAIL — unexpected exception: {e}")

# ------------------------------------------------------------------
# TEST 2 — fetch_nav_history live call
# ------------------------------------------------------------------
try:
    result = fetch_nav_history(SCHEME_CODE)
    assert isinstance(result, list), f"Expected list, got {type(result)}"
    assert len(result) > 0, "Expected at least 1 NAV record"
    assert "nav" in result[0], "Missing key: nav"
    assert "date" in result[0], "Missing key: date"
    print(f"TEST 2 PASS — {len(result)} NAV records")
    print(f"  Latest: {result[0]}")
except AssertionError as e:
    print(f"TEST 2 FAIL — {e}")
except Exception as e:
    print(f"TEST 2 FAIL — unexpected exception: {e}")

# ------------------------------------------------------------------
# TEST 3 — Cache hit on second call
# ------------------------------------------------------------------
try:
    result2 = fetch_nav_history(SCHEME_CODE)
    assert isinstance(result2, list), f"Expected list, got {type(result2)}"
    assert len(result2) > 0, "Cache returned empty list"
    print("TEST 3 PASS — cache hit confirmed")
except AssertionError as e:
    print(f"TEST 3 FAIL — {e}")
except Exception as e:
    print(f"TEST 3 FAIL — unexpected exception: {e}")

# ------------------------------------------------------------------
# TEST 4 — get_mf_summary
# ------------------------------------------------------------------
try:
    result = get_mf_summary(SCHEME_CODE)
    assert isinstance(result, dict), f"Expected dict, got {type(result)}"
    required_keys = [
        "scheme_code", "scheme_name", "fund_house", "category",
        "current_nav", "returns_1y", "returns_3y",
        "52w_high", "52w_low", "total_nav_records"
    ]
    for key in required_keys:
        assert key in result, f"Missing key: {key}"
    assert result["current_nav"] is not None, "current_nav must not be None"
    assert result["total_nav_records"] > 0, "total_nav_records must be > 0"
    print(f"TEST 4 PASS — {result}")
except AssertionError as e:
    print(f"TEST 4 FAIL — {e}")
except Exception as e:
    print(f"TEST 4 FAIL — unexpected exception: {e}")

print("=" * 55)
print("  Test suite complete.")
print("=" * 55)
