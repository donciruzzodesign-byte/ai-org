# 株スクリーニングアプリ 実装計画

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 日米株チャート表示・テクニカル/ファンダメンタル/マクロ条件スクリーニング・BBアラートを備えたElectronデスクトップアプリを構築する

**Architecture:** Python FastAPI がデータ取得・指標計算・スクリーニングを担当し、Electron + React フロントエンドが HTTP/WebSocket で通信する。Electronがアプリ起動時にFastAPIサーバーをサブプロセスとして起動する。

**Tech Stack:** Python 3.11 / FastAPI / yfinance / pandas-ta / SQLite / Electron 29 / React 18 / TypeScript / Lightweight Charts / electron-vite

---

## ファイルマップ

```
ai-org/
├── screener/                        # Python FastAPI バックエンド
│   ├── __init__.py
│   ├── main.py                      # FastAPI app + WebSocket
│   ├── data.py                      # yfinance OHLCV・ファンダメンタル・VIX取得
│   ├── indicators.py                # pandas-ta MA/BB/RSI/MACD計算
│   ├── engine.py                    # スクリーニング条件評価エンジン
│   ├── alerts.py                    # BBアラート監視バックグラウンドスレッド
│   └── db.py                        # SQLite ウォッチリスト・設定CRUD
├── tests/screener/
│   ├── __init__.py
│   ├── test_data.py
│   ├── test_indicators.py
│   ├── test_db.py
│   ├── test_engine.py
│   └── test_alerts.py
├── desktop/                         # Electron + React フロントエンド
│   ├── src/
│   │   ├── main/index.ts            # Electronメインプロセス（FastAPI起動含む）
│   │   ├── preload/index.ts         # Electronプリロード
│   │   └── renderer/
│   │       ├── index.html
│   │       └── src/
│   │           ├── main.tsx         # Reactエントリポイント
│   │           ├── App.tsx          # タブ切替・WebSocket・通知
│   │           ├── types.ts         # 共有型定義
│   │           ├── api.ts           # FastAPI HTTPクライアント
│   │           ├── ChartView.tsx    # ローソク足・MA/BB/RSI/MACDチャート
│   │           ├── ScreenerView.tsx # 条件設定・スクリーニング結果
│   │           └── WatchlistView.tsx# ウォッチリスト管理
│   ├── electron.vite.config.ts
│   ├── package.json
│   └── tsconfig.json
└── requirements.txt                 # screener依存追加
```

---

## Task 1: Python バックエンド環境セットアップ

**Files:**
- Modify: `requirements.txt`
- Create: `screener/__init__.py`
- Create: `tests/screener/__init__.py`

- [ ] **Step 1: requirements.txt に screener 依存を追記**

```txt
# 既存の内容の末尾に追加
fastapi==0.111.0
uvicorn[standard]==0.29.0
yfinance==0.2.38
pandas-ta==0.3.14b
pytest==8.2.0
httpx==0.27.0
```

- [ ] **Step 2: screener ディレクトリと空の __init__.py を作成**

```bash
mkdir -p screener tests/screener
touch screener/__init__.py tests/screener/__init__.py
```

- [ ] **Step 3: 依存インストール**

```bash
pip install -r requirements.txt
```

期待出力: `Successfully installed fastapi-0.111.0 uvicorn-...` などが表示される

- [ ] **Step 4: コミット**

```bash
git add requirements.txt screener/__init__.py tests/screener/__init__.py
git commit -m "chore: screener バックエンド依存を追加"
```

---

## Task 2: データ取得モジュール (data.py)

**Files:**
- Create: `screener/data.py`
- Create: `tests/screener/test_data.py`

- [ ] **Step 1: テストを書く**

`tests/screener/test_data.py`:
```python
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
    assert df.index.tzinfo is None  # tz除去済み


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
```

- [ ] **Step 2: テストが失敗することを確認**

```bash
pytest tests/screener/test_data.py -v
```

期待出力: `ImportError` または `ModuleNotFoundError: No module named 'screener.data'`

- [ ] **Step 3: data.py を実装**

`screener/data.py`:
```python
from typing import Optional
import yfinance as yf
import pandas as pd


def fetch_ohlcv(ticker: str, period: str = "1y") -> pd.DataFrame:
    t = yf.Ticker(ticker)
    df = t.history(period=period)
    if df.empty:
        raise ValueError(f"No data for ticker: {ticker}")
    df.index = df.index.tz_localize(None)
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
    if equity and assets and assets > 0:
        return round(equity / assets * 100, 2)
    return None


def fetch_vix() -> float:
    t = yf.Ticker("^VIX")
    df = t.history(period="1d")
    if df.empty:
        raise ValueError("Could not fetch VIX")
    return float(df["Close"].iloc[-1])
```

- [ ] **Step 4: テストが通ることを確認**

```bash
pytest tests/screener/test_data.py -v
```

期待出力: `5 passed`

- [ ] **Step 5: コミット**

```bash
git add screener/data.py tests/screener/test_data.py
git commit -m "feat: データ取得モジュール (yfinance)"
```

---

## Task 3: テクニカル指標計算 (indicators.py)

**Files:**
- Create: `screener/indicators.py`
- Create: `tests/screener/test_indicators.py`

- [ ] **Step 1: テストを書く**

`tests/screener/test_indicators.py`:
```python
import pandas as pd
import numpy as np
import pytest
from screener.indicators import add_indicators, is_bb_breakout, is_golden_cross


def _make_df(n=100, trend=True):
    """n本のダミーOHLCVデータ。trend=Trueで上昇トレンド。"""
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
    # 全て100.0なのでMA5 = 100.0
    assert round(result["ma5"].iloc[-1], 2) == 100.0


def test_is_bb_breakout_lower():
    df = _make_df(n=100, trend=False)
    df = add_indicators(df)
    # 最後の終値をBB下限より低く設定
    df.loc[df.index[-1], "Close"] = -9999
    df.loc[df.index[-1], "bb_lower"] = 0
    result = is_bb_breakout(df)
    assert result["lower"] is True
    assert result["upper"] is False


def test_is_bb_breakout_upper():
    df = _make_df(n=100, trend=False)
    df = add_indicators(df)
    df.loc[df.index[-1], "Close"] = 9999
    df.loc[df.index[-1], "bb_upper"] = 0
    result = is_bb_breakout(df)
    assert result["upper"] is True
    assert result["lower"] is False


def test_is_golden_cross_detected():
    df = _make_df(n=100)
    df = add_indicators(df)
    # 直前: ma25 <= ma75, 直後: ma25 > ma75 となるよう手動で設定
    df.loc[df.index[-2], "ma25"] = 99.0
    df.loc[df.index[-2], "ma75"] = 100.0
    df.loc[df.index[-1], "ma25"] = 101.0
    df.loc[df.index[-1], "ma75"] = 100.0
    assert is_golden_cross(df) is True


def test_is_golden_cross_not_detected():
    df = _make_df(n=100)
    df = add_indicators(df)
    df.loc[df.index[-2], "ma25"] = 101.0
    df.loc[df.index[-2], "ma75"] = 100.0
    df.loc[df.index[-1], "ma25"] = 102.0
    df.loc[df.index[-1], "ma75"] = 100.0
    assert is_golden_cross(df) is False
```

- [ ] **Step 2: テストが失敗することを確認**

```bash
pytest tests/screener/test_indicators.py -v
```

