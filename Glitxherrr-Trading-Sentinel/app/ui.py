# ===============================
# ui.py — Glitxherrr’s Trading Sentinel
# PART 1 / 3
# ===============================



import streamlit as st
import pandas as pd
from datetime import datetime

from core.config import DEFAULT_EXCHANGE
from core.ollama_agent import OllamaAgent
from core.multi_asset import compare_assets
from core.plan_formatter import format_trade_plan

from data.dxy import dxy_detector
from data.news import fetch_important_news
from data.macro_calendar import upcoming_events
from data.gold_news import fetch_gold_news
from core.market_state import build_market_state
from core.constraints import build_constraints
from core.state_diff import diff_market_state
from core.snapshot_store import load_snapshot, save_snapshot
from core.snapshot_store import format_ist_time
from data.macro_data import fetch_dxy_ohlcv
from core.structure_engine import detect_structure_state
from core.derivatives_bias import compute_derivatives_bias
from core.dxy_bias import compute_dxy_bias
from data.macro_calendar import fetch_macro_events
import copy
from core.macro_impact import macro_tailwind
from core.exhaustion import detect_exhaustion
import sys









# ---------------- Page Config ----------------
st.set_page_config(
    page_title="Glitxher’s Trading Sentinel",
    page_icon="🧠",
    layout="wide"
)




st.title("Glitxher’s Trading Sentinel")
st.caption("(Deterministic Trading Engine).")

agent = OllamaAgent(model="llama3.1:8b")



# ---------------- Sidebar ----------------
with st.sidebar:
    st.subheader("Settings")

    exchange = st.text_input("Exchange", DEFAULT_EXCHANGE)

    asset1 = st.text_input("Asset 1", "BTC/USDT").upper().strip()
    asset2 = st.text_input("Asset 2", "PAXG/USDT").upper().strip()

    st.write("Timeframes used internally: 15m / 1h / 4h")

    st.divider()
    st.subheader("Refresh")

    if st.button("🔄 Refresh Now"):
        st.rerun()


# ---------------- Helpers ----------------
def safe_float(x, default=None):
    try:
        if x is None:
            return default
        return float(x)
    except Exception:
        return default
    


def zone_fmt(z):
    if not z:
        return "NA"
    return f"{round(z['bottom'], 2)} → {round(z['top'], 2)}"


def nearest_watch_zones(plan: dict):
    """
    If price is INSIDE a zone, that zone still shows.
    """
    price = plan.get("price")
    zones = plan.get("zones") or []

    if price is None or not zones:
        return None, None

    supports = [z for z in zones if z.get("type") == "support"]
    resistances = [z for z in zones if z.get("type") == "resistance"]

    supports_inside = [z for z in supports if z["bottom"] <= price <= z["top"]]
    supports_below = [z for z in supports if z["top"] <= price]

    if supports_inside:
        support_zone = supports_inside[0]
    elif supports_below:
        support_zone = sorted(
            supports_below, key=lambda z: abs(price - z["top"])
        )[0]
    else:
        support_zone = None

    resist_inside = [z for z in resistances if z["bottom"] <= price <= z["top"]]
    resist_above = [z for z in resistances if z["bottom"] >= price]

    if resist_inside:
        resistance_zone = resist_inside[0]
    elif resist_above:
        resistance_zone = sorted(
            resist_above, key=lambda z: abs(z["bottom"] - price)
        )[0]
    else:
        resistance_zone = None

    return support_zone, resistance_zone


def color_label(text: str) -> str:
    if "Bullish" in text:
        return f"<span style='color:#00c853;font-weight:800'>{text}</span>"
    if "Bearish" in text:
        return f"<span style='color:#ff1744;font-weight:800'>{text}</span>"
    return f"<span style='color:white;font-weight:700'>{text}</span>"


def colored_metric(col, title: str, value, label: str):
    col.metric(title, value)
    col.markdown(color_label(label), unsafe_allow_html=True)

def news_bias_label(title: str):
    """
    Classifies news headline impact.
    This is NOT prediction — it's reaction guidance.
    """
    t = title.lower()

    if any(k in t for k in ["rate hike", "hawkish", "inflation surge", "tightening"]):
        return "❌ Bearish (risk-off pressure)"

    if any(k in t for k in ["rate cut", "easing", "dovish", "liquidity"]):
        return "✅ Bullish (liquidity tailwind)"

    if any(k in t for k in ["etf approved", "regulatory clarity", "institutional adoption"]):
        return "✅ Bullish"

    if any(k in t for k in ["hack", "exploit", "lawsuit", "ban", "crackdown"]):
        return "❌ Bearish"

    return "🟡 Wait — let price confirm"

