# Higgsfield AI動画生成連携 設計書

## 背景・目的

現在の動画素材パイプライン（`tools_video.py`）は、静止画をgpt-image-1（OpenAI）で、B-roll動画をPexelsのストック素材で調達している。Higgsfield APIを使い、シーン画像に動きを加えたオリジナルのAI動画クリップを生成する機能を新規追加する。既存のgpt-image-1・Pexels連携はそのまま残し、置き換えは行わない。

## スコープ

- **用途**: AI動画生成の新規追加（既存の静止画生成・B-roll取得は変更しない）
- **生成方式**: image-to-video。`generate_scene_image`（またはmy_photos経由の`assign_photo`）で既に作られたシーン画像を元に、動きを加えた動画を生成する。text-to-videoは対象外。
- **AEスクリプト連携**: 生成した動画は`auto_edit.jsx`の自動配置対象に含める。
- **既存B-rollとの関係**: 1シーンにつき`fetch_broll`（Pexelsストック）と`generate_scene_video`（Higgsfield AI生成）のどちらか一方をエージェントが選ぶ。両方生成することは想定しない。

## 認証

Higgsfield APIの認証は単一キーではなく、Key ID + Key Secretのペア（`Authorization: Key <ID>:<SECRET>`ヘッダー）。公式Python SDK（`higgsfield-client`）は環境変数`HF_API_KEY`（Key ID）・`HF_API_SECRET`（Key Secret）を自動で読み込む。

`.env`に以下を追加済み（値はオーナーが[cloud.higgsfield.ai](https://cloud.higgsfield.ai)のAPI Credentials画面から取得）:

```
HF_API_KEY=...
HF_API_SECRET=...
```

## アーキテクチャ

`tools_video.py`に`generate_scene_video()`を新規追加する。既存の`generate_scene_image`（静止画）・`fetch_broll`（ストック動画）と並列の第3の素材ソースという位置づけ。

認証・アップロード・非同期ポーリングの実装は、生のHTTPを書く既存パターン（OpenAI/Pexels/ElevenLabsは`requests`直書き）から外れ、Higgsfield公式Python SDK（`higgsfield-client`）を使う。理由: Higgsfieldの認証・画像アップロード・非同期ジョブのライフサイクルはSDKが安全にラップしており、生REST実装よりも壊れにくいため。

## API仕様（確認済み）

- ベースURL: `https://platform.higgsfield.ai`
- image-to-videoモデル: `higgsfield-ai/dop/standard`（他に`kling-video/v2.1/pro/image-to-video`等も選択可）
- リクエスト: `{"image_url": "...", "prompt": "モーション説明"}`（画像はURLで渡す必要があり、ローカル画像はSDKの`upload_file()`で事前アップロードしてURL化する）
- レスポンス: `request_id` / `status_url` / `cancel_url` を含む非同期レスポンス
- ステータス: `queued` → `in_progress` → `completed`（`video.url`に結果） / `failed` / `nsfw` / `canceled`
- 出力URLの保持期間は最低7日間

## コンポーネント設計

### `generate_scene_video(scene_number: int, output_dir: str, motion_description: str = "") -> str`

**入出力:**
- 入力: `images/scene_{NN}.png`（事前に存在している必要がある）
- 出力: `ai_video/scene_{NN}.mp4`

**処理フロー:**
1. `HF_API_KEY` / `HF_API_SECRET` 未設定 → `"HF_API_KEY / HF_API_SECRET が未設定のためスキップ"` を返す
2. `ai_video/scene_{NN}.mp4` が既に存在 → スキップメッセージを返す（既存関数と同じ冪等パターン）
3. `images/scene_{NN}.png` が存在しない → エラーメッセージを返す（"先にgenerate_scene_imageかassign_photoでシーン画像を作成してください"）
4. `higgsfield_client.upload_file(image_path)` で画像をアップロードしURLを取得
5. `higgsfield_client.submit("higgsfield-ai/dop/standard", arguments={"image_url": url, "prompt": motion_description})` でジョブ送信
6. `poll_request_status()` をタイムアウト付き（300秒）でポーリング
   - `completed` → `video.url` を `requests.get` でダウンロードして保存、成功メッセージを返す
   - `failed` / `nsfw` / `canceled` → ステータスを含むエラーメッセージを返す
   - タイムアウト → エラーメッセージを返す（不完全なファイルは残さない）
7. 例外は全て`try/except`で捕捉し、文字列で返す（既存関数と同じ方針。呼び出し元に例外を伝播させない）

### タイムライン統合

- `scenes[]`に`ai_video`フィールドを新設（`broll`と同じ相対パス形式の文字列）
- `generate_ae_script`内の `broll_rel = scene.get("broll", "")` を `scene.get("broll") or scene.get("ai_video", "")` に変更。既存のオーバーレイ配置ロジック（opacity 70%オーバーレイ）をそのまま再利用する。`broll`と`ai_video`は同じスロットの二択として扱う。

### ツール定義・ディスパッチ

- `VIDEO_TOOL_DEFINITIONS`に`generate_scene_video`のツール定義を追加（`scene_number` / `output_dir` / `motion_description`（任意）を受け取る）
- `execute_video_tool`に`generate_scene_video`のディスパッチ分岐を追加

### エージェントプロンプト更新

`.claude/agents/video.md`・`agents/video.txt`の両方に以下を追記:
- 利用可能ツール一覧に`generate_scene_video`を追加
- 各シーンについて、`fetch_broll`（汎用ストック映像）と`generate_scene_video`（AI生成・ブランド統一感重視、商品ショットなど独自性を出したいシーン向け）のどちらか一方を選ぶ判断基準
- `generate_scene_video`は対応する`generate_scene_image`（または`assign_photo`）の後に呼ぶ必要がある（元画像が前提のため）

### 依存関係

`requirements.txt`に`higgsfield-client`を追加

## エラーハンドリング方針

既存関数と同じ「例外を投げず文字列メッセージで返す」方式に統一する。`try/except`で全体を囲み、失敗時のメッセージも呼び出し元（videoエージェント）がそのまま読める形にする。

## テスト方針

`tests/test_tools_video.py`に既存の`monkeypatch` + `unittest.mock.patch`パターンで追加する。実APIは呼ばない。`tools_video.higgsfield_client`をモックする。

- キー未設定でスキップ
- 元画像（`images/scene_NN.png`）が無ければエラー
- 出力ファイル（`ai_video/scene_NN.mp4`）が既にあればスキップ
- upload → submit → poll(`completed`) → ダウンロード保存の正常系
- pollの結果が`failed`/`nsfw`の場合にエラーメッセージを返す
- `execute_video_tool`のディスパッチ
- `generate_ae_script`が`ai_video`フィールドを`broll`と同じ扱いでJSXに出力すること
