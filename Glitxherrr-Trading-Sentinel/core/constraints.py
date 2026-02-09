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

    volume_state = btc_mom.get("volume_state", "normal")
    downside_momentum = btc_mom.get("downside_momentum", False)
    compression = btc_mom.get("bb_squeeze", False)

    # ---------------- DERIVATIVES CONTEXT ----------------

    lsr = btc_deriv.get("long_short_ratio") or {}
    lsr_state = lsr.get("state", "neutral")

    

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


