import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import scripts.import_notion_to_vault as m


def rt(text, **ann):
    return {"plain_text": text, "type": "text", "annotations": ann, "href": None}


def blk(t, text="", **extra):
    return {"type": t, t: {"rich_text": [rt(text)], **extra}}


def test_rich_text_annotations_and_link():
    assert m.rich_text_md([rt("強", bold=True), rt("コード", code=True)]) == "**強**`コード`"
    assert m.rich_text_md([{"plain_text": "L", "type": "text", "annotations": {}, "href": "http://a"}]) == "[L](http://a)"


def test_blocks_to_markdown_headings_lists_nested_todo_table():
    b = [blk("heading_1", "題"), blk("paragraph", "本文"), blk("numbered_list_item", "一"), blk("numbered_list_item", "二"),
         {**blk("bulleted_list_item", "親"), "children": [blk("bulleted_list_item", "子")]}, blk("to_do", "済", checked=True),
         {"type": "table", "table": {}, "children": [
             {"type": "table_row", "table_row": {"cells": [[rt("a")], [rt("b")]]}},
             {"type": "table_row", "table_row": {"cells": [[rt("1")], [rt("2")]]}}]}]
    md = m.blocks_md(b)
    assert "## 題" in md and "1. 一" in md and "2. 二" in md and "- 親\n  - 子" in md and "- [x] 済" in md
    assert "| a | b |\n|---|---|\n| 1 | 2 |" in md


def test_child_page_is_plain_text_and_literal_double_brackets_are_escaped():
    assert m.blocks_md([{"type": "child_page", "child_page": {"title": "子ページ"}}]) == "- 📄 子ページ"
    assert "[[" not in m.blocks_md([blk("paragraph", "台本 [[テロップ]] です")])


def test_jst_date_and_safe_name():
    assert m.jst_date("2026-11-04T17:11:00.000Z") == "2026-11-05"
    assert "/" not in m.safe_name("産地/ピエモンテ") and m.safe_name("///") == "無題"


def test_cluster_groups_duplicates_and_near_copies_not_unrelated():
    base = "ピエモンテ州のネッビオーロは長期熟成に向く品種で、バローロとバルバレスコが有名です。" * 8
    items = [{"id": "a", "body": base}, {"id": "b", "body": base}, {"id": "c", "body": base + "追記です。"},
             {"id": "d", "body": "シチリアのネロ・ダーヴォラは濃い果実味を持つ赤ワインです。" * 8}, {"id": "e", "body": "短い"}]
    groups = m.cluster(items)
    assert [(sorted(g), k) for g, k in groups] == [(["a", "b", "c"], "類似")]


def test_cluster_same_task_same_day_is_duplicate_but_other_days_are_not():
    it = lambda i, t, c: {"id": i, "body": f"本文{i}", "title": t, "created": c}
    items = [it("a", "月曜：テーマ決定 (2026-06-04)", "2026-06-04"), it("b", "月曜：テーマ決定 (2026-06-04)", "2026-06-04"),
             it("c", "月曜：テーマ決定 (2026-06-11)", "2026-06-11")]
    assert [(sorted(g), k) for g, k in m.cluster(items)] == [(["a", "b"], "重複")]


def test_task_label_strips_date_tail():
    assert m.task_label("月曜：テーマ決定 (2026-06-04)") == "月曜：テーマ決定"
    assert m.task_label("クリエイター - 2026-09-18 03:02") == "クリエイター"


def _page(i, source, title, body, created="2026-11-01"):
    return {"id": f"id{i:04d}", "source": source, "title": title, "created": created, "edited": created, "props": {"ステータス": "要確認"}, "body": body}


