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
