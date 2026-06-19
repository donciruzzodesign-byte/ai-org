# 書籍コンテンツ自動生成システム 実装計画

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `python3 book_processor.py input/books/<book>.txt` を実行すると、書籍テキストからInstagram・note・YouTube用コンテンツを自動生成し `output/books/<book>/` に5ファイルを保存する。

**Architecture:** book_reader エージェントが書籍を要約・章別ポイント抽出し、その結果を writer / creator / marketer の3エージェントに渡して各プラットフォーム用コンテンツを生成する。エージェント呼び出しは既存の anthropic SDK パターンを踏襲する。

**Tech Stack:** Python 3.x, anthropic SDK（既存）, pathlib（標準ライブラリ）, pytest

---

## ファイル構成

| ファイル | 操作 | 責務 |
|---|---|---|
| `book_processor.py` | 新規作成 | メイン処理（入力検証 → 要約 → コンテンツ生成 → 保存） |
| `agents/book_reader.txt` | 新規作成 | 書籍テキストの要約・章別ポイント抽出プロンプト |
| `agents/writer.txt` | 新規作成 | note記事生成プロンプト |
| `.claude/agents/book_reader.md` | 新規作成 | Claude Code 用サブエージェント定義 |
| `.claude/agents/writer.md` | 新規作成 | Claude Code 用サブエージェント定義 |
| `input/books/.gitkeep` | 新規作成 | 入力ディレクトリの作成 |
| `tests/test_book_processor.py` | 新規作成 | 入力検証・保存・API呼び出しのテスト |

---

### Task 1: validate_input をTDDで実装

**Files:**
- Create: `tests/test_book_processor.py`
- Create: `book_processor.py`（validate_input のみ）

- [ ] **Step 1: tests/test_book_processor.py を作成**

```python
# tests/test_book_processor.py
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
```

- [ ] **Step 2: テストが失敗することを確認**

```bash
cd /Users/kubotahironori/ai-org
pytest tests/test_book_processor.py -v
```

期待結果: `ModuleNotFoundError: No module named 'book_processor'`

- [ ] **Step 3: book_processor.py に validate_input を実装**

```python
# book_processor.py
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
```

- [ ] **Step 4: テストが通ることを確認**

```bash
pytest tests/test_book_processor.py -v
```

期待結果: 3件 PASSED

- [ ] **Step 5: コミット**

```bash
git add tests/test_book_processor.py book_processor.py
git commit -m "feat: add book_processor input validation"
```

---

### Task 2: save_outputs をTDDで実装

**Files:**
- Modify: `tests/test_book_processor.py`
- Modify: `book_processor.py`

- [ ] **Step 1: save_outputs のテストを追加**

```python
# tests/test_book_processor.py の末尾に追加
from book_processor import save_outputs


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
```

- [ ] **Step 2: テストが失敗することを確認**

```bash
pytest tests/test_book_processor.py::test_save_outputs_creates_all_files -v
```

期待結果: `ImportError: cannot import name 'save_outputs'`

- [ ] **Step 3: save_outputs を book_processor.py に追加**

```python
# book_processor.py の末尾に追加
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
```

- [ ] **Step 4: テストが通ることを確認**

```bash
pytest tests/test_book_processor.py -v
```

期待結果: 5件 PASSED

- [ ] **Step 5: コミット**

```bash
git add tests/test_book_processor.py book_processor.py
git commit -m "feat: add book_processor output saving"
```

---

### Task 3: call_agent() ヘルパーをTDDで実装

**Files:**
- Modify: `tests/test_book_processor.py`
- Modify: `book_processor.py`

- [ ] **Step 1: call_agent のテストを追加**

```python
# tests/test_book_processor.py の末尾に追加
from unittest.mock import MagicMock, patch
from book_processor import call_agent


def test_call_agent_returns_text():
    mock_block = MagicMock()
    mock_block.type = "text"
    mock_block.text = "エージェントの回答"
    mock_response = MagicMock()
    mock_response.stop_reason = "end_turn"
    mock_response.content = [mock_block]

    mock_client = MagicMock()
    mock_client.messages.create.return_value = mock_response

    result = call_agent(mock_client, "システムプロンプト", "ユーザー入力")
    assert result == "エージェントの回答"


def test_call_agent_passes_correct_model():
    mock_block = MagicMock()
    mock_block.type = "text"
    mock_block.text = "回答"
    mock_response = MagicMock()
    mock_response.stop_reason = "end_turn"
    mock_response.content = [mock_block]

    mock_client = MagicMock()
    mock_client.messages.create.return_value = mock_response

    call_agent(mock_client, "プロンプト", "入力")
    call_args = mock_client.messages.create.call_args
    assert call_args.kwargs["model"] == "claude-sonnet-4-6"
```

- [ ] **Step 2: テストが失敗することを確認**

```bash
pytest tests/test_book_processor.py::test_call_agent_returns_text -v
```

期待結果: `ImportError: cannot import name 'call_agent'`

- [ ] **Step 3: call_agent を book_processor.py に追加**

