# exhaustion.py

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


def detect_exhaustion(momentum, structure, derivatives=None):
    """
    momentum can be:
      - a single momentum dict (current UI flow)
      - OR a list of momentum dicts (future extension)

    structure is latest structure dict
    derivatives is optional dict (funding/lsr/oi)
    """

    if not isinstance(structure, dict):
        return "UNKNOWN"

    # ---- Normalize momentum to list ----
    if isinstance(momentum, dict):
        momentum_series = [momentum]
    elif isinstance(momentum, list):
        momentum_series = momentum
    else:
        return "UNKNOWN"

    trend = structure.get("trend")
    state = structure.get("state")

    derivatives = derivatives or {}
    funding = derivatives.get("funding") or {}
    lsr = derivatives.get("long_short_ratio") or {}
    fbps = funding.get("fundingBps")
    ratio = lsr.get("longShortRatio")

    raw_flags = []
    compression_flags = []
    weakening_scores = []

    for mom in momentum_series:

        if not isinstance(mom, dict):
            raw_flags.append(False)
            continue

        atr = mom.get("atr_pct")
        vol = mom.get("vol_spike")
        sideways = mom.get("sideways", False)
        squeeze = mom.get("bb_squeeze", False)

        exhausted = False
        weakness_score = 0

        # ---- Compression / chop ----
        compression = bool(squeeze or sideways)
        compression_flags.append(compression)
        if compression:
            exhausted = True
            weakness_score += 1

        # ---- Weak energy ----
        if atr is not None and atr < 0.30:
            exhausted = True
            weakness_score += 1

        if vol is not None and vol < 1.0:
            exhausted = True
            weakness_score += 1

        # ---- Trend losing drive ----
        if trend in ["Uptrend", "Downtrend"]:
            if state in ["Higher Highs", "Lower Lows"]:
                if (atr is not None and atr < 0.35) or (vol is not None and vol < 1.1):
                    exhausted = True
                    weakness_score += 1

        # ---- Derivatives crowding vs trend ----
        if trend == "Uptrend":
            if fbps is not None and fbps >= 8:
                weakness_score += 1
            if ratio is not None and ratio >= 1.8:
                weakness_score += 1
        elif trend == "Downtrend":
            if fbps is not None and fbps <= -8:
                weakness_score += 1
            if ratio is not None and ratio <= 0.6:
                weakness_score += 1

        raw_flags.append(exhausted)
        weakening_scores.append(weakness_score)

    # ---- Apply persistence (needs at least 3 in a row, but works even if only 1 exists) ----
    persisted = _apply_persistence(raw_flags, required=3)
    compression_persisted = _apply_persistence(compression_flags, required=3)
    latest_weakness = weakening_scores[-1] if weakening_scores else 0

    if compression_persisted[-1]:
        return "COMPRESSION"

    if persisted[-1] or latest_weakness >= 3:
        return "EXHAUSTED"

    if latest_weakness >= 2:
        return "WEAKENING"

    return "HEALTHY"
