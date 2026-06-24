# Creator × Adobe Express 連携 設計ドキュメント

**作成日:** 2026-06-24  
**対象プロジェクト:** CUBOCCI STUDIO

---

## 概要

creatorエージェントがイタリアワイン・コーヒー動画の台本から、Adobe Express連携でブランドデザイン素材を自動生成するパイプラインを構築する。

生成物はデスクトップの専用フォルダで一括管理し、テンプレートファイルはIllustratorでオーナーが編集可能なSVG形式とする。

---

## 生成アセット

| アセット | サイズ | フォーマット |
|---|---|---|
| YouTubeサムネイル | 1280×720px (16:9) | SVG（テンプレート）/ PNG（週次出力） |
| Instagram Reelsカバー | 1080×1920px (9:16) | SVG（テンプレート）/ PNG（週次出力） |
| 動画内タイトルカード | 1920×1080px (16:9) | SVG（テンプレート）/ PNG（週次出力） |

---

## ブランドデザイン

### カラーパレット

| 役割 | 色名 | HEX |
|---|---|---|
| プライマリ | ディープバーガンディ | `#6B1A2A` |
| アクセント | アンティークゴールド | `#C9A84C` |
| 背景 | アイボリー | `#F5F0E8` |
| テキスト | チャコール | `#2C2C2C` |

### フォント

| 用途 | フォント | スタイル |
|---|---|---|
| タイトル | Cormorant Garamond | Bold / Italic |
| サブタイトル | Montserrat | Light |

### レイアウト方針

- **YouTubeサムネ:** 左半分に食材・ワイン画像、右半分にバーガンディ背景＋ゴールドのタイトルテキスト
- **Reelsカバー:** 縦長、上部ゴールドラインで区切り、中央にタイトル＋サブタイトル
- **タイトルカード:** 横長、中央配置、シンプルなゴールドボーダー枠

---

## フォルダ構成

```
~/Desktop/CUBOCCI_STUDIO/
├── templates/
│   ├── youtube_thumbnail.svg   # Illustratorで編集可能
│   ├── reels_cover.svg
│   └── title_card.svg
└── weekly/
    └── YYYY-MM-DD-{wine|coffee}/
        ├── youtube_thumbnail.png
        ├── reels_cover.png
        └── title_card.png
```

- `templates/` は初回セットアップ時に一度だけ生成する
- オーナーはイラレでSVGを自由に編集・上書き可能
- `weekly/` は既存の `output/` と同じ命名規則で火曜に自動生成

---

## 処理フロー

### 初回セットアップ（1回のみ）

1. AIがブランドSVGテンプレート3種を生成
2. `~/Desktop/CUBOCCI_STUDIO/templates/` に保存（Illustratorで編集可能なソースファイル）
3. 各SVGを最小限のHTMLでラップ → `export_html_to_express` でExpressドキュメントとして登録
   - SVGが変数テキスト要素（`data-field="title"` 等）を持つことでfill_textが機能する
4. オーナーがイラレでSVGを微調整した場合は手順3を再実行して同期

### 週次自動実行（火曜・既存パイプラインに追加）

1. creatorエージェントが台本からメタデータを抽出する
   - `title`: 動画タイトル（20文字以内）
   - `subtitle`: サブタイトル（30文字以内）
   - `keyword`: シーン画像検索用キーワード（英語）
   - `theme_color`: wine / coffee（テンプレート色合い分岐用）
2. Adobe Express MCP (`fill_text`, `document_merge_data_vector`) でテンプレートにデータ流し込み
3. PNG書き出し → `~/Desktop/CUBOCCI_STUDIO/weekly/YYYY-MM-DD-{wine|coffee}/`

---

## 実装スコープ

### 新規追加

| ファイル | 内容 |
|---|---|
| `tools_express.py` | Adobe Express連携ツール（SVG生成・テンプレート登録・データ流し込み・PNG書き出し） |
| `setup_express_templates.py` | 初回セットアップスクリプト（ブランドSVG生成＋Express登録） |

### 既存ファイルの変更

| ファイル | 変更内容 |
|---|---|
| `runner.py` | 火曜の動画パイプラインにExpress素材生成ステップを追加 |
| `.claude/agents/creator.md` | 台本からメタデータ（title/subtitle/keyword）を抽出する責務を追加 |

### スコープ外

- Illustratorでの編集作業（オーナー手動）
- 動画本編の編集（既存After Effectsパイプラインのまま）
- ElevenLabsナレーション（既存通り無効化中）

---

## Adobe MCP ツール対応表

| 処理 | 使用ツール |
|---|---|
| SVGをHTMLでラップしてExpress登録 | `export_html_to_express` |
| テキスト差し替え | `fill_text` |
| ベクターデータ流し込み | `document_merge_data_vector` |
| PNG書き出し | `document_render_vector` |
| アセットアップロード | `asset_add_file` |
