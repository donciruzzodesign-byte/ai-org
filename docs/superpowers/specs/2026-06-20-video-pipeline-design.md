# 動画素材自動生成パイプライン 設計仕様

**日付:** 2026-06-20  
**対象プロジェクト:** CUBOCCI STUDIO AI組織 (`~/ai-org`)  
**ステータス:** 承認済み

---

## 概要

`creator` エージェントが生成した台本・スライド構成を入力として、After Effects での最終編集に必要な動画素材一式（ナレーション音声・シーン画像・B-roll動画・タイムライン定義）を自動生成するパイプライン。

**対象フォーマット：** YouTube（16:9 / 10分前後）＋ Instagram Reels ハイライト素材（9:16用）  
**最終仕上げ：** ユーザーが After Effects で実施  
**ナレーション：** AI音声（ElevenLabs）を標準とし、自録音用の無音ガイドも出力

---

## アーキテクチャ

```
runner.py（週次スケジューラー）
    ↓ 火曜 09:00
creator エージェント → 台本 + スライド構成を生成
    ↓ 火曜 11:00（新規追加）
video エージェント（新規）
    ├── ElevenLabs API  → narration.wav（ナレーション音声）
    ├── DALL-E 3 API    → scene_01.png〜N.png（各シーン画像）
    ├── Pexels API      → broll_01.mp4〜M.mp4（B-roll 動画素材）
    └── マニフェスト生成 → timeline.json + edit_guide.md
         ↓
output/YYYY-MM-DD-{topic}/
    ├── audio/
    │   └── narration.wav         ← AI音声（自録音時はAEでミュートして使用）
    ├── images/
    │   └── scene_01.png 〜 N.png  ← 16:9 / 1792×1024px
    ├── broll/
    │   └── broll_01.mp4 〜 M.mp4  ← HD以上・Pexelsライセンスフリー
    ├── reels/
    │   └── highlight_01.png 〜 3.png  ← Reels用ハイライト素材
    ├── timeline.json              ← AEタイムライン定義
    └── edit_guide.md              ← 編集指示書（人間向け）
```

---

## 新規ファイル

| ファイル | 役割 |
|---------|------|
| `tools_video.py` | ElevenLabs / DALL-E 3 / Pexels のAPI呼び出し実装 |
| `agents/video.txt` | video エージェントのシステムプロンプト |
| `.claude/agents/video.md` | Claude Code から `@video` で呼び出せるエージェント定義 |

## 既存ファイルへの変更

| ファイル | 変更内容 |
|---------|---------|
| `runner.py` | 火曜 11:00 に video エージェント実行を追加（ワイン・コーヒー各1回） |
| `.env` | `ELEVENLABS_API_KEY`, `ELEVENLABS_VOICE_ID`, `OPENAI_API_KEY`, `PEXELS_API_KEY` を追加 |

---

## コンポーネント詳細

### `tools_video.py`

**`generate_narration(script_text, voice_id)`**
- ElevenLabs TTS API で台本をナレーション音声に変換
- `voice_id` のデフォルトは `.env` の `ELEVENLABS_VOICE_ID`（未設定時はElevenLabsの日本語デフォルト音声）
- 出力：`narration.wav`（自録音時はAEでこのレイヤーをミュートして使用）
- 台本が長い場合はシーン単位で分割してAPIに送信後、結合

**`generate_scene_image(scene_description, scene_number)`**
- DALL-E 3 API でシーン画像を生成
- サイズ：1792×1024px（16:9）
- プロンプトに「high quality photography, Italian wine, warm natural light」などの固定スタイルプレフィックスを付与
- シーンごとに1枚、合計8〜12枚程度

**`fetch_broll(keyword, count)`**
- Pexels API でキーワード検索（例：`"Italian wine"`, `"vineyard"`, `"espresso"`）
- 条件：HD以上・16:9・商用利用可（Pexelsは全素材ライセンスフリー）
- 取得したクリップを `broll/` に保存

---

### `timeline.json` 構造

```json
{
  "title": "バローロ特集",
  "duration_sec": 600,
  "narration": "audio/narration.wav",
  "scenes": [
    {
      "id": 1,
      "in_sec": 0,
      "out_sec": 60,
      "type": "slide",
      "image": "images/scene_01.png",
      "broll": "broll/broll_01.mp4",
      "caption": "バローロはなぜ「ワインの王」と呼ばれるのか？",
      "notes": "テロップは画面下部、フォントはSerif系推奨"
    }
  ],
  "reels_highlights": [
    {
      "id": 1,
      "in_sec": 45,
      "out_sec": 75,
      "reason": "最も印象的なフレーズ"
    }
  ]
}
```

---

### `edit_guide.md` 出力例

```markdown
# 編集ガイド：バローロ特集（2026-06-20）

## After Effects への読み込み手順
1. audio/narration.wav → オーディオレイヤーに配置
2. images/ → timeline.json の in_sec/out_sec に従いスライドとして配置
3. broll/ → 各シーン後半にオーバーレイ（opacity 70%推奨）

## Reels 用ハイライト（Instagram）
- 0:45〜1:15（30秒）→ 縦型クロップ（9:16）推奨
```

---

## 週次スケジュール統合

| 曜日 | 時刻 | タスク | エージェント |
|------|------|--------|-------------|
| 火 | 09:00 | ワイン動画台本作成 | creator |
| 火 | **11:00（新規）** | **ワイン動画素材生成** | **video** |
| 火 | 10:00 | コーヒー動画台本作成 | creator |
| 火 | **12:00（新規）** | **コーヒー動画素材生成** | **video** |

台本生成からのバッファ1時間を確保。

---

## エラーハンドリング

- **API失敗時：** 失敗したツールのみスキップし、生成済み素材は保存。`edit_guide.md` に `⚠️ 再実行コマンド` を記載
- **冪等性：** 既存ファイルがある場合はスキップして再実行を安全に行える
- **ログ：** 既存 `logs/YYYY-MM-DD.txt` に動画パイプラインのログを追記

---

## 手動実行

```bash
# app.py 経由でCEOに指示
python3 app.py
# → 「今週のワイン動画素材を生成して」

# Claude Code から直接
# @video 「バローロ特集」の動画素材を生成してください
```

---

## 必要なAPIキー・料金感

| サービス | 用途 | 料金感 |
|---------|------|-------|
| ElevenLabs | ナレーション音声生成 | $5/月〜（月10分程度なら無料枠内も可） |
| OpenAI (DALL-E 3) | シーン画像生成 | 約$0.04/枚 × 10枚 = $0.4/動画 |
| Pexels | B-roll動画取得 | 無料（商用利用可） |
