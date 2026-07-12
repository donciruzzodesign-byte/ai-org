# 動画パイプライン画像入力機能 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 動画パイプラインに、手持ち写真の素材利用（①）・参考画像による生成（②）・画像解析(vision)（③）の3機能を、動画エージェント用ツールとして追加する。

**Architecture:** すべて `tools_video.py` にツール関数として実装し、`VIDEO_TOOL_DEFINITIONS`（Claude に渡すツール定義）と `execute_video_tool`（ディスパッチャ）に登録する。画像解析は `analyze_image` が内部で Claude vision を呼ぶ「ツール化」方式（A案）。既存の tool 駆動アーキテクチャ（`run_video_agent`）は無改修。`generate_ae_script` は既に `images/scene_NN.png` を読むため、写真は同名で配置すれば下流は無改修で流れる。

**Tech Stack:** Python 3, anthropic SDK（vision）, OpenAI Images API（gpt-image-1 generations/edits）, Pillow（画像正規化）, requests, pytest（既存テストは API をモック）。

## Global Constraints

- ツール関数は例外を投げず、成功／エラー／スキップを**日本語メッセージ文字列**で返す（既存 `tools_video.py` の規約）。
- API キー未設定時は `"<KEY名> が未設定のためスキップ"` を返す。
- シーン番号は2桁ゼロ埋め（`scene_{n:02d}.png`）。
- 生成画像サイズは `1536x1024`。
- テストは `tests/test_tools_video.py` に追記し、外部 API（`requests`・anthropic クライアント）を必ずモックする。`tmp_path` を使う。
- 後方互換：`my_photos/` が無い／空なら現行と同一挙動（全シーン AI 生成）。
- Vision モデル定数：`VISION_MODEL = "claude-sonnet-4-6"`（`runner.MODEL` と同一値）。

---

### Task 1: 画像解析ツール `analyze_image`（機能③の中核）

**Files:**
- Modify: `tools_video.py`（先頭 import に `import base64` は関数内既存だが `import anthropic` を追加、`VISION_MODEL` 定数追加、`analyze_image` 関数追加、`VIDEO_TOOL_DEFINITIONS` に定義追加、`execute_video_tool` に分岐追加）
- Test: `tests/test_tools_video.py`

**Interfaces:**
- Produces:
  - `analyze_image(image_path: str, question: str) -> str` — 画像を Claude vision に送り `question` への回答テキストを返す。キー未設定・ファイル無し・API 失敗時はエラー文字列。
  - `VISION_MODEL: str`
  - ヘルパー `_load_image_b64(path) -> str`, `_guess_media_type(path) -> str`

- [ ] **Step 1: 失敗するテストを書く**

`tests/test_tools_video.py` の末尾に追記：

```python
from tools_video import analyze_image


def test_analyze_image_skips_when_no_key(monkeypatch, tmp_path):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    img = tmp_path / "x.png"
    img.write_bytes(b"fake")
    result = analyze_image(str(img), "何が写っていますか")
    assert "未設定" in result


def test_analyze_image_returns_error_when_file_missing(monkeypatch, tmp_path):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    result = analyze_image(str(tmp_path / "nope.png"), "説明して")
    assert "見つかりません" in result


def test_analyze_image_returns_vision_text(monkeypatch, tmp_path):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    img = tmp_path / "barolo.png"
    img.write_bytes(b"fake-png")

    text_block = MagicMock()
    text_block.text = "バローロの瓶が写っています"
    resp = MagicMock()
    resp.content = [text_block]
    mock_client = MagicMock()
    mock_client.messages.create.return_value = resp

    with patch("tools_video.anthropic.Anthropic", return_value=mock_client):
        result = analyze_image(str(img), "何が写っていますか")

    assert result == "バローロの瓶が写っています"
    sent = mock_client.messages.create.call_args[1]
    content = sent["messages"][0]["content"]
    assert content[0]["type"] == "image"
    assert content[0]["source"]["media_type"] == "image/png"
    assert content[1]["text"] == "何が写っていますか"
```

- [ ] **Step 2: テストが失敗することを確認**

Run: `python3 -m pytest tests/test_tools_video.py -k analyze_image -v`
Expected: FAIL（`ImportError: cannot import name 'analyze_image'`）

- [ ] **Step 3: 最小実装**

`tools_video.py` の先頭 import を更新：

```python
import os
import json
import base64
import requests
import anthropic
from typing import Optional
```

