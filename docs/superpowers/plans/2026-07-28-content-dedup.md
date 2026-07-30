# 週次コンテンツ重複回避システム Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 週次エージェント（sommelier/barista/creator/marketer）が新しいテーマ・コンテンツを生成する前に、Notionに保存済みの直近8件の同カテゴリテーマを参考情報として受け取り、産地・品種・切り口の重複を減らす。

**Architecture:** `tools.py` に一言テーマ抽出（Haiku呼び出し）とNotionからの直近テーマ取得関数を追加し、`runner.py` の `run_agent()` 内（全呼び出し元が経由する唯一の入口）に注入ロジックを集約する。呼び出し元のタスク関数（`monday_task` 等13箇所）は無変更。

**Tech Stack:** 既存の `anthropic` SDK・`requests`（Notion API直叩き）を踏襲。新規ライブラリ追加なし。

## Global Constraints

- Notion「コンテンツ生成物」DBへの新規プロパティ名は `テーマ`（rich_text型）
- テーマ抽出には `claude-haiku-4-5-20251001` を使う（既存の `runner.MODEL`=`claude-sonnet-4-6` とは別。低コスト・低レイテンシのため）
- 重複回避コンテキストの注入・テーマ抽出は `category`（`_infer_category` の結果）が `"ワイン"` または `"コーヒー"` の場合のみ行う。`"その他"` の場合は一切呼ばない（日曜の反応分析レポートなどが対象外になるのは意図した動作）
- 既存関数への変更は必ずデフォルト引数で後方互換を保つ（`theme: str = ""`）
- 全ステップTDD：失敗するテストを先に書き、実装し、パスを確認してからコミット

---

## 事前確認

このplanを実行する前に、`docs/superpowers/specs/2026-07-27-content-dedup-design.md` の設計に承認済みであることを前提とする。

---

## Task 1: テーマ抽出関数 `extract_theme`

**Files:**
- Modify: `tools.py`（`_detect_completion_status` 関数の直後、266行目付近に追加）
- Test: `tests/test_tools.py`

**Interfaces:**
- Produces:
  - `_get_anthropic_client()` — モジュールレベルの遅延初期化シングルトン。テストからは `patch("tools._get_anthropic_client", ...)` でモック可能
  - `extract_theme(content: str) -> str` — 本文から20文字以内の一言テーマを抽出。失敗・空入力時は `""`

- [ ] **Step 1: 失敗するテストを書く**

`tests/test_tools.py` の末尾に追記:

```python
def test_extract_theme_returns_summary_text():
    from tools import extract_theme
    fake_client = MagicMock()
    fake_resp = MagicMock()
    fake_resp.content = [MagicMock(text="ピエモンテ州のネッビオーロ特集", spec=["text"])]
    fake_client.messages.create.return_value = fake_resp
    with patch("tools._get_anthropic_client", return_value=fake_client):
        result = extract_theme("今週はピエモンテ州のネッビオーロについて特集します。" * 3)
    assert result == "ピエモンテ州のネッビオーロ特集"
    fake_client.messages.create.assert_called_once()
    kwargs = fake_client.messages.create.call_args.kwargs
    assert kwargs["model"] == "claude-haiku-4-5-20251001"


def test_extract_theme_returns_empty_on_exception():
    from tools import extract_theme
    with patch("tools._get_anthropic_client", side_effect=Exception("no api key")):
        result = extract_theme("何かの内容")
    assert result == ""


def test_extract_theme_returns_empty_for_empty_content():
    from tools import extract_theme
    assert extract_theme("") == ""
    assert extract_theme("   ") == ""
```

- [ ] **Step 2: テストを実行して失敗することを確認**

Run: `python3 -m pytest tests/test_tools.py -v -k extract_theme`
Expected: FAIL（`extract_theme` が未定義、`ImportError`）

- [ ] **Step 3: 実装を追加**

`tools.py` の `_detect_completion_status` 関数（`return "要確認"` で終わる関数）の直後、`_create_database_page` の直前に挿入:

```python
_anthropic_client = None


def _get_anthropic_client():
    global _anthropic_client
    if _anthropic_client is None:
        import anthropic
        _anthropic_client = anthropic.Anthropic()
    return _anthropic_client


def extract_theme(content: str) -> str:
    """生成された本文から重複回避用の一言テーマ（20文字以内）を抽出する。失敗時は空文字列。"""
    if not content or not content.strip():
        return ""
    try:
        client = _get_anthropic_client()
        resp = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=60,
            messages=[{
                "role": "user",
                "content": (
                    "以下の文章の主題を日本語で20文字以内の1行で要約してください。"
                    "要約のみを出力し、他の説明は書かないでください。\n\n" + content[:3000]
                ),
            }],
        )
        return "".join(b.text for b in resp.content if hasattr(b, "text")).strip()
    except Exception:
        return ""
```

- [ ] **Step 4: テストを実行して通過することを確認**

Run: `python3 -m pytest tests/test_tools.py -v -k extract_theme`
Expected: 3 passed

- [ ] **Step 5: コミット**

```bash
git add tools.py tests/test_tools.py
git commit -m "feat: 本文から重複回避用テーマを抽出するextract_themeを実装"
```

---

## Task 2: 直近テーマ取得関数 `notion_recent_themes`

