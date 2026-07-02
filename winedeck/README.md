# winedeck — ワイン・カルーセル生成エンジン（Claude Code 連携用）

背景＝ワインタイプで色分け／ゴールド枠・明朝見出し・ゴシック本文は全タイプ共通。
出力は **Illustrator編集可能なライブテキストSVG（1080×1350 / 4:5）** ＋ 任意でPNGプレビュー。
ブランド表記（CUBOCCI STUDIO 等）は入れない方針。

## 構成
```
winedeck.py          エンジン本体（パレット＋描画プリミティブ＋スライドビルダー）
render.py            JSON仕様 → SVG/PNG のデータ駆動ランナー（CLI）
deck.example.json    デッキ仕様のサンプル（バローロ）
```
依存は `requirements.txt`（リポジトリ直下）の `cairosvg` のみ、かつPNGを焼く時だけ必要。

## セットアップ
```bash
# 1) Python 依存（リポジトリ直下から）
pip install -r requirements.txt

# 2) cairosvg 用の system Cairo（PNGを焼く場合のみ）
#   macOS:
brew install cairo pango gdk-pixbuf libffi
```

### フォント（重要）
SVGは次のフォールバック順で指定：
- 見出し（明朝）: `Noto Serif CJK JP` → `Yu Mincho` → `Hiragino Mincho ProN`
- 本文（ゴシック）: `Noto Sans CJK JP` → `Yu Gothic` → `Hiragino Sans`

- **Illustratorで開く**：macOSなら游書体・ヒラギノで自動解決。確定フォントに揃えたい場合はAI側で置換してからアウトライン化。
- **PNGを焼く（cairosvg）**：その環境に上記CJKフォントのいずれかが必要。無いと日本語が豆腐(□)になる。

## 使い方：CLI（データ駆動・推奨）

リポジトリ直下から実行する。

```bash
# デフォルト：~/Desktop/CUBOCCI_STUDIO/weekly/{実行日}-wine/carousel/ に svg+png
python winedeck/render.py winedeck/deck.example.json

# --date を指定して特定週のフォルダへ
python winedeck/render.py winedeck/deck.example.json --date 2026-07-06

# --outdir を明示すればそちらを優先（依存なしで動く --svg-only も可）
python winedeck/render.py winedeck/deck.example.json --outdir ./out --svg-only
```
出力：`<outdir>/svg/<name>_NN.svg`, `<outdir>/png/<name>_NN.png`

## 使い方：ライブラリとして
```python
import sys, os
sys.path.insert(0, "winedeck")
import winedeck as wd

slides = [
    wd.cover("red", badge="赤ワイン", q=["長期熟成する","偉大な赤は？"],
             answer="ネッビオーロ", subtitle="バローロの主役", grape="nebbiolo"),
    wd.rows_slide("red", "REGULATION", "バローロDOCG規定",
        [("最低熟成","38ヶ月（うち樽18ヶ月）"), ("品種","ネッビオーロ100%")],
        num=2, total=3, grape="nebbiolo"),
    wd.summary_slide("red", "まとめ", ["100%ネッビオーロ","最低38ヶ月熟成"],
        cta="保存して一本選びに。", num=3, total=3),
]
wd.export(slides, "./out", "barolo")     # PNGも要る場合
```

## ワインタイプ（背景キー）
`white / red / spark / rose / orange / sweet / study / grape`
- 明地（white, spark, rose, orange, sweet）＝文字は濃色
- 暗地（red, study, grape）＝文字はクリーム
- `study`＝学び・格付け・歴史（ネイビー）、`grape`＝品種・構造（チャコール黒）

## 品種アクセント
`grape="sangiovese"` のように指定すると、`GRAPE_ACCENT`（winedeck.py内）の色で
- 明地：見出し（=答え）の色を品種色に
- 暗地：可読性優先でモチーフ/差し色に品種色を使い、見出しはゴールド維持

登録済み：sangiovese / nebbiolo / cabernet / merlot / vermentino / arneis / moscato / picolit。
品種追加は `GRAPE_ACCENT` に1行足すだけ。コーヒー向け配色は未対応（対象外）。

## JSON仕様（deck.example.json 参照）
トップ：`name`, `wine_type`（既定）, `grape`（既定・任意）, `slides[]`
各スライド `kind`：
| kind | 主なフィールド |
|------|----------------|
| cover | badge, q[1〜2行], answer, subtitle, (grape, swipe) |
| rows | eyebrow, title, rows[[label,value]...], (closing) |
| bullets | eyebrow, title, items[[head,note]...], (closing) |
| timeline | eyebrow, title, events[[year,event]...], (closing) |
| summary | title, points[...], (cta, sub) |
- 各スライドで `wine_type` / `grape` を指定すればデッキ既定を上書き。
- `num`/`total` は並び順から自動採番（cover はフッター無し）。

## 制約と運用ルール（要遵守）
1. **日本語の自動折り返しは無い**。長文は呼び出し側で改行・分割する。`render.py` は
   1行の目安を超えると `[warn]` を出す（目安：見出し13・値26・補足30・答え12全角程度）。
2. **出力サイズは 1080×1350 固定**（`winedeck.py` 冒頭 `W,H,M`）。
3. 各SVGの内部ID（グラデ等）は呼び出しごとに一意化済み。1ファイル1枚で使う前提。
4. スタンドアロンツールとして統合済み（`runner.py` への自動組み込みは無し）。
   毎週の実行はオーナーが手動で `python winedeck/render.py <deck.json> --date <週の日付>` を叩く運用。
