import pandas as pd
import pytest
from screener.indicators import add_indicators, is_bb_breakout, is_golden_cross


def _make_df(n=100, trend=True):
    close = [100.0 + i * 0.5 for i in range(n)] if trend else [100.0] * n
    return pd.DataFrame({
        "Open": close,
        "High": [c + 2 for c in close],
        "Low": [c - 2 for c in close],
        "Close": close,
        "Volume": [1000] * n,
    })


def test_add_indicators_adds_columns():
    df = add_indicators(_make_df())
    for col in ["ma5", "ma25", "ma75", "bb_upper", "bb_mid", "bb_lower", "rsi", "macd", "macd_signal", "macd_hist"]:
        assert col in df.columns, f"{col} missing"


def test_ma5_value():
    df = _make_df(n=10, trend=False)
    result = add_indicators(df)
    assert round(result["ma5"].iloc[-1], 2) == 100.0


def test_is_bb_breakout_lower():
    df = _make_df(n=100, trend=False)
    df = add_indicators(df)
    df = df.copy()
    df.loc[df.index[-1], "Close"] = -9999
    df.loc[df.index[-1], "bb_lower"] = 0
    result = is_bb_breakout(df)
    assert result["lower"] is True
    assert result["upper"] is False


def test_is_bb_breakout_upper():
    df = _make_df(n=100, trend=False)
    df = add_indicators(df)
    df = df.copy()
    df.loc[df.index[-1], "Close"] = 9999
    df.loc[df.index[-1], "bb_upper"] = 0
    result = is_bb_breakout(df)
    assert result["upper"] is True
    assert result["lower"] is False


def test_is_golden_cross_detected():
    df = _make_df(n=100)
    df = add_indicators(df)
    df = df.copy()
    df.loc[df.index[-2], "ma25"] = 99.0
    df.loc[df.index[-2], "ma75"] = 100.0
    df.loc[df.index[-1], "ma25"] = 101.0
    df.loc[df.index[-1], "ma75"] = 100.0
    assert is_golden_cross(df) is True


def test_is_golden_cross_not_detected():
    df = _make_df(n=100)
    df = add_indicators(df)
    df = df.copy()
    df.loc[df.index[-2], "ma25"] = 101.0
    df.loc[df.index[-2], "ma75"] = 100.0
    df.loc[df.index[-1], "ma25"] = 102.0
    df.loc[df.index[-1], "ma75"] = 100.0
    assert is_golden_cross(df) is False