**Files:**
- Modify: `tools.py`（`_extract_title` 関数の直後に `_extract_rich_text` を追加、`notion_find_wip` 関数の直後に `notion_recent_themes` を追加）
- Test: `tests/test_tools.py`

**Interfaces:**
- Consumes: `_notion_headers`（既存）、`_extract_title`（既存）
- Produces:
  - `_extract_rich_text(prop: dict) -> str` — rich_textプロパティからプレーンテキストを結合
  - `notion_recent_themes(category: str, limit: int = 8) -> str` — 指定カテゴリの直近`limit`件のテーマ一覧（`- テーマ（タイトル）` の改行区切り文字列）。取得不可・0件時は `""`

- [ ] **Step 1: 失敗するテストを書く**

`tests/test_tools.py` の末尾に追記:

```python
def test_extract_rich_text_joins_plain_text():
    from tools import _extract_rich_text
    prop = {"rich_text": [{"plain_text": "ピエモンテ州の"}, {"plain_text": "ネッビオーロ"}]}
    assert _extract_rich_text(prop) == "ピエモンテ州のネッビオーロ"
    assert _extract_rich_text({"rich_text": []}) == ""
    assert _extract_rich_text({}) == ""
    assert _extract_rich_text(None) == ""


def test_notion_recent_themes_queries_by_category_sorted_desc(monkeypatch):
    from tools import notion_recent_themes
    monkeypatch.setenv("NOTION_API_KEY", "test-token")
    monkeypatch.setenv("NOTION_DATABASE_ID", "db-id-123")

    resp = MagicMock()
    resp.status_code = 200
    resp.json.return_value = {
        "results": [
            {"properties": {
                "名前": {"type": "title", "title": [{"plain_text": "月曜：今週テーマ決定 (2026-07-20)"}]},
                "テーマ": {"rich_text": [{"plain_text": "ピエモンテ州のネッビオーロ"}]},
            }},
            {"properties": {
                "名前": {"type": "title", "title": [{"plain_text": "月曜：州別おすすめワイン紹介 (2026-07-13)"}]},
                "テーマ": {"rich_text": [{"plain_text": "トスカーナ州のサンジョヴェーゼ"}]},
            }},
        ]
    }
    with patch("tools.requests.post", return_value=resp) as mock_post:
        out = notion_recent_themes("ワイン", limit=8)

    body = mock_post.call_args[1]["json"]
    assert body["filter"] == {"property": "カテゴリ", "select": {"equals": "ワイン"}}
    assert body["sorts"] == [{"timestamp": "created_time", "direction": "descending"}]
    assert body["page_size"] == 8
    assert "ピエモンテ州のネッビオーロ" in out
    assert "トスカーナ州のサンジョヴェーゼ" in out
    assert "月曜：今週テーマ決定 (2026-07-20)" in out


def test_notion_recent_themes_skips_pages_without_theme(monkeypatch):
    from tools import notion_recent_themes
    monkeypatch.setenv("NOTION_API_KEY", "test-token")
    monkeypatch.setenv("NOTION_DATABASE_ID", "db-id-123")
    resp = MagicMock()
    resp.status_code = 200
    resp.json.return_value = {
        "results": [
            {"properties": {
                "名前": {"type": "title", "title": [{"plain_text": "古いページ"}]},
                "テーマ": {"rich_text": []},
            }},
        ]
    }
    with patch("tools.requests.post", return_value=resp):
        out = notion_recent_themes("ワイン")
    assert out == ""


def test_notion_recent_themes_returns_empty_without_env(monkeypatch):
    from tools import notion_recent_themes
    monkeypatch.delenv("NOTION_API_KEY", raising=False)
    monkeypatch.delenv("NOTION_DATABASE_ID", raising=False)
    assert notion_recent_themes("ワイン") == ""


def test_notion_recent_themes_returns_empty_on_error(monkeypatch):
    from tools import notion_recent_themes
    monkeypatch.setenv("NOTION_API_KEY", "test-token")
    monkeypatch.setenv("NOTION_DATABASE_ID", "db-id-123")
    resp = MagicMock()
    resp.status_code = 400
    resp.json.return_value = {"message": "bad"}
    with patch("tools.requests.post", return_value=resp):
        out = notion_recent_themes("ワイン")
    assert out == ""
```

- [ ] **Step 2: テストを実行して失敗することを確認**

Run: `python3 -m pytest tests/test_tools.py -v -k "extract_rich_text or notion_recent_themes"`
Expected: FAIL（`_extract_rich_text` / `notion_recent_themes` が未定義）

- [ ] **Step 3: 実装を追加**

`tools.py` の `_extract_title` 関数（`return ""` で終わる関数、365行目 `notion_find_wip` の直前）の直後に挿入:

```python
def _extract_rich_text(prop: dict) -> str:
    """rich_textプロパティからプレーンテキストを結合して返す。"""
    if not isinstance(prop, dict):
        return ""
    return "".join(t.get("plain_text", "") for t in prop.get("rich_text", []))
```

`notion_find_wip` 関数（`return "途中の制作物:\n" + "\n".join(lines)` で終わる関数、396行目付近）の直後、`_extract_block_text` の直前に挿入:

```python
def notion_recent_themes(category: str, limit: int = 8) -> str:
    """直近のテーマ一覧を取得する（重複回避のための参考情報）。テーマ未設定のページはスキップ。"""
    token = os.environ.get("NOTION_API_KEY")
    database_id = os.environ.get("NOTION_DATABASE_ID")
    if not token or not database_id:
        return ""
    body = {
        "filter": {"property": "カテゴリ", "select": {"equals": category}},
        "sorts": [{"timestamp": "created_time", "direction": "descending"}],
        "page_size": limit,
    }
    try:
        resp = requests.post(
            f"https://api.notion.com/v1/databases/{database_id}/query",
            headers=_notion_headers(token), json=body, timeout=15,
        )
        if resp.status_code != 200:
            return ""
        results = resp.json().get("results", [])
    except Exception:
        return ""

    lines = []
    for page in results:
        props = page.get("properties", {})
        theme = _extract_rich_text(props.get("テーマ", {}))
        if not theme:
            continue
        title = _extract_title(props) or ""
        lines.append(f"- {theme}（{title}）")
    return "\n".join(lines)
```

- [ ] **Step 4: テストを実行して通過することを確認**

Run: `python3 -m pytest tests/test_tools.py -v -k "extract_rich_text or notion_recent_themes"`
Expected: 5 passed

- [ ] **Step 5: コミット**

```bash
git add tools.py tests/test_tools.py
git commit -m "feat: 直近テーマ一覧を取得するnotion_recent_themesを実装"
```

---

## Task 3: `_create_database_page` / `save_to_notion` に `theme` 引数を追加

**Files:**
- Modify: `tools.py:268-342`
- Test: `tests/test_tools.py`

**Interfaces:**
- Consumes: なし（既存関数のシグネチャ拡張のみ）
- Produces:
  - `_create_database_page(token, database_id, title, category, status="要確認", theme="") -> Optional[str]`
  - `save_to_notion(title, content, status="要確認", theme="") -> str`

- [ ] **Step 1: 失敗するテストを書く**

`tests/test_tools.py` の末尾に追記:

```python
def test_save_to_notion_includes_theme_property_when_provided(monkeypatch):
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
        save_to_notion("タイトル", "## 内容", theme="ピエモンテ州のネッビオーロ")

    props = mock_post.call_args[1]["json"]["properties"]
    assert props["テーマ"] == {"rich_text": [{"text": {"content": "ピエモンテ州のネッビオーロ"}}]}


def test_save_to_notion_omits_theme_property_when_not_provided(monkeypatch):
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
        save_to_notion("タイトル", "## 内容")

    props = mock_post.call_args[1]["json"]["properties"]
    assert "テーマ" not in props
```

- [ ] **Step 2: テストを実行して失敗することを確認**

Run: `python3 -m pytest tests/test_tools.py -v -k "includes_theme_property or omits_theme_property"`
Expected: FAIL（`props["テーマ"]` が `KeyError`、`save_to_notion() got an unexpected keyword argument 'theme'`）

- [ ] **Step 3: 実装を変更**

`tools.py` の `_create_database_page` 関数全体（268〜291行目）を以下に置き換え:

```python
def _create_database_page(token: str, database_id: str, title: str, category: str,
                          status: str = "要確認", theme: str = "") -> Optional[str]:
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "Notion-Version": "2022-06-28",
    }
    properties = {
        "title": {"title": [{"text": {"content": title}}]},
        "カテゴリ": {"select": {"name": category}},
        "ステータス": {"select": {"name": status}},
    }
    if theme:
        properties["テーマ"] = {"rich_text": [{"text": {"content": theme}}]}
    payload = {
        "parent": {"database_id": database_id},
        "properties": properties,
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

`save_to_notion` 関数（320〜342行目）を以下に置き換え:

```python
def save_to_notion(title: str, content: str, status: str = "要確認", theme: str = "") -> str:
    token = os.environ.get("NOTION_API_KEY")
    database_id = os.environ.get("NOTION_DATABASE_ID")
    page_id = os.environ.get("NOTION_PAGE_ID")
    if not token or not (database_id or page_id):
        return "NOTION_API_KEY または NOTION_DATABASE_ID / NOTION_PAGE_ID が未設定のためスキップ"

    if database_id:
        child_id = _create_database_page(token, database_id, title,
                                         _infer_category(title, content), status, theme)
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

- [ ] **Step 4: テストを実行して通過することを確認**

Run: `python3 -m pytest tests/test_tools.py -v`
Expected: 全件 passed（既存テスト含む）

- [ ] **Step 5: コミット**

```bash
git add tools.py tests/test_tools.py
git commit -m "feat: save_to_notionにtheme引数を追加しテーマプロパティを保存できるようにする"
```

---

## Task 4: `notion_append_to_page` に `theme` 引数を追加（プロパティ更新の共通化）

**Files:**
- Modify: `tools.py:433-459`
- Test: `tests/test_tools.py`

**Interfaces:**
- Consumes: `_notion_headers`（既存）
- Produces:
  - `_update_page_properties(token, page_id, status, theme="") -> str`
  - `notion_update_status(page_id, status) -> str`（既存シグネチャ維持、内部で`_update_page_properties`に委譲）
  - `notion_append_to_page(page_id, content, status="要確認", theme="") -> str`

- [ ] **Step 1: 失敗するテストを書く**

`tests/test_tools.py` の末尾に追記:

```python
def test_notion_append_to_page_updates_theme_when_provided(monkeypatch):
    monkeypatch.setenv("NOTION_API_KEY", "test-token")
    blocks_resp = MagicMock()
    blocks_resp.status_code = 200
    patch_resp = MagicMock()
    patch_resp.status_code = 200
    patch_resp.json.return_value = {}
    with patch("tools.requests.patch", side_effect=[blocks_resp, patch_resp]) as mock_patch:
        out = notion_append_to_page("page-1", "追記内容", status="要確認", theme="トスカーナ州のサンジョヴェーゼ")

    props_call = mock_patch.call_args_list[1]
    body = props_call[1]["json"]
    assert body["properties"]["テーマ"] == {"rich_text": [{"text": {"content": "トスカーナ州のサンジョヴェーゼ"}}]}
    assert body["properties"]["ステータス"] == {"select": {"name": "要確認"}}
    assert "要確認" in out


def test_notion_append_to_page_omits_theme_when_not_provided(monkeypatch):
    monkeypatch.setenv("NOTION_API_KEY", "test-token")
    blocks_resp = MagicMock()
    blocks_resp.status_code = 200
    patch_resp = MagicMock()
    patch_resp.status_code = 200
    patch_resp.json.return_value = {}
    with patch("tools.requests.patch", side_effect=[blocks_resp, patch_resp]) as mock_patch:
        notion_append_to_page("page-1", "追記内容", status="要確認")

    body = mock_patch.call_args_list[1][1]["json"]
    assert "テーマ" not in body["properties"]
```

- [ ] **Step 2: テストを実行して失敗することを確認**

Run: `python3 -m pytest tests/test_tools.py -v -k notion_append_to_page`
Expected: FAIL（`notion_append_to_page() got an unexpected keyword argument 'theme'`）

- [ ] **Step 3: 実装を変更**

`tools.py` の `notion_update_status` 関数と `notion_append_to_page` 関数（433〜459行目、`def notion_update_status` から `return notion_update_status(page_id, status)` まで）を以下に置き換え:

```python
def _update_page_properties(token: str, page_id: str, status: str, theme: str = "") -> str:
    """ページの ステータス（と任意でテーマ）を更新する。"""
    properties = {"ステータス": {"select": {"name": status}}}
    if theme:
        properties["テーマ"] = {"rich_text": [{"text": {"content": theme}}]}
    body = {"properties": properties}
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


def notion_update_status(page_id: str, status: str) -> str:
    """ページの ステータス セレクトを更新する。"""
    token = os.environ.get("NOTION_API_KEY")
    if not token:
        return "NOTION_API_KEY が未設定のためスキップ"
    return _update_page_properties(token, page_id, status)


def notion_append_to_page(page_id: str, content: str, status: str = "要確認", theme: str = "") -> str:
    """既存ページに本文を追記し、ステータス（と任意でテーマ）を更新する（runner内部利用）。"""
    token = os.environ.get("NOTION_API_KEY")
    if not token:
        return "NOTION_API_KEY が未設定のためスキップ"
    err = _add_blocks_to_page(token, page_id, content)
    if err:
        return err
    return _update_page_properties(token, page_id, status, theme)
```

- [ ] **Step 4: テストを実行して通過することを確認**

Run: `python3 -m pytest tests/test_tools.py -v`
Expected: 全件 passed（`test_notion_update_status_patches` 含む既存テストが壊れていないこと）

- [ ] **Step 5: コミット**

```bash
git add tools.py tests/test_tools.py
git commit -m "feat: notion_append_to_pageにtheme引数を追加しプロパティ更新を共通化する"
```

---

## Task 5: `runner.py` の `run_agent()` に重複回避ロジックを組み込む

**Files:**
- Modify: `runner.py:1-11`（import）、`runner.py:77-157`（`run_agent`）
- Test: `tests/test_runner.py`

**Interfaces:**
- Consumes: `notion_recent_themes(category, limit=8)`, `extract_theme(content)`（Task 1/2で実装済み）、`save_to_notion(..., theme="")`, `notion_append_to_page(..., theme="")`（Task 3/4で実装済み）
- Produces: `run_agent()` の外部シグネチャ・戻り値は無変更（内部動作のみ変更）

**重要な注意（既存テストへの影響）:** `category = _infer_category(label, prompt)` が `"ワイン"` または `"コーヒー"` になる既存テストでは、今回の変更後に `notion_recent_themes` と `extract_theme` が実際に呼ばれるようになる。モックしないと実際のNotion/Anthropic APIを呼びに行ってしまうため、対象のテスト（`test_run_agent_resumes_existing_wip_page` と `test_run_agent_read_error_falls_back_to_new_page` — どちらもlabelに「ワイン」を含む）を必ずこのタスク内で更新すること。

- [ ] **Step 1: 失敗するテストを書く**

`tests/test_runner.py` の末尾に追記:

```python
def test_run_agent_injects_recent_themes_into_prompt(monkeypatch):
    import runner
    resp = _text_response("新しいテーマ提案です。以上。", "end_turn")
    with patch.object(runner.client.messages, "stream", return_value=_stream_cm(resp)) as mock_stream, \
         patch.object(runner, "notion_recent_themes",
                      return_value="- ピエモンテ州のネッビオーロ（月曜：今週テーマ決定 (2026-07-20)）") as mock_recent, \
         patch.object(runner, "notion_find_wip", return_value="途中の制作物はありません"), \
         patch.object(runner, "extract_theme", return_value=""), \
         patch.object(runner, "save_to_notion", return_value="ok"), \
         patch.object(runner, "save_log"):
        runner.run_agent("sommelier", "今週のワインテーマを提案してください", "月曜：今週テーマ決定")

    mock_recent.assert_called_once_with("ワイン")
    sent_prompt = mock_stream.call_args.kwargs["messages"][0]["content"]
    assert "重複回避" in sent_prompt
    assert "ピエモンテ州のネッビオーロ" in sent_prompt


def test_run_agent_skips_theme_injection_when_no_recent_themes(monkeypatch):
    import runner
    resp = _text_response("初回のテーマ提案です。以上。", "end_turn")
    with patch.object(runner.client.messages, "stream", return_value=_stream_cm(resp)) as mock_stream, \
         patch.object(runner, "notion_recent_themes", return_value=""), \
         patch.object(runner, "notion_find_wip", return_value="途中の制作物はありません"), \
         patch.object(runner, "extract_theme", return_value=""), \
         patch.object(runner, "save_to_notion", return_value="ok"), \
         patch.object(runner, "save_log"):
        runner.run_agent("sommelier", "今週のワインテーマを提案してください", "月曜：今週テーマ決定")

    sent_prompt = mock_stream.call_args.kwargs["messages"][0]["content"]
    assert "重複回避" not in sent_prompt


def test_run_agent_does_not_call_recent_themes_for_other_category(monkeypatch):
    import runner
    resp = _text_response("分析レポートです。以上。", "end_turn")
    with patch.object(runner.client.messages, "stream", return_value=_stream_cm(resp)), \
         patch.object(runner, "notion_recent_themes") as mock_recent, \
         patch.object(runner, "extract_theme") as mock_extract, \
         patch.object(runner, "save_to_notion", return_value="ok"), \
         patch.object(runner, "save_log"):
        runner.run_agent("marketer", "反応を分析してください", "日曜：反応分析レポート")

    mock_recent.assert_not_called()
    mock_extract.assert_not_called()


def test_run_agent_extracts_theme_and_passes_to_save_to_notion(monkeypatch):
    import runner
    resp = _text_response("ピエモンテ州のネッビオーロを紹介します。以上。", "end_turn")
    with patch.object(runner.client.messages, "stream", return_value=_stream_cm(resp)), \
         patch.object(runner, "notion_recent_themes", return_value=""), \
         patch.object(runner, "notion_find_wip", return_value="途中の制作物はありません"), \
         patch.object(runner, "extract_theme", return_value="ピエモンテ州のネッビオーロ") as mock_extract, \
         patch.object(runner, "save_to_notion", return_value="ok") as mock_save, \
         patch.object(runner, "save_log"):
        runner.run_agent("sommelier", "今週のワインテーマを提案してください", "月曜：今週テーマ決定")

    mock_extract.assert_called_once_with("ピエモンテ州のネッビオーロを紹介します。以上。")
    assert mock_save.call_args.kwargs.get("theme") == "ピエモンテ州のネッビオーロ"


def test_run_agent_extracts_theme_and_passes_to_notion_append_to_page(monkeypatch):
    import runner
    resp = _text_response("続きを完成させました。以上です。", "end_turn")
    find_out = "途中の制作物:\n- pageABC | ワイン | 火曜：ワイン動画台本作成 (2026-07-10)"
    with patch.object(runner.client.messages, "stream", return_value=_stream_cm(resp)), \
         patch.object(runner, "notion_recent_themes", return_value=""), \
         patch.object(runner, "notion_find_wip", return_value=find_out), \
         patch.object(runner, "notion_read_page", return_value="前回の途中原稿本文"), \
         patch.object(runner, "extract_theme", return_value="トスカーナ州のサンジョヴェーゼ") as mock_extract, \
         patch.object(runner, "notion_append_to_page", return_value="更新しました") as mock_append, \
         patch.object(runner, "save_to_notion", return_value="ok"), \
         patch.object(runner, "save_log"):
        runner.run_agent("creator", "ワインの台本を書いて", "火曜：ワイン動画台本作成")

    mock_extract.assert_called_once()
    assert mock_append.call_args.kwargs.get("theme") == "トスカーナ州のサンジョヴェーゼ"
```

続けて、既存テストを更新する。`test_run_agent_saves_to_notion` を以下に置き換え（`theme=""` を追加）:

```python
def test_run_agent_saves_to_notion():
    """run_agent の最終出力が save_to_notion に渡される。"""
    today = datetime.now().strftime('%Y-%m-%d')

    fake_response = MagicMock()
    fake_response.stop_reason = "end_turn"
    fake_response.content = [MagicMock(text="テスト出力", spec=["text"])]

    with patch("runner.client.messages.stream", return_value=_stream_cm(fake_response)), \
         patch("runner.save_to_notion", return_value="OK") as mock_notion, \
         patch("runner.save_log"):
        run_agent("sommelier", "テスト", "テストラベル")

    mock_notion.assert_called_once_with(f"テストラベル ({today})", "テスト出力", status="要確認", theme="")
```

続けて、`test_run_agent_resumes_existing_wip_page` を以下に置き換え（`notion_recent_themes` と `extract_theme` のモックを追加）:

```python
def test_run_agent_resumes_existing_wip_page(monkeypatch):
    import runner
    resp = _text_response("続きを書いて完成させました。以上です。", "end_turn")
    find_out = "途中の制作物:\n- pageABC | ワイン | 火曜：ワイン動画台本作成 (2026-07-10)"
    with patch.object(runner.client.messages, "stream", return_value=_stream_cm(resp)) as mock_stream, \
         patch.object(runner, "notion_recent_themes", return_value=""), \
         patch.object(runner, "notion_find_wip", return_value=find_out), \
         patch.object(runner, "notion_read_page", return_value="前回の途中原稿本文") as mock_read, \
         patch.object(runner, "extract_theme", return_value=""), \
         patch.object(runner, "notion_append_to_page", return_value="更新しました") as mock_append, \
         patch.object(runner, "save_to_notion", return_value="ok") as mock_save, \
         patch.object(runner, "save_log"):
        runner.run_agent("creator", "ワインの台本を書いて", "火曜：ワイン動画台本作成")

    # 既存原稿を読み、プロンプトに注入して生成、既存ページへ追記、新規保存はしない
    mock_read.assert_called_once_with("pageABC")
    sent_messages = mock_stream.call_args.kwargs["messages"]
    assert "前回の途中原稿本文" in sent_messages[0]["content"]
    mock_append.assert_called_once()
    assert mock_append.call_args[0][0] == "pageABC"
    assert mock_append.call_args.kwargs.get("status") == "要確認"
    mock_save.assert_not_called()
```

続けて、`test_run_agent_read_error_falls_back_to_new_page` を以下に置き換え:

```python
def test_run_agent_read_error_falls_back_to_new_page(monkeypatch):
    import runner
    resp = _text_response("新規に書き起こした完成原稿です。以上。", "end_turn")
    find_out = "途中の制作物:\n- pageABC | ワイン | 火曜：ワイン動画台本作成 (2026-07-10)"
    with patch.object(runner.client.messages, "stream", return_value=_stream_cm(resp)) as mock_stream, \
         patch.object(runner, "notion_recent_themes", return_value=""), \
         patch.object(runner, "notion_find_wip", return_value=find_out), \
         patch.object(runner, "notion_read_page", return_value="Notion読み取りエラー: 404 not found"), \
         patch.object(runner, "extract_theme", return_value=""), \
         patch.object(runner, "notion_append_to_page", return_value="x") as mock_append, \
         patch.object(runner, "save_to_notion", return_value="ok") as mock_save, \
         patch.object(runner, "save_log"):
        runner.run_agent("creator", "ワインの台本を書いて", "火曜：ワイン動画台本作成")
    sent = mock_stream.call_args.kwargs["messages"][0]["content"]
    assert "Notion読み取りエラー" not in sent          # error text NOT injected
    mock_append.assert_not_called()                     # did not append to unreadable page
    mock_save.assert_called_once()                      # fell back to new page
```

- [ ] **Step 2: テストを実行して失敗することを確認**

Run: `python3 -m pytest tests/test_runner.py -v -k "recent_themes or extracts_theme or other_category"`
Expected: FAIL（`AttributeError: <module 'runner'> does not have the attribute 'notion_recent_themes'` など）

- [ ] **Step 3: 実装を変更**

`runner.py` の import文（6〜9行目）を以下に置き換え:

```python
from tools import (
    TOOL_DEFINITIONS, execute_tool, save_to_notion, notion_find_wip,
    notion_read_page, notion_append_to_page, _infer_category,
    notion_recent_themes, extract_theme,
)
```

`runner.py` の `run_agent` 関数冒頭（77〜95行目、`def run_agent` から WIP再開ロジックの `if candidate_id:` ブロック終わりまで）を以下に置き換え:

```python
def run_agent(agent_name: str, prompt: str, label: str, max_continuations: int = 3) -> str:
    system = load_agent(agent_name)

    # 途中の制作物があれば読み込み、続きから書かせる（ワイン/コーヒーのみ対象）
    resume_page_id = ""
    category = _infer_category(label, prompt)
    if category in ("ワイン", "コーヒー"):
        recent_themes = notion_recent_themes(category)
        if recent_themes:
            prompt = (
                prompt
                + "\n\n【重複回避】直近の制作物テーマ一覧です。"
                + "同じ産地・品種・切り口・商品の重複を避けて新しい提案をしてください:\n"
                + recent_themes
            )

        find_out = notion_find_wip(category)
        candidate_id = _wip_page_id_for_label(find_out, label)
        if candidate_id:
            existing = notion_read_page(candidate_id)
            if existing and not existing.endswith("スキップ") and not existing.startswith("Notion読み取りエラー"):
                resume_page_id = candidate_id
                prompt = (
                    prompt
                    + "\n\n【前回の途中原稿】以下は前回、途中まで作成した内容です。"
                    + "繰り返さず、この続きから書いて全体を完成させてください:\n\n"
                    + existing
                )
```

`runner.py` の末尾（146〜157行目、`final_text = accumulated` から関数の `return final_text` まで）を以下に置き換え:

```python
    final_text = accumulated
    save_log(final_text, label)
    now = datetime.now()
    status = "途中" if truncated else "要確認"
    print(f"\n{'⚠️ 途中保存' if truncated else '✅'} {label} 完了（{status}）")

    theme = extract_theme(final_text) if category in ("ワイン", "コーヒー") else ""
    if resume_page_id:
        notion_result = notion_append_to_page(resume_page_id, final_text, status=status, theme=theme)
    else:
        notion_result = save_to_notion(f"{label} ({now.strftime('%Y-%m-%d')})", final_text, status=status, theme=theme)
    print(f"   📝 Notion: {notion_result}")
    return final_text
```