期待出力: `ImportError` または `ModuleNotFoundError`

- [ ] **Step 3: indicators.py を実装**

`screener/indicators.py`:
```python
import pandas as pd
import pandas_ta as ta


def add_indicators(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["ma5"] = ta.sma(df["Close"], length=5)
    df["ma25"] = ta.sma(df["Close"], length=25)
    df["ma75"] = ta.sma(df["Close"], length=75)

    bb = ta.bbands(df["Close"], length=20, std=2)
    df["bb_upper"] = bb["BBU_20_2.0"]
    df["bb_mid"] = bb["BBM_20_2.0"]
    df["bb_lower"] = bb["BBL_20_2.0"]

    df["rsi"] = ta.rsi(df["Close"], length=14)

    macd = ta.macd(df["Close"], fast=12, slow=26, signal=9)
    df["macd"] = macd["MACD_12_26_9"]
    df["macd_signal"] = macd["MACDs_12_26_9"]
    df["macd_hist"] = macd["MACDh_12_26_9"]

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
```

- [ ] **Step 4: テストが通ることを確認**

```bash
pytest tests/screener/test_indicators.py -v
```

期待出力: `5 passed`

- [ ] **Step 5: コミット**

```bash
git add screener/indicators.py tests/screener/test_indicators.py
git commit -m "feat: テクニカル指標計算モジュール (pandas-ta)"
```

---

## Task 4: SQLite ウォッチリスト管理 (db.py)

**Files:**
- Create: `screener/db.py`
- Create: `tests/screener/test_db.py`

- [ ] **Step 1: テストを書く**

`tests/screener/test_db.py`:
```python
import pytest
from pathlib import Path
from unittest.mock import patch
import screener.db as db_module
from screener.db import init_db, get_watchlist, add_to_watchlist, remove_from_watchlist, get_setting, set_setting


@pytest.fixture(autouse=True)
def tmp_db(tmp_path, monkeypatch):
    monkeypatch.setattr(db_module, "DB_PATH", tmp_path / "test.db")
    init_db()
    yield


def test_watchlist_empty_initially():
    assert get_watchlist() == []


def test_add_and_get_watchlist():
    add_to_watchlist("AAPL", "Apple Inc.")
    add_to_watchlist("7203.T", "Toyota")
    result = get_watchlist()
    assert "AAPL" in result
    assert "7203.T" in result


def test_add_duplicate_is_ignored():
    add_to_watchlist("AAPL")
    add_to_watchlist("AAPL")
    assert get_watchlist().count("AAPL") == 1


def test_remove_from_watchlist():
    add_to_watchlist("AAPL")
    remove_from_watchlist("AAPL")
    assert "AAPL" not in get_watchlist()


def test_ticker_uppercased():
    add_to_watchlist("aapl")
    assert "AAPL" in get_watchlist()


def test_default_alert_interval():
    assert get_setting("alert_interval_minutes") == "15"


def test_set_and_get_setting():
    set_setting("alert_interval_minutes", "30")
    assert get_setting("alert_interval_minutes") == "30"
```

- [ ] **Step 2: テストが失敗することを確認**

```bash
pytest tests/screener/test_db.py -v
```

期待出力: `ImportError` または `ModuleNotFoundError`

- [ ] **Step 3: db.py を実装**

`screener/db.py`:
```python
import sqlite3
from pathlib import Path
from typing import List

DB_PATH = Path(__file__).parent / "screener.db"


def get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    with get_conn() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS watchlist (
                ticker TEXT PRIMARY KEY,
                name TEXT DEFAULT '',
                added_at TEXT DEFAULT (datetime('now'))
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT
            )
        """)
        conn.execute(
            "INSERT OR IGNORE INTO settings (key, value) VALUES ('alert_interval_minutes', '15')"
        )


def get_watchlist() -> List[str]:
    with get_conn() as conn:
        rows = conn.execute("SELECT ticker FROM watchlist ORDER BY added_at").fetchall()
    return [row["ticker"] for row in rows]


def add_to_watchlist(ticker: str, name: str = "") -> None:
    with get_conn() as conn:
        conn.execute(
            "INSERT OR IGNORE INTO watchlist (ticker, name) VALUES (?, ?)",
            (ticker.upper(), name),
        )


def remove_from_watchlist(ticker: str) -> None:
    with get_conn() as conn:
        conn.execute("DELETE FROM watchlist WHERE ticker = ?", (ticker.upper(),))


def get_setting(key: str) -> str:
    with get_conn() as conn:
        row = conn.execute("SELECT value FROM settings WHERE key = ?", (key,)).fetchone()
    return row["value"] if row else ""


def set_setting(key: str, value: str) -> None:
    with get_conn() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)",
            (key, value),
        )
```

- [ ] **Step 4: テストが通ることを確認**

```bash
pytest tests/screener/test_db.py -v
```

期待出力: `7 passed`

- [ ] **Step 5: コミット**

```bash
git add screener/db.py tests/screener/test_db.py
git commit -m "feat: SQLite ウォッチリスト・設定管理"
```

---

## Task 5: スクリーニングエンジン (engine.py)

**Files:**
- Create: `screener/engine.py`
- Create: `tests/screener/test_engine.py`

- [ ] **Step 1: テストを書く**

`tests/screener/test_engine.py`:
```python
from unittest.mock import patch, MagicMock
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
```

- [ ] **Step 2: テストが失敗することを確認**

```bash
pytest tests/screener/test_engine.py -v
```

期待出力: `ImportError` または `ModuleNotFoundError`

- [ ] **Step 3: engine.py を実装**

`screener/engine.py`:
```python
from typing import List, Dict, Any
from screener.data import fetch_ohlcv, fetch_fundamentals, fetch_vix
from screener.indicators import add_indicators, is_golden_cross

_OPS = {
    "<": lambda a, b: a < b,
    ">": lambda a, b: a > b,
    "<=": lambda a, b: a <= b,
    ">=": lambda a, b: a >= b,
    "==": lambda a, b: a == b,
}


def evaluate_condition(condition: Dict[str, Any], ticker: str) -> bool:
    field = condition["field"]
    op = condition["op"]
    threshold = condition["value"]

    df = fetch_ohlcv(ticker)
    df = add_indicators(df)
    latest = df.iloc[-1]

    if field == "golden_cross":
        return is_golden_cross(df)

    if field in ("per", "pbr", "equity_ratio"):
        fund = fetch_fundamentals(ticker)
        actual = fund.get(field)
        if actual is None:
            return False
    elif field == "vix":
        actual = fetch_vix()
    elif field == "rsi":
        actual = float(latest["rsi"])
    elif field == "bb_lower":
        actual = float(latest["Close"])
        threshold = float(latest["bb_lower"])
    elif field == "bb_upper":
        actual = float(latest["Close"])
        threshold = float(latest["bb_upper"])
    else:
        return False

    fn = _OPS.get(op)
    return fn(actual, threshold) if fn else False


def run_screen(tickers: List[str], conditions: List[Dict], logic: str = "AND") -> List[str]:
    results = []
    for ticker in tickers:
        try:
            evals = [evaluate_condition(c, ticker) for c in conditions]
            passed = all(evals) if logic == "AND" else any(evals)
            if passed:
                results.append(ticker)
        except Exception:
            continue
    return results
```

- [ ] **Step 4: テストが通ることを確認**

