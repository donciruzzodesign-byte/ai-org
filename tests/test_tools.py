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
from datetime import datetime
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
    monkeypatch.delenv("NOTION_DATABASE_ID", raising=False)

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
    monkeypatch.delenv("NOTION_DATABASE_ID", raising=False)

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
    monkeypatch.delenv("NOTION_DATABASE_ID", raising=False)
    result = save_to_notion("タイトル", "内容")
    assert "未設定" in result


def test_save_to_notion_returns_error_when_child_page_fails(monkeypatch):
    monkeypatch.setenv("NOTION_API_KEY", "test-token")
    monkeypatch.setenv("NOTION_PAGE_ID", "parent-page-id")
    monkeypatch.delenv("NOTION_DATABASE_ID", raising=False)

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
    monkeypatch.delenv("NOTION_DATABASE_ID", raising=False)

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


def test_save_to_notion_saves_to_database_when_database_id_set(monkeypatch):
    """NOTION_DATABASE_ID があればデータベースにページを作成する。"""
    monkeypatch.setenv("NOTION_API_KEY", "test-token")
    monkeypatch.setenv("NOTION_PAGE_ID", "parent-page-id")
    monkeypatch.setenv("NOTION_DATABASE_ID", "db-id-123")

    create_resp = MagicMock()
    create_resp.status_code = 200
    create_resp.json.return_value = {"id": "row-id"}

    patch_resp = MagicMock()
    patch_resp.status_code = 200
    patch_resp.json.return_value = {}

    with patch("tools.requests.post", return_value=create_resp) as mock_post, \
         patch("tools.requests.patch", return_value=patch_resp) as mock_patch:
        result = save_to_notion("火曜：コーヒー動画台本作成 (2026-07-07)", "## 内容")

    assert "Notionにデータベースページを作成しました" in result
    post_payload = mock_post.call_args[1]["json"]
    assert post_payload["parent"] == {"database_id": "db-id-123"}
    assert post_payload["properties"]["カテゴリ"] == {"select": {"name": "コーヒー"}}
    patch_url = mock_patch.call_args[0][0]
    assert "row-id" in patch_url


def test_save_to_notion_database_error(monkeypatch):
    monkeypatch.setenv("NOTION_API_KEY", "test-token")
    monkeypatch.setenv("NOTION_DATABASE_ID", "db-id-123")

    create_resp = MagicMock()
    create_resp.status_code = 400
    create_resp.json.return_value = {"message": "bad request"}

    with patch("tools.requests.post", return_value=create_resp):
        result = save_to_notion("タイトル", "内容")

    assert "ページ作成エラー" in result


def test_infer_category():
    from tools import _infer_category
    assert _infer_category("月曜：コーヒーテーマ決定", "") == "コーヒー"
    assert _infer_category("月曜：州別おすすめワイン紹介", "") == "ワイン"
    assert _infer_category("月曜：今週テーマ決定", "バローロはワインの王様") == "ワイン"
    assert _infer_category("日曜：反応分析", "エスプレッソとコーヒー文化") == "コーヒー"
    assert _infer_category("レポート", "特に言及なし") == "その他"


from tools import _detect_completion_status


def test_detect_status_complete_sentence():
    # 句点で締めくくられた十分な長さ → 要確認
    text = "バローロはピエモンテを代表する赤ワインです。" * 5
    assert _detect_completion_status(text) == "要確認"


def test_detect_status_truncated_midsentence():
    # 文の途中でブツ切れ（句読点・記号で終わらない） → 途中
    text = "バローロの熟成についてこれから詳しく説明していきます。まず樽熟成の期間について触れると" * 2 + "最低でも三年間は"
    assert _detect_completion_status(text) == "途中"


def test_detect_status_too_short():
    # 極端に短い → 途中
    assert _detect_completion_status("テーマ決定。") == "途中"


