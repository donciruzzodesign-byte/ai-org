# 週次コンテンツ重複回避システム 設計ドキュメント

**作成日:** 2026-07-27
**ステータス:** 承認済み

---

## 概要

週次エージェント（sommelier / barista / creator / marketer）が新しいテーマ・コンテンツを生成する際、過去に扱った産地・品種・切り口・商品を意識せずに提案してしまい、週をまたいで内容が被ることがある。

本設計では、Notionの「コンテンツ生成物」DBに蓄積された過去の制作物から一言テーマを抽出して記録し、次回の生成時にそれを参考情報としてプロンプトへ注入することで、重複を減らす。

対象は `runner.py` の週次スケジュールタスク全体（`run_agent()` を経由するもの）。ただし日曜の反応分析レポート（`sunday_task`）は、性質上「毎週内容が異なるべきもの」であり、`カテゴリ` 推論が自然に「その他」となるため対象外（明示的な除外ロジックは実装しない）。

---

## ゴール

- 週次エージェントが新しいテーマ・コンテンツを生成する前に、同カテゴリ（ワイン/コーヒー）の直近8件のテーマ一覧をプロンプトに自動で受け取る
- 生成が完了したら、その本文から一言テーマを自動抽出し、Notionページの新規プロパティ「テーマ」に保存する
- `run_agent()` の呼び出し元（`runner.py` 内の各タスク関数、13箇所）は一切変更不要。ロジックは `run_agent()` 内に集約する
- Notion側の設定・API未設定時は今まで通りスキップ扱いとし、処理は止めない

---

## 前提となる外部セットアップ（オーナーが手動で実施）

1. `python3 scripts/notion_add_theme.py` を一度だけ実行し、「コンテンツ生成物」DBに「テーマ」プロパティ（rich_text）を追加する。このスクリプトは既存ページを遡って読み込み、テーマを抽出してバックフィルする。
2. 追加の環境変数は不要（既存の `NOTION_API_KEY` / `NOTION_DATABASE_ID` / `ANTHROPIC_API_KEY` を利用）。

このマイグレーションを実行する前に本機能をデプロイすると、「テーマ」プロパティが存在しないためNotionへの保存が失敗する。既存の `scripts/notion_add_status.py`（ステータス追加）と同じ運用パターン。

---

## ファイル構成

```
ai-org/
├── tools.py                          # extract_theme() / notion_recent_themes() を追加、
│                                      # _create_database_page / save_to_notion /
│                                      # notion_append_to_page に theme 引数を追加
├── runner.py                         # run_agent() 内に重複回避ロジックを追加（呼び出し元は無変更）
├── scripts/
│   └── notion_add_theme.py           # 新規：一度きりのマイグレーション
└── tests/
    ├── test_tools.py                 # extract_theme / notion_recent_themes のテスト追加
    └── test_runner.py                # run_agent の重複回避コンテキスト注入・保存テスト追加
```

---

## アーキテクチャ・データフロー

```
[run_agent() 開始]
      │
      ├─ category = _infer_category(label, prompt)   ← 既存ロジックを再利用
      │
      ├─ category が ワイン/コーヒー なら
      │     recent = notion_recent_themes(category, limit=8)
      │     recent があれば prompt 末尾に追記
      │        「【重複回避】直近の制作物テーマ一覧です。...」
      │
      ├─ (既存) WIP再開ロジック（変更なし）
      │
      ├─ LLM生成ループ（変更なし）→ final_text
      │
      ├─ theme = extract_theme(final_text)   ← Haikuで1行要約（新規）
      │
      └─ save_to_notion(title, final_text, status, theme)
            または notion_append_to_page(page_id, final_text, status, theme)
```

---

## コンポーネント詳細

### `tools.py: extract_theme(content: str) -> str`

生成された本文から重複回避用の一言テーマ（20文字以内）を抽出する軽量LLM呼び出し。

- モデルは `claude-haiku-4-5-20251001`（低コスト・低レイテンシ）
- `content` の先頭3000文字のみを渡す（コスト抑制、テーマは冒頭に出ることが多いため）
- プロンプト：「以下の文章の主題を日本語で20文字以内の1行で要約してください。要約のみを出力し、他の説明は書かないでください。」
- 失敗時（API未設定・例外）は空文字列を返す。呼び出し元はテーマなしとして扱い、処理を継続する（保存自体は失敗させない）
- Anthropicクライアントは `tools.py` 内でモジュールレベルの遅延初期化シングルトンとして保持する（`ANTHROPIC_API_KEY` 未設定時のインポートエラーを避けるため）

### `tools.py: notion_recent_themes(category: str, limit: int = 8) -> str`

指定カテゴリの直近 `limit` 件のテーマ一覧を取得する。