```bash
pytest tests/screener/test_engine.py -v
```

期待出力: `6 passed`

- [ ] **Step 5: コミット**

```bash
git add screener/engine.py tests/screener/test_engine.py
git commit -m "feat: スクリーニングエンジン (AND/OR条件評価)"
```

---

## Task 6: BBアラート監視 (alerts.py)

**Files:**
- Create: `screener/alerts.py`
- Create: `tests/screener/test_alerts.py`

- [ ] **Step 1: テストを書く**

`tests/screener/test_alerts.py`:
```python
from unittest.mock import patch, MagicMock, call
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
```

- [ ] **Step 2: テストが失敗することを確認**

```bash
pytest tests/screener/test_alerts.py -v
```

期待出力: `ImportError` または `ModuleNotFoundError`

- [ ] **Step 3: alerts.py を実装**

`screener/alerts.py`:
```python
import threading
from typing import Callable
from screener.data import fetch_ohlcv
from screener.indicators import add_indicators, is_bb_breakout
from screener.db import get_watchlist, get_setting


class AlertMonitor:
    def __init__(self, on_alert: Callable[[str, str], None]):
        self._on_alert = on_alert
        self._thread: threading.Thread | None = None
        self._stop_event = threading.Event()

    def start(self) -> None:
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop_event.set()

    def _loop(self) -> None:
        while not self._stop_event.is_set():
            self._check_all()
            interval = int(get_setting("alert_interval_minutes") or "15")
            self._stop_event.wait(timeout=interval * 60)

    def _check_all(self) -> None:
        for ticker in get_watchlist():
            try:
                df = fetch_ohlcv(ticker, period="1mo")
                df = add_indicators(df)
                result = is_bb_breakout(df)
                if result["upper"]:
                    self._on_alert(ticker, "upper")
                elif result["lower"]:
                    self._on_alert(ticker, "lower")
            except Exception:
                continue
```

- [ ] **Step 4: テストが通ることを確認**

```bash
pytest tests/screener/test_alerts.py -v
```

期待出力: `3 passed`

- [ ] **Step 5: コミット**

```bash
git add screener/alerts.py tests/screener/test_alerts.py
git commit -m "feat: BBアラート監視バックグラウンドスレッド"
```

---

## Task 7: FastAPI サーバー (main.py)

**Files:**
- Create: `screener/main.py`

- [ ] **Step 1: main.py を実装**

`screener/main.py`:
```python
import asyncio
import json
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from screener.alerts import AlertMonitor
from screener.data import fetch_fundamentals, fetch_ohlcv, fetch_vix
from screener.db import (add_to_watchlist, get_setting, get_watchlist,
                          init_db, remove_from_watchlist, set_setting)
from screener.engine import run_screen
from screener.indicators import add_indicators

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

_ws_clients: List[WebSocket] = []


def _on_alert(ticker: str, direction: str) -> None:
    payload = json.dumps({"type": "alert", "ticker": ticker, "direction": direction})
    asyncio.run(_broadcast(payload))


async def _broadcast(message: str) -> None:
    for ws in list(_ws_clients):
        try:
            await ws.send_text(message)
        except Exception:
            if ws in _ws_clients:
                _ws_clients.remove(ws)


_monitor = AlertMonitor(on_alert=_on_alert)


@app.on_event("startup")
async def startup() -> None:
    init_db()
    _monitor.start()


@app.on_event("shutdown")
async def shutdown() -> None:
    _monitor.stop()


@app.get("/stock/{ticker}")
async def get_stock(ticker: str, period: str = "1y"):
    try:
        df = fetch_ohlcv(ticker, period)
        df = add_indicators(df)
        df = df.where(df.notna(), None)
        records = []
        for ts, row in df.iterrows():
            records.append({
                "time": int(ts.timestamp()),
                "open": row["Open"], "high": row["High"],
                "low": row["Low"], "close": row["Close"],
                "volume": row["Volume"],
                "ma5": row["ma5"], "ma25": row["ma25"], "ma75": row["ma75"],
                "bb_upper": row["bb_upper"], "bb_mid": row["bb_mid"], "bb_lower": row["bb_lower"],
                "rsi": row["rsi"], "macd": row["macd"],
                "macd_signal": row["macd_signal"], "macd_hist": row["macd_hist"],
            })
        return {"ticker": ticker, "data": records}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@app.get("/fundamentals/{ticker}")
async def get_fundamentals(ticker: str):
    try:
        return fetch_fundamentals(ticker)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/vix")
async def get_vix():
    try:
        return {"vix": fetch_vix()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class ScreenRequest(BaseModel):
    tickers: Optional[List[str]] = None
    conditions: List[Dict[str, Any]]
    logic: str = "AND"


@app.post("/screen")
async def screen(req: ScreenRequest):
    tickers = req.tickers or get_watchlist()
    matched = run_screen(tickers, req.conditions, req.logic)
    return {"matched": matched}


@app.get("/watchlist")
async def watchlist():
    return {"tickers": get_watchlist()}


class WatchlistAddRequest(BaseModel):
    ticker: str
    name: str = ""


@app.post("/watchlist")
async def add_watchlist(req: WatchlistAddRequest):
    add_to_watchlist(req.ticker, req.name)
    return {"ok": True}


@app.delete("/watchlist/{ticker}")
async def del_watchlist(ticker: str):
    remove_from_watchlist(ticker)
    return {"ok": True}


@app.get("/settings")
async def get_settings():
    return {"alert_interval_minutes": get_setting("alert_interval_minutes")}


class SettingsRequest(BaseModel):
    alert_interval_minutes: str


@app.put("/settings")
async def put_settings(req: SettingsRequest):
    set_setting("alert_interval_minutes", req.alert_interval_minutes)
    return {"ok": True}


@app.websocket("/ws/alerts")
async def ws_alerts(websocket: WebSocket):
    await websocket.accept()
    _ws_clients.append(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        if websocket in _ws_clients:
            _ws_clients.remove(websocket)
```

- [ ] **Step 2: サーバーが起動することを確認**

```bash
cd /path/to/ai-org
python3 -m uvicorn screener.main:app --port 8765 &
sleep 2
curl http://localhost:8765/vix
kill %1
```

期待出力: `{"vix": <数値>}` (ネットワーク接続があれば)

- [ ] **Step 3: 全テストが通ることを確認**

```bash
pytest tests/screener/ -v
```

期待出力: `21 passed` (全テスト合計)

- [ ] **Step 4: コミット**

```bash
git add screener/main.py
git commit -m "feat: FastAPI サーバー (REST + WebSocket)"
```

---

## Task 8: Electron プロジェクト初期化

**Files:**
- Create: `desktop/package.json`
- Create: `desktop/tsconfig.json`
- Create: `desktop/electron.vite.config.ts`
- Create: `desktop/src/main/index.ts`
- Create: `desktop/src/preload/index.ts`
- Create: `desktop/src/renderer/index.html`
- Create: `desktop/src/renderer/src/main.tsx`

- [ ] **Step 1: package.json を作成**

