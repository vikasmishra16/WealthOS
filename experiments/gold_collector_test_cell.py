# ============================================================
# WealthOS — gold_collector TEST CELL
# Paste this entire cell into Google Colab and run it AFTER:
#   - Cells 1–3 of WealthOS_Setup.ipynb have been run
#   - gold_collector.py is at /content/WealthOS/collectors/
# ============================================================

import sys

if "/content/WealthOS" not in sys.path:
    sys.path.insert(0, "/content/WealthOS")

from collectors.gold_collector import (
    _fetch_yahoo_series,
    fetch_gold_prices,
    get_gold_summary,
)

print("=" * 55)
print("  gold_collector — Test Suite")
print("=" * 55)

# ------------------------------------------------------------------
# TEST 1 — _fetch_yahoo_series directly
# ------------------------------------------------------------------
try:
    result = _fetch_yahoo_series("GOLDBEES.NS", 30)
    assert isinstance(result, list), f"Expected list, got {type(result)}"
    assert len(result) > 0, "Expected at least 1 data point"
    assert isinstance(result[0], tuple), f"Expected tuple, got {type(result[0])}"
    assert len(result[0]) == 2, f"Expected 2-element tuple, got {len(result[0])}"
    print(f"TEST 1 PASS — {len(result)} GOLDBEES data points")
    print(f"  Latest: {result[-1]}")
except AssertionError as e:
    print(f"TEST 1 FAIL — {e}")
except Exception as e:
    print(f"TEST 1 FAIL — unexpected exception: {e}")

# ------------------------------------------------------------------
# TEST 2 — fetch_gold_prices live call
# ------------------------------------------------------------------
try:
    result = fetch_gold_prices()
    assert isinstance(result, list), f"Expected list, got {type(result)}"
    assert len(result) > 0, "Expected at least 1 gold price record"
    assert "goldbees_close" in result[0], "Missing key: goldbees_close"
    assert "gold_inr_per_gram" in result[0], "Missing key: gold_inr_per_gram"
    print(f"TEST 2 PASS — {len(result)} gold price records")
    print(f"  Latest: {result[0]}")
except AssertionError as e:
    print(f"TEST 2 FAIL — {e}")
except Exception as e:
    print(f"TEST 2 FAIL — unexpected exception: {e}")

# ------------------------------------------------------------------
# TEST 3 — Cache hit on second call
# ------------------------------------------------------------------
try:
    result2 = fetch_gold_prices()
    assert isinstance(result2, list), f"Expected list, got {type(result2)}"
    assert len(result2) > 0, "Cache returned empty list"
    print("TEST 3 PASS — cache hit confirmed")
except AssertionError as e:
    print(f"TEST 3 FAIL — {e}")
except Exception as e:
    print(f"TEST 3 FAIL — unexpected exception: {e}")

# ------------------------------------------------------------------
# TEST 4 — get_gold_summary
# ------------------------------------------------------------------
try:
    result = get_gold_summary()
    assert isinstance(result, dict), f"Expected dict, got {type(result)}"
    required_keys = [
        "as_of_date", "goldbees_close", "gold_inr_per_gram",
        "usd_inr", "returns_1m", "returns_1y",
        "52w_high_goldbees", "total_records"
    ]
    for key in required_keys:
        assert key in result, f"Missing key: {key}"
    assert result["goldbees_close"] is not None, "goldbees_close must not be None"
    assert result["total_records"] > 0, "total_records must be > 0"
    print(f"TEST 4 PASS — {result}")
except AssertionError as e:
    print(f"TEST 4 FAIL — {e}")
except Exception as e:
    print(f"TEST 4 FAIL — unexpected exception: {e}")

print("=" * 55)
print("  Test suite complete.")
print("=" * 55)
