import os
def _safe_call(fn, *args, **kwargs):
    try:
        return fn(*args, **kwargs)
    except Exception as e:
        print(f"[ContextBuilder] Warning — {fn.__name__} failed: {e}")
        return {"error": str(e)}


def build_stock_context(
    symbol: str,
    exchange: str = "NSE",
    sector: str = "default",
    company_name: str = "",
    db_path: str = os.getenv("WEALTHOS_DB_PATH", "./db/wealthos.duckdb")
) -> dict:
    symbol = symbol.strip().upper()
    if symbol.endswith(".NS") or symbol.endswith(".BO"):
        symbol = symbol[:-3]

    from collectors.price_collector       import fetch_price_history, get_current_price
    from collectors.macro_collector       import get_macro_snapshot, get_risk_free_rate
    from collectors.nse_collector         import get_shareholding_pattern, get_governance_flags, get_corporate_actions
    from collectors.news_collector        import get_news_summary
    from collectors.fundamental_collector import fetch_fundamentals
    from analyzers.technical_analyzer    import analyze_symbol
    from analyzers.fundamental_analyzer  import get_fundamental_analysis, build_fundamental_summary

    try:
        print(f"[ContextBuilder] Building context for {symbol}...")

        price_data    = _safe_call(get_current_price, symbol, exchange, db_path)
        current_price = (
            price_data.get("current_price")
            if isinstance(price_data, dict) and "error" not in price_data
            else None
        )

        technical = _safe_call(analyze_symbol, symbol, exchange, db_path)

        if current_price:
            fundamental = _safe_call(
                get_fundamental_analysis, symbol, current_price, sector, db_path
            )
        else:
            fundamental = {"error": "No current price available"}

        shareholding = _safe_call(get_shareholding_pattern, symbol, db_path)
        governance   = _safe_call(get_governance_flags, symbol, db_path)
        corp_actions = _safe_call(get_corporate_actions, symbol, db_path)

        news = _safe_call(get_news_summary, symbol, company_name, db_path)

        macro     = _safe_call(get_macro_snapshot, db_path)
        risk_free = _safe_call(get_risk_free_rate, db_path)
        if isinstance(risk_free, dict):
            risk_free = 0.071

        return {
            "symbol":        symbol,
            "exchange":      exchange,
            "sector":        sector,
            "company_name":  company_name,
            "current_price": current_price,
            "price_data":    price_data,
            "technical":     technical,
            "fundamental":   fundamental,
            "shareholding":  shareholding,
            "governance":    governance,
            "corp_actions":  corp_actions,
            "news":          news,
            "macro":         macro,
            "risk_free_rate": risk_free if isinstance(risk_free, float) else 0.071
        }

    except Exception as e:
        print(f"[ContextBuilder] Error building context for {symbol}: {e}")
        return {"error": str(e), "symbol": symbol}


