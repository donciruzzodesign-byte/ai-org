# Notion 部門別保存 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** ローカルログへの保存を廃止し、Notion のみに保存。ワイン部門・コーヒー部門に振り分け。

**Architecture:** `tools.py` に `_get_or_create_department_page()` を追加し、`save_to_notion()` が `department` 引数に応じて保存先を切り替える。`runner.py` の `run_agent()` に `department` 引数を追加し、`save_log()` の呼び出しを削除する。文脈引き継ぎ用の `save_log()` / `_read_todays_log()` は維持。

**Tech Stack:** Python 3.9+, requests, pytest, unittest.mock

---

## ファイル構成

| ファイル | 変更内容 |
|---|---|
| `tools.py` | `_get_or_create_department_page()` 追加、`save_to_notion()` に `department` 引数追加 |
| `runner.py` | `run_agent()` に `department` 引数追加、`save_log()` コンテンツ保存削除、全タスク関数を更新 |
| `tests/test_tools.py` | `_get_or_create_department_page` と `save_to_notion(department=...)` のテスト追加 |
| `tests/test_runner.py` | `run_agent(department=...)` のテスト追加 |

---

### Task 1: `_get_or_create_department_page` のテストを書く

**Files:**
- Modify: `tests/test_tools.py`

- [ ] **Step 1: テストを追加する**

`tests/test_tools.py` の末尾に追加：

```python
from tools import _get_or_create_department_page


def test_get_or_create_returns_existing_page_id(monkeypatch):
    """子ページが既に存在する場合、作成せずにそのIDを返す。"""
    list_resp = MagicMock()
    list_resp.status_code = 200
    list_resp.json.return_value = {
        "results": [
            {"id": "existing-wine-id", "type": "child_page", "child_page": {"title": "ワイン部門"}},
            {"id": "other-id", "type": "child_page", "child_page": {"title": "コーヒー部門"}},
        ],
        "has_more": False,
    }

    with patch("tools.requests.get", return_value=list_resp) as mock_get, \
         patch("tools.requests.post") as mock_post:
        result = _get_or_create_department_page("tok", "parent-id", "ワイン部門")

    assert result == "existing-wine-id"
    mock_get.assert_called_once()
    mock_post.assert_not_called()


def test_get_or_create_creates_when_missing(monkeypatch):
    """子ページが存在しない場合、新規作成して新しいIDを返す。"""
    list_resp = MagicMock()
    list_resp.status_code = 200
    list_resp.json.return_value = {"results": [], "has_more": False}

    create_resp = MagicMock()
    create_resp.status_code = 200
    create_resp.json.return_value = {"id": "new-wine-id"}

    with patch("tools.requests.get", return_value=list_resp), \
         patch("tools.requests.post", return_value=create_resp):
        result = _get_or_create_department_page("tok", "parent-id", "ワイン部門")

    assert result == "new-wine-id"


def test_get_or_create_returns_none_on_list_error(monkeypatch):
    """Notion API がエラーを返した場合、None を返す。"""
    list_resp = MagicMock()
    list_resp.status_code = 400
    list_resp.json.return_value = {"message": "bad request"}

    with patch("tools.requests.get", return_value=list_resp):
        result = _get_or_create_department_page("tok", "parent-id", "ワイン部門")

    assert result is None
```

- [ ] **Step 2: テストが失敗することを確認**

```bash
cd /Users/kubotahironori/ai-org && python -m pytest tests/test_tools.py::test_get_or_create_returns_existing_page_id -v
```

Expected: `ImportError` または `FAILED` (`_get_or_create_department_page` 未定義のため)

---

### Task 2: `_get_or_create_department_page` を実装する

**Files:**
- Modify: `tools.py:167`（`_create_child_page` の直前に挿入）

- [ ] **Step 1: 関数を追加する**

`tools.py` の `_create_child_page` 定義（167行目）の直前に挿入：