`desktop/package.json`:
```json
{
  "name": "stock-screener",
  "version": "1.0.0",
  "main": "out/main/index.js",
  "scripts": {
    "dev": "electron-vite dev",
    "build": "electron-vite build",
    "start": "electron-vite preview"
  },
  "dependencies": {
    "lightweight-charts": "^5.0.0",
    "react": "^18.2.0",
    "react-dom": "^18.2.0"
  },
  "devDependencies": {
    "@electron-toolkit/preload": "^3.0.0",
    "@electron-toolkit/utils": "^3.0.0",
    "@types/node": "^20.0.0",
    "@types/react": "^18.2.0",
    "@types/react-dom": "^18.2.0",
    "@vitejs/plugin-react": "^4.2.0",
    "electron": "^29.0.0",
    "electron-builder": "^24.0.0",
    "electron-vite": "^2.0.0",
    "typescript": "^5.4.0"
  }
}
```

- [ ] **Step 2: tsconfig.json を作成**

`desktop/tsconfig.json`:
```json
{
  "files": [],
  "references": [
    { "path": "./tsconfig.node.json" },
    { "path": "./tsconfig.web.json" }
  ]
}
```

`desktop/tsconfig.node.json`:
```json
{
  "extends": "@electron-toolkit/tsconfig/tsconfig.node.json",
  "include": ["electron.vite.config.*", "src/main/**/*", "src/preload/**/*"]
}
```

`desktop/tsconfig.web.json`:
```json
{
  "extends": "@electron-toolkit/tsconfig/tsconfig.web.json",
  "include": ["src/renderer/src/**/*"]
}
```

- [ ] **Step 3: electron.vite.config.ts を作成**

`desktop/electron.vite.config.ts`:
```typescript
import { resolve } from 'path'
import { defineConfig, externalizeDepsPlugin } from 'electron-vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  main: {
    plugins: [externalizeDepsPlugin()],
  },
  preload: {
    plugins: [externalizeDepsPlugin()],
  },
  renderer: {
    resolve: {
      alias: {
        '@renderer': resolve('src/renderer/src'),
      },
    },
    plugins: [react()],
  },
})
```

- [ ] **Step 4: Electron メインプロセスを作成**

`desktop/src/main/index.ts`:
```typescript
import { app, BrowserWindow, Notification, shell } from 'electron'
import { join } from 'path'
import { spawn, ChildProcess } from 'child_process'
import { is } from '@electron-toolkit/utils'

let win: BrowserWindow | null = null
let apiProcess: ChildProcess | null = null

function startApiServer(): void {
  const cwd = join(__dirname, '../../../..')
  apiProcess = spawn('python3', ['-m', 'uvicorn', 'screener.main:app', '--port', '8765'], {
    cwd,
    stdio: 'inherit',
  })
}

function createWindow(): void {
  win = new BrowserWindow({
    width: 1280,
    height: 800,
    title: '株スクリーナー',
    webPreferences: {
      preload: join(__dirname, '../preload/index.js'),
      contextIsolation: true,
      sandbox: false,
    },
  })

  if (is.dev && process.env['ELECTRON_RENDERER_URL']) {
    win.loadURL(process.env['ELECTRON_RENDERER_URL'])
  } else {
    win.loadFile(join(__dirname, '../renderer/index.html'))
  }
}

app.whenReady().then(() => {
  startApiServer()
  setTimeout(createWindow, 2000)
  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) createWindow()
  })
})

app.on('window-all-closed', () => {
  apiProcess?.kill()
  if (process.platform !== 'darwin') app.quit()
})
```

- [ ] **Step 5: プリロードスクリプトを作成**

`desktop/src/preload/index.ts`:
```typescript
import { contextBridge } from 'electron'
import { electronAPI } from '@electron-toolkit/preload'

contextBridge.exposeInMainWorld('electron', electronAPI)
```

- [ ] **Step 6: renderer/index.html を作成**

`desktop/src/renderer/index.html`:
```html
<!DOCTYPE html>
<html lang="ja">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>株スクリーナー</title>
    <style>
      * { box-sizing: border-box; margin: 0; padding: 0; }
      body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; background: #0d1117; color: #e6edf3; }
    </style>
  </head>
  <body>
    <div id="root"></div>
    <script type="module" src="/src/main.tsx"></script>
  </body>
</html>
```

- [ ] **Step 7: React エントリポイントを作成**

`desktop/src/renderer/src/main.tsx`:
```tsx
import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App'

ReactDOM.createRoot(document.getElementById('root') as HTMLElement).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
)
```

- [ ] **Step 8: 依存をインストール**

```bash
cd desktop
npm install
```

期待出力: `added N packages`

- [ ] **Step 9: コミット**

```bash
cd ..
git add desktop/
git commit -m "feat: Electron プロジェクト初期化 (electron-vite)"
```

---

## Task 9: 型定義・APIクライアント

**Files:**
- Create: `desktop/src/renderer/src/types.ts`
- Create: `desktop/src/renderer/src/api.ts`

- [ ] **Step 1: types.ts を作成**

`desktop/src/renderer/src/types.ts`:
```typescript
export interface Candle {
  time: number
  open: number
  high: number
  low: number
  close: number
  volume: number
  ma5: number | null
  ma25: number | null
  ma75: number | null
  bb_upper: number | null
  bb_mid: number | null
  bb_lower: number | null
  rsi: number | null
  macd: number | null
  macd_signal: number | null
  macd_hist: number | null
}

export interface StockResponse {
  ticker: string
  data: Candle[]
}

export interface Fundamentals {
  per: number | null
  pbr: number | null
  equity_ratio: number | null
  market_cap: number | null
}

export type ConditionField =
  | 'rsi' | 'per' | 'pbr' | 'equity_ratio'
  | 'vix' | 'bb_lower' | 'bb_upper' | 'golden_cross'

export type ConditionOp = '<' | '>' | '<=' | '>=' | '=='

export interface Condition {
  field: ConditionField
  op: ConditionOp
  value: number
}

export interface AlertMessage {
  type: 'alert'
  ticker: string
  direction: 'upper' | 'lower'
}
```

- [ ] **Step 2: api.ts を作成**

`desktop/src/renderer/src/api.ts`:
```typescript
import type { Condition, Fundamentals, StockResponse } from './types'

const BASE = 'http://localhost:8765'

async function req<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, options)
  if (!res.ok) {
    const body = await res.text()
    throw new Error(`${res.status}: ${body}`)
  }
  return res.json() as Promise<T>
}

export const getStock = (ticker: string, period = '1y'): Promise<StockResponse> =>
  req(`/stock/${encodeURIComponent(ticker)}?period=${period}`)

export const getFundamentals = (ticker: string): Promise<Fundamentals> =>
  req(`/fundamentals/${encodeURIComponent(ticker)}`)

export const getVix = (): Promise<{ vix: number }> => req('/vix')

export const getWatchlist = (): Promise<{ tickers: string[] }> => req('/watchlist')

export const addToWatchlist = (ticker: string, name = ''): Promise<{ ok: boolean }> =>
  req('/watchlist', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ ticker, name }),
  })

export const removeFromWatchlist = (ticker: string): Promise<{ ok: boolean }> =>
  req(`/watchlist/${encodeURIComponent(ticker)}`, { method: 'DELETE' })

export const runScreen = (
  conditions: Condition[],
  logic: 'AND' | 'OR' = 'AND',
  tickers?: string[]
): Promise<{ matched: string[] }> =>
  req('/screen', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ conditions, logic, tickers }),
  })

export const getSettings = (): Promise<{ alert_interval_minutes: string }> => req('/settings')

export const putSettings = (alert_interval_minutes: string): Promise<{ ok: boolean }> =>
  req('/settings', {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ alert_interval_minutes }),
  })

export function connectAlerts(onAlert: (ticker: string, direction: string) => void): WebSocket {
  const ws = new WebSocket('ws://localhost:8765/ws/alerts')
  ws.onmessage = (event) => {
    try {
      const data = JSON.parse(event.data as string)
      if (data.type === 'alert') {
        onAlert(data.ticker as string, data.direction as string)
      }
    } catch {
      // ignore malformed messages
    }
  }
  return ws
}
```

