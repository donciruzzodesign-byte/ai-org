from unittest.mock import patch
import pandas as pd
import pytest
from screener.engine import evaluate_condition, run_screen


def _make_df_with_indicators():
    idx = pd.date_range("2024-01-01", periods=100)
    df = pd.DataFrame({
        "Open": [100.0] * 100,
        "High": [110.0] * 100,
        "Low": [90.0] * 100,
        "Close": [105.0] * 100,
        "Volume": [1000] * 100,
        "ma25": [100.0, 101.0] + [105.0] * 98,
        "ma75": [101.0, 100.0] + [100.0] * 98,
        "bb_upper": [120.0] * 100,
        "bb_lower": [80.0] * 100,
        "rsi": [25.0] * 100,
        "macd": [0.5] * 100,
        "macd_signal": [0.3] * 100,
        "macd_hist": [0.2] * 100,
    }, index=idx)
    return df


def test_evaluate_rsi_below_threshold():
    df = _make_df_with_indicators()
    with patch("screener.engine.fetch_ohlcv", return_value=df), \
         patch("screener.engine.add_indicators", return_value=df):
        result = evaluate_condition({"field": "rsi", "op": "<", "value": 30}, "AAPL")
    assert result is True


def test_evaluate_rsi_above_threshold():
    df = _make_df_with_indicators()
    with patch("screener.engine.fetch_ohlcv", return_value=df), \
         patch("screener.engine.add_indicators", return_value=df):
        result = evaluate_condition({"field": "rsi", "op": ">", "value": 50}, "AAPL")
    assert result is False


def test_evaluate_per():
    df = _make_df_with_indicators()
    fund = {"per": 12.0, "pbr": 1.0, "equity_ratio": 50.0, "market_cap": None}
    with patch("screener.engine.fetch_ohlcv", return_value=df), \
         patch("screener.engine.add_indicators", return_value=df), \
         patch("screener.engine.fetch_fundamentals", return_value=fund):
        result = evaluate_condition({"field": "per", "op": "<", "value": 15}, "7203.T")
    assert result is True


def test_evaluate_vix():
    df = _make_df_with_indicators()
    with patch("screener.engine.fetch_ohlcv", return_value=df), \
         patch("screener.engine.add_indicators", return_value=df), \
         patch("screener.engine.fetch_vix", return_value=18.0):
        result = evaluate_condition({"field": "vix", "op": "<", "value": 20}, "AAPL")
    assert result is True


def test_run_screen_and_logic():
    df = _make_df_with_indicators()
    fund = {"per": 12.0, "pbr": 1.0, "equity_ratio": 50.0, "market_cap": None}
    conditions = [
        {"field": "rsi", "op": "<", "value": 30},
        {"field": "per", "op": "<", "value": 15},
    ]
    with patch("screener.engine.fetch_ohlcv", return_value=df), \
         patch("screener.engine.add_indicators", return_value=df), \
         patch("screener.engine.fetch_fundamentals", return_value=fund):
        matched = run_screen(["AAPL", "MSFT"], conditions, logic="AND")
    assert matched == ["AAPL", "MSFT"]


def test_run_screen_skips_errors():
    with patch("screener.engine.fetch_ohlcv", side_effect=ValueError("No data")):
        matched = run_screen(["INVALID"], [{"field": "rsi", "op": "<", "value": 30}])
    assert matched == []
