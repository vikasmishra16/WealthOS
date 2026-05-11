# ============================================================
# WealthOS — macro_collector TEST CELL
# Paste this entire cell into Google Colab and run it AFTER:
#   - Cells 1–3 of WealthOS_Setup.ipynb have been run
#   - macro_collector.py is at /content/WealthOS/collectors/
# ============================================================

import sys

if "/content/WealthOS" not in sys.path:
    sys.path.insert(0, "/content/WealthOS")

from collectors.macro_collector import (
    _get_db_connection,
    _is_macro_cache_fresh,
    _fetch_live_indicators,
    get_macro_snapshot,
    get_market_context,
    get_risk_free_rate,
)

print("=" * 55)
print("  macro_collector — Test Suite")
print("=" * 55)

# ------------------------------------------------------------------
# TEST 1 — get_macro_snapshot returns correct structure
# ------------------------------------------------------------------
try:
    snapshot = get_macro_snapshot()
    assert isinstance(snapshot, dict), "snapshot must be a dict"
    required_keys = ["date", "vix", "repo_rate", "cpi", "iip",
                     "ten_yr_gsec", "fii_net_flow", "dii_net_flow",
                     "usd_inr", "brent_crude"]
    for key in required_keys:
        assert key in snapshot, f"Missing key: {key}"
    print("TEST 1 PASS — snapshot keys verified")
    print(f"  Values: {snapshot}")
except AssertionError as e:
    print(f"TEST 1 FAIL — {e}")
except Exception as e:
    print(f"TEST 1 FAIL — unexpected exception: {e}")

# ------------------------------------------------------------------
# TEST 2 — Cache hit on second call
# ------------------------------------------------------------------
try:
    snapshot2 = get_macro_snapshot()
    assert isinstance(snapshot2, dict)
    print("TEST 2 PASS — second call completed (check Cache hit above)")
except AssertionError as e:
    print(f"TEST 2 FAIL — {e}")
except Exception as e:
    print(f"TEST 2 FAIL — unexpected exception: {e}")

# ------------------------------------------------------------------
# TEST 3 — get_market_context returns non-empty string
# ------------------------------------------------------------------
try:
    context = get_market_context()
    assert isinstance(context, str), "context must be a str"
    assert len(context) > 50, f"context too short ({len(context)} chars)"
    assert "VIX" in context, "'VIX' not found in context"
    assert "Repo Rate" in context, "'Repo Rate' not found in context"
    print("TEST 3 PASS — market context string verified")
    print(f"\nMarket Context Output:\n{context}")
except AssertionError as e:
    print(f"TEST 3 FAIL — {e}")
except Exception as e:
    print(f"TEST 3 FAIL — unexpected exception: {e}")

# ------------------------------------------------------------------
# TEST 4 — get_risk_free_rate returns valid decimal
# ------------------------------------------------------------------
try:
    rfr = get_risk_free_rate()
    assert isinstance(rfr, float), f"risk free rate must be float, got {type(rfr)}"
    assert 0.04 < rfr < 0.12, f"risk free rate {rfr} out of expected range (0.04–0.12)"
    print(f"TEST 4 PASS — risk free rate: {rfr} ({rfr*100:.2f}%)")
except AssertionError as e:
    print(f"TEST 4 FAIL — {e}")
except Exception as e:
    print(f"TEST 4 FAIL — unexpected exception: {e}")

print("=" * 55)
print("  Test suite complete.")
print("=" * 55)
