import os
import sys
import tempfile
import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from runner import run_agent, run_video_agent, tuesday_video_task, coffee_tuesday_video_task


def _stream_cm(resp):
    """client.messages.stream(...) の with構文をモックするコンテキストマネージャを作る。"""
    cm = MagicMock()
    cm.__enter__.return_value.get_final_message.return_value = resp
    return cm


def test_save_log_creates_file_with_content():
    import runner
    from datetime import datetime
    with tempfile.TemporaryDirectory() as tmpdir:
        with patch('runner.__file__', os.path.join(tmpdir, 'runner.py')):
            runner.save_log('テストログ内容', '月曜：テーマ決定')
            now = datetime.now()
            log_dir = os.path.join(tmpdir, 'logs', now.strftime('%Y-%m'))
            assert os.path.isdir(log_dir), f"ログディレクトリが作成されていません: {log_dir}"
            log_files = os.listdir(log_dir)
            assert len(log_files) == 1

            log_path = os.path.join(log_dir, log_files[0])
            with open(log_path, encoding='utf-8') as f:
                content = f.read()
            assert 'テストログ内容' in content
            assert '月曜：テーマ決定' in content


def test_run_agent_calls_api_and_saves_log():
    import runner
    mock_response = MagicMock()
    mock_response.content = [MagicMock(text='AIの返答テキスト')]

    with tempfile.TemporaryDirectory() as tmpdir:
        agents_dir = os.path.join(tmpdir, 'agents')
        os.makedirs(agents_dir)
        with open(os.path.join(agents_dir, 'sommelier.txt'), 'w', encoding='utf-8') as f:
            f.write('ソムリエシステムプロンプト')

        with patch('runner.__file__', os.path.join(tmpdir, 'runner.py')), \
             patch('runner.client') as mock_client:
            mock_client.messages.stream.return_value.__enter__.return_value.get_final_message.return_value = mock_response
            result = runner.run_agent('sommelier', 'テーマを提案してください', '月曜：テーマ決定')

        assert result == 'AIの返答テキスト'
        mock_client.messages.stream.assert_called_once()


def test_coffee_task_functions_are_callable():
    import runner
    assert callable(runner.coffee_monday_task), "coffee_monday_task が存在しません"
    assert callable(runner.coffee_regional_task), "coffee_regional_task が存在しません"
    assert callable(runner.coffee_tuesday_task), "coffee_tuesday_task が存在しません"
    assert callable(runner.coffee_friday_task), "coffee_friday_task が存在しません"


def test_run_agent_saves_to_notion():
    """run_agent の最終出力が save_to_notion に渡される。"""
    today = datetime.now().strftime('%Y-%m-%d')

    fake_response = MagicMock()
    fake_response.stop_reason = "end_turn"
    fake_response.content = [MagicMock(text="テスト出力", spec=["text"])]

    with patch("runner.client.messages.stream", return_value=_stream_cm(fake_response)), \
         patch("runner.save_to_notion", return_value="OK") as mock_notion, \
         patch("runner.save_log"):
        run_agent("sommelier", "テスト", "テストラベル")

    mock_notion.assert_called_once_with(f"テストラベル ({today})", "テスト出力", status="要確認", theme="")


def test_run_video_agent_calls_video_tools(tmp_path):
    """run_video_agent がツール定義を使って Claude を呼び出すことを確認（デフォルトはVIDEO_TOOL_DEFINITIONS_FREE）。"""
    import runner

    tool_use_block = MagicMock()
    tool_use_block.type = "tool_use"
    tool_use_block.name = "generate_narration"
    tool_use_block.id = "tu_01"
    tool_use_block.input = {"script_text": "台本", "output_dir": str(tmp_path)}

    tool_use_response = MagicMock()
    tool_use_response.stop_reason = "tool_use"
    tool_use_response.content = [tool_use_block]

    final_block = MagicMock()
    final_block.text = "素材生成完了"
    final_response = MagicMock()
    final_response.stop_reason = "end_turn"
    final_response.content = [final_block]

    with patch("runner.client.messages.create", side_effect=[tool_use_response, final_response]), \
         patch("runner.execute_video_tool", return_value="ナレーション保存: narration.mp3") as mock_exec, \
         patch("runner.save_log"):
        result = run_video_agent("台本テキスト", "イタリアワイン", str(tmp_path))

    mock_exec.assert_called_once_with("generate_narration", {"script_text": "台本", "output_dir": str(tmp_path)})
    assert result == "素材生成完了"


