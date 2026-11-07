import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


@pytest.fixture(autouse=True)
def _no_real_side_effects(monkeypatch, tmp_path):
    """テストが本物のNotion・ログ・ワイン台帳へ書き込まないようにする。

    例外を起こすテストが _report_failure 経由で「（失敗）」ページを本物のNotionに作り、
    logs/ に偽の失敗記録を残していたため。個別のテストが自分で patch した場合はそちらが優先される。
    """
    import runner
    real_save_log = runner.save_log
    real_file = runner.__file__

    def save_log_in_tmp(content, label):
        original = runner.__file__
        if original != real_file:  # テスト自身が書き込み先を指定している場合はそれに従う
            return real_save_log(content, label)
        runner.__file__ = str(tmp_path / "runner.py")  # logs/ の書き込み先だけ一時フォルダへ
        try:
            real_save_log(content, label)
        finally:
            runner.__file__ = original

    monkeypatch.delenv("WINE_VAULT_PATH", raising=False)  # 本物のワイン台帳(Obsidian)へ書かない。必要なテストは自分で設定する
    monkeypatch.setattr(runner, "save_to_notion", lambda *a, **k: "(テスト: Notion保存なし)")
    monkeypatch.setattr(runner, "save_log", save_log_in_tmp)
