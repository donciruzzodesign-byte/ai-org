from unittest.mock import patch, MagicMock
import pandas as pd
import pytest
from screener.data import fetch_ohlcv, fetch_fundamentals, fetch_vix


def _make_ohlcv():
    idx = pd.date_range("2024-01-01", periods=5, tz="UTC")
    return pd.DataFrame({
        "Open": [100.0] * 5,
        "High": [110.0] * 5,
        "Low": [90.0] * 5,
        "Close": [105.0] * 5,
        "Volume": [1000] * 5,
    }, index=idx)


def test_fetch_ohlcv_returns_dataframe():
    mock_ticker = MagicMock()
    mock_ticker.history.return_value = _make_ohlcv()
    with patch("screener.data.yf.Ticker", return_value=mock_ticker):
        df = fetch_ohlcv("AAPL")
    assert list(df.columns) == ["Open", "High", "Low", "Close", "Volume"]
    assert len(df) == 5
    assert df.index.tzinfo is None


def test_fetch_ohlcv_raises_on_empty():
    mock_ticker = MagicMock()
    mock_ticker.history.return_value = pd.DataFrame()
    with patch("screener.data.yf.Ticker", return_value=mock_ticker):
        with pytest.raises(ValueError, match="No data"):
            fetch_ohlcv("INVALID")


def test_fetch_fundamentals_returns_dict():
    mock_ticker = MagicMock()
    mock_ticker.info = {
        "trailingPE": 20.5,
        "priceToBook": 3.2,
        "totalStockholderEquity": 500000,
        "totalAssets": 1000000,
        "marketCap": 5000000,
    }
    with patch("screener.data.yf.Ticker", return_value=mock_ticker):
        result = fetch_fundamentals("AAPL")
    assert result["per"] == 20.5
    assert result["pbr"] == 3.2
    assert result["equity_ratio"] == 50.0
    assert result["market_cap"] == 5000000


def test_fetch_fundamentals_handles_missing():
    mock_ticker = MagicMock()
    mock_ticker.info = {}
    with patch("screener.data.yf.Ticker", return_value=mock_ticker):
        result = fetch_fundamentals("AAPL")
    assert result["per"] is None
    assert result["equity_ratio"] is None


def test_fetch_vix():
    mock_ticker = MagicMock()
    idx = pd.date_range("2024-01-01", periods=1, tz="UTC")
    mock_ticker.history.return_value = pd.DataFrame({"Close": [18.5]}, index=idx)
    with patch("screener.data.yf.Ticker", return_value=mock_ticker):
        vix = fetch_vix()
    assert vix == 18.5