- [ ] **Step 3: TypeScript コンパイルエラーがないことを確認**

```bash
cd desktop
npx tsc --noEmit
```

期待出力: エラーなし（または `tsconfig.json` 設定に応じた軽微な警告のみ）

- [ ] **Step 4: コミット**

```bash
cd ..
git add desktop/src/renderer/src/types.ts desktop/src/renderer/src/api.ts
git commit -m "feat: 型定義とAPIクライアント"
```

---

## Task 10: ChartView コンポーネント

**Files:**
- Create: `desktop/src/renderer/src/ChartView.tsx`

- [ ] **Step 1: ChartView.tsx を実装**

`desktop/src/renderer/src/ChartView.tsx`:
```tsx
import React, { useEffect, useRef, useState } from 'react'
import {
  createChart,
  CandlestickSeries,
  LineSeries,
  HistogramSeries,
  ColorType,
  IChartApi,
} from 'lightweight-charts'
import { getStock, getFundamentals } from './api'
import type { Candle, Fundamentals } from './types'

const PERIODS = ['1mo', '3mo', '6mo', '1y', '2y', '5y'] as const
type Period = typeof PERIODS[number]

export default function ChartView(): JSX.Element {
  const [ticker, setTicker] = useState('')
  const [inputTicker, setInputTicker] = useState('')
  const [period, setPeriod] = useState<Period>('1y')
  const [fundamentals, setFundamentals] = useState<Fundamentals | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)

  const mainRef = useRef<HTMLDivElement>(null)
  const rsiRef = useRef<HTMLDivElement>(null)
  const macdRef = useRef<HTMLDivElement>(null)
  const chartRef = useRef<IChartApi | null>(null)
  const rsiChartRef = useRef<IChartApi | null>(null)
  const macdChartRef = useRef<IChartApi | null>(null)

  useEffect(() => {
    if (!ticker || !mainRef.current || !rsiRef.current || !macdRef.current) return

    // メインチャート
    const chart = createChart(mainRef.current, {
      layout: { background: { type: ColorType.Solid, color: '#0d1117' }, textColor: '#e6edf3' },
      grid: { vertLines: { color: '#21262d' }, horzLines: { color: '#21262d' } },
      width: mainRef.current.offsetWidth,
      height: 400,
    })
    chartRef.current = chart

    const candleSeries = chart.addSeries(CandlestickSeries, {
      upColor: '#3fb950', downColor: '#f85149',
      borderUpColor: '#3fb950', borderDownColor: '#f85149',
      wickUpColor: '#3fb950', wickDownColor: '#f85149',
    })
    const ma5Series = chart.addSeries(LineSeries, { color: '#58a6ff', lineWidth: 1 })
    const ma25Series = chart.addSeries(LineSeries, { color: '#f0883e', lineWidth: 1 })
    const ma75Series = chart.addSeries(LineSeries, { color: '#bc8cff', lineWidth: 1 })
    const bbUpperSeries = chart.addSeries(LineSeries, { color: '#8b949e', lineWidth: 1, lineStyle: 2 })
    const bbMidSeries = chart.addSeries(LineSeries, { color: '#8b949e', lineWidth: 1, lineStyle: 1 })
    const bbLowerSeries = chart.addSeries(LineSeries, { color: '#8b949e', lineWidth: 1, lineStyle: 2 })

    // RSIチャート
    const rsiChart = createChart(rsiRef.current, {
      layout: { background: { type: ColorType.Solid, color: '#0d1117' }, textColor: '#e6edf3' },
      grid: { vertLines: { color: '#21262d' }, horzLines: { color: '#21262d' } },
      width: rsiRef.current.offsetWidth,
      height: 120,
    })
    rsiChartRef.current = rsiChart
    const rsiSeries = rsiChart.addSeries(LineSeries, { color: '#79c0ff', lineWidth: 1 })

    // MACDチャート
    const macdChart = createChart(macdRef.current, {
      layout: { background: { type: ColorType.Solid, color: '#0d1117' }, textColor: '#e6edf3' },
      grid: { vertLines: { color: '#21262d' }, horzLines: { color: '#21262d' } },
      width: macdRef.current.offsetWidth,
      height: 120,
    })
    macdChartRef.current = macdChart
    const macdLineSeries = macdChart.addSeries(LineSeries, { color: '#79c0ff', lineWidth: 1 })
    const macdSignalSeries = macdChart.addSeries(LineSeries, { color: '#f0883e', lineWidth: 1 })
    const macdHistSeries = macdChart.addSeries(HistogramSeries, {
      color: '#3fb950', priceFormat: { type: 'price' },
    })

    setLoading(true)
    setError(null)

    getStock(ticker, period)
      .then(({ data }) => {
        const validCandles = (data as Candle[]).filter((c) => c.open && c.high && c.low && c.close)
        candleSeries.setData(validCandles.map((c) => ({
          time: c.time as any, open: c.open, high: c.high, low: c.low, close: c.close,
        })))
        ma5Series.setData(validCandles.filter((c) => c.ma5 != null).map((c) => ({ time: c.time as any, value: c.ma5! })))
        ma25Series.setData(validCandles.filter((c) => c.ma25 != null).map((c) => ({ time: c.time as any, value: c.ma25! })))
        ma75Series.setData(validCandles.filter((c) => c.ma75 != null).map((c) => ({ time: c.time as any, value: c.ma75! })))
        bbUpperSeries.setData(validCandles.filter((c) => c.bb_upper != null).map((c) => ({ time: c.time as any, value: c.bb_upper! })))
        bbMidSeries.setData(validCandles.filter((c) => c.bb_mid != null).map((c) => ({ time: c.time as any, value: c.bb_mid! })))
        bbLowerSeries.setData(validCandles.filter((c) => c.bb_lower != null).map((c) => ({ time: c.time as any, value: c.bb_lower! })))
        rsiSeries.setData(validCandles.filter((c) => c.rsi != null).map((c) => ({ time: c.time as any, value: c.rsi! })))
        macdLineSeries.setData(validCandles.filter((c) => c.macd != null).map((c) => ({ time: c.time as any, value: c.macd! })))
        macdSignalSeries.setData(validCandles.filter((c) => c.macd_signal != null).map((c) => ({ time: c.time as any, value: c.macd_signal! })))
        macdHistSeries.setData(validCandles.filter((c) => c.macd_hist != null).map((c) => ({
          time: c.time as any, value: c.macd_hist!,
          color: c.macd_hist! >= 0 ? '#3fb950' : '#f85149',
        })))
        chart.timeScale().fitContent()
        rsiChart.timeScale().fitContent()
        macdChart.timeScale().fitContent()
      })
      .catch((e: Error) => setError(e.message))
      .finally(() => setLoading(false))

    getFundamentals(ticker)
      .then(setFundamentals)
      .catch(() => setFundamentals(null))

    return () => {
      chart.remove()
      rsiChart.remove()
      macdChart.remove()
    }
  }, [ticker, period])

  const handleSearch = (): void => {
    if (inputTicker.trim()) setTicker(inputTicker.trim().toUpperCase())
  }

  return (
    <div style={{ padding: 16 }}>
      <div style={{ display: 'flex', gap: 8, marginBottom: 12 }}>
        <input
          value={inputTicker}
          onChange={(e) => setInputTicker(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
          placeholder="銘柄コード (例: AAPL, 7203.T)"
          style={{ flex: 1, padding: '6px 10px', background: '#161b22', border: '1px solid #30363d', color: '#e6edf3', borderRadius: 6 }}
        />
        <button onClick={handleSearch} style={{ padding: '6px 16px', background: '#1f6feb', border: 'none', color: '#fff', borderRadius: 6, cursor: 'pointer' }}>
          検索
        </button>
        {PERIODS.map((p) => (
          <button
            key={p}
            onClick={() => setPeriod(p)}
            style={{ padding: '6px 10px', background: period === p ? '#1f6feb' : '#21262d', border: 'none', color: '#e6edf3', borderRadius: 6, cursor: 'pointer' }}
          >
            {p}
          </button>
        ))}
      </div>
      {fundamentals && (
        <div style={{ display: 'flex', gap: 16, marginBottom: 12, fontSize: 13, color: '#8b949e' }}>
          <span>PER: {fundamentals.per?.toFixed(1) ?? 'N/A'}</span>
          <span>PBR: {fundamentals.pbr?.toFixed(2) ?? 'N/A'}</span>
          <span>自己資本比率: {fundamentals.equity_ratio != null ? `${fundamentals.equity_ratio}%` : 'N/A'}</span>
        </div>
      )}
      {loading && <p style={{ color: '#8b949e' }}>読み込み中...</p>}
      {error && (
        <p style={{ color: '#f85149' }}>
          エラー: {error}
          <button onClick={handleSearch} style={{ marginLeft: 8, padding: '2px 8px', background: '#21262d', border: 'none', color: '#e6edf3', borderRadius: 4, cursor: 'pointer' }}>
            リトライ
          </button>
        </p>
      )}
      <div ref={mainRef} style={{ width: '100%' }} />
      <div style={{ color: '#8b949e', fontSize: 12, margin: '4px 0' }}>RSI (14)</div>
      <div ref={rsiRef} style={{ width: '100%' }} />
      <div style={{ color: '#8b949e', fontSize: 12, margin: '4px 0' }}>MACD (12,26,9)</div>
      <div ref={macdRef} style={{ width: '100%' }} />
    </div>
  )
}
```