def filter_news_for_asset(news_items, asset: str):
    asset = asset.upper()

    if asset.startswith("BTC"):
        keywords = [
            "bitcoin", "btc", "crypto", "cryptocurrency",
            "etf", "sec", "regulation", "miner",
            "hashrate", "on-chain", "binance", "coinbase"
        ]
    elif asset.startswith("PAXG") or asset.startswith("XAU"):
        keywords = [
            "gold", "xau", "bullion",
            "usd", "dollar", "dxy",
            "fed", "fomc", "rates",
            "inflation", "cpi", "yield"
        ]
    else:
        return []

    out = []
    for n in news_items:
        title = (n.get("title") or "").lower()
        if any(k in title for k in keywords):
            out.append(n)

    return out

def clean_title(title: str) -> str:
    """
    Cleans malformed / broken CryptoPanic headlines.
    Prevents vertical text, excessive spacing, emojis issues.
    """
    if not title:
        return "Unknown headline"

    # Collapse weird spacing / line breaks
    title = " ".join(str(title).split())

    # Guard against absurd malformed titles
    if len(title) > 300:
        title = title[:300] + "…"

    return title

def exhaustion_color(exh):

    if not isinstance(exh, dict):
        return "⚪ UNKNOWN"

    state = exh["state"]
    score = exh["score"]

    if state == "HEALTHY":
        return f"🟢 {state} ({score})"

    if state == "NEUTRAL":
        return f"🟡 {state} ({score})"

    if state == "WEAKENING":
        return f"🔴 {state} ({score})"

    return f"⚪ {state} ({score})"



def gold_news_bias(title: str):
    t = title.lower()

    if any(k in t for k in ["rate hike", "hawkish", "strong dollar", "bond yields rise"]):
        return "❌ Bearish (gold pressure)"

    if any(k in t for k in ["rate cut", "dovish", "weak dollar", "recession fears"]):
        return "✅ Bullish (gold tailwind)"

    return "🟡 Wait — macro dependent"

GOLD_KEYWORDS = [
    "gold", "xau", "bullion",
    "dollar", "usd", "dxy",
    "fed", "fomc", "interest rate", "rates",
    "yield", "bond",
    "inflation", "cpi", "pce",
    "recession", "slowdown",
    "safe haven", "risk-off"
]

EXCLUDE_KEYWORDS = [
    "oil", "crude", "gas", "lng",
    "energy", "electric", "power",
    "shipping", "tanker"
]


def is_gold_relevant(title: str) -> bool:
    t = title.lower()

    if any(x in t for x in EXCLUDE_KEYWORDS):
        return False

    return any(k in t for k in GOLD_KEYWORDS)



def rolling_correlation(df_a, df_b, window=50):
    """
    Correlation of % returns between two assets
    """
    ret_a = df_a["close"].pct_change()
    ret_b = df_b["close"].pct_change()

    corr = ret_a.rolling(window).corr(ret_b)

    return float(corr.iloc[-1])




# ----------- Sentiment Classifiers -----------
def label_funding(fbps):
    fbps = safe_float(fbps, None)
    if fbps is None:
        return "NA", "🟡 Medium"
    if fbps > 8:
        return f"{fbps:.3f}", "⚠️ Crowded longs"
    if fbps < -8:
        return f"{fbps:.3f}", "⚠️ Crowded shorts"
    if fbps > 0:
        return f"{fbps:.3f}", "🟡 Longs paying"
    if fbps < 0:
        return f"{fbps:.3f}", "🟡 Shorts paying"
    return f"{fbps:.3f}", "🟡 Neutral"


def label_oi(oi):
    oi = safe_float(oi, None)
    if oi is None:
        return "NA", "🟡 Medium"
    return f"{oi:.3f}", "🟡 Open interest present"


def label_lsr(ratio):
    ratio = safe_float(ratio, None)
    if ratio is None:
        return "NA", "🟡 Medium"
    if ratio >= 2.0:
        return f"{ratio:.3f}", "⚠️ Crowded longs"
    if ratio <= 0.6:
        return f"{ratio:.3f}", "⚠️ Crowded shorts"
    if 0.95 <= ratio <= 1.05:
        return f"{ratio:.3f}", "🟡 Medium (balanced)"
    return f"{ratio:.3f}", "🟡 Medium"


