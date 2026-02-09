import pandas as pd
import numpy as np


# ============================================================
# Pivot Detection (NO lookahead, symmetric window)
# ============================================================

def detect_pivots(df: pd.DataFrame, window: int = 5) -> pd.Series:

    highs = df["high"]
    lows  = df["low"]

    roll_max = highs.rolling(window * 2 + 1, center=True).max()
    roll_min = lows.rolling(window * 2 + 1, center=True).min()

    pivots = np.zeros(len(df), dtype=int)

    for i in range(len(df)):

        if i < window or i > len(df) - window - 1:
            continue

        if highs.iloc[i] >= roll_max.iloc[i]:
            pivots[i] = 1   # Pivot High

        elif lows.iloc[i] <= roll_min.iloc[i]:
            pivots[i] = 2   # Pivot Low

    return pd.Series(pivots, index=df.index)


# ============================================================
# Market Structure Engine (with confidence)
# ============================================================

def detect_structure_state(df: pd.DataFrame, lookback: int = 80) -> dict:

    df = df.copy()

    # ---------- Detect pivots ----------
    df["pivot"] = detect_pivots(df)

    recent = df.tail(lookback)

    highs = recent[recent["pivot"] == 1]
    lows  = recent[recent["pivot"] == 2]

    structure = {

        # ---- Regime ----
        "trend": "Neutral",
        "state": "Ranging",

        # ---- Pivot info ----
        "recent_highs": int(len(highs)),
        "recent_lows": int(len(lows)),

        "last_high": None,
        "last_low": None,

        # ---- Liquidity + BOS ----
        "liquidity_sweep": None,
        "sweep_price": None,

        "break_of_structure": None,
        "bos_price": None,

        # ---- Confidence (new) ----
        "structure_confidence": "LOW",
        "structure_confidence_score": 1,
    }

    # ---------- Store last pivot levels ----------

    if len(highs) > 0:
        structure["last_high"] = float(highs["high"].iloc[-1])

    if len(lows) > 0:
        structure["last_low"] = float(lows["low"].iloc[-1])

    # =========================================================
    # Core structure logic
    # =========================================================

    if len(highs) < 2 or len(lows) < 2:
        return structure   # Not enough data to infer structure

    prev_high = float(highs["high"].iloc[-2])
    last_high = float(highs["high"].iloc[-1])

    prev_low  = float(lows["low"].iloc[-2])
    last_low  = float(lows["low"].iloc[-1])

    close_now = float(recent["close"].iloc[-1])

    # ---------------------------------------------------------
    # 1) Liquidity Sweep Detection
    # ---------------------------------------------------------

    sweep_dir = None

    if last_low < prev_low:
        sweep_dir = "down"
        structure["liquidity_sweep"] = "down"
        structure["sweep_price"] = last_low

    elif last_high > prev_high:
        sweep_dir = "up"
        structure["liquidity_sweep"] = "up"
        structure["sweep_price"] = last_high


    # ---------------------------------------------------------
    # 2) Break of Structure Detection
    # ---------------------------------------------------------

    bos_dir = None

    if close_now > prev_high:
        bos_dir = "up"
        structure["break_of_structure"] = "up"
        structure["bos_price"] = prev_high

    elif close_now < prev_low:
        bos_dir = "down"
        structure["break_of_structure"] = "down"
        structure["bos_price"] = prev_low


    # ---------------------------------------------------------
    # 3) Trend + State Inference
    # ---------------------------------------------------------

    if bos_dir == "up":

        structure["trend"] = "Uptrend"
        structure["state"] = "Structure Break Up"

    elif bos_dir == "down":

        structure["trend"] = "Downtrend"
        structure["state"] = "Structure Break Down"

    else:
        # No BOS yet — infer from higher highs / lower lows

        if last_high > prev_high and last_low > prev_low:
            structure["trend"] = "Uptrend"
            structure["state"] = "Higher Highs"

        elif last_high < prev_high and last_low < prev_low:
            structure["trend"] = "Downtrend"
            structure["state"] = "Lower Lows"

        else:
            structure["trend"] = "Neutral"
            structure["state"] = "Ranging"


    # ---------------------------------------------------------
    # 4) Structure Confidence (NEW LOGIC)
    # ---------------------------------------------------------

    if bos_dir:

        if sweep_dir and bos_dir == sweep_dir:
            structure["structure_confidence"] = "HIGH"
            structure["structure_confidence_score"] = 3

        else:
            structure["structure_confidence"] = "MEDIUM"
            structure["structure_confidence_score"] = 2

    else:
        structure["structure_confidence"] = "LOW"
        structure["structure_confidence_score"] = 1


    return structure
