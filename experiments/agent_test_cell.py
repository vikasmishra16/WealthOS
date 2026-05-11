# ============================================================
# WealthOS — llm/agent TEST CELL
# Paste this entire cell into Google Colab and run it AFTER:
#   - LLM loaded from Cell 30 (do NOT reload)
#   - All modules at /content/WealthOS/
# IMPORTANT: Tests 3 and 4 take 30-120 seconds each.
# ============================================================

import sys

for key in list(sys.modules.keys()):
    if "agent" in key:
        del sys.modules[key]

if "/content/WealthOS" not in sys.path:
    sys.path.insert(0, "/content/WealthOS")

print("=" * 55)
print("  llm/agent — Test Suite")
print("=" * 55)

# ------------------------------------------------------------------
# TEST 1 — _select_tools with stock question
# ------------------------------------------------------------------
try:
    from llm.agent import _select_tools
    from llm.tools import ALL_TOOLS
    tool_calls = _select_tools(llm, "Should I buy RELIANCE stock?", ALL_TOOLS)
    assert isinstance(tool_calls, list), f"Expected list, got {type(tool_calls)}"
    print(f"TEST 1 PASS — selected {len(tool_calls)} tools: {tool_calls}")
except AssertionError as e:
    print(f"TEST 1 FAIL — {e}")
except Exception as e:
    print(f"TEST 1 FAIL — unexpected exception: {e}")

# ------------------------------------------------------------------
# TEST 2 — _execute_tools
# ------------------------------------------------------------------
try:
    from llm.agent import _execute_tools
    mock_calls = [{"tool": "get_macro_context", "input": "current"}]
    result = _execute_tools(mock_calls, ALL_TOOLS)
    assert isinstance(result, str), f"Expected str, got {type(result)}"
    assert len(result) > 20, f"Result too short ({len(result)} chars)"
    print(f"TEST 2 PASS — tool execution: {len(result)} chars")
except AssertionError as e:
    print(f"TEST 2 FAIL — {e}")
except Exception as e:
    print(f"TEST 2 FAIL — unexpected exception: {e}")

# ------------------------------------------------------------------
# TEST 3 — run_agent full pipeline (simple question)
# ------------------------------------------------------------------
try:
    from llm.agent import run_agent
    print("Running full agent pipeline — takes 30-90 seconds...")
    answer = run_agent(
        llm=llm,
        question="What is the current macro environment in India?",
        tools=ALL_TOOLS,
        verbose=True
    )
    assert isinstance(answer, str), f"Expected str, got {type(answer)}"
    assert len(answer) > 50, f"Answer too short ({len(answer)} chars)"
    assert "Agent error" not in answer, f"Agent returned error: {answer}"
    print(f"TEST 3 PASS — answer: {len(answer)} chars")
    print(answer)
except AssertionError as e:
    print(f"TEST 3 FAIL — {e}")
except Exception as e:
    print(f"TEST 3 FAIL — unexpected exception: {e}")

# ------------------------------------------------------------------
# TEST 4 — ask_wealthos end-to-end
# ------------------------------------------------------------------
try:
    from llm.agent import ask_wealthos
    print("Running ask_wealthos — takes 60-120 seconds...")
    answer = ask_wealthos(
        llm=llm,
        question="Analyze RELIANCE and give me a buy or sell recommendation",
        verbose=True
    )
    assert isinstance(answer, str), f"Expected str, got {type(answer)}"
    assert len(answer) > 100, f"Answer too short ({len(answer)} chars)"
    print(f"TEST 4 PASS — {len(answer)} chars")
    print(answer)
except AssertionError as e:
    print(f"TEST 4 FAIL — {e}")
except Exception as e:
    print(f"TEST 4 FAIL — unexpected exception: {e}")

print("=" * 55)
print("  Test suite complete.")
print("=" * 55)