`_ensure_dir` の直後に定数とヘルパー・関数を追加：

```python
VISION_MODEL = "claude-sonnet-4-6"

_MEDIA_TYPES = {
    ".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
    ".webp": "image/webp", ".gif": "image/gif",
}


def _guess_media_type(path: str) -> str:
    return _MEDIA_TYPES.get(os.path.splitext(path)[1].lower(), "image/jpeg")


def _load_image_b64(path: str) -> str:
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode()


def analyze_image(image_path: str, question: str) -> str:
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        return "ANTHROPIC_API_KEY が未設定のためスキップ"
    if not os.path.exists(image_path):
        return f"画像が見つかりません: {image_path}"
    try:
        client = anthropic.Anthropic(api_key=api_key)
        resp = client.messages.create(
            model=VISION_MODEL,
            max_tokens=1024,
            messages=[{
                "role": "user",
                "content": [
                    {"type": "image", "source": {
                        "type": "base64",
                        "media_type": _guess_media_type(image_path),
                        "data": _load_image_b64(image_path),
                    }},
                    {"type": "text", "text": question},
                ],
            }],
        )
        return resp.content[0].text
    except Exception as e:
        return f"画像解析エラー: {e}"
```

`VIDEO_TOOL_DEFINITIONS` リスト（`save_timeline` の定義の後、閉じ括弧 `]` の前）に追加：

```python
    ,{
        "name": "analyze_image",
        "description": "画像をClaude visionで解析し、質問に答えます。ラベル読み取り・シーン適合判定・キャプション生成・品質チェックに使えます。",
        "input_schema": {
            "type": "object",
            "properties": {
                "image_path": {"type": "string", "description": "解析する画像のパス（絶対、またはoutput_dir/相対）"},
                "question": {"type": "string", "description": "画像について尋ねたいこと（日本語可）"}
            },
            "required": ["image_path", "question"]
        }
    }
```

`execute_video_tool` に分岐を追加（`save_timeline` 分岐の後、`return f"不明なツール` の前）：

```python
    elif name == "analyze_image":
        return analyze_image(inputs["image_path"], inputs["question"])
```

- [ ] **Step 4: テストが通ることを確認**

Run: `python3 -m pytest tests/test_tools_video.py -k analyze_image -v`
Expected: PASS（3件）

- [ ] **Step 5: コミット**

```bash
git add tools_video.py tests/test_tools_video.py
git commit -m "feat: 画像解析ツール analyze_image を追加（Claude vision）

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 2: 写真一括スキャンツール `scan_photos`（機能①＋③）

**Files:**
- Modify: `tools_video.py`（`scan_photos` 追加、定義・ディスパッチ登録）
- Test: `tests/test_tools_video.py`

**Interfaces:**
- Consumes: `analyze_image`（Task 1）
- Produces: `scan_photos(output_dir: str) -> str` — `output_dir/my_photos/` の各画像を解析し `[{"file": ..., "analysis": ...}, ...]` の JSON 文字列を返す。フォルダ無し／空なら `"[]"`。

- [ ] **Step 1: 失敗するテストを書く**

`tests/test_tools_video.py` 末尾に追記：

```python
from tools_video import scan_photos


def test_scan_photos_returns_empty_when_no_folder(tmp_path):
    result = scan_photos(str(tmp_path))
    assert result == "[]"


def test_scan_photos_analyzes_each_photo(tmp_path):
    photos = tmp_path / "my_photos"
    photos.mkdir()
    (photos / "barolo.jpg").write_bytes(b"a")
    (photos / "vineyard.png").write_bytes(b"b")

    with patch("tools_video.analyze_image", return_value="解析結果") as mock_analyze:
        result = scan_photos(str(tmp_path))

    data = json.loads(result)
    assert len(data) == 2
    files = {d["file"] for d in data}
    assert files == {"barolo.jpg", "vineyard.png"}
    assert all(d["analysis"] == "解析結果" for d in data)
    assert mock_analyze.call_count == 2


def test_scan_photos_ignores_non_images(tmp_path):
    photos = tmp_path / "my_photos"
    photos.mkdir()
    (photos / "note.txt").write_text("x")
    (photos / "wine.jpg").write_bytes(b"a")

    with patch("tools_video.analyze_image", return_value="ok"):
        result = scan_photos(str(tmp_path))

    data = json.loads(result)
    assert len(data) == 1
    assert data[0]["file"] == "wine.jpg"