def test_run_video_agent_default_excludes_paid_tool(tmp_path):
    final_block = MagicMock()
    final_block.text = "完了"
    final_response = MagicMock()
    final_response.stop_reason = "end_turn"
    final_response.content = [final_block]

    with patch("runner.client.messages.create", return_value=final_response) as mock_create, \
         patch("runner.save_log"):
        run_video_agent("台本", "イタリアワイン", str(tmp_path))

    sent_tools = mock_create.call_args[1]["tools"]
    tool_names = [t["name"] for t in sent_tools]
    assert "generate_scene_video" not in tool_names


def test_run_video_agent_allow_paid_video_includes_paid_tool(tmp_path):
    final_block = MagicMock()
    final_block.text = "完了"
    final_response = MagicMock()
    final_response.stop_reason = "end_turn"
    final_response.content = [final_block]

    with patch("runner.client.messages.create", return_value=final_response) as mock_create, \
         patch("runner.save_log"):
        run_video_agent("台本", "イタリアワイン", str(tmp_path), allow_paid_video=True)

    sent_tools = mock_create.call_args[1]["tools"]
    tool_names = [t["name"] for t in sent_tools]
    assert "generate_scene_video" in tool_names


def test_run_video_agent_default_appends_paid_tool_constraint_to_system_prompt(tmp_path):
    final_block = MagicMock()
    final_block.text = "完了"
    final_response = MagicMock()
    final_response.stop_reason = "end_turn"
    final_response.content = [final_block]

    with patch("runner.client.messages.create", return_value=final_response) as mock_create, \
         patch("runner.save_log"):
        run_video_agent("台本", "イタリアワイン", str(tmp_path))

    sent_system = mock_create.call_args[1]["system"]
    assert "generate_scene_video" in sent_system
    assert "使用できません" in sent_system


def test_run_video_agent_allow_paid_video_omits_constraint_from_system_prompt(tmp_path):
    final_block = MagicMock()
    final_block.text = "完了"
    final_response = MagicMock()
    final_response.stop_reason = "end_turn"
    final_response.content = [final_block]

    with patch("runner.client.messages.create", return_value=final_response) as mock_create, \
         patch("runner.save_log"):
        run_video_agent("台本", "イタリアワイン", str(tmp_path), allow_paid_video=True)

    sent_system = mock_create.call_args[1]["system"]
    assert "今回の制約" not in sent_system


def test_tuesday_video_task_passes_consumed_flag_to_run_video_agent():
    with patch("runner.consume_paid_video_flag", return_value=True) as mock_flag, \
         patch("runner.run_video_agent") as mock_run, \
         patch("runner._read_todays_log", return_value="台本"):
        tuesday_video_task()

    mock_flag.assert_called_once()
    assert mock_run.call_args[1]["allow_paid_video"] is True


def test_coffee_tuesday_video_task_passes_consumed_flag_to_run_video_agent():
    with patch("runner.consume_paid_video_flag", return_value=False) as mock_flag, \
         patch("runner.run_video_agent") as mock_run, \
         patch("runner._read_todays_log", return_value="台本"):
        coffee_tuesday_video_task()

    mock_flag.assert_called_once()
    assert mock_run.call_args[1]["allow_paid_video"] is False


def test_tuesday_video_task_catches_exception(monkeypatch):
    with patch("runner.run_video_agent", side_effect=Exception("API error")):
        tuesday_video_task()


def test_coffee_tuesday_video_task_catches_exception(monkeypatch):
    with patch("runner.run_video_agent", side_effect=Exception("API error")):
        coffee_tuesday_video_task()


def _text_response(text, stop_reason):
    block = MagicMock()
    block.type = "text"
    block.text = text
    resp = MagicMock()
    resp.stop_reason = stop_reason
    resp.content = [block]
    return resp


def test_run_agent_saves_yokakunin_on_normal_finish(monkeypatch):
    import runner
    resp = _text_response("完成した台本です。ここまでで終わり。", "end_turn")
    with patch.object(runner.client.messages, "stream", return_value=_stream_cm(resp)), \
         patch.object(runner, "save_to_notion", return_value="ok") as mock_save, \
         patch.object(runner, "save_log"), \
         patch.object(runner, "notion_find_wip", return_value="途中の制作物はありません"):
        runner.run_agent("creator", "台本を書いて", "火曜：動画台本作成")
    # status キーワード引数が 要確認
    assert mock_save.call_args.kwargs.get("status") == "要確認"


