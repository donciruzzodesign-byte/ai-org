"""Instagram Insightsをスプレッドシートに同期する。

使い方: リポジトリ直下で `python3 scripts/sync_instagram_insights.py [since_date]`
since_date省略時は7日前から。META_ACCESS_TOKEN / META_IG_USER_ID /
GOOGLE_SERVICE_ACCOUNT_JSON / INSTAGRAM_SHEET_ID が必要。
"""
import os
import sys
from datetime import datetime, timedelta

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

from tools_instagram import sync_instagram_insights


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


def main() -> None:
    _load_env()
    access_token = os.environ.get("META_ACCESS_TOKEN")
    ig_user_id = os.environ.get("META_IG_USER_ID")
    service_account_json_path = os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON")
    sheet_id = os.environ.get("INSTAGRAM_SHEET_ID")

    missing = [name for name, val in [
        ("META_ACCESS_TOKEN", access_token), ("META_IG_USER_ID", ig_user_id),
        ("GOOGLE_SERVICE_ACCOUNT_JSON", service_account_json_path), ("INSTAGRAM_SHEET_ID", sheet_id),
    ] if not val]
    if missing:
        print(f"❌ 必要な環境変数が未設定です: {', '.join(missing)}")
        return

    since_date = sys.argv[1] if len(sys.argv) > 1 else (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
    print(f"🔄 Instagram Insightsを同期中（{since_date}以降の投稿）...")
    summary = sync_instagram_insights(ig_user_id, access_token, sheet_id, service_account_json_path, since_date)
    print(f"✅ {summary}")


if __name__ == "__main__":
    main()