def test_detect_status_closing_bracket_ok():
    # 閉じ括弧で終わる十分な長さ → 要確認
    text = "詳しいペアリングの提案はこちらの一覧を参照してください。おすすめは白ワインとの組み合わせです" * 2 + "（詳細は本文を参照）"
    assert _detect_completion_status(text) == "要確認"


def test_detect_status_empty():
    assert _detect_completion_status("") == "途中"


def test_save_to_notion_sets_status_on_database_page(monkeypatch):
    monkeypatch.setenv("NOTION_API_KEY", "test-token")
    monkeypatch.setenv("NOTION_DATABASE_ID", "db-id-123")
    monkeypatch.delenv("NOTION_PAGE_ID", raising=False)

    create_resp = MagicMock()
    create_resp.status_code = 200
    create_resp.json.return_value = {"id": "row-id"}
    patch_resp = MagicMock()
    patch_resp.status_code = 200
    patch_resp.json.return_value = {}

    with patch("tools.requests.post", return_value=create_resp) as mock_post, \
         patch("tools.requests.patch", return_value=patch_resp):
        save_to_notion("火曜：ワイン動画台本 (2026-07-16)", "## 内容\n本文", status="途中")

    props = mock_post.call_args[1]["json"]["properties"]
    assert props["ステータス"] == {"select": {"name": "途中"}}


def test_save_to_notion_default_status_is_yokakunin(monkeypatch):
    monkeypatch.setenv("NOTION_API_KEY", "test-token")
    monkeypatch.setenv("NOTION_DATABASE_ID", "db-id-123")
    monkeypatch.delenv("NOTION_PAGE_ID", raising=False)

    create_resp = MagicMock()
    create_resp.status_code = 200
    create_resp.json.return_value = {"id": "row-id"}
    patch_resp = MagicMock()
    patch_resp.status_code = 200
    patch_resp.json.return_value = {}

    with patch("tools.requests.post", return_value=create_resp) as mock_post, \
         patch("tools.requests.patch", return_value=patch_resp):
        save_to_notion("タイトル", "## 内容\n本文")

    props = mock_post.call_args[1]["json"]["properties"]
    assert props["ステータス"] == {"select": {"name": "要確認"}}


from tools import (
    notion_find_wip, notion_read_page, notion_update_status,
    notion_append_to_page, execute_tool, TOOL_DEFINITIONS,
)


def test_notion_find_wip_filters_status_and_category(monkeypatch):
    monkeypatch.setenv("NOTION_API_KEY", "test-token")
    monkeypatch.setenv("NOTION_DATABASE_ID", "db-id-123")

    resp = MagicMock()
    resp.status_code = 200
    resp.json.return_value = {
        "results": [
            {"id": "p1",
             "properties": {
                 # Notionのクエリ応答はタイトル列を実際の列名（例『名前』）でキー付けし type=title を持つ
                 "名前": {"type": "title", "title": [{"plain_text": "火曜：ワイン台本"}]},
                 "カテゴリ": {"select": {"name": "ワイン"}},
             }},
        ]
    }
    with patch("tools.requests.post", return_value=resp) as mock_post:
        out = notion_find_wip("ワイン")

    body = mock_post.call_args[1]["json"]
    # ステータス=途中 と カテゴリ=ワイン の and フィルタ
    assert body["filter"]["and"][0]["select"]["equals"] == "途中"
    assert body["filter"]["and"][1]["select"]["equals"] == "ワイン"
    assert "p1" in out
    assert "火曜：ワイン台本" in out


def test_notion_find_wip_none(monkeypatch):
    monkeypatch.setenv("NOTION_API_KEY", "test-token")
    monkeypatch.setenv("NOTION_DATABASE_ID", "db-id-123")
    resp = MagicMock()
    resp.status_code = 200
    resp.json.return_value = {"results": []}
    with patch("tools.requests.post", return_value=resp):
        out = notion_find_wip("ワイン")
    assert "ありません" in out


