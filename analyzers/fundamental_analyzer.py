import os
RISK_FREE_RATE = 0.071
ERP            = 0.060
TAX_RATE       = 0.25

SECTOR_PE = {
    "banks":      12,
    "nbfc":       18,
    "it":         25,
    "pharma":     28,
    "fmcg":       45,
    "auto":       20,
    "cement":     22,
    "steel":      10,
    "oil_gas":    10,
    "telecom":    30,
    "realty":     35,
    "infra":      18,
    "power":      15,
    "chemicals":  25,
    "default":    22
}


def compute_ratios(records: list, current_price: float) -> dict:
    try:
        if not records or current_price is None or current_price <= 0:
            return {"error": "Invalid input — no records or invalid price"}

        latest = records[0]

        pat_margin = None
        if latest["revenue"] and latest["pat"] and latest["revenue"] != 0:
            pat_margin = round(latest["pat"] / latest["revenue"] * 100, 2)

        ebitda_margin = None
        if latest["revenue"] and latest["ebitda"] and latest["revenue"] != 0:
            ebitda_margin = round(latest["ebitda"] / latest["revenue"] * 100, 2)

        roe = None
        if (latest["pat"] and latest["shareholders_equity"]
                and latest["shareholders_equity"] != 0):
            roe = round(latest["pat"] / latest["shareholders_equity"] * 100, 2)

        roce = None
        if (latest["pat"] and latest["shareholders_equity"]
                and latest["total_debt"] is not None):
            ebit = latest["pat"] / (1 - TAX_RATE)
            capital_employed = latest["shareholders_equity"] + (latest["total_debt"] or 0)
            if capital_employed != 0:
                roce = round(ebit / capital_employed * 100, 2)

        pe_ratio = None
        if latest["eps"] and latest["eps"] != 0:
            pe_ratio = round(current_price / latest["eps"], 2)

        pb_ratio = None
        if latest["eps"] and latest["eps"] != 0 and latest["pat"]:
            shares = latest["pat"] / latest["eps"]
            if shares and shares != 0 and latest["shareholders_equity"]:
                bvps = latest["shareholders_equity"] / shares
                if bvps and bvps != 0:
                    pb_ratio = round(current_price / bvps, 2)

        ev_ebitda = None
        if latest["eps"] and latest["eps"] != 0 and latest["pat"]:
            shares_cr  = latest["pat"] / latest["eps"]
            market_cap = current_price * shares_cr
            ev = (market_cap
                  + (latest["total_debt"] or 0)
                  - (latest["cash"] or 0))
            if latest["ebitda"] and latest["ebitda"] != 0:
                ev_ebitda = round(ev / latest["ebitda"], 2)

        debt_to_equity = None
        if (latest["total_debt"] is not None
                and latest["shareholders_equity"]
                and latest["shareholders_equity"] != 0):
            debt_to_equity = round(
                latest["total_debt"] / latest["shareholders_equity"], 2
            )

        cfo_to_pat = None
        if latest["cfo"] and latest["pat"] and latest["pat"] != 0:
            cfo_to_pat = round(latest["cfo"] / latest["pat"], 2)

        fcf = None
        if latest["cfo"] is not None and latest["cfi"] is not None:
            fcf = round(latest["cfo"] - abs(latest["cfi"]), 2)

        fcf_to_debt = None
        if fcf is not None and latest["total_debt"] and latest["total_debt"] != 0:
            fcf_to_debt = round(fcf / latest["total_debt"], 2)

        eps_growth_3y = None
        if len(records) >= 4:
            if (records[3]["eps"] and records[3]["eps"] != 0
                    and latest["eps"]):
                eps_growth_3y = round(
                    ((latest["eps"] / records[3]["eps"]) ** (1 / 3) - 1) * 100, 2
                )

        eps_growth_5y = None
        if len(records) >= 6:
            if (records[5]["eps"] and records[5]["eps"] != 0
                    and latest["eps"]):
                eps_growth_5y = round(
                    ((latest["eps"] / records[5]["eps"]) ** (1 / 5) - 1) * 100, 2
                )

        revenue_growth_1y = None
        if (len(records) >= 2
                and records[1]["revenue"]
                and records[1]["revenue"] != 0
                and latest["revenue"]):
            revenue_growth_1y = round(
                (latest["revenue"] - records[1]["revenue"])
                / records[1]["revenue"] * 100, 2
            )

        peg_ratio = None
        if pe_ratio and eps_growth_3y and eps_growth_3y > 0:
            peg_ratio = round(pe_ratio / eps_growth_3y, 2)

        return {
            "year":               latest["year"],
            "revenue":            latest["revenue"],
            "ebitda":             latest["ebitda"],
            "pat":                latest["pat"],
            "eps":                latest["eps"],
            "total_assets":       latest["total_assets"],
            "total_debt":         latest["total_debt"],
            "shareholders_equity": latest["shareholders_equity"],
            "cash":               latest["cash"],
            "cfo":                latest["cfo"],
            "pat_margin":         pat_margin,
            "ebitda_margin":      ebitda_margin,
            "roe":                roe,
            "roce":               roce,
            "pe_ratio":           pe_ratio,
            "pb_ratio":           pb_ratio,
            "ev_ebitda":          ev_ebitda,
            "debt_to_equity":     debt_to_equity,
            "cfo_to_pat":         cfo_to_pat,
            "fcf":                fcf,
            "fcf_to_debt":        fcf_to_debt,
            "eps_growth_3y":      eps_growth_3y,
            "eps_growth_5y":      eps_growth_5y,
            "revenue_growth_1y":  revenue_growth_1y,
            "peg_ratio":          peg_ratio,
            "promoter_trend":     None
        }

    except Exception as e:
        return {"error": str(e)}


