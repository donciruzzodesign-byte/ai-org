import threading
from typing import Callable, Optional

from screener.data import fetch_ohlcv
from screener.indicators import add_indicators, is_bb_breakout
from screener.db import get_watchlist, get_setting


class AlertMonitor:
    def __init__(self, on_alert: Callable[[str, str], None]):
        self._on_alert = on_alert
        self._thread: Optional[threading.Thread] = None
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
            try:
                interval = int(get_setting("alert_interval_minutes") or "15")
            except ValueError:
                interval = 15
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
