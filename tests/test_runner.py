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

    mock_notion.assert_called_once_with(f"テストラベル ({today})", "テスト出力")


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
