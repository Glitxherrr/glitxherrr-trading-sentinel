import requests
import pandas as pd
import numpy as np
from datetime import datetime, timezone, timedelta
from io import StringIO


# ============================================================
#                      SIMPLE CACHE
# ============================================================

_CACHE = {
    "timestamp": None,
    "result": None
}

CACHE_MINUTES = 10


def _now_utc():
    return datetime.now(timezone.utc)


def _get_cache():
    ts = _CACHE["timestamp"]

    if ts is None:
        return None

    if (_now_utc() - ts) < timedelta(minutes=CACHE_MINUTES):
        return _CACHE["result"]

    return None


def _set_cache(result):
    _CACHE["timestamp"] = _now_utc()
    _CACHE["result"] = result


# ============================================================
#                       MATH HELPERS
# ============================================================

def _linear_slope(series: np.ndarray) -> float:
    """
    Simple linear regression slope for trend direction.
    """
    if len(series) < 10:
        return 0.0

    x = np.arange(len(series))
    slope, _ = np.polyfit(x, series, 1)

    return float(slope)


def _build_detector(close: np.ndarray, interval_label: str) -> dict:
    """
    Builds normalized DXY regime detector.
    """

    last_price = float(close[-1])

    recent = close[-36:]
    slope = _linear_slope(recent)

    # Normalize slope by price level (scale-free)
    norm_strength = abs(slope) / max(last_price, 1e-9)

    # ---------------- Trend direction ----------------

    if norm_strength < 0.00003:
        trend = "NEUTRAL"
    elif slope > 0:
        trend = "UP"
    else:
        trend = "DOWN"

    # ---------------- Trend strength ----------------

    if norm_strength < 0.00005:
        strength = "LOW"
    elif norm_strength < 0.00012:
        strength = "MEDIUM"
    else:
        strength = "HIGH"

    # ---------------- Context note (NON-CAUSAL) ----------------

    if trend == "UP" and strength in ("MEDIUM", "HIGH"):
        note = (
            "USD trend strengthening — historically associated with tighter "
            "financial conditions and elevated volatility risk"
        )

    elif trend == "DOWN" and strength in ("MEDIUM", "HIGH"):
        note = (
            "USD trend weakening — historically associated with looser "
            "financial conditions and a more supportive liquidity backdrop"
        )

    else:
        note = (
            "USD trend neutral — no dominant macro regime currently observed"
        )

    return {
        "trend": trend,
        "strength": strength,
        "slope": round(float(slope), 6),
        "last": round(last_price, 4),
        "note": note,
        "interval": interval_label,
    }


# ============================================================
#                     DATA SOURCES
# ============================================================

def _fetch_fred_dxy():
    """
    Fetch DXY proxy from FRED (broad USD index).
    """
    url = "https://fred.stlouisfed.org/graph/fredgraph.csv?id=DTWEXM"

    r = requests.get(url, timeout=20)
    r.raise_for_status()

    df = pd.read_csv(StringIO(r.text))

    df.columns = ["date", "close"]
    df["date"] = pd.to_datetime(df["date"], utc=True)
    df["close"] = pd.to_numeric(df["close"], errors="coerce")

    df = df.dropna()

    return df.set_index("date")


def _fetch_stooq_dxy():
    """
    Fetch DXY from Stooq as fallback source.
    """
    url = "https://stooq.com/q/d/l/?s=dx.f&i=d"

    r = requests.get(url, timeout=20)
    r.raise_for_status()

    df = pd.read_csv(StringIO(r.text))

    df["Date"] = pd.to_datetime(df["Date"], utc=True)
    df["Close"] = pd.to_numeric(df["Close"], errors="coerce")

    df = df.dropna(subset=["Close"])

    df = df.rename(
        columns={
            "Date": "date",
            "Close": "close"
        }
    )

    return df.set_index("date")


# ============================================================
#                       PUBLIC API
# ============================================================

def dxy_detector(interval: str = "1h") -> dict:
    """
    Returns a macro regime snapshot for USD (DXY proxy).

    Output:
    {
        trend: UP / DOWN / NEUTRAL
        strength: LOW / MEDIUM / HIGH
        slope: float
        last: float
        note: contextual description
        interval: source timeframe label
        source: FRED | Stooq
    }
    """

    cached = _get_cache()
    if cached:
        return cached

    # ---- Primary source: FRED ----
    try:
        df = _fetch_fred_dxy()

        out = _build_detector(
            df["close"].values,
            interval_label="1d (FRED proxy)"
        )

        out["source"] = "FRED"

        _set_cache(out)

        return out

    except Exception:
        pass

    # ---- Fallback source: Stooq ----
    try:
        df = _fetch_stooq_dxy()

        out = _build_detector(
            df["close"].values,
            interval_label="1d (Stooq)"
        )

        out["source"] = "Stooq"

        _set_cache(out)

        return out

    except Exception:
        pass

    # ---- Total failure ----
    raise RuntimeError("DXY data unavailable from all sources")
