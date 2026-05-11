import os
import sys
sys.path.insert(0, "/content/WealthOS")

DB_PATH = os.getenv("WEALTHOS_DB_PATH", "./db/wealthos.duckdb")


class Tool:
    def __init__(self, name: str, func, description: str):
        self.name        = name
        self.func        = func
        self.description = description

    def run(self, input_str: str) -> str:
        try:
            return self.func(input_str)
        except Exception as e:
            return f"ERROR: {str(e)}"

    def invoke(self, input_str: str) -> str:
        return self.run(input_str)


def get_stock_context(symbol: str) -> str:
    """
    Fetches complete stock context for a given NSE symbol including
    price data, technical signals, fundamental analysis, shareholding
    pattern, governance score, news sentiment, and macro environment.
    Use this as the FIRST tool when analyzing any Indian stock.
    Input: NSE stock symbol (e.g. 'RELIANCE', 'TCS', 'HDFCBANK')
    Output: Complete formatted context string ready for analysis.
    """
    print(f"[Tool] get_stock_context called for {symbol}")
    try:
        from analyzers.context_builder import get_context
        symbol = symbol.strip().upper()
        if symbol.endswith(".NS") or symbol.endswith(".BO"):
            symbol = symbol[:-3]
        _, context_str = get_context(symbol, db_path=DB_PATH)
        return context_str
    except Exception as e:
        return f"ERROR fetching context for {symbol}: {str(e)}"


def analyze_technicals(symbol: str) -> str:
    """
    Runs technical analysis on a stock using price history.
    Computes RSI, MACD, Bollinger Bands, 50/200 DMA, ATR,
    volume trends, support and resistance levels.
    Use this when you need detailed technical signals for a stock.
    Input: NSE stock symbol (e.g. 'RELIANCE', 'TCS')
    Output: Technical analysis summary with buy/sell signals.
    """
    print(f"[Tool] analyze_technicals called for {symbol}")
    try:
        from analyzers.technical_analyzer import analyze_symbol
        symbol = symbol.strip().upper()
        if symbol.endswith(".NS") or symbol.endswith(".BO"):
            symbol = symbol[:-3]
        result = analyze_symbol(symbol, db_path=DB_PATH)
        if "error" in result:
            return f"Technical analysis error: {result['error']}"
        return result.get("summary", "No summary available")
    except Exception as e:
        return f"ERROR in technical analysis for {symbol}: {str(e)}"


def analyze_fundamentals(symbol_and_price: str) -> str:
    """
    Runs fundamental analysis on a stock using Screener.in data.
    Computes P/E, P/B, EV/EBITDA, ROE, ROCE, FCF, EPS growth,
    PEG ratio, debt/equity, CFO/PAT, and quality score.
    Use this when you need valuation and financial health assessment.
    Input: Stock symbol and current price separated by comma.
           Format: 'SYMBOL,PRICE' (e.g. 'RELIANCE,1408.80')
           If price unknown use 'SYMBOL,0'
    Output: Fundamental analysis with quality grade and flags.
    """
    print(f"[Tool] analyze_fundamentals called with {symbol_and_price}")
    try:
        parts = symbol_and_price.strip().split(",")
        symbol = parts[0].strip().upper()
        if symbol.endswith(".NS") or symbol.endswith(".BO"):
            symbol = symbol[:-3]

        try:
            price = float(parts[1].strip()) if len(parts) > 1 else 0.0
        except Exception:
            price = 0.0

        if price <= 0:
            try:
                from collectors.price_collector import get_current_price
                price_data = get_current_price(symbol, db_path=DB_PATH)
                price = price_data.get("current_price", 0.0) or 0.0
            except Exception:
                price = 100.0

        from analyzers.fundamental_analyzer import (
            get_fundamental_analysis, build_fundamental_summary
        )
        sector = "default"
        analysis = get_fundamental_analysis(symbol, price, sector, DB_PATH)
        if "error" in analysis:
            return f"Fundamental analysis error: {analysis['error']}"
        return build_fundamental_summary(analysis)
    except Exception as e:
        return f"ERROR in fundamental analysis: {str(e)}"


