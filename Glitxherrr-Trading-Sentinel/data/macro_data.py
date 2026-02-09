import yfinance as yf
import pandas as pd


def fetch_dxy_ohlcv(interval="4h", limit=400):

    ticker = yf.Ticker("DX-Y.NYB")

    # Map intervals
    tf_map = {
        "1h": "1h",
        "4h": "4h",
        "1d": "1d"
    }

    tf = tf_map.get(interval, "4h")

    df = ticker.history(period="60d", interval=tf)

    if df.empty:
        raise ValueError("No DXY data returned")

    df = df.reset_index()

    df = df.rename(columns={
        "Open": "open",
        "High": "high",
        "Low": "low",
        "Close": "close",
        "Volume": "volume"
    })

    return df.tail(limit)
