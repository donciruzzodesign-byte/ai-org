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
