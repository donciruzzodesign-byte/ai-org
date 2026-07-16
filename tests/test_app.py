import os
import sys
import re
import pytest
from unittest.mock import patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


def test_app_saves_with_yokakunin_status():
    # app.py が save_to_notion を status="要確認" 付きで呼ぶことをソース上で保証する
    with open(os.path.join(os.path.dirname(__file__), '..', 'app.py'), encoding='utf-8') as f:
        src = f.read()
    assert re.search(r'save_to_notion\([^)]*status\s*=\s*"要確認"', src, re.S)
    assert "max_tokens=32000" in src


def test_load_agent_reads_correct_file(tmp_path):
    agents_dir = tmp_path / 'agents'
    agents_dir.mkdir()
    (agents_dir / 'ceo.txt').write_text('CEOプロンプトのテスト内容', encoding='utf-8')

    import app
    original = app.__file__
    app.__file__ = str(tmp_path / 'app.py')
    result = app.load_agent('ceo')
    app.__file__ = original

    assert result == 'CEOプロンプトのテスト内容'


def test_load_agent_raises_for_missing_file(tmp_path):
    import app
    original = app.__file__
    app.__file__ = str(tmp_path / 'app.py')
    with pytest.raises(FileNotFoundError):
        app.load_agent('nonexistent')
    app.__file__ = original


def test_agents_dict_contains_barista():
    import importlib
    import app
    importlib.reload(app)
    agent_ids = [v[0] for v in app.AGENTS.values()]
    assert 'barista' in agent_ids, "AGENTS dict に barista が含まれていません"
