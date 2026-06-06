import pytest
from pathlib import Path
from book_processor import validate_input, save_outputs


def test_validate_input_file_not_found(tmp_path):
    with pytest.raises(FileNotFoundError):
        validate_input(tmp_path / "nonexistent.txt")


def test_validate_input_too_short(tmp_path):
    f = tmp_path / "book.txt"
    f.write_text("短いテキスト", encoding="utf-8")
    with pytest.raises(ValueError, match="テキストが少なすぎます"):
        validate_input(f)


def test_validate_input_valid(tmp_path):
    f = tmp_path / "book.txt"
    f.write_text("あ" * 501, encoding="utf-8")
    result = validate_input(f)
    assert result == "あ" * 501


def test_save_outputs_creates_all_files(tmp_path):
    outputs = {
        "summary": "全体要約",
        "chapter_points": "章別ポイント",
        "instagram_posts": "Instagram投稿文",
        "note_article": "note記事",
        "youtube_script": "YouTube台本",
    }
    book_dir = save_outputs("test_book", outputs, output_dir=tmp_path)
    assert book_dir == tmp_path / "test_book"
    assert (book_dir / "summary.md").read_text(encoding="utf-8") == "全体要約"
    assert (book_dir / "chapter_points.md").read_text(encoding="utf-8") == "章別ポイント"
    assert (book_dir / "instagram_posts.md").read_text(encoding="utf-8") == "Instagram投稿文"
    assert (book_dir / "note_article.md").read_text(encoding="utf-8") == "note記事"
    assert (book_dir / "youtube_script.md").read_text(encoding="utf-8") == "YouTube台本"


def test_save_outputs_creates_nested_directory(tmp_path):
    outputs = {"summary": "テスト", "chapter_points": "", "instagram_posts": "",
               "note_article": "", "youtube_script": ""}
    book_dir = save_outputs("nested/book", outputs, output_dir=tmp_path)
    assert book_dir.exists()
