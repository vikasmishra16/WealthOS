# ============================================================
# WealthOS — fundamental_analyzer TEST CELL
# Paste this entire cell into Google Colab and run it AFTER:
#   - Cells 1–3 of WealthOS_Setup.ipynb have been run
#   - fundamental_analyzer.py at /content/WealthOS/analyzers/
#   - fundamental_collector.py at /content/WealthOS/collectors/
# ============================================================

import sys

for key in list(sys.modules.keys()):
    if "fundamental_analyzer" in key or "fundamental_collector" in key:
        del sys.modules[key]

if "/content/WealthOS" not in sys.path:
    sys.path.insert(0, "/content/WealthOS")

from analyzers.fundamental_analyzer import (
    compute_ratios,
    score_quality,
    get_sector_context,
    get_fundamental_analysis,
    build_fundamental_summary,
)

print("=" * 55)
print("  fundamental_analyzer — Test Suite")
print("=" * 55)

# ------------------------------------------------------------------
# TEST 1 — get_fundamental_analysis for RELIANCE
# ------------------------------------------------------------------
try:
    result = get_fundamental_analysis("RELIANCE", current_price=1408.80)
    assert isinstance(result, dict), f"Expected dict, got {type(result)}"
    assert "error" not in result, f"Error: {result.get('error')}"
    assert "ratios" in result, "Missing key: ratios"
    assert "quality" in result, "Missing key: quality"
    assert result["ratios"]["pe_ratio"] is not None, "pe_ratio must not be None"
    assert result["ratios"]["roe"] is not None, "roe must not be None"
    print("TEST 1 PASS")
    print(f"  PE: {result['ratios']['pe_ratio']}x")
    print(f"  ROE: {result['ratios']['roe']}%")
    print(f"  ROCE: {result['ratios']['roce']}%")
    print(f"  FCF: {result['ratios']['fcf']} Cr")
    print(f"  EPS Growth 3Y: {result['ratios']['eps_growth_3y']}%")
    print(f"  Grade: {result['quality']['quality_grade']}")
except AssertionError as e:
    print(f"TEST 1 FAIL — {e}")
except Exception as e:
    print(f"TEST 1 FAIL — unexpected exception: {e}")

# ------------------------------------------------------------------
# TEST 2 — score_quality flags
# ------------------------------------------------------------------
try:
    assert "flags" in result["quality"], "Missing key: flags"
    assert "roe" in result["quality"]["flags"], "Missing flag: roe"
    assert "pe_ratio" in result["quality"]["flags"], "Missing flag: pe_ratio"
    assert "fcf" in result["quality"]["flags"], "Missing flag: fcf"
    assert isinstance(result["quality"]["quality_score"], int), \
        f"quality_score must be int, got {type(result['quality']['quality_score'])}"
    print(f"TEST 2 PASS — flags: {result['quality']['flags']}")
except AssertionError as e:
    print(f"TEST 2 FAIL — {e}")
except Exception as e:
    print(f"TEST 2 FAIL — unexpected exception: {e}")

# ------------------------------------------------------------------
# TEST 3 — sector context for TCS (IT sector)
# ------------------------------------------------------------------
try:
    result2 = get_fundamental_analysis("TCS", current_price=3200.0, sector="it")
    assert "sector_context" in result2, "Missing key: sector_context"
    assert result2["sector_context"]["sector_pe"] == 25, \
        f"IT sector PE should be 25, got {result2['sector_context']['sector_pe']}"
    assert result2["sector_context"]["vs_sector"] is not None, \
        "vs_sector must not be None"
    print(f"TEST 3 PASS — {result2['sector_context']}")
except AssertionError as e:
    print(f"TEST 3 FAIL — {e}")
except Exception as e:
    print(f"TEST 3 FAIL — unexpected exception: {e}")

# ------------------------------------------------------------------
# TEST 4 — build_fundamental_summary
# ------------------------------------------------------------------
try:
    summary = build_fundamental_summary(result)
    assert isinstance(summary, str), f"Expected str, got {type(summary)}"
    assert len(summary) > 100, f"Summary too short ({len(summary)} chars)"
    assert "Quality Grade" in summary, "'Quality Grade' not in summary"
    assert "ROE" in summary, "'ROE' not in summary"
    assert "FCF" in summary, "'FCF' not in summary"
    print("TEST 4 PASS — summary generated")
    print(summary)
except AssertionError as e:
    print(f"TEST 4 FAIL — {e}")
except Exception as e:
    print(f"TEST 4 FAIL — unexpected exception: {e}")

print("=" * 55)
print("  Test suite complete.")
print("=" * 55)