def get_news_sentiment(symbol: str) -> str:
    """
    Fetches recent news articles for a stock and analyzes sentiment.
    Returns overall sentiment (POSITIVE/NEUTRAL/NEGATIVE),
    article count, and top headlines from the last 7 days.
    Use this to understand recent market perception of a stock.
    Input: NSE stock symbol (e.g. 'RELIANCE', 'TCS')
    Output: News sentiment summary with headlines.
    """
    print(f"[Tool] get_news_sentiment called for {symbol}")
    try:
        from collectors.news_collector import get_news_summary
        symbol = symbol.strip().upper()
        if symbol.endswith(".NS") or symbol.endswith(".BO"):
            symbol = symbol[:-3]
        result = get_news_summary(symbol, db_path=DB_PATH)
        if not result or result.get("total_articles", 0) == 0:
            return f"No recent news found for {symbol}."
        lines = []
        lines.append(f"News Sentiment for {symbol}:")
        lines.append(
            f"Overall: {result['overall_sentiment']} | "
            f"Articles: {result['total_articles']}"
        )
        lines.append(
            f"Positive: {result['positive_count']} | "
            f"Negative: {result['negative_count']} | "
            f"Neutral: {result['neutral_count']}"
        )
        if result.get("top_headlines"):
            lines.append("Top Headlines:")
            for h in result["top_headlines"][:3]:
                lines.append(f"  \u2022 {h}")
        return "\n".join(lines)
    except Exception as e:
        return f"ERROR fetching news for {symbol}: {str(e)}"


def get_macro_context(query: str = "current") -> str:
    """
    Fetches current Indian macroeconomic indicators including
    India VIX, USD/INR rate, Brent crude price, RBI repo rate,
    10-year G-Sec yield, and overall market regime assessment.
    Use this to understand the broad market environment before
    making investment recommendations.
    Input: Any string (e.g. 'current', 'india macro')
    Output: Current macro snapshot with market regime.
    """
    print("[Tool] get_macro_context called")
    try:
        from collectors.macro_collector import get_market_context
        return get_market_context()
    except Exception as e:
        return f"ERROR fetching macro context: {str(e)}"


def get_mf_analysis(scheme_code: str) -> str:
    """
    Fetches mutual fund analysis including NAV history, returns
    over 1 week, 1 month, 3 months, 1 year, 3 years, 52-week
    high/low, fund house, and category.
    Use this when the user asks about a specific mutual fund.
    Input: Mutual fund scheme code as string (e.g. '119551')
           To find a scheme code, use search_mutual_fund tool first.
    Output: Complete MF analysis with return metrics.
    """
    print(f"[Tool] get_mf_analysis called for scheme {scheme_code}")
    try:
        from collectors.mf_collector import get_mf_summary
        code = int(scheme_code.strip())
        result = get_mf_summary(code, db_path=DB_PATH)
        if not result:
            return f"No data found for scheme code {scheme_code}"
        lines = []
        lines.append(f"Mutual Fund Analysis: {result.get('scheme_name', '?')}")
        lines.append(f"Fund House: {result.get('fund_house', '?')}")
        lines.append(f"Category: {result.get('category', '?')}")
        lines.append(f"Current NAV: \u20b9{result.get('current_nav', '?')}")
        lines.append(f"As of: {result.get('as_of_date', '?')}")
        lines.append("Returns:")
        lines.append(f"  1 Week:  {result.get('returns_1w', 'N/A')}%")
        lines.append(f"  1 Month: {result.get('returns_1m', 'N/A')}%")
        lines.append(f"  3 Month: {result.get('returns_3m', 'N/A')}%")
        lines.append(f"  1 Year:  {result.get('returns_1y', 'N/A')}%")
        lines.append(f"  3 Year:  {result.get('returns_3y', 'N/A')}%")
        lines.append(
            f"52w High: \u20b9{result.get('52w_high', 'N/A')} | "
            f"52w Low: \u20b9{result.get('52w_low', 'N/A')}"
        )
        lines.append(f"Total NAV Records: {result.get('total_nav_records', '?')}")
        return "\n".join(lines)
    except Exception as e:
        return f"ERROR fetching MF analysis: {str(e)}"


