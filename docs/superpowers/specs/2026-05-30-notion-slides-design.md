# Notion スライド風子ページ保存 — 設計仕様

**日付:** 2026-05-30  
**対象ファイル:** `tools.py`  
**ステータス:** 承認済み

---

## 背景と目的

現在の `save_to_notion` は親ページ（`NOTION_PAGE_ID`）に `heading_2` + `paragraph` ブロックを追記し続ける。出力がすべて1ページに混在するため読みづらく、そのまま利用できない。

**ゴール:** タスクの出力ごとに独立した子ページを作成し、コンテンツをスライド風（セクションごとに divider で区切り）に整形して保存する。

---

## アーキテクチャ

### 変更前

```
親ページ (NOTION_PAGE_ID)
 └── heading_2 + paragraph が追記され続ける
```

### 変更後

```
親ページ (NOTION_PAGE_ID)
 ├── 月曜：今週テーマ決定 (2026-05-30)   ← 子ページ
 ├── 火曜：動画台本作成 (2026-05-30)     ← 子ページ
 │    ├── [divider]
 │    ├── heading_2: オープニング
 │    │    bulleted_list_item × n
 │    ├── [divider]
 │    ├── heading_2: 本編
 │    │    bulleted_list_item × n
 │    └── ...
 └── 金曜：SNS投稿文 (2026-05-30)        ← 子ページ
```

---

## コンテンツ変換ルール

エージェント出力のテキストを行単位で解析し、以下のルールで Notion ブロックに変換する。

| 入力パターン | 変換後 Notion ブロック | 補足 |
|---|---|---|
| `# テキスト` | `heading_1` | ページタイトル相当 |
| `## テキスト` | `divider` → `heading_2` | スライド区切り |
| `### テキスト` | `heading_3` | — |
| `- テキスト` または `* テキスト` | `bulleted_list_item` | — |
| 数字. テキスト（`1. ...`） | `numbered_list_item` | — |
| 空行 | スキップ | — |
| それ以外 | `paragraph` | — |

---

## Notion API フロー

1. **子ページ作成**  
   `POST /pages`  
   ```json
   {
     "parent": { "page_id": "<NOTION_PAGE_ID>" },
     "properties": {
       "title": [{ "text": { "content": "<label> (<YYYY-MM-DD>)" } }]
     }
   }
   ```
   → レスポンスから `id`（子ページID）を取得

2. **ブロック追加**  
   `PATCH /blocks/<child_page_id>/children`  
   変換済みブロックのリストを送信。  
   Notion の上限（1リクエスト100ブロック）を超える場合は 100ブロックずつ分割して複数リクエストを送る。

---

## 変更スコープ

- **変更するファイル:** `tools.py` の `save_to_notion` 関数のみ
- **変更しないファイル:** `runner.py`, `app.py`, エージェント `.txt` ファイル, `TOOL_DEFINITIONS`
- **シグネチャ変更なし:** `save_to_notion(title, content)` のまま。呼び出し側（`runner.py:94`）は変更不要。

---

## エラーハンドリング

- 子ページ作成失敗 → エラーメッセージを返す（既存の動作を維持）
- ブロック追加失敗 → エラーメッセージを返す
- `NOTION_API_KEY` / `NOTION_PAGE_ID` 未設定 → 既存の early return を維持

---

## 成功基準

1. `runner.py` でタスクが完了するたびに、親ページ配下に新しい子ページが作成される
2. 子ページのタイトルは `{label} ({YYYY-MM-DD})` 形式
3. `##` で始まるセクションの前に `divider` が挿入される
4. `- ` で始まる行が `bulleted_list_item` として保存される
5. 100ブロックを超えるコンテンツも欠落なく保存される