def test_run_agent_auto_continues_on_max_tokens(monkeypatch):
    import runner
    first = _text_response("前半の途中まで", "max_tokens")
    second = _text_response("後半の続き。完了。", "end_turn")
    with patch.object(runner.client.messages, "stream", side_effect=[_stream_cm(first), _stream_cm(second)]) as mock_stream, \
         patch.object(runner, "save_to_notion", return_value="ok") as mock_save, \
         patch.object(runner, "save_log"), \
         patch.object(runner, "notion_find_wip", return_value="途中の制作物はありません"):
        result = runner.run_agent("creator", "台本を書いて", "火曜：動画台本作成")
    # 2回呼ばれ、全文が結合され、要確認で保存
    assert mock_stream.call_count == 2
    assert "前半の途中まで" in result and "後半の続き" in result
    assert mock_save.call_args.kwargs.get("status") == "要確認"


def test_run_agent_falls_back_to_tochu_when_still_truncated(monkeypatch):
    import runner
    trunc = _text_response("延々と切れ続ける", "max_tokens")
    with patch.object(runner.client.messages, "stream", return_value=_stream_cm(trunc)), \
         patch.object(runner, "save_to_notion", return_value="ok") as mock_save, \
         patch.object(runner, "save_log"), \
         patch.object(runner, "notion_find_wip", return_value="途中の制作物はありません"):
        runner.run_agent("creator", "台本を書いて", "火曜：動画台本作成", max_continuations=2)
    assert mock_save.call_args.kwargs.get("status") == "途中"


def test_wip_page_id_for_label_matches_title():
    import runner
    out = "途中の制作物:\n- pageABC | ワイン | 火曜：ワイン動画台本作成 (2026-07-10)\n- pageXYZ | ワイン | 月曜：今週テーマ決定 (2026-07-10)"
    assert runner._wip_page_id_for_label(out, "火曜：ワイン動画台本作成") == "pageABC"


def test_wip_page_id_for_label_no_match_different_task():
    import runner
    # 同カテゴリだが別タスク(テーマ決定)のページは拾わない
    out = "途中の制作物:\n- pageXYZ | ワイン | 月曜：今週テーマ決定 (2026-07-10)"
    assert runner._wip_page_id_for_label(out, "火曜：ワイン動画台本作成") == ""


def test_wip_page_id_for_label_none():
    import runner
    assert runner._wip_page_id_for_label("途中の制作物はありません", "火曜：ワイン動画台本作成") == ""


def test_run_agent_resumes_existing_wip_page(monkeypatch):
    import runner
    resp = _text_response("続きを書いて完成させました。以上です。", "end_turn")
    find_out = "途中の制作物:\n- pageABC | ワイン | 火曜：ワイン動画台本作成 (2026-07-10)"
    with patch.object(runner.client.messages, "stream", return_value=_stream_cm(resp)) as mock_stream, \
         patch.object(runner, "notion_recent_themes", return_value=""), \
         patch.object(runner, "notion_find_wip", return_value=find_out), \
         patch.object(runner, "notion_read_page", return_value="前回の途中原稿本文") as mock_read, \
         patch.object(runner, "extract_theme", return_value=""), \
         patch.object(runner, "notion_append_to_page", return_value="更新しました") as mock_append, \
         patch.object(runner, "save_to_notion", return_value="ok") as mock_save, \
         patch.object(runner, "save_log"):
        runner.run_agent("creator", "ワインの台本を書いて", "火曜：ワイン動画台本作成")

    # 既存原稿を読み、プロンプトに注入して生成、既存ページへ追記、新規保存はしない
    mock_read.assert_called_once_with("pageABC")
    sent_messages = mock_stream.call_args.kwargs["messages"]
    assert "前回の途中原稿本文" in sent_messages[0]["content"]
    mock_append.assert_called_once()
    assert mock_append.call_args[0][0] == "pageABC"
    assert mock_append.call_args.kwargs.get("status") == "要確認"
    mock_save.assert_not_called()


