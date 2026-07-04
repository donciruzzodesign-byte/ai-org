import os
import sys

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
