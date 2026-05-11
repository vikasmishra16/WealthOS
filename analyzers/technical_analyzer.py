import os
import pandas as pd

RSI_PERIOD       = 14
MACD_FAST        = 12
MACD_SLOW        = 26
MACD_SIGNAL      = 9
BB_PERIOD        = 20
BB_STD           = 2
ATR_PERIOD       = 14
VOL_MA_PERIOD    = 20
SUPPORT_LOOKBACK = 60
DMA_SHORT        = 50
DMA_LONG         = 200


def _signal(value, bull_thresh, bear_thresh, higher_is_bullish=True) -> str:
    if higher_is_bullish:
        if value >= bull_thresh:
            return "BULLISH"
        if value <= bear_thresh:
            return "BEARISH"
        return "NEUTRAL"
    else:
        if value <= bull_thresh:
            return "BULLISH"
        if value >= bear_thresh:
            return "BEARISH"
        return "NEUTRAL"


def compute_technicals(df: pd.DataFrame) -> dict:
    try:
        import pandas_ta as ta

        if df is None or len(df) < 30:
            return {"error": "Insufficient price data (need 30+ rows)"}

        df = df.sort_index()

        dma_50  = df["close"].rolling(DMA_SHORT).mean()
        dma_200 = df["close"].rolling(DMA_LONG).mean()

        current_close  = float(df["close"].iloc[-1])
        current_dma50  = float(dma_50.iloc[-1])  if not pd.isna(dma_50.iloc[-1])  else None
        current_dma200 = float(dma_200.iloc[-1]) if not pd.isna(dma_200.iloc[-1]) else None

        if current_dma50 is None:
            dma50_signal = "INSUFFICIENT DATA"
        elif current_close > current_dma50:
            dma50_signal = "BULLISH"
        else:
            dma50_signal = "BEARISH"

        if current_dma200 is None:
            dma200_signal = "INSUFFICIENT DATA"
        elif current_close > current_dma200:
            dma200_signal = "BULLISH"
        else:
            dma200_signal = "BEARISH"

        golden_cross = bool(
            current_dma50 and current_dma200 and current_dma50 > current_dma200
        )

        rsi_series  = ta.rsi(df["close"], length=RSI_PERIOD)
        current_rsi = (
            float(rsi_series.iloc[-1])
            if rsi_series is not None and not pd.isna(rsi_series.iloc[-1])
            else None
        )

        if current_rsi is None:
            rsi_signal = "INSUFFICIENT DATA"
        elif current_rsi >= 70:
            rsi_signal = "BEARISH"
        elif current_rsi <= 30:
            rsi_signal = "BULLISH"
        else:
            rsi_signal = "NEUTRAL"

        macd_df = ta.macd(
            df["close"],
            fast=MACD_FAST,
            slow=MACD_SLOW,
            signal=MACD_SIGNAL
        )

        macd_col   = f"MACD_{MACD_FAST}_{MACD_SLOW}_{MACD_SIGNAL}"
        signal_col = f"MACDs_{MACD_FAST}_{MACD_SLOW}_{MACD_SIGNAL}"
        hist_col   = f"MACDh_{MACD_FAST}_{MACD_SLOW}_{MACD_SIGNAL}"

        def _safe_float(series, idx=-1):
            try:
                val = series.iloc[idx]
                return float(val) if not pd.isna(val) else None
            except Exception:
                return None

        current_macd   = _safe_float(macd_df[macd_col])   if macd_df is not None and macd_col   in macd_df.columns else None
        current_signal = _safe_float(macd_df[signal_col]) if macd_df is not None and signal_col in macd_df.columns else None
        current_hist   = _safe_float(macd_df[hist_col])   if macd_df is not None and hist_col   in macd_df.columns else None
        prev_hist      = _safe_float(macd_df[hist_col], -2) if macd_df is not None and hist_col in macd_df.columns else None

        if current_macd is None:
            macd_signal_str = "INSUFFICIENT DATA"
        elif current_hist is not None and current_hist > 0 and prev_hist is not None and prev_hist <= 0:
            macd_signal_str = "BULLISH CROSSOVER"
        elif current_hist is not None and current_hist < 0 and prev_hist is not None and prev_hist >= 0:
            macd_signal_str = "BEARISH CROSSOVER"
        elif current_hist is not None and current_hist > 0:
            macd_signal_str = "BULLISH"
        elif current_hist is not None and current_hist < 0:
            macd_signal_str = "BEARISH"
        else:
            macd_signal_str = "NEUTRAL"

        bb_df = ta.bbands(df["close"], length=BB_PERIOD, std=BB_STD)

        bbu_col = f"BBU_{BB_PERIOD}_{float(BB_STD)}"
        bbl_col = f"BBL_{BB_PERIOD}_{float(BB_STD)}"
        bbm_col = f"BBM_{BB_PERIOD}_{float(BB_STD)}"

        current_bb_upper = _safe_float(bb_df[bbu_col]) if bb_df is not None and bbu_col in bb_df.columns else None
        current_bb_lower = _safe_float(bb_df[bbl_col]) if bb_df is not None and bbl_col in bb_df.columns else None
        current_bb_mid   = _safe_float(bb_df[bbm_col]) if bb_df is not None and bbm_col in bb_df.columns else None

        if any(v is None for v in [current_bb_upper, current_bb_lower, current_bb_mid]):
            bb_signal = "INSUFFICIENT DATA"
        elif current_close >= current_bb_upper:
            bb_signal = "OVERBOUGHT"
        elif current_close <= current_bb_lower:
            bb_signal = "OVERSOLD"
        elif current_close > current_bb_mid:
            bb_signal = "NEUTRAL-BULLISH"
        else:
            bb_signal = "NEUTRAL-BEARISH"

        if current_bb_upper is not None and current_bb_lower is not None and current_bb_mid and current_bb_mid != 0:
            bb_width = round((current_bb_upper - current_bb_lower) / current_bb_mid * 100, 2)
        else:
            bb_width = None

        atr_series  = ta.atr(df["high"], df["low"], df["close"], length=ATR_PERIOD)
        current_atr = _safe_float(atr_series) if atr_series is not None else None
        atr_pct     = round(current_atr / current_close * 100, 2) if current_atr and current_close else None

        vol_ma         = df["volume"].rolling(VOL_MA_PERIOD).mean()
        current_volume = float(df["volume"].iloc[-1])
        current_vol_ma = float(vol_ma.iloc[-1]) if not pd.isna(vol_ma.iloc[-1]) else None

        vol_ratio = round(current_volume / current_vol_ma, 2) if current_vol_ma else None

        if vol_ratio is None:
            volume_trend = "INSUFFICIENT DATA"
        elif vol_ratio >= 1.5:
            volume_trend = "HIGH VOLUME"
        elif vol_ratio <= 0.5:
            volume_trend = "LOW VOLUME"
        else:
            volume_trend = "NORMAL VOLUME"

        price_up = current_close > float(df["close"].iloc[-2])
        if vol_ratio and vol_ratio >= 1.5 and price_up:
            volume_confirmation = "BUYING VOLUME — BULLISH CONFIRMATION"
        elif vol_ratio and vol_ratio >= 1.5 and not price_up:
            volume_confirmation = "SELLING VOLUME — BEARISH CONFIRMATION"
        else:
            volume_confirmation = "NO STRONG CONFIRMATION"

        recent     = df.tail(SUPPORT_LOOKBACK)
        lows_arr   = recent["low"].values
        highs_arr  = recent["high"].values

        local_lows  = []
        local_highs = []
        for i in range(1, len(lows_arr) - 1):
            if lows_arr[i] < lows_arr[i - 1] and lows_arr[i] < lows_arr[i + 1]:
                local_lows.append(round(float(lows_arr[i]), 2))
            if highs_arr[i] > highs_arr[i - 1] and highs_arr[i] > highs_arr[i + 1]:
                local_highs.append(round(float(highs_arr[i]), 2))

        support_levels = sorted(
            [v for v in local_lows if v < current_close], reverse=False
        )[-3:] if local_lows else []

        resistance_levels = sorted(
            [v for v in local_highs if v > current_close]
        )[:3] if local_highs else []

        last_252    = df.tail(252)
        week52_high = round(float(last_252["high"].max()), 2)
        week52_low  = round(float(last_252["low"].min()), 2)
        pct_from_52w_high = round(
            (current_close - week52_high) / week52_high * 100, 2
        )

        return {
            "current_close":       round(current_close, 2),
            "week52_high":         week52_high,
            "week52_low":          week52_low,
            "pct_from_52w_high":   pct_from_52w_high,
            "dma_50":              round(current_dma50, 2)  if current_dma50  else None,
            "dma_200":             round(current_dma200, 2) if current_dma200 else None,
            "dma50_signal":        dma50_signal,
            "dma200_signal":       dma200_signal,
            "golden_cross":        golden_cross,
            "rsi":                 round(current_rsi, 2)    if current_rsi    else None,
            "rsi_signal":          rsi_signal,
            "macd":                round(current_macd, 4)   if current_macd   else None,
            "macd_signal_line":    round(current_signal, 4) if current_signal else None,
            "macd_histogram":      round(current_hist, 4)   if current_hist   else None,
            "macd_signal":         macd_signal_str,
            "bb_upper":            round(current_bb_upper, 2) if current_bb_upper else None,
            "bb_lower":            round(current_bb_lower, 2) if current_bb_lower else None,
            "bb_mid":              round(current_bb_mid, 2)   if current_bb_mid   else None,
            "bb_signal":           bb_signal,
            "bb_width_pct":        bb_width,
            "atr":                 round(current_atr, 2) if current_atr else None,
            "atr_pct":             atr_pct,
            "current_volume":      int(current_volume),
            "vol_ma_20":           int(current_vol_ma) if current_vol_ma else None,
            "vol_ratio":           vol_ratio,
            "volume_trend":        volume_trend,
            "volume_confirmation": volume_confirmation,
            "support_levels":      support_levels,
            "resistance_levels":   resistance_levels
        }

    except Exception as e:
        return {"error": str(e)}


