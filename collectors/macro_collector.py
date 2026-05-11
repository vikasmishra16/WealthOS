import os
import duckdb
import requests
import pandas as pd
from datetime import datetime, timedelta
from typing import Optional

STALENESS_DAYS = 7


def _get_db_connection(db_path: str) -> duckdb.DuckDBPyConnection:
    return duckdb.connect(db_path)


def _is_macro_cache_fresh(con: duckdb.DuckDBPyConnection) -> bool:
    try:
        rows = con.execute(
            "SELECT last_updated FROM cache_metadata "
            "WHERE table_name = 'macro_data' AND symbol = 'INDIA'"
        ).fetchall()

        if not rows:
            return False

        last_updated: datetime = rows[0][0]
        age = datetime.utcnow() - last_updated.replace(tzinfo=None)
        return age < timedelta(days=STALENESS_DAYS)

    except Exception:
        return False


def _fetch_live_indicators() -> dict:
    _session = requests.Session()
    _session.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                      "AppleWebKit/537.36 (KHTML, like Gecko) "
                      "Chrome/120.0.0.0 Safari/537.36",
        "Accept": "application/json",
        "Referer": "https://finance.yahoo.com/"
    })

    def _last_valid_close(ticker: str) -> Optional[float]:
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}"
        resp = _session.get(url, params={"interval": "1d", "range": "5d"}, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        closes = data["chart"]["result"][0]["indicators"]["quote"][0]["close"]
        values = [v for v in closes if v is not None]
        return round(values[-1], 2) if values else None

    try:
        vix = _last_valid_close("^INDIAVIX")
    except Exception:
        vix = None

    try:
        usd_inr = _last_valid_close("USDINR=X")
    except Exception:
        usd_inr = None

    try:
        brent_crude = _last_valid_close("BZ=F")
    except Exception:
        brent_crude = None

    try:
        ten_yr_gsec = _last_valid_close("^IN10Y")
    except Exception:
        ten_yr_gsec = None

    try:
        resp = _session.get("https://api.rbi.org.in/api/GetRepoRate", timeout=10)
        if resp.status_code == 200 and "repoRate" in resp.json():
            repo_rate = float(resp.json()["repoRate"])
        else:
            raise ValueError("repoRate key not found")
    except Exception:
        repo_rate = 6.5
        print("[MacroCollector] RBI API unavailable, using fallback repo rate: 6.5")

    try:
        url = "https://query1.finance.yahoo.com/v8/finance/chart/%5ENSEI"
        resp = _session.get(url, params={"interval": "1d", "range": "1mo"}, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        closes = data["chart"]["result"][0]["indicators"]["quote"][0]["close"]
        values = [v for v in closes if v is not None]
        first, last = values[0], values[-1]
        fii_net_flow = round(((last - first) / first) * 100, 2)
    except Exception:
        fii_net_flow = None

    cpi = None
    iip = None

    return {
        "date":         datetime.utcnow().date().isoformat(),
        "vix":          vix,
        "repo_rate":    repo_rate,
        "cpi":          cpi,
        "iip":          iip,
        "ten_yr_gsec":  ten_yr_gsec,
        "fii_net_flow": fii_net_flow,
        "dii_net_flow": None,
        "usd_inr":      usd_inr,
        "brent_crude":  brent_crude
    }


def get_macro_snapshot(
    db_path: str = os.getenv("WEALTHOS_DB_PATH", "./db/wealthos.duckdb")
) -> dict:
    con = _get_db_connection(db_path)

    if _is_macro_cache_fresh(con):
        rows = con.execute(
            "SELECT date, vix, repo_rate, cpi, iip, ten_yr_gsec, "
            "fii_net_flow, dii_net_flow, usd_inr, brent_crude "
            "FROM macro_data ORDER BY date DESC LIMIT 1"
        ).fetchall()

        if rows:
            con.close()
            row = rows[0]
            result = {
                "date":         str(row[0]),
                "vix":          row[1],
                "repo_rate":    row[2],
                "cpi":          row[3],
                "iip":          row[4],
                "ten_yr_gsec":  row[5],
                "fii_net_flow": row[6],
                "dii_net_flow": row[7],
                "usd_inr":      row[8],
                "brent_crude":  row[9]
            }
            print(f"[MacroCollector] Cache hit: macro data from {result['date']}")
            return result

    try:
        print("[MacroCollector] Fetching live macro indicators...")
        indicators = _fetch_live_indicators()

        con.execute("""
            INSERT OR REPLACE INTO macro_data
            (date, vix, repo_rate, cpi, iip, ten_yr_gsec,
             fii_net_flow, dii_net_flow, usd_inr, brent_crude,
             fetched_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, [
            indicators["date"],
            indicators["vix"],
            indicators["repo_rate"],
            indicators["cpi"],
            indicators["iip"],
            indicators["ten_yr_gsec"],
            indicators["fii_net_flow"],
            indicators["dii_net_flow"],
            indicators["usd_inr"],
            indicators["brent_crude"],
            datetime.utcnow()
        ])

        con.execute("""
            INSERT OR REPLACE INTO cache_metadata
            (table_name, symbol, last_updated)
            VALUES ('macro_data', 'INDIA', current_timestamp)
        """)

        con.close()
        print(f"[MacroCollector] Saved macro snapshot for {indicators['date']}")
        return indicators

    except Exception as e:
        try:
            con.close()
        except Exception:
            pass
        raise RuntimeError(f"Failed to fetch macro indicators: {str(e)}") from e


def get_market_context() -> str:
    snapshot = get_macro_snapshot()

    vix = snapshot.get("vix")
    if vix is None:
        vix_val = "N/A"
        vix_signal = ""
    else:
        vix_val = vix
        if vix < 14:
            vix_signal = "(LOW — calm market)"
        elif vix < 20:
            vix_signal = "(NORMAL — moderate volatility)"
        elif vix < 25:
            vix_signal = "(ELEVATED — caution advised)"
        else:
            vix_signal = "(HIGH — risk-off environment)"

    cpi = snapshot.get("cpi")
    cpi_val = "N/A (data pending)" if cpi is None else f"{cpi}%"

    usd_inr = snapshot.get("usd_inr", "N/A")
    brent_crude = snapshot.get("brent_crude", "N/A")
    ten_yr_gsec = snapshot.get("ten_yr_gsec", "N/A")
    fii_net_flow = snapshot.get("fii_net_flow", "N/A")

    context = f"""CURRENT INDIA MACRO ENVIRONMENT
================================
Date:              {snapshot['date']}
India VIX:         {vix_val} — {vix_signal}
RBI Repo Rate:     {snapshot['repo_rate']}%
USD/INR:           {usd_inr}
Brent Crude:       ${brent_crude} per barrel
10-yr G-Sec Yield: {ten_yr_gsec}%
Nifty 30d Change:  {fii_net_flow}% (directional proxy)
CPI Inflation:     {cpi_val}"""

    return context.strip()


def get_risk_free_rate(
    db_path: str = os.getenv("WEALTHOS_DB_PATH", "./db/wealthos.duckdb")
) -> float:
    snapshot = get_macro_snapshot(db_path=db_path)
    gsec = snapshot.get("ten_yr_gsec")
    if gsec is not None and gsec > 0:
        return round(gsec / 100, 4)
    return 0.071
