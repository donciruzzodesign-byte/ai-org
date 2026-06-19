# 動画素材自動生成パイプライン 実装計画

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `creator` エージェントが生成した台本から、After Effects 用の動画素材一式（ナレーション音声・シーン画像・B-roll動画・タイムライン定義）を自動生成するパイプラインを構築する。

**Architecture:** `tools_video.py` に ElevenLabs / DALL-E 3 / Pexels の API ラッパーを実装し、`agents/video.txt` の video エージェントが台本を解析してツールを順番に呼び出す。`runner.py` に火曜 11:00 / 12:00 のスケジュールタスクを追加し、既存の `run_agent()` と同パターンで `run_video_agent()` を実行する。

**Tech Stack:** Python 3.x, requests（既存）, ElevenLabs TTS API, OpenAI DALL-E 3 API, Pexels Videos API, pytest（既存）

---

## ファイル構成

| 操作 | ファイル | 役割 |
|------|---------|------|
| 新規作成 | `tools_video.py` | 動画ツール実装 + `VIDEO_TOOL_DEFINITIONS` + `execute_video_tool()` |
| 新規作成 | `agents/video.txt` | video エージェントのシステムプロンプト |
| 新規作成 | `.claude/agents/video.md` | `@video` Claude Code エージェント定義 |
| 新規作成 | `tests/test_tools_video.py` | `tools_video.py` のテスト |
| 変更 | `runner.py` | `run_video_agent()` + タスク関数 2 本 + スケジュール 2 エントリ追加 |

出力先: `output/YYYY-MM-DD-{wine|coffee}/`（実行時に自動作成）

---

## Task 1: `tools_video.py` — `generate_narration()`

**Files:**
- Create: `tools_video.py`
- Create: `tests/test_tools_video.py`

- [ ] **Step 1: テスト作成**

`tests/test_tools_video.py` を新規作成:

```python
import os
import sys
import json
import pytest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from unittest.mock import patch, MagicMock
import tempfile
from tools_video import generate_narration


def test_generate_narration_skips_when_no_key(monkeypatch, tmp_path):
    monkeypatch.delenv("ELEVENLABS_API_KEY", raising=False)
    result = generate_narration("テスト台本", str(tmp_path))
    assert "未設定" in result


def test_generate_narration_saves_mp3(monkeypatch, tmp_path):
    monkeypatch.setenv("ELEVENLABS_API_KEY", "test-key")
    monkeypatch.setenv("ELEVENLABS_VOICE_ID", "voice-123")

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.content = b"fake-audio-data"

    with patch("tools_video.requests.post", return_value=mock_resp):
        result = generate_narration("テスト台本", str(tmp_path))

    assert "narration.mp3" in result
    audio_path = tmp_path / "audio" / "narration.mp3"
    assert audio_path.exists()
    assert audio_path.read_bytes() == b"fake-audio-data"


def test_generate_narration_skips_existing_file(monkeypatch, tmp_path):
    monkeypatch.setenv("ELEVENLABS_API_KEY", "test-key")
    audio_dir = tmp_path / "audio"
    audio_dir.mkdir()
    (audio_dir / "narration.mp3").write_bytes(b"existing")

    with patch("tools_video.requests.post") as mock_post:
        result = generate_narration("台本", str(tmp_path))

    mock_post.assert_not_called()
    assert "スキップ" in result


def test_generate_narration_returns_error_on_api_failure(monkeypatch, tmp_path):
    monkeypatch.setenv("ELEVENLABS_API_KEY", "test-key")

    mock_resp = MagicMock()
    mock_resp.status_code = 401
    mock_resp.text = "Unauthorized"

    with patch("tools_video.requests.post", return_value=mock_resp):
        result = generate_narration("台本", str(tmp_path))

    assert "エラー" in result
```

- [ ] **Step 2: テストを実行して失敗を確認**

```bash
cd ~/ai-org && python -m pytest tests/test_tools_video.py -v
```

Expected: `ModuleNotFoundError: No module named 'tools_video'`

- [ ] **Step 3: `generate_narration()` を実装**

`tools_video.py` を新規作成:

```python
import os
import json
import requests
from typing import Optional


VIDEO_TOOL_DEFINITIONS = []  # Task 4 で完成させる


def _ensure_dir(path: str) -> None:
    os.makedirs(path, exist_ok=True)


def generate_narration(script_text: str, output_dir: str) -> str:
    api_key = os.environ.get("ELEVENLABS_API_KEY")
    if not api_key:
        return "ELEVENLABS_API_KEY が未設定のためスキップ"

    audio_dir = os.path.join(output_dir, "audio")
    _ensure_dir(audio_dir)
    audio_path = os.path.join(audio_dir, "narration.mp3")

    if os.path.exists(audio_path):
        return f"スキップ（既存）: {audio_path}"

    voice_id = os.environ.get("ELEVENLABS_VOICE_ID", "21m00Tcm4TlvDq8ikWAM")
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
    headers = {"xi-api-key": api_key, "Content-Type": "application/json"}
    payload = {
        "text": script_text,
        "model_id": "eleven_multilingual_v2",
        "voice_settings": {"stability": 0.5, "similarity_boost": 0.75},
    }

    try:
        resp = requests.post(url, headers=headers, json=payload, timeout=120)
        if resp.status_code != 200:
            return f"ナレーション生成エラー: {resp.status_code} {resp.text[:200]}"
        with open(audio_path, "wb") as f:
            f.write(resp.content)
        return f"ナレーション保存: {audio_path}"
    except Exception as e:
        return f"ナレーション生成エラー: {e}"
```

- [ ] **Step 4: テストを実行してパスを確認**

```bash
cd ~/ai-org && python -m pytest tests/test_tools_video.py -v
```

Expected: 4 tests PASSED

- [ ] **Step 5: コミット**

```bash
cd ~/ai-org && git add tools_video.py tests/test_tools_video.py
git commit -m "feat: add generate_narration tool (ElevenLabs TTS)"
```

---

## Task 2: `tools_video.py` — `generate_scene_image()`

**Files:**
- Modify: `tools_video.py`
- Modify: `tests/test_tools_video.py`

- [ ] **Step 1: テスト追加**

`tests/test_tools_video.py` に追記:

```python
from tools_video import generate_scene_image


def test_generate_scene_image_skips_when_no_key(monkeypatch, tmp_path):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    result = generate_scene_image("a bottle of Barolo wine", 1, str(tmp_path))
    assert "未設定" in result


def test_generate_scene_image_saves_png(monkeypatch, tmp_path):
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")

    gen_resp = MagicMock()
    gen_resp.status_code = 200
    gen_resp.json.return_value = {"data": [{"url": "https://example.com/img.png"}]}

    img_resp = MagicMock()
    img_resp.content = b"fake-png-data"

    with patch("tools_video.requests.post", return_value=gen_resp), \
         patch("tools_video.requests.get", return_value=img_resp):
        result = generate_scene_image("a bottle of Barolo wine", 1, str(tmp_path))

    assert "scene_01.png" in result
    img_path = tmp_path / "images" / "scene_01.png"
    assert img_path.exists()
    assert img_path.read_bytes() == b"fake-png-data"


def test_generate_scene_image_zero_pads_number(monkeypatch, tmp_path):
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")

    gen_resp = MagicMock()
    gen_resp.status_code = 200
    gen_resp.json.return_value = {"data": [{"url": "https://example.com/img.png"}]}
    img_resp = MagicMock()
    img_resp.content = b"data"

    with patch("tools_video.requests.post", return_value=gen_resp), \
         patch("tools_video.requests.get", return_value=img_resp):
        generate_scene_image("vineyard at sunset", 9, str(tmp_path))

    assert (tmp_path / "images" / "scene_09.png").exists()


def test_generate_scene_image_skips_existing_file(monkeypatch, tmp_path):
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    images_dir = tmp_path / "images"
    images_dir.mkdir()
    (images_dir / "scene_01.png").write_bytes(b"existing")

    with patch("tools_video.requests.post") as mock_post:
        result = generate_scene_image("wine", 1, str(tmp_path))

    mock_post.assert_not_called()
    assert "スキップ" in result


def test_generate_scene_image_prepends_style_prefix(monkeypatch, tmp_path):
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")

    gen_resp = MagicMock()
    gen_resp.status_code = 200
    gen_resp.json.return_value = {"data": [{"url": "https://example.com/img.png"}]}
    img_resp = MagicMock()
    img_resp.content = b"data"

    with patch("tools_video.requests.post", return_value=gen_resp) as mock_post, \
         patch("tools_video.requests.get", return_value=img_resp):
        generate_scene_image("Barolo bottle", 1, str(tmp_path))

    sent_prompt = mock_post.call_args[1]["json"]["prompt"]
    assert "High quality" in sent_prompt
    assert "Barolo bottle" in sent_prompt
```