```python
def _get_or_create_department_page(token: str, parent_page_id: str, department_name: str) -> Optional[str]:
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "Notion-Version": "2022-06-28",
    }
    try:
        resp = requests.get(
            f"https://api.notion.com/v1/blocks/{parent_page_id}/children",
            headers=headers,
            timeout=15,
        )
        if resp.status_code != 200:
            return None
        for block in resp.json().get("results", []):
            if block.get("type") == "child_page" and block.get("child_page", {}).get("title") == department_name:
                return block["id"]
    except Exception:
        return None
    return _create_child_page(token, parent_page_id, department_name)
```

- [ ] **Step 2: テストを実行して全て通ることを確認**

```bash
cd /Users/kubotahironori/ai-org && python -m pytest tests/test_tools.py::test_get_or_create_returns_existing_page_id tests/test_tools.py::test_get_or_create_creates_when_missing tests/test_tools.py::test_get_or_create_returns_none_on_list_error -v
```

Expected: 3 tests PASSED

- [ ] **Step 3: 既存テストが壊れていないことを確認**

```bash
cd /Users/kubotahironori/ai-org && python -m pytest tests/test_tools.py -v
```

Expected: 全テスト PASSED

- [ ] **Step 4: コミット**

```bash
git add tools.py tests/test_tools.py
git commit -m "feat: add _get_or_create_department_page to tools.py"
```

---

### Task 3: `save_to_notion` に `department` 引数を追加 — テスト先行

**Files:**
- Modify: `tests/test_tools.py`

- [ ] **Step 1: テストを追加する**

`tests/test_tools.py` の末尾に追加：

```python
def test_save_to_notion_with_department_routes_to_department_page(monkeypatch):
    """department 指定時、部門ページ配下に子ページを作成する。"""
    monkeypatch.setenv("NOTION_API_KEY", "test-token")
    monkeypatch.setenv("NOTION_PAGE_ID", "parent-page-id")

    # _get_or_create_department_page が "dept-page-id" を返す
    list_resp = MagicMock()
    list_resp.status_code = 200
    list_resp.json.return_value = {
        "results": [{"id": "dept-page-id", "type": "child_page", "child_page": {"title": "ワイン部門"}}],
        "has_more": False,
    }

    create_resp = MagicMock()
    create_resp.status_code = 200
    create_resp.json.return_value = {"id": "content-child-id"}

    patch_resp = MagicMock()
    patch_resp.status_code = 200
    patch_resp.json.return_value = {}

    with patch("tools.requests.get", return_value=list_resp), \
         patch("tools.requests.post", return_value=create_resp) as mock_post, \
         patch("tools.requests.patch", return_value=patch_resp):
        result = save_to_notion("テスト", "内容", department="ワイン部門")

    assert "Notionに子ページを作成しました" in result
    # POST は部門ページ ("dept-page-id") を親として呼ばれるはず
    post_payload = mock_post.call_args[1]["json"]
    assert post_payload["parent"] == {"page_id": "dept-page-id"}


def test_save_to_notion_without_department_saves_under_parent(monkeypatch):
    """department 未指定時、親ページ直下に子ページを作成する（既存の動作を維持）。"""
    monkeypatch.setenv("NOTION_API_KEY", "test-token")
    monkeypatch.setenv("NOTION_PAGE_ID", "parent-page-id")

    create_resp = MagicMock()
    create_resp.status_code = 200
    create_resp.json.return_value = {"id": "child-id"}

    patch_resp = MagicMock()
    patch_resp.status_code = 200
    patch_resp.json.return_value = {}

    with patch("tools.requests.post", return_value=create_resp) as mock_post, \
         patch("tools.requests.patch", return_value=patch_resp):
        result = save_to_notion("テスト", "内容")

    assert "Notionに子ページを作成しました" in result
    post_payload = mock_post.call_args[1]["json"]
    assert post_payload["parent"] == {"page_id": "parent-page-id"}
```

- [ ] **Step 2: テストが失敗することを確認**

