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


def execute_tool(name: str, inputs: dict) -> str:
    if name == "web_search":
        return web_search(inputs["query"], inputs.get("region", "jp-jp"))
    elif name == "search_papers":
        return search_papers(inputs["query"])
    elif name == "fetch_page":
        return fetch_page(inputs["url"])
    return f"不明なツール: {name}"
