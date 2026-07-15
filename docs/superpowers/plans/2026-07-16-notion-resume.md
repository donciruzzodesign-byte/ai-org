# Notion制作物 読み取り・ダブルチェック・続き生成 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 週次Pythonエージェントと Claude Code サブエージェントがNotionの既存制作物を読み、途中のものを続きから完成させ、途中切れを検知してオーナーのダブルチェック（要確認→完成）を経る仕組みを実装する。

**Architecture:** 既存 `tools.py:save_to_notion`（書き込み）と対になるNotion読み取り/更新関数を `tools.py` に追加し `TOOL_DEFINITIONS` に登録（A案）。`runner.py:run_agent` の生成ループを `stop_reason` で分岐させ、`max_tokens` で切れたら自動継続、なお切れたら `途中` ステータスにフォールバック。「コンテンツ生成物」DBに `ステータス` セレクトを追加し、既存ページは本文から自動仕分け。

**Tech Stack:** Python 3, `requests`（Notion REST API `Notion-Version: 2022-06-28`）, `anthropic` SDK, `pytest` + `unittest.mock`。

## Global Constraints

- Notion API は `save_to_notion` と同じ方式を踏襲: `Authorization: Bearer {NOTION_API_KEY}`、ヘッダ `Notion-Version: 2022-06-28`、`requests` で呼び、`timeout=15`。
- 環境変数（`NOTION_API_KEY` / `NOTION_DATABASE_ID`）未設定時は既存 `save_to_notion` 同様、例外を投げずスキップ相当の値を返し既存動作を壊さない。
- テストは実ネットワークを叩かない。Notion呼び出しは `unittest.mock.patch("tools.requests.*")` でモックする（既存 `tests/test_tools.py` のパターン踏襲）。
- ステータス値は文字列リテラルで統一: `"途中"` / `"要確認"` / `"完成"`。DBのセレクトプロパティ名は `"ステータス"`、カテゴリは既存の `"カテゴリ"`。
- このリポジトリは Public。APIキー等の秘密情報をコード・テスト・コミットに含めない。
- モデル・`max_tokens` 以外の `runner.py` / `app.py` の既存挙動（ログ保存、リトライ `_with_retry`、ツールループ）は変更しない。

---

## File Structure

- `tools.py`（変更）— Notion読み取り/更新関数、途中切れ判定の純粋関数、ブロック追記ヘルパー、`save_to_notion` のステータス対応、`TOOL_DEFINITIONS`・`execute_tool` への登録。
- `runner.py`（変更）— `run_agent` の `stop_reason` 分岐・自動継続・`max_tokens` 引き上げ・ステータス付き保存・WIP事前取得と既存ページへの続き反映。
- `app.py`（変更）— 手動モードの保存を `status="要確認"` で行う。
- `scripts/notion_add_status.py`（新規）— 一度きりのマイグレーション: `ステータス` プロパティ追加＋既存ページの初期仕分け。
- `tests/test_tools.py`（変更）— 新関数の単体テスト。
- `tests/test_runner.py`（変更）— `run_agent` の継続・ステータス・WIP再開テスト。
- `tests/test_notion_migration.py`（新規）— マイグレーションの仕分けロジックテスト。

---

### Task 1: 途中切れ判定の純粋関数 `_detect_completion_status`

**Files:**
- Modify: `tools.py`（`_infer_category` の下、`_create_database_page` の前あたりに追加）
- Test: `tests/test_tools.py`

**Interfaces:**
- Produces: `_detect_completion_status(content: str) -> str` — 戻り値は `"途中"` または `"要確認"`。本文が途中切れらしい（末尾が句読点・閉じ括弧・記号で終わらない／極端に短い＝80文字未満）なら `"途中"`、それ以外は `"要確認"`。

- [ ] **Step 1: 失敗するテストを書く**

`tests/test_tools.py` の末尾に追記:

```python
from tools import _detect_completion_status


def test_detect_status_complete_sentence():
    # 句点で締めくくられた十分な長さ → 要確認
    text = "バローロはピエモンテを代表する赤ワインです。" * 5
    assert _detect_completion_status(text) == "要確認"


def test_detect_status_truncated_midsentence():
    # 文の途中でブツ切れ（句読点・記号で終わらない） → 途中
    text = "バローロの熟成について説明します。まず樽熟成の期間は最低でも" 
    assert _detect_completion_status(text) == "途中"


def test_detect_status_too_short():
    # 極端に短い → 途中
    assert _detect_completion_status("テーマ決定。") == "途中"


def test_detect_status_closing_bracket_ok():
    # 閉じ括弧で終わる十分な長さ → 要確認
    text = "おすすめのペアリングはこちらです（チーズと合わせてください）" + "。詳細は本文参照。" * 5
    assert _detect_completion_status(text) == "要確認"


def test_detect_status_empty():
    assert _detect_completion_status("") == "途中"
```

- [ ] **Step 2: テストが失敗することを確認**

Run: `python3 -m pytest tests/test_tools.py -k detect_status -v`
Expected: FAIL — `ImportError: cannot import name '_detect_completion_status'`

- [ ] **Step 3: 最小実装を書く**

`tools.py` の `_infer_category` 関数の直後に追加:

```python
def _detect_completion_status(content: str) -> str:
    """本文が途中切れらしいかを判定する純粋関数。

    途中切れ（"途中"）とみなす条件:
      - 空、または実質80文字未満（短すぎる）
      - 末尾が文の終端記号（句点・感嘆符・閉じ括弧・引用符・ハッシュタグ）で終わらない
    それ以外は "要確認"。
    """
    text = (content or "").strip()
    if len(text) < 80:
        return "途中"
    # 末尾の空白・改行を除いた最後の文字
    last = text[-1]
    terminal = set("。．.!！?？」』）)】〕》>#0123456789")
    if last in terminal:
        return "要確認"
    return "途中"
```