def label_atr(atrp):
    atrp = safe_float(atrp, None)
    if atrp is None:
        return "NA", "🟡 Medium"
    if atrp >= 0.30:
        return f"{atrp:.4f}", "🟡 Expanding volatility"
    if atrp < 0.18:
        return f"{atrp:.4f}", "🟡 Contracting volatility"
    return f"{atrp:.4f}", "🟡 Normal"


def label_vol_spike(vs):
    vs = safe_float(vs, None)
    if vs is None:
        return "NA", "🟡 Medium"
    if vs >= 1.6:
        return f"{vs:.3f}", "✅ Bullish (ignition)"
    if vs >= 1.2:
        return f"{vs:.3f}", "🟡 Medium (building)"
    if vs >= 0.7:
        return f"{vs:.3f}", "🟡 Medium (low vol)"
    return f"{vs:.3f}", "❌ Bearish (dead)"


def overall_outlook(plan: dict):
    score = 0.0

    b4 = plan.get("bias_4h")
    b1 = plan.get("bias_1h")
    decision = plan.get("decision", "WATCH")

    mom = plan.get("momentum") or {}
    mscore = safe_float(mom.get("momentum_score"), 0) or 0

    lsr = plan.get("long_short_ratio") or {}
    ratio = safe_float(lsr.get("longShortRatio"), None)

    funding = plan.get("funding") or {}
    fbps = safe_float(funding.get("fundingBps"), None)

    if b4 == "Bullish":
        score += 2
    elif b4 == "Bearish":
        score -= 2

    if b1 == "Bullish":
        score += 1
    elif b1 == "Bearish":
        score -= 1

    score += max(-3, min(3, mscore / 3))

    if decision == "TRADE":
        score += 2
    elif decision == "AVOID":
        score -= 2

    if ratio is not None and ratio >= 2.0:
        score -= 2
    if ratio is not None and ratio <= 0.6:
        score -= 2

    if fbps is not None and abs(fbps) >= 10:
        score -= 1

    if score >= 3:
        return "✅ Bullish"
    if score <= -3:
        return "❌ Bearish"
    return "🟡 Medium"


# ---------------- Macro (DXY) ----------------
st.divider()
st.subheader("🌍 Macro Filter — DXY")

try:
    # ---- Macro momentum / pressure ----
    dxy = dxy_detector(interval="1h")

    if not isinstance(dxy, dict):
        raise ValueError("Invalid DXY detector output")

    # ---- Real OHLC for structure (4H) ----
    df_dxy_4h = fetch_dxy_ohlcv(interval="4h")

    # Clean inputs for structure engine
    df_dxy_4h = df_dxy_4h[["open", "high", "low", "close", "volume"]]

    # ---- Detect structure ----
    dxy_structure = detect_structure_state(df_dxy_4h)

    # ---- Macro metrics ----
    col1, col2, col3 = st.columns(3)

    col1.metric("DXY", round(float(dxy.get("last", 0)), 2))
    col2.metric("Trend", dxy.get("trend", "NA"))
    col3.metric("Strength", dxy.get("strength", "NA"))

    st.info(dxy.get("note", "No macro note available"))

    # ---- Save structure for unified panel ----
    dxy_struct = dxy_structure if isinstance(dxy_structure, dict) else None

except Exception as e:
    st.warning(f"DXY data unavailable: {e}")
    dxy_struct = None




 
      # ================= SAFE NEWS FETCH =================

try:
    btc_news = fetch_important_news(limit=8)
    if not isinstance(btc_news, list):
        btc_news = []
except Exception:
    btc_news = []
    st.warning("BTC news temporarily unavailable")

try:
    gold_news = fetch_gold_news(limit=8)
    if not isinstance(gold_news, list):
        gold_news = []
except Exception:
    gold_news = []
    st.warning("Gold news temporarily unavailable")


# ================= NEWS DASHBOARD =================
st.divider()
st.subheader("")

col1, col2 = st.columns(2)