- [ ] **Step 2: TypeScript コンパイルエラーがないことを確認**

```bash
cd desktop
npx tsc --noEmit
```

期待出力: エラーなし

- [ ] **Step 3: コミット**

```bash
cd ..
git add desktop/src/renderer/src/ChartView.tsx
git commit -m "feat: ChartView - ローソク足・MA/BB/RSI/MACDチャート"
```

---

## Task 11: WatchlistView コンポーネント

**Files:**
- Create: `desktop/src/renderer/src/WatchlistView.tsx`

- [ ] **Step 1: WatchlistView.tsx を実装**

`desktop/src/renderer/src/WatchlistView.tsx`:
```tsx
import React, { useEffect, useState } from 'react'
import { getWatchlist, addToWatchlist, removeFromWatchlist, getSettings, putSettings } from './api'

interface Props {
  onSelectTicker: (ticker: string) => void
}

export default function WatchlistView({ onSelectTicker }: Props): JSX.Element {
  const [tickers, setTickers] = useState<string[]>([])
  const [newTicker, setNewTicker] = useState('')
  const [interval, setInterval] = useState('15')
  const [error, setError] = useState<string | null>(null)

  const loadWatchlist = (): void => {
    getWatchlist()
      .then(({ tickers }) => setTickers(tickers))
      .catch((e: Error) => setError(e.message))
  }

  useEffect(() => {
    loadWatchlist()
    getSettings().then(({ alert_interval_minutes }) => setInterval(alert_interval_minutes))
  }, [])

  const handleAdd = (): void => {
    if (!newTicker.trim()) return
    addToWatchlist(newTicker.trim())
      .then(() => { setNewTicker(''); loadWatchlist() })
      .catch((e: Error) => setError(e.message))
  }

  const handleRemove = (ticker: string): void => {
    removeFromWatchlist(ticker).then(loadWatchlist)
  }

  const handleSaveInterval = (): void => {
    putSettings(interval).catch((e: Error) => setError(e.message))
  }

  return (
    <div style={{ padding: 16 }}>
      <h2 style={{ marginBottom: 12, fontSize: 16 }}>ウォッチリスト</h2>
      {error && <p style={{ color: '#f85149', marginBottom: 8 }}>{error}</p>}
      <div style={{ display: 'flex', gap: 8, marginBottom: 16 }}>
        <input
          value={newTicker}
          onChange={(e) => setNewTicker(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && handleAdd()}
          placeholder="銘柄追加 (例: 6758.T)"
          style={{ flex: 1, padding: '6px 10px', background: '#161b22', border: '1px solid #30363d', color: '#e6edf3', borderRadius: 6 }}
        />
        <button onClick={handleAdd} style={{ padding: '6px 16px', background: '#1f6feb', border: 'none', color: '#fff', borderRadius: 6, cursor: 'pointer' }}>
          追加
        </button>
      </div>
      {tickers.length === 0 ? (
        <p style={{ color: '#8b949e' }}>銘柄がありません。上のフォームから追加してください。</p>
      ) : (
        <table style={{ width: '100%', borderCollapse: 'collapse' }}>
          <thead>
            <tr style={{ borderBottom: '1px solid #30363d', color: '#8b949e', fontSize: 13 }}>
              <th style={{ textAlign: 'left', padding: '6px 8px' }}>銘柄</th>
              <th style={{ textAlign: 'right', padding: '6px 8px' }}>操作</th>
            </tr>
          </thead>
          <tbody>
            {tickers.map((t) => (
              <tr key={t} style={{ borderBottom: '1px solid #21262d' }}>
                <td
                  onClick={() => onSelectTicker(t)}
                  style={{ padding: '8px', cursor: 'pointer', color: '#58a6ff' }}
                >
                  {t}
                </td>
                <td style={{ padding: '8px', textAlign: 'right' }}>
                  <button
                    onClick={() => handleRemove(t)}
                    style={{ padding: '2px 8px', background: '#da3633', border: 'none', color: '#fff', borderRadius: 4, cursor: 'pointer', fontSize: 12 }}
                  >
                    削除
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
      <div style={{ marginTop: 24, borderTop: '1px solid #30363d', paddingTop: 16 }}>
        <h3 style={{ fontSize: 14, marginBottom: 8 }}>アラート設定</h3>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <label style={{ fontSize: 13, color: '#8b949e' }}>チェック間隔:</label>
          <input
            type="number"
            value={interval}
            onChange={(e) => setInterval(e.target.value)}
            min="1"
            style={{ width: 60, padding: '4px 8px', background: '#161b22', border: '1px solid #30363d', color: '#e6edf3', borderRadius: 6 }}
          />
          <span style={{ fontSize: 13, color: '#8b949e' }}>分</span>
          <button onClick={handleSaveInterval} style={{ padding: '4px 12px', background: '#238636', border: 'none', color: '#fff', borderRadius: 6, cursor: 'pointer', fontSize: 13 }}>
            保存
          </button>
        </div>
      </div>
    </div>
  )
}
```