- [ ] **Step 4: テストが通ることを確認**

Run: `python3 -m pytest tests/test_tools.py -k detect_status -v`
Expected: PASS（5件）

- [ ] **Step 5: コミット**

```bash
git add tools.py tests/test_tools.py
git commit -m "feat: Notion本文の途中切れ判定 _detect_completion_status を追加

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 2: ブロック追記ヘルパー抽出 ＋ `save_to_notion` のステータス対応

**Files:**
- Modify: `tools.py`（`save_to_notion`、`_create_database_page`）
- Test: `tests/test_tools.py`

**Interfaces:**
- Consumes: `_parse_content_to_blocks`, `_detect_completion_status`（Task 1）
- Produces:
  - `_add_blocks_to_page(token: str, page_id: str, content: str) -> Optional[str]` — 本文をブロック化し100件ずつ `PATCH /v1/blocks/{page_id}/children`。成功で `None`、失敗でエラーメッセージ文字列。
  - `save_to_notion(title: str, content: str, status: str = "要確認") -> str` — DB保存時に `ステータス` セレクトを `status` で設定。第3引数のデフォルトは `"要確認"`。

- [ ] **Step 1: 失敗するテストを書く**

`tests/test_tools.py` に追記:

```python
def test_save_to_notion_sets_status_on_database_page(monkeypatch):
    monkeypatch.setenv("NOTION_API_KEY", "test-token")
    monkeypatch.setenv("NOTION_DATABASE_ID", "db-id-123")
    monkeypatch.delenv("NOTION_PAGE_ID", raising=False)

    create_resp = MagicMock()
    create_resp.status_code = 200
    create_resp.json.return_value = {"id": "row-id"}
    patch_resp = MagicMock()
    patch_resp.status_code = 200
    patch_resp.json.return_value = {}

    with patch("tools.requests.post", return_value=create_resp) as mock_post, \
         patch("tools.requests.patch", return_value=patch_resp):
        save_to_notion("火曜：ワイン動画台本 (2026-07-16)", "## 内容\n本文", status="途中")

    props = mock_post.call_args[1]["json"]["properties"]
    assert props["ステータス"] == {"select": {"name": "途中"}}


def test_save_to_notion_default_status_is_yokakunin(monkeypatch):
    monkeypatch.setenv("NOTION_API_KEY", "test-token")
    monkeypatch.setenv("NOTION_DATABASE_ID", "db-id-123")
    monkeypatch.delenv("NOTION_PAGE_ID", raising=False)

    create_resp = MagicMock()
    create_resp.status_code = 200
    create_resp.json.return_value = {"id": "row-id"}
    patch_resp = MagicMock()
    patch_resp.status_code = 200
    patch_resp.json.return_value = {}

    with patch("tools.requests.post", return_value=create_resp) as mock_post, \
         patch("tools.requests.patch", return_value=patch_resp):
        save_to_notion("タイトル", "## 内容\n本文")

    props = mock_post.call_args[1]["json"]["properties"]
    assert props["ステータス"] == {"select": {"name": "要確認"}}
```

- [ ] **Step 2: テストが失敗することを確認**

Run: `python3 -m pytest tests/test_tools.py -k "sets_status or default_status" -v`
Expected: FAIL — `KeyError: 'ステータス'`

- [ ] **Step 3: 実装する**

3-a. `tools.py` の `_create_database_page` のシグネチャと payload にステータスを追加:

```python
def _create_database_page(token: str, database_id: str, title: str, category: str,
                          status: str = "要確認") -> Optional[str]:
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "Notion-Version": "2022-06-28",
    }
    payload = {
        "parent": {"database_id": database_id},
        "properties": {
            "title": {"title": [{"text": {"content": title}}]},
            "カテゴリ": {"select": {"name": category}},
            "ステータス": {"select": {"name": status}},
        }
    }
    try:
        resp = requests.post("https://api.notion.com/v1/pages", headers=headers,
                             json=payload, timeout=15)
        result = resp.json()
        if resp.status_code == 200:
            return result.get("id")
        return None
    except Exception:
        return None
```

3-b. ブロック追記ループを `save_to_notion` から `_add_blocks_to_page` に抽出。`save_to_notion` の下（またはすぐ上）に追加:

```python
def _add_blocks_to_page(token: str, page_id: str, content: str) -> Optional[str]:
    """本文をブロック化して100件ずつ page_id に追記。成功=None、失敗=エラー文字列。"""
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "Notion-Version": "2022-06-28",
    }
    blocks = _parse_content_to_blocks(content)
    chunk_size = 100
    for i in range(0, len(blocks), chunk_size):
        chunk = blocks[i:i + chunk_size]
        try:
            resp = requests.patch(
                f"https://api.notion.com/v1/blocks/{page_id}/children",
                headers=headers,
                json={"children": chunk},
                timeout=15,
            )
            if resp.status_code != 200:
                result = resp.json()
                return f"Notionブロック追加エラー: {result.get('message', resp.text)}"
        except Exception as e:
            return f"Notionブロック追加エラー: {e}"
    return None
```

3-c. `save_to_notion` を `status` 引数対応＋ヘルパー利用に書き換え:

```python
def save_to_notion(title: str, content: str, status: str = "要確認") -> str:
    token = os.environ.get("NOTION_API_KEY")
    database_id = os.environ.get("NOTION_DATABASE_ID")
    page_id = os.environ.get("NOTION_PAGE_ID")
    if not token or not (database_id or page_id):
        return "NOTION_API_KEY または NOTION_DATABASE_ID / NOTION_PAGE_ID が未設定のためスキップ"

    if database_id:
        child_id = _create_database_page(token, database_id, title,
                                         _infer_category(title, content), status)
        if not child_id:
            return "ページ作成エラー: Notion APIがデータベースにページを作成できませんでした"
        created_label = "データベースページ"
    else:
        child_id = _create_child_page(token, page_id, title)
        if not child_id:
            return "子ページ作成エラー: Notion APIが子ページを作成できませんでした"
        created_label = "子ページ"

    err = _add_blocks_to_page(token, child_id, content)
    if err:
        return err
    return f"Notionに{created_label}を作成しました"
