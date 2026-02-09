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


def detect_exhaustion(momentum, structure):
    """
    momentum can be:
      - a single momentum dict (current UI flow)
      - OR a list of momentum dicts (future extension)

    structure is latest structure dict
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

    raw_flags = []

    for mom in momentum_series:

        if not isinstance(mom, dict):
            raw_flags.append(False)
            continue

        atr = mom.get("atr_pct")
        vol = mom.get("vol_spike")
        sideways = mom.get("sideways", False)
        squeeze = mom.get("bb_squeeze", False)

        exhausted = False

        # ---- Compression / chop ----
        if squeeze or sideways:
            exhausted = True

        # ---- Weak energy ----
        if atr is not None and atr < 0.35:
            exhausted = True

        if vol is not None and vol < 0.8:
            exhausted = True

        # ---- Trend losing drive ----
        if trend in ["Uptrend", "Downtrend"]:
            if state in ["Higher Highs", "Lower Lows"]:
                if (atr is not None and atr < 0.4) or (vol is not None and vol < 1.0):
                    exhausted = True

        raw_flags.append(exhausted)

    # ---- Apply persistence (needs at least 3 in a row, but works even if only 1 exists) ----
    persisted = _apply_persistence(raw_flags, required=3)

    if persisted[-1]:
        return "EXHAUSTED"

    return "HEALTHY"