# -------- BTC / CRYPTO NEWS --------
with col1:

    st.markdown("### ₿ BTC / Crypto — News")

    if len(btc_news) == 0:
        st.info("🟡 No BTC news right now")

    else:
        for n in btc_news[:8]:

            title  = n.get("title", "Untitled")
            source = n.get("source", "Unknown")

            title_l = title.lower()

            # --- Bias dot ---
            bias_dot = "⚪"

            if any(k in title_l for k in [
                "etf inflow", "approval", "accumulate", "record high",
                "buying", "breakout", "rally", "surge"
            ]):
                bias_dot = "🟢"

            elif any(k in title_l for k in [
                "hack", "outflow", "crash", "dump", "lawsuit",
                "ban", "liquidation", "selloff"
            ]):
                bias_dot = "🔴"

            st.markdown(f"{bias_dot} {title}")
            st.caption(source)


# -------- GOLD / MACRO NEWS --------
with col2:

    st.markdown("### 🥇 Gold / USD / Rates — News")

    if len(gold_news) == 0:

        # ---- Macro fallback when no gold headlines ----
        if isinstance(dxy, dict):

            usd_trend = dxy.get("trend", "NEUTRAL")

            if usd_trend == "UP":
                macro_effect = "headwind"
            elif usd_trend == "DOWN":
                macro_effect = "tailwind"
            else:
                macro_effect = "neutral flow"

            st.info(
                "🟡 No fresh gold-relevant headlines.\n\n"
                f"Last macro bias: **USD {usd_trend}** → {macro_effect} for Gold.\n\n"
                "Bias: **WAIT — price confirmation required**"
            )

        else:
            st.info(
                "🟡 No fresh gold-relevant headlines.\n\n"
                "Macro context unavailable.\n\n"
                "Bias: **WAIT — let price action lead**"
            )

    else:

        for n in gold_news[:8]:

            title  = n.get("title", "Untitled")
            source = n.get("source", "Unknown")

            title_l = title.lower()

            bias_dot = "⚪"

            if any(k in title_l for k in [
                "safe haven demand", "record high", "gold jumps",
                "gold surges", "strong demand"
            ]):
                bias_dot = "🟢"

            elif any(k in title_l for k in [
                "rate hike", "strong dollar", "gold falls",
                "gold drops", "selloff"
            ]):
                bias_dot = "🔴"

            st.markdown(f"{bias_dot} {title}")
            st.caption(source)


# ===== END PART 1 =====


# ===============================
# ui.py — Glitxherrr’s Trading Sentinel
# PART 2 / 3
# ===============================

# ---------------- Terminal ----------------

st.divider()
st.subheader("")

cmp = None