```

- [ ] **Step 4: テストが通ることを確認（既存の save_to_notion テストも回帰確認）**

Run: `python3 -m pytest tests/test_tools.py -v`
Expected: PASS（既存の `test_save_to_notion_*`・`test_save_to_notion_chunks_over_100_blocks` を含め全件）

- [ ] **Step 5: コミット**

```bash
git add tools.py tests/test_tools.py
git commit -m "feat: save_to_notion にステータス設定を追加しブロック追記を _add_blocks_to_page に抽出

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 3: Notion読み取り/更新ツール群＋ツール登録

**Files:**
- Modify: `tools.py`（新関数、`TOOL_DEFINITIONS`、`execute_tool`）
- Test: `tests/test_tools.py`

**Interfaces:**
- Consumes: `_add_blocks_to_page`（Task 2）
- Produces:
  - `notion_find_wip(category: str = "") -> str` — `ステータス=途中` のDBページを検索。整形済みテキスト（`- {id} | {category} | {title}` の行、または「途中の制作物はありません」／未設定スキップ文）を返す。`category` 指定時はカテゴリでも絞る。
  - `notion_read_page(page_id: str) -> str` — ページの子ブロックのテキストを結合して返す（ページネーション対応）。
  - `notion_update_status(page_id: str, status: str) -> str` — ページの `ステータス` セレクトを更新。結果文字列を返す。
  - `notion_append_to_page(page_id: str, content: str, status: str = "要確認") -> str` — 既存ページに本文を追記しステータスを更新。
  - 上記のうちエージェントに公開するのは `notion_find_wip` / `notion_read_page` / `notion_update_status` の3つ（`TOOL_DEFINITIONS` に追加、`execute_tool` で分岐）。`notion_append_to_page` は runner.py 内部利用のため公開しない。

- [ ] **Step 1: 失敗するテストを書く**

`tests/test_tools.py` に追記:

```python
from tools import (
    notion_find_wip, notion_read_page, notion_update_status,
    notion_append_to_page, execute_tool, TOOL_DEFINITIONS,
)


def test_notion_find_wip_filters_status_and_category(monkeypatch):
    monkeypatch.setenv("NOTION_API_KEY", "test-token")
    monkeypatch.setenv("NOTION_DATABASE_ID", "db-id-123")

    resp = MagicMock()
    resp.status_code = 200
    resp.json.return_value = {
        "results": [
            {"id": "p1",
             "properties": {
                 "title": {"title": [{"plain_text": "火曜：ワイン台本"}]},
                 "カテゴリ": {"select": {"name": "ワイン"}},
             }},
        ]
    }
    with patch("tools.requests.post", return_value=resp) as mock_post:
        out = notion_find_wip("ワイン")

    body = mock_post.call_args[1]["json"]
    # ステータス=途中 と カテゴリ=ワイン の and フィルタ
    assert body["filter"]["and"][0]["select"]["equals"] == "途中"
    assert body["filter"]["and"][1]["select"]["equals"] == "ワイン"
    assert "p1" in out
    assert "火曜：ワイン台本" in out


def test_notion_find_wip_none(monkeypatch):
    monkeypatch.setenv("NOTION_API_KEY", "test-token")
    monkeypatch.setenv("NOTION_DATABASE_ID", "db-id-123")
    resp = MagicMock()
    resp.status_code = 200
    resp.json.return_value = {"results": []}
    with patch("tools.requests.post", return_value=resp):
        out = notion_find_wip("ワイン")
    assert "ありません" in out


def test_notion_read_page_joins_text(monkeypatch):
    monkeypatch.setenv("NOTION_API_KEY", "test-token")
    resp = MagicMock()
    resp.status_code = 200
    resp.json.return_value = {
        "has_more": False,
        "results": [
            {"type": "heading_2", "heading_2": {"rich_text": [{"plain_text": "オープニング"}]}},
            {"type": "paragraph", "paragraph": {"rich_text": [{"plain_text": "こんにちは"}]}},
        ],
    }
    with patch("tools.requests.get", return_value=resp):
        out = notion_read_page("page-1")
    assert "オープニング" in out
    assert "こんにちは" in out


def test_notion_update_status_patches(monkeypatch):
    monkeypatch.setenv("NOTION_API_KEY", "test-token")
    resp = MagicMock()
    resp.status_code = 200
    resp.json.return_value = {}
    with patch("tools.requests.patch", return_value=resp) as mock_patch:
        out = notion_update_status("page-1", "完成")
    url = mock_patch.call_args[0][0]
    body = mock_patch.call_args[1]["json"]
    assert "page-1" in url
    assert body["properties"]["ステータス"] == {"select": {"name": "完成"}}
    assert "完成" in out


def test_notion_tools_registered():
    names = {t["name"] for t in TOOL_DEFINITIONS}
    assert {"notion_find_wip", "notion_read_page", "notion_update_status"} <= names


def test_execute_tool_dispatches_notion_read(monkeypatch):
    monkeypatch.setenv("NOTION_API_KEY", "test-token")
    resp = MagicMock()
    resp.status_code = 200
    resp.json.return_value = {"has_more": False, "results": []}
    with patch("tools.requests.get", return_value=resp):
        out = execute_tool("notion_read_page", {"page_id": "p1"})
    assert isinstance(out, str)


def test_notion_find_wip_skips_without_env(monkeypatch):
    monkeypatch.delenv("NOTION_API_KEY", raising=False)
    monkeypatch.delenv("NOTION_DATABASE_ID", raising=False)
    out = notion_find_wip("ワイン")
    assert "未設定" in out
```

