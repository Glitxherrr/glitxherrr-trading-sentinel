import ccxt
import pandas as pd


def get_exchange(name: str = "binance"):
    name = name.lower()
    if not hasattr(ccxt, name):
        raise ValueError(f"Exchange '{name}' not supported in ccxt.")
    exchange_class = getattr(ccxt, name)
    ex = exchange_class({"enableRateLimit": True})
    return ex


def fetch_ohlcv(exchange_name: str, symbol: str, timeframe: str, limit: int = 500) -> pd.DataFrame:
    ex = get_exchange(exchange_name)
    ohlcv = ex.fetch_ohlcv(symbol, timeframe=timeframe, limit=limit)

    df = pd.DataFrame(
        ohlcv,
        columns=["timestamp", "open", "high", "low", "close", "volume"]
    )
    df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
    return df
