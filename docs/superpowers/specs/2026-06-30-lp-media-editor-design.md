# LP メディア埋め込み + ローカル編集サーバー 設計ドキュメント

**作成日:** 2026-06-30
**ステータス:** 承認済み

---

## 概要

既存のイタリアワインLP（`docs/index.html`）に動画・写真を埋め込む機能と、コードを触らずにブラウザ上でコンテンツを編集できるローカル編集サーバーを追加する。

- ヘッダー: Pexels の葡萄畑動画を背景に自動再生
- 全セクション: 各セクションに写真URLを設定可能（空欄なら非表示）
- 編集UI: `python3 tools_lp_editor.py` でブラウザ編集 → 保存 → デプロイ

---

## ゴール

- ターミナルを触らずに `http://localhost:8765` でテキスト・動画・写真を編集できる
- Pexels キーワード検索 → サムネイル選択 → URL 自動入力
- 「保存」で `docs/content.json` 更新 + `docs/index.html` 再生成
- 「デプロイ」で `bash docs/deploy.sh` 実行 → GitHub Pages に反映

---

## 追加・変更ファイル

```
ai-org/
├── docs/
│   ├── content.json      # media ブロックを追加（既存ファイル拡張）
│   └── index.html        # 動画・写真埋め込み対応（tools_lp.py が再生成）
├── tools_lp.py           # 動画・写真埋め込みロジックを追加（既存ファイル拡張）
├── tools_lp_editor.py    # ローカル編集サーバー（新規作成）
└── tests/
    └── test_lp.py        # メディア関連テストを追加（既存ファイル拡張）
```

---

## content.json メディアスキーマ拡張

既存の `meta`, `headline` 等のキーはそのまま維持し、`media` ブロックを追加する。

```json
{
  "meta": { ... },
  "media": {
    "header_video": "https://videos.pexels.com/video-files/XXXXX/XXXXX.mp4",
    "worries":     { "image": "" },
    "ideals":      { "image": "" },
    "gift":        { "image": "" },
    "cta1":        { "image": "" },
    "profile":     { "image": "" },
    "story": [
      { "image": "" },
      { "image": "" },
      { "image": "" },
      { "image": "" },
      { "image": "" },
      { "image": "" }
    ],
    "why_free":    { "image": "" },
    "why_me":      { "image": "" },
    "qa":          { "image": "" },
    "postscript":  { "image": "" }
  },
  "headline": { ... },
  "worries": [ ... ],
  ...
}
```

**ルール:**
- `media.header_video`: Pexels MP4 の直接URL。空文字の場合は hero.svg にフォールバック
- `media.<section>.image`: 各セクション上部に表示する写真URL。空文字の場合は写真なし
- `media.story` は配列（story セクションの6パートに対応）
- URL は Pexels 直リンクでも外部画像 URL でも可

---

## tools_lp.py 拡張

### ヘッダー動画の埋め込み

`generate_lp()` の `.hero` div を以下のように拡張する。

```python
media = content.get("media", {})
header_video = media.get("header_video", "")

if header_video:
    hero_inner = f"""
<video autoplay muted loop playsinline class="hero-video">
  <source src="{header_video}" type="video/mp4">
</video>
<div class="hero-content">
  <h1>{content["headline"]["catch"]}</h1>
  <div class="deco"></div>
  <p class="sub">{content["headline"]["sub"]}</p>
</div>"""
else:
    # フォールバック: 既存の hero.svg 背景
    hero_inner = f"""
<div class="hero-content">
  <h1>{content["headline"]["catch"]}</h1>
  <div class="deco"></div>
  <p class="sub">{content["headline"]["sub"]}</p>
</div>"""
```

### セクション写真の埋め込み

各セクションに `_section_image(url)` ヘルパーを使って写真を挿入する。

```python
def _section_image(url: str) -> str:
    if not url:
        return ""
    return f'<div class="section-image"><img src="{url}" alt="" loading="lazy"></div>'
```

### 追加 CSS

```css
/* ヘッダー動画 */
.hero { position: relative; overflow: hidden; }
.hero-video {
    position: absolute; top: 0; left: 0;
    width: 100%; height: 100%;
    object-fit: cover; z-index: 0;
}
.hero-content {
    position: relative; z-index: 1;
    padding: 80px 20px 60px;
    text-align: center;
}
/* セクション写真 */
.section-image {
    width: 100%; max-height: 300px;
    overflow: hidden;
}
.section-image img {
    width: 100%; height: 300px;
    object-fit: cover; display: block;
}
```

---

## tools_lp_editor.py 設計

### 起動

```bash
python3 tools_lp_editor.py
# → http://localhost:8765 をブラウザで自動オープン
```

### サーバー構成（Python stdlib のみ）