```

- [ ] **Step 2: テストが失敗することを確認**

Run: `python3 -m pytest tests/test_tools_video.py -k scan_photos -v`
Expected: FAIL（`cannot import name 'scan_photos'`）

- [ ] **Step 3: 最小実装**

`analyze_image` の後に追加：

```python
_PHOTO_EXTS = (".png", ".jpg", ".jpeg", ".webp", ".gif")

_SCAN_QUESTION = (
    "この画像について、(1)何が写っているか (2)ラベルやパッケージに読める文字があればその内容 "
    "(3)10分動画のどんなシーンに向くか、を簡潔にまとめてください。"
)


def scan_photos(output_dir: str) -> str:
    photos_dir = os.path.join(output_dir, "my_photos")
    if not os.path.isdir(photos_dir):
        return "[]"
    results = []
    for name in sorted(os.listdir(photos_dir)):
        if not name.lower().endswith(_PHOTO_EXTS):
            continue
        path = os.path.join(photos_dir, name)
        results.append({"file": name, "analysis": analyze_image(path, _SCAN_QUESTION)})
    return json.dumps(results, ensure_ascii=False)
```

`VIDEO_TOOL_DEFINITIONS` に追加（`analyze_image` 定義の後）：

```python
    ,{
        "name": "scan_photos",
        "description": "output_dir/my_photos/ 内のオーナー手持ち写真を一括で解析し、各写真の内容・ラベル・推奨シーンをJSONで返します。シーン割当の判断に使います。",
        "input_schema": {
            "type": "object",
            "properties": {
                "output_dir": {"type": "string", "description": "出力先ディレクトリ（my_photos の親）"}
            },
            "required": ["output_dir"]
        }
    }
```

`execute_video_tool` に追加：

```python
    elif name == "scan_photos":
        return scan_photos(inputs["output_dir"])
```

- [ ] **Step 4: テストが通ることを確認**

Run: `python3 -m pytest tests/test_tools_video.py -k scan_photos -v`
Expected: PASS（3件）

- [ ] **Step 5: コミット**

```bash
git add tools_video.py tests/test_tools_video.py
git commit -m "feat: 手持ち写真一括スキャンツール scan_photos を追加

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 3: 写真配置ツール `assign_photo`（機能①の組み込み）

**Files:**
- Modify: `tools_video.py`（`from PIL import Image` 追加、`_crop_resize`・`assign_photo` 追加、定義・ディスパッチ登録）
- Modify: `requirements.txt`（`Pillow>=10.0.0` 追加）
- Test: `tests/test_tools_video.py`

**Interfaces:**
- Produces:
  - `assign_photo(photo: str, scene_number: int, output_dir: str) -> str` — `output_dir/my_photos/<photo>` を 1536×1024 に正規化し `output_dir/images/scene_{NN:02d}.png` として保存。
  - `_crop_resize(img, target_w, target_h) -> Image`

- [ ] **Step 1: 失敗するテストを書く**

`tests/test_tools_video.py` 末尾に追記：

```python
from tools_video import assign_photo
from PIL import Image


def _make_photo(path, size=(4000, 2000)):
    Image.new("RGB", size, (120, 40, 40)).save(path)


def test_assign_photo_missing_source(tmp_path):
    result = assign_photo("nope.jpg", 1, str(tmp_path))
    assert "見つかりません" in result


def test_assign_photo_creates_normalized_png(tmp_path):
    photos = tmp_path / "my_photos"
    photos.mkdir()
    _make_photo(photos / "barolo.jpg", size=(4000, 2000))

    result = assign_photo("barolo.jpg", 3, str(tmp_path))

    assert "scene_03.png" in result
    out = tmp_path / "images" / "scene_03.png"
    assert out.exists()
    with Image.open(out) as im:
        assert im.size == (1536, 1024)


def test_assign_photo_handles_portrait_source(tmp_path):
    photos = tmp_path / "my_photos"
    photos.mkdir()
    _make_photo(photos / "tall.jpg", size=(1000, 3000))

    assign_photo("tall.jpg", 1, str(tmp_path))

    with Image.open(tmp_path / "images" / "scene_01.png") as im:
        assert im.size == (1536, 1024)
```

- [ ] **Step 2: テストが失敗することを確認**

Run: `python3 -m pytest tests/test_tools_video.py -k assign_photo -v`
Expected: FAIL（`cannot import name 'assign_photo'`）

- [ ] **Step 3: 最小実装**

`tools_video.py` の import に追加：

```python
from PIL import Image
```

