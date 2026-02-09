def compute_dxy_bias(structure, trend, strength):

    if not structure:
        return "NEUTRAL"

    struct_trend = structure.get("trend")
    state = structure.get("state")
    bos = structure.get("break_of_structure")

    # ---- Strong regime shifts ----
    if bos == "up":
        return "BULLISH"

    if bos == "down":
        return "BEARISH"

    # ---- Trend continuation ----
    if struct_trend == "Uptrend" and strength == "HIGH":
        return "BULLISH"

    if struct_trend == "Downtrend" and strength == "HIGH":
        return "BEARISH"

    # ---- Ranging or mixed ----
    if state == "Ranging":
        return "MIXED - Trend Continuation"

    return "NEUTRAL - Dead Market"
