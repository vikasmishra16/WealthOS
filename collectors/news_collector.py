import os
import duckdb
import hashlib
from datetime import datetime, timedelta
from typing import Optional

STALENESS_HOURS = 12
MAX_RESULTS = 10

POSITIVE_KEYWORDS = [
    "surge", "jump", "rally", "gain", "profit", "growth", "record",
    "beat", "strong", "upgrade", "buy", "outperform", "bullish",
    "expansion", "acquisition", "dividend", "revenue", "rise",
    "high", "boost"
]

NEGATIVE_KEYWORDS = [
    "fall", "drop", "crash", "loss", "decline", "weak", "downgrade",
    "sell", "underperform", "bearish", "default", "debt", "fraud",
    "penalty", "fine", "lawsuit", "investigation", "cut", "miss",
    "low"
]


def _score_sentiment(headline: str) -> float:
    text = headline.lower()
    score = 0.0
    for kw in POSITIVE_KEYWORDS:
        if kw in text:
            score += 0.1
    for kw in NEGATIVE_KEYWORDS:
        if kw in text:
            score -= 0.1
    score = max(-1.0, min(1.0, score))
    return round(score, 2)


def _is_cache_fresh(con: duckdb.DuckDBPyConnection, symbol: str) -> bool:
    try:
        rows = con.execute(
            "SELECT last_updated FROM cache_metadata "
            "WHERE table_name = 'news_cache' AND symbol = ?",
            [symbol]
        ).fetchall()
        if not rows:
            return False
        last_updated: datetime = rows[0][0]
        age = datetime.utcnow() - last_updated.replace(tzinfo=None)
        return age < timedelta(hours=STALENESS_HOURS)
    except Exception:
        return False


def fetch_news(
    symbol: str,
    company_name: str = "",
    max_results: int = MAX_RESULTS,
    db_path: str = os.getenv("WEALTHOS_DB_PATH", "./db/wealthos.duckdb")
) -> list:
    symbol = symbol.strip().upper()
    if symbol.endswith(".NS") or symbol.endswith(".BO"):
        symbol = symbol[:-3]

    con = duckdb.connect(db_path)

    if _is_cache_fresh(con, symbol):
        rows = con.execute(
            "SELECT id, symbol, headline, source, url, published_at, sentiment_score "
            "FROM news_cache WHERE symbol = ? "
            "ORDER BY published_at DESC",
            [symbol]
        ).fetchall()
        if rows:
            con.close()
            cached = []
            for row in rows:
                cached.append({
                    "id":              row[0],
                    "symbol":          row[1],
                    "headline":        row[2],
                    "source":          row[3],
                    "url":             row[4],
                    "published_at":    str(row[5]),
                    "sentiment_score": row[6]
                })
            print(f"[NewsCollector] Cache hit: {symbol} ({len(cached)} articles)")
            return cached

    try:
        if company_name and company_name.strip():
            query = f"{company_name} stock NSE India"
        else:
            query = f"{symbol} NSE India stock news"

        try:
            from duckduckgo_search import DDGS
            raw_results = DDGS().news(
                keywords=query,
                region="in-en",
                safesearch="off",
                timelimit="w",
                max_results=max_results
            )
            results = list(raw_results) if raw_results else []
        except Exception as e:
            print(f"[NewsCollector] Warning — DuckDuckGo fetch failed for {symbol}: {e}")
            con.close()
            return []

        articles = []
        rows_to_insert = []
        fetched_at = datetime.utcnow()

        for item in results:
            title      = item.get("title", "")
            url        = item.get("url", "")
            source     = item.get("source", "")
            date_str   = item.get("date", "")
            md5_hex    = hashlib.md5(url.encode()).hexdigest()[:16]
            sentiment  = _score_sentiment(title)

            article = {
                "id":              md5_hex,
                "symbol":          symbol,
                "headline":        str(title),
                "source":          str(source),
                "url":             str(url),
                "published_at":    str(date_str),
                "sentiment_score": sentiment
            }
            articles.append(article)

            rows_to_insert.append([
                md5_hex,
                symbol,
                str(title),
                str(source),
                str(url),
                str(date_str),
                sentiment,
                fetched_at
            ])

        if rows_to_insert:
            con.executemany(
                """
                INSERT OR REPLACE INTO news_cache
                (id, symbol, headline, source, url, published_at, sentiment_score, fetched_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                rows_to_insert
            )

        con.execute(
            """
            INSERT OR REPLACE INTO cache_metadata
            (table_name, symbol, last_updated)
            VALUES ('news_cache', ?, current_timestamp)
            """,
            [symbol]
        )

        con.close()
        print(f"[NewsCollector] Fetched {len(articles)} articles for {symbol}")
        return articles

    except Exception as e:
        try:
            con.close()
        except Exception:
            pass
        print(f"[NewsCollector] Warning — {symbol}: {e}")
        return []


def get_news_summary(
    symbol: str,
    company_name: str = "",
    db_path: str = os.getenv("WEALTHOS_DB_PATH", "./db/wealthos.duckdb")
) -> dict:
    symbol = symbol.strip().upper()
    if symbol.endswith(".NS") or symbol.endswith(".BO"):
        symbol = symbol[:-3]

    empty = {
        "symbol":            symbol,
        "total_articles":    0,
        "avg_sentiment":     0.0,
        "overall_sentiment": "NEUTRAL",
        "positive_count":    0,
        "negative_count":    0,
        "neutral_count":     0,
        "top_headlines":     [],
        "articles":          []
    }

    articles = fetch_news(symbol, company_name, db_path=db_path)

    if not articles:
        return empty

    total = len(articles)
    scores = [a["sentiment_score"] for a in articles]
    avg_sentiment = round(sum(scores) / total, 2)

    positive_count = sum(1 for s in scores if s > 0.1)
    negative_count = sum(1 for s in scores if s < -0.1)
    neutral_count  = total - positive_count - negative_count

    if avg_sentiment > 0.2:
        overall_sentiment = "POSITIVE"
    elif avg_sentiment < -0.2:
        overall_sentiment = "NEGATIVE"
    else:
        overall_sentiment = "NEUTRAL"

    top_headlines = [a["headline"] for a in articles[:3]]

    return {
        "symbol":            symbol,
        "total_articles":    total,
        "avg_sentiment":     avg_sentiment,
        "overall_sentiment": overall_sentiment,
        "positive_count":    positive_count,
        "negative_count":    negative_count,
        "neutral_count":     neutral_count,
        "top_headlines":     top_headlines,
        "articles":          articles
    }