- [ ] **Step 2: テストが失敗することを確認**

Run: `python3 -m pytest tests/test_tools.py -k "notion_find_wip or notion_read_page or notion_update_status or notion_tools_registered or execute_tool_dispatches" -v`
Expected: FAIL — `ImportError: cannot import name 'notion_find_wip'`

- [ ] **Step 3: 実装する**

3-a. `tools.py` に関数群を追加（`save_to_notion` の下）:

```python
def _notion_headers(token: str) -> dict:
    return {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "Notion-Version": "2022-06-28",
    }


def notion_find_wip(category: str = "") -> str:
    """ステータス=途中 のDBページを検索して一覧テキストを返す。"""
    token = os.environ.get("NOTION_API_KEY")
    database_id = os.environ.get("NOTION_DATABASE_ID")
    if not token or not database_id:
        return "NOTION_API_KEY / NOTION_DATABASE_ID が未設定のためスキップ"

    filters = [{"property": "ステータス", "select": {"equals": "途中"}}]
    if category:
        filters.append({"property": "カテゴリ", "select": {"equals": category}})
    body = {"filter": {"and": filters}}
    try:
        resp = requests.post(
            f"https://api.notion.com/v1/databases/{database_id}/query",
            headers=_notion_headers(token), json=body, timeout=15,
        )
        if resp.status_code != 200:
            return f"Notion検索エラー: {resp.json().get('message', resp.text)}"
        results = resp.json().get("results", [])
    except Exception as e:
        return f"Notion検索エラー: {e}"

    if not results:
        return "途中の制作物はありません"
    lines = []
    for page in results:
        pid = page.get("id", "")
        props = page.get("properties", {})
        title_arr = props.get("title", {}).get("title", [])
        title = title_arr[0].get("plain_text", "") if title_arr else "(無題)"
        cat = props.get("カテゴリ", {}).get("select") or {}
        lines.append(f"- {pid} | {cat.get('name', '')} | {title}")
    return "途中の制作物:\n" + "\n".join(lines)


def _extract_block_text(block: dict) -> str:
    btype = block.get("type", "")
    payload = block.get(btype, {})
    rich = payload.get("rich_text", []) if isinstance(payload, dict) else []
    return "".join(r.get("plain_text", "") for r in rich)


def notion_read_page(page_id: str) -> str:
    """ページの子ブロックのテキストを結合して返す（ページネーション対応）。"""
    token = os.environ.get("NOTION_API_KEY")
    if not token:
        return "NOTION_API_KEY が未設定のためスキップ"
    texts = []
    cursor = None
    try:
        while True:
            url = f"https://api.notion.com/v1/blocks/{page_id}/children?page_size=100"
            if cursor:
                url += f"&start_cursor={cursor}"
            resp = requests.get(url, headers=_notion_headers(token), timeout=15)
            if resp.status_code != 200:
                return f"Notion読み取りエラー: {resp.json().get('message', resp.text)}"
            data = resp.json()
            for block in data.get("results", []):
                texts.append(_extract_block_text(block))
            if data.get("has_more"):
                cursor = data.get("next_cursor")
            else:
                break
    except Exception as e:
        return f"Notion読み取りエラー: {e}"
    return "\n".join(t for t in texts if t)


def notion_update_status(page_id: str, status: str) -> str:
    """ページの ステータス セレクトを更新する。"""
    token = os.environ.get("NOTION_API_KEY")
    if not token:
        return "NOTION_API_KEY が未設定のためスキップ"
    body = {"properties": {"ステータス": {"select": {"name": status}}}}
    try:
        resp = requests.patch(
            f"https://api.notion.com/v1/pages/{page_id}",
            headers=_notion_headers(token), json=body, timeout=15,
        )
        if resp.status_code != 200:
            return f"ステータス更新エラー: {resp.json().get('message', resp.text)}"
    except Exception as e:
        return f"ステータス更新エラー: {e}"
    return f"ステータスを{status}に更新しました"


def notion_append_to_page(page_id: str, content: str, status: str = "要確認") -> str:
    """既存ページに本文を追記し、ステータスを更新する（runner内部利用）。"""
    token = os.environ.get("NOTION_API_KEY")
    if not token:
        return "NOTION_API_KEY が未設定のためスキップ"
    err = _add_blocks_to_page(token, page_id, content)
    if err:
        return err
    return notion_update_status(page_id, status)
```

3-b. `TOOL_DEFINITIONS`（`tools.py` 冒頭のリスト）末尾に3件追加:

```python
    {
        "name": "notion_find_wip",
        "description": (
            "Notionの『コンテンツ生成物』DBから、まだ完成していない（ステータス=途中）制作物を検索します。"
            "続きを作る前に呼び、途中の下書きがないか確認してください。"
            "category に『ワイン』『コーヒー』を指定するとそのカテゴリだけに絞れます。"
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "category": {
                    "type": "string",
                    "description": "絞り込むカテゴリ（ワイン / コーヒー）。省略時は全カテゴリ。",
                }
            },
            "required": []
        }
    },
    {
        "name": "notion_read_page",
        "description": "Notionページの本文テキストを読み取ります。notion_find_wip で得たページIDを渡し、途中の内容を把握して続きを書くのに使います。",
        "input_schema": {
            "type": "object",
            "properties": {
                "page_id": {"type": "string", "description": "読み取るNotionページのID"}
            },
            "required": ["page_id"]
        }
    },
    {
        "name": "notion_update_status",
        "description": (
            "Notionページのステータスを更新します。値は『途中』『要確認』『完成』のいずれか。"
            "途中の制作物を完成させたら『要確認』に更新してください（最終確認はオーナーが行います）。"
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "page_id": {"type": "string", "description": "更新するNotionページのID"},
                "status": {"type": "string", "description": "途中 / 要確認 / 完成 のいずれか"}
            },
            "required": ["page_id", "status"]
        }
    }
```

