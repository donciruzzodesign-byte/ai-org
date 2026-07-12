# 設計：動画パイプラインへの画像入力機能

- **日付:** 2026-07-12
- **対象:** `tools_video.py` / `runner.py`（`run_video_agent`）/ `agents/video.txt`
- **ステータス:** 承認済み（実装計画待ち）

## 目的

現在の動画パイプラインは、シーン画像を gpt-image-1 で「生成する」だけで、オーナーの手持ち画像を「読み込む」仕組みがない。以下3つの画像入力機能を追加する。

- **① 自分の写真を素材に使う** — 撮影した写真を AI 生成の代わりに動画素材として使う
- **② 参考画像で AI 生成を寄せる** — 参考画像に基づいてシーン画像を生成する
- **③ 画像を Claude に見せて解析させる** — ラベル読み取り・シーン割当・キャプション生成・品質チェック

3機能とも「動画エージェント（`run_video_agent`）に新ツールを追加する」形で実現する。画像認識（③）が①②の接着剤になる。

## 設計方針

### ③ の実装方式：画像解析を「ツール」にする（A案）

`analyze_image` ツールを作り、内部で Claude vision を呼んで結果テキストを返す。動画エージェント本体はテキストのみを扱う現行の tool 駆動アーキテクチャを維持する。

- **不採用（B案）:** エージェント本体のメッセージに画像を毎ターン混ぜる方式。エージェントが全体を一望できる利点はあるが、毎ターン全画像分のトークンがかかり、`run_video_agent` のループ改修が大きい。
- **採用理由:** 現行アーキテクチャに素直に載る。ツール単位で独立・テスト容易。①②③すべてを「ツール追加」だけで実現できる。

## アーキテクチャ

すべて `tools_video.py` に実装し、`VIDEO_TOOL_DEFINITIONS`（Claude に渡すツール定義）と `execute_video_tool`（ディスパッチャ）に登録する。エージェントがツールを選んで呼ぶ既存の流れは変えない。

### 追加・変更するツール

| ツール | 種別 | 機能 |
|---|---|---|
| `analyze_image(image_path, question)` | 🆕 | 画像を base64 で Claude vision に送り、`question` に答える。ラベル読み取り／シーン適合判定／キャプション生成／品質チェックの4用途を `question` の出し分けでカバー |
| `scan_photos(output_dir)` | 🆕 | `my_photos/` を一括で解析し、各写真の内容・ラベル文字・おすすめ用途を JSON 配列で返す。エージェントが1回の呼び出しでシーン割当を判断できる |
| `assign_photo(photo, scene_number, output_dir)` | 🆕 | `my_photos/<photo>` を `images/scene_NN.png` に 1536×1024 で正規化（Pillow センタークロップ）コピー。下流の timeline / AE 生成は無改修で流れる |
| `generate_scene_image(scene_description, scene_number, output_dir, reference_image=None)` | ✏️ | 既存に `reference_image` を追加。指定時は gpt-image-1 の画像編集 API（`/images/edits`）に切替え、参考画像を渡す。実物商品の登場・スタイル統一・不足補完を同じ仕組みで実現 |

### 各ツールの詳細

**`analyze_image(image_path, question)`**
- 入力: 解析対象画像の絶対 or `output_dir` 相対パス、質問文。
- 処理: 画像を base64 化し、`ANTHROPIC_API_KEY` で anthropic クライアントを内部生成、vision メッセージ（image block + question）を送信。
- 出力: 解析結果テキスト（失敗時はエラーメッセージ文字列。既存ツールと同じ規約）。
- 依存: `ANTHROPIC_API_KEY`（既に必須）、anthropic SDK（導入済み 0.97）。