- Notion DB クエリ：`filter: {property: "カテゴリ", select: {equals: category}}`、`sorts: [{timestamp: "created_time", direction: "descending"}]`、`page_size: limit`
- 各ページから「テーマ」プロパティ（rich_text）と「title」プロパティを取り出し、`- {テーマ}（{タイトル}）` の形式で行を作る
- テーマが空のページ（未マイグレーション・抽出失敗）はスキップする
- `NOTION_API_KEY` / `NOTION_DATABASE_ID` 未設定、またはAPIエラー時は空文字列を返す（`notion_find_wip` と同様のフェイルセーフ方針）
- 該当ページが1件もない、またはテーマがすべて空の場合も空文字列を返す（＝プロンプトへの追記なし）

### `tools.py`: 既存関数への `theme` 引数追加

- `_create_database_page(token, database_id, title, category, status="要確認", theme="")`：`theme` が非空なら `"テーマ": {"rich_text": [{"text": {"content": theme}}]}` をプロパティに追加
- `save_to_notion(title, content, status="要確認", theme="")`：`_create_database_page` に `theme` を渡す
- `notion_append_to_page(page_id, content, status="要確認", theme="")`：本文追記後、プロパティ更新を1回のPATCHにまとめる。`theme` が空なら `ステータス` のみ、非空なら `ステータス` と `テーマ` を同時に更新する新規ヘルパー `_update_page_properties(token, page_id, status, theme="")` を追加し、`notion_update_status` はこのヘルパーを `theme=""` で呼ぶ薄いラッパーとして維持する（既存の呼び出し元・テストへの後方互換を保つ）

いずれも `theme` はデフォルト空文字列（後方互換：既存呼び出し元・既存テストに影響なし）。

### `runner.py: run_agent()` の変更点

1. 既存の `category = _infer_category(label, prompt)` の直後に、`category in ("ワイン", "コーヒー")` なら `notion_recent_themes(category)` を呼び、結果が非空ならプロンプトに追記
2. `final_text` 確定後、`extract_theme(final_text)` を呼んで `theme` を得る
3. 末尾の `save_to_notion(...)` / `notion_append_to_page(...)` 呼び出しに `theme=theme` を追加

### `scripts/notion_add_theme.py`（新規）

`scripts/notion_add_status.py` と同じ構成・スタイルに揃える。

1. `_load_env()` で `.env` を読み込む
2. Notion DBに「テーマ」プロパティ（rich_text）を追加する `PATCH /v1/databases/{id}` を実行
3. 既存の全ページを走査し、「テーマ」が未設定のページは `notion_read_page()` で本文を取得 → `extract_theme()` で1行要約 → Notionページを直接PATCHしてテーマを設定する
4. 各ページの処理結果を標準出力にログする

---

## エラーハンドリング

- `extract_theme()` が失敗（API未設定・例外・タイムアウト）→ 空文字列、生成・保存フローは通常通り継続
- `notion_recent_themes()` が失敗 → 空文字列、プロンプトへの追記なし（重複回避ができないだけで、生成自体は通常通り進む）
- 「テーマ」プロパティ未追加の状態で `theme` 非空を保存しようとした場合 → Notion APIがエラーを返す可能性がある。この状態を避けるため、マイグレーションスクリプトの実行を前提条件として明記する（`CLAUDE.md` に追記）

---

## テスト方針（TDD）

`tests/test_tools.py` に追加：

- `extract_theme`: Anthropicクライアントをモックし、レスポンステキストがそのまま返ることを確認。API例外時に空文字列を返すことを確認
- `notion_recent_themes`: `requests.post` をモックし、正しいfilter/sortsでクエリされること、テーマ一覧が期待フォーマットで整形されること、テーマ空ページがスキップされること、結果0件で空文字列を返すことを確認
- `save_to_notion` / `notion_append_to_page`: `theme` 引数がNotionペイロードに正しく含まれること（省略時は含まれないこと）を確認

`tests/test_runner.py` に追加：

- `run_agent` がワイン/コーヒーカテゴリの場合に `notion_recent_themes` を呼び、結果をプロンプトに含めてAPIを呼ぶことを確認
- `notion_recent_themes` が空文字列を返す場合、プロンプトに重複回避セクションが追加されないことを確認
- `run_agent` が生成完了後に `extract_theme` を呼び、その結果を `save_to_notion` / `notion_append_to_page` に渡すことを確認
- 既存のWIP再開・自動継続・途中保存のテストが引き続き通ること（回帰確認）

`scripts/notion_add_theme.py` は `scripts/notion_add_status.py` に既存テストがあるか確認し、あれば同様のテストパターンを踏襲する。

---

## スコープ外（今回やらないこと）

- `sunday_task`（反応分析レポート）への明示的な除外ロジック（カテゴリ推論により自然に対象外となるため不要）
- `app.py` の対話モード（手動チャット）への適用（週次自動生成のみが対象）
- テーマの類似度判定（ベクトル検索・embeddingなど）による厳密な重複検出。今回はLLM自身の判断に委ねるプロンプト注入方式のみ
- 「テーマ」プロパティのUI（Notion側でのフィルタービュー等）の追加整備
