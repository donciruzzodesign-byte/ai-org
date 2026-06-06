# CUBOCCI STUDIO AI組織

週次ワインコンテンツを自動生成するマルチエージェントシステム。

## プロジェクト構成

- `runner.py` — 週次スケジューラー本体（schedule ライブラリで各曜日タスクを実行）
- `app.py` — 手動でCEOに指示するインタラクティブモード
- `tools.py` — エージェントが使うツール（web_search / search_papers / fetch_page / save_to_notion）
- `agents/` — エージェントのシステムプロンプト（.txt）
- `.claude/agents/` — Claude Code 用エージェント定義（.md）
- `logs/` — 日次ログファイル（YYYY-MM-DD.txt）
- `.env` — API キー（ANTHROPIC_API_KEY, NOTION_API_KEY, NOTION_PAGE_ID）

## エージェント構成

| エージェント | 役割 |
|---|---|
| ceo | 全体指揮・タスク振り分け・最終レポート |
| sommelier | イタリアワイン専門知識・テーマ提案・監修 |
| creator | 動画台本・編集指示書作成 |
| marketer | Instagram投稿文・アフィリエイト・反応分析 |
| barista | イタリアコーヒー専門知識・テーマ提案・地域紹介 |

## 週次スケジュール

| 曜日 | 時刻 | タスク | エージェント |
|------|------|--------|-------------|
| 月 | 09:00 | 今週テーマ決定 | sommelier |
| 月 | 09:30 | 州別おすすめワイン紹介 | sommelier |
| 月 | 10:00 | コーヒーテーマ決定 | barista |
| 月 | 10:30 | 地域別コーヒー紹介 | barista |
| 火 | 09:00 | 動画台本作成 | creator |
| 火 | 10:00 | コーヒー動画台本作成 | creator |
| 水 | 09:00 | レビュー通知（手動確認） | — |
| 木 | — | 動画収録・編集（オーナー手動） | — |
| 金 | 09:00 | SNS投稿文＋商品リスト | marketer |
| 金 | 10:00 | コーヒーSNS投稿文＋商品リスト | marketer |
| 土 | — | 動画公開＋SNS投稿（オーナー手動） | — |
| 日 | 20:00 | 反応分析レポート | marketer |

## 主要コマンド

```bash
# 手動でCEOに指示
python3 app.py

# 週次スケジューラー起動
python3 runner.py

# ログ確認
cat logs/$(date +%Y-%m-%d).txt
```

## 環境変数

```
ANTHROPIC_API_KEY=...       # 必須
NOTION_API_KEY=...          # 任意（Notion保存を有効にする場合）
NOTION_PAGE_ID=...          # 任意（保存先NotionページのID）
```

## Claude Code でのエージェント呼び出し方

.claude/agents/ に各エージェント定義があるため、Claude Code から直接呼び出し可能：
- `@sommelier` — ワイン知識・テーマ相談
- `@creator` — 台本・動画構成
- `@marketer` — SNS投稿文・マーケティング
- `@ceo` — 全体戦略・タスク調整
- `@barista` — コーヒー知識・テーマ相談・地域別コーヒー紹介

## 書籍コンテンツ生成（book_processor.py）

書籍テキストから複数のコンテンツを一括生成するスクリプト。

### 使い方

```bash
python3 book_processor.py input/books/<book>.txt
```

### 入力

`input/books/` に `.txt` ファイルを配置する（500文字以上必須）。

### 出力

`output/books/<book_name>/` に以下の5ファイルを生成：

| ファイル | 内容 |
|---|---|
| `summary.md` | 全体要約 |
| `chapter_points.md` | 章別ポイント |
| `note_article.md` | note記事 |
| `youtube_script.md` | YouTube動画台本 |
| `instagram_posts.md` | Instagram投稿文シリーズ |

### エージェント構成

| エージェント | 役割 |
|---|---|
| book_reader | 書籍テキストを要約・章別ポイント・ベネフィットに分解 |
| writer | note記事を執筆 |
| creator | YouTube動画台本を作成（ツールなし） |
| marketer | Instagram投稿文シリーズを作成（ツールなし） |