def test_notion_find_wip_joins_multi_run_title(monkeypatch):
    monkeypatch.setenv("NOTION_API_KEY", "test-token")
    monkeypatch.setenv("NOTION_DATABASE_ID", "db-id-123")
    resp = MagicMock()
    resp.status_code = 200
    resp.json.return_value = {
        "results": [
            {"id": "p1",
             "properties": {
                 "名前": {"type": "title",
                         "title": [{"plain_text": "火曜："}, {"plain_text": "ワイン台本"}]},
                 "カテゴリ": {"select": {"name": "ワイン"}},
             }},
        ]
    }
    with patch("tools.requests.post", return_value=resp):
        out = notion_find_wip("ワイン")
    assert "火曜：ワイン台本" in out


def test_extract_title_finds_title_by_type_not_key():
    from tools import _extract_title
    # タイトル列名は任意（『名前』など）。固定キー'title'ではなく type=title で判別する
    props = {
        "名前": {"type": "title", "title": [{"plain_text": "月曜："}, {"plain_text": "テーマ決定"}]},
        "カテゴリ": {"select": {"name": "ワイン"}},
        "ステータス": {"type": "select", "select": {"name": "途中"}},
    }
    assert _extract_title(props) == "月曜：テーマ決定"
    # タイトル列が無ければ空文字
    assert _extract_title({"カテゴリ": {"select": {"name": "ワイン"}}}) == ""


def test_notion_read_page_joins_text(monkeypatch):
    monkeypatch.setenv("NOTION_API_KEY", "test-token")
    resp = MagicMock()
    resp.status_code = 200
    resp.json.return_value = {
        "has_more": False,
        "results": [
            {"type": "heading_2", "heading_2": {"rich_text": [{"plain_text": "オープニング"}]}},
            {"type": "paragraph", "paragraph": {"rich_text": [{"plain_text": "こんにちは"}]}},
        ],
    }
    with patch("tools.requests.get", return_value=resp):
        out = notion_read_page("page-1")
    assert "オープニング" in out
    assert "こんにちは" in out


def test_notion_update_status_patches(monkeypatch):
    monkeypatch.setenv("NOTION_API_KEY", "test-token")
    resp = MagicMock()
    resp.status_code = 200
    resp.json.return_value = {}
    with patch("tools.requests.patch", return_value=resp) as mock_patch:
        out = notion_update_status("page-1", "完成")
    url = mock_patch.call_args[0][0]
    body = mock_patch.call_args[1]["json"]
    assert "page-1" in url
    assert body["properties"]["ステータス"] == {"select": {"name": "完成"}}
    assert "完成" in out


def test_notion_tools_registered():
    names = {t["name"] for t in TOOL_DEFINITIONS}
    assert {"notion_find_wip", "notion_read_page", "notion_update_status"} <= names


def test_execute_tool_dispatches_notion_read(monkeypatch):
    monkeypatch.setenv("NOTION_API_KEY", "test-token")
    resp = MagicMock()
    resp.status_code = 200
    resp.json.return_value = {"has_more": False, "results": []}
    with patch("tools.requests.get", return_value=resp):
        out = execute_tool("notion_read_page", {"page_id": "p1"})
    assert isinstance(out, str)


def test_notion_find_wip_skips_without_env(monkeypatch):
    monkeypatch.delenv("NOTION_API_KEY", raising=False)
    monkeypatch.delenv("NOTION_DATABASE_ID", raising=False)
    out = notion_find_wip("ワイン")
    assert "未設定" in out


def test_extract_theme_returns_summary_text():
    from tools import extract_theme
    fake_client = MagicMock()
    fake_resp = MagicMock()
    fake_resp.content = [MagicMock(text="ピエモンテ州のネッビオーロ特集", spec=["text"])]
    fake_client.messages.create.return_value = fake_resp
    with patch("tools._get_anthropic_client", return_value=fake_client):
        result = extract_theme("今週はピエモンテ州のネッビオーロについて特集します。" * 3)
    assert result == "ピエモンテ州のネッビオーロ特集"
    fake_client.messages.create.assert_called_once()
    kwargs = fake_client.messages.create.call_args.kwargs
    assert kwargs["model"] == "claude-haiku-4-5-20251001"