```bash
cd /Users/kubotahironori/ai-org && python -m pytest tests/test_tools.py::test_save_to_notion_with_department_routes_to_department_page -v
```

Expected: FAILED（`save_to_notion` が `department` 引数を受け付けないため）

---

### Task 4: `save_to_notion` に `department` 引数を実装する

**Files:**
- Modify: `tools.py:190`

- [ ] **Step 1: `save_to_notion` のシグネチャと内部ロジックを変更する**

`tools.py` の `save_to_notion` 関数（190行目〜）を以下に置き換える：

```python
def save_to_notion(title: str, content: str, department: Optional[str] = None) -> str:
    token = os.environ.get("NOTION_API_KEY")
    page_id = os.environ.get("NOTION_PAGE_ID")
    if not token or not page_id:
        return "NOTION_API_KEY または NOTION_PAGE_ID が未設定のためスキップ"

    if department:
        target_page_id = _get_or_create_department_page(token, page_id, department)
        if not target_page_id:
            return f"部門ページ取得エラー: '{department}' ページを作成できませんでした"
    else:
        target_page_id = page_id

    child_id = _create_child_page(token, target_page_id, title)
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

- [ ] **Step 2: 全テストを実行して通ることを確認**

```bash
cd /Users/kubotahironori/ai-org && python -m pytest tests/test_tools.py -v
```

Expected: 全テスト PASSED

- [ ] **Step 3: コミット**

```bash
git add tools.py tests/test_tools.py
git commit -m "feat: add department routing to save_to_notion"
```

---

### Task 5: `run_agent` に `department` 引数追加 + ローカルログ保存を削除 — テスト先行

**Files:**
- Modify: `tests/test_runner.py`

- [ ] **Step 1: 既存の test_runner.py を確認する**

```bash
cat /Users/kubotahironori/ai-org/tests/test_runner.py
```

- [ ] **Step 2: テストを追加する**

`tests/test_runner.py` に以下を追加（既存のインポートを流用）：

```python
from unittest.mock import patch, MagicMock, call
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from runner import run_agent


def test_run_agent_passes_department_to_save_to_notion(monkeypatch, tmp_path):
    """department 引数が save_to_notion に渡される。"""
    from datetime import datetime
    today = datetime.now().strftime('%Y-%m-%d')

    fake_response = MagicMock()
    fake_response.stop_reason = "end_turn"
    fake_response.content = [MagicMock(text="テスト出力", spec=["text"])]

    with patch("runner.client.messages.create", return_value=fake_response), \
         patch("runner.save_to_notion", return_value="OK") as mock_notion, \
         patch("runner.save_log"):
        run_agent("sommelier", "テスト", "テストラベル", department="ワイン部門")

    mock_notion.assert_called_once_with(f"テストラベル ({today})", "テスト出力", department="ワイン部門")
```

- [ ] **Step 3: テストが失敗することを確認**

```bash
cd /Users/kubotahironori/ai-org && python -m pytest tests/test_runner.py::test_run_agent_passes_department_to_save_to_notion -v
```

Expected: FAILED（`run_agent` が `department` 引数を受け付けないため）

---

### Task 6: `run_agent` を実装する

**Files:**
- Modify: `runner.py:57`

- [ ] **Step 1: `run_agent` のシグネチャと内部ロジックを変更する**

`runner.py` の `run_agent` 関数（57行目〜96行目）を以下に置き換える：

```python
def run_agent(agent_name: str, prompt: str, label: str, department: Optional[str] = None) -> str:
    system = load_agent(agent_name)
    messages = [{"role": "user", "content": prompt}]

    while True:
        response = _with_retry(
            lambda: client.messages.create(
                model=MODEL,
                max_tokens=16000,
                system=system,
                tools=TOOL_DEFINITIONS,
                messages=messages,
            ),
            label,
        )

        if response.stop_reason == "tool_use":
            messages.append({"role": "assistant", "content": response.content})
            tool_results = []
            for block in response.content:
                if block.type == "tool_use":
                    print(f"  🔍 {label} ツール実行: {block.name}({list(block.input.values())[0][:40]}...)")
                    result = execute_tool(block.name, block.input)
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": result
                    })
            messages.append({"role": "user", "content": tool_results})
        else:
            final_text = next(
                (b.text for b in response.content if hasattr(b, "text")), ""
            )
            save_log(final_text, label)
            now = datetime.now()
            notion_result = save_to_notion(f"{label} ({now.strftime('%Y-%m-%d')})", final_text, department=department)
            print(f"\n✅ {label} 完了")
            print(f"   📝 Notion: {notion_result}")
            return final_text
