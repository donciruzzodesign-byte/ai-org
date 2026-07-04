# note連携（案A：note原稿の自動生成）設計書

日付: 2026-07-04
ステータス: ユーザー承認済み（案A採用）

## 目的

週次パイプラインで生成される台本・テーマ情報をもとに、note.com 向けの記事原稿を自動生成する。
note には公式投稿 API がないため、本設計の範囲は**原稿ファイルの生成まで**とし、投稿は水曜レビュー時にオーナーがコピペで行う。ブラウザ自動化による下書き作成（案B）は本設計の範囲外（将来の拡張）。

## 背景

- 金曜の marketer タスクは既に「note誘導リンク付き」の Instagram キャプションを生成しており、note 記事の存在が運用上前提になっている。
- 火曜 09:00/10:00 に creator が台本を作成し、11:00/12:00 に video エージェントが `output/YYYY-MM-DD-{wine|coffee}/` に素材（`images/scene_01.png` 含む）を出力する。

## 生成物

`output/YYYY-MM-DD-{wine|coffee}/note_article.md` （ワイン・コーヒー各1本、週2本）

ファイル構成（1ファイル内）:

1. **投稿メモ**（コピペ時の指示）: 見出し画像に `images/scene_01.png` を使う旨、推奨公開日（土曜）
2. **タイトル案**: 3案（note の検索・おすすめ面を意識したもの）
3. **本文**: 動画を見なくても読み物として成立する 2,000〜3,000 字程度の記事。見出し（`##`）区切り、冒頭リード → 本編 → まとめ → YouTube 動画への誘導 CTA
4. **ハッシュタグ**: note 用 5〜8 個

## アーキテクチャ

既存の runner タスクパターンを踏襲する。新しいエージェントは作らず、文章作成担当の **creator** に note 記事化プロンプトを渡す。

### 変更ファイル

| ファイル | 変更内容 |
|---|---|
| `runner.py` | `tuesday_note_task()` / `coffee_tuesday_note_task()` を追加し、火曜 13:00 / 13:30 にスケジュール登録 |
| `runner.py` | ヘルパー `_write_note_article(text: str, output_dir: str) -> str` を追加（`note_article.md` の書き出し。ディレクトリがなければ作成） |
| `tests/test_runner_note.py` | `_write_note_article` のユニットテスト |

### 処理フロー（wine 側。coffee 側は対称）

```
13:00 tuesday_note_task
  ├─ _read_todays_log() で当日ログ（テーマ＋台本）を取得
  ├─ run_agent("creator", note記事化プロンプト, "火曜：note記事作成（ワイン）")
  │    └─ 既存の仕組みでログ保存・Notion 保存も行われる
  └─ 戻り値の記事テキストを _write_note_article() で
     output/YYYY-MM-DD-wine/note_article.md に保存
```

### プロンプト方針（creator への指示）

- 当日ログ（テーマ・台本）を渡し、「YouTube 動画の台本を、動画を見なくても単体で読める note 記事に再構成する」ことを指示
- 話し言葉の台本を書き言葉に整え、note 読者（30〜50代女性、ソムリエ/コーヒー好き）向けのトーンにする
- 出力フォーマット（投稿メモ／タイトル案／本文／ハッシュタグ）を明示
- ログに台本がない場合はテーマ情報のみから記事を作成し、それもなければ既定テーマで作成（既存タスクと同じフォールバック方針）

## エラーハンドリング

- 各タスクは既存タスクと同様に try/except で包み、失敗時は `❌` ログを出して他タスクに影響させない
- `_write_note_article` は出力ディレクトリを `os.makedirs(exist_ok=True)` で作成（video タスクが失敗していてもファイルは書ける）

## テスト

- `_write_note_article`: 指定ディレクトリに `note_article.md` が正しい内容で書かれること、ディレクトリ未存在時に作成されること（tmp_path 使用）
- タスク関数本体は既存タスク同様、API 呼び出しを含むためユニットテスト対象外（手動テストは `python3 -c "from runner import tuesday_note_task; tuesday_note_task()"` で実施）

## スコープ外

- note への自動投稿・下書き作成（案B: Claude in Chrome によるブラウザ自動化。案A の運用が安定したら別途設計）
- 見出し画像の自動加工（scene_01.png をそのまま流用）
- 公開後の反応分析への note 指標追加