def test_extract_theme_returns_empty_on_exception():
    from tools import extract_theme
    with patch("tools._get_anthropic_client", side_effect=Exception("no api key")):
        result = extract_theme("何かの内容")
    assert result == ""


def test_extract_theme_returns_empty_for_empty_content():
    from tools import extract_theme
    assert extract_theme("") == ""
    assert extract_theme("   ") == ""


def test_extract_rich_text_joins_plain_text():
    from tools import _extract_rich_text
    prop = {"rich_text": [{"plain_text": "ピエモンテ州の"}, {"plain_text": "ネッビオーロ"}]}
    assert _extract_rich_text(prop) == "ピエモンテ州のネッビオーロ"
    assert _extract_rich_text({"rich_text": []}) == ""
    assert _extract_rich_text({}) == ""
    assert _extract_rich_text(None) == ""


def test_notion_recent_themes_queries_by_category_sorted_desc(monkeypatch):
    from tools import notion_recent_themes
    monkeypatch.setenv("NOTION_API_KEY", "test-token")
    monkeypatch.setenv("NOTION_DATABASE_ID", "db-id-123")

    resp = MagicMock()
    resp.status_code = 200
    resp.json.return_value = {
        "results": [
            {"properties": {
                "名前": {"type": "title", "title": [{"plain_text": "月曜：今週テーマ決定 (2026-07-20)"}]},
                "テーマ": {"rich_text": [{"plain_text": "ピエモンテ州のネッビオーロ"}]},
            }},
            {"properties": {
                "名前": {"type": "title", "title": [{"plain_text": "月曜：州別おすすめワイン紹介 (2026-07-13)"}]},
                "テーマ": {"rich_text": [{"plain_text": "トスカーナ州のサンジョヴェーゼ"}]},
            }},
        ]
    }
    with patch("tools.requests.post", return_value=resp) as mock_post:
        out = notion_recent_themes("ワイン", limit=8)

    body = mock_post.call_args[1]["json"]
    assert body["filter"]["and"][0] == {"property": "カテゴリ", "select": {"equals": "ワイン"}}
    assert "created_time" in body["filter"]["and"][1]
    assert "before" in body["filter"]["and"][1]["created_time"]
    assert body["sorts"] == [{"timestamp": "created_time", "direction": "descending"}]
    assert body["page_size"] == 8
    assert "ピエモンテ州のネッビオーロ" in out
    assert "トスカーナ州のサンジョヴェーゼ" in out
    assert "月曜：今週テーマ決定 (2026-07-20)" in out


def test_notion_recent_themes_scopes_query_to_before_current_week(monkeypatch):
    """今週月曜00:00より前に作成されたページのみを対象とするフィルタが送信されること。"""
    from tools import notion_recent_themes

    monkeypatch.setenv("NOTION_API_KEY", "test-token")
    monkeypatch.setenv("NOTION_DATABASE_ID", "db-id-123")

    resp = MagicMock()
    resp.status_code = 200
    resp.json.return_value = {"results": []}

    fixed_now = datetime(2026, 7, 30, 15, 0, 0)  # 木曜
    expected_week_start = datetime(2026, 7, 27, 0, 0, 0).isoformat()  # 直前の月曜00:00

    with patch("tools.datetime") as mock_datetime, \
         patch("tools.requests.post", return_value=resp) as mock_post:
        mock_datetime.now.return_value = fixed_now
        notion_recent_themes("ワイン")

    body = mock_post.call_args[1]["json"]
    created_time_filter = body["filter"]["and"][1]["created_time"]
    assert created_time_filter == {"before": expected_week_start}


def test_notion_recent_themes_skips_pages_without_theme(monkeypatch):
    from tools import notion_recent_themes
    monkeypatch.setenv("NOTION_API_KEY", "test-token")
    monkeypatch.setenv("NOTION_DATABASE_ID", "db-id-123")
    resp = MagicMock()
    resp.status_code = 200
    resp.json.return_value = {
        "results": [
            {"properties": {
                "名前": {"type": "title", "title": [{"plain_text": "古いページ"}]},
                "テーマ": {"rich_text": []},
            }},
        ]
    }
    with patch("tools.requests.post", return_value=resp):
        out = notion_recent_themes("ワイン")
    assert out == ""