- [ ] **Step 2: テストを実行して失敗を確認**

```bash
cd ~/ai-org && python -m pytest tests/test_tools_video.py::test_generate_scene_image_skips_when_no_key -v
```

Expected: `ImportError` または `AttributeError`（関数未定義）

- [ ] **Step 3: `generate_scene_image()` を実装**

`tools_video.py` に追記:

```python
SCENE_IMAGE_STYLE = (
    "High quality food and travel photography, Italian wine, "
    "warm natural golden light, cinematic, 8k resolution, "
)


def generate_scene_image(scene_description: str, scene_number: int, output_dir: str) -> str:
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        return "OPENAI_API_KEY が未設定のためスキップ"

    images_dir = os.path.join(output_dir, "images")
    _ensure_dir(images_dir)
    image_path = os.path.join(images_dir, f"scene_{scene_number:02d}.png")

    if os.path.exists(image_path):
        return f"スキップ（既存）: {image_path}"

    prompt = SCENE_IMAGE_STYLE + scene_description
    url = "https://api.openai.com/v1/images/generations"
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    payload = {"model": "dall-e-3", "prompt": prompt, "size": "1792x1024", "quality": "hd", "n": 1}

    try:
        resp = requests.post(url, headers=headers, json=payload, timeout=120)
        if resp.status_code != 200:
            return f"画像生成エラー (scene {scene_number}): {resp.status_code} {resp.text[:200]}"
        image_url = resp.json()["data"][0]["url"]
        img_resp = requests.get(image_url, timeout=60)
        with open(image_path, "wb") as f:
            f.write(img_resp.content)
        return f"画像保存: {image_path}"
    except Exception as e:
        return f"画像生成エラー (scene {scene_number}): {e}"
```

- [ ] **Step 4: テストを実行してパスを確認**

```bash
cd ~/ai-org && python -m pytest tests/test_tools_video.py -v
```

Expected: 9 tests PASSED

- [ ] **Step 5: コミット**

```bash
cd ~/ai-org && git add tools_video.py tests/test_tools_video.py
git commit -m "feat: add generate_scene_image tool (DALL-E 3)"
```

---

## Task 3: `tools_video.py` — `fetch_broll()`

**Files:**
- Modify: `tools_video.py`
- Modify: `tests/test_tools_video.py`

- [ ] **Step 1: テスト追加**

`tests/test_tools_video.py` に追記:

```python
from tools_video import fetch_broll


def test_fetch_broll_skips_when_no_key(monkeypatch, tmp_path):
    monkeypatch.delenv("PEXELS_API_KEY", raising=False)
    result = fetch_broll("Italian vineyard", 1, str(tmp_path))
    assert "未設定" in result


def test_fetch_broll_saves_mp4(monkeypatch, tmp_path):
    monkeypatch.setenv("PEXELS_API_KEY", "test-key")

    search_resp = MagicMock()
    search_resp.status_code = 200
    search_resp.json.return_value = {
        "videos": [{
            "video_files": [
                {"link": "https://example.com/hd.mp4", "quality": "hd", "width": 1280, "height": 720}
            ]
        }]
    }

    clip_resp = MagicMock()
    clip_resp.iter_content = MagicMock(return_value=[b"fake-video-data"])

    with patch("tools_video.requests.get", side_effect=[search_resp, clip_resp]):
        result = fetch_broll("Italian vineyard", 1, str(tmp_path))

    assert "broll_01.mp4" in result
    clip_path = tmp_path / "broll" / "broll_01.mp4"
    assert clip_path.exists()


def test_fetch_broll_skips_existing_file(monkeypatch, tmp_path):
    monkeypatch.setenv("PEXELS_API_KEY", "test-key")
    broll_dir = tmp_path / "broll"
    broll_dir.mkdir()
    (broll_dir / "broll_01.mp4").write_bytes(b"existing")

    with patch("tools_video.requests.get") as mock_get:
        result = fetch_broll("wine", 1, str(tmp_path))

    mock_get.assert_not_called()
    assert "スキップ" in result


def test_fetch_broll_returns_message_when_no_videos(monkeypatch, tmp_path):
    monkeypatch.setenv("PEXELS_API_KEY", "test-key")

    search_resp = MagicMock()
    search_resp.status_code = 200
    search_resp.json.return_value = {"videos": []}

    with patch("tools_video.requests.get", return_value=search_resp):
        result = fetch_broll("xyznotfound", 1, str(tmp_path))

    assert "見つかりません" in result
```

