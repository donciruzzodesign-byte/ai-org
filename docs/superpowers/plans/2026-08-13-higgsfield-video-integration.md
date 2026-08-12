# Higgsfield AI動画生成連携 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** シーン画像を元にHiggsfield APIでAI動画クリップを生成する`generate_scene_video`を`tools_video.py`に追加し、既存の動画素材生成パイプライン（ツール定義・AEスクリプト生成・videoエージェント）に統合する。

**Architecture:** `tools_video.py`に第3の素材ソースとして新関数を追加する。画像アップロードのみHiggsfield公式Python SDK（`higgsfield-client`）の`upload_file()`を使い、ジョブ送信・ポーリング・動画ダウンロードは既存コードと同じ`requests`直書きで行う（Higgsfieldの生REST APIの契約は公式ドキュメントで確認済みで安定しているが、SDK側のポーリング用型クラスの内部仕様は未確認のため、確実性の低いSDK内部APIへの依存を避ける）。

**Tech Stack:** Python, `requests`（既存）, `higgsfield-client`（新規依存）, pytest + `unittest.mock`（既存パターン踏襲）

## Global Constraints

- 認証は`HF_API_KEY`（Key ID）・`HF_API_SECRET`（Key Secret）の2つの環境変数（`.env`に設定済み）。単一キーではない。
- 既存の`generate_scene_image`（gpt-image-1静止画）・`fetch_broll`（Pexels）は変更しない。
- 生成は image-to-video のみ（text-to-videoは対象外）。元画像は`images/scene_{NN}.png`が事前に存在している必要がある。
- モデルは`higgsfield-ai/dop/standard`固定（ベースURL: `https://platform.higgsfield.ai`）。
- エラーは例外を投げず、既存関数と同じく文字列メッセージで返す。
- ポーリングタイムアウトは300秒、ポーリング間隔は5秒。
- 出力は`ai_video/scene_{NN}.mp4`。既に存在する場合はスキップ（既存関数と同じ冪等パターン）。
- 生成した動画は`auto_edit.jsx`の自動配置対象に含める（`broll`と同じスロットの二択として扱う）。

---

### Task 1: `generate_scene_video` コア関数

**Files:**
- Modify: `requirements.txt`（末尾に依存追加）
- Modify: `tools_video.py:1-7`（import追加）, `tools_video.py:340-341`（新関数を`fetch_broll`と`save_timeline`の間に追加）
- Test: `tests/test_tools_video.py`（末尾に追加）

**Interfaces:**
- Produces: `generate_scene_video(scene_number: int, output_dir: str, motion_description: str = "") -> str`
  （成功時 `"AI動画保存: {path}"` を含む文字列、失敗時はエラー内容を含む文字列を返す。例外は投げない）
- Produces（モジュール定数）: `HIGGSFIELD_BASE_URL`, `HIGGSFIELD_MODEL`, `HIGGSFIELD_POLL_INTERVAL_SEC`, `HIGGSFIELD_POLL_TIMEOUT_SEC`, `HIGGSFIELD_TERMINAL_STATUSES`
- Consumes: なし（既存の`_ensure_dir`ヘルパーのみ利用）

- [ ] **Step 1: ガード節（キー未設定／元画像なし／出力済み）の失敗するテストを書く**

`tests/test_tools_video.py`の末尾に追加:

```python
from tools_video import generate_scene_video


def test_generate_scene_video_skips_when_no_key(monkeypatch, tmp_path):
    monkeypatch.delenv("HF_API_KEY", raising=False)
    monkeypatch.delenv("HF_API_SECRET", raising=False)
    result = generate_scene_video(1, str(tmp_path))
    assert "未設定" in result


def test_generate_scene_video_missing_source_image(monkeypatch, tmp_path):
    monkeypatch.setenv("HF_API_KEY", "id")
    monkeypatch.setenv("HF_API_SECRET", "secret")
    result = generate_scene_video(1, str(tmp_path))
    assert "見つかりません" in result


def test_generate_scene_video_skips_existing_file(monkeypatch, tmp_path):
    monkeypatch.setenv("HF_API_KEY", "id")
    monkeypatch.setenv("HF_API_SECRET", "secret")
    video_dir = tmp_path / "ai_video"
    video_dir.mkdir()
    (video_dir / "scene_01.mp4").write_bytes(b"existing")

    with patch("tools_video.higgsfield_client.upload_file") as mock_upload:
        result = generate_scene_video(1, str(tmp_path))

    mock_upload.assert_not_called()
    assert "スキップ" in result
```