def test_run_agent_read_error_falls_back_to_new_page(monkeypatch):
    import runner
    resp = _text_response("新規に書き起こした完成原稿です。以上。", "end_turn")
    find_out = "途中の制作物:\n- pageABC | ワイン | 火曜：ワイン動画台本作成 (2026-07-10)"
    with patch.object(runner.client.messages, "stream", return_value=_stream_cm(resp)) as mock_stream, \
         patch.object(runner, "notion_recent_themes", return_value=""), \
         patch.object(runner, "notion_find_wip", return_value=find_out), \
         patch.object(runner, "notion_read_page", return_value="Notion読み取りエラー: 404 not found"), \
         patch.object(runner, "extract_theme", return_value=""), \
         patch.object(runner, "notion_append_to_page", return_value="x") as mock_append, \
         patch.object(runner, "save_to_notion", return_value="ok") as mock_save, \
         patch.object(runner, "save_log"):
        runner.run_agent("creator", "ワインの台本を書いて", "火曜：ワイン動画台本作成")
    sent = mock_stream.call_args.kwargs["messages"][0]["content"]
    assert "Notion読み取りエラー" not in sent          # error text NOT injected
    mock_append.assert_not_called()                     # did not append to unreadable page
    mock_save.assert_called_once()                      # fell back to new page


def test_run_agent_resume_path_skips_recent_themes_injection(monkeypatch):
    """WIP再開時は、直近テーマ一覧があっても【重複回避】ブロックを注入しない（自分自身のテーマを避けよと言わない）。"""
    import runner
    resp = _text_response("続きを書いて完成させました。以上です。", "end_turn")
    find_out = "途中の制作物:\n- pageABC | ワイン | 火曜：ワイン動画台本作成 (2026-07-10)"
    with patch.object(runner.client.messages, "stream", return_value=_stream_cm(resp)) as mock_stream, \
         patch.object(runner, "notion_recent_themes",
                      return_value="- トスカーナ州のサンジョヴェーゼ（月曜：今週テーマ決定 (2026-07-20)）") as mock_recent, \
         patch.object(runner, "notion_find_wip", return_value=find_out), \
         patch.object(runner, "notion_read_page", return_value="前回の途中原稿本文"), \
         patch.object(runner, "extract_theme", return_value=""), \
         patch.object(runner, "notion_append_to_page", return_value="更新しました"), \
         patch.object(runner, "save_to_notion", return_value="ok"), \
         patch.object(runner, "save_log"):
        runner.run_agent("creator", "ワインの台本を書いて", "火曜：ワイン動画台本作成")

    mock_recent.assert_not_called()
    sent_prompt = mock_stream.call_args.kwargs["messages"][0]["content"]
    assert "重複回避" not in sent_prompt
    assert "前回の途中原稿" in sent_prompt


def test_run_agent_injects_recent_themes_into_prompt(monkeypatch):
    import runner
    resp = _text_response("新しいテーマ提案です。以上。", "end_turn")
    with patch.object(runner.client.messages, "stream", return_value=_stream_cm(resp)) as mock_stream, \
         patch.object(runner, "notion_recent_themes",
                      return_value="- ピエモンテ州のネッビオーロ（月曜：今週テーマ決定 (2026-07-20)）") as mock_recent, \
         patch.object(runner, "notion_find_wip", return_value="途中の制作物はありません"), \
         patch.object(runner, "extract_theme", return_value=""), \
         patch.object(runner, "save_to_notion", return_value="ok"), \
         patch.object(runner, "save_log"):
        runner.run_agent("sommelier", "今週のワインテーマを提案してください", "月曜：今週テーマ決定")

    mock_recent.assert_called_once_with("ワイン")
    sent_prompt = mock_stream.call_args.kwargs["messages"][0]["content"]
    assert "重複回避" in sent_prompt
    assert "ピエモンテ州のネッビオーロ" in sent_prompt


def test_run_agent_skips_theme_injection_when_no_recent_themes(monkeypatch):
    import runner
    resp = _text_response("初回のテーマ提案です。以上。", "end_turn")
    with patch.object(runner.client.messages, "stream", return_value=_stream_cm(resp)) as mock_stream, \
         patch.object(runner, "notion_recent_themes", return_value=""), \
         patch.object(runner, "notion_find_wip", return_value="途中の制作物はありません"), \
         patch.object(runner, "extract_theme", return_value=""), \
         patch.object(runner, "save_to_notion", return_value="ok"), \
         patch.object(runner, "save_log"):
        runner.run_agent("sommelier", "今週のワインテーマを提案してください", "月曜：今週テーマ決定")

    sent_prompt = mock_stream.call_args.kwargs["messages"][0]["content"]
    assert "重複回避" not in sent_prompt


def test_run_agent_does_not_call_recent_themes_for_other_category(monkeypatch):
    import runner
    resp = _text_response("分析レポートです。以上。", "end_turn")
    with patch.object(runner.client.messages, "stream", return_value=_stream_cm(resp)), \
         patch.object(runner, "notion_recent_themes") as mock_recent, \
         patch.object(runner, "extract_theme") as mock_extract, \
         patch.object(runner, "save_to_notion", return_value="ok"), \
         patch.object(runner, "save_log"):
        runner.run_agent("marketer", "反応を分析してください", "日曜：反応分析レポート")

    mock_recent.assert_not_called()
    mock_extract.assert_not_called()