- [ ] **Step 2: テストを実行して失敗を確認**

```bash
cd ~/ai-org && python -m pytest tests/test_tools_video.py::test_fetch_broll_skips_when_no_key -v
```

Expected: `ImportError`（関数未定義）

- [ ] **Step 3: `fetch_broll()` を実装**

`tools_video.py` に追記:

```python
def fetch_broll(keyword: str, clip_index: int, output_dir: str) -> str:
    api_key = os.environ.get("PEXELS_API_KEY")
    if not api_key:
        return "PEXELS_API_KEY が未設定のためスキップ"

    broll_dir = os.path.join(output_dir, "broll")
    _ensure_dir(broll_dir)
    clip_path = os.path.join(broll_dir, f"broll_{clip_index:02d}.mp4")

    if os.path.exists(clip_path):
        return f"スキップ（既存）: {clip_path}"

    try:
        search_url = "https://api.pexels.com/videos/search"
        headers = {"Authorization": api_key}
        params = {"query": keyword, "per_page": 5, "orientation": "landscape", "size": "large"}
        resp = requests.get(search_url, headers=headers, params=params, timeout=30)
        if resp.status_code != 200:
            return f"Pexels検索エラー: {resp.status_code}"

        videos = resp.json().get("videos", [])
        if not videos:
            return f"B-roll素材が見つかりません: {keyword}"

        hd_files = [
            f for f in videos[0]["video_files"]
            if f.get("quality") in ("hd", "uhd") and f.get("width", 0) >= 1280
        ]
        file_url = (hd_files or videos[0]["video_files"])[0]["link"]

        clip_resp = requests.get(file_url, timeout=120, stream=True)
        with open(clip_path, "wb") as f:
            for chunk in clip_resp.iter_content(chunk_size=8192):
                f.write(chunk)
        return f"B-roll保存: {clip_path} (キーワード: {keyword})"
    except Exception as e:
        return f"B-roll取得エラー: {e}"
```

- [ ] **Step 4: テストを実行してパスを確認**

```bash
cd ~/ai-org && python -m pytest tests/test_tools_video.py -v
```

Expected: 13 tests PASSED

- [ ] **Step 5: コミット**

```bash
cd ~/ai-org && git add tools_video.py tests/test_tools_video.py
git commit -m "feat: add fetch_broll tool (Pexels API)"
```

---

## Task 4: `tools_video.py` — `save_timeline()` + `VIDEO_TOOL_DEFINITIONS` + `execute_video_tool()`

**Files:**
- Modify: `tools_video.py`
- Modify: `tests/test_tools_video.py`

- [ ] **Step 1: テスト追加**

`tests/test_tools_video.py` に追記:

```python
from tools_video import save_timeline, execute_video_tool


SAMPLE_TIMELINE = {
    "title": "バローロ特集",
    "duration_sec": 600,
    "narration": "audio/narration.mp3",
    "scenes": [
        {
            "id": 1, "in_sec": 0, "out_sec": 60,
            "type": "slide", "image": "images/scene_01.png",
            "broll": "broll/broll_01.mp4",
            "caption": "バローロはなぜ「ワインの王」と呼ばれるのか？",
            "notes": "テロップは画面下部"
        }
    ],
    "reels_highlights": [
        {"id": 1, "in_sec": 45, "out_sec": 75, "reason": "最も印象的なフレーズ"}
    ]
}


def test_save_timeline_creates_json(tmp_path):
    result = save_timeline(SAMPLE_TIMELINE, str(tmp_path))
    assert "timeline.json" in result
    json_path = tmp_path / "timeline.json"
    assert json_path.exists()
    data = json.loads(json_path.read_text(encoding="utf-8"))
    assert data["title"] == "バローロ特集"
    assert len(data["scenes"]) == 1


def test_save_timeline_creates_edit_guide_md(tmp_path):
    save_timeline(SAMPLE_TIMELINE, str(tmp_path))
    guide_path = tmp_path / "edit_guide.md"
    assert guide_path.exists()
    content = guide_path.read_text(encoding="utf-8")
    assert "バローロ特集" in content
    assert "After Effects" in content
    assert "Reels" in content
    assert "0s〜60s" in content


def test_execute_video_tool_dispatches_generate_narration(monkeypatch, tmp_path):
    monkeypatch.delenv("ELEVENLABS_API_KEY", raising=False)
    result = execute_video_tool("generate_narration", {
        "script_text": "テスト", "output_dir": str(tmp_path)
    })
    assert "未設定" in result


def test_execute_video_tool_dispatches_generate_scene_image(monkeypatch, tmp_path):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    result = execute_video_tool("generate_scene_image", {
        "scene_description": "wine", "scene_number": 1, "output_dir": str(tmp_path)
    })
    assert "未設定" in result


def test_execute_video_tool_dispatches_fetch_broll(monkeypatch, tmp_path):
    monkeypatch.delenv("PEXELS_API_KEY", raising=False)
    result = execute_video_tool("fetch_broll", {
        "keyword": "wine", "clip_index": 1, "output_dir": str(tmp_path)
    })
    assert "未設定" in result


def test_execute_video_tool_dispatches_save_timeline(tmp_path):
    result = execute_video_tool("save_timeline", {
        "timeline": SAMPLE_TIMELINE, "output_dir": str(tmp_path)
    })
    assert "timeline.json" in result


def test_execute_video_tool_returns_error_for_unknown(tmp_path):
    result = execute_video_tool("unknown_tool", {})
    assert "不明" in result
```

