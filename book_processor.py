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


BASE_DIR = Path(__file__).parent

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


def load_agent(name: str) -> str:
    return (BASE_DIR / "agents" / f"{name}.txt").read_text(encoding="utf-8")


def process_book(book_text: str, client: anthropic.Anthropic) -> dict:
    print("📖 書籍を読み込み中...")
    book_summary = call_agent(
        client,
        load_agent("book_reader"),
        f"以下の書籍テキストを分析してください:\n\n{book_text}",
    )
    print("✅ 要約完了")

    print("✍️  note記事を生成中...")
    note_article = call_agent(
        client,
        load_agent("writer"),
        f"以下の書籍要約をもとにnote記事を作成してください:\n\n{book_summary}",
    )
    print("✅ note記事完了")

    print("🎬 YouTube台本を生成中...")
    youtube_script = call_agent(
        client,
        load_agent("creator"),
        f"以下の書籍要約をもとに書籍解説YouTube動画の台本を作成してください:\n\n{book_summary}",
    )
    print("✅ YouTube台本完了")

    print("📸 Instagram投稿文を生成中...")
    instagram_posts = call_agent(
        client,
        load_agent("marketer"),
        f"以下の書籍要約をもとにInstagramの投稿文シリーズ（章ごと）を作成してください:\n\n{book_summary}",
    )
    print("✅ Instagram投稿文完了")

    # book_readerが ## 全体要約 / ## 章別ポイント の形式で返す
    summary_section = ""
    chapter_section = ""
    if "## 全体要約" in book_summary and "## 章別ポイント" in book_summary:
        parts = book_summary.split("## 章別ポイント")
        summary_section = parts[0].replace("## 全体要約", "").strip()
        chapter_section = "## 章別ポイント\n" + parts[1].split("## 読者へのベネフィット")[0].strip()
    else:
        summary_section = book_summary

    return {
        "summary": summary_section,
        "chapter_points": chapter_section,
        "note_article": note_article,
        "youtube_script": youtube_script,
        "instagram_posts": instagram_posts,
    }
