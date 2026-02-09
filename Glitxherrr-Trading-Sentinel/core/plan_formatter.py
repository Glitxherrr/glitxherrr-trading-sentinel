def _zone_lines(zones, max_n=6):
    if not zones:
        return "- None"

    lines = []
    for z in zones[:max_n]:
        lines.append(f"- {z['type'].upper()}: {round(z['bottom'],2)} → {round(z['top'],2)}")
    return "\n".join(lines)


def _next_setup_map(plan: dict) -> str:
    price = plan.get("price")
    zones = plan.get("zones") or []

    supports = [z for z in zones if z["type"] == "support"]
    resistances = [z for z in zones if z["type"] == "resistance"]

    supports_sorted = sorted(supports, key=lambda z: z["top"])
    resistances_sorted = sorted(resistances, key=lambda z: z["bottom"])

    next_support = None
    for z in supports_sorted[::-1]:
        if z["top"] <= price:
            next_support = z
            break

    next_res = None
    for z in resistances_sorted:
        if z["bottom"] >= price:
            next_res = z
            break

    mom = plan.get("momentum") or {}
    squeeze = mom.get("bb_squeeze", False)
    breakout_watch = mom.get("breakout_watch", False)
    breakout_dir = mom.get("breakout_direction", "NEUTRAL")
    sideways = mom.get("sideways", False)
    spike = mom.get("vol_spike", "NA")

    lines = []
    lines.append("### 4) Next 3 Best Setups (Waiting Phase)")
    lines.append("These are **potential** setups (not active until triggers appear).")
    lines.append("")

    # Setup 1: Support bounce
    if next_support:
        lines.append(
            f"**1) Support Rejection (Bounce Long)** — `{round(next_support['bottom'],2)} → {round(next_support['top'],2)}`\n"
            f"- Trigger: sweep/hold support + bullish candle close + volume confirmation\n"
            f"- Entry style: after reclaim or retest of top of zone\n"
            f"- Invalidate: strong close below zone"
        )
    else:
        lines.append("**1) Support Rejection (Bounce Long)** — No clean support zone detected below price.")

    lines.append("")

    # Setup 2: Resistance rejection
    if next_res:
        lines.append(
            f"**2) Resistance Rejection (Short)** — `{round(next_res['bottom'],2)} → {round(next_res['top'],2)}`\n"
            f"- Trigger: failure to break above + bearish close + volume rejection\n"
            f"- Entry style: retest of bottom of resistance zone\n"
            f"- Invalidate: break & hold above zone"
        )
    else:
        lines.append("**2) Resistance Rejection (Short)** — No clean resistance zone detected above price.")

    lines.append("")

    # Setup 3: Breakout continuation (squeeze-driven)
    if squeeze:
        lines.append(
            f"**3) Squeeze Breakout Continuation** — BB squeeze active\n"
            f"- Expected breakout bias: **{breakout_dir}** (OBV + trend context)\n"
            f"- Trigger: expansion candle close + volume spike (spike now: `{spike}`)\n"
            f"- Confirmation: break → retest → continuation candle\n"
            f"- Avoid: wick fakeout + immediate reclaim into range"
        )
        if breakout_watch:
            lines.append("🚨 **Breakout Watch ON:** squeeze + ignition detected — move can start anytime.")
    else:
        lines.append(
            "**3) Squeeze Breakout Continuation** — No squeeze now.\n"
            "- Alternative: wait for compression (tight range + falling volatility)."
        )

    lines.append("")

    if sideways and not squeeze:
        lines.append("🧊 **Market state:** Dead chop — avoid forcing trades. Let momentum return first.")

    return "\n".join(lines)



def format_trade_plan(symbol: str, plan: dict) -> str:
    direction = plan.get("direction")
    decision = plan.get("decision", "NA")

    bias4h = plan.get("bias_4h")
    bias1h = plan.get("bias_1h")

    funding = plan.get("funding") or {}
    oi = plan.get("open_interest") or {}
    lsr = plan.get("long_short_ratio") or {}
    mom = plan.get("momentum") or {}

    zones = plan.get("zones") or []
    zones_txt = _zone_lines(zones)

    squeeze_txt = f"{mom.get('bb_squeeze', False)} (pctile={mom.get('bb_squeeze_percentile', 'NA')})"

    header = f"""
## 🧠 Trade Plan — {symbol}

### 1) Snapshot
- Decision: **{decision}**
- Price: **{plan.get('price')}**
- Bias: **4H={bias4h} | 1H={bias1h}**
- Momentum: ATR%={mom.get('atr_pct')} | Spike={mom.get('vol_spike')} | Sideways={mom.get('sideways')} | Squeeze={squeeze_txt} | BreakoutWatch={mom.get('breakout_watch')}
- Derivatives: Funding={funding.get('fundingBps','NA')} bps | OI={oi.get('openInterest','NA')} | L/S={lsr.get('longShortRatio','NA')}

### 2) Key Zones
{zones_txt}
""".strip()

    # WAIT/WATCH mode
    if direction == "WAIT":
        return (
            header
            + "\n\n### 3) Execution\n- Direction: **WAIT**\n- No entry yet — conditions not valid.\n\n"
            + _next_setup_map(plan)
        )

    # TRADE mode
    entry = plan.get("entry")
    stop = plan.get("stop")
    t1 = plan.get("target1")
    t2 = plan.get("target2")
    rr = plan.get("rr")

    if direction == "LONG":
        invalidation = f"Break & close BELOW {stop}"
    else:
        invalidation = f"Break & close ABOVE {stop}"

    trade_block = f"""
### 3) Execution (Locked)
- Direction: **{direction}**
- Entry: **{entry}**
- Stop: **{stop}**
- Targets: **{t1} / {t2}**
- RR (to T1): **{rr}**
- Invalidation: **{invalidation}**
""".strip()

    return header + "\n\n" + trade_block