`scan_photos` の後に追加：

```python
def _crop_resize(img: "Image.Image", target_w: int, target_h: int) -> "Image.Image":
    src_w, src_h = img.size
    target_ratio = target_w / target_h
    src_ratio = src_w / src_h
    if src_ratio > target_ratio:
        new_w = int(src_h * target_ratio)
        left = (src_w - new_w) // 2
        img = img.crop((left, 0, left + new_w, src_h))
    else:
        new_h = int(src_w / target_ratio)
        top = (src_h - new_h) // 2
        img = img.crop((0, top, src_w, top + new_h))
    return img.resize((target_w, target_h), Image.LANCZOS)


def assign_photo(photo: str, scene_number: int, output_dir: str) -> str:
    src = os.path.join(output_dir, "my_photos", photo)
    if not os.path.exists(src):
        return f"写真が見つかりません: {src}"
    images_dir = os.path.join(output_dir, "images")
    _ensure_dir(images_dir)
    dst = os.path.join(images_dir, f"scene_{scene_number:02d}.png")
    try:
        with Image.open(src) as im:
            im = im.convert("RGB")
            im = _crop_resize(im, 1536, 1024)
            im.save(dst, "PNG")
        return f"写真を配置: {dst} (元: {photo})"
    except Exception as e:
        return f"写真配置エラー: {e}"
```

`VIDEO_TOOL_DEFINITIONS` に追加（`scan_photos` 定義の後）：

```python
    ,{
        "name": "assign_photo",
        "description": "my_photos内の写真を1536x1024に正規化し、指定シーンの画像(images/scene_NN.png)として配置します。AI生成の代わりに実写を使う場合に呼びます。",
        "input_schema": {
            "type": "object",
            "properties": {
                "photo": {"type": "string", "description": "my_photos内のファイル名"},
                "scene_number": {"type": "integer", "description": "配置先シーン番号（1始まり）"},
                "output_dir": {"type": "string", "description": "出力先ディレクトリ"}
            },
            "required": ["photo", "scene_number", "output_dir"]
        }
    }
```

`execute_video_tool` に追加：

```python
    elif name == "assign_photo":
        return assign_photo(inputs["photo"], inputs["scene_number"], inputs["output_dir"])
```

`requirements.txt` に1行追加（`cairosvg>=2.7.0` の後）：

```
Pillow>=10.0.0
```

- [ ] **Step 4: テストが通ることを確認**

Run: `python3 -m pytest tests/test_tools_video.py -k assign_photo -v`
Expected: PASS（3件）

- [ ] **Step 5: コミット**

```bash
git add tools_video.py tests/test_tools_video.py requirements.txt
git commit -m "feat: 手持ち写真配置ツール assign_photo を追加（Pillowで正規化）

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 4: 参考画像対応 `generate_scene_image(reference_image=...)`（機能②）

**Files:**
- Modify: `tools_video.py`（`generate_scene_image` に `reference_image` 引数追加、`VIDEO_TOOL_DEFINITIONS` の該当定義更新、`execute_video_tool` の該当分岐更新）
- Test: `tests/test_tools_video.py`

**Interfaces:**
- Changed: `generate_scene_image(scene_description: str, scene_number: int, output_dir: str, reference_image: Optional[str] = None) -> str` — `reference_image` 指定時は OpenAI `/images/edits`（multipart）を使い、未指定時は現行の `/images/generations`。参考画像パスは絶対／`output_dir` 相対／`my_photos/` 相対の順に解決。

- [ ] **Step 1: 失敗するテストを書く**

`tests/test_tools_video.py` 末尾に追記：

```python
def test_generate_scene_image_uses_edits_endpoint_with_reference(monkeypatch, tmp_path):
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    photos = tmp_path / "my_photos"
    photos.mkdir()
    Image.new("RGB", (100, 100), (0, 0, 0)).save(photos / "ref.png")

    gen_resp = MagicMock()
    gen_resp.status_code = 200
    gen_resp.json.return_value = {"data": [{"b64_json": base64.b64encode(b"png").decode()}]}

    with patch("tools_video.requests.post", return_value=gen_resp) as mock_post:
        result = generate_scene_image(
            "Barolo bottle on table", 2, str(tmp_path), reference_image="ref.png"
        )

    assert "scene_02.png" in result
    url = mock_post.call_args[0][0]
    assert "edits" in url
    assert "files" in mock_post.call_args[1]
    assert (tmp_path / "images" / "scene_02.png").exists()