3-c. `execute_tool` に分岐を追加:

```python
def execute_tool(name: str, inputs: dict) -> str:
    if name == "web_search":
        return web_search(inputs["query"], inputs.get("region", "jp-jp"))
    elif name == "search_papers":
        return search_papers(inputs["query"])
    elif name == "fetch_page":
        return fetch_page(inputs["url"])
    elif name == "notion_find_wip":
        return notion_find_wip(inputs.get("category", ""))
    elif name == "notion_read_page":
        return notion_read_page(inputs["page_id"])
    elif name == "notion_update_status":
        return notion_update_status(inputs["page_id"], inputs["status"])
    return f"不明なツール: {name}"
```

- [ ] **Step 4: テストが通ることを確認**

Run: `python3 -m pytest tests/test_tools.py -v`
Expected: PASS（全件）

- [ ] **Step 5: コミット**

```bash
git add tools.py tests/test_tools.py
git commit -m "feat: Notion読み取り/更新ツール(find_wip/read_page/update_status)を追加しツール登録

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 4: `run_agent` の途中切れ検知＆自動継続＆ステータス付き保存

**Files:**
- Modify: `runner.py`（`run_agent`、`import`）
- Test: `tests/test_runner.py`

**Interfaces:**
- Consumes: `save_to_notion(title, content, status)`（Task 2）
- Produces: `run_agent(agent_name, prompt, label, max_continuations=3)` — `stop_reason` を分岐。`max_tokens` で切れたら続きを促して最大 `max_continuations` 回まで再生成し全文を結合。なお切れたら `save_to_notion(..., status="途中")`、正常完了は `status="要確認"`。`max_tokens` 上限は 32000。戻り値は結合済み全文（既存同様）。

**注:** WIP事前取得（既存の途中原稿を読み込んで続きから書く処理）は Task 5 で追加する。本タスクは切れ検知と保存ステータスに集中する。

- [ ] **Step 1: 失敗するテストを書く**

`tests/test_runner.py` を確認し、末尾に追記（新規なら下記ヘッダも含めて作成）:

```python
import os
import sys
from unittest.mock import patch, MagicMock
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


def _text_response(text, stop_reason):
    block = MagicMock()
    block.type = "text"
    block.text = text
    resp = MagicMock()
    resp.stop_reason = stop_reason
    resp.content = [block]
    return resp


def test_run_agent_saves_yokakunin_on_normal_finish(monkeypatch):
    import runner
    resp = _text_response("完成した台本です。ここまでで終わり。", "end_turn")
    with patch.object(runner.client.messages, "create", return_value=resp), \
         patch.object(runner, "save_to_notion", return_value="ok") as mock_save, \
         patch.object(runner, "save_log"), \
         patch.object(runner, "notion_find_wip", return_value="途中の制作物はありません"):
        runner.run_agent("creator", "台本を書いて", "火曜：動画台本作成")
    # status キーワード引数が 要確認
    assert mock_save.call_args.kwargs.get("status") == "要確認"


def test_run_agent_auto_continues_on_max_tokens(monkeypatch):
    import runner
    first = _text_response("前半の途中まで", "max_tokens")
    second = _text_response("後半の続き。完了。", "end_turn")
    with patch.object(runner.client.messages, "create", side_effect=[first, second]) as mock_create, \
         patch.object(runner, "save_to_notion", return_value="ok") as mock_save, \
         patch.object(runner, "save_log"), \
         patch.object(runner, "notion_find_wip", return_value="途中の制作物はありません"):
        result = runner.run_agent("creator", "台本を書いて", "火曜：動画台本作成")
    # 2回呼ばれ、全文が結合され、要確認で保存
    assert mock_create.call_count == 2
    assert "前半の途中まで" in result and "後半の続き" in result
    assert mock_save.call_args.kwargs.get("status") == "要確認"


def test_run_agent_falls_back_to_tochu_when_still_truncated(monkeypatch):
    import runner
    trunc = _text_response("延々と切れ続ける", "max_tokens")
    with patch.object(runner.client.messages, "create", return_value=trunc), \
         patch.object(runner, "save_to_notion", return_value="ok") as mock_save, \
         patch.object(runner, "save_log"), \
         patch.object(runner, "notion_find_wip", return_value="途中の制作物はありません"):
        runner.run_agent("creator", "台本を書いて", "火曜：動画台本作成", max_continuations=2)
    assert mock_save.call_args.kwargs.get("status") == "途中"
