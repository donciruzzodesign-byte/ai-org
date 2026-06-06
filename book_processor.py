from pathlib import Path
import os
import anthropic

MIN_TEXT_LENGTH = 500

MODEL = "claude-sonnet-4-6"


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


OUTPUT_BASE = Path(__file__).parent / "output" / "books"

FILE_MAP = {
    "summary": "summary.md",
    "chapter_points": "chapter_points.md",
    "instagram_posts": "instagram_posts.md",
    "note_article": "note_article.md",
    "youtube_script": "youtube_script.md",
}


def save_outputs(book_name: str, outputs: dict, output_dir: Path = OUTPUT_BASE) -> Path:
    book_dir = Path(output_dir) / book_name
    book_dir.mkdir(parents=True, exist_ok=True)
    for key, filename in FILE_MAP.items():
        (book_dir / filename).write_text(outputs.get(key, ""), encoding="utf-8")
    return book_dir


def call_agent(client: anthropic.Anthropic, system_prompt: str, user_message: str) -> str:
    response = client.messages.create(
        model=MODEL,
        max_tokens=16000,
        system=system_prompt,
        messages=[{"role": "user", "content": user_message}],
    )
    return next(
        (block.text for block in response.content if hasattr(block, "text")), ""
    )