- [ ] **Step 2: テストを実行して失敗を確認**

```bash
cd ~/ai-org && python -m pytest tests/test_tools_video.py::test_save_timeline_creates_json -v
```

Expected: `ImportError`（関数未定義）

- [ ] **Step 3: `save_timeline()` + `VIDEO_TOOL_DEFINITIONS` + `execute_video_tool()` を実装**

`tools_video.py` に追記し、ファイル冒頭の `VIDEO_TOOL_DEFINITIONS = []` を以下で置き換え:

```python
VIDEO_TOOL_DEFINITIONS = [
    {
        "name": "generate_narration",
        "description": "台本テキストをElevenLabs APIでナレーション音声(.mp3)に変換して保存します。",
        "input_schema": {
            "type": "object",
            "properties": {
                "script_text": {"type": "string", "description": "読み上げる台本テキスト"},
                "output_dir": {"type": "string", "description": "保存先ディレクトリ（例: output/2026-06-20-wine）"}
            },
            "required": ["script_text", "output_dir"]
        }
    },
    {
        "name": "generate_scene_image",
        "description": "シーン説明からDALL-E 3で画像(1792x1024)を生成して保存します。",
        "input_schema": {
            "type": "object",
            "properties": {
                "scene_description": {"type": "string", "description": "シーンの説明（英語推奨）"},
                "scene_number": {"type": "integer", "description": "シーン番号（1始まり）"},
                "output_dir": {"type": "string", "description": "保存先ディレクトリ"}
            },
            "required": ["scene_description", "scene_number", "output_dir"]
        }
    },
    {
        "name": "fetch_broll",
        "description": "Pexels APIでキーワードに合うB-roll動画素材(.mp4)を取得して保存します。",
        "input_schema": {
            "type": "object",
            "properties": {
                "keyword": {"type": "string", "description": "検索キーワード（英語推奨）"},
                "clip_index": {"type": "integer", "description": "クリップ番号（1始まり）"},
                "output_dir": {"type": "string", "description": "保存先ディレクトリ"}
            },
            "required": ["keyword", "clip_index", "output_dir"]
        }
    },
    {
        "name": "save_timeline",
        "description": "タイムラインデータをtimeline.jsonとedit_guide.mdとして保存します。",
        "input_schema": {
            "type": "object",
            "properties": {
                "timeline": {
                    "type": "object",
                    "description": "title, duration_sec, narration, scenes, reels_highlights を含むタイムラインデータ"
                },
                "output_dir": {"type": "string", "description": "保存先ディレクトリ"}
            },
            "required": ["timeline", "output_dir"]
        }
    }
]


def save_timeline(timeline: dict, output_dir: str) -> str:
    try:
        _ensure_dir(output_dir)

        json_path = os.path.join(output_dir, "timeline.json")
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(timeline, f, ensure_ascii=False, indent=2)

        guide_path = os.path.join(output_dir, "edit_guide.md")
        title = timeline.get("title", "動画")
        scenes = timeline.get("scenes", [])
        highlights = timeline.get("reels_highlights", [])
        narration = timeline.get("narration", "audio/narration.mp3")

        lines = [
            f"# 編集ガイド：{title}",
            "",
            "## After Effects への読み込み手順",
            f"1. `{narration}` → オーディオレイヤーに配置（自録音の場合はミュート）",
            "2. `images/` → timeline.json の in_sec/out_sec に従いスライドとして配置",
            "3. `broll/` → 各シーン後半にオーバーレイ（opacity 70%推奨）",
            "",
            "## シーン構成",
        ]
        for s in scenes:
            lines.append(f"- シーン{s['id']} ({s['in_sec']}s〜{s['out_sec']}s): {s.get('caption', '')}")
            if s.get("notes"):
                lines.append(f"  ※ {s['notes']}")

        if highlights:
            lines += ["", "## Instagram Reels ハイライト（縦型クロップ推奨）"]
            for h in highlights:
                lines.append(f"- {h['in_sec']}s〜{h['out_sec']}s: {h.get('reason', '')}")

        with open(guide_path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")

        return f"タイムライン保存: {json_path}, {guide_path}"
    except Exception as e:
        return f"タイムライン保存エラー: {e}"


def execute_video_tool(name: str, inputs: dict) -> str:
    if name == "generate_narration":
        return generate_narration(inputs["script_text"], inputs["output_dir"])
    elif name == "generate_scene_image":
        return generate_scene_image(inputs["scene_description"], inputs["scene_number"], inputs["output_dir"])
    elif name == "fetch_broll":
        return fetch_broll(inputs["keyword"], inputs["clip_index"], inputs["output_dir"])
    elif name == "save_timeline":
        return save_timeline(inputs["timeline"], inputs["output_dir"])
    return f"不明なツール: {name}"
```

