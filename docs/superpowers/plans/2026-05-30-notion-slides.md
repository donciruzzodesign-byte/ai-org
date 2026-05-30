# Notion スライド風子ページ保存 実装計画

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `tools.py` の `save_to_notion` を改修し、タスク出力をNotionの子ページとして独立保存し、`##` セクションをdividerで区切るスライド風レイアウトで整形する。

**Architecture:** マークダウンテキストを行単位で解析してNotionブロックのリストに変換する `_parse_content_to_blocks` ヘルパーと、子ページを作成して返す `_create_child_page` ヘルパーに分割し、`save_to_notion` はそれらを組み合わせる。呼び出し側 (`runner.py:94`) のシグネチャは変更しない。

**Tech Stack:** Python 3, requests, pytest, unittest.mock

---

## ファイル構成

| ファイル | 変更内容 |
|---|---|
| `tools.py` | `save_to_notion` 改修、`_parse_content_to_blocks`・`_create_child_page` ヘルパー追加 |
| `tests/test_tools.py` | 新規作成。上記3関数のユニットテスト |

---

### Task 1: `_parse_content_to_blocks` のテストを書いて失敗させる

**Files:**
- Create: `tests/test_tools.py`

- [ ] **Step 1: テストファイルを作成する**

```python
# tests/test_tools.py
import os
import sys
import pytest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from tools import _parse_content_to_blocks


def test_heading1():
    blocks = _parse_content_to_blocks("# タイトル")
    assert blocks == [
        {"object": "block", "type": "heading_1",
         "heading_1": {"rich_text": [{"text": {"content": "タイトル"}}]}}
    ]


def test_heading2_inserts_divider_before():
    blocks = _parse_content_to_blocks("## セクション")
    assert blocks[0] == {"object": "block", "type": "divider", "divider": {}}
    assert blocks[1] == {
        "object": "block", "type": "heading_2",
        "heading_2": {"rich_text": [{"text": {"content": "セクション"}}]}
    }


def test_heading3():
    blocks = _parse_content_to_blocks("### 小見出し")
    assert blocks == [
        {"object": "block", "type": "heading_3",
         "heading_3": {"rich_text": [{"text": {"content": "小見出し"}}]}}
    ]


def test_bulleted_list_hyphen():
    blocks = _parse_content_to_blocks("- 箇条書き")
    assert blocks == [
        {"object": "block", "type": "bulleted_list_item",
         "bulleted_list_item": {"rich_text": [{"text": {"content": "箇条書き"}}]}}
    ]


def test_bulleted_list_asterisk():
    blocks = _parse_content_to_blocks("* 箇条書き")
    assert blocks == [
        {"object": "block", "type": "bulleted_list_item",
         "bulleted_list_item": {"rich_text": [{"text": {"content": "箇条書き"}}]}}
    ]


def test_numbered_list():
    blocks = _parse_content_to_blocks("1. 番号付き")
    assert blocks == [
        {"object": "block", "type": "numbered_list_item",
         "numbered_list_item": {"rich_text": [{"text": {"content": "番号付き"}}]}}
    ]


def test_empty_line_skipped():
    blocks = _parse_content_to_blocks("\n\n")
    assert blocks == []


def test_plain_text_becomes_paragraph():
    blocks = _parse_content_to_blocks("普通のテキスト")
    assert blocks == [
        {"object": "block", "type": "paragraph",
         "paragraph": {"rich_text": [{"text": {"content": "普通のテキスト"}}]}}
    ]


def test_multiline_mixed():
    content = "## オープニング\n- 箇条書き1\n- 箇条書き2\n\n普通のテキスト"
    blocks = _parse_content_to_blocks(content)
    types = [b["type"] for b in blocks]
    assert types == ["divider", "heading_2", "bulleted_list_item", "bulleted_list_item", "paragraph"]
```

- [ ] **Step 2: テストを実行して失敗を確認する**

```bash
cd /Users/kubotahironori/ai-org
python -m pytest tests/test_tools.py -v 2>&1 | head -30
```

期待: `ImportError: cannot import name '_parse_content_to_blocks' from 'tools'`

---

### Task 2: `_parse_content_to_blocks` を実装してテストを通す

**Files:**
- Modify: `tools.py`（`save_to_notion` 関数の直前に追加）

- [ ] **Step 1: `tools.py` に `_parse_content_to_blocks` を追加する**

`save_to_notion` 関数（133行目）の直前に以下を挿入する:

