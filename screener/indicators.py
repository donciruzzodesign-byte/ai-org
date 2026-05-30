import pandas as pd
import ta


def add_indicators(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    close = df["Close"]

    df["ma5"] = ta.trend.SMAIndicator(close=close, window=5).sma_indicator()
    df["ma25"] = ta.trend.SMAIndicator(close=close, window=25).sma_indicator()
    df["ma75"] = ta.trend.SMAIndicator(close=close, window=75).sma_indicator()

    bb = ta.volatility.BollingerBands(close=close, window=20, window_dev=2)
    df["bb_upper"] = bb.bollinger_hband()
    df["bb_mid"] = bb.bollinger_mavg()
    df["bb_lower"] = bb.bollinger_lband()

    df["rsi"] = ta.momentum.RSIIndicator(close=close, window=14).rsi()

    macd = ta.trend.MACD(close=close, window_slow=26, window_fast=12, window_sign=9)
    df["macd"] = macd.macd()
    df["macd_signal"] = macd.macd_signal()
    df["macd_hist"] = macd.macd_diff()

    return df


def is_bb_breakout(df: pd.DataFrame) -> dict:
    latest = df.iloc[-1]
    return {
        "upper": bool(latest["Close"] > latest["bb_upper"]),
        "lower": bool(latest["Close"] < latest["bb_lower"]),
    }


def is_golden_cross(df: pd.DataFrame) -> bool:
    if len(df) < 2:
        return False
    prev = df.iloc[-2]
    curr = df.iloc[-1]
    return bool(prev["ma25"] <= prev["ma75"] and curr["ma25"] > curr["ma75"])
