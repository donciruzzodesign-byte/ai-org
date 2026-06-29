# LP メディア埋め込み + ローカル編集サーバー 実装計画

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** LP に Pexels 動画・写真を埋め込み、`localhost:8765` でブラウザ編集できるようにする。

**Architecture:** `content.json` に `media` ブロックを追加し、`tools_lp.py` でヘッダー動画と各セクション写真を HTML に埋め込む。`tools_lp_editor.py` が Python stdlib だけで HTTP サーバーを起動し、編集UI・Pexels プロキシ・保存・デプロイのエンドポイントを提供する。

**Tech Stack:** Python 3 stdlib（http.server, json, os, subprocess, urllib）、Pexels API v1 / Videos API

## Global Constraints

- Python 標準ライブラリのみ（Flask 等の外部パッケージ追加禁止）
- カラー固定: bg=#F5F0E8, text=#6B1A2A, accent=#C9A84C
- CUBOCCI STUDIO のブランド名は LP 上に表示しない
- `docs/content.json` が single source of truth（`tools_lp.py` が index.html を再生成）
- `PEXELS_API_KEY` は `.env` から読み込む
- 既存の 19 テストをすべて維持する（テスト数が減ってはいけない）

---

### Task 1: content.json 拡張 + tools_lp.py メディア埋め込み

**Files:**
- Modify: `tests/test_lp.py` — CONTENT_PATH バグ修正 + 5 個のメディアテスト追加
- Modify: `docs/content.json` — `media` ブロック追加
- Modify: `tools_lp.py` — `_section_image()` ヘルパー追加、`_css()` 拡張、`generate_lp()` 更新

**Interfaces:**
- Produces: `generate_lp(content)` が `content["media"]["header_video"]` を `<video>` タグに、`content["media"][section]["image"]` を `<img>` タグに変換する
- Produces: `_section_image(url: str) -> str` — url が空なら空文字、あれば `<div class="section-image"><img ...></div>`

---

- [ ] **Step 1: `tests/test_lp.py` の CONTENT_PATH バグを修正**

`lp/` ディレクトリは `docs/` に移動済みだが `test_lp.py` が古いパスを参照している。

`tests/test_lp.py` の 8 行目を変更:

```python
# 変更前
CONTENT_PATH = os.path.join(os.path.dirname(__file__), "..", "lp", "content.json")

# 変更後
CONTENT_PATH = os.path.join(os.path.dirname(__file__), "..", "docs", "content.json")
```

- [ ] **Step 2: 既存テストが通ることを確認**

```bash
python3 -m pytest tests/test_lp.py -v
```

期待: 19 テストすべて PASS

- [ ] **Step 3: `docs/content.json` に `media` ブロックを追加**

`"meta"` ブロックの直後（`"headline"` の前）に `"media"` キーを追加する。

`docs/content.json` を更新（`"meta": {...},` の次の行に挿入）:

```json
  "media": {
    "header_video": "",
    "worries":    { "image": "" },
    "ideals":     { "image": "" },
    "gift":       { "image": "" },
    "cta1":       { "image": "" },
    "profile":    { "image": "" },
    "story": [
      { "image": "" },
      { "image": "" },
      { "image": "" },
      { "image": "" },
      { "image": "" },
      { "image": "" }
    ],
    "why_free":   { "image": "" },
    "why_me":     { "image": "" },
    "qa":         { "image": "" },
    "postscript": { "image": "" }
  },
```

- [ ] **Step 4: 5 個のメディアテストを書く（まだ FAIL することを確認するため先に書く）**

`tests/test_lp.py` の末尾に追加:

```python
def test_content_json_media_structure():
    content = load_content()
    assert "media" in content, "content.json に 'media' ブロックがありません"
    m = content["media"]
    assert "header_video" in m
    for key in ["worries", "ideals", "gift", "cta1", "profile", "why_free", "why_me", "qa", "postscript"]:
        assert key in m, f"media に '{key}' がありません"
        assert "image" in m[key], f"media.{key} に 'image' がありません"
    assert "story" in m
    assert len(m["story"]) == 6
    for i, s in enumerate(m["story"]):
        assert "image" in s, f"media.story[{i}] に 'image' がありません"


def test_generate_lp_with_header_video():
    from tools_lp import generate_lp
    content = load_content()
    content["media"] = content.get("media", {})
    content["media"]["header_video"] = "https://example.com/vineyard.mp4"
    html = generate_lp(content)
    assert "<video" in html
    assert "https://example.com/vineyard.mp4" in html
    assert 'autoplay' in html
    assert 'muted' in html
    assert 'loop' in html


def test_generate_lp_without_header_video():
    from tools_lp import generate_lp
    content = load_content()
    content["media"] = content.get("media", {})
    content["media"]["header_video"] = ""
    html = generate_lp(content)
    assert "<video" not in html
    assert content["headline"]["catch"] in html


def test_generate_lp_with_section_image():
    from tools_lp import generate_lp
    content = load_content()
    content["media"] = content.get("media", {})
    content["media"]["worries"] = {"image": "https://example.com/worry.jpg"}
    html = generate_lp(content)
    assert '<div class="section-image">' in html
    assert "https://example.com/worry.jpg" in html
    assert 'loading="lazy"' in html


def test_generate_lp_without_section_image():
    from tools_lp import generate_lp
    content = load_content()
    content["media"] = content.get("media", {})
    content["media"]["worries"] = {"image": ""}
    html = generate_lp(content)
    # section-image div は出力されない（他セクションも空なら）
    # 少なくとも空 URL の img タグは出力されないことを確認
    assert 'src=""' not in html
```

- [ ] **Step 5: テストが FAIL することを確認**

```bash
python3 -m pytest tests/test_lp.py -v -k "media or header_video or section_image"
```

期待: 上記 5 テストが FAIL（`test_content_json_media_structure` は Step 3 で追加済みなら PASS になるはず）

- [ ] **Step 6: `tools_lp.py` に `_section_image()` ヘルパーを追加**

`_nl2br()` 関数の直後に追加:

```python
def _section_image(url: str) -> str:
    if not url:
        return ""
    return f'<div class="section-image"><img src="{url}" alt="" loading="lazy"></div>'
```

- [ ] **Step 7: `tools_lp.py` の `_css()` にメディア用 CSS を追加**

`_css()` の return 文の f-string の末尾（`@media (min-width: 768px) {{ ... }}` の後）に追加:

```python
.hero {{ position: relative; overflow: hidden; }}
.hero-video {{
    position: absolute; top: 0; left: 0;
    width: 100%; height: 100%;
    object-fit: cover; z-index: 0;
}}
.hero-content {{
    position: relative; z-index: 1;
    padding: 80px 20px 60px;
    text-align: center;
}}
.section-image {{ width: 100%; max-height: 300px; overflow: hidden; margin-bottom: 24px; }}
.section-image img {{ width: 100%; height: 300px; object-fit: cover; display: block; }}
```

（`_css()` の return 文は f-string なので `{{` と `}}` でエスケープする点に注意）

- [ ] **Step 8: `tools_lp.py` の `generate_lp()` を更新してメディアを埋め込む**

`generate_lp()` 関数を以下のように変更する。変更箇所は 4 つ。

**8a. `line_url = c["meta"]["line_url"]` の直後に media 抽出を追加**:

```python
    media = c.get("media", {})
    header_video = media.get("header_video", "")
```

**8b. `hero_style` を使った if/elif/else ブロックの後、`worries_html = ...` の前に `hero_div` を構築する**:

```python
    if header_video:
        hero_div = (
            f'<div class="hero" style="padding:0;min-height:400px;">\n'
            f'  <video autoplay muted loop playsinline class="hero-video">\n'
            f'    <source src="{header_video}" type="video/mp4">\n'
            f'  </video>\n'
            f'  <div class="hero-content"><div class="container">\n'
            f'    <h1>{c["headline"]["catch"]}</h1>\n'
            f'    <div class="deco"></div>\n'
            f'    <p class="sub">{c["headline"]["sub"]}</p>\n'
            f'  </div></div>\n'
            f'</div>'
        )
    else:
        hero_div = (
            f'<div class="hero" {hero_style}>\n'
            f'  <div class="container">\n'
            f'    <h1>{c["headline"]["catch"]}</h1>\n'
            f'    <div class="deco"></div>\n'
            f'    <p class="sub">{c["headline"]["sub"]}</p>\n'
            f'  </div>\n'
            f'</div>'
        )
```

**8c. `story_html` の生成を変更してストーリー写真を含める**:

```python
    story_media = media.get("story", [])
    story_html = "\n".join(
        f'<div class="story-part">'
        f'{_section_image(story_media[i].get("image", "") if i < len(story_media) else "")}'
        f'<h3>{p["title"]}</h3><p>{_nl2br(p["body"])}</p>'
        f'</div>'
        for i, p in enumerate(c["story"])
    )
```

**8d. return 文の HTML を更新する**:

hero div と各セクションに写真を挿入する。return 文の該当箇所を以下に置き換え:

```python
    return f"""<!DOCTYPE html>
<html lang="ja">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{c["headline"]["catch"]}</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Cormorant+Garamond:wght@400;600;700&family=Noto+Sans+JP:wght@400;700&display=swap">
  <style>{_css(colors)}</style>
</head>
<body>

{hero_div}

<section>
  <div class="container">
    {_section_image(media.get("worries", {{}}).get("image", ""))}
    <h2>こんなお悩みありませんか？</h2>
    <div class="divider"></div>
    <ul class="bullets">{worries_html}</ul>
  </div>
</section>

<section>
  <div class="container">
    {_section_image(media.get("ideals", {{}}).get("image", ""))}
    <h2>でも…こうなりたい！</h2>
    <div class="divider"></div>
    <ul class="bullets">{ideals_html}</ul>
  </div>
</section>

<section>
  <div class="container">
    {_section_image(media.get("gift", {{}}).get("image", ""))}
    <h2>そんなあなたにプレゼント！</h2>
    <div class="divider"></div>
    <div class="gift-box">
      <div class="gift-title">『{{c["gift"]["title"]}}』</div>
      <div class="gift-subtitle">{{c["gift"].get("subtitle", "")}}</div>
      <p>{{c["gift"]["description"]}}</p>
      <ul class="bullets" style="margin-top:16px">{{gift_items_html}}</ul>
    </div>
  </div>
</section>

<section>
  <div class="container" style="text-align:center">
    {_section_image(media.get("cta1", {{}}).get("image", ""))}
    <h2>公式LINE追加の手順</h2>
    <div class="divider" style="margin:16px auto 32px"></div>
    <div class="steps">{{steps_html}}</div>
    {{cta_btn}}
  </div>
</section>

<section>
  <div class="container">
    {_section_image(media.get("profile", {{}}).get("image", ""))}
    <h2>はじめまして</h2>
    <div class="divider"></div>
    <div class="profile-name">{{c["profile"]["name"]}}</div>
    <p>{{_nl2br(c["profile"]["body"])}}</p>
  </div>
</section>

<section>
  <div class="container">
    <h2>私のストーリー</h2>
    <div class="divider"></div>
    {{story_html}}
  </div>
</section>

<section>
  <div class="container">
    {_section_image(media.get("why_free", {{}}).get("image", ""))}
    <h2>なんで無料なの？</h2>
    <div class="divider"></div>
    <p>{{_nl2br(c["why_free"])}}</p>
  </div>
</section>

<section>
  <div class="container">
    {_section_image(media.get("why_me", {{}}).get("image", ""))}
    <h2>あなただからなんです！</h2>
    <div class="divider"></div>
    <p>{{_nl2br(c["why_me"])}}</p>
  </div>
</section>

<section>
  <div class="container">
    {_section_image(media.get("qa", {{}}).get("image", ""))}
    <h2>よくあるご質問</h2>
    <div class="divider"></div>
    <div class="accordion">{{qa_html}}</div>
  </div>
</section>

<div class="postscript">
  <div class="container">
    {_section_image(media.get("postscript", {{}}).get("image", ""))}
    <h2>追伸</h2>
    <div class="divider"></div>
    <p>{{_nl2br(c["postscript"])}}</p>
  </div>
</div>

<section>
  <div class="container" style="text-align:center">
    <h2>さあ、一緒に始めましょう</h2>
    <div class="divider" style="margin:16px auto 32px"></div>
    {{cta_btn}}
  </div>
</section>

<footer>
  <div class="container">
    <p>© 2026 Ciro／Hiro. All rights reserved.</p>
  </div>
</footer>

<script>
document.querySelectorAll('.accordion-btn').forEach(function(btn) {{
  btn.addEventListener('click', function() {{
    this.parentElement.classList.toggle('open');
  }});
}});
</script>
</body>
</html>"""
```

**注意:** 上記の return 文中の `{_section_image(...)}` は Python f-string の外側で評価される（generate_lp の f-string 全体のコンテキスト内）。`{{` と `}}` は f-string のリテラルの `{` と `}` を表す。`c["gift"]["title"]` のような変数参照は `{{c["gift"]["title"]}}` ではなく実際に generate_lp の f-string 内の式として評価される。

**重要:** 既存の return 文（166〜336行）を丸ごとこの新しい return 文に置き換える。`{_section_image(...)}` 部分は f-string 内の Python 式として動作する。`{{c[...]}}` は f-string エスケープなので `{c[...]}` として展開される。

実際の実装時のコード（f-string として正しい形式）:

```python
    return f"""<!DOCTYPE html>
<html lang="ja">
...
{hero_div}

<section>
  <div class="container">
    {_section_image(media.get("worries", {}).get("image", ""))}
    <h2>こんなお悩みありませんか？</h2>
    ...
```

