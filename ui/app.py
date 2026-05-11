import os
# =============================================================================
# WealthOS — Gradio UI  (ui/app.py)
# Fixed for: pydantic conflict, gr.State Llama callable, DuckDB startup block,
#            subprocess silent death — runs DIRECTLY in the Colab kernel.
# =============================================================================
# HOW THIS FILE IS USED:
#   Do NOT run this as __main__ from a subprocess.
#   Import create_app() from the Colab launch cell and call demo.launch() there.
#   The llm object is passed in from kernel memory — model is NOT reloaded here.
# =============================================================================

import sys
sys.path.insert(0, "/content/WealthOS")


# ---------------------------------------------------------------------------
# Lazy imports — gradio is imported AFTER pydantic shim is applied in the
# launch cell, so we do NOT import it at module top-level.
# ---------------------------------------------------------------------------


DB_PATH = os.getenv("WEALTHOS_DB_PATH", "./db/wealthos.duckdb")
MODEL_PATH = os.getenv("WEALTHOS_MODEL_PATH", "./models/mistral-7b-instruct-v0.3.Q4_K_M.gguf")


# ---------------------------------------------------------------------------
# Dashboard helper — called ONLY on button click, never at import / build time
# ---------------------------------------------------------------------------

def get_market_dashboard() -> str:
    """Fetch gold + macro data. Called lazily from the Refresh button only."""
    lines = ["WEALTHOS MARKET DASHBOARD", "=" * 40, ""]
    try:
        from collectors.gold_collector import get_gold_summary
        gold = get_gold_summary(DB_PATH)
        lines.append("GOLD (GoldBees ETF)")
        lines.append("-" * 30)
        lines.append(f"Price:      \u20b9{gold.get('goldbees_close', 'N/A')} per unit")
        lines.append(f"As of:      {gold.get('as_of_date', 'N/A')}")
        lines.append(f"1M Return:  {gold.get('returns_1m', 'N/A')}%")
        lines.append(f"3M Return:  {gold.get('returns_3m', 'N/A')}%")
        lines.append(f"1Y Return:  {gold.get('returns_1y', 'N/A')}%")
        lines.append(f"52w High:   \u20b9{gold.get('52w_high_goldbees', 'N/A')}")
        lines.append(f"52w Low:    \u20b9{gold.get('52w_low_goldbees', 'N/A')}")
    except Exception as e:
        lines.append(f"Gold data unavailable: {e}")
    lines.append("")
    try:
        from collectors.macro_collector import get_macro_snapshot
        macro = get_macro_snapshot(DB_PATH)
        lines.append("MACRO INDICATORS")
        lines.append("-" * 30)
        lines.append(f"India VIX:    {macro.get('vix', 'N/A')}")
        lines.append(f"USD/INR:      {macro.get('usd_inr', 'N/A')}")
        lines.append(f"Brent Crude:  ${macro.get('brent_crude', 'N/A')}")
        lines.append(f"Repo Rate:    {macro.get('repo_rate', 'N/A')}%")
        lines.append(f"10yr G-Sec:   {macro.get('ten_yr_gsec', 'N/A')}%")
        vix = macro.get("vix")
        if vix is not None:
            if vix > 20:
                regime = "\u26a0\ufe0f CAUTIOUS \u2014 elevated volatility"
            elif vix < 14:
                regime = "\u2705 CALM \u2014 low volatility"
            else:
                regime = "\u27a1\ufe0f NEUTRAL"
            lines.append(f"Market Regime: {regime}")
    except Exception as e:
        lines.append(f"Macro data unavailable: {e}")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Core handlers — receive llm_state as a plain list [llm] so Gradio never
# tries to call the Llama object as a factory function.
# ---------------------------------------------------------------------------

def analyze_stock(symbol: str, llm_state: list):
    """Generator: stream stock analysis for the given NSE symbol."""
    if not symbol or not symbol.strip():
        yield "Please enter a stock symbol (e.g. RELIANCE, TCS)"
        return

    symbol = symbol.strip().upper()
    # Support .NS / .BO suffixes
    if symbol.endswith(".NS") or symbol.endswith(".BO"):
        symbol = symbol[:-3]

    if not llm_state or llm_state[0] is None:
        yield "Model not loaded. Please restart the app."
        return

    yield f"Fetching data for {symbol}...\n"
    try:
        from llm.agent import ask_wealthos
        question = (
            f"Analyze {symbol} stock and give me a detailed buy, hold, "
            f"or sell recommendation with specific data points."
        )
        answer = ask_wealthos(llm_state[0], question, verbose=False)
        yield answer
    except Exception as e:
        yield f"Error analyzing {symbol}: {str(e)}"


def ask_question(question: str, llm_state: list):
    """Generator: stream advisory answer for an arbitrary investment question."""
    if not question or not question.strip():
        yield "Please enter a question."
        return

    if not llm_state or llm_state[0] is None:
        yield "Model not loaded. Please restart the app."
        return

    yield "Thinking...\n"
    try:
        from llm.agent import ask_wealthos
        answer = ask_wealthos(llm_state[0], question.strip(), verbose=False)
        yield answer
    except Exception as e:
        yield f"Error: {str(e)}"


def refresh_dashboard():
    """Called only when the user clicks 'Refresh Data' — never at startup."""
    try:
        return get_market_dashboard()
    except Exception as e:
        return f"Dashboard error: {str(e)}"


