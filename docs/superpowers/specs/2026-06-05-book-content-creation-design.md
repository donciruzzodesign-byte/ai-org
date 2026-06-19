# 書籍コンテンツ自動生成システム 設計書

**日付:** 2026-06-05
**対象書籍:** BUSINESS STORY TELLING（紙の書籍）
**目的:** 書籍テキストからInstagram・note・YouTube用コンテンツを一括生成し、認知拡大に活用する

---

## 全体アーキテクチャ

```
input/books/
  └── business_story_telling.txt   ← ユーザーが書籍テキストを配置（抜粋でも可）

book_processor.py   ← 専用スクリプト（新規）
  ↓
[book_reader エージェント]（新規）
  └── 書籍を読み込み → 全体要約 + 章別ポイント + 読者ベネフィットを抽出
  ↓
[ceo エージェント]（既存）
  └── 要約を3エージェントに振り分け
       ├── [creator]（既存）   → YouTube 解説動画台本
       ├── [marketer]（既存）  → Instagram 投稿文シリーズ
       └── [writer エージェント]（新規） → note 記事

output/books/business_story_telling/
  ├── summary.md
  ├── chapter_points.md
  ├── instagram_posts.md
  ├── note_article.md
  └── youtube_script.md
```

---

## 新規コンポーネント

### `book_reader` エージェント
- **ファイル:** `agents/book_reader.txt`, `.claude/agents/book_reader.md`
- **入力:** 書籍テキスト（全文・抜粋どちらも対応）
- **出力:**
  - 全体要約（文字数制限なし）
  - 章別ポイント（各章の核心メッセージを箇条書き）
  - 読者へのベネフィット（「この本を読むと何が変わるか」）

### `writer` エージェント（note記事専門）
- **ファイル:** `agents/writer.txt`, `.claude/agents/writer.md`
- **入力:** book_readerが生成した要約・章別ポイント
- **出力:** note向け解説記事
  - 導入（なぜこの本？）
  - 章別解説（各章のポイント＋解釈）
  - まとめ（読者へのアクション提案）

### `book_processor.py`（実行スクリプト）
- **入力:** `.txt` ファイルパス
- **処理:** book_reader → ceo → creator / marketer / writer を順次呼び出し
- **出力:** `output/books/<book_name>/` 以下に5ファイルを生成

---

## 既存エージェントの拡張

| エージェント | 拡張内容 |
|---|---|
| creator | 書籍解説モードの指示を追加（YouTube台本生成） |
| marketer | 章ごとシリーズ形式のInstagram投稿文生成に対応 |
| ceo | book_readerからの要約を受け取り3エージェントに振り分ける指示を追加 |

---

## 書籍テキストの入力方法（紙の書籍）

1. iPhoneカメラで重要なページを撮影
2. 写真アプリでテキスト長押し → 「テキストをコピー」（Live Text機能）
3. コピーしたテキストを `input/books/business_story_telling.txt` に貼り付けて保存
4. 全ページ不要。章ごとに重要な箇所だけの抜粋でも動作する

---

## 出力ファイル構成

```
output/books/business_story_telling/
  ├── summary.md          ← 全体要約（文字数制限なし）
  ├── chapter_points.md   ← 章別ポイント一覧
  ├── instagram_posts.md  ← Instagram投稿文（章ごとシリーズ）
  ├── note_article.md     ← note記事
  └── youtube_script.md   ← YouTube解説動画台本
```

全ファイルはMarkdown形式。コピペで各プラットフォームにそのまま投稿できる状態で出力する。

---

## エラーハンドリング

| ケース | 対処 |
|---|---|
| 入力ファイルが存在しない | エラーメッセージを出して終了 |
| テキストが500文字未満 | 「テキストが少なすぎます。もう少し追加してください」と警告して終了 |
| APIエラー | 既存 `app.py` と同じエラー処理を流用 |

---

## 実行コマンド

```bash
# 書籍テキストを配置
cp business_story_telling.txt input/books/

# 実行（全プラットフォーム一括生成）
python3 book_processor.py input/books/business_story_telling.txt
```

---

## スコープ外

- PDF直接読み込み（今後必要になれば追加）
- 複数書籍の一括処理（今回は1冊のみ）
- コンテンツのNotion自動保存（手動コピペで対応）