- [ ] **Step 2: テストを実行して失敗を確認する**

Run: `python3 -m pytest tests/test_tools_video.py -k generate_scene_video -v`
Expected: FAIL（`ImportError: cannot import name 'generate_scene_video'`、または`ModuleNotFoundError: No module named 'higgsfield_client'`）

- [ ] **Step 3: 依存追加・import・定数・ガード節を実装する**

`requirements.txt`の末尾に追加:

```
higgsfield-client
```

`pip install -r requirements.txt` を実行して依存をインストールする。

`tools_video.py`の先頭import群（1-7行目）を以下に変更:

```python
import os
import json
import base64
import time
import requests
import higgsfield_client
import anthropic
from typing import Optional
from PIL import Image
```

`tools_video.py`の`fetch_broll`関数の直後（340行目の空行の後、`save_timeline`定義の前）に追加:

```python
HIGGSFIELD_BASE_URL = "https://platform.higgsfield.ai"
HIGGSFIELD_MODEL = "higgsfield-ai/dop/standard"
HIGGSFIELD_POLL_INTERVAL_SEC = 5
HIGGSFIELD_POLL_TIMEOUT_SEC = 300
HIGGSFIELD_TERMINAL_STATUSES = {"completed", "failed", "nsfw", "canceled"}


def generate_scene_video(scene_number: int, output_dir: str, motion_description: str = "") -> str:
    api_key = os.environ.get("HF_API_KEY")
    api_secret = os.environ.get("HF_API_SECRET")
    if not api_key or not api_secret:
        return "HF_API_KEY / HF_API_SECRET が未設定のためスキップ"

    video_dir = os.path.join(output_dir, "ai_video")
    _ensure_dir(video_dir)
    video_path = os.path.join(video_dir, f"scene_{scene_number:02d}.mp4")

    if os.path.exists(video_path):
        return f"スキップ（既存）: {video_path}"

    image_path = os.path.join(output_dir, "images", f"scene_{scene_number:02d}.png")
    if not os.path.exists(image_path):
        return f"シーン画像が見つかりません（先にgenerate_scene_imageかassign_photoで作成してください）: {image_path}"

    raise NotImplementedError("Step 7で実装")
```

- [ ] **Step 4: テストを実行してガード節のテストが通ることを確認する**

Run: `python3 -m pytest tests/test_tools_video.py -k generate_scene_video -v`
Expected: `test_generate_scene_video_skips_when_no_key` と `test_generate_scene_video_missing_source_image` と `test_generate_scene_video_skips_existing_file` が PASS

- [ ] **Step 5: 生成本体（正常系・failed・タイムアウト）の失敗するテストを書く**

`tests/test_tools_video.py`に追加:

```python
def test_generate_scene_video_saves_mp4(monkeypatch, tmp_path):
    monkeypatch.setenv("HF_API_KEY", "id")
    monkeypatch.setenv("HF_API_SECRET", "secret")
    images_dir = tmp_path / "images"
    images_dir.mkdir()
    (images_dir / "scene_01.png").write_bytes(b"fake-png")

    submit_resp = MagicMock()
    submit_resp.status_code = 200
    submit_resp.json.return_value = {
        "status": "queued",
        "request_id": "req-1",
        "status_url": "https://platform.higgsfield.ai/requests/req-1/status",
        "cancel_url": "https://platform.higgsfield.ai/requests/req-1/cancel",
    }

    status_resp = MagicMock()
    status_resp.json.return_value = {
        "status": "completed",
        "video": {"url": "https://example.com/out.mp4"},
    }

    video_resp = MagicMock()
    video_resp.iter_content = MagicMock(return_value=[b"fake-video-data"])

    with patch("tools_video.higgsfield_client.upload_file", return_value="https://example.com/uploaded.png"), \
         patch("tools_video.requests.post", return_value=submit_resp), \
         patch("tools_video.requests.get", side_effect=[status_resp, video_resp]), \
         patch("tools_video.time.sleep"):
        result = generate_scene_video(1, str(tmp_path), motion_description="slow zoom in")

    assert "ai_video" in result
    video_path = tmp_path / "ai_video" / "scene_01.mp4"
    assert video_path.exists()
    assert video_path.read_bytes() == b"fake-video-data"


def test_generate_scene_video_returns_error_on_failed_status(monkeypatch, tmp_path):
    monkeypatch.setenv("HF_API_KEY", "id")
    monkeypatch.setenv("HF_API_SECRET", "secret")
    images_dir = tmp_path / "images"
    images_dir.mkdir()
    (images_dir / "scene_01.png").write_bytes(b"fake-png")

    submit_resp = MagicMock()
    submit_resp.status_code = 200
    submit_resp.json.return_value = {
        "status": "queued",
        "status_url": "https://platform.higgsfield.ai/requests/req-1/status",
    }
    status_resp = MagicMock()
    status_resp.json.return_value = {"status": "failed"}

    with patch("tools_video.higgsfield_client.upload_file", return_value="https://example.com/uploaded.png"), \
         patch("tools_video.requests.post", return_value=submit_resp), \
         patch("tools_video.requests.get", return_value=status_resp), \
         patch("tools_video.time.sleep"):
        result = generate_scene_video(1, str(tmp_path))

    assert "エラー" in result
    assert "failed" in result


def test_generate_scene_video_returns_error_on_timeout(monkeypatch, tmp_path):
    monkeypatch.setenv("HF_API_KEY", "id")
    monkeypatch.setenv("HF_API_SECRET", "secret")
    images_dir = tmp_path / "images"
    images_dir.mkdir()
    (images_dir / "scene_01.png").write_bytes(b"fake-png")

    submit_resp = MagicMock()
    submit_resp.status_code = 200
    submit_resp.json.return_value = {
        "status": "queued",
        "status_url": "https://platform.higgsfield.ai/requests/req-1/status",
    }
    status_resp = MagicMock()
    status_resp.json.return_value = {"status": "in_progress"}

    with patch("tools_video.higgsfield_client.upload_file", return_value="https://example.com/uploaded.png"), \
         patch("tools_video.requests.post", return_value=submit_resp), \
         patch("tools_video.requests.get", return_value=status_resp), \
         patch("tools_video.time.sleep"), \
         patch("tools_video.HIGGSFIELD_POLL_TIMEOUT_SEC", 5), \
         patch("tools_video.HIGGSFIELD_POLL_INTERVAL_SEC", 5):
        result = generate_scene_video(1, str(tmp_path))

    assert "タイムアウト" in result
```

- [ ] **Step 6: テストを実行して失敗を確認する**

Run: `python3 -m pytest tests/test_tools_video.py -k generate_scene_video -v`
Expected: 上記3つの新規テストが FAIL（`NotImplementedError: Step 7で実装`）

- [ ] **Step 7: 生成本体を実装する**

`tools_video.py`の`raise NotImplementedError("Step 7で実装")`を以下に置き換える（Step 3の関数を完成させる）:

```python
    headers = {"Authorization": f"Key {api_key}:{api_secret}"}

    try:
        image_url = higgsfield_client.upload_file(image_path)

        submit_resp = requests.post(
            f"{HIGGSFIELD_BASE_URL}/{HIGGSFIELD_MODEL}",
            headers={**headers, "Content-Type": "application/json"},
            json={"image_url": image_url, "prompt": motion_description},
            timeout=30,
        )
        if submit_resp.status_code not in (200, 201, 202):
            return f"動画生成リクエストエラー (scene {scene_number}): {submit_resp.status_code} {submit_resp.text[:200]}"
        status_url = submit_resp.json()["status_url"]

        elapsed = 0
        status_json = {}
        while elapsed < HIGGSFIELD_POLL_TIMEOUT_SEC:
            status_resp = requests.get(status_url, headers=headers, timeout=30)
            status_json = status_resp.json()
            if status_json.get("status") in HIGGSFIELD_TERMINAL_STATUSES:
                break
            time.sleep(HIGGSFIELD_POLL_INTERVAL_SEC)
            elapsed += HIGGSFIELD_POLL_INTERVAL_SEC
        else:
            return f"動画生成タイムアウト (scene {scene_number})"

        status = status_json.get("status")
        if status != "completed":
            return f"動画生成エラー (scene {scene_number}): status={status}"

        video_url = status_json["video"]["url"]
        video_resp = requests.get(video_url, timeout=120, stream=True)
        with open(video_path, "wb") as f:
            for chunk in video_resp.iter_content(chunk_size=8192):
                f.write(chunk)
        return f"AI動画保存: {video_path}"
    except Exception as e:
        return f"動画生成エラー (scene {scene_number}): {e}"
```