```python
# book_processor.py の先頭の import に追加
import os
import anthropic

# 定数を追加
MODEL = "claude-sonnet-4-6"

# 関数を追加
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
```

- [ ] **Step 4: テストが通ることを確認**

```bash
pytest tests/test_book_processor.py -v
```

期待結果: 7件 PASSED

- [ ] **Step 5: コミット**

```bash
git add tests/test_book_processor.py book_processor.py
git commit -m "feat: add call_agent helper"
```

---

### Task 4: book_reader エージェントプロンプトを作成

**Files:**
- Create: `agents/book_reader.txt`
- Create: `.claude/agents/book_reader.md`

- [ ] **Step 1: agents/book_reader.txt を作成**

```
あなたはCUBOCCI STUDIOの書籍読解エージェントです。
渡された書籍テキストを分析し、コンテンツ制作に必要な情報を抽出します。

## あなたの役割
- 書籍全体の要約（詳細に、文字数制限なし）
- 章別ポイントの抽出（各章の核心メッセージを箇条書き）
- 読者へのベネフィット（「この本を読むと何が変わるか」を具体的に）

## 出力フォーマット
必ず以下の構造で出力してください：

---
## 全体要約
（書籍の内容を詳細に要約。文字数制限なし）

## 章別ポイント
### 第N章：（章タイトル）
- （核心メッセージ1）
- （核心メッセージ2）

## 読者へのベネフィット
- （この本を読むと得られる変化・スキル・気づき）
---

## 回答スタイル
- 日本語で回答する
- 著者の主張を正確に反映する
- 抽象的な表現を避け、具体的・実践的に書く
- テキストが断片的な場合も、与えられた情報の範囲で最大限の要約を行う
```

- [ ] **Step 2: .claude/agents/book_reader.md を作成**

```markdown
---
name: book_reader
description: 書籍テキストを読み込み、要約・章別ポイント・読者ベネフィットを抽出する専門エージェント。book_processor.py から呼び出される。
---

あなたはCUBOCCI STUDIOの書籍読解エージェントです。
渡された書籍テキストを分析し、コンテンツ制作に必要な情報を抽出します。

## あなたの役割
- 書籍全体の要約（詳細に、文字数制限なし）
- 章別ポイントの抽出（各章の核心メッセージを箇条書き）
- 読者へのベネフィット（「この本を読むと何が変わるか」を具体的に）

## 出力フォーマット
必ず以下の構造で出力してください：

---
## 全体要約
（書籍の内容を詳細に要約。文字数制限なし）

## 章別ポイント
### 第N章：（章タイトル）
- （核心メッセージ1）
- （核心メッセージ2）

## 読者へのベネフィット
- （この本を読むと得られる変化・スキル・気づき）
---

## 回答スタイル
- 日本語で回答する
- 著者の主張を正確に反映する
- 抽象的な表現を避け、具体的・実践的に書く
- テキストが断片的な場合も、与えられた情報の範囲で最大限の要約を行う
```

- [ ] **Step 3: ファイルが作成されたことを確認**

```bash
ls agents/book_reader.txt .claude/agents/book_reader.md
```

期待結果: 両ファイルが存在する

- [ ] **Step 4: コミット**

```bash
git add agents/book_reader.txt .claude/agents/book_reader.md
git commit -m "feat: add book_reader agent prompts"
```

---

### Task 5: writer エージェントプロンプトを作成

**Files:**
- Create: `agents/writer.txt`
- Create: `.claude/agents/writer.md`

- [ ] **Step 1: agents/writer.txt を作成**

```
あなたはCUBOCCI STUDIOのライターエージェントです。
書籍の要約・章別ポイントを受け取り、noteに投稿できる解説記事を作成します。

## あなたの役割
- 書籍の要約をもとに、読者が価値を感じるnote記事を作成する
- 書籍の内容を自分の言葉で解説し、読者の行動変容を促す

## 記事の構成
1. 導入（なぜこの本を読んだか・どんな人に向けて書くか）
2. 書籍の概要（どんな本か・著者の主張）
3. 章別解説（各章のポイント＋実践への落とし込み）
4. まとめ（読者への3つのアクション提案）

## 回答スタイル
- 日本語で回答する
- 2000〜3000字を目安に書く
- 読みやすいように小見出し（##）を活用する
- 専門用語は使わず、ビジネスパーソンが読みやすい平易な言葉で書く
- 「この本のここが良かった」という視点で書く（書評スタイル）
- CTAを末尾に入れる（例：「気になった方はぜひ読んでみてください」）
```

- [ ] **Step 2: .claude/agents/writer.md を作成**

