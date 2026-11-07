import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import vault
from scripts.build_wine_graph import build, parse_theme


def _vault(tmp_path):
    v = tmp_path / "v"
    v.mkdir()
    vault.append_row(str(v), "州別.md", ["9・Piemonte", "州", "1ファイル", "2026-10-19", "/x/9・Piemonte", "登録済み"])
    vault.append_row(str(v), "投稿テーマ.md", ["月曜", "週次", "ピエモンテ州のネッビオーロ", "2026-11-04", "Notion", "要確認"])
    return v


def test_parse_theme():
    assert parse_theme("ピエモンテ州のネッビオーロ", ["ピエモンテ", "トスカーナ"]) == ("ピエモンテ", "ネッビオーロ")
    assert parse_theme("ワインの色の話", ["ピエモンテ"]) == (None, None)


def test_build_links_state_variety_post(tmp_path):
    v = _vault(tmp_path)
    build(str(v))
    g = v / "05_グラフ"
    state = (g / "州" / "ピエモンテ.md").read_text(encoding="utf-8")
    assert "[[イタリア20州]]" in state and "[[ネッビオーロ]]" in state
    assert "[[2026-11-04 ピエモンテ州のネッビオーロ]]" in state and "/x/9・Piemonte" in state
    assert "[[ピエモンテ]]" in (g / "品種" / "ネッビオーロ.md").read_text(encoding="utf-8")
    assert (g / "投稿" / "2026-11-04 ピエモンテ州のネッビオーロ.md").exists()


def test_build_is_idempotent_and_keeps_ledger(tmp_path):
    v = _vault(tmp_path)
    before = (v / "01_台帳" / "州別.md").read_text(encoding="utf-8")
    first = build(str(v))
    assert build(str(v)) == first
    assert (v / "01_台帳" / "州別.md").read_text(encoding="utf-8") == before


def test_stale_generated_notes_removed_but_handwritten_kept(tmp_path):
    v = _vault(tmp_path)
    build(str(v))
    ledger = v / "01_台帳" / "投稿テーマ.md"
    ledger.write_text("# 投稿テーマ.md\n# 名称｜種類｜切り口(一言)｜作成日｜場所(パスまたはURL)｜使用状況\n", encoding="utf-8")
    hand = v / "05_グラフ" / "品種" / "手書き.md"
    hand.write_text("自分のメモ", encoding="utf-8")
    build(str(v))
    assert not (v / "05_グラフ" / "投稿" / "2026-11-04 ピエモンテ州のネッビオーロ.md").exists()
    assert not (v / "05_グラフ" / "品種" / "ネッビオーロ.md").exists()
    assert hand.read_text(encoding="utf-8") == "自分のメモ"
