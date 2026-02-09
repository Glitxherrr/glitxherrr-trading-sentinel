def _volume_state(vs):
    if vs is None:
        return "unknown"
    if vs >= 1.6:
        return "ignition"
    if vs >= 1.2:
        return "building"
    if vs >= 0.7:
        return "thin"
    return "dead"


def _lsr_state(ratio):
    if ratio is None:
        return "unknown"
    if ratio >= 2.0:
        return "extreme_longs"
    if ratio >= 1.5:
        return "long_heavy"
    if ratio <= 0.6:
        return "extreme_shorts"
    if ratio <= 0.8:
        return "short_heavy"
    return "balanced"


def build_constraints(market_state: dict) -> dict:

    btc  = market_state.get("btc", {})
    paxg = market_state.get("paxg", {})
    dxy  = market_state.get("dxy", {})

    # ---------------- SAFE EXTRACT ----------------

    btc_struct = btc.get("structure") or {}
    btc_mom    = btc.get("momentum") or {}
    btc_deriv  = btc.get("derivatives") or {}

    # ---------------- STRUCTURE CONTEXT ----------------

    htf_bias = btc_struct.get("trend")   # Uptrend / Downtrend / Neutral
    bos      = btc_struct.get("break_of_structure")

    # ---------------- MOMENTUM CONTEXT ----------------

    vol_spike = btc_mom.get("vol_spike")
    volume_state = _volume_state(vol_spike)
    downside_momentum = btc_mom.get("flow_state") == "DOWN"
    compression = btc_mom.get("bb_squeeze", False)

    # ---------------- DERIVATIVES CONTEXT ----------------

    lsr = btc_deriv.get("long_short_ratio") or {}
    ratio = lsr.get("longShortRatio")
    lsr_state = _lsr_state(ratio)

    

    # ==================================================
    #                 SHORT CONSTRAINT
    # ==================================================

    allow_shorts = (
        htf_bias != "Uptrend"              # structure not bullish
        and bos in ["down", "bearish"]     # real structure weakness
        and volume_state not in ["dead", "thin"]
        and downside_momentum is True
    )

    # ==================================================
    #                 SQUEEZE RISK
    # ==================================================

    squeeze_risk = (
        lsr_state in ["extreme_longs", "long_heavy"]
        and volume_state in ["dead", "thin"]
        and compression is True
    )

    # ==================================================
    #                 MACRO RULE
    # ==================================================

    macro_risk_type = "event-driven"

    return {
        "allow_shorts": allow_shorts,
        "squeeze_risk": squeeze_risk,
        "macro_risk_type": macro_risk_type,

        # (Optional debug info — very useful)
        "structure_bias": htf_bias,
        "bos_state": bos,
        "volume_state": volume_state,
        "lsr_state": lsr_state,
    }


