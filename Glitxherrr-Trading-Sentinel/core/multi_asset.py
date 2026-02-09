from data.market_data import fetch_ohlcv
from core.trade_planner import build_trade_plan

from core.momentum import (
    momentum_score,          # 4H regime + trend health
    momentum_score_1h        # 1H fast ignition + chop
)

from data.derivatives import fetch_derivatives_snapshot
from core.structure_engine import detect_structure_state


# ============================================================
# Utilities
# ============================================================

def clamp(x, lo, hi):
    return max(lo, min(hi, x))


def safe_float(x, default=None):
    try:
        if x is None:
            return default
        return float(x)
    except Exception:
        return default


# ============================================================
# Decision Engine (FAST triggers + SLOW permission)
# ============================================================

def decision_label(plan: dict) -> str:

    direction = plan.get("direction")

    fast = plan.get("momentum_fast") or {}
    slow = plan.get("momentum_slow") or {}

    sideways = fast.get("sideways", False)
    squeeze = fast.get("bb_squeeze", False)

    atr_pct = safe_float(fast.get("atr_pct"), 0) or 0
    spike = safe_float(fast.get("vol_spike"), 1) or 1

    breakout_watch = slow.get("breakout_watch", False)

    # ---------------- DEAD ZONE ----------------
    if sideways and spike < 0.9 and not squeeze:
        return "AVOID"

    # ---------------- COMPRESSION ----------------
    if squeeze and not breakout_watch:
        return "WATCH"

    # ---------------- IGNITION ----------------
    if breakout_watch:
        return "TRADE"

    # ---------------- TREND CONTINUATION ----------------
    if direction in ("LONG", "SHORT") and atr_pct >= 0.12 and spike >= 1.1:
        return "TRADE"

    return "WATCH"


# ============================================================
# Asset Analyzer
# ============================================================

def analyze_asset(exchange: str, symbol: str):

    # ---------------- Fetch candles ----------------

    df_15m = fetch_ohlcv(exchange, symbol, "15m", limit=400)
    df_1h  = fetch_ohlcv(exchange, symbol, "1h",  limit=400)
    df_4h  = fetch_ohlcv(exchange, symbol, "4h",  limit=400)

    # ---------------- Core trade plan ----------------

    plan = build_trade_plan(symbol, df_15m, df_1h, df_4h)

    # =================================================
    # FAST LAYER (1H) — pressure & ignition
    # =================================================

    mom_fast = momentum_score_1h(df_1h)

    plan["momentum_fast"] = mom_fast

    # =================================================
    # SLOW LAYER (4H) — regime & health
    # =================================================

    mom_slow = momentum_score(df_4h)

    plan["momentum_slow"] = mom_slow

    # =================================================
    # Market Structure (4H only)
    # =================================================

    try:
        structure_state = detect_structure_state(df_4h)
        plan["structure_state"] = structure_state
    except Exception as e:
        plan["structure_state_error"] = str(e)

    # =================================================
    # Derivatives (fast pressure by nature)
    # =================================================

    try:
        snap = fetch_derivatives_snapshot(symbol)
        if isinstance(snap, dict):
            plan.update(snap)

            plan["derivatives_fast"] = {
                "funding": snap.get("funding"),
                "open_interest": snap.get("open_interest"),
                "long_short_ratio": snap.get("long_short_ratio"),
            }
    except Exception as e:
        plan["derivatives_error"] = str(e)

    # =================================================
    # Compatibility layer (for UI + older logic)
    # =================================================
    # This mimics the old "momentum" object but is now explicit

    plan["momentum"] = {
        **mom_slow,
        **mom_fast
    }

    # =================================================
    # Final Decision
    # =================================================

    plan["decision"] = decision_label(plan)

    return plan


# ============================================================
# Scoring Engine
# ============================================================

def score_plan(plan: dict) -> float:

    score = 0.0

    # ---------------- RR reward ----------------

    rr = safe_float(plan.get("rr"), None)
    if rr is not None:
        score += clamp(rr, 0, 4) * 1.5

    # ---------------- Bias alignment ----------------

    b4 = plan.get("bias_4h")
    b1 = plan.get("bias_1h")

    if b4 == b1 and b4 != "Neutral":
        score += 3
    elif b4 != "Neutral":
        score += 1

    # ---------------- Derivatives pressure ----------------

    funding = plan.get("funding") or {}
    fbps = safe_float(funding.get("fundingBps"), None)

    if fbps is not None:
        if -5 <= fbps <= 5:
            score += 1.5
        elif abs(fbps) > 15:
            score -= 2
        elif abs(fbps) > 10:
            score -= 1

    lsr = plan.get("long_short_ratio") or {}
    ratio = safe_float(lsr.get("longShortRatio"), None)

    if ratio is not None:
        if 0.95 <= ratio <= 1.05:
            score += 1.5
        elif ratio > 1.2 or ratio < 0.8:
            score -= 1.0
        elif ratio > 1.8 or ratio < 0.6:
            score -= 2.0

    # ---------------- HTF momentum power ----------------

    slow = plan.get("momentum_slow") or {}
    raw_mom = safe_float(slow.get("momentum_score"), 0) or 0

    score += clamp(raw_mom, -6, 8)

    # ---------------- Decision bias ----------------

    decision = plan.get("decision")

    if decision == "TRADE":
        score += 4
    elif decision == "WATCH":
        score += 0.5
    elif decision == "AVOID":
        score -= 6

    if plan.get("direction") == "WAIT":
        score -= 2

    score = clamp(score, -15, 15)

    return round(score, 2)


# ============================================================
# Asset Comparison
# ============================================================

def compare_assets(exchange: str, a: str, b: str):

    plan_a = analyze_asset(exchange, a)
    plan_b = analyze_asset(exchange, b)

    score_a = score_plan(plan_a)
    score_b = score_plan(plan_b)

    winner = a if score_a > score_b else b

    return {
        "asset_a": a,
        "asset_b": b,
        "plan_a": plan_a,
        "plan_b": plan_b,
        "score_a": score_a,
        "score_b": score_b,
        "winner": winner,
    }