def test_notion_recent_themes_returns_empty_without_env(monkeypatch):
    from tools import notion_recent_themes
    monkeypatch.delenv("NOTION_API_KEY", raising=False)
    monkeypatch.delenv("NOTION_DATABASE_ID", raising=False)
    assert notion_recent_themes("ワイン") == ""


def test_notion_recent_themes_returns_empty_on_error(monkeypatch):
    from tools import notion_recent_themes
    monkeypatch.setenv("NOTION_API_KEY", "test-token")
    monkeypatch.setenv("NOTION_DATABASE_ID", "db-id-123")
    resp = MagicMock()
    resp.status_code = 400
    resp.json.return_value = {"message": "bad"}
    with patch("tools.requests.post", return_value=resp):
        out = notion_recent_themes("ワイン")
    assert out == ""


def test_save_to_notion_includes_theme_property_when_provided(monkeypatch):
    monkeypatch.setenv("NOTION_API_KEY", "test-token")
    monkeypatch.setenv("NOTION_DATABASE_ID", "db-id-123")
    monkeypatch.delenv("NOTION_PAGE_ID", raising=False)

    create_resp = MagicMock()
    create_resp.status_code = 200
    create_resp.json.return_value = {"id": "row-id"}
    patch_resp = MagicMock()
    patch_resp.status_code = 200
    patch_resp.json.return_value = {}

    with patch("tools.requests.post", return_value=create_resp) as mock_post, \
         patch("tools.requests.patch", return_value=patch_resp):
        save_to_notion("タイトル", "## 内容", theme="ピエモンテ州のネッビオーロ")

    props = mock_post.call_args[1]["json"]["properties"]
    assert props["テーマ"] == {"rich_text": [{"text": {"content": "ピエモンテ州のネッビオーロ"}}]}


def test_save_to_notion_omits_theme_property_when_not_provided(monkeypatch):
    monkeypatch.setenv("NOTION_API_KEY", "test-token")
    monkeypatch.setenv("NOTION_DATABASE_ID", "db-id-123")
    monkeypatch.delenv("NOTION_PAGE_ID", raising=False)

    create_resp = MagicMock()
    create_resp.status_code = 200
    create_resp.json.return_value = {"id": "row-id"}
    patch_resp = MagicMock()
    patch_resp.status_code = 200
    patch_resp.json.return_value = {}

    with patch("tools.requests.post", return_value=create_resp) as mock_post, \
         patch("tools.requests.patch", return_value=patch_resp):
        save_to_notion("タイトル", "## 内容")

    props = mock_post.call_args[1]["json"]["properties"]
    assert "テーマ" not in props


def test_notion_append_to_page_updates_theme_when_provided(monkeypatch):
    monkeypatch.setenv("NOTION_API_KEY", "test-token")
    blocks_resp = MagicMock()
    blocks_resp.status_code = 200
    patch_resp = MagicMock()
    patch_resp.status_code = 200
    patch_resp.json.return_value = {}
    with patch("tools.requests.patch", side_effect=[blocks_resp, patch_resp]) as mock_patch:
        out = notion_append_to_page("page-1", "追記内容", status="要確認", theme="トスカーナ州のサンジョヴェーゼ")

    props_call = mock_patch.call_args_list[1]
    body = props_call[1]["json"]
    assert body["properties"]["テーマ"] == {"rich_text": [{"text": {"content": "トスカーナ州のサンジョヴェーゼ"}}]}
    assert body["properties"]["ステータス"] == {"select": {"name": "要確認"}}
    assert "要確認" in out