try:
    with st.spinner("Fetching + derivatives data..."):
        cmp = compare_assets(exchange, asset1, asset2)

    plan_a = cmp["plan_a"]
    plan_b = cmp["plan_b"]

    # ================= ACTIVE SYMBOL SELECTION =================

    asset1 = cmp["asset_a"]
    asset2 = cmp["asset_b"]

    selected_symbol = cmp.get("winner")

    # ---- Safe fallback (never crash UI) ----
    if selected_symbol not in (asset1, asset2):
        selected_symbol = asset1

    selected_plan = plan_a if selected_symbol == asset1 else plan_b


    # -------- Summary Table --------

    st.markdown("### 🧾 Quick Summary (Watchlist Table)")

    rows = []

    for sym, plan, score in [
        (asset1, plan_a, cmp["score_a"]),
        (asset2, plan_b, cmp["score_b"]),
    ]:

        mom = plan.get("momentum") or {}
        funding = plan.get("funding") or {}
        oi = plan.get("open_interest") or {}
        lsr = plan.get("long_short_ratio") or {}

        ns, nr = nearest_watch_zones(plan)

        rows.append({
            "Asset": sym,
            "Decision": plan.get("decision", "NA"),
            "Overall Outlook": overall_outlook(plan),
            "Funding (bps)": funding.get("fundingBps", "NA"),
            "Open Interest": oi.get("openInterest", "NA"),
            "Long/Short Ratio": lsr.get("longShortRatio", "NA"),
            "ATR%": mom.get("atr_pct", "NA"),
            "Vol Spike": mom.get("vol_spike", "NA"),
            "Sideways": mom.get("sideways", False),
            "BB Squeeze": mom.get("bb_squeeze", False),
            "Next Support": zone_fmt(ns),
            "Next Resistance": zone_fmt(nr),
            "HTF Bias": plan.get("bias_4h", "NA"),
            "1H Bias": plan.get("bias_1h", "NA"),
            "Score": score,
        })

    st.dataframe(pd.DataFrame(rows), use_container_width=True)
    st.caption(f"Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")


    # -------- Metric Panels --------
    st.divider()
    col1, col2 = st.columns(2)

    def show_asset_panel(col, name, plan, score):

        funding = plan.get("funding") or {}
        oi = plan.get("open_interest") or {}
        lsr = plan.get("long_short_ratio") or {}
        mom = plan.get("momentum") or {}

        col.markdown(f"## {name}")

        col.metric("Price", f"{plan.get('price', 0):.2f}")
        col.metric("Decision", plan.get("decision", "NA"))
        col.metric("Overall Outlook", overall_outlook(plan))
        col.metric("HTF Bias", plan.get("bias_4h", "NA"))
        col.metric("1H Bias", plan.get("bias_1h", "NA"))

        f_val, f_lab = label_funding(funding.get("fundingBps"))
        colored_metric(col, "Funding (bps)", f_val, f_lab)

        oi_val, oi_lab = label_oi(oi.get("openInterest"))
        colored_metric(col, "Open Interest", oi_val, oi_lab)

        lsr_val, lsr_lab = label_lsr(lsr.get("longShortRatio"))
        colored_metric(col, "Long/Short Ratio", lsr_val, lsr_lab)

        atr_val, atr_lab = label_atr(mom.get("atr_pct"))
        colored_metric(col, "ATR%", atr_val, atr_lab)

        vs_val, vs_lab = label_vol_spike(mom.get("vol_spike"))
        colored_metric(col, "Vol Spike", vs_val, vs_lab)

        col.metric("Sideways?", str(mom.get("sideways", False)))
        col.metric("BB Squeeze?", str(mom.get("bb_squeeze", False)))
        col.metric("Squeeze %tile", mom.get("bb_squeeze_percentile", "NA"))
        col.metric("Breakout Watch", str(mom.get("breakout_watch", False)))
        col.metric("Breakout Direction", mom.get("breakout_direction", "NA"))
        col.metric("Score", score)
        


    show_asset_panel(col1, asset1, plan_a, cmp["score_a"])
    show_asset_panel(col2, asset2, plan_b, cmp["score_b"])

    st.success(
        f"✅ Better chances now: **{cmp['winner']}** (stable scoring + filters)"
    )


except Exception as e:
    st.warning(f"Terminal unavailable: {e}")


    

# ===== END PART 2 =====


# ===============================
# ui.py — Glitxherrr’s Trading Sentinel
# PART 3 / 3
# ===============================

# ---------------- Alerts Scanner ----------------
st.divider()
st.subheader("🚨 Watchlist Alerts Scanner (Support/Resistance + Next Trades)")

def setup_suggestions(plan: dict):
    zones = plan.get("zones") or []
    price = plan.get("price")

    if not zones or price is None:
        return ["No zones available."]

    supports = [z for z in zones if z.get("type") == "support"]
    resists  = [z for z in zones if z.get("type") == "resistance"]

    supports = sorted(supports, key=lambda z: z["top"], reverse=True)
    resists  = sorted(resists, key=lambda z: z["bottom"])

    ideas = []

    if supports:
        s = supports[0]
        ideas.append(
            f"🟢 Support Bounce Long — {zone_fmt(s)} | Trigger: sweep + reclaim + volume"
        )

    if resists:
        r = resists[0]
        ideas.append(
            f"🔴 Resistance Rejection Short — {zone_fmt(r)} | Trigger: rejection candle + volume"
        )

    ideas.append(
        "⚡ Breakout setup — only if squeeze + volume ignition appears "
        "(follow breakout direction)."
    )

    return ideas


if cmp is None:
    st.info("No scanner output available.")