def get_technical_summary(df: pd.DataFrame) -> dict:
    result = compute_technicals(df)

    if "error" in result:
        return result

    signals = [
        result["dma50_signal"],
        result["dma200_signal"],
        result["rsi_signal"],
        result["macd_signal"],
        result["bb_signal"]
    ]
    bullish_count = sum(1 for s in signals if "BULLISH" in s)
    bearish_count = sum(1 for s in signals if "BEARISH" in s)

    if bullish_count >= 3:
        overall = "BULLISH"
    elif bearish_count >= 3:
        overall = "BEARISH"
    else:
        overall = "NEUTRAL"

    lines = []
    lines.append(f"Overall Technical Signal: {overall}")
    lines.append(
        f"Price: ₹{result['current_close']} | "
        f"52w High: ₹{result['week52_high']} | "
        f"52w Low: ₹{result['week52_low']} "
        f"({result['pct_from_52w_high']}% from high)"
    )
    lines.append(f"50 DMA: ₹{result['dma_50']} — {result['dma50_signal']}")
    lines.append(f"200 DMA: ₹{result['dma_200']} — {result['dma200_signal']}")
    lines.append(f"Golden Cross: {'YES' if result['golden_cross'] else 'NO'}")
    lines.append(f"RSI(14): {result['rsi']} — {result['rsi_signal']}")
    lines.append(f"MACD: {result['macd_signal']}")
    lines.append(f"Bollinger: {result['bb_signal']}")
    lines.append(f"ATR: ₹{result['atr']} ({result['atr_pct']}% of price)")
    lines.append(
        f"Volume: {result['volume_trend']} "
        f"(ratio: {result['vol_ratio']}x) — "
        f"{result['volume_confirmation']}"
    )
    if result["support_levels"]:
        lines.append(f"Support: {result['support_levels']}")
    if result["resistance_levels"]:
        lines.append(f"Resistance: {result['resistance_levels']}")

    summary_str = "\n".join(lines)

    result["overall_signal"] = overall
    result["summary"]        = summary_str
    return result


def analyze_symbol(
    symbol: str,
    exchange: str = "NSE",
    db_path: str = os.getenv("WEALTHOS_DB_PATH", "./db/wealthos.duckdb")
) -> dict:
    try:
        from collectors.price_collector import fetch_price_history
        df = fetch_price_history(symbol, exchange=exchange, period="2y", db_path=db_path)

        if df is None or df.empty:
            return {"error": f"No price data for {symbol}"}

        df = df.sort_index()
        print(f"[TechnicalAnalyzer] Analyzing {symbol} — {len(df)} data points")
        return get_technical_summary(df)

    except Exception as e:
        return {"error": str(e)}