def test_notion_append_to_page_omits_theme_when_not_provided(monkeypatch):
    monkeypatch.setenv("NOTION_API_KEY", "test-token")
    blocks_resp = MagicMock()
    blocks_resp.status_code = 200
    patch_resp = MagicMock()
    patch_resp.status_code = 200
    patch_resp.json.return_value = {}
    with patch("tools.requests.patch", side_effect=[blocks_resp, patch_resp]) as mock_patch:
        notion_append_to_page("page-1", "追記内容", status="要確認")

    body = mock_patch.call_args_list[1][1]["json"]
    assert "テーマ" not in body["properties"]


import json
import tools
from tools import list_reference_post_files, scan_reference_posts, archive_reference_posts, execute_tool


def test_list_reference_post_files_returns_empty_when_no_folder(tmp_path, monkeypatch):
    monkeypatch.setattr(tools, "_REFERENCE_POSTS_ROOT", str(tmp_path))
    assert list_reference_post_files("wine") == []


def test_list_reference_post_files_ignores_non_images_and_archive(tmp_path, monkeypatch):
    monkeypatch.setattr(tools, "_REFERENCE_POSTS_ROOT", str(tmp_path))
    posts_dir = tmp_path / "wine"
    posts_dir.mkdir()
    (posts_dir / "post1.jpg").write_bytes(b"a")
    (posts_dir / "note.txt").write_text("x")
    (posts_dir / "archive").mkdir()

    assert list_reference_post_files("wine") == ["post1.jpg"]


def test_scan_reference_posts_returns_empty_when_no_folder(tmp_path, monkeypatch):
    monkeypatch.setattr(tools, "_REFERENCE_POSTS_ROOT", str(tmp_path))
    assert scan_reference_posts("wine") == "[]"


def test_scan_reference_posts_analyzes_each_image(tmp_path, monkeypatch):
    monkeypatch.setattr(tools, "_REFERENCE_POSTS_ROOT", str(tmp_path))
    posts_dir = tmp_path / "wine"
    posts_dir.mkdir()
    (posts_dir / "post1.jpg").write_bytes(b"a")
    (posts_dir / "post2.png").write_bytes(b"b")

    with patch("tools.analyze_image", return_value="解析結果") as mock_analyze:
        result = scan_reference_posts("wine")

    data = json.loads(result)
    assert len(data) == 2
    files = {d["file"] for d in data}
    assert files == {"post1.jpg", "post2.png"}
    assert all(d["analysis"] == "解析結果" for d in data)
    assert mock_analyze.call_count == 2


def test_archive_reference_posts_returns_message_when_no_files(tmp_path, monkeypatch):
    monkeypatch.setattr(tools, "_REFERENCE_POSTS_ROOT", str(tmp_path))
    assert archive_reference_posts("wine") == "アーカイブ対象なし"


def test_archive_reference_posts_moves_files_into_dated_folder(tmp_path, monkeypatch):
    monkeypatch.setattr(tools, "_REFERENCE_POSTS_ROOT", str(tmp_path))
    posts_dir = tmp_path / "wine"
    posts_dir.mkdir()
    (posts_dir / "post1.jpg").write_bytes(b"a")

    result = archive_reference_posts("wine")

    assert "1件" in result
    assert not (posts_dir / "post1.jpg").exists()
    archived = list((posts_dir / "archive").glob("*/post1.jpg"))
    assert len(archived) == 1
    assert list_reference_post_files("wine") == []


def test_execute_tool_dispatches_analyze_image(tmp_path):
    img = tmp_path / "x.png"
    img.write_bytes(b"a")
    with patch("tools.analyze_image", return_value="ok") as mock_analyze:
        result = execute_tool("analyze_image", {"image_path": str(img), "question": "何"})
    assert result == "ok"
    mock_analyze.assert_called_once_with(str(img), "何")


def test_execute_tool_dispatches_scan_reference_posts(tmp_path, monkeypatch):
    monkeypatch.setattr(tools, "_REFERENCE_POSTS_ROOT", str(tmp_path))
    result = execute_tool("scan_reference_posts", {"category": "wine"})
    assert result == "[]"