- [ ] **Step 4: テストを実行してパスを確認**

```bash
cd ~/ai-org && python -m pytest tests/test_tools_video.py -v
```

Expected: 20 tests PASSED

- [ ] **Step 5: コミット**

```bash
cd ~/ai-org && git add tools_video.py tests/test_tools_video.py
git commit -m "feat: add save_timeline, VIDEO_TOOL_DEFINITIONS, execute_video_tool"
```

---

## Task 5: `agents/video.txt` — video エージェントシステムプロンプト

**Files:**
- Create: `agents/video.txt`

- [ ] **Step 1: ファイル作成**

`agents/video.txt` を作成:

```
あなたはCUBOCCI STUDIOの動画素材生成エージェントです。
クリエイターエージェントが作成した台本を受け取り、After Effects での最終編集に必要な素材一式を自動生成します。

## あなたの役割
台本を解析し、以下の素材を生成して指定フォルダに保存する：
- ナレーション音声（ElevenLabs）
- シーン画像（DALL-E 3 / 16:9 高品質）
- B-roll動画素材（Pexels ライセンスフリー）
- タイムライン定義（timeline.json + edit_guide.md）

## 処理手順

### ステップ1：ナレーション生成
台本テキスト全体（スライド構成セクションを除く本文）を `generate_narration` に渡す。
output_dir はユーザーから受け取った値をそのまま使う。

### ステップ2：シーン構成の抽出
台本の「## スライド構成」セクションを読み、スライドごとにシーンを特定する。
スライド構成がない場合は台本の構成（オープニング・本編・まとめ）から4〜6シーンを設定する。
各シーンの in_sec / out_sec は合計 600秒（10分）に収まるよう均等に割り当てる。

### ステップ3：シーン画像生成
各シーンについて `generate_scene_image` を呼ぶ。
- scene_description は英語で書く（例: "Barolo wine bottle on rustic wooden table, Piedmont Italy"）
- scene_number は 1 始まりの連番

### ステップ4：B-roll取得
各シーンに対応するキーワードで `fetch_broll` を呼ぶ。
- keyword は英語の具体的なキーワード（例: "Italian vineyard sunset", "red wine pouring glass"）
- clip_index は 1 始まりの連番（scene_number と同じ番号を使う）

### ステップ5：タイムライン保存
全シーンの情報をまとめて `save_timeline` を呼ぶ。
- scenes 配列に全シーン（id, in_sec, out_sec, type="slide", image, broll, caption, notes）を含める
- reels_highlights に最も印象的な 30〜60秒のシーンを 1〜3 個指定する

## 使用可能なツール
- `generate_narration(script_text, output_dir)` — ナレーション音声生成
- `generate_scene_image(scene_description, scene_number, output_dir)` — シーン画像生成
- `fetch_broll(keyword, clip_index, output_dir)` — B-roll動画取得
- `save_timeline(timeline, output_dir)` — タイムライン保存

## 完了報告
全ツール完了後、以下の形式で日本語サマリーを出力する：

```
## 動画素材生成完了：{タイトル}

