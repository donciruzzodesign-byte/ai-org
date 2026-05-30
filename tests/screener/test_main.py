from unittest.mock import patch, MagicMock
import pandas as pd
import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client(tmp_path, monkeypatch):
    import screener.db as db_module
    monkeypatch.setattr(db_module, "DB_PATH", tmp_path / "test.db")
    from screener.db import init_db
    init_db()
    # main をここでインポートしてモニターを起動しないようにする
    with patch("screener.main._monitor") as mock_monitor:
        mock_monitor.start.return_value = None
        mock_monitor.stop.return_value = None
        from screener.main import app
        from fastapi.testclient import TestClient
        with TestClient(app) as c:
            yield c


def _make_ohlcv():
    idx = pd.date_range("2024-01-01", periods=50)
    return pd.DataFrame({
        "Open": [100.0] * 50,
        "High": [110.0] * 50,
        "Low": [90.0] * 50,
        "Close": [105.0] * 50,
        "Volume": [1000] * 50,
    }, index=idx)


def _make_ohlcv_with_indicators():
    idx = pd.date_range("2024-01-01", periods=50)
    return pd.DataFrame({
        "Open": [100.0] * 50,
        "High": [110.0] * 50,
        "Low": [90.0] * 50,
        "Close": [105.0] * 50,
        "Volume": [1000] * 50,
        "ma5": [103.0] * 50,
        "ma25": [102.0] * 50,
        "ma75": [101.0] * 50,
        "bb_upper": [115.0] * 50,
        "bb_mid": [105.0] * 50,
        "bb_lower": [95.0] * 50,
        "rsi": [50.0] * 50,
        "macd": [0.5] * 50,
        "macd_signal": [0.3] * 50,
        "macd_hist": [0.2] * 50,
    }, index=idx)


def test_get_stock(client):
    with patch("screener.main.fetch_ohlcv", return_value=_make_ohlcv()), \
         patch("screener.main.add_indicators", return_value=_make_ohlcv_with_indicators()):
        resp = client.get("/stock/AAPL")
    assert resp.status_code == 200
    data = resp.json()
    assert data["ticker"] == "AAPL"
    assert isinstance(data["data"], list)


def test_get_stock_invalid(client):
    with patch("screener.main.fetch_ohlcv", side_effect=ValueError("No data")):
        resp = client.get("/stock/INVALID")
    assert resp.status_code == 404


def test_watchlist_crud(client):
    # 追加
    resp = client.post("/watchlist", json={"ticker": "AAPL"})
    assert resp.status_code == 200
    # 取得
    resp = client.get("/watchlist")
    assert "AAPL" in resp.json()["tickers"]
    # 削除
    resp = client.delete("/watchlist/AAPL")
    assert resp.status_code == 200
    resp = client.get("/watchlist")
    assert "AAPL" not in resp.json()["tickers"]


def test_settings(client):
    resp = client.get("/settings")
    assert resp.json()["alert_interval_minutes"] == "15"
    resp = client.put("/settings", json={"alert_interval_minutes": "30"})
    assert resp.status_code == 200
    resp = client.get("/settings")
    assert resp.json()["alert_interval_minutes"] == "30"