else:
    col1, col2 = st.columns(2)

    assets = [
        (asset1, cmp["plan_a"]),
        (asset2, cmp["plan_b"]),
    ]

    for col, (sym, plan) in zip([col1, col2], assets):

        with col:

            ns, nr = nearest_watch_zones(plan)
            mom = plan.get("momentum") or {}

            st.markdown(f"### {sym}")

            st.markdown(f"**📌 Next Support:** {zone_fmt(ns)}")
            st.markdown(f"**📌 Next Resistance:** {zone_fmt(nr)}")

            st.markdown(
                f"**Decision:** {plan.get('decision')}  \n"
                f"**Breakout Watch:** {mom.get('breakout_watch')}  \n"
                f"**Sideways:** {mom.get('sideways')}"
            )

            # ---- DXY Macro Warnings ----
            if dxy is not None:

                if sym.upper().startswith("PAXG") and dxy["trend"] == "UP":
                    st.warning("⚠️ DXY rising → Gold fakeout / dump risk")

                if sym.upper().startswith("BTC") and dxy["trend"] == "UP":
                    st.warning("⚠️ DXY rising → BTC pullback / squeeze risk")

            # ---- Trade State ----
            if plan.get("decision") == "TRADE":
                st.markdown("**Active trade setups:**")
            else:
                st.markdown("**Next setups (waiting):**")

            for idea in setup_suggestions(plan):
                st.markdown(f"- {idea}")

            # ---- Reminders ----
            if sym.upper().startswith("PAXG"):
                st.info("Gold reacts strongly to USD, yields, CPI, FOMC")

            if sym.upper().startswith("BTC"):
                st.info("BTC reacts to ETF flows, regulation, liquidity news")

            # ================= MARKET STRUCTURE (4H) =================
st.divider()
st.subheader("📐 Market Structure (4H)")

# ---- Identify BTC & PAXG plans safely ----

btc_plan  = cmp["plan_a"] if "BTC" in cmp["asset_a"] else cmp["plan_b"]
paxg_plan = cmp["plan_b"] if btc_plan == cmp["plan_a"] else cmp["plan_a"]

btc_struct  = btc_plan.get("structure_state") if isinstance(btc_plan, dict) else None
paxg_struct = paxg_plan.get("structure_state") if isinstance(paxg_plan, dict) else None
dxy_struct = dxy_structure if "dxy_structure" in locals() else None



# ---------------- Display Helper ----------------

def show_structure(name: str, struct: dict | None):

    st.markdown(f"### {name}")

    if not isinstance(struct, dict):
        st.write("No structure data")
        return

    trend = struct.get("trend", "Unknown")
    state = struct.get("state", "Unknown")

    sweep_dir   = struct.get("liquidity_sweep")
    sweep_price = struct.get("sweep_price")

    bos_dir   = struct.get("break_of_structure")
    bos_price = struct.get("bos_price")

    st.write("Trend:", trend)
    st.write("State:", state)

    # ---- Sweep display ----
    if sweep_dir:
        st.write("Sweep:", f"{sweep_dir} @ {round(float(sweep_price), 2)}")
    else:
        st.write("Sweep:", "None")

    # ---- BOS display ----
    if bos_dir:
        st.write("BOS:", f"{bos_dir} @ {round(float(bos_price), 2)}")
    else:
        st.write("BOS:", "None")


# ---------------- Render (SIDE BY SIDE) ----------------

col_btc, col_paxg, col_dxy = st.columns(3)

with col_btc:
    show_structure("₿ BTC/USDT", btc_struct)

with col_paxg:
    show_structure("🟡 PAXG/USDT", paxg_struct)

with col_dxy:
    show_structure("💵 DXY", dxy_struct)




def build_asset_state(plan, asset_name, dxy_state):

    # ---- Core price context ----
    structure = plan.get("structure_state") if isinstance(plan, dict) else None
    momentum  = plan.get("momentum") if isinstance(plan, dict) else None

    # ---- Trend exhaustion ----
    exhaustion = detect_exhaustion(momentum, structure)

    # ---- Derivatives context ----
    derivatives = {
        "funding": plan.get("funding"),
        "open_interest": plan.get("open_interest"),
        "long_short_ratio": plan.get("long_short_ratio"),
    }

    # ---- Macro tailwind / headwind ----
    dxy_trend = None
    dxy_strength = None

    if isinstance(dxy_state, dict):
        dxy_trend = dxy_state.get("trend")
        dxy_strength = dxy_state.get("strength")

    macro_effect = macro_tailwind(
        asset_name,
        dxy_trend,
        dxy_strength
    )

    # ---- Build final asset state ----
    return {
        "structure": structure,
        "momentum": momentum,
        "derivatives": derivatives,
        "exhaustion": exhaustion,

        # ---- Combined derivatives pressure ----
        "derivatives_bias": compute_derivatives_bias(
            structure,
            momentum,
            derivatives
        ),

        # ---- Macro context (tailwind / headwind / neutral) ----
        "macro_effect": macro_effect,

        # ---- Timeframe bias ----
        "bias": {
            "htf": plan.get("bias_4h"),
            "ltf": plan.get("bias_1h"),
        }
    }


