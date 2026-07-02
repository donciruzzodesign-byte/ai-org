# winedeck Instagram カルーセル生成ツール — 統合設計

## 背景

`~/Desktop/files/` に置かれていた自己完結型のSVGカルーセル生成ツール（`winedeck.py` / `render.py` /
`deck.example.json` / `requirements.txt` / `README.md`）を、`ai-org` リポジトリに取り込む。

ワインタイプ別の配色（背景グラデ・ゴールド枠・明朝見出し／ゴシック本文）で、Illustrator編集可能な
ライブテキストSVG（1080×1350 / 4:5、Instagramカルーセル向け）を生成するエンジン。任意でcairosvgを
使いPNGプレビューも書き出せる。ブランド表記（CUBOCCI STUDIO等）は入れない方針。

既存の `tools_express.py` / `.claude/agents/express.md` は週次のYouTubeサムネイル・Reelsカバー・
タイトルカード（各1枚もの）を生成するのに対し、winedeckは教育コンテンツ用の**複数枚カルーセル**
（表紙＋規定＋年表＋まとめ、等）を生成するもので、用途が異なる。両者は独立して共存する。

## スコープ

- **統合方法**: スタンドアロンツールとして取り込むのみ。`runner.py` への新規スケジュールステップ追加、
  新規/既存エージェントの拡張は行わない。手動で `python winedeck/render.py <deck.json>` を実行する運用。
- **対象**: ワインのみ。コーヒー向け配色（PAL拡張）は対象外（将来必要になれば別タスクとする）。
- **エンジンのロジック変更なし**: `winedeck.py` の描画プリミティブ・スライドビルダー・パレットは
  元ファイルのまま移設する。

## ファイル配置

リポジトリルートに新規フォルダ `winedeck/` を作成し、以下を配置する（既存の `tools_video.py` などの
フラットな `tools_*.py` 群とは別に、自己完結パッケージとして隔離する）:

```
winedeck/
  winedeck.py         # エンジン本体（無変更）
  render.py            # CLIランナー（出力先デフォルトのみ変更、後述）
  deck.example.json    # サンプル仕様（バローロ、無変更）
  README.md            # 元READMEを、新しい配置・出力先デフォルトに合わせて更新
```

`requirements.txt`（リポジトリ直下）は変更不要 — `cairosvg>=2.7.0` は既に登録済み。

## 出力先のデフォルト変更

現状の `render.py` は `--outdir` 未指定時 `./out` に書き出す。これを以下のように変更する:

- 新規オプション `--date YYYY-MM-DD`（デフォルト: 実行日）を追加。
- `--outdir` 未指定時のデフォルトを
  `~/Desktop/CUBOCCI_STUDIO/weekly/{date}-wine/carousel/` に変更する
  （中に `svg/` `png/` サブフォルダ、既存の `wd.export()` / `--svg-only` 分岐の挙動はそのまま）。
  これは `.claude/agents/express.md` が使っている既存の週次出力規約
  （`~/Desktop/CUBOCCI_STUDIO/weekly/{date}-{theme}/`）に合わせたもの。
- `--outdir` を明示的に渡した場合はそちらを優先し、`--date` は無視する。

使用例:
```bash
python winedeck/render.py winedeck/deck.example.json --date 2026-07-06
# → ~/Desktop/CUBOCCI_STUDIO/weekly/2026-07-06-wine/carousel/{svg,png}/barolo_NN.*

python winedeck/render.py winedeck/deck.example.json --outdir ./out --svg-only
# → 従来通り、明示指定を優先（依存なしでSVGのみ）
```

## 変更しないもの

- `winedeck.py` の配色・描画ロジック・スライド種別（cover/rows/bullets/timeline/summary）。
- `deck.example.json` のJSON仕様・フィールド。
- `runner.py` / 各エージェント定義（`.claude/agents/*.md`）— 一切変更なし。
- コーヒー向け配色 — 対象外。

## テスト方針

- `winedeck/render.py winedeck/deck.example.json --date <任意日>` を実行し、
  `~/Desktop/CUBOCCI_STUDIO/weekly/<日付>-wine/carousel/svg/` に4枚のSVGが、
  `png/` に4枚のPNGが生成されることを確認する（cairosvgが使える環境前提）。
- `--svg-only` でcairosvg無しでもSVGのみ生成できることを確認する。
- `--outdir` 明示指定時に、そちらが優先されることを確認する。
