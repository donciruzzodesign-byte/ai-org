import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import vault
from scripts.backfill_wine_vault import backfill


def _touch(p, name="a.png"):
    p.mkdir(parents=True, exist_ok=True)
    (p / name).write_text("x")


def _tree(tmp_path):
    a = tmp_path / "archive"
    _touch(a / "1・イタリアワイン入門")
    _touch(a / "75 イントロ　トスカーナ")
    _touch(a / "20州の旅　DOCG深掘り" / "9・Piemonte")
    _touch(a / "20州の旅　DOCG深掘り" / "16・Toscana")
    _touch(a / "リール素材" / "ピコリット")
    _touch(a / "リール素材" / "キャンティ")
    _touch(a / "trivia")
    _touch(a / "公式LINE登録者プレゼント")
    return a


def test_classifies_lessons_states_series_and_gifts(tmp_path):
    a, v = _tree(tmp_path), tmp_path / "vault"
    v.mkdir()
    counts = backfill(str(a), str(v))
    assert counts["講座の回"] == 2
    assert counts["州別"] == 2
    assert counts["シリーズ"] == 3
    assert counts["配布物"] == 1
    assert len(vault.read_rows(str(v), "州別.md", 99)) == 2


def test_empty_folder_marked_and_not_counted_as_file(tmp_path):
    a, v = tmp_path / "archive", tmp_path / "vault"
    v.mkdir()
    _touch(a / "3・空", ".DS_Store")
    counts = backfill(str(a), str(v))
    assert counts["空"] == 1
    assert counts["講座の回"] == 0
    assert vault.read_rows(str(v), "講座の回.md", 99) == []


def test_backfill_is_idempotent(tmp_path):
    a, v = _tree(tmp_path), tmp_path / "vault"
    v.mkdir()
    backfill(str(a), str(v))
    before = {f: len(vault.read_rows(str(v), f, 999)) for f in ("講座の回.md", "州別.md", "シリーズ.md", "配布物.md")}
    again = backfill(str(a), str(v))
    after = {f: len(vault.read_rows(str(v), f, 999)) for f in before}
    assert before == after
    assert again["講座の回"] == again["州別"] == again["シリーズ"] == again["配布物"] == 0


def test_never_reads_chiave(tmp_path):
    a, v = tmp_path / "archive", tmp_path / "vault"
    v.mkdir()
    _touch(a / "CHIAVE")
    _touch(a / "1・CHIAVE入門")
    _touch(a / "リール素材" / "CHIAVE")
    backfill(str(a), str(v))
    for f in (v / "01_台帳").glob("*.md"):
        assert "CHIAVE" not in f.read_text(encoding="utf-8")
