import os
import duckdb
import requests
from datetime import datetime, timedelta
from typing import Optional

STALENESS_DAYS_NAV     = 1
STALENESS_DAYS_DETAILS = 90
MFAPI_BASE             = "https://api.mfapi.in/mf"


def search_scheme(query: str) -> list:
    try:
        url = f"{MFAPI_BASE}"
        response = requests.get(url, timeout=15)
        if response.status_code != 200:
            return []
        data = response.json()
        query_lower = query.strip().lower()
        matches = []
        for item in data:
            name = str(item.get("schemeName", "")).lower()
            if query_lower in name:
                matches.append({
                    "scheme_code": int(item["schemeCode"]),
                    "scheme_name": str(item["schemeName"])
                })
        return matches[:10]
    except Exception as e:
        print(f"[MFCollector] Warning — search_scheme failed: {e}")
        return []


def _is_cache_fresh(
    con: duckdb.DuckDBPyConnection,
    scheme_code: int,
    table_name: str
) -> bool:
    try:
        rows = con.execute(
            "SELECT last_updated FROM cache_metadata "
            "WHERE table_name = ? AND symbol = ?",
            [table_name, str(scheme_code)]
        ).fetchall()
        if not rows:
            return False
        last_updated: datetime = rows[0][0]
        age = datetime.utcnow() - last_updated.replace(tzinfo=None)
        staleness = STALENESS_DAYS_NAV if table_name == "mf_nav" else STALENESS_DAYS_DETAILS
        return age < timedelta(days=staleness)
    except Exception:
        return False


def fetch_nav_history(
    scheme_code: int,
    db_path: str = os.getenv("WEALTHOS_DB_PATH", "./db/wealthos.duckdb")
) -> list:
    con = duckdb.connect(db_path)

    if _is_cache_fresh(con, scheme_code, "mf_nav"):
        rows = con.execute(
            "SELECT scheme_code, date, nav FROM mf_nav "
            "WHERE scheme_code = ? ORDER BY date DESC",
            [scheme_code]
        ).fetchall()
        if rows:
            con.close()
            result = [
                {"scheme_code": row[0], "date": str(row[1]), "nav": row[2]}
                for row in rows
            ]
            print(f"[MFCollector] Cache hit: NAV {scheme_code} ({len(result)} records)")
            return result

    try:
        url = f"{MFAPI_BASE}/{scheme_code}"
        response = requests.get(url, timeout=15)
        if response.status_code != 200:
            con.close()
            raise RuntimeError(
                f"mfapi returned {response.status_code} for {scheme_code}"
            )
        data = response.json()
        nav_data = data.get("data", [])

        records = []
        rows_to_insert = []
        fetched_at = datetime.utcnow()

        for item in nav_data:
            try:
                date_obj = datetime.strptime(item["date"], "%d-%m-%Y").date()
                nav_val = float(item["nav"])
                records.append({
                    "scheme_code": scheme_code,
                    "date":        str(date_obj),
                    "nav":         nav_val
                })
                rows_to_insert.append([scheme_code, date_obj, nav_val, fetched_at])
            except Exception:
                continue

        if rows_to_insert:
            con.executemany(
                "INSERT OR REPLACE INTO mf_nav "
                "(scheme_code, date, nav, fetched_at) "
                "VALUES (?, ?, ?, ?)",
                rows_to_insert
            )

        con.execute(
            "INSERT OR REPLACE INTO cache_metadata "
            "(table_name, symbol, last_updated) "
            "VALUES ('mf_nav', ?, current_timestamp)",
            [str(scheme_code)]
        )

        con.close()
        print(f"[MFCollector] Saved {len(records)} NAV records for {scheme_code}")
        return records

    except Exception as e:
        try:
            con.close()
        except Exception:
            pass
        raise RuntimeError(
            f"Failed to fetch NAV history for {scheme_code}: {str(e)}"
        ) from e


