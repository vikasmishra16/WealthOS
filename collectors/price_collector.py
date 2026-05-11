import os
import duckdb
import json
import pandas as pd
import requests
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

STALENESS_DAYS = 1


def resolve_symbol(symbol: str, exchange: str = "NSE") -> str:
    symbol = symbol.strip().upper()

    if symbol.endswith(".NS") or symbol.endswith(".BO"):
        return symbol

    if exchange == "NSE":
        return f"{symbol}.NS"
    elif exchange == "BSE":
        return f"{symbol}.BO"
    else:
        raise ValueError(f"exchange must be 'NSE' or 'BSE', got '{exchange}'")


def _is_cache_fresh(con: duckdb.DuckDBPyConnection, symbol: str) -> bool:
    try:
        rows = con.execute(
            "SELECT last_updated FROM cache_metadata "
            "WHERE table_name = 'prices' AND symbol = ?",
            [symbol],
        ).fetchall()

        if not rows:
            return False

        last_updated: datetime = rows[0][0]
        age = datetime.utcnow() - last_updated.replace(tzinfo=None)
        return age < timedelta(days=STALENESS_DAYS)

    except Exception:
        return False


def fetch_price_history(
    symbol: str,
    exchange: str = "NSE",
    period: str = "2y",
    interval: str = "1d",
    db_path: str = os.getenv("WEALTHOS_DB_PATH", "./db/wealthos.duckdb"),
) -> pd.DataFrame:
    yf_symbol = resolve_symbol(symbol, exchange)

    con = duckdb.connect(db_path)

    if _is_cache_fresh(con, yf_symbol):
        rows = con.execute(
            "SELECT symbol, date, open, high, low, close, volume "
            "FROM prices WHERE symbol = ? ORDER BY date ASC",
            [yf_symbol],
        ).fetchall()
        con.close()

        df = pd.DataFrame(
            rows,
            columns=["symbol", "date", "open", "high", "low", "close", "volume"],
        )
        df = df.set_index("date")
        df = df[["open", "high", "low", "close", "volume"]]
        print(f"[PriceCollector] Cache hit: {yf_symbol} ({len(df)} rows)")
        return df

    try:
        print(f"[PriceCollector] Fetching from yfinance: {yf_symbol}")

        PERIOD_TO_RANGE = {
            "1d": "1d", "5d": "5d", "1mo": "1mo", "3mo": "3mo",
            "6mo": "6mo", "1y": "1y", "2y": "2y", "5y": "5y",
            "10y": "10y", "ytd": "ytd", "max": "max"
        }

        _session = requests.Session()
        _session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                          "AppleWebKit/537.36 (KHTML, like Gecko) "
                          "Chrome/120.0.0.0 Safari/537.36",
            "Accept": "application/json",
            "Referer": "https://finance.yahoo.com/"
        })

        range_val = PERIOD_TO_RANGE.get(period, "2y")
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{yf_symbol}"
        params = {"interval": interval, "range": range_val}

        response = _session.get(url, params=params, timeout=30)
        response.raise_for_status()
        data = response.json()

        if data["chart"]["error"] is not None:
            raise ValueError(
                f"Yahoo Finance error for {yf_symbol}: "
                f"{data['chart']['error']}"
            )

        result = data["chart"]["result"][0]
        timestamps = result["timestamp"]
        ohlcv = result["indicators"]["quote"][0]

        raw_df = pd.DataFrame({
            "date":   pd.to_datetime(timestamps, unit="s").normalize(),
            "open":   ohlcv["open"],
            "high":   ohlcv["high"],
            "low":    ohlcv["low"],
            "close":  ohlcv["close"],
            "volume": ohlcv["volume"]
        })
        raw_df = raw_df.set_index("date")
        raw_df = raw_df.dropna()
        raw_df["volume"] = raw_df["volume"].fillna(0).astype("int64")

        if raw_df is None or len(raw_df) == 0:
            con.close()
            raise ValueError(
                f"No price data returned for {yf_symbol}. "
                "Check symbol and exchange."
            )

        raw_df = raw_df.reset_index()

        raw_df["symbol"] = yf_symbol
        raw_df["fetched_at"] = datetime.utcnow()
        raw_df["volume"] = raw_df["volume"].fillna(0).astype("int64")

        rows = raw_df[
            ["symbol", "date", "open", "high", "low", "close", "volume", "fetched_at"]
        ].values.tolist()

        con.executemany(
            """
            INSERT OR REPLACE INTO prices
            (symbol, date, open, high, low, close, volume, fetched_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            rows,
        )

        con.execute(
            """
            INSERT OR REPLACE INTO cache_metadata
            (table_name, symbol, last_updated)
            VALUES ('prices', ?, current_timestamp)
            """,
            [yf_symbol],
        )

        con.close()

        raw_df = raw_df.set_index("date")
        raw_df = raw_df[["open", "high", "low", "close", "volume"]]

        print(f"[PriceCollector] Saved {len(raw_df)} rows for {yf_symbol}")
        return raw_df

    except Exception as e:
        try:
            con.close()
        except Exception:
            pass
        raise RuntimeError(
            f"Failed to fetch price data for {yf_symbol}: {str(e)}"
        ) from e


def get_current_price(
    symbol: str,
    exchange: str = "NSE",
    db_path: str = os.getenv("WEALTHOS_DB_PATH", "./db/wealthos.duckdb"),
) -> dict:
    try:
        yf_symbol = resolve_symbol(symbol, exchange)
        df = fetch_price_history(symbol, exchange, period="1y", db_path=db_path)

        current_price = df["close"].iloc[-1]
        prev_close = df["close"].iloc[-2]
        change = current_price - prev_close
        change_pct = (change / prev_close) * 100
        week_52_high = df["close"].max()
        week_52_low = df["close"].min()
        avg_volume_20d = df["volume"].tail(20).mean()
        last_updated = df.index[-1]

        return {
            "symbol": yf_symbol,
            "current_price": round(float(current_price), 2),
            "prev_close": round(float(prev_close), 2),
            "change": round(float(change), 2),
            "change_pct": round(float(change_pct), 2),
            "week_52_high": round(float(week_52_high), 2),
            "week_52_low": round(float(week_52_low), 2),
            "avg_volume_20d": int(avg_volume_20d),
            "last_updated": str(last_updated.date()) if hasattr(last_updated, 'hour') else str(last_updated),
        }

    except Exception as e:
        raise RuntimeError(
            f"Failed to get current price for {symbol} ({exchange}): {str(e)}"
        ) from e
