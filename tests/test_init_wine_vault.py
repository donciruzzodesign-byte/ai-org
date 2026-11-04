import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from scripts.init_wine_vault import init_vault

LEDGERS = ["シリーズ", "講座の回", "州別", "投稿テーマ", "配布物", "B-roll"]


def test_init_vault_creates_structure(tmp_path):
    root = tmp_path / "ワイン台帳"
    created = init_vault(str(root))
    assert created
    assert (root / "00_ルール.md").is_file()
    assert (root / "02_進行中.md").is_file()
    assert (root / "03_決めごと.md").is_file()
    assert (root / "04_プロモーション").is_dir()
    for name in LEDGERS:
        assert (root / "01_台帳" / f"{name}.md").is_file()


def test_init_vault_is_idempotent_and_keeps_edits(tmp_path):
    root = tmp_path / "ワイン台帳"
    init_vault(str(root))
    f = root / "03_決めごと.md"
    f.write_text("書き換え済み", encoding="utf-8")
    assert init_vault(str(root)) == []
    assert f.read_text(encoding="utf-8") == "書き換え済み"


def test_rules_mention_required_steps(tmp_path):
    root = tmp_path / "ワイン台帳"
    init_vault(str(root))
    text = (root / "00_ルール.md").read_text(encoding="utf-8")
    for word in ("02_進行中", "01_台帳", "追記専用", "パスワード"):
        assert word in text