```

- [ ] **Step 2: `runner.py` の先頭インポートに `Optional` を追加する**

`runner.py` の1行目を確認し、`from typing import Optional` が未追加なら追加：

```python
from typing import Optional
```

- [ ] **Step 3: テストを実行して通ることを確認**

```bash
cd /Users/kubotahironori/ai-org && python -m pytest tests/test_runner.py -v
```

Expected: 全テスト PASSED

- [ ] **Step 4: コミット**

```bash
git add runner.py tests/test_runner.py
git commit -m "feat: add department arg to run_agent, remove content save_log call"
```

---

### Task 7: 全タスク関数に `department` を渡す

**Files:**
- Modify: `runner.py`（各タスク関数）

- [ ] **Step 1: 全 `run_agent()` 呼び出しに `department` を追加する**

以下の対応で `runner.py` の各 `run_agent()` 呼び出しを更新する：

| 関数 | department |
|---|---|
| `monday_task` | `"ワイン部門"` |
| `tuesday_task` | `"ワイン部門"` |
| `friday_task` | `"ワイン部門"` |
| `sunday_task` | なし（省略） |
| `_regional_wines_task_inner` | `"ワイン部門"` |
| `collab_task`（sommelier/creator 両方） | `"ワイン部門"` |
| `coffee_monday_task` | `"コーヒー部門"` |
| `coffee_regional_task` | `"コーヒー部門"` |
| `coffee_tuesday_task` | `"コーヒー部門"` |
| `coffee_friday_task` | `"コーヒー部門"` |

例（`monday_task`）:
```python
def monday_task():
    try:
        run_agent(
            "sommelier",
            "今週のコンテンツテーマを1つ提案してください。...",
            "月曜：今週テーマ決定",
            department="ワイン部門",
        )
    except Exception as e:
        print(f"  ❌ 月曜：今週テーマ決定 失敗: {e}")
```

- [ ] **Step 2: 全テストを実行して通ることを確認**

```bash
cd /Users/kubotahironori/ai-org && python -m pytest tests/ -v
```

Expected: 全テスト PASSED

- [ ] **Step 3: コミット**

```bash
git add runner.py
git commit -m "feat: route all tasks to wine/coffee departments in Notion"
```

---

### Task 8: `wednesday_task` のログパス参照を削除する

**Files:**
- Modify: `runner.py:136`

- [ ] **Step 1: `wednesday_task` を更新する**

`runner.py` の `wednesday_task` 関数を以下に置き換える：

```python
def wednesday_task():
    try:
        message = "台本が完成しました。Notion の各部門ページで確認してください。収録は明日（木曜）の予定です。"
        save_log(message, "水曜：レビュー通知")
        print(f"\n📋 レビュー依頼：Notion のワイン部門・コーヒー部門ページを確認してください。")
    except Exception as e:
        print(f"  ❌ 水曜：レビュー通知 失敗: {e}")
```

- [ ] **Step 2: 全テストを実行して通ることを確認**

```bash
cd /Users/kubotahironori/ai-org && python -m pytest tests/ -v
```

Expected: 全テスト PASSED

- [ ] **Step 3: コミット**

```bash
git add runner.py
git commit -m "chore: update wednesday_task to reference Notion instead of log file"
```
