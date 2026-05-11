# ============================================================
# WealthOS — technical_analyzer TEST CELL
# Paste this entire cell into Google Colab and run it AFTER:
#   - Cells 1–3 of WealthOS_Setup.ipynb have been run
#   - technical_analyzer.py is at /content/WealthOS/analyzers/
#   - price_collector.py is at /content/WealthOS/collectors/
# ============================================================

import sys

for key in list(sys.modules.keys()):
    if "technical_analyzer" in key or "price_collector" in key:
        del sys.modules[key]

if "/content/WealthOS" not in sys.path:
    sys.path.insert(0, "/content/WealthOS")

from analyzers.technical_analyzer import (
    compute_technicals,
    get_technical_summary,
    analyze_symbol,
)

print("=" * 55)
print("  technical_analyzer — Test Suite")
print("=" * 55)

# ------------------------------------------------------------------
# TEST 1 — analyze_symbol live call for RELIANCE
# ------------------------------------------------------------------
try:
    result = analyze_symbol("RELIANCE")
    assert isinstance(result, dict), f"Expected dict, got {type(result)}"
    assert "error" not in result, f"Error: {result.get('error')}"
    assert "overall_signal" in result, "Missing key: overall_signal"
    assert "rsi" in result, "Missing key: rsi"
    assert "support_levels" in result, "Missing key: support_levels"
    assert isinstance(result["support_levels"], list), \
        f"support_levels must be list, got {type(result['support_levels'])}"
    print("TEST 1 PASS — RELIANCE technical analysis complete")
    print(f"  Overall: {result['overall_signal']}")
    print(f"  RSI: {result['rsi']} — {result['rsi_signal']}")
    print(f"  MACD: {result['macd_signal']}")
    print(f"  200 DMA: {result['dma200_signal']}")
    print(f"  Support: {result['support_levels']}")
    print(f"  Resistance: {result['resistance_levels']}")
except AssertionError as e:
    print(f"TEST 1 FAIL — {e}")
except Exception as e:
    print(f"TEST 1 FAIL — unexpected exception: {e}")

# ------------------------------------------------------------------
# TEST 2 — summary string present
# ------------------------------------------------------------------
try:
    assert "summary" in result, "Missing key: summary"
    assert isinstance(result["summary"], str), \
        f"summary must be str, got {type(result['summary'])}"
    assert len(result["summary"]) > 50, \
        f"summary too short ({len(result['summary'])} chars)"
    print("TEST 2 PASS — summary string generated")
    print(result["summary"])
except AssertionError as e:
    print(f"TEST 2 FAIL — {e}")
except Exception as e:
    print(f"TEST 2 FAIL — unexpected exception: {e}")

# ------------------------------------------------------------------
# TEST 3 — analyze_symbol for TCS
# ------------------------------------------------------------------
try:
    result2 = analyze_symbol("TCS")
    assert isinstance(result2, dict), f"Expected dict, got {type(result2)}"
    assert "error" not in result2, f"Error: {result2.get('error')}"
    assert result2["current_close"] is not None, "current_close must not be None"
    print(f"TEST 3 PASS — TCS: ₹{result2['current_close']} | {result2['overall_signal']}")
except AssertionError as e:
    print(f"TEST 3 FAIL — {e}")
except Exception as e:
    print(f"TEST 3 FAIL — unexpected exception: {e}")

# ------------------------------------------------------------------
# TEST 4 — insufficient data guard
# ------------------------------------------------------------------
try:
    import pandas as pd
    import numpy as np
    small_df = pd.DataFrame({
        "open":   np.random.uniform(100, 200, 10),
        "high":   np.random.uniform(200, 300, 10),
        "low":    np.random.uniform(50, 100, 10),
        "close":  np.random.uniform(100, 200, 10),
        "volume": np.random.randint(1000, 9000, 10)
    })
    result3 = compute_technicals(small_df)
    assert "error" in result3, f"Expected 'error' key, got: {result3.keys()}"
    print(f"TEST 4 PASS — insufficient data guard: {result3['error']}")
except AssertionError as e:
    print(f"TEST 4 FAIL — {e}")
except Exception as e:
    print(f"TEST 4 FAIL — unexpected exception: {e}")

print("=" * 55)
print("  Test suite complete.")
print("=" * 55)
