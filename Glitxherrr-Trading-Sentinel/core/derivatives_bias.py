def compute_derivatives_bias(struct, momentum, derivatives):
    funding = derivatives.get("funding", {})
    oi = derivatives.get("open_interest", {})
    lsr = derivatives.get("long_short_ratio", {})
    
    fbps = funding.get("fundingBps")
    open_i = oi.get("openInterest")
    ratio = lsr.get("longShortRatio")
    
    atr = (momentum or {}).get("atr_pct")
    vol = (momentum or {}).get("vol_spike")

    bullish = 0
    bearish = 0

    # ---- Funding (crowd positioning) ----
    if fbps is not None:
        if fbps < 0:
            bullish += 2   # shorts paying = strong bullish fuel
        elif fbps > 0:
            bearish += 2   # longs crowded

    # ---- Long/Short ratio ----
    if ratio is not None:
        if ratio >= 2:
            bearish += 1
        elif ratio <= 0.6:
            bullish += 1

    # ---- Open interest (fuel pressure) ----
    if open_i is not None:
        bullish += 1   # presence of leverage = movement potential

    # ---- Volatility energy ----
    if atr is not None:
        if atr > 0.30:
            bullish += 1
        elif atr < 0.18:
            bearish += 1

    # ---- Final synthesis ----
    if bullish >= 3 and bearish == 0:
        return "BULLISH"

    if bearish >= 3:
        return "BEARISH"

    if bullish == 0 and bearish == 0:
        return "NEUTRAL - Dead Market"

    return "MIXED - Trend Continuation"
