import os, sys
from unittest.mock import patch
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from scripts.notion_add_status import classify_existing_page


def test_classify_truncated(monkeypatch):
    with patch("scripts.notion_add_status.notion_read_page",
               return_value="樽熟成の期間は最低でも"):
        assert classify_existing_page("p1") == "途中"


def test_classify_complete(monkeypatch):
    long_done = "バローロはピエモンテを代表する赤ワインです。" * 5
    with patch("scripts.notion_add_status.notion_read_page", return_value=long_done):
        assert classify_existing_page("p1") == "要確認"


def test_extract_status_reads_select():
    from scripts.notion_add_status import _extract_status
    assert _extract_status({"properties": {"ステータス": {"select": {"name": "完成"}}}}) == "完成"
    assert _extract_status({"properties": {}}) == ""
    assert _extract_status({"properties": {"ステータス": {"select": None}}}) == ""


def test_main_skips_pages_with_existing_status(monkeypatch):
    import scripts.notion_add_status as m
    monkeypatch.setenv("NOTION_API_KEY", "t")
    monkeypatch.setenv("NOTION_DATABASE_ID", "db")
    pages = [
        {"id": "done1", "properties": {"ステータス": {"select": {"name": "完成"}}}},
        {"id": "fresh1", "properties": {"ステータス": {"select": None}}},
    ]
    with patch.object(m, "_ensure_status_property"), \
         patch.object(m, "_iter_pages", return_value=iter(pages)), \
         patch.object(m, "classify_existing_page", return_value="要確認") as mock_cls, \
         patch.object(m, "notion_update_status", return_value="ok") as mock_upd:
        m.main()
    # 完成 page skipped, only the statusless page classified + updated
    mock_cls.assert_called_once_with("fresh1")
    mock_upd.assert_called_once()
    assert mock_upd.call_args[0][0] == "fresh1"