`http.server.BaseHTTPRequestHandler` を継承したカスタムハンドラ:

| エンドポイント | メソッド | 処理 |
|---|---|---|
| `GET /` | GET | 編集UI HTMLを返す |
| `GET /content` | GET | `docs/content.json` の内容を JSON で返す |
| `POST /save` | POST | リクエストボディの JSON を `docs/content.json` に保存 → `write_lp()` 実行 |
| `POST /deploy` | POST | `bash docs/deploy.sh` をサブプロセスで実行 |
| `GET /pexels?q=<query>&type=<video|photo>` | GET | Pexels API を叩いてサムネイル一覧を JSON で返す |

### 編集UI レイアウト

```
┌─────────────────────────────────────────────┐
│  LP エディタ              [💾 保存] [🚀 デプロイ] │
├─────────────────────────────────────────────┤
│ ▼ ヘッダー動画                                │
│   [Pexels検索: 葡萄畑          🔍]            │
│   動画URL: [_________________________]       │
│   キャッチコピー: [___________________]       │
│   サブテキスト:   [___________________]       │
├─────────────────────────────────────────────┤
│ ▼ お悩みセクション                             │
│   写真URL: [___________] [Pexels検索 🔍]     │
│   ・[_____________________________] [削除]   │
│   ・[_____________________________] [削除]   │
│   [+ 項目追加]                               │
├─────────────────────────────────────────────┤
│ ▼ ストーリー①「日常・現実の世界」                │
│   写真URL: [___________] [Pexels検索 🔍]     │
│   タイトル: [_________________________]      │
│   本文: [textarea____________________]      │
│  ...（全6パート）                             │
└─────────────────────────────────────────────┘
```

### Pexels 検索の動作

1. キーワードを入力して🔍をクリック
2. サーバーが `GET /pexels?q=<keyword>&type=video` を Pexels API に転送
3. サムネイル画像一覧をモーダルで表示
4. クリックで対応する URL フィールドに自動入力
5. `.env` の `PEXELS_API_KEY` を使用（既存の環境変数）

### 保存フロー

1. ブラウザの「保存」ボタン → `POST /save` に JSON を送信
2. サーバーが `docs/content.json` に書き込み
3. サーバーが `write_lp()` を呼び出して `docs/index.html` を再生成
4. レスポンス: `{"status": "ok", "message": "保存完了"}` または `{"status": "error", ...}`
5. ブラウザに「✅ 保存完了」を表示

### デプロイフロー

1. 「デプロイ」ボタン → `POST /deploy`
2. サーバーが `subprocess.run(["bash", "docs/deploy.sh"])` を実行
3. 完了後: `{"status": "ok", "url": "https://donciruzzodesign-byte.github.io/ai-org/"}`
4. ブラウザに URL を表示

---

## HTML 埋め込みの仕様

### ヘッダー動画

- `header_video` が設定されている場合: `<video autoplay muted loop playsinline>` で背景動画
- 空の場合: 現状の `hero.svg` SVG 背景にフォールバック（既存動作を維持）
- テキスト（キャッチコピー・サブ）は動画の上に `z-index: 1` でオーバーレイ

### セクション写真

- `image` が設定されているセクションのみ `<div class="section-image">` を出力
- 空の場合は写真エリアなし（セクションのレイアウトに影響なし）
- `loading="lazy"` で遅延読み込み（パフォーマンス維持）
- 最大高さ 300px、`object-fit: cover` で縦横比維持

---

## テスト方針

既存の `tests/test_lp.py` に以下を追加する:

| テスト名 | 内容 |
|---|---|
| `test_generate_lp_with_header_video` | `header_video` を設定すると `<video>` タグが出力される |
| `test_generate_lp_without_header_video` | `header_video` が空でも正常に生成される（フォールバック） |
| `test_generate_lp_with_section_image` | `media.worries.image` を設定すると `<img>` タグが出力される |
| `test_generate_lp_without_section_image` | `image` が空のセクションには `<img>` タグが出力されない |
| `test_content_json_media_structure` | `media` ブロックのスキーマバリデーション |

`tools_lp_editor.py` のサーバー自体はブラウザ操作が必要なため自動テスト対象外。
Pexels API 呼び出しは既存の `PEXELS_API_KEY` に依存するためテスト対象外。

---

## 制約

- Python 標準ライブラリのみ（Flask 等の外部パッケージ追加禁止）
- `PEXELS_API_KEY` は既存の `.env` から読み込む（既存の `_load_env()` を流用）
- `tools_lp_editor.py` は開発用ローカルサーバー。本番公開用ではない
- CUBOCCI STUDIO のブランド名は LP 上に表示しない（既存制約を維持）
- カラー固定: bg=#F5F0E8, text=#6B1A2A, accent=#C9A84C（既存制約を維持）
