import requests


BINANCE_FAPI = "https://fapi.binance.com"


def to_binance_symbol(symbol: str) -> str:
    return symbol.replace("/", "").upper()


def get_funding_rate(symbol: str):
    """
    ✅ Reliable funding snapshot using Premium Index.
    Returns latest funding rate (lastFundingRate) + nextFundingTime.
    """
    s = to_binance_symbol(symbol)
    url = f"{BINANCE_FAPI}/fapi/v1/premiumIndex"
    params = {"symbol": s}

    r = requests.get(url, params=params, timeout=20)
    r.raise_for_status()
    data = r.json()

    # lastFundingRate is string
    fr = data.get("lastFundingRate") or data.get("fundingRate")
    if fr is None:
        return None

    fr = float(fr)
    return {
        "fundingRate": fr,
        "fundingBps": round(fr * 10000, 3),  # ✅ bps
        "nextFundingTime": int(data.get("nextFundingTime", 0)),
        "markPrice": float(data.get("markPrice", 0)) if data.get("markPrice") else None,
    }


def get_open_interest(symbol: str):
    """
    Returns current open interest for Binance USDT-M perpetual.
    """
    s = to_binance_symbol(symbol)
    url = f"{BINANCE_FAPI}/fapi/v1/openInterest"
    params = {"symbol": s}

    r = requests.get(url, params=params, timeout=20)
    r.raise_for_status()
    data = r.json()

    return {
        "openInterest": float(data["openInterest"]),
    }


def get_global_long_short_ratio(symbol: str, period: str = "15m", limit: int = 1):
    """
    Global Account Long/Short Ratio (Binance Futures).
    period: 5m, 15m, 30m, 1h, 2h, 4h, 6h, 12h, 1d
    """
    s = to_binance_symbol(symbol)
    url = f"{BINANCE_FAPI}/futures/data/globalLongShortAccountRatio"
    params = {"symbol": s, "period": period, "limit": limit}

    r = requests.get(url, params=params, timeout=20)
    r.raise_for_status()
    data = r.json()

    if not data:
        return None

    item = data[-1]
    return {
        "longShortRatio": float(item["longShortRatio"]),
        "longAccount": float(item["longAccount"]),
        "shortAccount": float(item["shortAccount"]),
    }


def fetch_derivatives_snapshot(symbol: str):
    """
    Unified snapshot so your core engine can use:
    plan["funding"]["fundingBps"]
    plan["open_interest"]["openInterest"]
    plan["long_short_ratio"]["longShortRatio"]
    """
    snap = {}

    # funding
    try:
        fr = get_funding_rate(symbol)
        snap["funding"] = fr if fr else {"fundingBps": None}
    except Exception as e:
        snap["funding"] = {"fundingBps": None, "error": str(e)}

    # open interest
    try:
        oi = get_open_interest(symbol)
        snap["open_interest"] = oi if oi else {"openInterest": None}
    except Exception as e:
        snap["open_interest"] = {"openInterest": None, "error": str(e)}

    # long/short ratio
    try:
        lsr = get_global_long_short_ratio(symbol, period="15m", limit=1)
        snap["long_short_ratio"] = lsr if lsr else {"longShortRatio": None}
    except Exception as e:
        snap["long_short_ratio"] = {"longShortRatio": None, "error": str(e)}

    return snap