def score_quality(ratios: dict) -> dict:
    if "error" in ratios:
        return {"error": ratios["error"]}

    score = 100
    flags = {}

    pat_margin = ratios.get("pat_margin")
    if pat_margin is None:
        flags["pat_margin"] = "UNKNOWN"
    elif pat_margin >= 15:
        flags["pat_margin"] = "EXCELLENT"
    elif pat_margin >= 8:
        flags["pat_margin"] = "GOOD"
    elif pat_margin >= 3:
        flags["pat_margin"] = "AVERAGE"
        score -= 10
    else:
        flags["pat_margin"] = "WEAK"
        score -= 20

    roe = ratios.get("roe")
    if roe is None:
        flags["roe"] = "UNKNOWN"
    elif roe >= 20:
        flags["roe"] = "EXCELLENT"
    elif roe >= 12:
        flags["roe"] = "GOOD"
    elif roe >= 8:
        flags["roe"] = "AVERAGE"
        score -= 10
    else:
        flags["roe"] = "WEAK"
        score -= 20

    roce = ratios.get("roce")
    if roce is None:
        flags["roce"] = "UNKNOWN"
    elif roce >= 15:
        flags["roce"] = "EXCELLENT"
    elif roce >= 10:
        flags["roce"] = "GOOD"
    elif roce >= 6:
        flags["roce"] = "AVERAGE"
        score -= 10
    else:
        flags["roce"] = "WEAK"
        score -= 20

    cfo_to_pat = ratios.get("cfo_to_pat")
    if cfo_to_pat is None:
        flags["cfo_to_pat"] = "UNKNOWN"
    elif cfo_to_pat >= 1.0:
        flags["cfo_to_pat"] = "EXCELLENT — strong cash conversion"
    elif cfo_to_pat >= 0.7:
        flags["cfo_to_pat"] = "GOOD"
    elif cfo_to_pat >= 0.5:
        flags["cfo_to_pat"] = "AVERAGE"
        score -= 10
    else:
        flags["cfo_to_pat"] = "WEAK — earnings not converting to cash"
        score -= 20

    fcf = ratios.get("fcf")
    if fcf is None:
        flags["fcf"] = "UNKNOWN"
    elif fcf > 0:
        flags["fcf"] = "POSITIVE FCF"
    else:
        flags["fcf"] = "NEGATIVE FCF"
        score -= 15

    debt_to_equity = ratios.get("debt_to_equity")
    if debt_to_equity is None:
        flags["debt_to_equity"] = "UNKNOWN"
    elif debt_to_equity <= 0.3:
        flags["debt_to_equity"] = "VERY LOW DEBT"
    elif debt_to_equity <= 1.0:
        flags["debt_to_equity"] = "MANAGEABLE"
    elif debt_to_equity <= 2.0:
        flags["debt_to_equity"] = "HIGH"
        score -= 10
    else:
        flags["debt_to_equity"] = "VERY HIGH DEBT"
        score -= 20

    pe_ratio = ratios.get("pe_ratio")
    if pe_ratio is None:
        flags["pe_ratio"] = "UNKNOWN"
    elif pe_ratio <= 15:
        flags["pe_ratio"] = "UNDERVALUED"
    elif pe_ratio <= 25:
        flags["pe_ratio"] = "FAIR VALUE"
    elif pe_ratio <= 40:
        flags["pe_ratio"] = "PREMIUM"
        score -= 5
    else:
        flags["pe_ratio"] = "EXPENSIVE"
        score -= 10

    peg_ratio = ratios.get("peg_ratio")
    if peg_ratio is None:
        flags["peg_ratio"] = "UNKNOWN"
    elif peg_ratio <= 1.0:
        flags["peg_ratio"] = "ATTRACTIVE — growth at reasonable price"
    elif peg_ratio <= 2.0:
        flags["peg_ratio"] = "FAIR"
    else:
        flags["peg_ratio"] = "EXPENSIVE RELATIVE TO GROWTH"
        score -= 5

    eps_growth_3y = ratios.get("eps_growth_3y")
    if eps_growth_3y is None:
        flags["eps_growth_3y"] = "UNKNOWN"
    elif eps_growth_3y >= 15:
        flags["eps_growth_3y"] = "STRONG"
    elif eps_growth_3y >= 8:
        flags["eps_growth_3y"] = "MODERATE"
    elif eps_growth_3y >= 0:
        flags["eps_growth_3y"] = "WEAK"
        score -= 10
    else:
        flags["eps_growth_3y"] = "DECLINING"
        score -= 20

    quality_score = max(0, score)

    if quality_score >= 80:
        grade = "A — High Quality"
    elif quality_score >= 65:
        grade = "B — Good Quality"
    elif quality_score >= 50:
        grade = "C — Average"
    elif quality_score >= 35:
        grade = "D — Below Average"
    else:
        grade = "F — Poor Quality"

    return {
        "quality_score": quality_score,
        "quality_grade": grade,
        "flags":         flags
    }


