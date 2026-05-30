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
_loop: Optional[asyncio.AbstractEventLoop] = None


def _on_alert(ticker: str, direction: str) -> None:
    """バックグラウンドスレッドから呼ばれる。メインのイベントループに送る。"""
    if _loop and not _loop.is_closed():
        payload = json.dumps({"type": "alert", "ticker": ticker, "direction": direction})
        asyncio.run_coroutine_threadsafe(_broadcast(payload), _loop)


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
    global _loop
    _loop = asyncio.get_running_loop()
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
        import numpy as np, math

        def _safe(v):
            if v is None:
                return None
            try:
                if math.isnan(v) or math.isinf(v):
                    return None
            except (TypeError, ValueError):
                pass
            return v

        df = df.replace([np.inf, -np.inf], np.nan).where(df.notna(), None)
        records = []
        for ts, row in df.iterrows():
            o, h, l, c = _safe(row["Open"]), _safe(row["High"]), _safe(row["Low"]), _safe(row["Close"])
            if None in (o, h, l, c):
                continue
            records.append({
                "time": int(ts.timestamp()),
                "open": o, "high": h, "low": l, "close": c,
                "volume": _safe(row["Volume"]) or 0,
                "ma5": _safe(row["ma5"]), "ma25": _safe(row["ma25"]), "ma75": _safe(row["ma75"]),
                "bb_upper": _safe(row["bb_upper"]), "bb_mid": _safe(row["bb_mid"]), "bb_lower": _safe(row["bb_lower"]),
                "rsi": _safe(row["rsi"]), "macd": _safe(row["macd"]),
                "macd_signal": _safe(row["macd_signal"]), "macd_hist": _safe(row["macd_hist"]),
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
async def get_vix_route():
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
