import os, sys
from unittest.mock import patch
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from scripts.notion_add_theme import classify_existing_page, _extract_theme_property


def test_classify_existing_page_calls_extract_theme():
    with patch("scripts.notion_add_theme.notion_read_page", return_value="バローロについての記事"), \
         patch("scripts.notion_add_theme.extract_theme", return_value="バローロ特集") as mock_extract:
        result = classify_existing_page("p1")
    mock_extract.assert_called_once_with("バローロについての記事")
    assert result == "バローロ特集"


def test_extract_theme_property_reads_rich_text():
    page = {"properties": {"テーマ": {"rich_text": [{"plain_text": "ピエモンテ州のネッビオーロ"}]}}}
    assert _extract_theme_property(page) == "ピエモンテ州のネッビオーロ"
    assert _extract_theme_property({"properties": {}}) == ""


def test_main_skips_pages_with_existing_theme(monkeypatch):
    import scripts.notion_add_theme as m
    monkeypatch.setenv("NOTION_API_KEY", "t")
    monkeypatch.setenv("NOTION_DATABASE_ID", "db")
    pages = [
        {"id": "done1", "properties": {"テーマ": {"rich_text": [{"plain_text": "既存テーマ"}]}}},
        {"id": "fresh1", "properties": {"テーマ": {"rich_text": []}}},
    ]
    with patch.object(m, "_ensure_theme_property"), \
         patch.object(m, "_iter_pages", return_value=iter(pages)), \
         patch.object(m, "classify_existing_page", return_value="新しいテーマ") as mock_cls, \
         patch.object(m, "_update_theme", return_value="ok") as mock_upd:
        m.main()
    mock_cls.assert_called_once_with("fresh1")
    mock_upd.assert_called_once_with("t", "fresh1", "新しいテーマ")


def test_main_skips_pages_when_extraction_fails(monkeypatch):
    import scripts.notion_add_theme as m
    monkeypatch.setenv("NOTION_API_KEY", "t")
    monkeypatch.setenv("NOTION_DATABASE_ID", "db")
    pages = [{"id": "empty1", "properties": {"テーマ": {"rich_text": []}}}]
    with patch.object(m, "_ensure_theme_property"), \
         patch.object(m, "_iter_pages", return_value=iter(pages)), \
         patch.object(m, "classify_existing_page", return_value="") as mock_cls, \
         patch.object(m, "_update_theme") as mock_upd:
        m.main()
    mock_cls.assert_called_once_with("empty1")
    mock_upd.assert_not_called()
