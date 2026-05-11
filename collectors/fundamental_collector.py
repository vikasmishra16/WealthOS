import os
import duckdb
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
from typing import Optional

STALENESS_DAYS = 90


def _get_screener_url(symbol: str) -> str:
    symbol = symbol.strip().upper()
    if symbol.endswith(".NS") or symbol.endswith(".BO"):
        symbol = symbol[:-3]
    return f"https://www.screener.in/company/{symbol}/consolidated/"


def _is_cache_fresh(con: duckdb.DuckDBPyConnection, symbol: str) -> bool:
    try:
        rows = con.execute(
            "SELECT last_updated FROM cache_metadata "
            "WHERE table_name = 'fundamentals' AND symbol = ?",
            [symbol]
        ).fetchall()
        if not rows:
            return False
        last_updated: datetime = rows[0][0]
        age = datetime.utcnow() - last_updated.replace(tzinfo=None)
        return age < timedelta(days=STALENESS_DAYS)
    except Exception:
        return False


def _parse_screener_page(html: str, symbol: str) -> list:
    def _parse_val(val_str) -> Optional[float]:
        if val_str is None:
            return None
        cleaned = str(val_str).strip().replace(",", "")
        if not cleaned or cleaned in ("-", "--"):
            return None
        try:
            return float(cleaned)
        except Exception:
            return None

    def _safe_get(data: dict, key: str, idx: int):
        vals = data.get(key, [])
        return vals[idx] if idx < len(vals) else None

    def _extract_table(soup, section_id: str) -> dict:
        data = {}
        try:
            section = soup.find("section", {"id": section_id})
            if not section:
                return data
            table = section.find(
                "table",
                class_=lambda c: c and "data-table" in c
            )
            if not table:
                return data
            for row in table.find("tbody").find_all("tr"):
                cols = row.find_all("td")
                if not cols:
                    continue
                label = cols[0].get_text(strip=True)
                values = [c.get_text(strip=True) for c in cols[1:]]
                if label:
                    data[label] = values
        except Exception:
            pass
        return data

    try:
        soup = BeautifulSoup(html, "lxml")

        years = []
        try:
            pl_section = soup.find("section", {"id": "profit-loss"})
            if pl_section:
                pl_table = pl_section.find(
                    "table",
                    class_=lambda c: c and "data-table" in c
                )
                if pl_table:
                    thead = pl_table.find("thead")
                    if thead:
                        ths = thead.find_all("th")
                        years = [
                            th.get_text(strip=True) for th in ths[1:]
                            if th.get_text(strip=True)
                        ]
        except Exception:
            pass

        if not years:
            print(f"[FundamentalCollector] Warning — no year headers found for {symbol}")
            return []

        pl_data = _extract_table(soup, "profit-loss")
        bs_data = _extract_table(soup, "balance-sheet")
        cf_data = _extract_table(soup, "cash-flow")

        records = []
        for i, year in enumerate(years):
            try:
                year_int = int(year.split()[-1])
            except Exception:
                continue

            revenue  = _parse_val(_safe_get(pl_data, "Sales+", i))
            expenses = _parse_val(_safe_get(pl_data, "Expenses+", i))
            pat      = _parse_val(_safe_get(pl_data, "Net Profit+", i))
            eps      = _parse_val(_safe_get(pl_data, "EPS in Rs", i))

            if revenue is not None and expenses is not None:
                ebitda = round(revenue - expenses, 2)
            else:
                ebitda = None

            total_assets        = _parse_val(_safe_get(bs_data, "Total Assets", i))
            total_debt          = _parse_val(_safe_get(bs_data, "Borrowings+", i))
            shareholders_equity = _parse_val(_safe_get(bs_data, "Equity Capital", i))
            cash                = _parse_val(_safe_get(bs_data, "Cash Equivalents", i))

            cfo = _parse_val(_safe_get(cf_data, "Cash from Operating Activity+", i))
            cfi = _parse_val(_safe_get(cf_data, "Cash from Investing Activity+", i))
            cff = _parse_val(_safe_get(cf_data, "Cash from Financing Activity+", i))

            if revenue is None and pat is None and total_assets is None:
                continue

            records.append({
                "symbol":              symbol,
                "year":                year_int,
                "revenue":             revenue,
                "ebitda":              ebitda,
                "pat":                 pat,
                "eps":                 eps,
                "dps":                 None,
                "total_assets":        total_assets,
                "total_debt":          total_debt,
                "shareholders_equity": shareholders_equity,
                "cash":                cash,
                "cfo":                 cfo,
                "cfi":                 cfi,
                "cff":                 cff,
                "roe":                 None,
                "roce":                None,
                "pe_ratio":            None,
                "pb_ratio":            None,
                "debt_to_equity":      None
            })

        records.sort(key=lambda r: r["year"], reverse=True)
        return records

    except Exception as e:
        print(f"[FundamentalCollector] Warning — parse failed for {symbol}: {e}")
        return []


