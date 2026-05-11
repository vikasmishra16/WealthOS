# ============================================================
# CELL 39 — WealthOS Gradio Launch
# Paste this ENTIRE block into a new Colab code cell and run.
# Prerequisites:  llm  must already be defined in this kernel
#                 (loaded in a previous cell — do NOT reload).
# ============================================================

# ── Step 1: Fix pydantic / gradio conflict BEFORE any gradio import ──────────
# The pydantic_core shipped with pydantic 2.7.4 is incompatible with older
# gradio ≤ 4.x which tries to import validate_core_schema.
# Force-reinstall a compatible pair inside the CURRENT kernel process via
# importlib reload — no subprocess needed.

import subprocess, sys

def _pip(args):
    subprocess.check_call(
        [sys.executable, "-m", "pip"] + args,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )

print("[Cell 39] Checking pydantic / gradio versions...")

try:
    from pydantic_core import validate_core_schema   # noqa: F401
    print("[Cell 39] pydantic_core OK — no reinstall needed.")
except ImportError:
    print("[Cell 39] pydantic_core missing validate_core_schema — reinstalling...")
    # Use versions known to be mutually compatible on Python 3.12 in Colab
    _pip(["install", "--quiet", "--upgrade",
          "pydantic==2.5.3",
          "pydantic-core==2.14.6",
          "gradio==4.44.1"])
    print("[Cell 39] Reinstall complete. Reloading pydantic_core...")
    # Evict stale module objects so subsequent imports get the new ABI
    for mod_name in list(sys.modules.keys()):
        if "pydantic" in mod_name or "gradio" in mod_name:
            del sys.modules[mod_name]
    print("[Cell 39] Module cache cleared.")

# ── Step 2: Verify llm is available in kernel memory ─────────────────────────
try:
    llm   # defined in a previous cell
    print(f"[Cell 39] llm object found: {type(llm).__name__}")
except NameError:
    print("[Cell 39] WARNING — 'llm' not found in kernel. "
          "Launching with llm=None (analysis features will be disabled).")
    llm = None

# ── Step 3: (Re-)load the fixed app module ───────────────────────────────────
import importlib, sys as _sys

# Remove any stale cached version of the ui.app module
for mod_name in list(_sys.modules.keys()):
    if mod_name in ("ui.app", "ui"):
        del _sys.modules[mod_name]

_sys.path.insert(0, "/content/WealthOS")

from ui.app import create_app   # import AFTER pydantic shim above
print("[Cell 39] ui.app imported successfully.")

# ── Step 4: Build Gradio interface ───────────────────────────────────────────
print("[Cell 39] Building Gradio interface...")
demo = create_app(llm)
print("[Cell 39] Interface built.")

# ── Step 5: Launch — direct in-kernel launch, share=True for public URL ──────
print("[Cell 39] Launching WealthOS... (public URL will appear below)")
demo.launch(
    share=True,          # generates a  *.gradio.live  public URL
    debug=False,
    show_error=True,
    server_name="0.0.0.0",
    server_port=7860,
    quiet=False,         # print the URL to stdout
    prevent_thread_lock=True   # keeps Colab cell non-blocking
)
# The public gradio.live URL is printed by Gradio itself above.
print("[Cell 39] WealthOS is live. Copy the gradio.live URL from the output above.")