# ---------------------------------------------------------------------------
# UI builder — receives the already-loaded llm object from kernel memory.
# gr.State stores [llm] (a list) so Gradio cannot mistake it for a callable
# initializer.  All collectors/DuckDB calls are deferred to button clicks.
# ---------------------------------------------------------------------------

def create_app(llm):
    """
    Build and return the Gradio Blocks demo.
    llm  — Llama instance already in kernel memory (may be None for testing).
    """
    import gradio as gr   # imported here so the launch cell can patch pydantic first

    status_text = "\u2705 Model Ready" if llm is not None else "\u274c Model Not Loaded"

    # Store llm in a plain list so gr.State receives a list, not a callable.
    # Gradio calls value() if value is callable — wrapping in a list avoids this.
    _llm_container = [llm]

    with gr.Blocks(theme=gr.themes.Soft(), title="WealthOS") as demo:

        gr.Markdown("# \U0001f3e6 WealthOS")
        gr.Markdown("### AI Investment Advisory for Indian Markets")
        gr.Markdown("*Powered by Mistral 7B \u2022 NSE \u2022 Screener.in \u2022 mfapi.in*")
        gr.Markdown(f"**Status:** {status_text}")

        # ---- Persistent state: list wrapper prevents Gradio callable-check ----
        llm_state = gr.State(value=_llm_container)

        # ================================================================
        # Tab 1 — Stock Analyzer
        # ================================================================
        with gr.Tab("\U0001f4ca Stock Analyzer"):
            gr.Markdown("Enter any NSE-listed stock symbol to get a full analysis.")
            symbol_input = gr.Textbox(
                label="Stock Symbol",
                placeholder="e.g. RELIANCE, TCS, HDFCBANK, INFY",
                lines=1,
                elem_id="stock_symbol_input"
            )
            analyze_btn = gr.Button("Analyze", variant="primary", elem_id="analyze_btn")
            stock_output = gr.Textbox(
                label="WealthOS Analysis",
                lines=25,
                max_lines=40,
                elem_id="stock_output"
            )
            analyze_btn.click(
                fn=analyze_stock,
                inputs=[symbol_input, llm_state],
                outputs=stock_output,
                show_progress=True
            )
            gr.Examples(
                examples=[["RELIANCE"], ["TCS"], ["HDFCBANK"], ["INFY"], ["WIPRO"]],
                inputs=symbol_input,
                elem_id="stock_examples"
            )

        # ================================================================
        # Tab 2 — Ask WealthOS
        # ================================================================
        with gr.Tab("\U0001f4ac Ask WealthOS"):
            gr.Markdown("Ask any investment question in plain English.")
            question_input = gr.Textbox(
                label="Your Question",
                placeholder="e.g. I have \u20b95 lakh to invest for 5 years. Where should I put it?",
                lines=3,
                elem_id="question_input"
            )
            ask_btn = gr.Button("Ask WealthOS", variant="primary", elem_id="ask_btn")
            answer_output = gr.Textbox(
                label="WealthOS Answer",
                lines=25,
                max_lines=40,
                elem_id="answer_output"
            )
            ask_btn.click(
                fn=ask_question,
                inputs=[question_input, llm_state],
                outputs=answer_output,
                show_progress=True
            )
            gr.Examples(
                examples=[
                    ["I have \u20b95 lakh to invest for 5 years with moderate risk. Where should I put it?"],
                    ["Should I invest in gold or equity mutual funds right now?"],
                    ["What is the current macro environment and how should it affect my portfolio?"],
                    ["Analyze RELIANCE and TCS and tell me which is better to buy now."],
                    ["I am in the 30% tax bracket investing \u20b92 lakh. What is the most tax-efficient option?"]
                ],
                inputs=question_input,
                elem_id="question_examples"
            )

        # ================================================================
        # Tab 3 — Market Dashboard (all DB access deferred to button click)
        # ================================================================
        with gr.Tab("\U0001f4c8 Market Dashboard"):
            gr.Markdown("Live gold prices and macro indicators.")
            gr.Markdown("Click **Refresh** to load live market data from the database.")
            refresh_btn = gr.Button(
                "\U0001f504 Refresh Data",
                variant="primary",
                elem_id="refresh_btn"
            )
            dashboard_output = gr.Textbox(
                label="Market Data",
                lines=20,
                max_lines=30,
                value="Click 'Refresh Data' to load gold and macro indicators.",
                elem_id="dashboard_output"
            )
            refresh_btn.click(
                fn=refresh_dashboard,
                inputs=[],
                outputs=dashboard_output,
                show_progress=True
            )

    return demo


# ---------------------------------------------------------------------------
# __main__ guard — only used for local testing outside Colab.
# In Colab, use the Cell 39 launch cell below; do NOT run as subprocess.
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    # Local test only — loads model fresh (not needed in Colab)
    print("[app.py] Running in __main__ mode (local test only)")
    try:
        from llm.llm_loader import load_model
        llm = load_model(MODEL_PATH)
    except Exception as e:
        print(f"[app.py] Model load failed: {e} — launching with llm=None")
        llm = None

    import gradio as gr  # noqa: F401 — needed for create_app
    demo = create_app(llm)
    demo.launch(
        share=True,
        debug=False,
        show_error=True,
        server_name="0.0.0.0",
        server_port=7860
    )