import os
import sys
import tempfile
import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from runner import run_agent, run_video_agent, tuesday_video_task, coffee_tuesday_video_task


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
            mock_client.messages.create.return_value = mock_response
            result = runner.run_agent('sommelier', 'テーマを提案してください', '月曜：テーマ決定')

        assert result == 'AIの返答テキスト'
        mock_client.messages.create.assert_called_once()


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

    with patch("runner.client.messages.create", return_value=fake_response), \
         patch("runner.save_to_notion", return_value="OK") as mock_notion, \
         patch("runner.save_log"):
        run_agent("sommelier", "テスト", "テストラベル")

    mock_notion.assert_called_once_with(f"テストラベル ({today})", "テスト出力", status="要確認")


def test_run_video_agent_calls_video_tools(tmp_path):
    """run_video_agent が VIDEO_TOOL_DEFINITIONS を使って Claude を呼び出すことを確認。"""
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
    with patch.object(runner.client.messages, "create", return_value=resp), \
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
    with patch.object(runner.client.messages, "create", side_effect=[first, second]) as mock_create, \
         patch.object(runner, "save_to_notion", return_value="ok") as mock_save, \
         patch.object(runner, "save_log"), \
         patch.object(runner, "notion_find_wip", return_value="途中の制作物はありません"):
        result = runner.run_agent("creator", "台本を書いて", "火曜：動画台本作成")
    # 2回呼ばれ、全文が結合され、要確認で保存
    assert mock_create.call_count == 2
    assert "前半の途中まで" in result and "後半の続き" in result
    assert mock_save.call_args.kwargs.get("status") == "要確認"


def test_run_agent_falls_back_to_tochu_when_still_truncated(monkeypatch):
    import runner
    trunc = _text_response("延々と切れ続ける", "max_tokens")
    with patch.object(runner.client.messages, "create", return_value=trunc), \
         patch.object(runner, "save_to_notion", return_value="ok") as mock_save, \
         patch.object(runner, "save_log"), \
         patch.object(runner, "notion_find_wip", return_value="途中の制作物はありません"):
        runner.run_agent("creator", "台本を書いて", "火曜：動画台本作成", max_continuations=2)
    assert mock_save.call_args.kwargs.get("status") == "途中"