- 📁 出力先: {output_dir}
- 🎙️ ナレーション: audio/narration.mp3
- 🖼️ 画像: {枚数}枚（images/scene_01.png〜）
- 🎬 B-roll: {本数}本（broll/broll_01.mp4〜）
- 📋 タイムライン: timeline.json / edit_guide.md

After Effects で output_dir を開き、edit_guide.md の手順に従ってください。
```
```

- [ ] **Step 2: コミット**

```bash
cd ~/ai-org && git add agents/video.txt
git commit -m "feat: add video agent system prompt"
```

---

## Task 6: `runner.py` — `run_video_agent()` + スケジュールタスク追加

**Files:**
- Modify: `runner.py`
- Modify: `tests/test_runner.py`

- [ ] **Step 1: テスト追加**

`tests/test_runner.py` に追記:

```python
from runner import run_video_agent, tuesday_video_task, coffee_tuesday_video_task


def test_run_video_agent_calls_video_tools(tmp_path):
    """run_video_agent が VIDEO_TOOL_DEFINITIONS を使って Claude を呼び出すことを確認。"""
    import runner

    tool_use_block = MagicMock()
    tool_use_block.type = "tool_use"
    tool_use_block.name = "generate_narration"
    tool_use_block.id = "tu_01"
    tool_use_block.input = {"script_text": "台本", "output_dir": str(tmp_path)}

    tool_use_response = MagicMock()
    tool_use_response.stop_reason = "tool_use"
    tool_use_response.content = [tool_use_block]

    final_block = MagicMock()
    final_block.text = "素材生成完了"
    final_response = MagicMock()
    final_response.stop_reason = "end_turn"
    final_response.content = [final_block]

    with patch("runner.client.messages.create", side_effect=[tool_use_response, final_response]), \
         patch("runner.execute_video_tool", return_value="ナレーション保存: narration.mp3") as mock_exec, \
         patch("runner.save_log"):
        result = run_video_agent("台本テキスト", "イタリアワイン", str(tmp_path))

    mock_exec.assert_called_once_with("generate_narration", {"script_text": "台本", "output_dir": str(tmp_path)})
    assert result == "素材生成完了"


def test_tuesday_video_task_catches_exception(monkeypatch):
    with patch("runner.run_video_agent", side_effect=Exception("API error")):
        tuesday_video_task()  # 例外が外に出ないことを確認


def test_coffee_tuesday_video_task_catches_exception(monkeypatch):
    with patch("runner.run_video_agent", side_effect=Exception("API error")):
        coffee_tuesday_video_task()
```

- [ ] **Step 2: テストを実行して失敗を確認**

```bash
cd ~/ai-org && python -m pytest tests/test_runner.py::test_run_video_agent_calls_video_tools -v
```

Expected: `ImportError`（`run_video_agent` 未定義）

- [ ] **Step 3: `runner.py` を変更**

`runner.py` の先頭 import 行に追加（`from tools import ...` の下）:

```python
from tools_video import VIDEO_TOOL_DEFINITIONS, execute_video_tool
```

`runner.py` の `collab_task` 関数の下に追加:

```python
def run_video_agent(script_text: str, topic: str, output_dir: str) -> str:
    system = load_agent("video")
    prompt = f"出力先ディレクトリ: {output_dir}\n\nトピック: {topic}\n\n台本：\n{script_text}"
    messages = [{"role": "user", "content": prompt}]

    while True:
        response = _with_retry(
            lambda: client.messages.create(
                model=MODEL,
                max_tokens=16000,
                system=system,
                tools=VIDEO_TOOL_DEFINITIONS,
                messages=messages,
            ),
            f"video-{topic}",
        )

        if response.stop_reason == "tool_use":
            messages.append({"role": "assistant", "content": response.content})
            tool_results = []
            for block in response.content:
                if block.type == "tool_use":
                    print(f"  🎬 動画エージェント: {block.name}")
                    result = execute_video_tool(block.name, block.input)
                    print(f"     → {result}")
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": result,
                    })
            messages.append({"role": "user", "content": tool_results})
        else:
            final_text = next((b.text for b in response.content if hasattr(b, "text")), "")
            save_log(final_text, f"video-{topic}")
            print(f"\n✅ 動画素材生成完了: {output_dir}")
            return final_text


def tuesday_video_task():
    try:
        script = _read_todays_log()
        date_str = datetime.now().strftime("%Y-%m-%d")
        output_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "output", f"{date_str}-wine")
        run_video_agent(script, "イタリアワイン", output_dir)
    except Exception as e:
        print(f"  ❌ 火曜：ワイン動画素材生成 失敗: {e}")


def coffee_tuesday_video_task():
    try:
        script = _read_todays_log()
        date_str = datetime.now().strftime("%Y-%m-%d")
        output_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "output", f"{date_str}-coffee")
        run_video_agent(script, "イタリアコーヒー", output_dir)
    except Exception as e:
        print(f"  ❌ 火曜：コーヒー動画素材生成 失敗: {e}")
```

