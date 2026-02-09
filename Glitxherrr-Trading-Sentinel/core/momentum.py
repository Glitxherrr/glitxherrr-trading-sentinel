import pandas as pd
import numpy as np


# ============================================================
# Utilities
# ============================================================

def _safe_float(x, default=0.0):
    try:
        if x is None:
            return default
        return float(x)
    except Exception:
        return default


def _percentile_rank(hist: np.ndarray, x: float) -> float:
    if hist is None or len(hist) == 0:
        return 50.0
    return float((hist < x).mean() * 100)


def _apply_persistence(flags, required=3):
    count = 0
    out = []

    for v in flags:
        if v:
            count += 1
        else:
            count = 0

        out.append(count >= required)

    return out


# ============================================================
# Indicators
# ============================================================

def compute_obv(df: pd.DataFrame) -> pd.Series:
    diff = df["close"].diff()
    direction = np.sign(diff).fillna(0.0)
    return (direction * df["volume"]).cumsum()


def fast_slope(series: pd.Series, window: int = 20) -> float:
    if len(series) < window + 1:
        return 0.0
    y = series.tail(window).values
    return float((y[-1] - y[0]) / window)


def atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
    high = df["high"]
    low = df["low"]
    close = df["close"]

    prev_close = close.shift(1)

    tr = pd.concat(
        [
            (high - low),
            (high - prev_close).abs(),
            (low - prev_close).abs(),
        ],
        axis=1,
    ).max(axis=1)

    return tr.rolling(period).mean()


def volume_spike(df: pd.DataFrame, window: int = 50) -> float:
    vol = df["volume"].astype(float)

    baseline = _safe_float(vol.tail(window).median(), 0.0)
    now = _safe_float(vol.iloc[-1], 0.0)

    if baseline > 0:
        vs = now / baseline
    else:
        vs = 1.0

    return float(max(0.0, min(5.0, vs)))


def bollinger_squeeze(
    df: pd.DataFrame,
    period: int = 20,
    mult: float = 2.0,
    squeeze_lookback: int = 120,
):

    close = df["close"]

    ma = close.rolling(period).mean()
    std = close.rolling(period).std(ddof=0)

    upper = ma + mult * std
    lower = ma - mult * std

    bandwidth = (upper - lower) / ma

    bw_now = bandwidth.iloc[-1]

    bw_hist = bandwidth.shift(1).tail(squeeze_lookback).dropna()

    if len(bw_hist) < 30:
        return {
            "bb_width": None,
            "squeeze": False,
            "squeeze_percentile": None,
            "squeeze_series": [False] * len(df),
        }

    percentiles = [
        float((bw_hist.values < bw).mean() * 100)
        if not np.isnan(bw) else 100
        for bw in bandwidth
    ]

    squeeze_series = [p <= 15.0 for p in percentiles]

    percentile_now = percentiles[-1]

    return {
        "bb_width": round(float(bw_now), 6),
        "squeeze": squeeze_series[-1],
        "squeeze_percentile": round(percentile_now, 2),
        "squeeze_series": squeeze_series,
    }


# ============================================================
# ===================== SLOW ENGINE (4H) ====================
# Regime, trend health, compression
# ============================================================