def get_sector_context(pe_ratio: float, sector: str = "default") -> dict:
    sector_key = sector.lower().strip()
    if sector_key not in SECTOR_PE:
        sector_key = "default"
    sector_pe = SECTOR_PE[sector_key]

    if pe_ratio is None:
        return {
            "sector":      sector,
            "sector_pe":   sector_pe,
            "stock_pe":    None,
            "premium_pct": None,
            "vs_sector":   "UNKNOWN"
        }

    premium_pct = round((pe_ratio - sector_pe) / sector_pe * 100, 2)

    if premium_pct <= -20:
        vs_sector = "SIGNIFICANT DISCOUNT TO SECTOR"
    elif premium_pct <= -5:
        vs_sector = "SLIGHT DISCOUNT TO SECTOR"
    elif premium_pct <= 10:
        vs_sector = "IN LINE WITH SECTOR"
    elif premium_pct <= 25:
        vs_sector = "SLIGHT PREMIUM TO SECTOR"
    else:
        vs_sector = "SIGNIFICANT PREMIUM TO SECTOR"

    return {
        "sector":      sector,
        "sector_pe":   sector_pe,
        "stock_pe":    pe_ratio,
        "premium_pct": premium_pct,
        "vs_sector":   vs_sector
    }


def get_fundamental_analysis(
    symbol: str,
    current_price: float,
    sector: str = "default",
    db_path: str = os.getenv("WEALTHOS_DB_PATH", "./db/wealthos.duckdb")
) -> dict:
    try:
        from collectors.fundamental_collector import fetch_fundamentals
        records = fetch_fundamentals(symbol, db_path)
        if not records:
            return {"error": f"No fundamental data for {symbol}"}

        ratios = compute_ratios(records, current_price)
        if "error" in ratios:
            return ratios

        quality     = score_quality(ratios)
        sector_ctx  = get_sector_context(ratios.get("pe_ratio"), sector)

        print(
            f"[FundamentalAnalyzer] {symbol}: "
            f"PE={ratios.get('pe_ratio')} "
            f"ROE={ratios.get('roe')}% "
            f"Grade={quality['quality_grade']}"
        )

        return {
            "symbol":         symbol,
            "ratios":         ratios,
            "quality":        quality,
            "sector_context": sector_ctx
        }

    except Exception as e:
        return {"error": str(e)}


