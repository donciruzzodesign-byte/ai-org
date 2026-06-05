import pytest
from pathlib import Path
from book_processor import validate_input


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