- [ ] **Step 8: 全テストを実行してすべて通ることを確認する**

Run: `python3 -m pytest tests/test_tools_video.py -v`
Expected: PASS（既存テストを含め全件）

- [ ] **Step 9: コミット**

```bash
git add requirements.txt tools_video.py tests/test_tools_video.py
git commit -m "$(cat <<'EOF'
feat: Higgsfield APIでシーン画像からAI動画クリップを生成するgenerate_scene_videoを追加

image-to-videoでシーン画像に動きを加えた動画を生成する新機能。既存のgpt-image-1静止画・
Pexels B-rollとは独立した第3の素材ソース。画像アップロードのみ公式SDKを使い、
ジョブ送信・ポーリングは契約が確認済みの生REST APIで行う。

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 2: ツール定義とディスパッチへの登録

**Files:**
- Modify: `tools_video.py:90-104`（`VIDEO_TOOL_DEFINITIONS`リストに追加）
- Modify: `tools_video.py:539-540`（`execute_video_tool`にディスパッチ分岐を追加）
- Test: `tests/test_tools_video.py`

**Interfaces:**
- Consumes: `generate_scene_video(scene_number, output_dir, motion_description="")`（Task 1で定義）
- Produces: `execute_video_tool("generate_scene_video", {...})` 経由での呼び出し

- [ ] **Step 1: ディスパッチの失敗するテストを書く**

`tests/test_tools_video.py`に追加:

```python
def test_execute_video_tool_dispatches_generate_scene_video(monkeypatch, tmp_path):
    monkeypatch.delenv("HF_API_KEY", raising=False)
    monkeypatch.delenv("HF_API_SECRET", raising=False)
    result = execute_video_tool("generate_scene_video", {
        "scene_number": 1, "output_dir": str(tmp_path)
    })
    assert "未設定" in result
```

- [ ] **Step 2: テストを実行して失敗を確認する**

Run: `python3 -m pytest tests/test_tools_video.py -k dispatches_generate_scene_video -v`
Expected: FAIL（`不明なツール: generate_scene_video`が返り、アサーション失敗）

- [ ] **Step 3: ツール定義とディスパッチを実装する**

`tools_video.py`の`VIDEO_TOOL_DEFINITIONS`リスト内、`assign_photo`のツール定義（94-103行目）の直後、リストを閉じる`]`（104行目）の直前に追加:

```python
    ,{
        "name": "generate_scene_video",
        "description": "シーン画像(images/scene_NN.png)を元にHiggsfield APIでAI動画クリップ(ai_video/scene_NN.mp4)を生成します。事前にgenerate_scene_imageかassign_photoでシーン画像を作成しておく必要があります。fetch_broll(ストック映像)の代わりに使う、ブランド統一感を出したいシーン向けの選択肢です。",
        "input_schema": {
            "type": "object",
            "properties": {
                "scene_number": {"type": "integer", "description": "シーン番号（1始まり）"},
                "output_dir": {"type": "string", "description": "保存先ディレクトリ"},
                "motion_description": {"type": "string", "description": "任意。動きの説明（英語推奨、例: 'slow zoom in, gentle camera pan'）"}
            },
            "required": ["scene_number", "output_dir"]
        }
    }
```

`tools_video.py`の`execute_video_tool`内、`fetch_broll`のディスパッチ（`elif name == "fetch_broll": return fetch_broll(...)`）の直後に追加:

```python
    elif name == "generate_scene_video":
        return generate_scene_video(
            inputs["scene_number"], inputs["output_dir"], inputs.get("motion_description", ""),
        )
```

- [ ] **Step 4: テストを実行して通ることを確認する**

Run: `python3 -m pytest tests/test_tools_video.py -v`
Expected: PASS（全件）

- [ ] **Step 5: コミット**

```bash
git add tools_video.py tests/test_tools_video.py
git commit -m "$(cat <<'EOF'
feat: generate_scene_videoをVIDEO_TOOL_DEFINITIONSとexecute_video_toolに登録

