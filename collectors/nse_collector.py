import os
import duckdb
import requests
import time
from datetime import datetime, timedelta
from typing import Optional

STALENESS_DAYS = 90


def _get_nse_session() -> requests.Session:
    try:
        session = requests.Session()
        session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                          "AppleWebKit/537.36 (KHTML, like Gecko) "
                          "Chrome/120.0.0.0 Safari/537.36",
            "Accept": "*/*",
            "Accept-Language": "en-US,en;q=0.9",
            "Accept-Encoding": "gzip, deflate, br",
            "Referer": "https://www.nseindia.com/",
            "Connection": "keep-alive",
        })
        session.get("https://www.nseindia.com", timeout=10)
        time.sleep(2)
        session.get(
            "https://www.nseindia.com/market-data/live-equity-market",
            timeout=10
        )
        time.sleep(2)
        return session
    except Exception:
        fallback = requests.Session()
        fallback.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                          "AppleWebKit/537.36 (KHTML, like Gecko) "
                          "Chrome/120.0.0.0 Safari/537.36"
        })
        return fallback


def _is_cache_fresh(
    con: duckdb.DuckDBPyConnection,
    symbol: str,
    table_name: str
) -> bool:
    try:
        rows = con.execute(
            "SELECT last_updated FROM cache_metadata "
            "WHERE table_name = ? AND symbol = ?",
            [table_name, symbol]
        ).fetchall()
        if not rows:
            return False
        last_updated: datetime = rows[0][0]
        age = datetime.utcnow() - last_updated.replace(tzinfo=None)
        return age < timedelta(days=STALENESS_DAYS)
    except Exception:
        return False


