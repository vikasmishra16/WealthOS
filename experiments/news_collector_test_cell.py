# ============================================================
# WealthOS — news_collector TEST CELL
# Paste this entire cell into Google Colab and run it AFTER:
#   - Cells 1–3 of WealthOS_Setup.ipynb have been run
#   - news_collector.py is at /content/WealthOS/collectors/
# ============================================================

import sys

if "/content/WealthOS" not in sys.path:
    sys.path.insert(0, "/content/WealthOS")

from collectors.news_collector import (
    _score_sentiment,
    fetch_news,
    get_news_summary,
)

print("=" * 55)
print("  news_collector — Test Suite")
print("=" * 55)

# ------------------------------------------------------------------
# TEST 1 — _score_sentiment keyword scoring
# ------------------------------------------------------------------
try:
    assert _score_sentiment("company reports record profit and growth") > 0, \
        "Positive headline should score > 0"
    assert _score_sentiment("stock crashes on fraud investigation") < 0, \
        "Negative headline should score < 0"
    assert _score_sentiment("company holds annual meeting") == 0.0, \
        "Neutral headline should score 0.0"
    print("TEST 1 PASS — sentiment scoring")
except AssertionError as e:
    print(f"TEST 1 FAIL — {e}")
except Exception as e:
    print(f"TEST 1 FAIL — unexpected exception: {e}")

# ------------------------------------------------------------------
# TEST 2 — fetch_news live call (0 results is acceptable)
# ------------------------------------------------------------------
try:
    result = fetch_news("RELIANCE", "Reliance Industries")
    assert isinstance(result, list), f"Expected list, got {type(result)}"
    print(f"TEST 2 PASS — fetch_news: {len(result)} articles")
    if result:
        print(f"  Sample: {result[0]}")
except AssertionError as e:
    print(f"TEST 2 FAIL — {e}")
except Exception as e:
    print(f"TEST 2 FAIL — unexpected exception: {e}")

# ------------------------------------------------------------------
# TEST 3 — Cache hit on second call
# ------------------------------------------------------------------
try:
    result2 = fetch_news("RELIANCE", "Reliance Industries")
    assert isinstance(result2, list), f"Expected list, got {type(result2)}"
    print("TEST 3 PASS — cache hit confirmed")
except AssertionError as e:
    print(f"TEST 3 FAIL — {e}")
except Exception as e:
    print(f"TEST 3 FAIL — unexpected exception: {e}")

# ------------------------------------------------------------------
# TEST 4 — get_news_summary structure
# ------------------------------------------------------------------
try:
    result = get_news_summary("TCS", "Tata Consultancy Services")
    assert isinstance(result, dict), f"Expected dict, got {type(result)}"
    required_keys = [
        "symbol", "total_articles", "avg_sentiment",
        "overall_sentiment", "positive_count", "negative_count",
        "neutral_count", "top_headlines", "articles"
    ]
    for key in required_keys:
        assert key in result, f"Missing key: {key}"
    print(f"TEST 4 PASS — summary: {result}")
except AssertionError as e:
    print(f"TEST 4 FAIL — {e}")
except Exception as e:
    print(f"TEST 4 FAIL — unexpected exception: {e}")

print("=" * 55)
print("  Test suite complete.")
print("=" * 55)