videoエージェントがツールとして呼び出せるようにする。

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 3: AEスクリプト生成での`ai_video`統合

**Files:**
- Modify: `tools_video.py:425`（`broll_rel = scene.get("broll", "")`を変更）
- Test: `tests/test_tools_video.py`

**Interfaces:**
- Consumes: `scenes[]`の`ai_video`フィールド（`broll`と同じ相対パス文字列形式）
- Produces: `generate_ae_script`が`ai_video`のみ指定されたシーンでも`broll`と同じオーバーレイ配置ロジック（opacity 70%）でJSXに出力する

- [ ] **Step 1: 失敗するテストを書く**

`tests/test_tools_video.py`に追加:

```python
def test_generate_ae_script_jsx_references_ai_video_when_no_broll(tmp_path):
    timeline = {
        "title": "バローロ特集",
        "duration_sec": 600,
        "narration": "audio/narration.mp3",
        "scenes": [{
            "id": 1, "in_sec": 0, "out_sec": 60,
            "type": "slide", "image": "images/scene_01.png",
            "ai_video": "ai_video/scene_01.mp4",
            "caption": "テスト",
        }],
        "reels_highlights": [],
    }
    generate_ae_script(timeline, str(tmp_path))
    content = (tmp_path / "auto_edit.jsx").read_text(encoding="utf-8")
    assert "scene_01.mp4" in content


def test_generate_ae_script_prefers_broll_over_ai_video(tmp_path):
    timeline = {
        "title": "バローロ特集",
        "duration_sec": 600,
        "narration": "audio/narration.mp3",
        "scenes": [{
            "id": 1, "in_sec": 0, "out_sec": 60,
            "type": "slide", "image": "images/scene_01.png",
            "broll": "broll/broll_01.mp4",
            "ai_video": "ai_video/scene_01.mp4",
            "caption": "テスト",
        }],
        "reels_highlights": [],
    }
    generate_ae_script(timeline, str(tmp_path))
    content = (tmp_path / "auto_edit.jsx").read_text(encoding="utf-8")
    assert "broll_01.mp4" in content
    assert "ai_video/scene_01.mp4" not in content
```

- [ ] **Step 2: テストを実行して失敗を確認する**

Run: `python3 -m pytest tests/test_tools_video.py -k ai_video -v`
Expected: `test_generate_ae_script_jsx_references_ai_video_when_no_broll` が FAIL（`ai_video/scene_01.mp4`がJSXに出力されない）

- [ ] **Step 3: `generate_ae_script`を修正する**

`tools_video.py`の425行目:

```python
            broll_rel = scene.get("broll", "")
```

を以下に変更:

```python
            broll_rel = scene.get("broll") or scene.get("ai_video", "")
```

- [ ] **Step 4: テストを実行して通ることを確認する**

Run: `python3 -m pytest tests/test_tools_video.py -v`
Expected: PASS（全件）

- [ ] **Step 5: コミット**

```bash
git add tools_video.py tests/test_tools_video.py
git commit -m "$(cat <<'EOF'
feat: auto_edit.jsxがscenes[].ai_videoをbrollと同じスロットで自動配置するように対応

1シーンにつきbrollとai_videoはどちらか一方を想定し、brollが優先される。

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 4: ドキュメント更新（videoエージェントプロンプト・CLAUDE.md）

**Files:**
- Modify: `.claude/agents/video.md`
- Modify: `agents/video.txt`
- Modify: `CLAUDE.md:28-32`（環境変数）, `CLAUDE.md:119-120`（動画パイプライン出力表）

**Interfaces:**
- Consumes: Task 1〜3で実装した`generate_scene_video`ツール（関数シグネチャ・ツール名は変更しない）
- Produces: なし（ドキュメントのみ。後続タスクなし）

- [ ] **Step 1: `.claude/agents/video.md`を更新する**

frontmatterの`description`を以下に変更（既存の文末に追記）:

```yaml
description: 動画素材生成エージェント。台本テキストと出力ディレクトリを渡すと、ElevenLabs でナレーション、DALL-E 3 でシーン画像、Pexels で B-roll 動画、Higgsfield で AI動画クリップを生成し After Effects 用素材パックを作成する。必要な環境変数: ELEVENLABS_API_KEY, ELEVENLABS_VOICE_ID, OPENAI_API_KEY, PEXELS_API_KEY, HF_API_KEY, HF_API_SECRET
```

`## 処理手順`の`### ステップ4：B-roll取得`の直後（`### ステップ5：タイムライン保存`の直前）に追加:

```markdown
### ステップ4.5：AI動画クリップの選択的生成
シーンのうち、ブランド統一感を出したい・実写ストックでは表現しきれないもの（商品ショット、こだわりの構図など）は、`fetch_broll`の代わりに`generate_scene_video`を呼ぶ。それ以外の汎用的な雰囲気カットは`fetch_broll`のままでよい。1シーンにつき`fetch_broll`と`generate_scene_video`はどちらか一方のみ呼ぶ。`generate_scene_video`は対応する`generate_scene_image`（ステップ3）より後に呼ぶこと（元画像が前提のため）。
```

`## 使用可能なツール`のリストに追加:

```markdown
- `generate_scene_video(scene_number, output_dir, motion_description)` — シーン画像からAI動画クリップ生成（Higgsfield、fetch_brollの代替）
```

- [ ] **Step 2: `agents/video.txt`を更新する**

`### ステップ3：B-roll取得`の直後（`### ステップ4：タイムライン保存`の直前）に追加:

```markdown
### ステップ3.5：AI動画クリップの選択的生成
シーンのうち、ブランド統一感を出したい・実写ストックでは表現しきれないもの（商品ショット、こだわりの構図など）は、`fetch_broll`の代わりに`generate_scene_video`を呼ぶ。それ以外の汎用的な雰囲気カットは`fetch_broll`のままでよい。1シーンにつき`fetch_broll`と`generate_scene_video`はどちらか一方のみ呼ぶ。`generate_scene_video`は対応する`generate_scene_image`（ステップ2）より後に呼ぶこと（元画像が前提のため）。
```

`## 使用可能なツール`のリストに追加:

```markdown
- `generate_scene_video(scene_number, output_dir, motion_description)` — シーン画像からAI動画クリップ生成（Higgsfield、fetch_brollの代替）
```

- [ ] **Step 3: `CLAUDE.md`の環境変数一覧を更新する**

29行目 `META_ACCESS_TOKEN=...        # 任意（Instagram Insights自動連携に必須）` の直前に追加:

```
HF_API_KEY=...               # 任意（Higgsfield AI動画クリップ生成に必須）
HF_API_SECRET=...            # 任意（同上）
```

- [ ] **Step 4: `CLAUDE.md`の動画パイプライン出力表を更新する**

120行目 `| \`auto_edit.jsx\` | AE自動配置スクリプト（File→Scripts→Run で実行） |` の直後に追加:

```
| `ai_video/scene_NN.mp4` | Higgsfield生成AI動画クリップ（任意、brollの代わりに使うシーンのみ） |
```

- [ ] **Step 5: 変更箇所を目視確認する**

Run: `git diff .claude/agents/video.md agents/video.txt CLAUDE.md`
Expected: 上記4ファイルの追記のみが差分に含まれ、既存記述の意図しない変更がないこと

- [ ] **Step 6: コミット**

```bash
git add .claude/agents/video.md agents/video.txt CLAUDE.md
git commit -m "$(cat <<'EOF'
docs: generate_scene_video(Higgsfield)をvideoエージェントプロンプトとCLAUDE.mdに反映

エージェントがfetch_broll(ストック)とgenerate_scene_video(AI生成)を
シーンごとに使い分けられるよう判断基準を明記。

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 5: 全体検証

**Files:**
- なし（検証のみ、コード変更なし）

**Interfaces:**
- Consumes: Task 1〜4の全成果物

- [ ] **Step 1: 全テストスイートを実行する**

Run: `python3 -m pytest tests/ -v`
Expected: PASS（全件、`test_tools_video.py`の新規10テストを含む）

- [ ] **Step 2: 新規ツールがVIDEO_TOOL_DEFINITIONSとエージェントドキュメントの双方に整合していることを確認する**

Run: `grep -n "generate_scene_video" tools_video.py .claude/agents/video.md agents/video.txt`
Expected: `tools_video.py`（ツール定義・関数定義・ディスパッチの3箇所）、`.claude/agents/video.md`、`agents/video.txt`のそれぞれに出現すること
