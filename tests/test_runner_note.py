import os
import sys
from unittest.mock import patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from runner import _write_note_article


def test_write_note_article_creates_file(tmp_path):
    output_dir = str(tmp_path / "2026-07-07-wine")
    path = _write_note_article("# タイトル案\n\n記事本文", output_dir)

    assert path == os.path.join(output_dir, "note_article.md")
    with open(path, encoding="utf-8") as f:
        assert f.read() == "# タイトル案\n\n記事本文"


def test_write_note_article_creates_missing_dir(tmp_path):
    """videoタスクが失敗して出力ディレクトリが無くても書き込める。"""
    output_dir = str(tmp_path / "not" / "yet" / "created")
    path = _write_note_article("本文", output_dir)

    assert os.path.isfile(path)


def test_note_task_functions_are_callable():
    import runner
    assert callable(runner.tuesday_note_task), "tuesday_note_task が存在しません"
    assert callable(runner.coffee_tuesday_note_task), "coffee_tuesday_note_task が存在しません"


def test_note_article_prompt_contains_context_and_format():
    import runner
    prompt = runner._note_article_prompt("今週のテーマ：バローロ", "ワイン", "既定テーマ")
    assert "今週のテーマ：バローロ" in prompt
    assert "タイトル案" in prompt
    assert "ハッシュタグ" in prompt
    assert "既定テーマ" in prompt


def test_tuesday_note_task_writes_article(tmp_path):
    """run_agent の戻り値が output/YYYY-MM-DD-wine/note_article.md に保存される。"""
    import runner
    from datetime import datetime

    with patch("runner.__file__", str(tmp_path / "runner.py")), \
         patch("runner.run_agent", return_value="note記事本文") as mock_run:
        runner.tuesday_note_task()

    mock_run.assert_called_once()
    assert mock_run.call_args.args[0] == "creator"

    date_str = datetime.now().strftime("%Y-%m-%d")
    article_path = tmp_path / "output" / f"{date_str}-wine" / "note_article.md"
    assert article_path.is_file()
    assert article_path.read_text(encoding="utf-8") == "note記事本文"


def test_coffee_tuesday_note_task_writes_article(tmp_path):
    import runner
    from datetime import datetime

    with patch("runner.__file__", str(tmp_path / "runner.py")), \
         patch("runner.run_agent", return_value="コーヒーnote記事本文"):
        runner.coffee_tuesday_note_task()

    date_str = datetime.now().strftime("%Y-%m-%d")
    article_path = tmp_path / "output" / f"{date_str}-coffee" / "note_article.md"
    assert article_path.is_file()


def test_note_tasks_catch_exceptions(capsys):
    """run_agent が失敗してもタスク関数は例外を外に漏らさない。"""
    import runner
    with patch("runner.run_agent", side_effect=Exception("API error")):
        runner.tuesday_note_task()
        runner.coffee_tuesday_note_task()
    out = capsys.readouterr().out
    assert "火曜：note記事作成（ワイン） 失敗" in out
    assert "火曜：note記事作成（コーヒー） 失敗" in out