def build_dxy_state(dxy_data, dxy_structure):

    if not isinstance(dxy_data, dict):
        return None

    trend = (
        dxy_data.get("trend").upper()
        if dxy_data.get("trend")
        else None
    )

    strength = (
        dxy_data.get("strength").upper()
        if dxy_data.get("strength")
        else None
    )

    return {
        "structure": dxy_structure,
        "trend": trend,
        "strength": strength,

        # ---- Synthesized macro bias ----
        "bias": compute_dxy_bias(
            dxy_structure,
            trend,
            strength
        )
    }


# ================= BUILD MARKET STATE =================

dxy_state = build_dxy_state(
    dxy,
    dxy_structure if "dxy_structure" in locals() else None
)

market_state = {
    "dxy": dxy_state,

    "btc": build_asset_state(
        btc_plan,
        "BTC",
        dxy_state
    ),

    "paxg": build_asset_state(
        paxg_plan,
        "PAXG",
        dxy_state
    )
}

# ================= CONSTRAINTS =================

constraints = build_constraints(market_state)
market_state["constraints"] = constraints

last_state = st.session_state.get("last_market_state")

# ================= SMART EXHAUSTION ALERTS =================

for asset in ["btc", "paxg"]:

    ex = market_state[asset]["exhaustion"]
    macro = market_state[asset]["macro_effect"]

    if ex == "WEAKENING":
        st.warning(f"⚠️ {asset.upper()} trend weakening — pullback risk rising")

    if ex == "COMPRESSION":
        st.info(f"⚡ {asset.upper()} volatility compression — breakout or reversal soon")

    if macro == "HEADWIND":
        st.warning(f"🌪 {asset.upper()} facing macro pressure")




# ================= SNAPSHOT + DIFF =================

last_state = st.session_state.get("last_market_state")
last_timestamp = None

if last_state is None:
    snapshot_payload = load_snapshot()
    if snapshot_payload:
        last_state = snapshot_payload.get("state")
        last_timestamp = snapshot_payload.get("timestamp")

st.session_state["last_market_state"] = copy.deepcopy(market_state)
save_snapshot(market_state)

market_state["last_snapshot_time"] = last_timestamp
market_state["state_diff"] = diff_market_state(last_state, market_state)





# ================= TREND HEALTH =================

st.divider()    
st.subheader("📉 Trend Health")

c1, c2 = st.columns(2)

with c1:
    st.markdown(f"**BTC Trend State**  \n{market_state['btc']['exhaustion']}")

with c2:
    st.markdown(f"**PAXG Trend State**  \n{market_state['paxg']['exhaustion']}")


# ================= BIAS SUMMARY =================

st.divider()
st.subheader("📊 Derivatives Bias")

col1, col2, col3 = st.columns(3)

with col1:
    st.markdown(
        f"**BTC Derivatives Bias**  \n{market_state['btc']['derivatives_bias']}"
    )
    st.caption(f"Macro: {market_state['btc']['macro_effect']}")

with col2:
    st.markdown(
        f"**PAXG Derivatives Bias**  \n{market_state['paxg']['derivatives_bias']}"
    )
    st.caption(f"Macro: {market_state['paxg']['macro_effect']}")

with col3:
    st.markdown(
        f"**DXY Bias**  \n{market_state['dxy']['bias']}"
    )




# ================= CHAT (NOW BELOW BIAS) =================

st.divider()
st.subheader("💬 Chat")

if "messages" not in st.session_state:
    st.session_state.messages = []

# Render history
for msg_obj in st.session_state.messages:
    with st.chat_message(msg_obj["role"]):
        st.markdown(msg_obj["content"])

# Input
user_input = st.chat_input(
    "Ask: btc plan | paxg funding | compare | next setup"
)


# ================= HANDLE INPUT =================

if user_input:

    st.session_state.messages.append(
        {"role": "user", "content": user_input}
    )

    with st.chat_message("user"):
        st.markdown(user_input)

    with st.chat_message("assistant"):
        with st.spinner("Analyzing assets..."):

            if cmp is None:
                cmp = compare_assets(exchange, asset1, asset2)

            mentor = agent.think(user_input, market_state)

            st.markdown(mentor)

            st.session_state.messages.append(
                {"role": "assistant", "content": mentor}
            )
