# ============================================================
# WealthOS — context_builder TEST CELL
# Paste this entire cell into Google Colab and run it AFTER:
#   - Cells 1–3 of WealthOS_Setup.ipynb have been run
#   - All Phase 1 collectors at /content/WealthOS/collectors/
#   - All Phase 2 analyzers at /content/WealthOS/analyzers/
# ============================================================

import sys

for key in list(sys.modules.keys()):
    if any(x in key for x in [
        "context_builder", "technical_analyzer",
        "fundamental_analyzer", "price_collector",
        "macro_collector", "nse_collector",
        "news_collector", "fundamental_collector"
    ]):
        del sys.modules[key]

if "/content/WealthOS" not in sys.path:
    sys.path.insert(0, "/content/WealthOS")

from analyzers.context_builder import (
    build_stock_context,
    format_context_string,
    get_context,
)

print("=" * 55)
print("  context_builder — Test Suite")
print("=" * 55)

# ------------------------------------------------------------------
# TEST 1 — build_stock_context for RELIANCE
# ------------------------------------------------------------------
try:
    context = build_stock_context("RELIANCE", sector="oil_gas")
    assert isinstance(context, dict), f"Expected dict, got {type(context)}"
    assert "error" not in context or "symbol" in context, \
        f"Context error with no symbol: {context.get('error')}"
    assert context.get("symbol") == "RELIANCE", \
        f"Expected symbol RELIANCE, got {context.get('symbol')}"
    assert context.get("current_price") is not None, \
        "current_price must not be None"
    assert "technical" in context, "Missing key: technical"
    assert "fundamental" in context, "Missing key: fundamental"
    assert "macro" in context, "Missing key: macro"
    print("TEST 1 PASS — context built for RELIANCE")
    print(f"  Current price: ₹{context.get('current_price')}")
    print(f"  Technical signal: {context.get('technical', {}).get('overall_signal')}")
    print(f"  Fundamental grade: {context.get('fundamental', {}).get('quality', {}).get('quality_grade')}")
except AssertionError as e:
    print(f"TEST 1 FAIL — {e}")
except Exception as e:
    print(f"TEST 1 FAIL — unexpected exception: {e}")

# ------------------------------------------------------------------
# TEST 2 — format_context_string produces valid string
# ------------------------------------------------------------------
try:
    context_str = format_context_string(context)
    assert isinstance(context_str, str), f"Expected str, got {type(context_str)}"
    assert len(context_str) > 500, \
        f"Context string too short ({len(context_str)} chars)"
    assert "TECHNICAL ANALYSIS" in context_str, \
        "'TECHNICAL ANALYSIS' not in context string"
    assert "FUNDAMENTAL ANALYSIS" in context_str, \
        "'FUNDAMENTAL ANALYSIS' not in context string"
    assert "MACRO" in context_str, \
        "'MACRO' not in context string"
    print(f"TEST 2 PASS — context string: {len(context_str)} chars")
except AssertionError as e:
    print(f"TEST 2 FAIL — {e}")
except Exception as e:
    print(f"TEST 2 FAIL — unexpected exception: {e}")

# ------------------------------------------------------------------
# TEST 3 — get_context end-to-end for TCS
# ------------------------------------------------------------------
try:
    ctx_dict, ctx_str = get_context(
        "TCS", sector="it", company_name="Tata Consultancy Services"
    )
    assert isinstance(ctx_dict, dict), f"Expected dict, got {type(ctx_dict)}"
    assert isinstance(ctx_str, str), f"Expected str, got {type(ctx_str)}"
    assert len(ctx_str) > 500, \
        f"TCS context string too short ({len(ctx_str)} chars)"
    assert "TCS" in ctx_str, "'TCS' not found in context string"
    print(f"TEST 3 PASS — TCS context: {len(ctx_str)} chars")
except AssertionError as e:
    print(f"TEST 3 FAIL — {e}")
except Exception as e:
    print(f"TEST 3 FAIL — unexpected exception: {e}")

# ------------------------------------------------------------------
# TEST 4 — print full context string for RELIANCE
# ------------------------------------------------------------------
print("TEST 4 — Full context string output:")
print(context_str)

print("=" * 55)
print("  Test suite complete.")
print("=" * 55)