ただし Python の f-string 内で `{` と `}` を使うには `{{` と `}}` でエスケープが必要（`media.get("worries", {{}})` のように）。しかし `_section_image()` の呼び出し自体は f-string 式として評価されるため `{_section_image(media.get("worries", {}).get("image", ""))}` の内側の `{}` はエスケープ不要。

**実装上の最も確実な方法:** return 文を f-string として書くとエスケープが複雑になるため、各セクション画像を事前に変数に展開してから f-string を構成する:

```python
    img_worries    = _section_image(media.get("worries",    {}).get("image", ""))
    img_ideals     = _section_image(media.get("ideals",     {}).get("image", ""))
    img_gift       = _section_image(media.get("gift",       {}).get("image", ""))
    img_cta1       = _section_image(media.get("cta1",       {}).get("image", ""))
    img_profile    = _section_image(media.get("profile",    {}).get("image", ""))
    img_why_free   = _section_image(media.get("why_free",   {}).get("image", ""))
    img_why_me     = _section_image(media.get("why_me",     {}).get("image", ""))
    img_qa         = _section_image(media.get("qa",         {}).get("image", ""))
    img_postscript = _section_image(media.get("postscript", {}).get("image", ""))
```

そして return 文で `{img_worries}` のように参照する。

- [ ] **Step 9: 全テスト（24 テスト）を実行して PASS を確認**

```bash
python3 -m pytest tests/test_lp.py -v
```

期待: 24 テスト全 PASS（既存 19 + 新規 5）

- [ ] **Step 10: LP を手動再生成してメディアブロック対応を確認**

```bash
python3 tools_lp.py --skip-assets
```

期待: `✅ LP生成完了: .../docs/index.html`（エラーなし）

- [ ] **Step 11: コミット**

```bash
git add tests/test_lp.py docs/content.json tools_lp.py
git commit -m "feat: add media block to content.json and LP video/photo embedding"
```

---

### Task 2: tools_lp_editor.py ローカル編集サーバー

**Files:**
- Create: `tools_lp_editor.py` — Python stdlib HTTP サーバー（ポート 8765）

**Interfaces:**
- Consumes: `docs/content.json`（Task 1 で `media` ブロック追加済み）
- Consumes: `tools_lp.write_lp(content)` — 保存時に HTML 再生成
- Consumes: `docs/deploy.sh` — デプロイ時に bash 実行
- Consumes: `PEXELS_API_KEY`（`.env` から読み込み）
- Produces: `python3 tools_lp_editor.py` でブラウザが自動オープンする編集 UI

---

- [ ] **Step 1: `tools_lp_editor.py` を新規作成**

以下の内容でファイルを作成する（Python stdlib のみ使用）:

```python
import http.server
import json
import os
import subprocess
import urllib.parse
import urllib.request

ROOT = os.path.dirname(os.path.abspath(__file__))
CONTENT_PATH = os.path.join(ROOT, "docs", "content.json")
DEPLOY_SH = os.path.join(ROOT, "docs", "deploy.sh")


def _load_env():
    env_path = os.path.join(ROOT, ".env")
    if not os.path.exists(env_path):
        return
    with open(env_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, _, v = line.partition("=")
                os.environ.setdefault(k.strip(), v.strip())


class LPEditorHandler(http.server.BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        print(f"[editor] {fmt % args}")

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        query = urllib.parse.parse_qs(parsed.query)
        if path == "/":
            self._serve_html(_editor_html())
        elif path == "/content":
            with open(CONTENT_PATH, encoding="utf-8") as f:
                self._serve_html(f.read(), content_type="application/json")
        elif path == "/pexels":
            self._serve_pexels(query)
        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        if self.path == "/save":
            self._handle_save()
        elif self.path == "/deploy":
            self._handle_deploy()
        else:
            self.send_response(404)
            self.end_headers()

    def _serve_html(self, body_str, content_type="text/html; charset=utf-8"):
        body = body_str.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", len(body))
        self.end_headers()
        self.wfile.write(body)

    def _json_response(self, data, code=200):
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", len(body))
        self.end_headers()
        self.wfile.write(body)

    def _serve_pexels(self, query):
        q = query.get("q", [""])[0]
        media_type = query.get("type", ["photo"])[0]
        api_key = os.environ.get("PEXELS_API_KEY", "")
        if not api_key:
            self._json_response({"error": "PEXELS_API_KEY が未設定です"}, 400)
            return
        try:
            if media_type == "video":
                url = f"https://api.pexels.com/videos/search?query={urllib.parse.quote(q)}&per_page=12"
            else:
                url = f"https://api.pexels.com/v1/search?query={urllib.parse.quote(q)}&per_page=12"
            req = urllib.request.Request(url, headers={"Authorization": api_key})
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            self._json_response(data)
        except Exception as e:
            self._json_response({"error": str(e)}, 500)

    def _handle_save(self):
        length = int(self.headers.get("Content-Length", 0))
        raw = self.rfile.read(length)
        try:
            content = json.loads(raw.decode("utf-8"))
            with open(CONTENT_PATH, "w", encoding="utf-8") as f:
                json.dump(content, f, ensure_ascii=False, indent=2)
            from tools_lp import write_lp
            write_lp(content)
            self._json_response({"status": "ok", "message": "保存完了"})
        except Exception as e:
            self._json_response({"status": "error", "message": str(e)}, 500)

    def _handle_deploy(self):
        try:
            result = subprocess.run(
                ["bash", DEPLOY_SH],
                capture_output=True, text=True, timeout=120
            )
            if result.returncode == 0:
                self._json_response({
                    "status": "ok",
                    "url": "https://donciruzzodesign-byte.github.io/ai-org/",
                    "output": result.stdout,
                })
            else:
                self._json_response(
                    {"status": "error", "message": result.stderr or result.stdout}, 500
                )
        except Exception as e:
            self._json_response({"status": "error", "message": str(e)}, 500)


def _editor_html():
    return """<!DOCTYPE html>
<html lang="ja">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>LP エディタ</title>
  <style>
    *{box-sizing:border-box;margin:0;padding:0}
    body{font-family:'Noto Sans JP',sans-serif;background:#f0ece4;color:#333}
    #topbar{position:sticky;top:0;z-index:100;background:#6B1A2A;color:#F5F0E8;
      padding:12px 20px;display:flex;align-items:center;gap:12px;box-shadow:0 2px 6px rgba(0,0,0,.3)}
    #topbar h1{font-size:18px;flex:1}
    .btn{padding:8px 20px;border:none;border-radius:4px;cursor:pointer;font-size:14px;font-weight:bold}
    .btn-save{background:#C9A84C;color:#6B1A2A}
    .btn-deploy{background:#2a6b2a;color:#fff}
    #status{font-size:13px;min-width:140px}
    .card{background:#fff;margin:16px;border-radius:8px;box-shadow:0 1px 4px rgba(0,0,0,.1);overflow:hidden}
    .card-header{background:#6B1A2A;color:#F5F0E8;padding:12px 16px;cursor:pointer;
      display:flex;justify-content:space-between;font-weight:bold;user-select:none}
    .card-body{padding:16px;display:none}
    .card-body.open{display:block}
    label{display:block;font-size:12px;color:#888;margin:12px 0 4px}
    label:first-child{margin-top:0}
    input[type=text],textarea{width:100%;padding:8px 10px;border:1px solid #ddd;
      border-radius:4px;font-size:14px;font-family:inherit}
    textarea{min-height:80px;resize:vertical}
    .row{display:flex;gap:8px;align-items:center}
    .row input{flex:1}
    .btn-px{padding:8px 12px;background:#05A081;color:#fff;border:none;
      border-radius:4px;cursor:pointer;font-size:12px;white-space:nowrap}
    .list-item{display:flex;gap:8px;margin-bottom:8px}
    .list-item input{flex:1}
    .btn-del{background:#c44;color:#fff;border:none;border-radius:4px;padding:6px 10px;cursor:pointer}
    .btn-add{background:#C9A84C;color:#fff;border:none;border-radius:4px;
      padding:8px 16px;cursor:pointer;margin-top:8px;font-size:13px}
    fieldset{border:1px solid #e0d8cc;border-radius:4px;padding:12px;margin-bottom:12px}
    legend{font-weight:bold;color:#6B1A2A;font-size:13px;padding:0 4px}
    #modal{display:none;position:fixed;inset:0;background:rgba(0,0,0,.7);z-index:200;overflow:auto;padding:40px 20px}
    #modal.open{display:block}
    #modal-inner{background:#fff;max-width:800px;margin:0 auto;border-radius:8px;overflow:hidden}
    #modal-head{background:#6B1A2A;color:#F5F0E8;padding:12px 16px;display:flex;gap:8px;align-items:center}
    #modal-head input{flex:1;padding:8px;border:none;border-radius:4px}
    #modal-head .search-btn{padding:8px 16px;background:#C9A84C;border:none;border-radius:4px;cursor:pointer;font-weight:bold}
    #modal-close{background:none;border:none;color:#F5F0E8;font-size:22px;cursor:pointer;margin-left:auto;line-height:1}
    #modal-grid{padding:16px;display:grid;grid-template-columns:repeat(auto-fill,minmax(160px,1fr));gap:12px;max-height:60vh;overflow:auto}
    .res{cursor:pointer;border-radius:4px;overflow:hidden;border:2px solid transparent}
    .res:hover{border-color:#C9A84C}
    .res img{width:100%;height:110px;object-fit:cover;display:block}
    .res-url{font-size:10px;color:#666;padding:4px;word-break:break-all}
  </style>
</head>
<body>
<div id="topbar">
  <h1>LP エディタ</h1>
  <button class="btn btn-save" onclick="saveContent()">💾 保存</button>
  <button class="btn btn-deploy" onclick="deployContent()">🚀 デプロイ</button>
  <span id="status"></span>
</div>
<div id="editor"></div>

<div id="modal">
  <div id="modal-inner">
    <div id="modal-head">
      <input id="px-q" type="text" placeholder="Pexels キーワード（英語推奨）..."
             onkeydown="if(event.key==='Enter')searchPx()">
      <button class="search-btn" onclick="searchPx()">🔍 検索</button>
      <button id="modal-close" onclick="closeModal()">✕</button>
    </div>
    <div id="modal-grid"></div>
  </div>
</div>

<script>
let C={};
let _px_target=null, _px_type='photo';

async function init(){
  const r=await fetch('/content');
  C=await r.json();
  render();
}

function status(msg,ok=true){
  const el=document.getElementById('status');
  el.textContent=msg;
  el.style.color=ok?'#C9A84C':'#ff8888';
}

async function saveContent(){
  status('保存中...');
  try{
    const data=collect();
    const r=await fetch('/save',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(data)});
    const res=await r.json();
    res.status==='ok'?status('✅ 保存完了'):(status('❌ '+res.message,false),console.error(res));
  }catch(e){status('❌ '+e.message,false);}
}

async function deployContent(){
  status('デプロイ中...');
  try{
    const r=await fetch('/deploy',{method:'POST'});
    const res=await r.json();
    res.status==='ok'?status('✅ デプロイ完了'):status('❌ '+res.message,false);
  }catch(e){status('❌ '+e.message,false);}
}

function collect(){
  const c=JSON.parse(JSON.stringify(C));
  // simple scalar paths
  document.querySelectorAll('[data-p]').forEach(el=>{
    const parts=el.getAttribute('data-p').split('.');
    let o=c;
    for(let i=0;i<parts.length-1;i++){
      const k=isNaN(parts[i])?parts[i]:+parts[i];
      if(o[k]===undefined) o[k]=isNaN(parts[i+1])?{}:[];
      o=o[k];
    }
    const last=isNaN(parts[parts.length-1])?parts[parts.length-1]:+parts[parts.length-1];
    o[last]=el.value;
  });
  // arrays rebuilt from list containers
  ['worries','ideals','line_steps'].forEach(k=>{
    const el=document.querySelector(`[data-list="${k}"]`);
    if(el) c[k]=[...el.querySelectorAll('input')].map(i=>i.value);
  });
  const giftEl=document.querySelector('[data-list="gift.items"]');
  if(giftEl) c.gift.items=[...giftEl.querySelectorAll('input')].map(i=>i.value);
  c.qa=[...document.querySelectorAll('.qa-item')].map(el=>({
    q:el.querySelector('[data-qa="q"]').value,
    a:el.querySelector('[data-qa="a"]').value,
  }));
  return c;
}

function openPx(inputId,type='photo'){
  _px_target=document.getElementById(inputId);
  _px_type=type;
  document.getElementById('modal').classList.add('open');
  document.getElementById('px-q').focus();
}
function closeModal(){
  document.getElementById('modal').classList.remove('open');
  document.getElementById('modal-grid').innerHTML='';
}
async function searchPx(){
  const q=document.getElementById('px-q').value.trim();
  if(!q)return;
  document.getElementById('modal-grid').innerHTML='<p style="padding:16px">検索中...</p>';
  const r=await fetch(`/pexels?q=${encodeURIComponent(q)}&type=${_px_type}`);
  const data=await r.json();
  const grid=document.getElementById('modal-grid');
  grid.innerHTML='';
  if(data.error){grid.innerHTML=`<p style="padding:16px;color:red">${data.error}</p>`;return;}
  const items=_px_type==='video'
    ?(data.videos||[]).map(v=>{const f=(v.video_files||[]).find(x=>x.quality==='hd')||(v.video_files||[])[0];return f?{thumb:v.image,url:f.link}:null;}).filter(Boolean)
    :(data.photos||[]).map(p=>({thumb:p.src.medium,url:p.src.large}));
  items.forEach(({thumb,url})=>{
    const d=document.createElement('div');
    d.className='res';
    d.innerHTML=`<img src="${esc(thumb)}" alt=""><div class="res-url">${esc(url)}</div>`;
    d.onclick=()=>{if(_px_target)_px_target.value=url;closeModal();};
    grid.appendChild(d);
  });
  if(!items.length) grid.innerHTML='<p style="padding:16px">結果なし</p>';
}

function esc(s){return(s||'').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');}
function addItem(key,val=''){
  const c=document.querySelector(`[data-list="${key}"]`);
  const d=document.createElement('div');d.className='list-item';
  d.innerHTML=`<input type="text" value="${esc(val)}"><button class="btn-del" onclick="this.parentElement.remove()">削除</button>`;
  c.appendChild(d);
}
function toggle(h){
  const b=h.nextElementSibling;b.classList.toggle('open');
  h.querySelector('.ico').textContent=b.classList.contains('open')?'▲':'▼';
}

function pxBtn(id,type='photo'){
  return `<button class="btn-px" onclick="openPx('${id}','${type}')">Pexels 🔍</button>`;
}
function mediaInput(label,id,path,type='photo'){
  const m=C.media||{};
  const val=path.split('.').reduce((o,k)=>o&&o[isNaN(k)?k:+k],m)||'';
  return `<label>${label}</label><div class="row"><input type="text" id="${id}" data-p="${path}" value="${esc(val)}">${pxBtn(id,type)}</div>`;
}
function card(title,bodyHtml){
  return `<div class="card"><div class="card-header" onclick="toggle(this)">${esc(title)}<span class="ico">▼</span></div><div class="card-body">${bodyHtml}</div></div>`;
}
function listItems(key,arr){
  return `<div data-list="${key}">${(arr||[]).map(v=>`<div class="list-item"><input type="text" value="${esc(v)}"><button class="btn-del" onclick="this.parentElement.remove()">削除</button></div>`).join('')}</div><button class="btn-add" onclick="addItem('${key}')">＋ 項目追加</button>`;
}

function render(){
  const c=C, m=c.media||{};
  let h='';

  h+=card('ヘッダー動画・メインコピー',`
    ${mediaInput('葡萄畑動画 URL（Pexels MP4）','hv','media.header_video','video')}
    <label>キャッチコピー</label><textarea data-p="headline.catch">${esc(c.headline?.catch||'')}</textarea>
    <label>サブテキスト</label><input type="text" data-p="headline.sub" value="${esc(c.headline?.sub||'')}">
    <label>LINE URL</label><input type="text" data-p="meta.line_url" value="${esc(c.meta?.line_url||'')}">
  `);

  h+=card('お悩みセクション',`
    ${mediaInput('セクション写真 URL','img_worries','media.worries.image')}
    <label>お悩みリスト</label>${listItems('worries',c.worries)}
  `);

  h+=card('こうなりたい（理想）',`
    ${mediaInput('セクション写真 URL','img_ideals','media.ideals.image')}
    <label>理想リスト</label>${listItems('ideals',c.ideals)}
  `);

  h+=card('プレゼントセクション',`
    ${mediaInput('セクション写真 URL','img_gift','media.gift.image')}
    <label>タイトル</label><input type="text" data-p="gift.title" value="${esc(c.gift?.title||'')}">
    <label>サブタイトル</label><input type="text" data-p="gift.subtitle" value="${esc(c.gift?.subtitle||'')}">
    <label>説明文</label><textarea data-p="gift.description">${esc(c.gift?.description||'')}</textarea>
    <label>内容リスト</label>${listItems('gift.items',c.gift?.items)}
  `);

  h+=card('LINE 登録セクション',`
    ${mediaInput('セクション写真 URL','img_cta1','media.cta1.image')}
    <label>CTA ボタンテキスト</label><input type="text" data-p="cta_text" value="${esc(c.cta_text||'')}">
    <label>手順リスト</label>${listItems('line_steps',c.line_steps)}
  `);

  h+=card('プロフィールセクション',`
    ${mediaInput('セクション写真 URL','img_profile','media.profile.image')}
    <label>名前</label><input type="text" data-p="profile.name" value="${esc(c.profile?.name||'')}">
    <label>本文</label><textarea data-p="profile.body">${esc(c.profile?.body||'')}</textarea>
  `);

  const sm=m.story||[];
  const storyParts=(c.story||[]).map((p,i)=>`
    <fieldset>
      <legend>パート ${i+1}「${esc(p.title)}」</legend>
      ${mediaInput('写真 URL',`img_st${i}`,`media.story.${i}.image`)}
      <label>タイトル</label><input type="text" data-p="story.${i}.title" value="${esc(p.title||'')}">
      <label>本文</label><textarea data-p="story.${i}.body">${esc(p.body||'')}</textarea>
    </fieldset>`).join('');
  h+=card('ストーリーセクション（全6パート）',storyParts);

  h+=card('なんで無料なの？',`
    ${mediaInput('セクション写真 URL','img_wf','media.why_free.image')}
    <textarea data-p="why_free">${esc(c.why_free||'')}</textarea>
  `);

  h+=card('あなただからなんです！',`
    ${mediaInput('セクション写真 URL','img_wm','media.why_me.image')}
    <textarea data-p="why_me">${esc(c.why_me||'')}</textarea>
  `);

  const qaHtml=(c.qa||[]).map((q,i)=>`
    <div class="qa-item">
      <label>質問 ${i+1}</label><input type="text" data-qa="q" value="${esc(q.q||'')}">
      <label>回答</label><textarea data-qa="a">${esc(q.a||'')}</textarea>
    </div>`).join('');
  h+=card('よくあるご質問',`
    ${mediaInput('セクション写真 URL','img_qa','media.qa.image')}
    ${qaHtml}
  `);

  h+=card('追伸',`
    ${mediaInput('セクション写真 URL','img_ps','media.postscript.image')}
    <textarea data-p="postscript">${esc(c.postscript||'')}</textarea>
  `);

  document.getElementById('editor').innerHTML=h;
}

init();
</script>
</body>
</html>"""


if __name__ == "__main__":
    import webbrowser
    _load_env()
    PORT = 8765
    server = http.server.HTTPServer(("localhost", PORT), LPEditorHandler)
    url = f"http://localhost:{PORT}"
    print(f"✅ LP エディタ起動: {url}")
    print("終了するには Ctrl+C を押してください")
    webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n✋ サーバーを停止しました")
```