**`scan_photos(output_dir)`**
- 入力: `output_dir`。内部で `output_dir/my_photos/` を対象にする。
- 処理: 対象フォルダの画像ファイルを列挙し、各画像に対して `analyze_image` 相当の vision 解析を実行（内容・ラベル文字・推奨用途を構造化するプロンプト）。
- 出力: JSON 文字列 `[{"file": "barolo.jpg", "description": "...", "label_text": "...", "suggested_use": "..."}, ...]`。フォルダが無い／空なら空配列。

**`assign_photo(photo, scene_number, output_dir)`**
- 入力: 写真ファイル名（`my_photos/` 内）、シーン番号、`output_dir`。
- 処理: Pillow で開き、1536×1024 にアスペクト維持のセンタークロップ＋リサイズし、`output_dir/images/scene_{NN:02d}.png` として保存。
- 出力: 保存結果メッセージ文字列。
- 備考: `generate_ae_script` は既に `scene.get("image")` で `images/scene_NN.png` を読むため、これで①の下流は無改修で動く。

**`generate_scene_image(..., reference_image=None)`**
- `reference_image` 未指定時: 現行どおり `/images/generations`。
- `reference_image` 指定時: `/images/edits` に切替え、参考画像（`output_dir` 相対 or `my_photos/` 相対）を `image` として渡す。プロンプトは既存の `SCENE_IMAGE_STYLE + scene_description` を踏襲し、用途（実物登場／スタイル統一／不足補完）は文言で出し分ける。
- 既存の「既存ファイルはスキップ」挙動・保存先（`images/scene_NN.png`）は維持。

## データフロー（週次ワークフロー）

火曜の `run_video_agent` の流れ。トリガー・実行タイミングは現行のまま。

1. （任意）オーナーが `output/<日付>-{wine|coffee}/my_photos/` に写真を置く。空でも可。
2. エージェントが `scan_photos` で写真の内容・ラベルを一括把握。
3. 台本と照合し、シーンごとに割当を判断 → 一致する写真は `assign_photo` で `images/scene_NN.png` に配置。
4. 写真がないシーンだけ `generate_scene_image`。統一したい場合は手持ち写真を `reference_image` に渡す。
5. 配置・生成画像を `analyze_image` で品質チェック。問題があれば再生成。
6. `analyze_image` の内容をもとに `timeline.json` の caption を自動生成。
7. `save_timeline` → `generate_ae_script`（現行と同じ）。

## エラーハンドリング・後方互換

- **後方互換:** `my_photos/` が空 or 存在しない場合、全シーン AI 生成となり**現行と完全に同一の挙動**。既存の週次運用を壊さない。
- 各ツールは失敗時に例外を投げず、エラーメッセージ文字列を返す（既存ツールの規約に統一）。API キー未設定時はスキップメッセージを返す。
- `assign_photo` は対象ファイルが無い場合エラーメッセージを返す。

## エージェントプロンプト更新

`agents/video.txt` に手順を追記：
「まず `scan_photos` で `my_photos` を確認する。実写を優先し `assign_photo` で配置。写真がないシーンだけ AI 生成し、統一したい場合は `reference_image` を使う。配置・生成した画像は `analyze_image` で品質チェックする。」

## テスト

既存 `tests/` のパターン（API 呼び出しをモック）に沿う。

- `analyze_image`: anthropic vision 呼び出しをモックし、質問→テキスト応答が返ることを確認。
- `scan_photos`: `my_photos/` にダミー画像を置き、vision をモックして JSON 配列が返ることを確認。空フォルダで空配列を確認。
- `assign_photo`: Pillow で作った一時画像を渡し、`images/scene_NN.png` が 1536×1024 で生成されることを確認。
- `generate_scene_image(reference_image=...)`: openai `/images/edits` 呼び出しをモックし、reference 有無でエンドポイントが切り替わることを確認。
- 後方互換: `my_photos/` 無しで従来フローが変わらないことを確認。

## スコープ外（YAGNI）

- 動画（B-roll）への画像入力対応。
- 複数参考画像の同時指定。
- 画像編集 UI・GUI。
