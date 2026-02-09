def compute_derivatives_bias(struct, momentum, derivatives):
    funding = derivatives.get("funding", {})
    oi = derivatives.get("open_interest", {})
    lsr = derivatives.get("long_short_ratio", {})

    fbps = funding.get("fundingBps")
    open_i = oi.get("openInterest")
    ratio = lsr.get("longShortRatio")

    structure = struct or {}
    trend = str(structure.get("trend", "")).lower()
    trend_dir = "neutral"
    if "up" in trend:
        trend_dir = "up"
    elif "down" in trend:
        trend_dir = "down"

    flow = (momentum or {}).get("flow_state")
    flow_dir = "neutral"
    if flow == "UP":
        flow_dir = "up"
    elif flow == "DOWN":
        flow_dir = "down"

    bullish = 0
    bearish = 0

    # ---- Funding (positioning vs structure) ----
    if fbps is not None:
        if fbps < 0:
            if trend_dir == "up" or flow_dir == "up":
                bullish += 2 if fbps <= -8 else 1
            elif trend_dir == "down" or flow_dir == "down":
                bearish += 2 if fbps <= -8 else 1
            else:
                bullish += 1
        elif fbps > 0:
            if trend_dir == "down" or flow_dir == "down":
                bearish += 2 if fbps >= 8 else 1
            elif trend_dir == "up" or flow_dir == "up":
                bearish += 1
            else:
                bearish += 1

    # ---- Long/Short ratio ----
    if ratio is not None:
        if ratio >= 2:
            bearish += 2 if trend_dir == "down" else 1
        elif ratio <= 0.6:
            if trend_dir == "up" or flow_dir == "up":
                bullish += 2
            elif trend_dir == "neutral":
                bullish += 1

    # ---- Open interest (context only, no directional bias) ----
    _ = open_i

    # ---- Final synthesis ----
    if bullish >= 3 and bullish >= bearish + 2:
        return "BULLISH"

    if bearish >= 3 and bearish >= bullish + 2:
        return "BEARISH"

    if bullish == 0 and bearish == 0:
        return "NEUTRAL - Thin Derivatives"

    return "MIXED - Positioning vs Trend"
