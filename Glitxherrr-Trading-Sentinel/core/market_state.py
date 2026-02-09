# ============================================
# market_state.py
# Builds a hallucination-safe Market State Object (MSO)
# ============================================

from typing import Optional


def _atr_regime(atrp: Optional[float]) -> str:
    if atrp is None:
        return "unknown"
    if atrp >= 0.30:
        return "expanding"
    if atrp < 0.18:
        return "contracting"
    return "normal"


def _volume_state(vs: Optional[float]) -> str:
    if vs is None:
        return "unknown"
    if vs >= 1.6:
        return "ignition"
    if vs >= 1.2:
        return "building"
    if vs >= 0.7:
        return "thin"
    return "dead"


def _funding_state(fbps: Optional[float]) -> str:
    if fbps is None:
        return "unknown"
    if fbps > 8:
        return "crowded_longs"
    if fbps < -8:
        return "crowded_shorts"
    if fbps > 0:
        return "positive"
    if fbps < 0:
        return "negative"
    return "neutral"


def _lsr_state(ratio: Optional[float]) -> str:
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


def build_market_state(
    symbol: str,
    plan: dict,
    dxy: Optional[dict] = None,
    news_context: Optional[str] = None,
) -> dict:
    """
    Converts raw plan + macro context into a reasoning-safe Market State Object.

    GUARANTEES:
    - No prices
    - No zones
    - No SL/TP
    - No trade direction
    - No decisions
    """

    # ---------------- RAW INPUTS ----------------
    mom = plan.get("momentum") or {}
    funding = plan.get("funding") or {}
    oi = plan.get("open_interest") or {}
    lsr = plan.get("long_short_ratio") or {}

    atrp = mom.get("atr_pct")
    vol_spike = mom.get("vol_spike")
    fbps = funding.get("fundingBps")
    ratio = lsr.get("longShortRatio")

    # ---------------- STRUCTURE ----------------
    structure = {
        "higher_timeframe_bias": plan.get("bias_4h", "unknown"),
        "intraday_bias": plan.get("bias_1h", "unknown"),
        "base_present": bool(mom.get("sideways")),
        "breakout_watch": bool(mom.get("breakout_watch")),
    }

    # ---------------- MOMENTUM ----------------
    momentum = {
        "atr_regime": _atr_regime(atrp),
        "volume_state": _volume_state(vol_spike),
        "volatility_compression": bool(mom.get("bb_squeeze")),
        "volatility_percentile": mom.get("bb_squeeze_percentile", "NA"),
    }

    # ---------------- DERIVATIVES ----------------
    derivatives = {
        "funding_state": _funding_state(fbps),
        "open_interest_present": oi.get("openInterest") is not None,
        "lsr_state": _lsr_state(ratio),
    }

    # ---------------- MACRO ----------------
    macro = {
        "dxy_trend": dxy.get("trend") if dxy else "unknown",
        "dxy_strength": dxy.get("strength") if dxy else "unknown",
        "macro_event_risk": bool(dxy),
    }

    # ---------------- NEWS ----------------
    news = {
        "recent_context": news_context or "none",
        "news_is_driver": bool(news_context),
    }

    # ---------------- RECENT CHANGES (DELTA) ----------------
    recent_changes = {
        "funding_pressure": (
            "rising" if fbps is not None and fbps > 0 else "neutral_or_falling"
        ),
        "volatility_shift": momentum["atr_regime"],
        "volume_participation": momentum["volume_state"],
        "derivatives_balance": derivatives["lsr_state"],
    }

    # ---------------- FINAL STATE ----------------
    return {
        "asset": symbol,
        "structure": structure,
        "momentum": momentum,
        "derivatives": derivatives,
        "macro": macro,
        "news": news,
        "recent_changes": recent_changes,
    }