def test_generate_scene_image_reference_not_found(monkeypatch, tmp_path):
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    result = generate_scene_image("x", 1, str(tmp_path), reference_image="missing.png")
    assert "見つかりません" in result


def test_generate_scene_image_no_reference_uses_generations(monkeypatch, tmp_path):
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    gen_resp = MagicMock()
    gen_resp.status_code = 200
    gen_resp.json.return_value = {"data": [{"b64_json": base64.b64encode(b"png").decode()}]}

    with patch("tools_video.requests.post", return_value=gen_resp) as mock_post:
        generate_scene_image("vineyard", 1, str(tmp_path))

    assert "generations" in mock_post.call_args[0][0]
```

（`import base64` と `from PIL import Image` は Task 1・3 で既にテストファイル先頭付近に追加済み。未追加なら追記する。）

- [ ] **Step 2: テストが失敗することを確認**

Run: `python3 -m pytest tests/test_tools_video.py -k "reference or generations" -v`
Expected: FAIL（`reference_image` 引数未対応 / edits 未実装）

- [ ] **Step 3: 最小実装**

`generate_scene_image` を差し替え：

```python
def _resolve_reference(reference_image: str, output_dir: str) -> Optional[str]:
    if os.path.isabs(reference_image) and os.path.exists(reference_image):
        return reference_image
    for cand in (
        os.path.join(output_dir, reference_image),
        os.path.join(output_dir, "my_photos", reference_image),
    ):
        if os.path.exists(cand):
            return cand
    return None


def generate_scene_image(scene_description: str, scene_number: int, output_dir: str,
                         reference_image: Optional[str] = None) -> str:
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        return "OPENAI_API_KEY が未設定のためスキップ"

    images_dir = os.path.join(output_dir, "images")
    _ensure_dir(images_dir)
    image_path = os.path.join(images_dir, f"scene_{scene_number:02d}.png")

    if os.path.exists(image_path):
        return f"スキップ（既存）: {image_path}"

    prompt = SCENE_IMAGE_STYLE + scene_description
    headers = {"Authorization": f"Bearer {api_key}"}

    try:
        if reference_image:
            ref_path = _resolve_reference(reference_image, output_dir)
            if not ref_path:
                return f"参考画像が見つかりません: {reference_image}"
            url = "https://api.openai.com/v1/images/edits"
            with open(ref_path, "rb") as rf:
                files = {"image": (os.path.basename(ref_path), rf, "image/png")}
                data = {"model": "gpt-image-1", "prompt": prompt, "size": "1536x1024", "n": "1"}
                resp = requests.post(url, headers=headers, files=files, data=data, timeout=180)
        else:
            url = "https://api.openai.com/v1/images/generations"
            headers["Content-Type"] = "application/json"
            payload = {"model": "gpt-image-1", "prompt": prompt, "size": "1536x1024", "n": 1}
            resp = requests.post(url, headers=headers, json=payload, timeout=120)

        if resp.status_code != 200:
            return f"画像生成エラー (scene {scene_number}): {resp.status_code} {resp.text[:200]}"
        b64_data = resp.json()["data"][0]["b64_json"]
        with open(image_path, "wb") as f:
            f.write(base64.b64decode(b64_data))
        return f"画像保存: {image_path}"
    except Exception as e:
        return f"画像生成エラー (scene {scene_number}): {e}"
```

（`import base64` は Task 1 でモジュール先頭に追加済みのため、関数内の `import base64` は不要。）

`VIDEO_TOOL_DEFINITIONS` の `generate_scene_image` 定義の `properties` に追加、`description` を更新：

```python
        "description": "シーン説明からgpt-image-1で画像(1536x1024)を生成して保存します。reference_image指定時はその画像を参考に生成（実物商品の登場・スタイル統一・不足補完）。",
        "input_schema": {
            "type": "object",
            "properties": {
                "scene_description": {"type": "string", "description": "シーンの説明（英語推奨）"},
                "scene_number": {"type": "integer", "description": "シーン番号（1始まり）"},
                "output_dir": {"type": "string", "description": "保存先ディレクトリ"},
                "reference_image": {"type": "string", "description": "任意。参考画像パス（絶対／output_dir相対／my_photos相対）"}
            },
            "required": ["scene_description", "scene_number", "output_dir"]
        }
```

`execute_video_tool` の `generate_scene_image` 分岐を更新：

```python
    elif name == "generate_scene_image":
        return generate_scene_image(
            inputs["scene_description"], inputs["scene_number"], inputs["output_dir"],
            inputs.get("reference_image"),
        )