def format_context_string(context: dict) -> str:
    if "error" in context and "symbol" not in context:
        return f"ERROR: Could not build context — {context.get('error')}"

    symbol = context.get("symbol", "UNKNOWN")
    lines  = []

    def section(title):
        lines.append("")
        lines.append("━" * 50)
        lines.append(title)
        lines.append("━" * 50)

    def sg(obj, key, fallback="N/A"):
        if obj is None or not isinstance(obj, dict):
            return fallback
        val = obj.get(key)
        return val if val is not None else fallback

    lines.append(f"STOCK CONTEXT: {symbol}")
    lines.append(
        f"Exchange: {context.get('exchange', 'NSE')} | "
        f"Sector: {context.get('sector', 'default')} | "
        f"As of: {__import__('datetime').datetime.utcnow().strftime('%Y-%m-%d')}"
    )

    section("PRICE SNAPSHOT")
    p = context.get("price_data", {})
    lines.append(f"Current Price:    ₹{sg(p, 'current_price')}")
    lines.append(f"Change (1d):      {sg(p, 'change_pct')}%")
    lines.append(f"52w High:         ₹{sg(p, 'week_52_high')}")
    lines.append(f"52w Low:          ₹{sg(p, 'week_52_low')}")
    lines.append(f"Avg Volume (20d): {sg(p, 'avg_volume_20d')}")

    section("TECHNICAL ANALYSIS")
    t = context.get("technical", {})
    if isinstance(t, dict) and "error" in t:
        lines.append(f"Technical data unavailable: {t['error']}")
    else:
        lines.append(f"Overall Signal:  {sg(t, 'overall_signal')}")
        lines.append(f"50 DMA:  ₹{sg(t, 'dma_50')} — {sg(t, 'dma50_signal')}")
        lines.append(f"200 DMA: ₹{sg(t, 'dma_200')} — {sg(t, 'dma200_signal')}")
        lines.append(f"Golden Cross: {'YES' if t.get('golden_cross') else 'NO'}")
        lines.append(f"RSI(14): {sg(t, 'rsi')} — {sg(t, 'rsi_signal')}")
        lines.append(f"MACD: {sg(t, 'macd_signal')}")
        lines.append(f"Bollinger: {sg(t, 'bb_signal')}")
        lines.append(f"ATR: ₹{sg(t, 'atr')} ({sg(t, 'atr_pct')}% of price)")
        lines.append(
            f"Volume: {sg(t, 'volume_trend')} "
            f"(ratio: {sg(t, 'vol_ratio')}x) — "
            f"{sg(t, 'volume_confirmation')}"
        )
        sup = t.get("support_levels", [])
        res = t.get("resistance_levels", [])
        lines.append(f"Support Levels:    {sup if sup else 'None identified'}")
        lines.append(f"Resistance Levels: {res if res else 'None identified'}")

    section("FUNDAMENTAL ANALYSIS")
    f = context.get("fundamental", {})
    if isinstance(f, dict) and "error" in f:
        lines.append(f"Fundamental data unavailable: {f['error']}")
    else:
        from analyzers.fundamental_analyzer import build_fundamental_summary
        lines.append(build_fundamental_summary(f))
        lines.append("")
        lines.append("NOTE: ROE and P/B computed on paid-up Equity Capital only")
        lines.append("      (Reserves excluded — standard Screener.in data limitation)")
        lines.append(
            f"      ROCE ({sg(f.get('ratios', {}), 'roce')}%) is more reliable."
        )

    section("SHAREHOLDING & GOVERNANCE")
    sh  = context.get("shareholding", {})
    gov = context.get("governance", {})
    if isinstance(sh, dict) and "error" not in sh:
        lines.append(f"Quarter:      {sg(sh, 'quarter')}")
        lines.append(f"Promoter:     {sg(sh, 'promoter_pct')}%")
        lines.append(f"Public:       {sg(sh, 'public_pct')}%")
        lines.append(f"FII:          {sg(sh, 'fii_pct')} (unavailable — NSE API limitation)")
        lines.append(f"DII:          {sg(sh, 'dii_pct')} (unavailable — NSE API limitation)")
        lines.append(f"Pledge:       {sg(sh, 'pledge_pct')} (unavailable — NSE API limitation)")
    if isinstance(gov, dict) and "error" not in gov:
        lines.append(f"Promoter Flag:         {sg(gov, 'promoter_flag')}")
        lines.append(f"Pledge Flag:           {sg(gov, 'pledge_flag')}")
        lines.append(f"Institutional Interest:{sg(gov, 'institutional_interest')}")
        lines.append(f"Governance Score:      {sg(gov, 'governance_score')}/100")

    section("RECENT CORPORATE ACTIONS")
    ca = context.get("corp_actions", [])
    if isinstance(ca, list) and ca:
        for action in ca[:5]:
            lines.append(
                f"  {action.get('ex_date', '?')} — "
                f"{action.get('purpose') or action.get('subject') or '—'}"
            )
    else:
        lines.append("No recent corporate actions found.")

    section("NEWS SENTIMENT (Last 7 Days)")
    n = context.get("news", {})
    if isinstance(n, dict) and "error" not in n:
        lines.append(
            f"Overall:  {sg(n, 'overall_sentiment')} | "
            f"{sg(n, 'total_articles')} articles"
        )
        lines.append(
            f"Positive: {sg(n, 'positive_count')} | "
            f"Negative: {sg(n, 'negative_count')} | "
            f"Neutral:  {sg(n, 'neutral_count')}"
        )
        headlines = n.get("top_headlines", [])
        if headlines:
            lines.append("Top Headlines:")
            for h in headlines[:3]:
                lines.append(f"  \u2022 {h}")
    else:
        lines.append("News data unavailable.")

    section("MACRO & MARKET CONTEXT")
    m = context.get("macro", {})
    if isinstance(m, dict) and "error" not in m:
        lines.append(f"India VIX:      {sg(m, 'vix')}")
        lines.append(f"USD/INR:        {sg(m, 'usd_inr')}")
        lines.append(f"Brent Crude:    ${sg(m, 'brent_crude')}")
        lines.append(f"Repo Rate:      {sg(m, 'repo_rate')}%")
        lines.append(f"10yr G-Sec:     {sg(m, 'ten_yr_gsec')}%")
        rfr = context.get("risk_free_rate", 0.071)
        lines.append(f"Risk-Free Rate: {rfr * 100:.1f}%")

        vix = m.get("vix")
        if vix is not None:
            if vix > 20:
                regime = "CAUTIOUS — elevated volatility"
            elif vix < 14:
                regime = "CALM — low volatility"
            else:
                regime = "NEUTRAL"
            lines.append(f"Market Regime:  {regime}")
    else:
        lines.append("Macro data unavailable.")

    return "\n".join(lines)


def get_context(
    symbol: str,
    exchange: str = "NSE",
    sector: str = "default",
    company_name: str = "",
    db_path: str = os.getenv("WEALTHOS_DB_PATH", "./db/wealthos.duckdb")
) -> tuple:
    print(f"[ContextBuilder] Starting full context build for {symbol}")
    context_dict = build_stock_context(symbol, exchange, sector, company_name, db_path)
    context_str  = format_context_string(context_dict)
    print(f"[ContextBuilder] Context ready — {len(context_str)} chars")
    return (context_dict, context_str)