```python
import re

def _parse_content_to_blocks(content: str) -> list:
    blocks = []
    for line in content.splitlines():
        if not line.strip():
            continue
        if line.startswith("# "):
            text = line[2:].strip()
            blocks.append({"object": "block", "type": "heading_1",
                           "heading_1": {"rich_text": [{"text": {"content": text}}]}})
        elif line.startswith("## "):
            text = line[3:].strip()
            blocks.append({"object": "block", "type": "divider", "divider": {}})
            blocks.append({"object": "block", "type": "heading_2",
                           "heading_2": {"rich_text": [{"text": {"content": text}}]}})
        elif line.startswith("### "):
            text = line[4:].strip()
            blocks.append({"object": "block", "type": "heading_3",
                           "heading_3": {"rich_text": [{"text": {"content": text}}]}})
        elif line.startswith("- ") or line.startswith("* "):
            text = line[2:].strip()
            blocks.append({"object": "block", "type": "bulleted_list_item",
                           "bulleted_list_item": {"rich_text": [{"text": {"content": text}}]}})
        elif re.match(r'^\d+\. ', line):
            text = re.sub(r'^\d+\. ', '', line).strip()
            blocks.append({"object": "block", "type": "numbered_list_item",
                           "numbered_list_item": {"rich_text": [{"text": {"content": text}}]}})
        else:
            blocks.append({"object": "block", "type": "paragraph",
                           "paragraph": {"rich_text": [{"text": {"content": line.strip()}}]}})
    return blocks
```

- [ ] **Step 2: テストを実行してすべてパスすることを確認する**

```bash
python -m pytest tests/test_tools.py -v
```

期待: `9 passed`

- [ ] **Step 3: コミットする**

```bash
git add tools.py tests/test_tools.py
git commit -m "feat: add _parse_content_to_blocks helper with tests"
```

---

### Task 3: `_create_child_page` のテストを書いて失敗させる

**Files:**
- Modify: `tests/test_tools.py`（テスト追加）

- [ ] **Step 1: テストを追加する**

`tests/test_tools.py` の末尾に追記:

```python
from unittest.mock import patch, MagicMock
from tools import _create_child_page


def test_create_child_page_calls_post(monkeypatch):
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"id": "child-page-id-123"}

    with patch("tools.requests.post", return_value=mock_resp) as mock_post:
        child_id = _create_child_page(
            token="tok",
            parent_page_id="parent-id",
            title="火曜：動画台本 (2026-05-30)"
        )

    mock_post.assert_called_once()
    call_kwargs = mock_post.call_args
    assert call_kwargs[0][0] == "https://api.notion.com/v1/pages"
    payload = call_kwargs[1]["json"]
    assert payload["parent"] == {"page_id": "parent-id"}
    assert payload["properties"]["title"][0]["text"]["content"] == "火曜：動画台本 (2026-05-30)"
    assert child_id == "child-page-id-123"


def test_create_child_page_returns_none_on_error(monkeypatch):
    mock_resp = MagicMock()
    mock_resp.status_code = 400
    mock_resp.json.return_value = {"message": "bad request"}

    with patch("tools.requests.post", return_value=mock_resp):
        child_id = _create_child_page(
            token="tok",
            parent_page_id="parent-id",
            title="テスト"
        )
    assert child_id is None
```

- [ ] **Step 2: テストを実行して失敗を確認する**

```bash
python -m pytest tests/test_tools.py::test_create_child_page_calls_post -v
```

期待: `ImportError: cannot import name '_create_child_page' from 'tools'`

---

### Task 4: `_create_child_page` を実装してテストを通す

**Files:**
- Modify: `tools.py`（`_parse_content_to_blocks` の直後に追加）

- [ ] **Step 1: `_create_child_page` を `tools.py` に追加する**

`_parse_content_to_blocks` の直後に追記:

```python
def _create_child_page(token: str, parent_page_id: str, title: str) -> str | None:
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "Notion-Version": "2022-06-28",
    }
    payload = {
        "parent": {"page_id": parent_page_id},
        "properties": {
            "title": [{"text": {"content": title}}]
        }
    }
    resp = requests.post("https://api.notion.com/v1/pages", headers=headers,
                         json=payload, timeout=15)
    result = resp.json()
    if resp.status_code == 200:
        return result.get("id")
    return None
```

- [ ] **Step 2: テストを実行してすべてパスすることを確認する**

```bash
python -m pytest tests/test_tools.py -v
```

期待: `11 passed`

- [ ] **Step 3: コミットする**

```bash
git add tools.py tests/test_tools.py
git commit -m "feat: add _create_child_page helper with tests"
```

---

### Task 5: `save_to_notion` のテストを書いて失敗させる

**Files:**
- Modify: `tests/test_tools.py`（テスト追加）

- [ ] **Step 1: テストを追加する**

`tests/test_tools.py` の末尾に追記:

```python
from tools import save_to_notion


def test_save_to_notion_creates_child_page_and_adds_blocks(monkeypatch):
    monkeypatch.setenv("NOTION_API_KEY", "test-token")
    monkeypatch.setenv("NOTION_PAGE_ID", "parent-page-id")

    create_resp = MagicMock()
    create_resp.status_code = 200
    create_resp.json.return_value = {"id": "child-id-abc"}

    patch_resp = MagicMock()
    patch_resp.status_code = 200
    patch_resp.json.return_value = {}

    with patch("tools.requests.post", return_value=create_resp) as mock_post, \
         patch("tools.requests.patch", return_value=patch_resp) as mock_patch:
        result = save_to_notion("火曜：動画台本作成", "## オープニング\n- こんにちは")

    assert "Notionに子ページを作成しました" in result
    mock_post.assert_called_once()
    mock_patch.assert_called_once()
    patch_url = mock_patch.call_args[0][0]
    assert "child-id-abc" in patch_url


def test_save_to_notion_chunks_over_100_blocks(monkeypatch):
    monkeypatch.setenv("NOTION_API_KEY", "test-token")
    monkeypatch.setenv("NOTION_PAGE_ID", "parent-page-id")

    create_resp = MagicMock()
    create_resp.status_code = 200
    create_resp.json.return_value = {"id": "child-id-abc"}

    patch_resp = MagicMock()
    patch_resp.status_code = 200
    patch_resp.json.return_value = {}

    # 150行の箇条書きを生成（150ブロック → 2回に分割されるはず）
    content = "\n".join(f"- 項目{i}" for i in range(150))

    with patch("tools.requests.post", return_value=create_resp), \
         patch("tools.requests.patch", return_value=patch_resp) as mock_patch:
        save_to_notion("テスト", content)

    assert mock_patch.call_count == 2


def test_save_to_notion_returns_skip_when_env_not_set(monkeypatch):
    monkeypatch.delenv("NOTION_API_KEY", raising=False)
    monkeypatch.delenv("NOTION_PAGE_ID", raising=False)
    result = save_to_notion("タイトル", "内容")
    assert "未設定" in result


def test_save_to_notion_returns_error_when_child_page_fails(monkeypatch):
    monkeypatch.setenv("NOTION_API_KEY", "test-token")
    monkeypatch.setenv("NOTION_PAGE_ID", "parent-page-id")

    create_resp = MagicMock()
    create_resp.status_code = 400
    create_resp.json.return_value = {"message": "bad request"}

    with patch("tools.requests.post", return_value=create_resp):
        result = save_to_notion("タイトル", "内容")

    assert "子ページ作成エラー" in result
```

- [ ] **Step 2: テストを実行して失敗を確認する**

```bash
python -m pytest tests/test_tools.py::test_save_to_notion_creates_child_page_and_adds_blocks -v
```

期待: FAIL（現在の `save_to_notion` は子ページを作らないため）

---

### Task 6: `save_to_notion` を書き換えてテストを通す

**Files:**
- Modify: `tools.py` — `save_to_notion` 関数全体を置き換え

- [ ] **Step 1: `save_to_notion` を以下で置き換える**

`tools.py` の `save_to_notion` 関数（現在の133〜165行）を削除し、以下に置き換える:

```python
def save_to_notion(title: str, content: str) -> str:
    token = os.environ.get("NOTION_API_KEY")
    page_id = os.environ.get("NOTION_PAGE_ID")
    if not token or not page_id:
        return "NOTION_API_KEY または NOTION_PAGE_ID が未設定のためスキップ"

    child_id = _create_child_page(token, page_id, title)
    if not child_id:
        return "子ページ作成エラー: Notion APIが子ページを作成できませんでした"

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "Notion-Version": "2022-06-28",
    }
    blocks = _parse_content_to_blocks(content)

    chunk_size = 100
    if blocks:
        for i in range(0, len(blocks), chunk_size):
            chunk = blocks[i:i + chunk_size]
            try:
                resp = requests.patch(
                    f"https://api.notion.com/v1/blocks/{child_id}/children",
                    headers=headers,
                    json={"children": chunk},
                    timeout=15,
                )
                if resp.status_code != 200:
                    result = resp.json()
                    return f"Notionブロック追加エラー: {result.get('message', resp.text)}"
            except Exception as e:
                return f"Notionブロック追加エラー: {e}"

    return "Notionに子ページを作成しました"
```

- [ ] **Step 2: テスト全件を実行してすべてパスすることを確認する**

```bash
python -m pytest tests/test_tools.py -v
```

期待: `15 passed`

- [ ] **Step 3: 既存のテストに影響がないか確認する**

```bash
python -m pytest tests/ -v
```

期待: 既存テストもすべてパス

- [ ] **Step 4: コミットする**

```bash
git add tools.py tests/test_tools.py
git commit -m "feat: save_to_notion creates child page with slide layout"
```

---

## チェックリスト（スペックとの対照）

| 成功基準 | 対応タスク |
|---|---|
| タスクごとに子ページが作成される | Task 5・6 |
| 子ページタイトルが `{label} ({YYYY-MM-DD})` 形式 | Task 3・4（呼び出し側 runner.py:94 が既に日付付きで渡している） |
| `##` の前に `divider` が挿入される | Task 1・2 |
| `- ` が `bulleted_list_item` に変換される | Task 1・2 |
| 100ブロック超でも欠落なく保存される | Task 5・6 |