- [ ] **Step 2: TypeScript コンパイルエラーがないことを確認**

```bash
cd desktop
npx tsc --noEmit
```

期待出力: エラーなし

- [ ] **Step 3: コミット**

```bash
cd ..
git add desktop/src/renderer/src/WatchlistView.tsx
git commit -m "feat: WatchlistView - ウォッチリスト管理・アラート間隔設定"
```

---

## Task 12: ScreenerView コンポーネント

**Files:**
- Create: `desktop/src/renderer/src/ScreenerView.tsx`

- [ ] **Step 1: ScreenerView.tsx を実装**

`desktop/src/renderer/src/ScreenerView.tsx`:
```tsx
import React, { useState } from 'react'
import { runScreen } from './api'
import type { Condition, ConditionField, ConditionOp } from './types'

const FIELDS: { value: ConditionField; label: string }[] = [
  { value: 'rsi', label: 'RSI' },
  { value: 'per', label: 'PER' },
  { value: 'pbr', label: 'PBR' },
  { value: 'equity_ratio', label: '自己資本比率 (%)' },
  { value: 'vix', label: 'VIX' },
  { value: 'bb_lower', label: 'BB下限を下回る' },
  { value: 'bb_upper', label: 'BB上限を上回る' },
  { value: 'golden_cross', label: 'ゴールデンクロス' },
]

const OPS: ConditionOp[] = ['<', '<=', '>', '>=', '==']

interface Props {
  onSelectTicker: (ticker: string) => void
}

export default function ScreenerView({ onSelectTicker }: Props): JSX.Element {
  const [conditions, setConditions] = useState<Condition[]>([
    { field: 'rsi', op: '<', value: 30 },
  ])
  const [logic, setLogic] = useState<'AND' | 'OR'>('AND')
  const [customTickers, setCustomTickers] = useState('')
  const [matched, setMatched] = useState<string[] | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const addCondition = (): void => {
    setConditions([...conditions, { field: 'rsi', op: '<', value: 30 }])
  }

  const removeCondition = (i: number): void => {
    setConditions(conditions.filter((_, idx) => idx !== i))
  }

  const updateCondition = (i: number, patch: Partial<Condition>): void => {
    setConditions(conditions.map((c, idx) => (idx === i ? { ...c, ...patch } : c)))
  }

  const handleRun = (): void => {
    setLoading(true)
    setError(null)
    const tickers = customTickers.trim()
      ? customTickers.split(',').map((t) => t.trim().toUpperCase()).filter(Boolean)
      : undefined
    runScreen(conditions, logic, tickers)
      .then(({ matched }) => setMatched(matched))
      .catch((e: Error) => setError(e.message))
      .finally(() => setLoading(false))
  }

  return (
    <div style={{ padding: 16 }}>
      <h2 style={{ marginBottom: 12, fontSize: 16 }}>スクリーニング</h2>
      <div style={{ marginBottom: 12, display: 'flex', alignItems: 'center', gap: 8 }}>
        <span style={{ fontSize: 13, color: '#8b949e' }}>条件の結合:</span>
        {(['AND', 'OR'] as const).map((l) => (
          <button
            key={l}
            onClick={() => setLogic(l)}
            style={{ padding: '4px 12px', background: logic === l ? '#1f6feb' : '#21262d', border: 'none', color: '#e6edf3', borderRadius: 6, cursor: 'pointer' }}
          >
            {l}
          </button>
        ))}
      </div>
      {conditions.map((cond, i) => (
        <div key={i} style={{ display: 'flex', gap: 8, marginBottom: 8, alignItems: 'center' }}>
          <select
            value={cond.field}
            onChange={(e) => updateCondition(i, { field: e.target.value as ConditionField })}
            style={{ padding: '6px 8px', background: '#161b22', border: '1px solid #30363d', color: '#e6edf3', borderRadius: 6 }}
          >
            {FIELDS.map((f) => <option key={f.value} value={f.value}>{f.label}</option>)}
          </select>
          {cond.field !== 'golden_cross' && cond.field !== 'bb_lower' && cond.field !== 'bb_upper' && (
            <>
              <select
                value={cond.op}
                onChange={(e) => updateCondition(i, { op: e.target.value as ConditionOp })}
                style={{ padding: '6px 8px', background: '#161b22', border: '1px solid #30363d', color: '#e6edf3', borderRadius: 6 }}
              >
                {OPS.map((op) => <option key={op} value={op}>{op}</option>)}
              </select>
              <input
                type="number"
                value={cond.value}
                onChange={(e) => updateCondition(i, { value: Number(e.target.value) })}
                style={{ width: 80, padding: '6px 8px', background: '#161b22', border: '1px solid #30363d', color: '#e6edf3', borderRadius: 6 }}
              />
            </>
          )}
          <button
            onClick={() => removeCondition(i)}
            style={{ padding: '4px 8px', background: '#da3633', border: 'none', color: '#fff', borderRadius: 4, cursor: 'pointer' }}
          >
            ×
          </button>
        </div>
      ))}
      <button onClick={addCondition} style={{ marginBottom: 16, padding: '6px 12px', background: '#21262d', border: '1px solid #30363d', color: '#e6edf3', borderRadius: 6, cursor: 'pointer' }}>
        + 条件追加
      </button>
      <div style={{ marginBottom: 12 }}>
        <label style={{ fontSize: 13, color: '#8b949e', display: 'block', marginBottom: 4 }}>
          対象銘柄 (空欄=ウォッチリスト、カンマ区切りで直接指定可):
        </label>
        <input
          value={customTickers}
          onChange={(e) => setCustomTickers(e.target.value)}
          placeholder="AAPL, MSFT, 7203.T"
          style={{ width: '100%', padding: '6px 10px', background: '#161b22', border: '1px solid #30363d', color: '#e6edf3', borderRadius: 6 }}
        />
      </div>
      <button
        onClick={handleRun}
        disabled={loading || conditions.length === 0}
        style={{ padding: '8px 24px', background: '#238636', border: 'none', color: '#fff', borderRadius: 6, cursor: 'pointer', fontSize: 14 }}
      >
        {loading ? '実行中...' : 'スクリーニング実行'}
      </button>
      {error && <p style={{ color: '#f85149', marginTop: 12 }}>エラー: {error}</p>}
      {matched !== null && (
        <div style={{ marginTop: 16 }}>
          <h3 style={{ fontSize: 14, marginBottom: 8 }}>結果: {matched.length}件</h3>
          {matched.length === 0 ? (
            <p style={{ color: '#8b949e' }}>条件に一致する銘柄はありませんでした。</p>
          ) : (
            <table style={{ width: '100%', borderCollapse: 'collapse' }}>
              <thead>
                <tr style={{ borderBottom: '1px solid #30363d', color: '#8b949e', fontSize: 13 }}>
                  <th style={{ textAlign: 'left', padding: '6px 8px' }}>銘柄</th>
                  <th style={{ textAlign: 'right', padding: '6px 8px' }}>操作</th>
                </tr>
              </thead>
              <tbody>
                {matched.map((t) => (
                  <tr key={t} style={{ borderBottom: '1px solid #21262d' }}>
                    <td
                      onClick={() => onSelectTicker(t)}
                      style={{ padding: '8px', cursor: 'pointer', color: '#58a6ff' }}
                    >
                      {t}
                    </td>
                    <td style={{ padding: '8px', textAlign: 'right' }}>
                      <button
                        onClick={() => onSelectTicker(t)}
                        style={{ padding: '2px 8px', background: '#1f6feb', border: 'none', color: '#fff', borderRadius: 4, cursor: 'pointer', fontSize: 12 }}
                      >
                        チャート表示
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      )}
    </div>
  )
}
```

