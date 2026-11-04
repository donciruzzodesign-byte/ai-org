import vault


def test_vault_path_requires_existing_dir(tmp_path, monkeypatch):
    monkeypatch.delenv("WINE_VAULT_PATH", raising=False)
    assert vault.vault_path() is None
    monkeypatch.setenv("WINE_VAULT_PATH", str(tmp_path / "nope"))
    assert vault.vault_path() is None
    monkeypatch.setenv("WINE_VAULT_PATH", str(tmp_path))
    assert vault.vault_path() == str(tmp_path)


def test_append_row_and_read_rows_roundtrip(tmp_path):
    cols = ["A", "テーマ", "切り口", "2026-11-04", "x", "使用済"]
    assert vault.append_row(str(tmp_path), "投稿テーマ.md", cols) is True
    assert (tmp_path / "01_台帳").is_dir()
    assert vault.read_rows(str(tmp_path), "投稿テーマ.md") == [cols]


def test_append_row_replaces_separator_and_newline(tmp_path):
    cols = ["A｜B", "テーマ\nX", "切り口", "2026-11-04", "x", "使用済"]
    assert vault.append_row(str(tmp_path), "投稿テーマ.md", cols)
    rows = vault.read_rows(str(tmp_path), "投稿テーマ.md")
    assert len(rows) == 1 and len(rows[0]) == 6
    assert rows[0][0] == "A B"


def test_append_row_returns_false_without_vault():
    assert vault.append_row(None, "投稿テーマ.md", ["a"] * 6) is False


def test_read_rows_skips_broken_lines(tmp_path):
    d = tmp_path / "01_台帳"
    d.mkdir()
    (d / "投稿テーマ.md").write_text(
        "# 投稿テーマ.md\n---\n\n不完全｜行\nA｜B｜C｜D｜E｜F\n",
        encoding="utf-8",
    )
    assert vault.read_rows(str(tmp_path), "投稿テーマ.md") == [list("ABCDEF")]


def test_slug_words():
    url = "https://www.pexels.com/video/woman-pouring-red-wine-3195394/"
    assert vault.slug_words(url) == {"woman", "pouring", "red", "wine"}
    assert vault.slug_words("") == set()
    assert vault.slug_words("https://www.pexels.com/video/3195394/") == set()


def test_is_similar():
    assert vault.is_similar({"red", "wine", "glass"}, [{"red", "wine", "pouring"}])
    assert not vault.is_similar({"vineyard", "sunset"}, [{"red", "wine", "pouring"}])
    assert not vault.is_similar(set(), [set()])


def test_recent_broll_words(tmp_path):
    vault.append_row(str(tmp_path), "B-roll.md", ["2026-11-04", "wine", "red wine glass", "1", "p"])
    assert vault.recent_broll_words(str(tmp_path)) == [{"red", "wine", "glass"}]


def test_ledger_summary_formats_recent_rows(tmp_path):
    for n in "ABC":
        vault.append_row(str(tmp_path), "投稿テーマ.md", [n, "テーマ", f"切り口{n}", "d", "x", "u"])
    assert vault.ledger_summary(str(tmp_path), limit=2) == "・B（切り口B）\n・C（切り口C）"
    assert vault.ledger_summary(None) == ""