```

- [ ] **Step 2: テストが失敗することを確認**

Run: `python3 -m pytest tests/test_runner.py -k run_agent -v`
Expected: FAIL（`save_to_notion` が status 引数なしで呼ばれる／`notion_find_wip` 属性が無い 等）

- [ ] **Step 3: 実装する**

3-a. `runner.py` の import 行（`from tools import ...`）を更新:

```python
from tools import (
    TOOL_DEFINITIONS, execute_tool, save_to_notion,
    notion_find_wip, notion_read_page, notion_append_to_page, _infer_category,
)
```

3-b. `run_agent` を書き換え（`max_tokens` を 32000、`stop_reason` 分岐、自動継続、ステータス保存）:

```python
def run_agent(agent_name: str, prompt: str, label: str, max_continuations: int = 3) -> str:
    system = load_agent(agent_name)
    messages = [{"role": "user", "content": prompt}]

    accumulated = ""
    continuations = 0
    truncated = False

    while True:
        response = _with_retry(
            lambda: client.messages.create(
                model=MODEL,
                max_tokens=32000,
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
                    print(f"  🔍 {label} ツール実行: {block.name}({str(list(block.input.values())[0])[:40] if block.input else ''}...)")
                    result = execute_tool(block.name, block.input)
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": result,
                    })
            messages.append({"role": "user", "content": tool_results})
            continue

        segment = "".join(b.text for b in response.content if hasattr(b, "text"))
        accumulated += segment

        if response.stop_reason == "max_tokens" and continuations < max_continuations:
            messages.append({"role": "assistant", "content": response.content})
            messages.append({
                "role": "user",
                "content": "文字数上限で途中で切れました。前の文章の続きから、繰り返さずに最後まで書き続けてください。",
            })
            continuations += 1
            continue

        if response.stop_reason == "max_tokens":
            truncated = True
        break

    final_text = accumulated
    save_log(final_text, label)
    now = datetime.now()
    status = "途中" if truncated else "要確認"
    print(f"\n{'⚠️ 途中保存' if truncated else '✅'} {label} 完了（{status}）")
    notion_result = save_to_notion(f"{label} ({now.strftime('%Y-%m-%d')})", final_text, status=status)
    print(f"   📝 Notion: {notion_result}")
    return final_text
```

- [ ] **Step 4: テストが通ることを確認**

Run: `python3 -m pytest tests/test_runner.py -k run_agent -v`
Expected: PASS（3件）

- [ ] **Step 5: コミット**

```bash
git add runner.py tests/test_runner.py
git commit -m "fix: run_agentがmax_tokens途中切れを検知し自動継続＋要確認/途中で保存

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 5: `run_agent` にWIP事前取得と既存ページへの続き反映

**Files:**
- Modify: `runner.py`（`run_agent`）
- Test: `tests/test_runner.py`

**Interfaces:**
- Consumes: `notion_find_wip`, `notion_read_page`, `notion_append_to_page`, `_infer_category`（Task 3 で import 済み）
- Produces: `run_agent` が実行冒頭に同カテゴリ（`ワイン`/`コーヒー`のみ）の途中原稿を探し、あれば本文をプロンプトに注入して続きから書かせ、完成時は**新規作成せず既存ページに追記**してステータス更新する。

**WIPページID抽出の契約:** `notion_find_wip` の戻り先頭行は `- {page_id} | {category} | {title}` 形式（Task 3）。先頭行から page_id を取り出す内部ヘルパー `_first_wip_page_id(find_output: str) -> str` を runner.py に置く（該当なしは空文字）。

- [ ] **Step 1: 失敗するテストを書く**

`tests/test_runner.py` に追記:

```python
def test_first_wip_page_id_parses_first_line():
    import runner
    out = "途中の制作物:\n- pageABC | ワイン | 火曜：ワイン台本\n- pageXYZ | ワイン | 別件"
    assert runner._first_wip_page_id(out) == "pageABC"


def test_first_wip_page_id_none():
    import runner
    assert runner._first_wip_page_id("途中の制作物はありません") == ""


def test_run_agent_resumes_existing_wip_page(monkeypatch):
    import runner
    resp = _text_response("続きを書いて完成させました。以上です。", "end_turn")
    find_out = "途中の制作物:\n- pageABC | ワイン | 火曜：ワイン台本"
    with patch.object(runner.client.messages, "create", return_value=resp) as mock_create, \
         patch.object(runner, "notion_find_wip", return_value=find_out), \
         patch.object(runner, "notion_read_page", return_value="前回の途中原稿本文") as mock_read, \
         patch.object(runner, "notion_append_to_page", return_value="更新しました") as mock_append, \
         patch.object(runner, "save_to_notion", return_value="ok") as mock_save, \
         patch.object(runner, "save_log"):
        runner.run_agent("creator", "ワインの台本を書いて", "火曜：ワイン動画台本作成")

    # 既存原稿を読み、プロンプトに注入して生成、既存ページへ追記、新規保存はしない
    mock_read.assert_called_once_with("pageABC")
    sent_messages = mock_create.call_args.kwargs["messages"]
    assert "前回の途中原稿本文" in sent_messages[0]["content"]
    mock_append.assert_called_once()
    assert mock_append.call_args[0][0] == "pageABC"
    assert mock_append.call_args.kwargs.get("status") == "要確認"
    mock_save.assert_not_called()
```

- [ ] **Step 2: テストが失敗することを確認**

Run: `python3 -m pytest tests/test_runner.py -k "wip or resumes" -v`
Expected: FAIL — `AttributeError: module 'runner' has no attribute '_first_wip_page_id'`

- [ ] **Step 3: 実装する**

3-a. `runner.py` に `_first_wip_page_id` ヘルパーを追加（`run_agent` の上）:

```python
def _first_wip_page_id(find_output: str) -> str:
    """notion_find_wip の出力先頭行から page_id を取り出す。該当なしは空文字。"""
    for line in find_output.splitlines():
        line = line.strip()
        if line.startswith("- "):
            parts = line[2:].split("|")
            if parts:
                return parts[0].strip()
    return ""
```

3-b. `run_agent` の冒頭（`messages = [...]` の前）にWIP事前取得を挿入し、保存分岐を既存ページ追記に対応させる。`run_agent` を次の形に更新:

```python
def run_agent(agent_name: str, prompt: str, label: str, max_continuations: int = 3) -> str:
    system = load_agent(agent_name)

    # 途中の制作物があれば読み込み、続きから書かせる（ワイン/コーヒーのみ対象）
    resume_page_id = ""
    category = _infer_category(label, prompt)
    if category in ("ワイン", "コーヒー"):
        find_out = notion_find_wip(category)
        resume_page_id = _first_wip_page_id(find_out)
        if resume_page_id:
            existing = notion_read_page(resume_page_id)
            if existing and not existing.endswith("スキップ") and "エラー" not in existing[:12]:
                prompt = (
                    prompt
                    + "\n\n【前回の途中原稿】以下は前回、途中まで作成した内容です。"
                    + "繰り返さず、この続きから書いて全体を完成させてください:\n\n"
                    + existing
                )

    messages = [{"role": "user", "content": prompt}]
    accumulated = ""
    continuations = 0
    truncated = False

    while True:
        response = _with_retry(
            lambda: client.messages.create(
                model=MODEL,
                max_tokens=32000,
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
                    print(f"  🔍 {label} ツール実行: {block.name}({str(list(block.input.values())[0])[:40] if block.input else ''}...)")
                    result = execute_tool(block.name, block.input)
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": result,
                    })
            messages.append({"role": "user", "content": tool_results})
            continue

        segment = "".join(b.text for b in response.content if hasattr(b, "text"))
        accumulated += segment

        if response.stop_reason == "max_tokens" and continuations < max_continuations:
            messages.append({"role": "assistant", "content": response.content})
            messages.append({
                "role": "user",
                "content": "文字数上限で途中で切れました。前の文章の続きから、繰り返さずに最後まで書き続けてください。",
            })
            continuations += 1
            continue

        if response.stop_reason == "max_tokens":
            truncated = True
        break

    final_text = accumulated
    save_log(final_text, label)
    now = datetime.now()
    status = "途中" if truncated else "要確認"
    print(f"\n{'⚠️ 途中保存' if truncated else '✅'} {label} 完了（{status}）")

    if resume_page_id:
        notion_result = notion_append_to_page(resume_page_id, final_text, status=status)
    else:
        notion_result = save_to_notion(f"{label} ({now.strftime('%Y-%m-%d')})", final_text, status=status)
    print(f"   📝 Notion: {notion_result}")
    return final_text
```

- [ ] **Step 4: テストが通ることを確認（Task 4 の run_agent テストも回帰確認）**

Run: `python3 -m pytest tests/test_runner.py -v`
Expected: PASS（Task 4 の3件は `notion_find_wip` が「ありません」を返すため resume されず、既存アサーションを満たす）

- [ ] **Step 5: コミット**

```bash
git add runner.py tests/test_runner.py
git commit -m "feat: run_agentが途中の制作物を読み込み続きから完成させ既存ページへ反映

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 6: 手動モード（app.py）のステータス保存

**Files:**
- Modify: `app.py`（保存呼び出し、`max_tokens`）
- Test: `tests/test_app.py`

**Interfaces:**
- Consumes: `save_to_notion(title, content, status)`（Task 2）
- Produces: 手動モードの保存を `status="要確認"` で行う。`max_tokens` を 32000 に引き上げる。

- [ ] **Step 1: 失敗するテストを書く**

`tests/test_app.py` を確認し追記（既存の構造に合わせる。無ければ下記で新規作成）:

```python
import os, sys, re
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


def test_app_saves_with_yokakunin_status():
    # app.py が save_to_notion を status="要確認" 付きで呼ぶことをソース上で保証する
    with open(os.path.join(os.path.dirname(__file__), '..', 'app.py'), encoding='utf-8') as f:
        src = f.read()
    assert re.search(r'save_to_notion\([^)]*status\s*=\s*"要確認"', src, re.S)
    assert "max_tokens=32000" in src
```

- [ ] **Step 2: テストが失敗することを確認**

Run: `python3 -m pytest tests/test_app.py -k yokakunin -v`
Expected: FAIL — 現状は `status` 引数なし・`max_tokens=16000`

- [ ] **Step 3: 実装する**

`app.py` の該当箇所を変更:
- `max_tokens=16000` → `max_tokens=32000`（`app.py:85`）
- 保存呼び出し（`app.py:116`）:

```python
                notion_result = save_to_notion(title, final_text, status="要確認")
```

- [ ] **Step 4: テストが通ることを確認**

Run: `python3 -m pytest tests/test_app.py -k yokakunin -v`
Expected: PASS

- [ ] **Step 5: コミット**

```bash
git add app.py tests/test_app.py
git commit -m "feat: 手動モードの保存を要確認ステータス＋max_tokens 32000に

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 7: 一度きりのマイグレーション（ステータス追加＋既存ページ仕分け）

**Files:**
- Create: `scripts/notion_add_status.py`
- Test: `tests/test_notion_migration.py`

**Interfaces:**
- Consumes: `_detect_completion_status`（Task 1）, `notion_read_page`（Task 3）
- Produces:
  - `classify_existing_page(page_id: str) -> str` — 既存ページの本文を読み `_detect_completion_status` で `途中`/`要確認` を返す。
  - `main()` — `NOTION_DATABASE_ID` のDBに `ステータス` セレクトプロパティ（選択肢 `途中`/`要確認`/`完成`）を作成し、全既存ページを走査して `classify_existing_page` の結果でステータスを設定する。ネットワーク実行は手動（`python3 scripts/notion_add_status.py`）。

- [ ] **Step 1: 失敗するテストを書く**

`tests/test_notion_migration.py`:

```python
import os, sys
from unittest.mock import patch
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from scripts.notion_add_status import classify_existing_page


def test_classify_truncated(monkeypatch):
    with patch("scripts.notion_add_status.notion_read_page",
               return_value="樽熟成の期間は最低でも"):
        assert classify_existing_page("p1") == "途中"


def test_classify_complete(monkeypatch):
    long_done = "バローロはピエモンテを代表する赤ワインです。" * 5
    with patch("scripts.notion_add_status.notion_read_page", return_value=long_done):
        assert classify_existing_page("p1") == "要確認"
```

