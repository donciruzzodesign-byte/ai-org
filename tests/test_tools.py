import os
import sys
import pytest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from tools import _parse_content_to_blocks


def test_heading1():
    blocks = _parse_content_to_blocks("# タイトル")
    assert blocks == [
        {"object": "block", "type": "heading_1",
         "heading_1": {"rich_text": [{"text": {"content": "タイトル"}}]}}
    ]


def test_heading2_inserts_divider_before():
    blocks = _parse_content_to_blocks("## セクション")
    assert blocks[0] == {"object": "block", "type": "divider", "divider": {}}
    assert blocks[1] == {
        "object": "block", "type": "heading_2",
        "heading_2": {"rich_text": [{"text": {"content": "セクション"}}]}
    }


def test_heading3():
    blocks = _parse_content_to_blocks("### 小見出し")
    assert blocks == [
        {"object": "block", "type": "heading_3",
         "heading_3": {"rich_text": [{"text": {"content": "小見出し"}}]}}
    ]


def test_bulleted_list_hyphen():
    blocks = _parse_content_to_blocks("- 箇条書き")
    assert blocks == [
        {"object": "block", "type": "bulleted_list_item",
         "bulleted_list_item": {"rich_text": [{"text": {"content": "箇条書き"}}]}}
    ]


def test_bulleted_list_asterisk():
    blocks = _parse_content_to_blocks("* 箇条書き")
    assert blocks == [
        {"object": "block", "type": "bulleted_list_item",
         "bulleted_list_item": {"rich_text": [{"text": {"content": "箇条書き"}}]}}
    ]


def test_numbered_list():
    blocks = _parse_content_to_blocks("1. 番号付き")
    assert blocks == [
        {"object": "block", "type": "numbered_list_item",
         "numbered_list_item": {"rich_text": [{"text": {"content": "番号付き"}}]}}
    ]


def test_empty_line_skipped():
    blocks = _parse_content_to_blocks("\n\n")
    assert blocks == []


def test_plain_text_becomes_paragraph():
    blocks = _parse_content_to_blocks("普通のテキスト")
    assert blocks == [
        {"object": "block", "type": "paragraph",
         "paragraph": {"rich_text": [{"text": {"content": "普通のテキスト"}}]}}
    ]


def test_multiline_mixed():
    content = "## オープニング\n- 箇条書き1\n- 箇条書き2\n\n普通のテキスト"
    blocks = _parse_content_to_blocks(content)
    types = [b["type"] for b in blocks]
    assert types == ["divider", "heading_2", "bulleted_list_item", "bulleted_list_item", "paragraph"]


from unittest.mock import patch, MagicMock
from tools import _create_child_page


def test_create_child_page_calls_post(monkeypatch):
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"id": "child-page-id-123"}

    with patch("tools.requests.post", return_value=mock_resp) as mock_post:
        child_id = _create_child_page(
            token="tok",
            parent_page_id="parent-id",
            title="火曜：動画台本 (2026-05-30)"
        )

    mock_post.assert_called_once()
    call_kwargs = mock_post.call_args
    assert call_kwargs[0][0] == "https://api.notion.com/v1/pages"
    payload = call_kwargs[1]["json"]
    assert payload["parent"] == {"page_id": "parent-id"}
    assert payload["properties"]["title"][0]["text"]["content"] == "火曜：動画台本 (2026-05-30)"
    assert child_id == "child-page-id-123"


def test_create_child_page_returns_none_on_error(monkeypatch):
    mock_resp = MagicMock()
    mock_resp.status_code = 400
    mock_resp.json.return_value = {"message": "bad request"}

    with patch("tools.requests.post", return_value=mock_resp):
        child_id = _create_child_page(
            token="tok",
            parent_page_id="parent-id",
            title="テスト"
        )
    assert child_id is None


from tools import save_to_notion


def test_save_to_notion_creates_child_page_and_adds_blocks(monkeypatch):
    monkeypatch.setenv("NOTION_API_KEY", "test-token")
    monkeypatch.setenv("NOTION_PAGE_ID", "parent-page-id")

    create_resp = MagicMock()
    create_resp.status_code = 200
    create_resp.json.return_value = {"id": "child-id-abc"}

    patch_resp = MagicMock()
    patch_resp.status_code = 200
    patch_resp.json.return_value = {}

    with patch("tools.requests.post", return_value=create_resp) as mock_post, \
         patch("tools.requests.patch", return_value=patch_resp) as mock_patch:
        result = save_to_notion("火曜：動画台本作成", "## オープニング\n- こんにちは")

    assert "Notionに子ページを作成しました" in result
    mock_post.assert_called_once()
    mock_patch.assert_called_once()
    patch_url = mock_patch.call_args[0][0]
    assert "child-id-abc" in patch_url


def test_save_to_notion_chunks_over_100_blocks(monkeypatch):
    monkeypatch.setenv("NOTION_API_KEY", "test-token")
    monkeypatch.setenv("NOTION_PAGE_ID", "parent-page-id")

    create_resp = MagicMock()
    create_resp.status_code = 200
    create_resp.json.return_value = {"id": "child-id-abc"}

    patch_resp = MagicMock()
    patch_resp.status_code = 200
    patch_resp.json.return_value = {}

    # 150行の箇条書きを生成（150ブロック → 2回に分割されるはず）
    content = "\n".join(f"- 項目{i}" for i in range(150))

    with patch("tools.requests.post", return_value=create_resp), \
         patch("tools.requests.patch", return_value=patch_resp) as mock_patch:
        save_to_notion("テスト", content)

    assert mock_patch.call_count == 2
    first_call_blocks = mock_patch.call_args_list[0][1]["json"]["children"]
    second_call_blocks = mock_patch.call_args_list[1][1]["json"]["children"]
    assert len(first_call_blocks) == 100
    assert len(second_call_blocks) == 50


def test_save_to_notion_returns_skip_when_env_not_set(monkeypatch):
    monkeypatch.delenv("NOTION_API_KEY", raising=False)
    monkeypatch.delenv("NOTION_PAGE_ID", raising=False)
    result = save_to_notion("タイトル", "内容")
    assert "未設定" in result


def test_save_to_notion_returns_error_when_child_page_fails(monkeypatch):
    monkeypatch.setenv("NOTION_API_KEY", "test-token")
    monkeypatch.setenv("NOTION_PAGE_ID", "parent-page-id")

    create_resp = MagicMock()
    create_resp.status_code = 400
    create_resp.json.return_value = {"message": "bad request"}

    with patch("tools.requests.post", return_value=create_resp):
        result = save_to_notion("タイトル", "内容")

    assert "子ページ作成エラー" in result


def test_save_to_notion_saves_under_parent(monkeypatch):
    """親ページ直下に子ページを作成する。"""
    monkeypatch.setenv("NOTION_API_KEY", "test-token")
    monkeypatch.setenv("NOTION_PAGE_ID", "parent-page-id")

    create_resp = MagicMock()
    create_resp.status_code = 200
    create_resp.json.return_value = {"id": "child-id"}

    patch_resp = MagicMock()
    patch_resp.status_code = 200
    patch_resp.json.return_value = {}

    with patch("tools.requests.post", return_value=create_resp) as mock_post, \
         patch("tools.requests.patch", return_value=patch_resp):
        result = save_to_notion("テスト", "内容")

    assert "Notionに子ページを作成しました" in result
    post_payload = mock_post.call_args[1]["json"]
    assert post_payload["parent"] == {"page_id": "parent-page-id"}
