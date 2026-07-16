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
