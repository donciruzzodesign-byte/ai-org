from unittest.mock import patch, MagicMock
import pandas as pd
import pytest
from screener.alerts import AlertMonitor


def _make_df_breakout_lower():
    idx = pd.date_range("2024-01-01", periods=100)
    df = pd.DataFrame({
        "Open": [100.0] * 100,
        "High": [110.0] * 100,
        "Low": [90.0] * 100,
        "Close": [70.0] * 100,
        "Volume": [1000] * 100,
        "bb_upper": [120.0] * 100,
        "bb_lower": [80.0] * 100,
    }, index=idx)
    return df


def test_alert_fires_on_bb_lower_breakout():
    received = []
    monitor = AlertMonitor(on_alert=lambda t, d: received.append((t, d)))

    df = _make_df_breakout_lower()
    with patch("screener.alerts.get_watchlist", return_value=["AAPL"]), \
         patch("screener.alerts.fetch_ohlcv", return_value=df), \
         patch("screener.alerts.add_indicators", return_value=df), \
         patch("screener.alerts.get_setting", return_value="15"):
        monitor._check_all()

    assert ("AAPL", "lower") in received


def test_alert_skips_error_tickers():
    received = []
    monitor = AlertMonitor(on_alert=lambda t, d: received.append((t, d)))

    with patch("screener.alerts.get_watchlist", return_value=["BAD"]), \
         patch("screener.alerts.fetch_ohlcv", side_effect=ValueError("No data")):
        monitor._check_all()

    assert received == []


def test_monitor_start_stop():
    monitor = AlertMonitor(on_alert=lambda t, d: None)
    with patch("screener.alerts.get_watchlist", return_value=[]):
        monitor.start()
        assert monitor._thread is not None
        assert monitor._thread.is_alive()
        monitor.stop()
