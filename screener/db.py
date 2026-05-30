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
