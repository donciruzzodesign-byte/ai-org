from pathlib import Path

MIN_TEXT_LENGTH = 500


def validate_input(file_path) -> str:
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"ファイルが見つかりません: {file_path}")
    text = path.read_text(encoding="utf-8").strip()
    if len(text) < MIN_TEXT_LENGTH:
        raise ValueError(
            f"テキストが少なすぎます。{MIN_TEXT_LENGTH}文字以上入力してください"
            f"（現在: {len(text)}文字）"
        )
    return text
