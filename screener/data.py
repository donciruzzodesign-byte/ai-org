from typing import Optional
import yfinance as yf
import pandas as pd


def fetch_ohlcv(ticker: str, period: str = "1y") -> pd.DataFrame:
    t = yf.Ticker(ticker)
    df = t.history(period=period)
    if df.empty:
        raise ValueError(f"No data for ticker: {ticker}")
    df.index = df.index.tz_convert(None)
    return df[["Open", "High", "Low", "Close", "Volume"]]


def fetch_fundamentals(ticker: str) -> dict:
    t = yf.Ticker(ticker)
    info = t.info
    return {
        "per": info.get("trailingPE"),
        "pbr": info.get("priceToBook"),
        "equity_ratio": _calc_equity_ratio(info),
        "market_cap": info.get("marketCap"),
    }


def _calc_equity_ratio(info: dict) -> Optional[float]:
    equity = info.get("totalStockholderEquity")
    assets = info.get("totalAssets")
    if equity is not None and assets and assets > 0:
        return round(equity / assets * 100, 2)
    return None


def fetch_vix() -> float:
    t = yf.Ticker("^VIX")
    df = t.history(period="1d")
    if df.empty:
        raise ValueError("Could not fetch VIX")
    return float(df["Close"].iloc[-1])