- [ ] **Step 2: TypeScript コンパイルエラーがないことを確認**

```bash
cd desktop
npx tsc --noEmit
```

期待出力: エラーなし

- [ ] **Step 3: コミット**

```bash
cd ..
git add desktop/src/renderer/src/ScreenerView.tsx
git commit -m "feat: ScreenerView - スクリーニング条件設定・結果表示"
```

---

## Task 13: App.tsx - タブ統合・WebSocketアラート

**Files:**
- Create: `desktop/src/renderer/src/App.tsx`

- [ ] **Step 1: App.tsx を実装**

`desktop/src/renderer/src/App.tsx`:
```tsx
import React, { useEffect, useRef, useState } from 'react'
import ChartView from './ChartView'
import ScreenerView from './ScreenerView'
import WatchlistView from './WatchlistView'
import { connectAlerts } from './api'

type Tab = 'chart' | 'screener' | 'watchlist'

interface AlertItem {
  id: number
  ticker: string
  direction: 'upper' | 'lower'
  time: string
}

let alertIdCounter = 0

export default function App(): JSX.Element {
  const [tab, setTab] = useState<Tab>('chart')
  const [chartTicker, setChartTicker] = useState('')
  const [alerts, setAlerts] = useState<AlertItem[]>([])
  const wsRef = useRef<WebSocket | null>(null)

  useEffect(() => {
    const connect = (): void => {
      const ws = connectAlerts((ticker, direction) => {
        const label = direction === 'upper' ? 'BB上限突破' : 'BB下限割れ'
        setAlerts((prev) => [
          { id: alertIdCounter++, ticker, direction: direction as 'upper' | 'lower', time: new Date().toLocaleTimeString() },
          ...prev.slice(0, 49),
        ])
        if (window.Notification?.permission === 'granted') {
          new window.Notification(`【アラート】${ticker}`, { body: `${label}を検知しました` })
        }
      })
      wsRef.current = ws
    }

    if (window.Notification?.permission === 'default') {
      window.Notification.requestPermission().then(connect)
    } else {
      connect()
    }

    return () => wsRef.current?.close()
  }, [])

  const handleSelectTicker = (ticker: string): void => {
    setChartTicker(ticker)
    setTab('chart')
  }

  const TAB_STYLE = (active: boolean): React.CSSProperties => ({
    padding: '8px 20px',
    background: active ? '#1f6feb' : 'transparent',
    border: 'none',
    borderBottom: active ? '2px solid #58a6ff' : '2px solid transparent',
    color: active ? '#fff' : '#8b949e',
    cursor: 'pointer',
    fontSize: 14,
  })

  return (
    <div style={{ minHeight: '100vh', display: 'flex', flexDirection: 'column' }}>
      <header style={{ background: '#161b22', borderBottom: '1px solid #30363d', display: 'flex', alignItems: 'center', padding: '0 16px' }}>
        <span style={{ fontWeight: 'bold', marginRight: 24, color: '#e6edf3' }}>株スクリーナー</span>
        <button onClick={() => setTab('chart')} style={TAB_STYLE(tab === 'chart')}>チャート</button>
        <button onClick={() => setTab('screener')} style={TAB_STYLE(tab === 'screener')}>スクリーニング</button>
        <button onClick={() => setTab('watchlist')} style={TAB_STYLE(tab === 'watchlist')}>ウォッチリスト</button>
        {alerts.length > 0 && (
          <span style={{ marginLeft: 'auto', fontSize: 12, color: '#f0883e' }}>
            最新: {alerts[0].ticker} {alerts[0].direction === 'upper' ? '↑BB上限' : '↓BB下限'} ({alerts[0].time})
          </span>
        )}
      </header>
      <main style={{ flex: 1, overflow: 'auto' }}>
        {tab === 'chart' && <ChartView initialTicker={chartTicker} />}
        {tab === 'screener' && <ScreenerView onSelectTicker={handleSelectTicker} />}
        {tab === 'watchlist' && <WatchlistView onSelectTicker={handleSelectTicker} />}
      </main>
    </div>
  )
}
```

- [ ] **Step 2: ChartView の Props に initialTicker を追加**

`desktop/src/renderer/src/ChartView.tsx` の先頭部分を修正:

```tsx
// 変更前
export default function ChartView(): JSX.Element {
  const [ticker, setTicker] = useState('')
  const [inputTicker, setInputTicker] = useState('')

// 変更後
interface Props {
  initialTicker?: string
}

export default function ChartView({ initialTicker = '' }: Props): JSX.Element {
  const [ticker, setTicker] = useState(initialTicker)
  const [inputTicker, setInputTicker] = useState(initialTicker)
```

- [ ] **Step 3: TypeScript コンパイルエラーがないことを確認**

```bash
cd desktop
npx tsc --noEmit
```

期待出力: エラーなし

- [ ] **Step 4: コミット**

```bash
cd ..
git add desktop/src/renderer/src/App.tsx desktop/src/renderer/src/ChartView.tsx
git commit -m "feat: App.tsx - タブ統合・WebSocketアラート・OS通知"
```

---

## Task 14: 起動確認・最終統合

**Files:**
- Create: `start.sh` (起動補助スクリプト)

- [ ] **Step 1: start.sh を作成**

`start.sh`:
```bash
#!/bin/bash
set -e
echo "FastAPI サーバーを起動中..."
python3 -m uvicorn screener.main:app --port 8765 &
API_PID=$!

echo "Electron アプリを起動中..."
cd desktop && npm run dev

kill $API_PID
```

```bash
chmod +x start.sh
```

- [ ] **Step 2: バックエンドのみ起動してAPIを確認**

```bash
python3 -m uvicorn screener.main:app --port 8765 &
sleep 2
curl http://localhost:8765/watchlist
```

期待出力: `{"tickers":[]}`

```bash
curl -X POST http://localhost:8765/watchlist \
  -H "Content-Type: application/json" \
  -d '{"ticker": "AAPL"}'
curl http://localhost:8765/watchlist
```

期待出力: `{"tickers":["AAPL"]}`

```bash
kill %1
```

- [ ] **Step 3: 全テストが通ることを最終確認**

```bash
pytest tests/screener/ -v
```

期待出力: `21 passed`

- [ ] **Step 4: Electron + FastAPI を統合起動**

```bash
bash start.sh
```

期待動作:
- FastAPIサーバーが `localhost:8765` で起動
- Electronウィンドウが開き「株スクリーナー」タイトルが表示される
- 「チャート」タブで `AAPL` と入力してEnterを押すとローソク足チャートが表示される
- 「ウォッチリスト」タブで銘柄追加・削除ができる

- [ ] **Step 5: 最終コミット**

```bash
git add start.sh
git commit -m "feat: 起動スクリプト追加、株スクリーナー初期実装完了"
```
