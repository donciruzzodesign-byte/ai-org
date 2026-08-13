# 週次自動実行におけるHiggsfield課金APIガード 設計書

## 背景・目的

Higgsfield AI動画生成連携（`generate_scene_video`）の実装後、オーナーから「有料APIを実行する際は一度確認を取るようにしましょう」という方針が示された。インタラクティブなセッション（Claude Codeでの手動操作）では、実行前にオーナーへ確認する運用で対応できる。しかし週次自動実行（`runner.py`の火曜11:00ワイン／12:00コーヒーの動画素材生成タスク）は無人実行が前提であり、その場で確認を待つ仕組みは作れない。

本設計では、無人実行中に`generate_scene_video`（課金API）が誰の確認もなく自動的に呼ばれてしまう事態を防ぐガードを追加する。

## スコープ

- 対象は`runner.py`の週次自動実行パスのみ（`tuesday_video_task`／`coffee_tuesday_video_task`）。Claude Codeでのインタラクティブな`@video`エージェント利用は対象外（人が既にその場で判断できるため、既存メモリ「有料APIは実行前に確認」で担保）。
- **デフォルトは無効**：通常の週次自動実行では`generate_scene_video`は一切使わせず、従来通り`fetch_broll`のみを使う。
- **ワンショット許可フラグ**：オーナーが事前に明示的な操作（スクリプト実行）でフラグを立てた場合のみ、その回の自動実行1回に限って`generate_scene_video`を解禁する。フラグは読み取り時に即座に消費（削除）され、次週は自動的にまた無効に戻る。「ONにしたまま忘れて課金され続ける」事故を構造的に防ぐ。
- フラグはワイン・コーヒーで独立に消費する（同じ日に両方使いたい場合はフラグを2回立てる必要がある）。安全側に倒した設計。
- 実現方式は「ツール自体をLLMに見せない」（呼び出し可能なツールリストから`generate_scene_video`を除外する）。エージェントの自己判断に依存せず、構造的に呼べなくする。

## コンポーネント設計

### フラグファイル

リポジトリ直下 `.higgsfield_auto_once`。中身は使わず存在有無のみで判定する。`.gitignore`に追加する。

### `tools_video.py`への追加

- `HIGGSFIELD_ONESHOT_FLAG_PATH` — フラグファイルの絶対パス定数（`os.path.dirname(__file__)`基準）
- `consume_paid_video_flag() -> bool`
  - フラグファイルが存在すれば削除して`True`を返す
  - 存在しなければ`False`を返す
  - ファイル操作で例外が発生した場合も`False`を返す（フェイルセーフ。疑わしいときは必ず「使わせない」方向に倒す）
- `VIDEO_TOOL_DEFINITIONS_FREE` — `VIDEO_TOOL_DEFINITIONS`から`name == "generate_scene_video"`のエントリだけを除いたリスト。モジュール読み込み時に一度だけ生成する。

### `scripts/enable_higgsfield_once.py`（新規）

オーナーが手動実行するとフラグファイルを作成し、「次回の自動実行1回だけHiggsfieldを許可します」という趣旨のメッセージを表示する。既存の`scripts/sync_instagram_insights.py`等と同じ配置・スタイルに合わせる。

### `runner.py`の変更

- `run_video_agent(script_text, topic, output_dir, allow_paid_video: bool = False)` に引数を追加。`allow_paid_video`が`True`なら`VIDEO_TOOL_DEFINITIONS`、`False`なら`VIDEO_TOOL_DEFINITIONS_FREE`をClaude API呼び出しの`tools`引数に渡す。
- `tuesday_video_task()`は`consume_paid_video_flag()`の戻り値を`run_video_agent(..., allow_paid_video=<戻り値>)`に渡す。
- `coffee_tuesday_video_task()`も同様に、独立して`consume_paid_video_flag()`を呼び、その戻り値を渡す（ワイン用フラグ消費とは別に、もう一度フラグの有無を確認する＝2つのタスクは独立）。

### CLAUDE.mdへの追記

`.env`の環境変数説明の近くか、動画パイプラインの節に、フラグの使い方（`python3 scripts/enable_higgsfield_once.py`を事前に実行すると次回1回だけHiggsfieldが有効になる）を追記する。

## エラーハンドリング方針

`consume_paid_video_flag()`はいかなる例外もフラグ「なし」（`False`）として扱う。呼び出し元（`tuesday_video_task`/`coffee_tuesday_video_task`）は既存の`try/except`でタスク全体を保護しているため、追加のエラーハンドリングは不要。

## テスト方針

**`tests/test_tools_video.py`に追加:**
- フラグファイルが存在する状態で呼ぶと`True`を返し、ファイルが削除されること
- フラグファイルが存在しない状態で呼ぶと`False`を返すこと
- 同じフラグに対して2回連続で呼ぶと、1回目`True`・2回目`False`になること（消費済み）
- `VIDEO_TOOL_DEFINITIONS_FREE`に`generate_scene_video`という名前のツール定義が含まれないこと

**`tests/test_runner.py`に追加:**
- `run_video_agent(..., allow_paid_video=False)`（デフォルト）で呼び出したとき、Claude API呼び出しに渡される`tools`引数に`generate_scene_video`が含まれないこと
- `run_video_agent(..., allow_paid_video=True)`で呼び出したとき、`tools`引数に`generate_scene_video`が含まれること
- `tuesday_video_task`が`consume_paid_video_flag()`の戻り値を`run_video_agent`の`allow_paid_video`引数にそのまま渡していること（`coffee_tuesday_video_task`も同様）
