# Instagram Insights 自動連携システム 設計ドキュメント

**作成日:** 2026-07-24
**ステータス:** 承認済み

---

## 概要

オーナーが運用しているワインInstagramアカウント（`italian.wine.ciro`）の投稿分析用Googleスプレッドシートに対し、Meta（Instagram Graph API）から取得できるInsightsデータを自動で書き込むシステム。

現状、オーナーは毎週手動でMeta Business Suiteの画面からInsights数値を確認し、スプレッドシートにコピーしている。この転記作業を自動化する。

対象は既存スプレッドシート（1w668TozaQX-hM7rJsEXSde0fiwxfW0g0i9Dumvx3P0I）の**タブ1・タブ2のみ**。他の3タブ（ダイエットアカウント風のデータが入っている）は別件のテンプレートであり、本設計とは無関係。

CUBOCCI STUDIOのmarketerエージェントの反応分析タスク（日曜20:00）とは連携しない。今回のスコープはスプレッドシートへの自動書き込みのみ。

---

## ゴール

- `python3 scripts/sync_instagram_insights.py` を実行すると、直近の投稿のInsightsデータがスプレッドシートのタブ1・2に自動入力される
- `runner.py` の週次スケジュールからも同じ処理を呼び出せる
- APIで取得できない項目（インプレッション流入元内訳、翌日/1週間後スナップショット、動画時間、スキップ率、視聴維持率、サムネ列）は自動入力せず、これまで通り手動入力の運用を維持する
- 個別投稿の取得失敗やトークン期限切れが起きても、処理全体は止まらず分かりやすいエラーメッセージを出す

---

## 前提となる外部セットアップ（オーナーが手動で実施）

実装に着手する前に、以下がオーナー側で完了している必要がある。