- [ ] **Step 2: テストが失敗することを確認**

Run: `python3 -m pytest tests/test_notion_migration.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'scripts.notion_add_status'`

- [ ] **Step 3: 実装する**

3-a. `scripts/__init__.py`（空ファイル）を作成。

3-b. `scripts/notion_add_status.py`:

```python
"""一度きりのマイグレーション: コンテンツ生成物DBに『ステータス』を追加し既存ページを仕分ける。

使い方: リポジトリ直下で `python3 scripts/notion_add_status.py`
NOTION_API_KEY / NOTION_DATABASE_ID が必要。
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

import requests
from tools import _detect_completion_status, notion_read_page, notion_update_status, _notion_headers


def classify_existing_page(page_id: str) -> str:
    content = notion_read_page(page_id)
    return _detect_completion_status(content)


def _ensure_status_property(token: str, database_id: str) -> None:
    body = {
        "properties": {
            "ステータス": {
                "select": {
                    "options": [
                        {"name": "途中", "color": "yellow"},
                        {"name": "要確認", "color": "orange"},
                        {"name": "完成", "color": "green"},
                    ]
                }
            }
        }
    }
    resp = requests.patch(
        f"https://api.notion.com/v1/databases/{database_id}",
        headers=_notion_headers(token), json=body, timeout=15,
    )
    print(f"プロパティ追加: {resp.status_code}")


def _iter_page_ids(token: str, database_id: str):
    cursor = None
    while True:
        body = {}
        if cursor:
            body["start_cursor"] = cursor
        resp = requests.post(
            f"https://api.notion.com/v1/databases/{database_id}/query",
            headers=_notion_headers(token), json=body, timeout=15,
        )
        data = resp.json()
        for page in data.get("results", []):
            yield page["id"]
        if data.get("has_more"):
            cursor = data.get("next_cursor")
        else:
            break


def main() -> None:
    token = os.environ.get("NOTION_API_KEY")
    database_id = os.environ.get("NOTION_DATABASE_ID")
    if not token or not database_id:
        print("NOTION_API_KEY / NOTION_DATABASE_ID が未設定です。")
        return
    _ensure_status_property(token, database_id)
    for page_id in _iter_page_ids(token, database_id):
        status = classify_existing_page(page_id)
        print(f"{page_id} -> {status}: {notion_update_status(page_id, status)}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: テストが通ることを確認**

Run: `python3 -m pytest tests/test_notion_migration.py -v`
Expected: PASS（2件）

- [ ] **Step 5: コミット**

```bash
git add scripts/__init__.py scripts/notion_add_status.py tests/test_notion_migration.py
git commit -m "feat: ステータスDBプロパティ追加＋既存ページ仕分けのマイグレーションスクリプト

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 8: 全体回帰＋ドキュメント更新

**Files:**
- Modify: `CLAUDE.md`（Notionステータス運用と続き生成の説明を追記）
- Test: 既存全テスト

- [ ] **Step 1: 全テストを実行して回帰がないことを確認**

Run: `python3 -m pytest tests/ -v`
Expected: PASS（全件。既存テストを壊していないこと）

- [ ] **Step 2: `CLAUDE.md` に運用を追記**

`## 環境変数（.env）` セクションの後、または `## エージェント構成` の前に次を追加:

```markdown
## Notionステータスと続き生成

「コンテンツ生成物」DBの各ページに `ステータス`（`途中` / `要確認` / `完成`）を持たせる。

- エージェントは完成候補を `要確認` で保存する（`完成` はオーナーが最終確認して手動で付ける）。
- `max_tokens` で途中切れした生成は自動継続し、なお切れたら `途中` で保存され次回に続きが作られる。
- 週次エージェントは実行時、同カテゴリの `途中` ページがあれば本文を読み込み、続きから完成させて同じページへ反映する。
- Claude Code から手動で「この途中のやつを続けて」と頼めば、`notion_find_wip` / `notion_read_page` で該当ページを読み続きを作れる。
- 初回のみ `python3 scripts/notion_add_status.py` を実行して `ステータス` プロパティ追加と既存ページの自動仕分けを行う。
```

- [ ] **Step 3: コミット**

```bash
git add CLAUDE.md
git commit -m "docs: Notionステータス運用と続き生成の説明をCLAUDE.mdに追記

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Self-Review

**Spec coverage（仕様書の各項目 → 対応タスク）:**
- ステータス・データモデル（設計1） → Task 2（保存時付与）, Task 7（プロパティ作成・既存仕分け）
- 途中切れ検知＆自動継続（設計2） → Task 4（`stop_reason` 分岐・自動継続・`max_tokens` 32000）
- 読み取り/更新ツール（設計3） → Task 3
- 続きを作るフロー（設計4） → Task 5（WIP事前取得・既存ページ反映）
- これまでの制作物への対応（設計5） → Task 7（自動仕分け）＋ Task 5（再開）
- 途中切れ判定の純粋関数（設計6） → Task 1
- テスト設計 → 各タスクのテスト＋ Task 8 の全体回帰
- 手動モード（app.py, 影響範囲） → Task 6

**Placeholder scan:** TODO/TBD等なし。全コードステップに実コードを記載済み。

**Type consistency:** `save_to_notion(title, content, status)`, `notion_find_wip(category)`, `notion_read_page(page_id)`, `notion_update_status(page_id, status)`, `notion_append_to_page(page_id, content, status)`, `_detect_completion_status(content)`, `_add_blocks_to_page(token, page_id, content)`, `_first_wip_page_id(find_output)`, `_notion_headers(token)` は定義（Task 2/3）と利用（Task 4/5/7）で一致。`notion_find_wip` の出力形式 `- {id} | {cat} | {title}` は Task 3 の実装と Task 5 の `_first_wip_page_id` パーサで一致。
