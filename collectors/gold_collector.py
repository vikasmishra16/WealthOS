import os
import duckdb
import requests
from datetime import datetime, timedelta
from typing import Optional

STALENESS_DAYS  = 1
GOLDBEES_SYMBOL = "GOLDBEES.NS"
USDINR_SYMBOL   = "USDINDR=X"
GOLD_USD_SYMBOL = "GC=F"


def _is_cache_fresh(con: duckdb.DuckDBPyConnection) -> bool:
    try:
        rows = con.execute(
            "SELECT last_updated FROM cache_metadata "
            "WHERE table_name = 'gold_prices' AND symbol = 'GOLD'"
        ).fetchall()
        if not rows:
            return False
        last_updated: datetime = rows[0][0]
        age = datetime.utcnow() - last_updated.replace(tzinfo=None)
        return age < timedelta(days=STALENESS_DAYS)
    except Exception:
        return False


def _fetch_yahoo_series(symbol: str, period_days: int = 365) -> list:
    try:
        import time as time_module
        end_ts   = int(datetime.utcnow().timestamp())
        start_ts = int((datetime.utcnow() - timedelta(days=period_days)).timestamp())

        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"
        params = {
            "period1":  start_ts,
            "period2":  end_ts,
            "interval": "1d"
        }
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                          "AppleWebKit/537.36 (KHTML, like Gecko) "
                          "Chrome/120.0.0.0 Safari/537.36",
            "Referer": "https://finance.yahoo.com"
        }

        response = requests.get(url, params=params, headers=headers, timeout=15)
        if response.status_code != 200:
            return []

        data = response.json()
        result_data = data.get("chart", {}).get("result", [])
        if not result_data:
            return []

        chart      = result_data[0]
        timestamps = chart.get("timestamp", [])
        closes     = (chart.get("indicators", {})
                           .get("quote", [{}])[0]
                           .get("close", []))

        pairs = []
        for ts, close in zip(timestamps, closes):
            if close is None:
                continue
            date_obj = datetime.utcfromtimestamp(ts).date()
            pairs.append((date_obj, round(float(close), 4)))

        return sorted(pairs, key=lambda x: x[0])

    except Exception as e:
        print(f"[GoldCollector] Warning — _fetch_yahoo_series({symbol}) failed: {e}")
        return []


def fetch_gold_prices(
    db_path: str = os.getenv("WEALTHOS_DB_PATH", "./db/wealthos.duckdb")
) -> list:
    con = duckdb.connect(db_path)

    if _is_cache_fresh(con):
        rows = con.execute(
            "SELECT date, goldbees_close, mcx_spot_inr, "
            "usd_inr, gold_inr_per_gram "
            "FROM gold_prices ORDER BY date DESC"
        ).fetchall()
        if rows:
            con.close()
            result = [
                {
                    "date":             str(row[0]),
                    "goldbees_close":   row[1],
                    "mcx_spot_inr":     row[2],
                    "usd_inr":          row[3],
                    "gold_inr_per_gram": row[4]
                }
                for row in rows
            ]
            print(f"[GoldCollector] Cache hit: {len(result)} records")
            return result

    try:
        print("[GoldCollector] Fetching gold price data...")
        goldbees_series = _fetch_yahoo_series(GOLDBEES_SYMBOL, 365)
        usdinr_series   = _fetch_yahoo_series(USDINR_SYMBOL, 365)
        gold_usd_series = _fetch_yahoo_series(GOLD_USD_SYMBOL, 365)

        goldbees_map = {date: price for date, price in goldbees_series}
        usdinr_map   = {date: price for date, price in usdinr_series}
        gold_usd_map = {date: price for date, price in gold_usd_series}

        all_dates = sorted(goldbees_map.keys(), reverse=True)
        records = []
        for date in all_dates:
            goldbees_close = goldbees_map.get(date)
            usd_inr        = usdinr_map.get(date)
            gold_usd       = gold_usd_map.get(date)

            if usd_inr and gold_usd:
                gold_inr_per_gram = round((gold_usd / 31.1035) * usd_inr, 2)
            else:
                gold_inr_per_gram = None

            records.append({
                "date":              str(date),
                "goldbees_close":    goldbees_close,
                "mcx_spot_inr":      None,
                "usd_inr":           usd_inr,
                "gold_inr_per_gram": gold_inr_per_gram
            })

        rows_to_insert = [
            [r["date"], r["goldbees_close"], r["mcx_spot_inr"],
             r["usd_inr"], r["gold_inr_per_gram"], datetime.utcnow()]
            for r in records
        ]

        if rows_to_insert:
            con.executemany(
                "INSERT OR REPLACE INTO gold_prices "
                "(date, goldbees_close, mcx_spot_inr, usd_inr, "
                "gold_inr_per_gram, fetched_at) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                rows_to_insert
            )

        con.execute(
            "INSERT OR REPLACE INTO cache_metadata "
            "(table_name, symbol, last_updated) "
            "VALUES ('gold_prices', 'GOLD', current_timestamp)"
        )

        con.close()
        print(f"[GoldCollector] Saved {len(records)} gold price records")
        return records

    except Exception as e:
        try:
            con.close()
        except Exception:
            pass
        raise RuntimeError(
            f"Failed to fetch gold prices: {str(e)}"
        ) from e


def get_gold_summary(
    db_path: str = os.getenv("WEALTHOS_DB_PATH", "./db/wealthos.duckdb")
) -> dict:
    empty = {
        "as_of_date":        None,
        "goldbees_close":    None,
        "gold_inr_per_gram": None,
        "usd_inr":           None,
        "returns_1m":        None,
        "returns_3m":        None,
        "returns_1y":        None,
        "52w_high_goldbees": None,
        "52w_low_goldbees":  None,
        "total_records":     0
    }

    records = fetch_gold_prices(db_path)

    if not records:
        return empty

    def _ret(curr, past):
        if curr and past and past != 0:
            return round((curr - past) / past * 100, 2)
        return None

    current_goldbees = records[0]["goldbees_close"]
    current_inr_gram = records[0]["gold_inr_per_gram"]

    goldbees_1m_ago  = records[21]["goldbees_close"]  if len(records) > 21  else None
    goldbees_3m_ago  = records[63]["goldbees_close"]  if len(records) > 63  else None
    goldbees_1y_ago  = records[252]["goldbees_close"] if len(records) > 252 else None

    returns_1m = _ret(current_goldbees, goldbees_1m_ago)
    returns_3m = _ret(current_goldbees, goldbees_3m_ago)
    returns_1y = _ret(current_goldbees, goldbees_1y_ago)

    valid_closes = [r["goldbees_close"] for r in records[:252] if r["goldbees_close"]]
    week52_high = max(valid_closes) if valid_closes else None
    week52_low  = min(valid_closes) if valid_closes else None

    return {
        "as_of_date":        records[0]["date"],
        "goldbees_close":    current_goldbees,
        "gold_inr_per_gram": current_inr_gram,
        "usd_inr":           records[0]["usd_inr"],
        "returns_1m":        returns_1m,
        "returns_3m":        returns_3m,
        "returns_1y":        returns_1y,
        "52w_high_goldbees": week52_high,
        "52w_low_goldbees":  week52_low,
        "total_records":     len(records)
    }