def fetch_scheme_details(
    scheme_code: int,
    db_path: str = os.getenv("WEALTHOS_DB_PATH", "./db/wealthos.duckdb")
) -> dict:
    con = duckdb.connect(db_path)

    if _is_cache_fresh(con, scheme_code, "mf_details"):
        rows = con.execute(
            "SELECT scheme_code, scheme_name, fund_house, category, "
            "benchmark, expense_ratio, aum "
            "FROM mf_details WHERE scheme_code = ?",
            [scheme_code]
        ).fetchall()
        if rows:
            con.close()
            row = rows[0]
            print(f"[MFCollector] Cache hit: details {scheme_code}")
            return {
                "scheme_code":  row[0],
                "scheme_name":  row[1],
                "fund_house":   row[2],
                "category":     row[3],
                "benchmark":    row[4],
                "expense_ratio": row[5],
                "aum":          row[6]
            }

    try:
        url = f"{MFAPI_BASE}/{scheme_code}"
        response = requests.get(url, timeout=15)
        if response.status_code != 200:
            con.close()
            raise RuntimeError(
                f"mfapi returned {response.status_code} for {scheme_code}"
            )
        data = response.json()
        meta = data.get("meta", {})

        scheme_name     = str(meta.get("scheme_name", ""))
        fund_house      = str(meta.get("fund_house", ""))
        scheme_type     = str(meta.get("scheme_type", ""))
        scheme_category = str(meta.get("scheme_category", ""))
        expense_ratio   = None
        aum             = None

        con.execute(
            "INSERT OR REPLACE INTO mf_details "
            "(scheme_code, scheme_name, fund_house, category, "
            "benchmark, expense_ratio, aum, fetched_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            [scheme_code, scheme_name, fund_house,
             scheme_category, scheme_type, expense_ratio,
             aum, datetime.utcnow()]
        )

        con.execute(
            "INSERT OR REPLACE INTO cache_metadata "
            "(table_name, symbol, last_updated) "
            "VALUES ('mf_details', ?, current_timestamp)",
            [str(scheme_code)]
        )

        con.close()
        print(f"[MFCollector] Saved details for {scheme_code}: {scheme_name}")
        return {
            "scheme_code":  scheme_code,
            "scheme_name":  scheme_name,
            "fund_house":   fund_house,
            "category":     scheme_category,
            "benchmark":    scheme_type,
            "expense_ratio": expense_ratio,
            "aum":          aum
        }

    except Exception as e:
        try:
            con.close()
        except Exception:
            pass
        raise RuntimeError(
            f"Failed to fetch scheme details for {scheme_code}: {str(e)}"
        ) from e


def get_mf_summary(
    scheme_code: int,
    db_path: str = os.getenv("WEALTHOS_DB_PATH", "./db/wealthos.duckdb")
) -> dict:
    details = fetch_scheme_details(scheme_code, db_path)
    records = fetch_nav_history(scheme_code, db_path)

    def _ret(current, past):
        if current is not None and past is not None and past != 0:
            return round((current - past) / past * 100, 2)
        return None

    if not records:
        return {
            "scheme_code":       scheme_code,
            "scheme_name":       details.get("scheme_name"),
            "fund_house":        details.get("fund_house"),
            "category":          details.get("category"),
            "current_nav":       None,
            "returns_1w":        None,
            "returns_1m":        None,
            "returns_3m":        None,
            "returns_1y":        None,
            "returns_3y":        None,
            "52w_high":          None,
            "52w_low":           None,
            "total_nav_records": 0,
            "as_of_date":        None
        }

    current_nav = records[0]["nav"]
    nav_1w_ago  = records[5]["nav"]   if len(records) > 5   else None
    nav_1m_ago  = records[21]["nav"]  if len(records) > 21  else None
    nav_3m_ago  = records[63]["nav"]  if len(records) > 63  else None
    nav_1y_ago  = records[252]["nav"] if len(records) > 252 else None
    nav_3y_ago  = records[756]["nav"] if len(records) > 756 else None

    returns_1w = _ret(current_nav, nav_1w_ago)
    returns_1m = _ret(current_nav, nav_1m_ago)
    returns_3m = _ret(current_nav, nav_3m_ago)
    returns_1y = _ret(current_nav, nav_1y_ago)
    returns_3y = _ret(current_nav, nav_3y_ago)

    week52_high = max(r["nav"] for r in records[:252]) if len(records) >= 252 else None
    week52_low  = min(r["nav"] for r in records[:252]) if len(records) >= 252 else None

    return {
        "scheme_code":       scheme_code,
        "scheme_name":       details.get("scheme_name"),
        "fund_house":        details.get("fund_house"),
        "category":          details.get("category"),
        "current_nav":       current_nav,
        "returns_1w":        returns_1w,
        "returns_1m":        returns_1m,
        "returns_3m":        returns_3m,
        "returns_1y":        returns_1y,
        "returns_3y":        returns_3y,
        "52w_high":          week52_high,
        "52w_low":           week52_low,
        "total_nav_records": len(records),
        "as_of_date":        records[0]["date"]
    }