def fetch_fundamentals(
    symbol: str,
    db_path: str = os.getenv("WEALTHOS_DB_PATH", "./db/wealthos.duckdb")
) -> list:
    symbol = symbol.strip().upper()
    if symbol.endswith(".NS") or symbol.endswith(".BO"):
        symbol = symbol[:-3]

    con = duckdb.connect(db_path)

    if _is_cache_fresh(con, symbol):
        col_names = [
            "symbol", "year", "revenue", "ebitda", "pat", "eps", "dps",
            "total_assets", "total_debt", "shareholders_equity", "cash",
            "cfo", "cfi", "cff", "roe", "roce", "pe_ratio", "pb_ratio",
            "debt_to_equity"
        ]
        rows = con.execute(
            "SELECT symbol, year, revenue, ebitda, pat, eps, dps, "
            "total_assets, total_debt, shareholders_equity, cash, "
            "cfo, cfi, cff, roe, roce, pe_ratio, pb_ratio, debt_to_equity "
            "FROM fundamentals WHERE symbol = ? ORDER BY year DESC",
            [symbol]
        ).fetchall()
        if rows:
            con.close()
            result = [dict(zip(col_names, row)) for row in rows]
            print(f"[FundamentalCollector] Cache hit: {symbol} ({len(result)} years)")
            return result

    try:
        url = _get_screener_url(symbol)
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                          "AppleWebKit/537.36 (KHTML, like Gecko) "
                          "Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml",
            "Accept-Language": "en-US,en;q=0.9",
            "Referer": "https://www.screener.in/"
        }
        response = requests.get(url, headers=headers, timeout=20)

        if response.status_code == 404:
            url = f"https://www.screener.in/company/{symbol}/"
            response = requests.get(url, headers=headers, timeout=20)

        if response.status_code != 200:
            con.close()
            raise RuntimeError(
                f"Screener.in returned {response.status_code} for {symbol}"
            )

        records = _parse_screener_page(response.text, symbol)

        if not records:
            con.close()
            raise ValueError(
                f"No fundamental data parsed for {symbol}. "
                "Check if symbol is correct on Screener.in"
            )

        fetched_at = datetime.utcnow()
        rows_to_insert = [
            [
                r["symbol"], r["year"], r["revenue"], r["ebitda"], r["pat"],
                r["eps"], r["dps"], r["total_assets"], r["total_debt"],
                r["shareholders_equity"], r["cash"], r["cfo"], r["cfi"],
                r["cff"], r["roe"], r["roce"], r["pe_ratio"], r["pb_ratio"],
                r["debt_to_equity"], fetched_at
            ]
            for r in records
        ]

        con.executemany(
            """
            INSERT OR REPLACE INTO fundamentals
            (symbol, year, revenue, ebitda, pat, eps, dps,
             total_assets, total_debt, shareholders_equity, cash,
             cfo, cfi, cff, roe, roce, pe_ratio, pb_ratio,
             debt_to_equity, fetched_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            rows_to_insert
        )

        con.execute(
            """
            INSERT OR REPLACE INTO cache_metadata
            (table_name, symbol, last_updated)
            VALUES ('fundamentals', ?, current_timestamp)
            """,
            [symbol]
        )

        con.close()
        print(f"[FundamentalCollector] Saved {len(records)} years for {symbol}")
        return records

    except Exception as e:
        try:
            con.close()
        except Exception:
            pass
        raise RuntimeError(
            f"Failed to fetch fundamentals for {symbol}: {str(e)}"
        ) from e


def get_fundamental_summary(
    symbol: str,
    db_path: str = os.getenv("WEALTHOS_DB_PATH", "./db/wealthos.duckdb")
) -> dict:
    symbol = symbol.strip().upper()
    if symbol.endswith(".NS") or symbol.endswith(".BO"):
        symbol = symbol[:-3]

    empty = {
        "symbol":             symbol,
        "latest_year":        None,
        "revenue":            None,
        "ebitda":             None,
        "pat":                None,
        "eps":                None,
        "total_assets":       None,
        "total_debt":         None,
        "shareholders_equity": None,
        "cash":               None,
        "cfo":                None,
        "revenue_growth_pct": None,
        "pat_margin_pct":     None,
        "debt_to_equity":     None,
        "cfo_to_pat":         None,
        "years_available":    0,
        "all_years":          []
    }

    records = fetch_fundamentals(symbol, db_path)

    if not records:
        return empty

    latest = records[0]

    revenue_growth_pct = None
    if len(records) >= 2 and records[0]["revenue"] and records[1]["revenue"]:
        revenue_growth_pct = round(
            (records[0]["revenue"] - records[1]["revenue"])
            / records[1]["revenue"] * 100, 2
        )

    pat_margin_pct = None
    if latest["revenue"] and latest["pat"]:
        pat_margin_pct = round(latest["pat"] / latest["revenue"] * 100, 2)

    debt_to_equity = None
    if (latest["total_debt"] and latest["shareholders_equity"]
            and latest["shareholders_equity"] != 0):
        debt_to_equity = round(
            latest["total_debt"] / latest["shareholders_equity"], 2
        )

    cfo_to_pat = None
    if latest["cfo"] and latest["pat"] and latest["pat"] != 0:
        cfo_to_pat = round(latest["cfo"] / latest["pat"], 2)

    return {
        "symbol":              symbol,
        "latest_year":         latest["year"],
        "revenue":             latest["revenue"],
        "ebitda":              latest["ebitda"],
        "pat":                 latest["pat"],
        "eps":                 latest["eps"],
        "total_assets":        latest["total_assets"],
        "total_debt":          latest["total_debt"],
        "shareholders_equity": latest["shareholders_equity"],
        "cash":                latest["cash"],
        "cfo":                 latest["cfo"],
        "revenue_growth_pct":  revenue_growth_pct,
        "pat_margin_pct":      pat_margin_pct,
        "debt_to_equity":      debt_to_equity,
        "cfo_to_pat":          cfo_to_pat,
        "years_available":     len(records),
        "all_years":           [r["year"] for r in records]
    }
