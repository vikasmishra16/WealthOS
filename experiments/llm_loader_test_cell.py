# ============================================================
# WealthOS — llm_loader TEST CELL
# Paste this entire cell into Google Colab and run it AFTER:
#   - llama-cpp-python is installed (setup cell)
#   - Model file is at /content/drive/MyDrive/WealthOS/models/
#     mistral-7b-instruct-v0.3.Q4_K_M.gguf
# NOTE: Model loading takes 30-60 seconds on T4.
# ============================================================

import sys

for key in list(sys.modules.keys()):
    if "llm_loader" in key:
        del sys.modules[key]

if "/content/WealthOS" not in sys.path:
    sys.path.insert(0, "/content/WealthOS")

from llm.llm_loader import (
    load_model,
    format_prompt,
    generate,
    get_model_info,
)

print("=" * 55)
print("  llm_loader — Test Suite")
print("=" * 55)

# ------------------------------------------------------------------
# TEST 1 — load_model
# ------------------------------------------------------------------
llm = None
try:
    print("Loading model — this takes 30-60 seconds...")
    llm = load_model()
    assert llm is not None, "load_model returned None"
    print("TEST 1 PASS — model loaded")
except AssertionError as e:
    print(f"TEST 1 FAIL — {e}")
except Exception as e:
    print(f"TEST 1 FAIL — unexpected exception: {e}")

# ------------------------------------------------------------------
# TEST 2 — format_prompt
# ------------------------------------------------------------------
try:
    prompt = format_prompt(
        "You are a financial advisor.",
        "What is P/E ratio?"
    )
    assert isinstance(prompt, str), f"Expected str, got {type(prompt)}"
    assert "<s>[INST]" in prompt, "'<s>[INST]' not in prompt"
    assert "[/INST]" in prompt, "'[/INST]' not in prompt"
    assert "You are a financial advisor." in prompt, \
        "System prompt not in output"
    assert "What is P/E ratio?" in prompt, \
        "User message not in output"
    print("TEST 2 PASS — prompt formatted correctly")
    print(f"  Prompt preview: {prompt[:100]}")
except AssertionError as e:
    print(f"TEST 2 FAIL — {e}")
except Exception as e:
    print(f"TEST 2 FAIL — unexpected exception: {e}")

# ------------------------------------------------------------------
# TEST 3 — generate (requires model loaded in TEST 1)
# ------------------------------------------------------------------
if llm is not None:
    try:
        print("Running inference — this takes 10-30 seconds...")
        response = generate(
            llm,
            system_prompt = "You are a financial advisor for Indian markets. Give concise answers.",
            user_message  = "In one sentence, what is a P/E ratio?"
        )
        assert isinstance(response, str), f"Expected str, got {type(response)}"
        assert len(response) > 10, f"Response too short ({len(response)} chars)"
        assert "ERROR" not in response, f"generate returned error: {response}"
        print("TEST 3 PASS — inference working")
        print(f"  Response: {response}")
    except AssertionError as e:
        print(f"TEST 3 FAIL — {e}")
    except Exception as e:
        print(f"TEST 3 FAIL — unexpected exception: {e}")
else:
    print("TEST 3 SKIP — model not loaded (TEST 1 failed)")

# ------------------------------------------------------------------
# TEST 4 — get_model_info
# ------------------------------------------------------------------
if llm is not None:
    try:
        info = get_model_info(llm)
        assert isinstance(info, dict), f"Expected dict, got {type(info)}"
        assert info.get("status") == "loaded", \
            f"Expected status 'loaded', got {info.get('status')}"
        print(f"TEST 4 PASS — {info}")
    except AssertionError as e:
        print(f"TEST 4 FAIL — {e}")
    except Exception as e:
        print(f"TEST 4 FAIL — unexpected exception: {e}")
else:
    print("TEST 4 SKIP — model not loaded (TEST 1 failed)")

print("=" * 55)
print("  Test suite complete.")
print("=" * 55)