def build_fundamental_summary(analysis: dict) -> str:
    if "error" in analysis:
        return f"FUNDAMENTAL DATA UNAVAILABLE: {analysis['error']}"

    r = analysis["ratios"]
    q = analysis["quality"]
    s = analysis["sector_context"]

    def fmt(val, suffix="", prefix=""):
        return f"{prefix}{val}{suffix}" if val is not None else "N/A"

    lines = []
    lines.append(
        f"FUNDAMENTALS (FY{r['year']}) — Quality Grade: {q['quality_grade']}"
    )
    lines.append(
        f"Revenue: ₹{fmt(r['revenue'])} Cr | "
        f"EBITDA: ₹{fmt(r['ebitda'])} Cr | "
        f"PAT: ₹{fmt(r['pat'])} Cr"
    )
    lines.append(
        f"PAT Margin: {fmt(r['pat_margin'], '%')} | "
        f"EBITDA Margin: {fmt(r['ebitda_margin'], '%')} | "
        f"Revenue Growth: {fmt(r['revenue_growth_1y'], '%')}"
    )
    lines.append(
        f"EPS: ₹{fmt(r['eps'])} | "
        f"EPS Growth 3Y: {fmt(r['eps_growth_3y'], '%')} | "
        f"EPS Growth 5Y: {fmt(r['eps_growth_5y'], '%')}"
    )
    lines.append(
        f"ROE: {fmt(r['roe'], '%')} [{q['flags'].get('roe', 'N/A')}] | "
        f"ROCE: {fmt(r['roce'], '%')} [{q['flags'].get('roce', 'N/A')}]"
    )
    lines.append(
        f"P/E: {fmt(r['pe_ratio'], 'x')} | "
        f"P/B: {fmt(r['pb_ratio'], 'x')} | "
        f"EV/EBITDA: {fmt(r['ev_ebitda'], 'x')} | "
        f"PEG: {fmt(r['peg_ratio'])}"
    )
    lines.append(
        f"Sector P/E: {s['sector_pe']}x — {s['vs_sector']}"
    )
    lines.append(
        f"Debt/Equity: {fmt(r['debt_to_equity'])} [{q['flags'].get('debt_to_equity', 'N/A')}] | "
        f"CFO/PAT: {fmt(r['cfo_to_pat'])} [{q['flags'].get('cfo_to_pat', 'N/A')}]"
    )
    lines.append(
        f"FCF (CFO - |CFI| approx): ₹{fmt(r['fcf'])} Cr "
        f"[{q['flags'].get('fcf', 'N/A')}] | "
        f"FCF/Debt: {fmt(r['fcf_to_debt'])}"
    )
    lines.append(f"Quality Score: {q['quality_score']}/100")

    return "\n".join(lines)