```

- [ ] **Step 4: テストが通ることを確認**

Run: `python3 -m pytest tests/test_tools_video.py -v`
Expected: PASS（既存＋新規すべて。既存の generations 系テストも維持）

- [ ] **Step 5: コミット**

```bash
git add tools_video.py tests/test_tools_video.py
git commit -m "feat: generate_scene_image に参考画像(reference_image)対応を追加

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 5: エージェント手順とドキュメント更新

**Files:**
- Modify: `agents/video.txt`（画像入力ワークフローの手順を追記）
- Modify: `CLAUDE.md`（動画パイプライン節に `my_photos/` と新ツールを追記）

**Interfaces:**
- Consumes: Task 1–4 の全ツール（`scan_photos`, `assign_photo`, `generate_scene_image(reference_image)`, `analyze_image`）
- Produces: なし（ドキュメント／プロンプトのみ）

- [ ] **Step 1: `agents/video.txt` に手順を追記**

`agents/video.txt` を開き、既存の作業手順の記述に続けて、以下の段落を追記する（既存の文体に合わせる）：

```
【手持ち写真の活用（重要）】
1. まず scan_photos で output_dir/my_photos/ の写真を確認する。写真がある場合は実写を優先する。
2. 台本の各シーンに合う写真を選び、assign_photo で該当シーンに配置する（AI生成より優先）。
3. 写真がないシーンだけ generate_scene_image でAI生成する。動画全体の見た目を統一したい場合は、代表的な手持ち写真を reference_image に渡す。
4. 配置・生成した各画像を analyze_image で品質チェックする（変な歪み・不適切な内容がないか）。問題があれば再生成する。
5. 必要に応じて analyze_image でラベルを読み取り、timeline のキャプションに反映する。
my_photos/ が空または無い場合は、従来どおり全シーンをAI生成すること。
```

- [ ] **Step 2: `CLAUDE.md` の動画パイプライン節を更新**

`## 動画パイプライン（tools_video.py）` のファイル表の直前または直後に、以下を追記：

```markdown
### 手持ち写真の利用（任意）
`output/YYYY-MM-DD-{wine|coffee}/my_photos/` に写真を置くと、動画エージェントが実写を優先してシーンに配置する（`scan_photos` で解析 → `assign_photo` で配置）。写真がないシーンのみ AI 生成。`my_photos/` が空・無い場合は従来どおり全シーン AI 生成。

追加ツール: `analyze_image`（画像をClaude visionで解析）, `scan_photos`（my_photos一括解析）, `assign_photo`（写真をscene_NN.pngに正規化配置）, `generate_scene_image` の `reference_image`（参考画像で生成）。
```

- [ ] **Step 3: 全テストが通ることを確認（回帰確認）**

Run: `python3 -m pytest tests/test_tools_video.py tests/test_runner.py -v`
Expected: PASS（全件。ドキュメント変更なので既存テストに影響なし）

- [ ] **Step 4: コミット**

```bash
git add agents/video.txt CLAUDE.md
git commit -m "docs: 動画エージェントの手持ち写真ワークフローとCLAUDE.mdを更新

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Self-Review

**Spec coverage:**
- 機能①（手持ち写真を素材に）→ Task 2（scan_photos）+ Task 3（assign_photo）+ Task 5（手順）✓
- 機能②（参考画像で生成）→ Task 4（reference_image）✓
- 機能③（画像解析）→ Task 1（analyze_image）。4用途（ラベル読み取り・シーン割当・キャプション・品質チェック）は `question` 出し分けと Task 5 手順で担保 ✓
- 後方互換 → Task 2（フォルダ無し→"[]"）、Task 4（reference なし→現行 generations）、Task 5（空なら全AI生成）✓
- テスト → 各タスクに TDD ステップあり ✓
- Pillow 依存の明記 → Task 3 で requirements.txt 追記 ✓

**Placeholder scan:** プレースホルダなし。全ステップに実コード／実コマンドあり。

**Type consistency:** `analyze_image(image_path, question)`, `scan_photos(output_dir)`, `assign_photo(photo, scene_number, output_dir)`, `generate_scene_image(scene_description, scene_number, output_dir, reference_image=None)`, `_crop_resize`, `_resolve_reference` — 全タスクで名称・引数一貫。`VISION_MODEL` は Global Constraints と Task 1 で一致。