def test_build_notes_separates_study_links_state_and_groups_similar(tmp_path):
    v = tmp_path / "v"
    long = "ネッビオーロの解説。" * 40
    pages = [_page(1, "生成物", "ピエモンテ州のネッビオーロ", long), _page(2, "生成物", "ピエモンテ州のネッビオーロ（再）", long, "2026-11-02"),
             _page(3, "学習", "産地/トスカーナ", "上級者向けの学習メモ。" * 30), _page(4, "保管", "ソムリエ - 2026-05-15", "短い")]
    counts = m.build_notes(pages, str(v))
    assert counts == {"学習": 1, "生成物": 2, "保管": 1, "類似グループ": 1}
    study = (v / "08_ソムリエ学習ノート" / "産地・トスカーナ.md").read_text(encoding="utf-8")
    assert "tags: [上級者, 学習ノート]" in study and "[[トスカーナ]]" in study and "[[ソムリエ学習ノート]]" in study
    gen = (v / "06_Notion" / "コンテンツ生成物" / "2026-11-01 ピエモンテ州のネッビオーロ.md").read_text(encoding="utf-8")
    assert "[[ピエモンテ]]" in gen and "- 類似・重複: [[重複グループ・生成物系01" in gen and "類似・重複" in gen
    assert len(list((v / "07_類似・重複").glob("*.md"))) == 1


def test_build_notes_rerun_replaces_generated_but_keeps_handwritten(tmp_path):
    v = tmp_path / "v"
    pages = [_page(1, "生成物", "A", "本文" * 10)]
    m.build_notes(pages, str(v))
    hand = v / "06_Notion" / "コンテンツ生成物" / "手書き.md"
    hand.write_text("自分のメモ", encoding="utf-8")
    m.build_notes([_page(2, "生成物", "B", "本文" * 10)], str(v))
    assert hand.exists() and not (v / "06_Notion" / "コンテンツ生成物" / "2026-11-01 A.md").exists()


class FakeNotion:
    """通信しないNotion。呼ばれたblocks取得を数える。"""
    def __init__(self, rows, study, archive_kids, pages):
        self.rows, self.study, self.kids, self.pages = rows, study, archive_kids, pages
        self.block_calls = []

    def query_all(self, db):
        return self.rows if db == "DB" else self.study

    def blocks(self, bid, child_pages=None):
        self.block_calls.append(bid)
        if bid == m.ARCHIVE_PAGE_ID and child_pages is not None:
            child_pages += self.kids
        return [blk("paragraph", f"本文{bid}")]

    def req(self, method, path, **kw):
        return self.pages[path.split("/")[-1]]


def _row(i, edited):
    return {"id": i, "created_time": "2026-11-01T00:00:00.000Z", "last_edited_time": edited,
            "properties": {"名前": {"type": "title", "title": [{"plain_text": f"題{i}"}]}}}


def test_fetch_all_reuses_unchanged_pages_and_rereads_changed(monkeypatch):
    monkeypatch.setenv("NOTION_DATABASE_ID", "DB")
    mk = lambda: FakeNotion([_row("r1", "2026-11-01T00:00:00.000Z"), _row("r2", "2026-11-01T00:00:00.000Z")], [], [("c1", "子")], {"c1": _row("c1", "2026-11-01T00:00:00.000Z")})
    first = m.fetch_all(lambda _: None, None, mk())
    assert len(first) == 3
    n2 = mk()
    n2.rows[1] = _row("r2", "2026-11-02T00:00:00.000Z")  # r2 だけ更新された
    second = m.fetch_all(lambda _: None, first, n2)
    assert {p["id"] for p in second} == {"r1", "r2", "c1"}
    assert sorted(n2.block_calls) == sorted([m.ARCHIVE_PAGE_ID, "r2"])  # 直下の確認と、更新された r2 だけ


def test_sync_writes_cache_and_notes(tmp_path, monkeypatch):
    monkeypatch.setenv("NOTION_DATABASE_ID", "DB")
    v = tmp_path / "v"
    v.mkdir()
    n = FakeNotion([_row("r1", "2026-11-01T00:00:00.000Z")], [], [], {})
    assert m.sync(str(v), lambda _: None, n)["生成物"] == 1
    assert (v / ".notion_cache.json").exists() and (v / "06_Notion" / "コンテンツ生成物").exists()