def get_gold_analysis(query: str = "current") -> str:
    """
    Fetches current gold price analysis using GoldBees ETF data.
    Returns current GoldBees price, 1-month, 3-month returns,
    52-week high/low, and gold price in INR per gram.
    Use this when the user asks about gold as an investment.
    Input: Any string (e.g. 'current', 'gold analysis')
    Output: Gold price analysis with return metrics.
    """
    print("[Tool] get_gold_analysis called")
    try:
        from collectors.gold_collector import get_gold_summary
        result = get_gold_summary(db_path=DB_PATH)
        if not result or result.get("total_records", 0) == 0:
            return "Gold price data unavailable."
        lines = []
        lines.append("Gold Analysis (via GoldBees ETF):")
        lines.append(f"As of: {result.get('as_of_date', '?')}")
        lines.append(
            f"GoldBees Price: \u20b9{result.get('goldbees_close', '?')} per unit"
        )
        lines.append(
            f"Gold INR/gram: \u20b9{result.get('gold_inr_per_gram', 'N/A')}"
        )
        lines.append("Returns:")
        lines.append(f"  1 Month: {result.get('returns_1m', 'N/A')}%")
        lines.append(f"  3 Month: {result.get('returns_3m', 'N/A')}%")
        lines.append(f"  1 Year:  {result.get('returns_1y', 'N/A')}%")
        lines.append(
            f"52w High: \u20b9{result.get('52w_high_goldbees', 'N/A')} | "
            f"52w Low: \u20b9{result.get('52w_low_goldbees', 'N/A')}"
        )
        lines.append(
            "Note: GoldBees tracks 1 gram of 24K gold in INR. "
            "MCX spot price unavailable from free sources."
        )
        return "\n".join(lines)
    except Exception as e:
        return f"ERROR fetching gold analysis: {str(e)}"


def search_mutual_fund(query: str) -> str:
    """
    Searches for mutual fund schemes by name or fund house.
    Returns matching scheme names and their scheme codes.
    Use this BEFORE get_mf_analysis to find the correct scheme code.
    Input: Fund name or partial name (e.g. 'SBI Bluechip',
           'HDFC Mid Cap', 'Axis ELSS')
    Output: List of matching schemes with scheme codes.
    """
    print(f"[Tool] search_mutual_fund called for '{query}'")
    try:
        from collectors.mf_collector import search_scheme
        results = search_scheme(query)
        if not results:
            return f"No mutual funds found matching '{query}'. Try a shorter search term."
        lines = [f"Mutual funds matching '{query}':"]
        for r in results[:10]:
            lines.append(
                f"  Code: {r['scheme_code']} \u2014 {r['scheme_name']}"
            )
        lines.append(
            "\nUse the scheme code with get_mf_analysis tool."
        )
        return "\n".join(lines)
    except Exception as e:
        return f"ERROR searching mutual funds: {str(e)}"


ALL_TOOLS = [
    Tool("get_stock_context",     get_stock_context,
         "Fetches complete stock context for a given NSE symbol. "
         "Input: stock symbol like 'RELIANCE'"),
    Tool("analyze_technicals",    analyze_technicals,
         "Runs technical analysis. Input: stock symbol like 'TCS'"),
    Tool("analyze_fundamentals",  analyze_fundamentals,
         "Runs fundamental analysis. Input: 'SYMBOL,PRICE' like 'RELIANCE,1408.80'"),
    Tool("get_news_sentiment",    get_news_sentiment,
         "Gets news sentiment. Input: stock symbol like 'RELIANCE'"),
    Tool("get_macro_context",     get_macro_context,
         "Gets macro indicators. Input: any string like 'current'"),
    Tool("get_mf_analysis",       get_mf_analysis,
         "Gets MF analysis. Input: scheme code like '119551'"),
    Tool("get_gold_analysis",     get_gold_analysis,
         "Gets gold analysis. Input: any string like 'current'"),
    Tool("search_mutual_fund",    search_mutual_fund,
         "Searches MF by name. Input: fund name like 'SBI Bluechip'"),
]