- [ ] **Step 4: テストを実行して通過することを確認**

Run: `python3 -m pytest tests/test_runner.py -v`
Expected: 全件 passed（新規5件＋既存15件、実行時間が数秒程度で完了し、実際のAPI呼び出しが発生していないこと＝ハングしないことも確認）

- [ ] **Step 5: 全体テストを実行して既存テストを壊していないことを確認**

Run: `python3 -m pytest tests/ -v`
Expected: 全件 passed

- [ ] **Step 6: コミット**

```bash
git add runner.py tests/test_runner.py
git commit -m "feat: run_agentに重複回避コンテキスト注入とテーマ保存を組み込む"
```

---

## Task 6: Notionマイグレーションスクリプト `scripts/notion_add_theme.py`

**Files:**
- Create: `scripts/notion_add_theme.py`
- Test: `tests/test_notion_theme_migration.py`

**Interfaces:**
- Consumes: `extract_theme`, `notion_read_page`, `_notion_headers`（`tools.py`、Task 1で実装済み）
- Produces: CLIスクリプト（`python3 scripts/notion_add_theme.py` で実行）

- [ ] **Step 1: 失敗するテストを書く**

`tests/test_notion_theme_migration.py` を新規作成:

```python
import os, sys
from unittest.mock import patch
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from scripts.notion_add_theme import classify_existing_page, _extract_theme_property


def test_classify_existing_page_calls_extract_theme():
    with patch("scripts.notion_add_theme.notion_read_page", return_value="バローロについての記事"), \
         patch("scripts.notion_add_theme.extract_theme", return_value="バローロ特集") as mock_extract:
        result = classify_existing_page("p1")
    mock_extract.assert_called_once_with("バローロについての記事")
    assert result == "バローロ特集"


def test_extract_theme_property_reads_rich_text():
    page = {"properties": {"テーマ": {"rich_text": [{"plain_text": "ピエモンテ州のネッビオーロ"}]}}}
    assert _extract_theme_property(page) == "ピエモンテ州のネッビオーロ"
    assert _extract_theme_property({"properties": {}}) == ""


def test_main_skips_pages_with_existing_theme(monkeypatch):
    import scripts.notion_add_theme as m
    monkeypatch.setenv("NOTION_API_KEY", "t")
    monkeypatch.setenv("NOTION_DATABASE_ID", "db")
    pages = [
        {"id": "done1", "properties": {"テーマ": {"rich_text": [{"plain_text": "既存テーマ"}]}}},
        {"id": "fresh1", "properties": {"テーマ": {"rich_text": []}}},
    ]
    with patch.object(m, "_ensure_theme_property"), \
         patch.object(m, "_iter_pages", return_value=iter(pages)), \
         patch.object(m, "classify_existing_page", return_value="新しいテーマ") as mock_cls, \
         patch.object(m, "_update_theme", return_value="ok") as mock_upd:
        m.main()
    mock_cls.assert_called_once_with("fresh1")
    mock_upd.assert_called_once_with("t", "fresh1", "新しいテーマ")


def test_main_skips_pages_when_extraction_fails(monkeypatch):
    import scripts.notion_add_theme as m
    monkeypatch.setenv("NOTION_API_KEY", "t")
    monkeypatch.setenv("NOTION_DATABASE_ID", "db")
    pages = [{"id": "empty1", "properties": {"テーマ": {"rich_text": []}}}]
    with patch.object(m, "_ensure_theme_property"), \
         patch.object(m, "_iter_pages", return_value=iter(pages)), \
         patch.object(m, "classify_existing_page", return_value="") as mock_cls, \
         patch.object(m, "_update_theme") as mock_upd:
        m.main()
    mock_cls.assert_called_once_with("empty1")
    mock_upd.assert_not_called()
```

- [ ] **Step 2: テストを実行して失敗することを確認**

Run: `python3 -m pytest tests/test_notion_theme_migration.py -v`
Expected: FAIL（`ModuleNotFoundError: No module named 'scripts.notion_add_theme'`）

- [ ] **Step 3: 実装を追加**

`scripts/notion_add_theme.py` を新規作成:

```python
"""一度きりのマイグレーション: コンテンツ生成物DBに『テーマ』を追加し既存ページを遡って要約する。

使い方: リポジトリ直下で `python3 scripts/notion_add_theme.py`
NOTION_API_KEY / NOTION_DATABASE_ID / ANTHROPIC_API_KEY が必要。
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

import requests
from tools import extract_theme, notion_read_page, _notion_headers


def _load_env() -> None:
    """リポジトリ直下の .env を環境変数へ読み込む（runner.py と同方式）。"""
    env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".env")
    if os.path.exists(env_path):
        with open(env_path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, _, value = line.partition("=")
                    os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def classify_existing_page(page_id: str) -> str:
    content = notion_read_page(page_id)
    return extract_theme(content)


def _extract_theme_property(page: dict) -> str:
    rich = page.get("properties", {}).get("テーマ", {}).get("rich_text") or []
    return "".join(t.get("plain_text", "") for t in rich)


def _ensure_theme_property(token: str, database_id: str) -> None:
    body = {"properties": {"テーマ": {"rich_text": {}}}}
    try:
        resp = requests.patch(
            f"https://api.notion.com/v1/databases/{database_id}",
            headers=_notion_headers(token), json=body, timeout=15,
        )
        if resp.status_code != 200:
            print(f"プロパティ追加エラー: {resp.status_code} {resp.text}")
        else:
            print(f"プロパティ追加: {resp.status_code}")
    except Exception as e:
        print(f"プロパティ追加エラー: {e}")


def _iter_pages(token: str, database_id: str):
    cursor = None
    while True:
        body = {}
        if cursor:
            body["start_cursor"] = cursor
        try:
            resp = requests.post(
                f"https://api.notion.com/v1/databases/{database_id}/query",
                headers=_notion_headers(token), json=body, timeout=15,
            )
        except Exception as e:
            print(f"Notion検索エラー: {e}")
            return
        if resp.status_code != 200:
            print(f"Notion検索エラー: {resp.status_code} {resp.text}")
            return
        data = resp.json()
        for page in data.get("results", []):
            yield page
        if data.get("has_more"):
            cursor = data.get("next_cursor")
        else:
            break


def _update_theme(token: str, page_id: str, theme: str) -> str:
    body = {"properties": {"テーマ": {"rich_text": [{"text": {"content": theme}}]}}}
    try:
        resp = requests.patch(
            f"https://api.notion.com/v1/pages/{page_id}",
            headers=_notion_headers(token), json=body, timeout=15,
        )
        if resp.status_code != 200:
            return f"テーマ更新エラー: {resp.status_code} {resp.text}"
    except Exception as e:
        return f"テーマ更新エラー: {e}"
    return f"テーマを設定: {theme}"


def main() -> None:
    _load_env()
    token = os.environ.get("NOTION_API_KEY")
    database_id = os.environ.get("NOTION_DATABASE_ID")
    if not token or not database_id:
        print("NOTION_API_KEY / NOTION_DATABASE_ID が未設定です。")
        return
    _ensure_theme_property(token, database_id)
    for page in _iter_pages(token, database_id):
        page_id = page["id"]
        theme = _extract_theme_property(page)
        if theme:
            print(f"{page_id} -> スキップ（既存: {theme}）")
            continue
        theme = classify_existing_page(page_id)
        if not theme:
            print(f"{page_id} -> テーマ抽出失敗、スキップ")
            continue
        print(f"{page_id} -> {_update_theme(token, page_id, theme)}")


if __name__ == "__main__":
    main()
```

`scripts/` ディレクトリに `__init__.py` が既にあるか確認する。無ければ空ファイルを作成:

Run: `test -f scripts/__init__.py && echo exists || touch scripts/__init__.py`

- [ ] **Step 4: テストを実行して通過することを確認**

Run: `python3 -m pytest tests/test_notion_theme_migration.py -v`
Expected: 4 passed

- [ ] **Step 5: コミット**

```bash
git add scripts/notion_add_theme.py tests/test_notion_theme_migration.py
git add scripts/__init__.py 2>/dev/null || true
git commit -m "feat: テーマプロパティ追加・遡及要約用のマイグレーションスクリプトを追加"
```

---

## Task 7: CLAUDE.mdへのドキュメント追記

**Files:**
- Modify: `CLAUDE.md`

**Interfaces:**
- Consumes: なし（ドキュメントのみ）
- Produces: なし

- [ ] **Step 1: 「Notionステータスと続き生成」セクションの直後に新セクションを追加**

`CLAUDE.md` の `## Notionステータスと続き生成` セクション（`初回のみ python3 scripts/notion_add_status.py を実行して...` の行で終わるセクション）の直後、`## エージェント構成` の直前に以下を挿入:

```markdown
## 重複回避（テーマ管理）

「コンテンツ生成物」DBの各ページに `テーマ`（一言要約、20文字程度）を持たせる。

- エージェントが生成物を保存する際、本文からHaikuで一言テーマを自動抽出して保存する。
- 週次エージェント実行時、同カテゴリ（ワイン/コーヒー）の直近8件のテーマ一覧を参考情報としてプロンプトに渡し、産地・品種・切り口の重複を避けるよう促す。
- 初回のみ `python3 scripts/notion_add_theme.py` を実行して `テーマ` プロパティ追加と既存ページの遡及要約を行う。
```

- [ ] **Step 2: 目視確認**

Run: `grep -n "重複回避" CLAUDE.md`
Expected: 追加した見出し行が表示される

- [ ] **Step 3: コミット**

```bash
git add CLAUDE.md
git commit -m "docs: 重複回避機能とマイグレーション手順をCLAUDE.mdに追記"
```

---

## 完了確認

- [ ] `python3 -m pytest tests/ -v` が全件通過する
- [ ] `python3 -m pytest tests/ -v` の実行時間が数秒程度（実APIへの呼び出しが発生していないこと）
- [ ] オーナーが `python3 scripts/notion_add_theme.py` を実行し、「コンテンツ生成物」DBに `テーマ` 列が追加され、既存ページに遡及でテーマが入ることを確認する（この最終確認だけは実際のNotion環境が必要）
- [ ] 次回の週次実行（月曜09:00〜）で、Notionページの本文にどのような重複回避コンテキストが渡ったか `logs/` で確認する