def momentum_score(df_4h: pd.DataFrame) -> dict:

    df = df_4h.copy()

    if len(df) < 120:
        return {
            "trend_energy_pctile": 50.0,
            "trend_slope": 0.0,
            "bb_squeeze": False,
            "bb_squeeze_percentile": None,
            "sideways_regime": True,
            "breakout_watch": False,
            "breakout_direction": "NEUTRAL",
            "momentum_score": -5.0,
        }

    price = float(df["close"].iloc[-1])

    # ---------- OBV energy ----------

    obv = compute_obv(df)
    obv_slope = fast_slope(obv, window=40)

    obv_energy = obv.diff().abs().rolling(40).sum()
    energy_now = _safe_float(obv_energy.iloc[-1], 0.0)

    energy_hist = obv_energy.shift(1).tail(180).dropna().values
    energy_pctile = _percentile_rank(energy_hist, energy_now)

    # ---------- Volatility regime ----------

    atr_val = atr(df, period=14).iloc[-1]
    atr_val = _safe_float(atr_val, 0.0)

    atr_pct = (atr_val / price) * 100 if price else 0.0

    # ---------- Compression (with persistence) ----------

    bb = bollinger_squeeze(df, squeeze_lookback=140)

    squeeze_raw = bb["squeeze_series"]
    squeeze_persisted = _apply_persistence(squeeze_raw, required=3)

    squeeze = squeeze_persisted[-1]

    # ---------- Sideways regime ----------

    sideways_regime = (
        (atr_pct < 0.25)
        and (energy_pctile < 35)
        and (not squeeze)
    )

    # ---------- Trend context ----------

    ma20 = df["close"].rolling(20).mean().iloc[-1]
    ma20 = _safe_float(ma20, price)

    trend_context = "UP" if price > ma20 else "DOWN"

    if obv_slope > 0:
        flow_dir = "UP"
    elif obv_slope < 0:
        flow_dir = "DOWN"
    else:
        flow_dir = "NEUTRAL"

    # ---------- Breakout regime ----------

    breakout_watch = bool(squeeze and energy_pctile > 55)

    breakout_direction = "NEUTRAL"

    if squeeze:
        if flow_dir == trend_context:
            breakout_direction = trend_context
        elif flow_dir != "NEUTRAL":
            breakout_direction = flow_dir
        else:
            breakout_direction = trend_context

    # ---------- Momentum health score ----------

    score = 0.0

    score += ((energy_pctile - 50) / 50) * 4.0

    if obv_slope > 0:
        score += 1.5
    elif obv_slope < 0:
        score -= 1.5

    if sideways_regime:
        score -= 4.5

    if squeeze:
        score += 1.5

    if breakout_watch:
        score += 4.0

    score = max(-10.0, min(10.0, score))

    return {
        "trend_energy_pctile": round(float(energy_pctile), 2),
        "trend_slope": round(float(obv_slope), 3),
        "bb_squeeze": squeeze,
        "bb_squeeze_percentile": bb["squeeze_percentile"],
        "sideways_regime": sideways_regime,
        "breakout_watch": breakout_watch,
        "breakout_direction": breakout_direction,
        "momentum_score": round(score, 2),
    }


# ============================================================
# ===================== FAST ENGINE (1H) ====================
# Pressure & ignition
# ============================================================

def momentum_score_1h(df_1h: pd.DataFrame) -> dict:

    df = df_1h.copy()

    if len(df) < 60:
        return {
            "atr_pct": 0.0,
            "vol_spike": 1.0,
            "obv_slope": 0.0,
            "flow_state": "NEUTRAL",
            "bb_squeeze": False,
            "bb_squeeze_percentile": None,
            "sideways": True,
        }

    price = float(df["close"].iloc[-1])

    # ---------- ATR pressure ----------

    atr_val = atr(df, period=14).iloc[-1]
    atr_val = _safe_float(atr_val, 0.0)

    atr_pct = (atr_val / price) * 100 if price else 0.0

    # ---------- Volume ignition ----------

    vs = volume_spike(df, window=30)

    # ---------- OBV flow ----------

    obv = compute_obv(df)
    slope = fast_slope(obv, window=20)

    if slope > 0:
        flow = "UP"
    elif slope < 0:
        flow = "DOWN"
    else:
        flow = "NEUTRAL"

    # ---------- Fast compression (with persistence) ----------

    bb = bollinger_squeeze(df, squeeze_lookback=80)

    squeeze_raw = bb["squeeze_series"]
    squeeze_persisted = _apply_persistence(squeeze_raw, required=3)

    squeeze = squeeze_persisted[-1]

    # ---------- Fast sideways ----------

    sideways = (
        (atr_pct < 0.25)
        and (vs < 0.85)
        and (not squeeze)
    )

    return {
        "atr_pct": round(atr_pct, 4),
        "vol_spike": round(vs, 3),
        "obv_slope": round(float(slope), 3),
        "flow_state": flow,
        "bb_squeeze": squeeze,
        "bb_squeeze_percentile": bb["squeeze_percentile"],
        "sideways": sideways,
    }
