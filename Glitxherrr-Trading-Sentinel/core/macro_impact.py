def macro_tailwind(asset: str, dxy_trend: str, dxy_strength: str):

    if not dxy_trend:
        return "NEUTRAL"

    asset = asset.upper()

    # ---- GOLD / PAXG (inverse USD) ----
    if asset.startswith("PAXG") or asset.startswith("XAU"):

        if dxy_trend == "DOWN":
            return "BULLISH_TAILWIND"

        if dxy_trend == "UP":
            return "BEARISH_HEADWIND"

        return "NEUTRAL"

    # ---- BTC / risk assets ----
    if asset.startswith("BTC"):

        # Strong rising USD = pressure
        if dxy_trend == "UP" and dxy_strength in ("MEDIUM", "HIGH"):
            return "BEARISH_PRESSURE"

        # Falling USD can help but depends on liquidity
        if dxy_trend == "DOWN":
            return "POTENTIAL_TAILWIND"

        return "NEUTRAL"

    return "NEUTRAL"
