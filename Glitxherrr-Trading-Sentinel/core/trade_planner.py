import pandas as pd
from core.structure import trend_bias, last_swing_levels
from core.zones import sr_zones
from data.derivatives import get_funding_rate, get_open_interest, get_global_long_short_ratio


def nearest_levels(zones, price: float):
    supports = [z for z in zones if z["type"] == "support" and z["top"] <= price]
    resistances = [z for z in zones if z["type"] == "resistance" and z["bottom"] >= price]

    supports = sorted(supports, key=lambda z: abs(price - z["top"]))
    resistances = sorted(resistances, key=lambda z: abs(z["bottom"] - price))

    return supports[:2], resistances[:2]


def is_entry_in_zone(entry: float, zones: list, direction: str) -> bool:
    if not zones:
        return False

    if direction == "LONG":
        for z in zones:
            if z["type"] == "support" and z["bottom"] <= entry <= z["top"]:
                return True

    if direction == "SHORT":
        for z in zones:
            if z["type"] == "resistance" and z["bottom"] <= entry <= z["top"]:
                return True

    return False


def build_trade_plan(symbol: str, df_15m: pd.DataFrame, df_1h: pd.DataFrame, df_4h: pd.DataFrame):
    price = float(df_15m.iloc[-1]["close"])

    bias_4h = trend_bias(df_4h)
    bias_1h = trend_bias(df_1h)

    zones = sr_zones(df_1h, lookback=250)
    supports, resistances = nearest_levels(zones, price)

    last_high, last_low = last_swing_levels(df_1h)

    direction = "WAIT"
    entry = None
    stop = None
    target1 = None
    target2 = None

    # Decide direction from HTF
    if bias_4h == "Bullish" and bias_1h in ("Bullish", "Neutral"):
        direction = "LONG"
    elif bias_4h == "Bearish" and bias_1h in ("Bearish", "Neutral"):
        direction = "SHORT"
    else:
        direction = "WAIT"

    # Entry must be inside zone
    if direction == "LONG":
        if supports:
            entry = float(supports[0]["top"])
            stop = float(supports[0]["bottom"])
        else:
            direction = "WAIT"

        if resistances:
            target1 = float(resistances[0]["bottom"])
            target2 = float(resistances[0]["top"])
        else:
            target1 = entry * 1.01 if entry else None
            target2 = entry * 1.02 if entry else None

    if direction == "SHORT":
        if resistances:
            entry = float(resistances[0]["bottom"])
            stop = float(resistances[0]["top"])
        else:
            direction = "WAIT"

        if supports:
            target1 = float(supports[0]["top"])
            target2 = float(supports[0]["bottom"])
        else:
            target1 = entry * 0.99 if entry else None
            target2 = entry * 0.98 if entry else None

    # Enforce entry inside zone
    if direction in ("LONG", "SHORT"):
        if entry is None or not is_entry_in_zone(entry, zones, direction):
            direction = "WAIT"
            entry = stop = target1 = target2 = None

    # Structural invalidation via last swing break
    if direction == "LONG" and last_low and stop is not None:
        stop = min(stop, last_low * 0.999)

    if direction == "SHORT" and last_high and stop is not None:
        stop = max(stop, last_high * 1.001)

    rr = None
    if direction != "WAIT" and entry and stop and target1:
        risk = abs(entry - stop)
        reward = abs(target1 - entry)
        rr = round(reward / risk, 2) if risk != 0 else None

    # Normalize WAIT outputs (CRITICAL)
    if direction == "WAIT":
        entry = None
        stop = None
        target1 = None
        target2 = None
        rr = None

    # Derivatives
    funding = None
    oi = None
    lsr = None
    try:
        funding = get_funding_rate(symbol)
        oi = get_open_interest(symbol)
        lsr = get_global_long_short_ratio(symbol, period="5m", limit=1)
    except Exception:
        pass

    return {
        "symbol": symbol,
        "price": price,
        "bias_4h": bias_4h,
        "bias_1h": bias_1h,

        "direction": direction,
        "entry": round(entry, 2) if entry is not None else None,
        "stop": round(stop, 2) if stop is not None else None,
        "target1": round(target1, 2) if target1 is not None else None,
        "target2": round(target2, 2) if target2 is not None else None,
        "rr": rr,

        "last_swing_high": last_high,
        "last_swing_low": last_low,

        "zones": zones[:8],

        "funding": funding,
        "open_interest": oi,
        "long_short_ratio": lsr,
    }
