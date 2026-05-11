# ============================================================
# WealthOS — llm/tools TEST CELL
# Paste this entire cell into Google Colab and run it AFTER:
#   - All Phase 1 collectors at /content/WealthOS/collectors/
#   - All Phase 2 analyzers at /content/WealthOS/analyzers/
#   - llm/tools.py at /content/WealthOS/llm/
#   - LLM already loaded from Cell 30 (do NOT reload)
# ============================================================

import sys

for key in list(sys.modules.keys()):
    if any(x in key for x in [
        "tools", "context_builder", "technical_analyzer",
        "fundamental_analyzer", "price_collector",
        "macro_collector", "nse_collector",
        "news_collector", "fundamental_collector",
        "mf_collector", "gold_collector"
    ]):
        del sys.modules[key]

if "/content/WealthOS" not in sys.path:
    sys.path.insert(0, "/content/WealthOS")

from llm.tools import (
    get_stock_context,
    analyze_technicals,
    analyze_fundamentals,
    get_news_sentiment,
    get_macro_context,
    get_gold_analysis,
    search_mutual_fund,
)

print("=" * 55)
print("  llm/tools — Test Suite")
print("=" * 55)

# ------------------------------------------------------------------
# TEST 1 — get_stock_context
# ------------------------------------------------------------------
try:
    result = get_stock_context.invoke("RELIANCE")
    assert isinstance(result, str), f"Expected str, got {type(result)}"
    assert len(result) > 100, f"Context too short ({len(result)} chars)"
    assert "TECHNICAL" in result or "ERROR" not in result, \
        "Missing TECHNICAL section or has error"
    print(f"TEST 1 PASS — context: {len(result)} chars")
except AssertionError as e:
    print(f"TEST 1 FAIL — {e}")
except Exception as e:
    print(f"TEST 1 FAIL — unexpected exception: {e}")

# ------------------------------------------------------------------
# TEST 2 — analyze_technicals
# ------------------------------------------------------------------
try:
    result = analyze_technicals.invoke("TCS")
    assert isinstance(result, str), f"Expected str, got {type(result)}"
    assert len(result) > 20, f"Result too short ({len(result)} chars)"
    print(f"TEST 2 PASS — {result[:100]}")
except AssertionError as e:
    print(f"TEST 2 FAIL — {e}")
except Exception as e:
    print(f"TEST 2 FAIL — unexpected exception: {e}")

# ------------------------------------------------------------------
# TEST 3 — analyze_fundamentals
# ------------------------------------------------------------------
try:
    result = analyze_fundamentals.invoke("RELIANCE,1408.80")
    assert isinstance(result, str), f"Expected str, got {type(result)}"
    assert "ROE" in result or "ERROR" not in result, \
        "Missing ROE or has error"
    print(f"TEST 3 PASS — {result[:100]}")
except AssertionError as e:
    print(f"TEST 3 FAIL — {e}")
except Exception as e:
    print(f"TEST 3 FAIL — unexpected exception: {e}")

# ------------------------------------------------------------------
# TEST 4 — get_news_sentiment
# ------------------------------------------------------------------
try:
    result = get_news_sentiment.invoke("TCS")
    assert isinstance(result, str), f"Expected str, got {type(result)}"
    print(f"TEST 4 PASS — {result[:100]}")
except AssertionError as e:
    print(f"TEST 4 FAIL — {e}")
except Exception as e:
    print(f"TEST 4 FAIL — unexpected exception: {e}")

# ------------------------------------------------------------------
# TEST 5 — get_macro_context
# ------------------------------------------------------------------
try:
    result = get_macro_context.invoke("current")
    assert isinstance(result, str), f"Expected str, got {type(result)}"
    assert len(result) > 20, f"Result too short ({len(result)} chars)"
    print(f"TEST 5 PASS — {result[:100]}")
except AssertionError as e:
    print(f"TEST 5 FAIL — {e}")
except Exception as e:
    print(f"TEST 5 FAIL — unexpected exception: {e}")

# ------------------------------------------------------------------
# TEST 6 — get_gold_analysis
# ------------------------------------------------------------------
try:
    result = get_gold_analysis.invoke("current")
    assert isinstance(result, str), f"Expected str, got {type(result)}"
    assert len(result) > 20, f"Result too short ({len(result)} chars)"
    print(f"TEST 6 PASS — {result[:100]}")
except AssertionError as e:
    print(f"TEST 6 FAIL — {e}")
except Exception as e:
    print(f"TEST 6 FAIL — unexpected exception: {e}")

# ------------------------------------------------------------------
# TEST 7 — search_mutual_fund
# ------------------------------------------------------------------
try:
    result = search_mutual_fund.invoke("SBI Bluechip")
    assert isinstance(result, str), f"Expected str, got {type(result)}"
    print(f"TEST 7 PASS — {result[:150]}")
except AssertionError as e:
    print(f"TEST 7 FAIL — {e}")
except Exception as e:
    print(f"TEST 7 FAIL — unexpected exception: {e}")

# ------------------------------------------------------------------
# TEST 8 — ALL_TOOLS list
# ------------------------------------------------------------------
try:
    from llm.tools import ALL_TOOLS
    assert isinstance(ALL_TOOLS, list), f"Expected list, got {type(ALL_TOOLS)}"
    assert len(ALL_TOOLS) == 8, f"Expected 8 tools, got {len(ALL_TOOLS)}"
    print(f"TEST 8 PASS — {len(ALL_TOOLS)} tools registered")
    for t in ALL_TOOLS:
        print(f"  Tool: {t.name}")
except AssertionError as e:
    print(f"TEST 8 FAIL — {e}")
except Exception as e:
    print(f"TEST 8 FAIL — unexpected exception: {e}")

print("=" * 55)
print("  Test suite complete.")
print("=" * 55)
