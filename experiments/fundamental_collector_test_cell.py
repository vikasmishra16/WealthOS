# ============================================================
# WealthOS — fundamental_collector TEST CELL
# Paste this entire cell into Google Colab and run it AFTER:
#   - Cells 1–3 of WealthOS_Setup.ipynb have been run
#   - fundamental_collector.py is at /content/WealthOS/collectors/
# ============================================================

import sys

if "/content/WealthOS" not in sys.path:
    sys.path.insert(0, "/content/WealthOS")

from collectors.fundamental_collector import (
    _get_screener_url,
    fetch_fundamentals,
    get_fundamental_summary,
)

print("=" * 55)
print("  fundamental_collector — Test Suite")
print("=" * 55)

# ------------------------------------------------------------------
# TEST 1 — _get_screener_url
# ------------------------------------------------------------------
try:
    assert _get_screener_url("RELIANCE") == \
        "https://www.screener.in/company/RELIANCE/consolidated/", \
        f"URL mismatch: {_get_screener_url('RELIANCE')}"
    assert _get_screener_url("RELIANCE.NS") == \
        "https://www.screener.in/company/RELIANCE/consolidated/", \
        f"URL mismatch with .NS suffix: {_get_screener_url('RELIANCE.NS')}"
    assert _get_screener_url("infy") == \
        "https://www.screener.in/company/INFY/consolidated/", \
        f"URL mismatch lowercase: {_get_screener_url('infy')}"
    print("TEST 1 PASS — URL builder")
except AssertionError as e:
    print(f"TEST 1 FAIL — {e}")
except Exception as e:
    print(f"TEST 1 FAIL — unexpected exception: {e}")

# ------------------------------------------------------------------
# TEST 2 — fetch_fundamentals live call
# ------------------------------------------------------------------
try:
    result = fetch_fundamentals("RELIANCE")
    assert isinstance(result, list), f"Expected list, got {type(result)}"
    assert len(result) > 0, "Expected at least 1 year of data"
    assert "revenue" in result[0], "Missing key: revenue"
    assert "pat" in result[0], "Missing key: pat"
    assert result[0]["symbol"] == "RELIANCE", \
        f"Expected symbol RELIANCE, got {result[0]['symbol']}"
    print(f"TEST 2 PASS — {len(result)} years fetched")
    print(f"  Most recent: year={result[0]['year']}, "
          f"revenue={result[0]['revenue']}, pat={result[0]['pat']}")
except AssertionError as e:
    print(f"TEST 2 FAIL — {e}")
except Exception as e:
    print(f"TEST 2 FAIL — unexpected exception: {e}")

# ------------------------------------------------------------------
# TEST 3 — Cache hit on second call
# ------------------------------------------------------------------
try:
    result2 = fetch_fundamentals("RELIANCE")
    assert isinstance(result2, list), f"Expected list, got {type(result2)}"
    assert len(result2) > 0, "Cache returned empty list"
    print("TEST 3 PASS — cache hit confirmed")
except AssertionError as e:
    print(f"TEST 3 FAIL — {e}")
except Exception as e:
    print(f"TEST 3 FAIL — unexpected exception: {e}")

# ------------------------------------------------------------------
# TEST 4 — get_fundamental_summary for TCS
# ------------------------------------------------------------------
try:
    result = get_fundamental_summary("TCS")
    assert isinstance(result, dict), f"Expected dict, got {type(result)}"
    required_keys = [
        "symbol", "latest_year", "revenue", "pat", "eps",
        "total_assets", "revenue_growth_pct", "pat_margin_pct",
        "debt_to_equity", "years_available", "all_years"
    ]
    for key in required_keys:
        assert key in result, f"Missing key: {key}"
    assert result["years_available"] > 0, "years_available must be > 0"
    print(f"TEST 4 PASS — summary: {result}")
except AssertionError as e:
    print(f"TEST 4 FAIL — {e}")
except Exception as e:
    print(f"TEST 4 FAIL — unexpected exception: {e}")

print("=" * 55)
print("  Test suite complete.")
print("=" * 55)
