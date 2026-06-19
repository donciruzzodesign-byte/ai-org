# Notion 部門別保存 設計ドキュメント

**日付:** 2026-06-04  
**対象:** CUBOCCI STUDIO AI組織（ai-org）

## 概要

ローカルログへの保存を廃止し、Notion を唯一のコンテンツ保管場所とする。
Notion 内はワイン部門・コーヒー部門に分けて保管する。

## Notion 構造

```
CUBOCCI STUDIO（既存の親ページ / NOTION_PAGE_ID）
├── ワイン部門（初回時に自動作成）
│   ├── 月曜：今週のワインテーマ決定 (YYYY-MM-DD)
│   ├── 月曜：州別おすすめワイン紹介 (YYYY-MM-DD)
│   ├── 火曜：ワイン動画台本作成 (YYYY-MM-DD)
│   └── 金曜：SNS投稿文＋商品リスト (YYYY-MM-DD)
├── コーヒー部門（初回時に自動作成）
│   ├── 月曜：コーヒーテーマ決定 (YYYY-MM-DD)
│   ├── 月曜：地域別コーヒー紹介 (YYYY-MM-DD)
│   ├── 火曜：コーヒー動画台本作成 (YYYY-MM-DD)
│   └── 金曜：コーヒーSNS投稿文＋商品リスト (YYYY-MM-DD)
└── 日曜：反応分析レポート (YYYY-MM-DD)  ← 部門なし・親直下
```

## タスクと部門の対応

| タスク | 部門 |
|---|---|
| 月曜：今週のワインテーマ決定 | ワイン部門 |
| 月曜：州別おすすめワイン紹介 | ワイン部門 |
| 火曜：ワイン動画台本作成 | ワイン部門 |
| 金曜：SNS投稿文＋商品リスト | ワイン部門 |
| 月曜：コーヒーテーマ決定 | コーヒー部門 |
| 月曜：地域別コーヒー紹介 | コーヒー部門 |
| 火曜：コーヒー動画台本作成 | コーヒー部門 |
| 金曜：コーヒーSNS投稿文＋商品リスト | コーヒー部門 |
| 日曜：反応分析レポート | なし（親直下） |

## 変更ファイル

### tools.py

1. `_get_or_create_department_page(token, parent_page_id, department_name) -> str | None`
   - 親ページの子ページ一覧を検索
   - 指定名のページが存在すれば page_id を返す
   - 存在しなければ新規作成して page_id を返す

2. `save_to_notion(title, content, department=None) -> str`
   - `department` が指定された場合、`_get_or_create_department_page()` で保存先を決定
   - `department=None` の場合、既存通り親ページ直下に保存

### runner.py

1. `save_log()` の呼び出しをコンテンツ保存用途で削除（91行目）
2. `save_log()` 関数・`_read_todays_log()` 関数は内部の文脈渡し用として維持
3. 全 `save_to_notion()` 呼び出しに `department` 引数を追加
4. ログファイルパスを表示する print メッセージを削除

## 保持するもの

- `save_log()` / `_read_todays_log()` — タスク間の文脈引き継ぎ用一時ファイルとして残す（`logs/` ディレクトリ）
- `logs/launchagent.log` / `logs/launchagent_error.log` — LaunchAgent のシステムログは変更なし

## 環境変数

変更なし。`NOTION_API_KEY` と `NOTION_PAGE_ID` のみで動作する。
