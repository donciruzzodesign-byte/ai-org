import pytest
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