def test_run_agent_extracts_theme_and_passes_to_save_to_notion(monkeypatch):
    import runner
    resp = _text_response("ピエモンテ州のネッビオーロを紹介します。以上。", "end_turn")
    with patch.object(runner.client.messages, "stream", return_value=_stream_cm(resp)), \
         patch.object(runner, "notion_recent_themes", return_value=""), \
         patch.object(runner, "notion_find_wip", return_value="途中の制作物はありません"), \
         patch.object(runner, "extract_theme", return_value="ピエモンテ州のネッビオーロ") as mock_extract, \
         patch.object(runner, "save_to_notion", return_value="ok") as mock_save, \
         patch.object(runner, "save_log"):
        runner.run_agent("sommelier", "今週のワインテーマを提案してください", "月曜：今週テーマ決定")

    mock_extract.assert_called_once_with("ピエモンテ州のネッビオーロを紹介します。以上。")
    assert mock_save.call_args.kwargs.get("theme") == "ピエモンテ州のネッビオーロ"


def test_run_agent_extracts_theme_and_passes_to_notion_append_to_page(monkeypatch):
    import runner
    resp = _text_response("続きを完成させました。以上です。", "end_turn")
    find_out = "途中の制作物:\n- pageABC | ワイン | 火曜：ワイン動画台本作成 (2026-07-10)"
    with patch.object(runner.client.messages, "stream", return_value=_stream_cm(resp)), \
         patch.object(runner, "notion_recent_themes", return_value=""), \
         patch.object(runner, "notion_find_wip", return_value=find_out), \
         patch.object(runner, "notion_read_page", return_value="前回の途中原稿本文"), \
         patch.object(runner, "extract_theme", return_value="トスカーナ州のサンジョヴェーゼ") as mock_extract, \
         patch.object(runner, "notion_append_to_page", return_value="更新しました") as mock_append, \
         patch.object(runner, "save_to_notion", return_value="ok"), \
         patch.object(runner, "save_log"):
        runner.run_agent("creator", "ワインの台本を書いて", "火曜：ワイン動画台本作成")

    mock_extract.assert_called_once()
    assert mock_append.call_args.kwargs.get("theme") == "トスカーナ州のサンジョヴェーゼ"


from unittest.mock import patch
from runner import instagram_insights_task

# NOTE: instagram_insights_task() skips calling sync_instagram_insights when
# any of these env vars is unset (see runner.py). Neither this worktree nor
# the main repo's .env defines them, so both tests below patch os.environ to
# ensure the function actually reaches the sync call being tested, rather
# than silently short-circuiting on the "not configured" branch.
_FAKE_IG_ENV = {
    "META_ACCESS_TOKEN": "fake-token",
    "META_IG_USER_ID": "fake-ig-user-id",
    "GOOGLE_SERVICE_ACCOUNT_JSON": "fake-service-account.json",
    "INSTAGRAM_SHEET_ID": "fake-sheet-id",
}


@patch("runner.sync_instagram_insights")
def test_instagram_insights_task_calls_sync_and_does_not_raise(mock_sync):
    mock_sync.return_value = "タブ1: 1件処理、タブ2: 1件処理"
    with patch.dict(os.environ, _FAKE_IG_ENV):
        instagram_insights_task()  # 例外を投げなければOK
    mock_sync.assert_called_once()


@patch("runner.sync_instagram_insights")
def test_instagram_insights_task_swallows_exceptions(mock_sync):
    mock_sync.side_effect = Exception("boom")
    with patch.dict(os.environ, _FAKE_IG_ENV):
        instagram_insights_task()  # 例外が外に漏れないことを確認
    mock_sync.assert_called_once()


@patch("runner.sync_instagram_insights")
def test_instagram_insights_task_skips_when_env_vars_missing(mock_sync):
    ig_env_keys = ["META_ACCESS_TOKEN", "META_IG_USER_ID", "GOOGLE_SERVICE_ACCOUNT_JSON", "INSTAGRAM_SHEET_ID"]
    with patch.dict(os.environ, {}, clear=False):
        for key in ig_env_keys:
            os.environ.pop(key, None)
        instagram_insights_task()  # 環境変数未設定でも例外を投げずスキップすること
    mock_sync.assert_not_called()
