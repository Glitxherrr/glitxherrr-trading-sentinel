import pandas as pd
import numpy as np


def detect_swings(df: pd.DataFrame, left: int = 3, right: int = 3) -> pd.DataFrame:
    highs = df["high"].values
    lows = df["low"].values

    swing_high = np.zeros(len(df), dtype=bool)
    swing_low = np.zeros(len(df), dtype=bool)

    for i in range(left, len(df) - right):
        if highs[i] > highs[i - left:i].max() and highs[i] > highs[i + 1:i + 1 + right].max():
            swing_high[i] = True
        if lows[i] < lows[i - left:i].min() and lows[i] < lows[i + 1:i + 1 + right].min():
            swing_low[i] = True

    out = df.copy()
    out["swing_high"] = swing_high
    out["swing_low"] = swing_low
    return out


def trend_bias(df: pd.DataFrame) -> str:
    sdf = detect_swings(df, left=3, right=3)
    sh = sdf[sdf["swing_high"]]
    sl = sdf[sdf["swing_low"]]

    if len(sh) < 2 or len(sl) < 2:
        return "Neutral"

    last_sh = float(sh.iloc[-1]["high"])
    prev_sh = float(sh.iloc[-2]["high"])
    last_sl = float(sl.iloc[-1]["low"])
    prev_sl = float(sl.iloc[-2]["low"])

    if last_sh > prev_sh and last_sl > prev_sl:
        return "Bullish"
    if last_sh < prev_sh and last_sl < prev_sl:
        return "Bearish"
    return "Neutral"


def last_swing_levels(df: pd.DataFrame):
    sdf = detect_swings(df, left=3, right=3)
    sh = sdf[sdf["swing_high"]]
    sl = sdf[sdf["swing_low"]]

    last_high = float(sh.iloc[-1]["high"]) if len(sh) else None
    last_low = float(sl.iloc[-1]["low"]) if len(sl) else None
    return last_high, last_low