1. Instagramアカウントをプロアカウント（ビジネスまたはクリエイター）に切り替える
2. 連携用のFacebookページを作成し、Instagramアカウントと連携する
3. [Meta for Developers](https://developers.facebook.com/) でアプリを作成し、Instagram Graph API・`instagram_basic`・`instagram_manage_insights` 権限を設定する
4. 長期アクセストークン（有効期限約60日）を発行する
5. Google Cloud Consoleでサービスアカウントを作成し、JSONキーをダウンロードする
6. 対象スプレッドシートを、サービスアカウントのメールアドレスに対して編集権限で共有する

このガイドは実装完了後、オーナー向けの手順書として `docs/` に別途まとめる。

---

## 環境変数（`.env` に追加）

```
META_ACCESS_TOKEN=...            # Instagram Graph API 長期アクセストークン
META_IG_USER_ID=...              # Instagram ビジネスアカウントのID
GOOGLE_SERVICE_ACCOUNT_JSON=...  # Google Sheets書き込み用サービスアカウントJSONキーのパス
INSTAGRAM_SHEET_ID=...           # 対象スプレッドシートID
```

`META_ACCESS_TOKEN` と `GOOGLE_SERVICE_ACCOUNT_JSON` は既存の `NOTION_API_KEY` 等と同様に任意環境変数として扱い、未設定時は起動時に分かりやすいメッセージを出して終了する。

---

## ファイル構成

```
ai-org/
├── tools_instagram.py                     # 核心ロジック（新規）
├── scripts/
│   └── sync_instagram_insights.py         # 単体実行用CLI（新規）
├── runner.py                              # 週次タスクとして1行追加
└── tests/
    └── test_instagram.py                  # 新規
```

---

## アーキテクチャ

```
[Meta for Developers アプリ] --Graph API--> [tools_instagram.py] --gspread--> [Google Sheet(既存)]
                                                      ^
                                        [scripts/sync_instagram_insights.py]（単体実行）
                                                      ^
                                              [runner.py の週次タスク]（自動実行）
```

`tools_instagram.py` は他の `tools_*.py` と同じ配置パターンに従い、Graph APIとのやり取り・Sheets書き込みロジックをまとめる。`scripts/sync_instagram_insights.py` は `scripts/notion_add_status.py` と同じ位置づけのCLIラッパー。`runner.py` には既存の水曜レビュー通知タスクの近くに新しい曜日タスクとして追加する。

---

## `tools_instagram.py` の主要関数

```python
fetch_recent_media(ig_user_id, since_date) -> list[dict]
    # media_id, permalink, timestamp, media_product_type(REELS/IMAGE/CAROUSEL) を取得

fetch_media_insights(media_id, media_product_type) -> dict
    # reach, likes, saved, comments, follows, profile_activity, views,
    # ig_reels_avg_watch_time 等をメトリクスとして取得
    # breakdown=follow_type でフォロワー/フォロワー外のリーチ内訳も取得

sync_to_sheet(sheet_id, tab_gid, rows) -> None
    # gspread で該当行を検索し、自動取得列だけ上書き。手動入力列（空でも）には触れない
```

Metaが提供するメトリクス名・breakdown仕様は変更されることがあるため、実装時に最新のGraph APIドキュメントで各フィールド名を確認する。取得できないと判明した項目はすべて「手動列」として扱う。

---

## カラムの自動／手動マッピング

| 分類 | 自動取得できる列 | 手動のままにする列 |
|---|---|---|
| 基本 | 全体リーチ、フォロワー％／フォロワー／フォロワー外、いいね、保存、コメント、フォロー数 | サムネ（キャプション見出しなので人が書く） |
| 動画系 | 再生数、平均再生時間（Reelsのみ） | 動画時間、スキップ率、視聴維持率 |
| 導線系 | プロアク、リンクタップ | インプ内訳（④プロフィール／⑤ホーム／⑥ハッシュタグ／⑦発見／⑧その他） |
| 比率 | いいね率・保存率・プロアク率・リンクタップ率（取得した数値から自動計算） | — |
| 時系列 | — | 「翌日」「1週間後」ブロック全体 |

---

## 行のマッチングルール

- **タブ1**：`投稿URL` 列とAPIの `permalink` を完全一致で照合。一致する行があれば自動列だけ上書き、なければ最下部に新規行を追加（日付・URLも自動入力）。
- **タブ2**：URL列がないため `日付` 列で照合。同日に複数投稿がある場合は1件目のみ自動入力し、2件目以降はログに「手動で確認してください」と出力してスキップする。
- IG投稿のタイムスタンプはJST日付（例: `7/20`）に変換してから照合する。

---

## エラーハンドリング

既存の運用（`logs/YYYY-MM-DD.txt`への記録、ネットワークエラー処理）に合わせる。

| 状況 | 挙動 |
|---|---|
| アクセストークン期限切れ・無効 | 「トークン期限切れです。.envのMETA_ACCESS_TOKENを再発行してください」と明示してその回の同期を中断 |
| Graph APIレート制限 | 数回リトライ（バックオフ）→ 失敗ならその投稿だけスキップしログに記録、他の投稿は処理継続 |
| 個別投稿のInsights取得失敗 | その投稿だけスキップし処理継続（全体を止めない） |
| Google Sheets書き込みエラー（権限不足・一時的なAPIエラー） | リトライ→失敗時は明確なエラーメッセージを出して終了 |
| 必須環境変数未設定 | 起動時点で分かりやすいメッセージを出して即終了 |

トークン更新は自動リフレッシュを行わず、60日ごとにオーナーが手動で再発行する運用とする。

---

## テスト方針

`tests/test_instagram.py` にネットワーク非依存のテストを実装する。

- カラム計算ロジック（いいね率・保存率・プロアク率・リンクタップ率の計算）を純粋関数として単体テスト
- 行マッチングロジック（URL一致／日付一致／同日複数投稿時は1件目のみ）をダミーのシート行データで検証
- Graph APIレスポンスをモックし、`fetch_media_insights` が想定通りにパースすることを確認
- トークン期限切れ・レート制限のエラーハンドリングを、モックで例外を発生させて確認

`python3 -m pytest tests/test_instagram.py -v` で実行する。

---

## スコープ外（今回やらないこと）

- Notionへの保存、marketerエージェントの反応分析タスクへのデータ連携
- インプレッション流入元内訳、翌日/1週間後スナップショットの自動取得
- アクセストークンの自動リフレッシュ
- ダイエットアカウント関連の3タブへの対応
