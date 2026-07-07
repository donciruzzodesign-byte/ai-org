# CUBOCCI STUDIO AI組織

週次ワイン・コーヒーコンテンツを自動生成するマルチエージェントシステム。
YouTube（16:9、10分）+ Instagram Reels（9:16）向けに素材一式を自動生成し、After Effects で最終仕上げを行うパイプライン。

## プロジェクト構成

- `runner.py` — 週次スケジューラー本体（schedule ライブラリで各曜日タスクを実行）
- `app.py` — 手動でCEOに指示するインタラクティブモード
- `tools.py` — エージェントが使うツール（web_search / search_papers / fetch_page / save_to_notion）
- `tools_video.py` — 動画素材生成ツール（generate_scene_image / fetch_broll / save_timeline / generate_ae_script）
- `agents/` — エージェントのシステムプロンプト（.txt）
- `.claude/agents/` — Claude Code 用エージェント定義（.md）
- `logs/` — 日次ログファイル（YYYY-MM-DD.txt）
- `output/YYYY-MM-DD-{wine|coffee}/` — 動画素材出力先
- `.env` — API キー（下記参照）

## 環境変数（.env）

```
ANTHROPIC_API_KEY=...       # 必須
NOTION_API_KEY=...          # 任意
NOTION_DATABASE_ID=...      # 任意（設定時は最上位の「コンテンツ生成物」DBにページ作成）
NOTION_PAGE_ID=...          # 任意（NOTION_DATABASE_ID 未設定時のフォールバック：子ページ作成）
OPENAI_API_KEY=...          # 画像生成（gpt-image-1）に必須
PEXELS_API_KEY=...          # B-roll動画取得に必須
ELEVENLABS_API_KEY=...      # ナレーション（現在は無効化中・有料プラン必要）
ELEVENLABS_VOICE_ID=...     # ElevenLabs ボイスID
```

## エージェント構成

| エージェント | 役割 |
|---|---|
| ceo | 全体指揮・タスク振り分け・最終レポート |
| sommelier | イタリアワイン専門知識・テーマ提案・監修 |
| creator | 動画台本・編集指示書作成 |
| marketer | Instagram投稿文・アフィリエイト・反応分析 |
| barista | イタリアコーヒー専門知識・テーマ提案・地域紹介 |
| video | 動画素材生成（画像・B-roll・タイムライン・AEスクリプト） |

## 週次スケジュール

| 曜日 | 時刻 | タスク | エージェント |
|------|------|--------|-------------|
| 月 | 09:00 | 今週テーマ決定 | sommelier |
| 月 | 09:30 | 州別おすすめワイン紹介 | sommelier |
| 月 | 10:00 | コーヒーテーマ決定 | barista |
| 月 | 10:30 | 地域別コーヒー紹介 | barista |
| 火 | 09:00 | 動画台本作成 | creator |
| 火 | 10:00 | コーヒー動画台本作成 | creator |
| 火 | 11:00 | ワイン動画素材生成（画像・B-roll・AEスクリプト） | video |
| 火 | 12:00 | コーヒー動画素材生成 | video |
| 火 | 13:00 | ワインnote記事原稿生成 | creator |
| 火 | 13:30 | コーヒーnote記事原稿生成 | creator |
| 水 | 09:00 | レビュー通知（手動確認） | — |
| 木 | — | AE で auto_edit.jsx 実行 → 仕上げ（オーナー手動） | — |
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

# 動画パイプラインの手動テスト実行
python3 test_video_full.py

# ログ確認
cat logs/$(date +%Y-%m-%d).txt

# テスト実行
python3 -m pytest tests/ -v
```

## 動画パイプライン（tools_video.py）

火曜日に自動実行。出力先: `output/YYYY-MM-DD-{wine|coffee}/`

| ファイル | 内容 |
|---|---|
| `images/scene_NN.png` | gpt-image-1 生成シーン画像（1536×1024） |
| `broll/broll_NN.mp4` | Pexels HD動画素材 |
| `timeline.json` | シーン構成データ |
| `edit_guide.md` | After Effects 編集手順 |
| `auto_edit.jsx` | AE自動配置スクリプト（File→Scripts→Run で実行） |
| `note_article.md` | note記事原稿（投稿メモ・タイトル案・本文・ハッシュタグ。水曜レビュー時に手動でnoteへコピペ） |

## Claude Code でのエージェント呼び出し方

.claude/agents/ に各エージェント定義があるため、Claude Code から直接呼び出し可能：
- `@sommelier` — ワイン知識・テーマ相談
- `@creator` — 台本・動画構成
- `@marketer` — SNS投稿文・マーケティング
- `@ceo` — 全体戦略・タスク調整
- `@barista` — コーヒー知識・テーマ相談・地域別コーヒー紹介
- `@video` — 動画素材生成（台本を渡すと素材一式＋AEスクリプトを出力）