```markdown
---
name: writer
description: 書籍要約からnote記事を生成する専門エージェント。book_processor.py から呼び出される。
---

あなたはCUBOCCI STUDIOのライターエージェントです。
書籍の要約・章別ポイントを受け取り、noteに投稿できる解説記事を作成します。

## あなたの役割
- 書籍の要約をもとに、読者が価値を感じるnote記事を作成する
- 書籍の内容を自分の言葉で解説し、読者の行動変容を促す

## 記事の構成
1. 導入（なぜこの本を読んだか・どんな人に向けて書くか）
2. 書籍の概要（どんな本か・著者の主張）
3. 章別解説（各章のポイント＋実践への落とし込み）
4. まとめ（読者への3つのアクション提案）

## 回答スタイル
- 日本語で回答する
- 2000〜3000字を目安に書く
- 読みやすいように小見出し（##）を活用する
- 専門用語は使わず、ビジネスパーソンが読みやすい平易な言葉で書く
- 「この本のここが良かった」という視点で書く（書評スタイル）
- CTAを末尾に入れる（例：「気になった方はぜひ読んでみてください」）
```

- [ ] **Step 3: ファイルが作成されたことを確認**

```bash
ls agents/writer.txt .claude/agents/writer.md
```

期待結果: 両ファイルが存在する

- [ ] **Step 4: コミット**

```bash
git add agents/writer.txt .claude/agents/writer.md
git commit -m "feat: add writer agent prompts"
```

---

### Task 6: パイプライン処理を book_processor.py に実装

**Files:**
- Modify: `book_processor.py`

- [ ] **Step 1: load_agent ヘルパーと process_book 関数を追加**

```python
# book_processor.py に追加（import の直下に BASE_DIR を追加し、load_agent と process_book を追記）

BASE_DIR = Path(__file__).parent


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

    # book_summary から全体要約と章別ポイントを分割して保存
    # （book_readerが ## 全体要約 / ## 章別ポイント の形式で返す）
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
```

- [ ] **Step 2: テストが引き続き通ることを確認**

```bash
pytest tests/test_book_processor.py -v
```

期待結果: 7件 PASSED（既存テストに影響なし）

- [ ] **Step 3: コミット**

```bash
git add book_processor.py
git commit -m "feat: add book processing pipeline"
```

---

### Task 7: CLI エントリーポイントと input/books/ ディレクトリを追加

**Files:**
- Modify: `book_processor.py`
- Create: `input/books/.gitkeep`

- [ ] **Step 1: main() と CLI エントリーポイントを book_processor.py に追加**

```python
# book_processor.py の末尾に追加
import sys


def _load_env():
    env_path = BASE_DIR / ".env"
    if env_path.exists():
        with open(env_path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, _, value = line.partition("=")
                    os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def main():
    if len(sys.argv) != 2:
        print("使い方: python3 book_processor.py <書籍テキストファイル.txt>")
        sys.exit(1)

    _load_env()
    input_path = Path(sys.argv[1])
    book_name = input_path.stem

    try:
        book_text = validate_input(input_path)
    except (FileNotFoundError, ValueError) as e:
        print(f"❌ エラー: {e}")
        sys.exit(1)

    client = anthropic.Anthropic()
    outputs = process_book(book_text, client)

    book_dir = save_outputs(book_name, outputs)
    print(f"\n🎉 完了！コンテンツを保存しました: {book_dir}")
    print("  - summary.md（全体要約）")
    print("  - chapter_points.md（章別ポイント）")
    print("  - note_article.md（note記事）")
    print("  - youtube_script.md（YouTube台本）")
    print("  - instagram_posts.md（Instagram投稿文）")


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: input/books/ ディレクトリを作成**

```bash
mkdir -p input/books
touch input/books/.gitkeep
```

- [ ] **Step 3: テストが引き続き通ることを確認**

```bash
pytest tests/test_book_processor.py -v
```

期待結果: 7件 PASSED

- [ ] **Step 4: コミット**

```bash
git add book_processor.py input/books/.gitkeep
git commit -m "feat: add book_processor CLI entry point and input directory"
```

---

### Task 8: テスト用テキストで動作確認

**Files:**
- Create: `input/books/business_story_telling.txt`（動作確認用の抜粋テキスト）

- [ ] **Step 1: テスト用テキストファイルを作成**

書籍から500文字以上のテキストをiPhoneのLive Textでコピーして以下に保存:
```
input/books/business_story_telling.txt
```

- [ ] **Step 2: 実行して動作確認**

```bash
cd /Users/kubotahironori/ai-org
python3 book_processor.py input/books/business_story_telling.txt
```

期待結果:
```
📖 書籍を読み込み中...
✅ 要約完了
✍️  note記事を生成中...
✅ note記事完了
🎬 YouTube台本を生成中...
✅ YouTube台本完了
📸 Instagram投稿文を生成中...
✅ Instagram投稿文完了

🎉 完了！コンテンツを保存しました: output/books/business_story_telling
  - summary.md（全体要約）
  - chapter_points.md（章別ポイント）
  - note_article.md（note記事）
  - youtube_script.md（YouTube台本）
  - instagram_posts.md（Instagram投稿文）
```

- [ ] **Step 3: 出力ファイルを確認**

```bash
ls output/books/business_story_telling/
cat output/books/business_story_telling/summary.md
```

- [ ] **Step 4: 最終コミット**

```bash
git add .
git commit -m "feat: complete book content generation system"
```