- [ ] **Step 2: 構文チェック**

```bash
python3 -m py_compile tools_lp_editor.py && echo "OK"
```

期待: `OK`（エラーなし）

- [ ] **Step 3: サーバーを起動してブラウザで動作確認**

```bash
python3 tools_lp_editor.py &
sleep 2
curl -s http://localhost:8765/ | head -5
curl -s http://localhost:8765/content | python3 -c "import sys,json; d=json.load(sys.stdin); print('media' in d, 'headline' in d)"
```

期待:
```
<!DOCTYPE html>
True True
```

確認後、バックグラウンドのサーバーを終了: `kill %1`

- [ ] **Step 4: `/save` エンドポイントを確認**

```bash
python3 tools_lp_editor.py &
sleep 1
# 現在の content.json を読んでそのまま POST
curl -s -X POST http://localhost:8765/save \
  -H "Content-Type: application/json" \
  -d "$(cat docs/content.json)"
kill %1
```

期待: `{"status": "ok", "message": "保存完了"}`

- [ ] **Step 5: 全テストが引き続き通ることを確認**

```bash
python3 -m pytest tests/test_lp.py -v
```

期待: 24 テスト全 PASS

- [ ] **Step 6: コミット**

```bash
git add tools_lp_editor.py
git commit -m "feat: add local LP editor server with Pexels search on port 8765"
```

---

## Self-Review Checklist

**Spec coverage:**
- ✅ `media` ブロック: `header_video` + 10 セクションの `image` フィールド
- ✅ ヘッダー動画: `<video autoplay muted loop playsinline>` + `hero.svg` フォールバック
- ✅ セクション写真: `<div class="section-image"><img loading="lazy">` / 空なら非表示
- ✅ エディタ起動: `python3 tools_lp_editor.py` → `http://localhost:8765` ブラウザ自動オープン
- ✅ Pexels 検索: `GET /pexels?q=<query>&type=<video|photo>` → サムネイル表示 → URL 入力
- ✅ 保存: `POST /save` → `docs/content.json` 更新 + `write_lp()` 実行
- ✅ デプロイ: `POST /deploy` → `bash docs/deploy.sh`
- ✅ Python stdlib のみ（Flask なし）
- ✅ 5 個の新規メディアテスト追加
- ✅ `CUBOCCI STUDIO` 非表示・カラー固定は既存テストが担保

**Placeholder scan:** なし（全ステップにコードあり）

**Type consistency:** `_section_image(url: str) -> str` — Task 1 Step 6 で定義し、Step 8 で使用 ✅
