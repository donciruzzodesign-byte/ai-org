import os
import re
import requests
from bs4 import BeautifulSoup
from typing import Optional

TOOL_DEFINITIONS = [
    {
        "name": "web_search",
        "description": (
            "Webを検索して最新情報を取得します。ワインのニュース・トレンド・価格・"
            "イタリアの最新情報などに使います。"
            "region を it-it にするとイタリア語圏の情報が優先されます。"
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "検索クエリ。イタリア現地情報はイタリア語で検索すると精度が上がります。"
                },
                "region": {
                    "type": "string",
                    "description": "検索地域: jp-jp（日本）/ it-it（イタリア）/ en-us（英語）",
                    "default": "jp-jp"
                }
            },
            "required": ["query"]
        }
    },
    {
        "name": "search_papers",
        "description": (
            "学術論文・研究資料を検索します。"
            "ワインの醸造科学・テロワール研究・品種の特性など専門的情報を調べる際に使います。"
            "英語での検索を推奨します。"
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "検索クエリ（英語推奨）"
                }
            },
            "required": ["query"]
        }
    },
    {
        "name": "fetch_page",
        "description": "指定URLのWebページを取得して内容を読みます。検索結果を詳しく読む際に使います。",
        "input_schema": {
            "type": "object",
            "properties": {
                "url": {
                    "type": "string",
                    "description": "取得するWebページのURL"
                }
            },
            "required": ["url"]
        }
    },
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
]


def web_search(query: str, region: str = "jp-jp") -> str:
    try:
        from ddgs import DDGS
        import time
        results = []
        for attempt in range(3):
            try:
                with DDGS() as ddgs:
                    results = list(ddgs.text(query, region=region, max_results=5))
                if results:
                    break
                time.sleep(2)
            except Exception:
                time.sleep(2)
        if not results:
            return "検索結果が見つかりませんでした。クエリを変えて再試行してください。"
        lines = []
        for r in results:
            lines.append(
                f"タイトル: {r.get('title', '')}\n"
                f"URL: {r.get('href', '')}\n"
                f"概要: {r.get('body', '')}"
            )
        return "\n---\n".join(lines)
    except Exception as e:
        return f"検索エラー: {e}"


def search_papers(query: str) -> str:
    try:
        url = "https://api.semanticscholar.org/graph/v1/paper/search"
        params = {
            "query": query,
            "fields": "title,abstract,year,authors,url",
            "limit": 5
        }
        resp = requests.get(url, params=params, timeout=10)
        papers = resp.json().get("data", [])
        if not papers:
            return "論文が見つかりませんでした。"
        lines = []
        for p in papers:
            authors = ", ".join(a.get("name", "") for a in p.get("authors", [])[:3])
            abstract = (p.get("abstract") or "要約なし")[:300]
            lines.append(
                f"タイトル: {p.get('title', '')}\n"
                f"著者: {authors}　年: {p.get('year', '不明')}\n"
                f"要約: {abstract}\n"
                f"URL: {p.get('url', '')}"
            )
        return "\n---\n".join(lines)
    except Exception as e:
        return f"論文検索エラー: {e}"


def fetch_page(url: str) -> str:
    try:
        headers = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"}
        resp = requests.get(url, headers=headers, timeout=10)
        resp.encoding = resp.apparent_encoding
        soup = BeautifulSoup(resp.text, "html.parser")
        for tag in soup(["script", "style", "nav", "footer", "header", "aside"]):
            tag.decompose()
        text = soup.get_text(separator="\n", strip=True)
        return text[:4000]
    except Exception as e:
        return f"ページ取得エラー: {e}"


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


def _create_child_page(token: str, parent_page_id: str, title: str) -> Optional[str]:
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
    try:
        resp = requests.post("https://api.notion.com/v1/pages", headers=headers,
                             json=payload, timeout=15)
        result = resp.json()
        if resp.status_code == 200:
            return result.get("id")
        return None
    except Exception:
        return None


def _infer_category(title: str, content: str) -> str:
    if "コーヒー" in title:
        return "コーヒー"
    if "ワイン" in title:
        return "ワイン"
    coffee = content.count("コーヒー")
    wine = content.count("ワイン")
    if coffee > wine:
        return "コーヒー"
    if wine > coffee:
        return "ワイン"
    return "その他"


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