`main()` 関数の `schedule.every().tuesday.at("10:00").do(coffee_tuesday_task)` の次の行に追加:

```python
    schedule.every().tuesday.at("11:00").do(tuesday_video_task)
    schedule.every().tuesday.at("12:00").do(coffee_tuesday_video_task)
```

`main()` 内の print 文を更新:

```python
    print("火 11:00 ワイン動画素材 / 火 12:00 コーヒー動画素材")
```

- [ ] **Step 4: テストを実行してパスを確認**

```bash
cd ~/ai-org && python -m pytest tests/test_runner.py -v
```

Expected: すべての既存テスト + 新規 3 テスト PASSED

- [ ] **Step 5: 全テストを実行**

```bash
cd ~/ai-org && python -m pytest -v
```

Expected: すべての tests PASSED

- [ ] **Step 6: コミット**

```bash
cd ~/ai-org && git add runner.py tests/test_runner.py
git commit -m "feat: add run_video_agent and tuesday video pipeline tasks to runner"
```

---

## Task 7: `.claude/agents/video.md` — Claude Code エージェント定義

**Files:**
- Create: `.claude/agents/video.md`

- [ ] **Step 1: ファイル作成**

`.claude/agents/video.md` を作成。frontmatter + `agents/video.txt` と同じ本文を貼る:

```markdown
---
name: video
description: 動画素材生成エージェント。台本テキストと出力ディレクトリを渡すと、ElevenLabs でナレーション、DALL-E 3 でシーン画像、Pexels で B-roll 動画を生成し After Effects 用素材パックを作成する。必要な環境変数: ELEVENLABS_API_KEY, ELEVENLABS_VOICE_ID, OPENAI_API_KEY, PEXELS_API_KEY
---

（ここに agents/video.txt の全文をそのままコピーする）
```

`agents/video.txt` を Read してその内容を frontmatter の下に貼り付けること。

- [ ] **Step 2: コミット**

```bash
cd ~/ai-org && git add .claude/agents/video.md
git commit -m "feat: add @video Claude Code agent definition"
```

---

## Task 8: `.env` への APIキー追加案内

**Files:**
- Modify: `.env`（API キーは実際の値を入力すること）

- [ ] **Step 1: `.env` に以下を追加**

```
ELEVENLABS_API_KEY=your_elevenlabs_api_key_here
ELEVENLABS_VOICE_ID=21m00Tcm4TlvDq8ikWAM
OPENAI_API_KEY=your_openai_api_key_here
PEXELS_API_KEY=your_pexels_api_key_here
```

ElevenLabs Voice ID の確認: https://api.elevenlabs.io/v1/voices でリスト取得可能。日本語対応の音声を選ぶこと。

- [ ] **Step 2: 動作確認（手動）**

```bash
cd ~/ai-org && python3 -c "
from tools_video import generate_narration
import tempfile, os
with tempfile.TemporaryDirectory() as d:
    result = generate_narration('こんにちは。テストナレーションです。', d)
    print(result)
"
```

Expected: `ナレーション保存: /tmp/xxx/audio/narration.mp3`

---

## スコープ注記

スペックの `reels/highlight_01.png 〜 3.png`（縦型ハイライト画像）は本計画では生成しない。
縦型クロップは After Effects でのユーザー作業とし、`timeline.json` の `reels_highlights` セクションが時間情報を提供する。
Reels 用の自動画像生成は次フェーズで追加可能。

---

## 全テスト確認

```bash
cd ~/ai-org && python -m pytest -v
```

Expected: すべて PASSED