def get_shareholding_pattern(
    symbol: str,
    db_path: str = os.getenv("WEALTHOS_DB_PATH", "./db/wealthos.duckdb")
) -> dict:
    symbol = symbol.strip().upper()
    if symbol.endswith(".NS") or symbol.endswith(".BO"):
        symbol = symbol[:-3]

    con = duckdb.connect(db_path)

    if _is_cache_fresh(con, symbol, "shareholding"):
        rows = con.execute(
            "SELECT symbol, quarter, promoter_pct, fii_pct, "
            "dii_pct, public_pct, pledge_pct "
            "FROM shareholding WHERE symbol = ? "
            "ORDER BY quarter DESC LIMIT 1",
            [symbol]
        ).fetchall()
        if rows:
            con.close()
            row = rows[0]
            result = {
                "symbol":       row[0],
                "quarter":      row[1],
                "promoter_pct": row[2],
                "fii_pct":      row[3],
                "dii_pct":      row[4],
                "public_pct":   row[5],
                "pledge_pct":   row[6],
                "source":       "cache"
            }
            print(f"[NSECollector] Cache hit: shareholding {symbol}")
            return result

    try:
        print(f"[NSECollector] Fetching shareholding: {symbol}")
        session = _get_nse_session()
        url = (
            f"https://www.nseindia.com/api/corporate-share-holdings-master"
            f"?index=equities&symbol={symbol}"
        )
        response = session.get(url, timeout=15)

        if response.status_code != 200:
            con.close()
            raise RuntimeError(
                f"NSE API returned status {response.status_code} "
                f"for shareholding {symbol}"
            )

        data = response.json()

        promoter_pct = None
        fii_pct      = None
        dii_pct      = None
        public_pct   = None
        pledge_pct   = None
        quarter      = None

        if isinstance(data, list) and len(data) > 0:
            for item in data:
                category = item.get("category", "").upper()
                perc = item.get("holdingPerc") or item.get("holdingPercentage")
                try:
                    perc = float(perc)
                except (TypeError, ValueError):
                    continue

                if "PROMOTER" in category and "PLEDGE" not in category:
                    promoter_pct = perc
                elif "FOREIGN" in category or "FII" in category or "FPI" in category:
                    fii_pct = perc
                elif (
                    "MUTUAL FUND" in category
                    or "DII" in category
                    or "INSURANCE" in category
                ):
                    if dii_pct is None:
                        dii_pct = perc
                    else:
                        dii_pct += perc
                elif "PUBLIC" in category or "RETAIL" in category:
                    public_pct = perc
                elif "PLEDGE" in category:
                    pledge_pct = perc

            try:
                quarter = str(
                    data[0].get("endDate")
                    or data[0].get("quarter")
                    or datetime.utcnow().strftime("%Y-Q%q")
                )
            except Exception:
                quarter = datetime.utcnow().strftime("%Y-%m")

        if all(v is None for v in [promoter_pct, fii_pct, dii_pct, public_pct]):
            con.close()
            raise ValueError(
                f"No shareholding data found for {symbol}. "
                "Verify the NSE symbol is correct."
            )

        for val, name in [
            (promoter_pct, "promoter_pct"),
            (fii_pct, "fii_pct"),
            (dii_pct, "dii_pct"),
            (public_pct, "public_pct"),
            (pledge_pct, "pledge_pct"),
        ]:
            pass

        if promoter_pct is not None:
            promoter_pct = round(promoter_pct, 2)
        if fii_pct is not None:
            fii_pct = round(fii_pct, 2)
        if dii_pct is not None:
            dii_pct = round(dii_pct, 2)
        if public_pct is not None:
            public_pct = round(public_pct, 2)
        if pledge_pct is not None:
            pledge_pct = round(pledge_pct, 2)

        con.execute("""
            INSERT OR REPLACE INTO shareholding
            (symbol, quarter, promoter_pct, fii_pct, dii_pct,
             public_pct, pledge_pct, fetched_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, [symbol, quarter, promoter_pct, fii_pct, dii_pct,
              public_pct, pledge_pct, datetime.utcnow()])

        con.execute("""
            INSERT OR REPLACE INTO cache_metadata
            (table_name, symbol, last_updated)
            VALUES ('shareholding', ?, current_timestamp)
        """, [symbol])

        con.close()

        result = {
            "symbol":       symbol,
            "quarter":      quarter,
            "promoter_pct": promoter_pct,
            "fii_pct":      fii_pct,
            "dii_pct":      dii_pct,
            "public_pct":   public_pct,
            "pledge_pct":   pledge_pct,
            "source":       "live"
        }
        print(
            f"[NSECollector] Saved shareholding for {symbol}: "
            f"Promoter={promoter_pct}%, FII={fii_pct}%, Pledge={pledge_pct}%"
        )
        return result

    except Exception as e:
        try:
            con.close()
        except Exception:
            pass
        raise RuntimeError(
            f"Failed to fetch shareholding for {symbol}: {str(e)}"
        ) from e


def get_corporate_actions(
    symbol: str,
    db_path: str = os.getenv("WEALTHOS_DB_PATH", "./db/wealthos.duckdb")
) -> list:
    symbol = symbol.strip().upper()
    if symbol.endswith(".NS") or symbol.endswith(".BO"):
        symbol = symbol[:-3]

    try:
        session = _get_nse_session()
        url = (
            f"https://www.nseindia.com/api/corporates-corporateActions"
            f"?index=equities&symbol={symbol}"
        )
        response = session.get(url, timeout=15)

        if response.status_code != 200:
            return []

        data = response.json()
        if not isinstance(data, list):
            return []

        actions = []
        for item in data[:10]:
            action = {
                "symbol":  symbol,
                "ex_date": str(item.get("exDate") or item.get("ex_date") or ""),
                "purpose": str(item.get("purpose") or item.get("subject") or ""),
                "details": str(item.get("remarks") or item.get("details") or "")
            }
            actions.append(action)

        print(
            f"[NSECollector] Corporate actions for {symbol}: "
            f"{len(actions)} records"
        )
        return actions

    except Exception as e:
        print(f"[NSECollector] Warning — corporate actions fetch failed for {symbol}: {e}")
        return []


def get_governance_flags(
    symbol: str,
    db_path: str = os.getenv("WEALTHOS_DB_PATH", "./db/wealthos.duckdb")
) -> dict:
    symbol = symbol.strip().upper()
    if symbol.endswith(".NS") or symbol.endswith(".BO"):
        symbol = symbol[:-3]

    shp = get_shareholding_pattern(symbol, db_path)

    promoter_pct = shp.get("promoter_pct")
    fii_pct      = shp.get("fii_pct")
    dii_pct      = shp.get("dii_pct")
    public_pct   = shp.get("public_pct")
    pledge_pct   = shp.get("pledge_pct")

    if promoter_pct is None:
        promoter_flag = "UNKNOWN"
    elif promoter_pct >= 50:
        promoter_flag = "SAFE"
    elif promoter_pct >= 40:
        promoter_flag = "ADEQUATE"
    elif promoter_pct >= 30:
        promoter_flag = "CAUTION"
    else:
        promoter_flag = "LOW — below 30%, reduced promoter commitment"

    if pledge_pct is None:
        pledge_flag = "UNKNOWN"
    elif pledge_pct <= 10:
        pledge_flag = "SAFE"
    elif pledge_pct <= 30:
        pledge_flag = "CAUTION"
    elif pledge_pct <= 50:
        pledge_flag = "HIGH RISK"
    else:
        pledge_flag = "CRITICAL — above 50%, forced selling risk"

    total_inst = (fii_pct or 0) + (dii_pct or 0)
    if total_inst >= 30:
        institutional_interest = "HIGH"
    elif total_inst >= 15:
        institutional_interest = "MODERATE"
    elif total_inst >= 5:
        institutional_interest = "LOW"
    else:
        institutional_interest = "VERY LOW — minimal institutional participation"

    score = 100
    if promoter_pct is not None and promoter_pct < 40:
        score -= 20
    if pledge_pct is not None and pledge_pct > 10:
        score -= 15
    if pledge_pct is not None and pledge_pct > 30:
        score -= 15
    if pledge_pct is not None and pledge_pct > 50:
        score -= 20
    if total_inst < 10:
        score -= 10
    governance_score = max(0, round(score))

    return {
        "symbol":                 symbol,
        "quarter":                shp.get("quarter"),
        "promoter_pct":           promoter_pct,
        "fii_pct":                fii_pct,
        "dii_pct":                dii_pct,
        "public_pct":             public_pct,
        "pledge_pct":             pledge_pct,
        "promoter_flag":          promoter_flag,
        "pledge_flag":            pledge_flag,
        "institutional_interest": institutional_interest,
        "governance_score":       governance_score
    }
