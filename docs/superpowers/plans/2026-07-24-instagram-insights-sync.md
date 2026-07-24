# Instagram Insights 自動連携システム Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Meta Instagram Graph APIから取得したInsightsデータを、既存のオーナー運用スプレッドシートのタブ1・2に自動書き込みする。

**Architecture:** `tools_instagram.py` にGraph API呼び出し・データ整形・Sheets書き込みロジックを集約し、`scripts/sync_instagram_insights.py`（単体CLI）と `runner.py`（週次スケジュール）の両方から同じ関数を呼び出す。

**Tech Stack:** `requests`（Graph API呼び出し、既存の`tools.py`のNotion連携と同じ流儀）、`gspread`（Sheets書き込み、サービスアカウント認証）

## Global Constraints

- 対象は既存スプレッドシート（`1w668TozaQX-hM7rJsEXSde0fiwxfW0g0i9Dumvx3P0I`）の**タブ1・タブ2のみ**。他3タブは対象外。
- APIで取得できない列（インプ内訳④〜⑧、動画時間、スキップ率、視聴維持率、サムネ、翌日/1週間後ブロック）には一切書き込まない。
- Notion連携・marketerエージェントとの統合は行わない（今回のスコープ外）。
- トークン期限切れ時は同期処理全体を中断する。個別投稿のInsights取得失敗はその投稿だけスキップし処理継続する。
- アクセストークンの自動リフレッシュは実装しない（60日ごとの手動再発行）。
- 新規コードは既存の `tools_*.py` の流儀（生の`requests`呼び出し、関数はエラー時に例外を投げず文字列で返す箇所と、内部ヘルパーは例外を使う箇所の使い分け）に合わせる。

---

## 事前確認（実装開始前にオーナーと一緒に行う）

このプランのTask 6以降で使うタブのgid（`TAB1_GID` / `TAB2_GID`）は、ブラウザでスプレッドシートを開き、以下の2つのURLのタブ名と中身を確認して決める。

- `https://docs.google.com/spreadsheets/d/1w668TozaQX-hM7rJsEXSde0fiwxfW0g0i9Dumvx3P0I/edit?gid=1526183674` → ヘッダーに「投稿ＵＲＬ」列があるタブ（= タブ1、投稿ごとメイン指標）
- `https://docs.google.com/spreadsheets/d/1w668TozaQX-hM7rJsEXSde0fiwxfW0g0i9Dumvx3P0I/edit?gid=0` → ヘッダーに「①リーチ」「⑨いいね」等がある詳細内訳タブ（= タブ2）

このplanでは `TAB1_GID = 1526183674`、`TAB2_GID = 0` と仮定してコードを書く。実装者は必ず上記2つのURLを開いて仮定が正しいか確認し、違っていればTask 7の定数を実際の値に直すこと。

同様に、両タブとも実際の列見出し行はシート内の**3行目**（1〜2行目は結合されたグループ見出し）にあると想定している。これも実物を開いて行番号がずれていないか確認すること。

---

## Task 1: 依存パッケージと環境変数テンプレートの追加

**Files:**
- Modify: `requirements.txt`
- Modify: `.env.example`

**Interfaces:**
- Produces: `gspread` パッケージがインストール済みであること（Task 6以降が依存）

- [ ] **Step 1: requirements.txtにgspreadを追加**

`requirements.txt` の末尾に1行追加する。

```
gspread>=6.1.0
```

- [ ] **Step 2: インストールして確認**

Run: `pip install -r requirements.txt && python3 -c "import gspread; print(gspread.__version__)"`
Expected: バージョン番号が表示される（エラーなし）

- [ ] **Step 3: .env.exampleに新規環境変数を追加**

`.env.example` の末尾に追記する。

```
META_ACCESS_TOKEN=your_meta_long_lived_access_token   # 任意：Instagram Insights自動連携を使う場合
META_IG_USER_ID=your_instagram_business_account_id    # 任意：同上
GOOGLE_SERVICE_ACCOUNT_JSON=/path/to/service_account.json  # 任意：同上（Sheets書き込み用）
INSTAGRAM_SHEET_ID=your_spreadsheet_id                # 任意：同上（対象スプレッドシートID）
```

- [ ] **Step 4: コミット**

```bash
git add requirements.txt .env.example
git commit -m "chore: Instagram Insights連携用の依存関係と環境変数テンプレートを追加"
```

---

## Task 2: 日付変換・レート計算・投稿グルーピングの純粋関数

**Files:**
- Create: `tools_instagram.py`
- Test: `tests/test_instagram.py`

**Interfaces:**
- Produces:
  - `to_jst_date_str(timestamp: str) -> str`
  - `compute_rates(insights: dict) -> dict`
  - `group_media_by_date(media_items: list[dict]) -> dict[str, list[dict]]`

- [ ] **Step 1: 失敗するテストを書く**

`tests/test_instagram.py` を新規作成:

```python
from tools_instagram import to_jst_date_str, compute_rates, group_media_by_date


def test_to_jst_date_str_converts_utc_to_jst_date():
    # UTC 2026-07-20T23:30:00 は JST では翌日 2026-07-21 になる
    assert to_jst_date_str("2026-07-20T23:30:00+0000") == "7/21"


def test_to_jst_date_str_same_day():
    assert to_jst_date_str("2026-07-20T10:15:30+0000") == "7/20"


def test_compute_rates_basic():
    insights = {
        "reach": 100,
        "likes": 10,
        "saved": 5,
        "profile_activity": 20,
        "link_taps": 4,
    }
    rates = compute_rates(insights)
    assert rates["like_rate"] == 0.1
    assert rates["save_rate"] == 0.05
    assert rates["profile_activity_rate"] == 0.2
    assert rates["link_tap_rate"] == 0.2  # 4/20 (profile_activityが分母)


def test_compute_rates_zero_reach_returns_zero():
    insights = {"reach": 0, "likes": 5, "saved": 0, "profile_activity": 0, "link_taps": 0}
    rates = compute_rates(insights)
    assert rates["like_rate"] == 0.0
    assert rates["profile_activity_rate"] == 0.0
    assert rates["link_tap_rate"] == 0.0


def test_group_media_by_date_groups_and_sorts_by_timestamp():
    media = [
        {"id": "2", "timestamp": "2026-07-20T18:00:00+0000"},
        {"id": "1", "timestamp": "2026-07-20T10:00:00+0000"},
        {"id": "3", "timestamp": "2026-07-21T09:00:00+0000"},
    ]
    grouped = group_media_by_date(media)
    assert list(grouped.keys()) == ["7/20", "7/21"]
    assert [m["id"] for m in grouped["7/20"]] == ["1", "2"]
    assert [m["id"] for m in grouped["7/21"]] == ["3"]
```

- [ ] **Step 2: テストを実行して失敗することを確認**

Run: `python3 -m pytest tests/test_instagram.py -v`
Expected: FAIL（`tools_instagram` モジュールが存在しない）

- [ ] **Step 3: 最小実装を書く**

`tools_instagram.py` を新規作成:

```python
from datetime import datetime, timedelta, timezone

_JST = timezone(timedelta(hours=9))


def to_jst_date_str(timestamp: str) -> str:
    """Graph APIのタイムスタンプ（例: '2026-07-20T10:15:30+0000'）をJSTの 'M/D' 表記に変換する。"""
    dt = datetime.strptime(timestamp, "%Y-%m-%dT%H:%M:%S%z")
    jst_dt = dt.astimezone(_JST)
    return f"{jst_dt.month}/{jst_dt.day}"


def compute_rates(insights: dict) -> dict:
    """取得済みのInsights数値から、シートの各種「率」列を計算する。
    リンクタップ率だけプロアク数（プロフィールアクセス起点の行動数）を分母にする。
    プロフィール内の行動のうちどれだけがリンクタップだったか、を見る指標のため。
    """
    reach = insights.get("reach") or 0
    profile_activity = insights.get("profile_activity") or 0

    def safe_div(numerator, denominator):
        return round(numerator / denominator, 4) if denominator else 0.0

    return {
        "like_rate": safe_div(insights.get("likes", 0), reach),
        "save_rate": safe_div(insights.get("saved", 0), reach),
        "profile_activity_rate": safe_div(profile_activity, reach),
        "link_tap_rate": safe_div(insights.get("link_taps", 0), profile_activity),
    }


def group_media_by_date(media_items: list) -> dict:
    """メディア一覧をJST日付ごとにグルーピングし、各グループ内はタイムスタンプ昇順に並べる。
    同日に複数投稿がある場合、呼び出し側は各グループの先頭要素だけをタブ2の自動入力に使う。
    """
    grouped = {}
    for item in media_items:
        date_key = to_jst_date_str(item["timestamp"])
        grouped.setdefault(date_key, []).append(item)
    for date_key in grouped:
        grouped[date_key].sort(key=lambda m: m["timestamp"])
    return grouped
```

- [ ] **Step 4: テストを実行して通過することを確認**

Run: `python3 -m pytest tests/test_instagram.py -v`
Expected: 6 passed

- [ ] **Step 5: コミット**

```bash
git add tools_instagram.py tests/test_instagram.py
git commit -m "feat: Instagram Insights同期の日付変換・レート計算・投稿グルーピングを実装"
```

---

## Task 3: シート行マッチングロジック

**Files:**
- Modify: `tools_instagram.py`
- Test: `tests/test_instagram.py`

**Interfaces:**
- Consumes: なし（純粋関数）
- Produces: `find_row_by_value(all_values: list, col_idx: int, target_value: str, start_row_idx: int) -> int | None`

- [ ] **Step 1: 失敗するテストを書く**

`tests/test_instagram.py` に追記:

```python
from tools_instagram import find_row_by_value


def test_find_row_by_value_finds_matching_row():
    all_values = [
        ["日付", "投稿URL", "いいね"],
        ["", "", ""],
        ["日付", "投稿URL", "いいね"],
        ["7/20", "https://www.instagram.com/p/AAA/", "2"],
        ["7/21", "https://www.instagram.com/p/BBB/", "0"],
    ]
    idx = find_row_by_value(all_values, col_idx=1, target_value="https://www.instagram.com/p/BBB/", start_row_idx=3)
    assert idx == 4


def test_find_row_by_value_returns_none_when_not_found():
    all_values = [
        ["日付", "投稿URL"],
        ["7/20", "https://www.instagram.com/p/AAA/"],
    ]
    idx = find_row_by_value(all_values, col_idx=1, target_value="https://www.instagram.com/p/ZZZ/", start_row_idx=1)
    assert idx is None


def test_find_row_by_value_ignores_short_rows():
    all_values = [
        ["日付", "投稿URL"],
        ["7/20"],  # 投稿URL列が欠けている行
        ["7/21", "https://www.instagram.com/p/BBB/"],
    ]
    idx = find_row_by_value(all_values, col_idx=1, target_value="https://www.instagram.com/p/BBB/", start_row_idx=1)
    assert idx == 2
```

- [ ] **Step 2: テストを実行して失敗することを確認**

Run: `python3 -m pytest tests/test_instagram.py -v -k find_row_by_value`
Expected: FAIL（`find_row_by_value` が未定義）

- [ ] **Step 3: 実装を追加**

`tools_instagram.py` に追記:

```python
def find_row_by_value(all_values: list, col_idx: int, target_value: str, start_row_idx: int):
    """all_values（get_all_valuesの生データ）からcol_idx列がtarget_valueと一致する
    最初の行の0-indexedの絶対行番号を返す。start_row_idxより前は探索しない。
    見つからなければNoneを返す。
    """
    for i in range(start_row_idx, len(all_values)):
        row = all_values[i]
        if len(row) > col_idx and row[col_idx].strip() == target_value.strip():
            return i
    return None
```

- [ ] **Step 4: テストを実行して通過することを確認**

Run: `python3 -m pytest tests/test_instagram.py -v`
Expected: 9 passed

- [ ] **Step 5: コミット**

```bash
git add tools_instagram.py tests/test_instagram.py
git commit -m "feat: シート行マッチングロジックを実装"
```

---

## Task 4: Graph APIから投稿一覧を取得する（fetch_recent_media）

**Files:**
- Modify: `tools_instagram.py`
- Test: `tests/test_instagram.py`

**Interfaces:**
- Produces:
  - `class TokenExpiredError(Exception)`
  - `class RateLimitError(Exception)`
  - `class GraphAPIError(Exception)`
  - `fetch_recent_media(ig_user_id: str, access_token: str, since_date: str) -> list[dict]`
    - 各dictは `{"id": str, "permalink": str, "timestamp": str, "caption": str, "media_product_type": str}`

- [ ] **Step 1: 失敗するテストを書く**

`tests/test_instagram.py` に追記:

```python
from unittest.mock import patch, MagicMock
import requests
from tools_instagram import fetch_recent_media, TokenExpiredError, RateLimitError, GraphAPIError


def _mock_response(status_code, json_data):
    resp = MagicMock()
    resp.status_code = status_code
    resp.json.return_value = json_data
    return resp


@patch("tools_instagram.requests.get")
def test_fetch_recent_media_returns_parsed_list(mock_get):
    mock_get.return_value = _mock_response(200, {
        "data": [
            {
                "id": "123",
                "permalink": "https://www.instagram.com/p/AAA/",
                "timestamp": "2026-07-20T10:15:30+0000",
                "caption": "テスト投稿",
                "media_product_type": "REELS",
            }
        ]
    })
    result = fetch_recent_media("IG_USER_ID", "TOKEN", "2026-07-01")
    assert result == [{
        "id": "123",
        "permalink": "https://www.instagram.com/p/AAA/",
        "timestamp": "2026-07-20T10:15:30+0000",
        "caption": "テスト投稿",
        "media_product_type": "REELS",
    }]


@patch("tools_instagram.requests.get")
def test_fetch_recent_media_missing_caption_defaults_to_empty_string(mock_get):
    mock_get.return_value = _mock_response(200, {
        "data": [{
            "id": "123",
            "permalink": "https://www.instagram.com/p/AAA/",
            "timestamp": "2026-07-20T10:15:30+0000",
            "media_product_type": "IMAGE",
        }]
    })
    result = fetch_recent_media("IG_USER_ID", "TOKEN", "2026-07-01")
    assert result[0]["caption"] == ""


@patch("tools_instagram.requests.get")
def test_fetch_recent_media_raises_token_expired_error(mock_get):
    mock_get.return_value = _mock_response(400, {
        "error": {"message": "Error validating access token", "type": "OAuthException", "code": 190}
    })
    try:
        fetch_recent_media("IG_USER_ID", "TOKEN", "2026-07-01")
        assert False, "TokenExpiredError が発生するべき"
    except TokenExpiredError:
        pass


@patch("tools_instagram.time.sleep")
@patch("tools_instagram.requests.get")
def test_fetch_recent_media_retries_then_raises_rate_limit_error(mock_get, mock_sleep):
    mock_get.return_value = _mock_response(400, {
        "error": {"message": "Application request limit reached", "type": "OAuthException", "code": 4}
    })
    try:
        fetch_recent_media("IG_USER_ID", "TOKEN", "2026-07-01")
        assert False, "RateLimitError が発生するべき"
    except RateLimitError:
        pass
    assert mock_get.call_count == 4  # 初回 + リトライ3回
    assert mock_sleep.call_count == 3


@patch("tools_instagram.requests.get")
def test_fetch_recent_media_raises_generic_graph_api_error(mock_get):
    mock_get.return_value = _mock_response(400, {
        "error": {"message": "Unknown error", "type": "APIError", "code": 999}
    })
    try:
        fetch_recent_media("IG_USER_ID", "TOKEN", "2026-07-01")
        assert False, "GraphAPIError が発生するべき"
    except GraphAPIError:
        pass
```

- [ ] **Step 2: テストを実行して失敗することを確認**

Run: `python3 -m pytest tests/test_instagram.py -v -k fetch_recent_media`
Expected: FAIL（`fetch_recent_media` が未定義）

- [ ] **Step 3: 実装を追加**

`tools_instagram.py` の先頭に `import requests` と `import time` を追加し、末尾に追記:

```python
import time
import requests

GRAPH_API_BASE = "https://graph.facebook.com/v21.0"

_TOKEN_EXPIRED_CODES = {190}
_RATE_LIMIT_CODES = {4, 17, 32, 613}
_RATE_LIMIT_RETRY_DELAYS = [5, 15, 30]


class TokenExpiredError(Exception):
    pass


class RateLimitError(Exception):
    pass


class GraphAPIError(Exception):
    pass


def _raise_for_graph_error(resp) -> None:
    if resp.status_code == 200:
        return
    error = resp.json().get("error", {})
    code = error.get("code")
    message = error.get("message", resp.text)
    if code in _TOKEN_EXPIRED_CODES:
        raise TokenExpiredError(message)
    if code in _RATE_LIMIT_CODES:
        raise RateLimitError(message)
    raise GraphAPIError(f"code={code}: {message}")


def _get_with_retry(url: str, params: dict):
    """Graph APIにGETし、レート制限エラー(RateLimitError)の場合だけ
    バックオフしながら数回リトライする。トークン期限切れ・その他エラーは
    即座に呼び出し元へ伝播させる（リトライしない）。
    """
    last_error = None
    for delay in _RATE_LIMIT_RETRY_DELAYS:
        try:
            resp = requests.get(url, params=params, timeout=15)
            _raise_for_graph_error(resp)
            return resp
        except RateLimitError as e:
            last_error = e
            time.sleep(delay)
    resp = requests.get(url, params=params, timeout=15)
    _raise_for_graph_error(resp)
    return resp


def fetch_recent_media(ig_user_id: str, access_token: str, since_date: str) -> list:
    """指定日以降にIGアカウントへ投稿されたメディア一覧を取得する。
    since_date は 'YYYY-MM-DD' 形式。
    """
    resp = _get_with_retry(
        f"{GRAPH_API_BASE}/{ig_user_id}/media",
        params={
            "fields": "id,permalink,timestamp,caption,media_product_type",
            "since": since_date,
            "access_token": access_token,
        },
    )
    items = []
    for item in resp.json().get("data", []):
        items.append({
            "id": item["id"],
            "permalink": item["permalink"],
            "timestamp": item["timestamp"],
            "caption": item.get("caption", ""),
            "media_product_type": item["media_product_type"],
        })
    return items
```

- [ ] **Step 4: テストを実行して通過することを確認**

Run: `python3 -m pytest tests/test_instagram.py -v`
Expected: 14 passed

- [ ] **Step 5: コミット**

```bash
git add tools_instagram.py tests/test_instagram.py
git commit -m "feat: Graph APIから投稿一覧を取得するfetch_recent_mediaを実装"
```

---

## Task 5: Graph APIから投稿ごとのInsightsを取得する（fetch_media_insights）

**Files:**
- Modify: `tools_instagram.py`
- Test: `tests/test_instagram.py`

**Interfaces:**
- Consumes: `_raise_for_graph_error`, `TokenExpiredError`, `RateLimitError`, `GraphAPIError`（Task 4で定義）
- Produces: `fetch_media_insights(media_id: str, media_product_type: str, access_token: str) -> dict`
  - 戻り値のキー: `reach`, `reach_follower`, `reach_nonfollower`, `likes`, `comments`, `saved`, `follows`, `profile_activity`, `link_taps`, `views`, `avg_watch_time`

Meta Graph APIのメトリクス名・breakdown仕様は変わることがあるため、実装後は必ず実アカウントの1投稿で疎通確認すること（Task 9のセットアップ手順書にも明記する）。

- [ ] **Step 1: 失敗するテストを書く**

`tests/test_instagram.py` に追記:

```python
from tools_instagram import fetch_media_insights


def _breakdown_response(total_value, dimension_key, breakdown_results):
    return {
        "data": [{
            "name": "reach",
            "total_value": {
                "value": total_value,
                "breakdowns": [{
                    "results": [
                        {"dimension_values": [dim], "value": val}
                        for dim, val in breakdown_results.items()
                    ]
                }]
            }
        }]
    }


@patch("tools_instagram.requests.get")
def test_fetch_media_insights_image_post(mock_get):
    def side_effect(url, params, timeout):
        metric = params.get("metric", "")
        if metric == "reach":
            return _mock_response(200, _breakdown_response(100, "follow_type", {"FOLLOWER": 80, "NON_FOLLOWER": 20}))
        if metric == "profile_activity":
            return _mock_response(200, _breakdown_response(10, "action_type", {"BIO_LINK_CLICKED": 3, "OTHER": 7}))
        if metric == "likes,comments,saved,follows,profile_visits":
            return _mock_response(200, {
                "data": [
                    {"name": "likes", "total_value": {"value": 15}},
                    {"name": "comments", "total_value": {"value": 2}},
                    {"name": "saved", "total_value": {"value": 5}},
                    {"name": "follows", "total_value": {"value": 1}},
                    {"name": "profile_visits", "total_value": {"value": 8}},
                ]
            })
        raise AssertionError(f"想定外のmetricリクエスト: {metric}")

    mock_get.side_effect = side_effect
    result = fetch_media_insights("MEDIA_ID", "IMAGE", "TOKEN")
    assert result["reach"] == 100
    assert result["reach_follower"] == 80
    assert result["reach_nonfollower"] == 20
    assert result["likes"] == 15
    assert result["comments"] == 2
    assert result["saved"] == 5
    assert result["follows"] == 1
    assert result["profile_activity"] == 10
    assert result["link_taps"] == 3
    assert result["views"] is None
    assert result["avg_watch_time"] is None


@patch("tools_instagram.requests.get")
def test_fetch_media_insights_reels_post_includes_video_metrics(mock_get):
    def side_effect(url, params, timeout):
        metric = params.get("metric", "")
        if metric == "reach":
            return _mock_response(200, _breakdown_response(50, "follow_type", {"FOLLOWER": 40, "NON_FOLLOWER": 10}))
        if metric == "profile_activity":
            return _mock_response(200, _breakdown_response(2, "action_type", {"BIO_LINK_CLICKED": 1, "OTHER": 1}))
        if metric == "likes,comments,saved,follows,profile_visits":
            return _mock_response(200, {
                "data": [
                    {"name": "likes", "total_value": {"value": 5}},
                    {"name": "comments", "total_value": {"value": 0}},
                    {"name": "saved", "total_value": {"value": 1}},
                    {"name": "follows", "total_value": {"value": 0}},
                    {"name": "profile_visits", "total_value": {"value": 3}},
                ]
            })
        if metric == "views,ig_reels_avg_watch_time":
            return _mock_response(200, {
                "data": [
                    {"name": "views", "total_value": {"value": 155}},
                    {"name": "ig_reels_avg_watch_time", "total_value": {"value": 3.2}},
                ]
            })
        raise AssertionError(f"想定外のmetricリクエスト: {metric}")

    mock_get.side_effect = side_effect
    result = fetch_media_insights("MEDIA_ID", "REELS", "TOKEN")
    assert result["views"] == 155
    assert result["avg_watch_time"] == 3.2


@patch("tools_instagram.requests.get")
def test_fetch_media_insights_raises_token_expired_error(mock_get):
    mock_get.return_value = _mock_response(400, {
        "error": {"message": "Error validating access token", "type": "OAuthException", "code": 190}
    })
    try:
        fetch_media_insights("MEDIA_ID", "IMAGE", "TOKEN")
        assert False, "TokenExpiredError が発生するべき"
    except TokenExpiredError:
        pass
```

- [ ] **Step 2: テストを実行して失敗することを確認**

Run: `python3 -m pytest tests/test_instagram.py -v -k fetch_media_insights`
Expected: FAIL（`fetch_media_insights` が未定義）

- [ ] **Step 3: 実装を追加**

`tools_instagram.py` に追記:

```python
def _graph_insights_get(media_id: str, metric: str, access_token: str, breakdown: str = None) -> dict:
    params = {"metric": metric, "access_token": access_token, "metric_type": "total_value"}
    if breakdown:
        params["breakdown"] = breakdown
    resp = _get_with_retry(f"{GRAPH_API_BASE}/{media_id}/insights", params)
    return resp.json()


def _parse_totals(payload: dict) -> dict:
    """breakdownなしの単純な合計値レスポンスを {メトリクス名: 値} に変換する。"""
    return {item["name"]: item["total_value"]["value"] for item in payload.get("data", [])}


def _parse_breakdown(payload: dict) -> dict:
    """breakdown付きレスポンスを {"total": 合計値, "breakdown": {次元名: 値}} に変換する。"""
    entry = payload["data"][0]
    total = entry["total_value"]["value"]
    breakdown = {}
    for result in entry["total_value"]["breakdowns"][0]["results"]:
        dim = result["dimension_values"][0]
        breakdown[dim] = result["value"]
    return {"total": total, "breakdown": breakdown}


def fetch_media_insights(media_id: str, media_product_type: str, access_token: str) -> dict:
    """1投稿分のInsightsを取得し、シートの自動入力列に対応する形へ正規化する。"""
    reach_payload = _graph_insights_get(media_id, "reach", access_token, breakdown="follow_type")
    reach_data = _parse_breakdown(reach_payload)

    profile_payload = _graph_insights_get(media_id, "profile_activity", access_token, breakdown="action_type")
    profile_data = _parse_breakdown(profile_payload)

    totals_payload = _graph_insights_get(
        media_id, "likes,comments,saved,follows,profile_visits", access_token
    )
    totals = _parse_totals(totals_payload)

    result = {
        "reach": reach_data["total"],
        "reach_follower": reach_data["breakdown"].get("FOLLOWER", 0),
        "reach_nonfollower": reach_data["breakdown"].get("NON_FOLLOWER", 0),
        "likes": totals.get("likes", 0),
        "comments": totals.get("comments", 0),
        "saved": totals.get("saved", 0),
        "follows": totals.get("follows", 0),
        "profile_activity": profile_data["total"],
        "link_taps": profile_data["breakdown"].get("BIO_LINK_CLICKED", 0),
        "views": None,
        "avg_watch_time": None,
    }

    if media_product_type == "REELS":
        video_payload = _graph_insights_get(media_id, "views,ig_reels_avg_watch_time", access_token)
        video_totals = _parse_totals(video_payload)
        result["views"] = video_totals.get("views", 0)
        result["avg_watch_time"] = video_totals.get("ig_reels_avg_watch_time", 0)

    return result
```

- [ ] **Step 4: テストを実行して通過することを確認**

Run: `python3 -m pytest tests/test_instagram.py -v`
Expected: 17 passed

- [ ] **Step 5: コミット**

```bash
git add tools_instagram.py tests/test_instagram.py
git commit -m "feat: 投稿ごとのInstagram Insights取得(fetch_media_insights)を実装"
```

---

## Task 6: Google Sheetsへの書き込み（sync_to_sheet）

**Files:**
- Modify: `tools_instagram.py`
- Test: `tests/test_instagram.py`

**Interfaces:**
- Consumes: `find_row_by_value`（Task 3）
- Produces: `sync_to_sheet(worksheet, header_row_idx: int, id_col_name: str, entries: list) -> list[str]`
  - `worksheet` は `get_all_values() -> list[list[str]]`、`update_cell(row, col, value) -> None`、`append_row(values: list, value_input_option: str) -> None` を持つダックタイピングオブジェクト（`gspread.Worksheet` 互換）
  - `entries` の各要素: `{"match_value": str, "updates": {列名: 値}, "new_row_defaults": {列名: 値}}`
  - 戻り値: 処理内容のログメッセージのリスト（各投稿1行）

- [ ] **Step 1: 失敗するテストを書く**

`tests/test_instagram.py` に追記:

```python
from tools_instagram import sync_to_sheet


class FakeWorksheet:
    def __init__(self, all_values):
        self._all_values = all_values
        self.updated_cells = []
        self.appended_rows = []

    def get_all_values(self):
        return self._all_values

    def update_cell(self, row, col, value):
        self.updated_cells.append((row, col, value))

    def append_row(self, values, value_input_option="USER_ENTERED"):
        self.appended_rows.append(values)


def test_sync_to_sheet_updates_existing_row():
    all_values = [
        ["", "", ""],
        ["", "", ""],
        ["日付", "投稿URL", "いいね"],
        ["7/20", "https://www.instagram.com/p/AAA/", ""],
    ]
    ws = FakeWorksheet(all_values)
    entries = [{
        "match_value": "https://www.instagram.com/p/AAA/",
        "updates": {"いいね": 12},
        "new_row_defaults": {"日付": "7/20", "投稿URL": "https://www.instagram.com/p/AAA/"},
    }]
    logs = sync_to_sheet(ws, header_row_idx=2, id_col_name="投稿URL", entries=entries)
    # header_row_idx=2 は0-indexed。実シート行番号は header_row_idx+1(1-indexed) から数えて
    # 一致した行(0-indexedで3) => 1-indexed row 4, いいね列は0-indexedで2 => 1-indexed col 3
    assert ws.updated_cells == [(4, 3, 12)]
    assert ws.appended_rows == []
    assert len(logs) == 1


def test_sync_to_sheet_appends_new_row_when_not_found():
    all_values = [
        ["日付", "投稿URL", "いいね"],
    ]
    ws = FakeWorksheet(all_values)
    entries = [{
        "match_value": "https://www.instagram.com/p/NEW/",
        "updates": {"いいね": 3},
        "new_row_defaults": {"日付": "7/22", "投稿URL": "https://www.instagram.com/p/NEW/"},
    }]
    logs = sync_to_sheet(ws, header_row_idx=0, id_col_name="投稿URL", entries=entries)
    assert ws.updated_cells == []
    assert ws.appended_rows == [["7/22", "https://www.instagram.com/p/NEW/", 3]]
    assert len(logs) == 1


def test_sync_to_sheet_skips_unknown_column_names():
    all_values = [
        ["日付", "投稿URL"],
        ["7/20", "https://www.instagram.com/p/AAA/"],
    ]
    ws = FakeWorksheet(all_values)
    entries = [{
        "match_value": "https://www.instagram.com/p/AAA/",
        "updates": {"存在しない列": 99},
        "new_row_defaults": {},
    }]
    sync_to_sheet(ws, header_row_idx=0, id_col_name="投稿URL", entries=entries)
    assert ws.updated_cells == []
```

- [ ] **Step 2: テストを実行して失敗することを確認**

Run: `python3 -m pytest tests/test_instagram.py -v -k sync_to_sheet`
Expected: FAIL（`sync_to_sheet` が未定義）

- [ ] **Step 3: 実装を追加**

`tools_instagram.py` に追記:

```python
def sync_to_sheet(worksheet, header_row_idx: int, id_col_name: str, entries: list) -> list:
    """entriesの各項目をworksheetに反映する。
    header列名は最初に出現した位置（leftmost）を使う。タブ2のように同名列が
    複数回出現するシートでも、当日ブロック（左側）が常に自動入力対象になる想定。
    """
    all_values = worksheet.get_all_values()
    header = all_values[header_row_idx]
    id_col_idx = header.index(id_col_name)
    logs = []

    for entry in entries:
        row_idx = find_row_by_value(
            all_values, id_col_idx, entry["match_value"], start_row_idx=header_row_idx + 1
        )
        if row_idx is not None:
            sheet_row_number = row_idx + 1  # gspreadは1-indexed
            for col_name, value in entry["updates"].items():
                if col_name not in header:
                    continue
                col_number = header.index(col_name) + 1
                worksheet.update_cell(sheet_row_number, col_number, value)
            logs.append(f"更新: {entry['match_value']}")
        else:
            new_row = [""] * len(header)
            for col_name, value in {**entry["new_row_defaults"], **entry["updates"]}.items():
                if col_name not in header:
                    continue
                new_row[header.index(col_name)] = value
            worksheet.append_row(new_row, value_input_option="USER_ENTERED")
            logs.append(f"新規追加: {entry['match_value']}")

    return logs
```

- [ ] **Step 4: テストを実行して通過することを確認**

Run: `python3 -m pytest tests/test_instagram.py -v`
Expected: 20 passed

- [ ] **Step 5: コミット**

```bash
git add tools_instagram.py tests/test_instagram.py
git commit -m "feat: Google Sheetsへのシート行反映(sync_to_sheet)を実装"
```

---

## Task 7: オーケストレーション関数とCLIスクリプト

**Files:**
- Modify: `tools_instagram.py`
- Create: `scripts/sync_instagram_insights.py`
- Test: `tests/test_instagram.py`

**Interfaces:**
- Consumes: `fetch_recent_media`, `fetch_media_insights`, `compute_rates`, `group_media_by_date`, `sync_to_sheet`, `TokenExpiredError`, `RateLimitError`, `GraphAPIError`（Task 2, 4, 5, 6）
- Produces: `sync_instagram_insights(ig_user_id, access_token, sheet_id, service_account_json_path, since_date) -> str`（実行結果のサマリーテキストを返す）

- [ ] **Step 1: 失敗するテストを書く**

`tests/test_instagram.py` に追記:

```python
from tools_instagram import sync_instagram_insights


@patch("tools_instagram._open_worksheets")
@patch("tools_instagram.fetch_media_insights")
@patch("tools_instagram.fetch_recent_media")
def test_sync_instagram_insights_happy_path(mock_fetch_media, mock_fetch_insights, mock_open_ws):
    mock_fetch_media.return_value = [{
        "id": "1", "permalink": "https://www.instagram.com/p/AAA/",
        "timestamp": "2026-07-20T10:00:00+0000", "caption": "テスト", "media_product_type": "REELS",
    }]
    mock_fetch_insights.return_value = {
        "reach": 100, "reach_follower": 80, "reach_nonfollower": 20,
        "likes": 10, "comments": 1, "saved": 5, "follows": 2,
        "profile_activity": 8, "link_taps": 3, "views": 150, "avg_watch_time": 3.5,
    }
    tab1_ws = FakeWorksheet([
        ["日付", "投稿ＵＲＬ", "全体リーチ", "フォロワー％", "フォロワー", "フォロワー外", "いいね", "保存"],
    ])
    tab2_ws = FakeWorksheet([
        ["日付", "①リーチ", "フォロワー", "フォロワー外", "⑨いいね", "⑩保存"],
    ])
    mock_open_ws.return_value = (tab1_ws, tab2_ws)

    summary = sync_instagram_insights(
        ig_user_id="IG_ID", access_token="TOKEN", sheet_id="SHEET_ID",
        service_account_json_path="/path/to/key.json", since_date="2026-07-01",
    )
    assert "1件" in summary
    assert len(tab1_ws.appended_rows) == 1
    assert len(tab2_ws.appended_rows) == 1


@patch("tools_instagram._open_worksheets")
@patch("tools_instagram.fetch_media_insights")
@patch("tools_instagram.fetch_recent_media")
def test_sync_instagram_insights_aborts_on_token_expired(mock_fetch_media, mock_fetch_insights, mock_open_ws):
    mock_fetch_media.side_effect = TokenExpiredError("expired")
    summary = sync_instagram_insights(
        ig_user_id="IG_ID", access_token="TOKEN", sheet_id="SHEET_ID",
        service_account_json_path="/path/to/key.json", since_date="2026-07-01",
    )
    assert "トークン期限切れ" in summary
    mock_open_ws.assert_not_called()


@patch("tools_instagram._open_worksheets")
@patch("tools_instagram.fetch_media_insights")
@patch("tools_instagram.fetch_recent_media")
def test_sync_instagram_insights_skips_media_on_insights_failure(mock_fetch_media, mock_fetch_insights, mock_open_ws):
    mock_fetch_media.return_value = [
        {"id": "1", "permalink": "https://www.instagram.com/p/AAA/",
         "timestamp": "2026-07-20T10:00:00+0000", "caption": "", "media_product_type": "IMAGE"},
        {"id": "2", "permalink": "https://www.instagram.com/p/BBB/",
         "timestamp": "2026-07-21T10:00:00+0000", "caption": "", "media_product_type": "IMAGE"},
    ]
    mock_fetch_insights.side_effect = [
        GraphAPIError("boom"),
        {"reach": 50, "reach_follower": 40, "reach_nonfollower": 10, "likes": 5, "comments": 0,
         "saved": 1, "follows": 0, "profile_activity": 2, "link_taps": 0, "views": None, "avg_watch_time": None},
    ]
    tab1_ws = FakeWorksheet([
        ["日付", "投稿ＵＲＬ", "全体リーチ", "フォロワー％", "フォロワー", "フォロワー外", "いいね", "保存"],
    ])
    tab2_ws = FakeWorksheet([
        ["日付", "①リーチ", "フォロワー", "フォロワー外", "⑨いいね", "⑩保存"],
    ])
    mock_open_ws.return_value = (tab1_ws, tab2_ws)

    summary = sync_instagram_insights(
        ig_user_id="IG_ID", access_token="TOKEN", sheet_id="SHEET_ID",
        service_account_json_path="/path/to/key.json", since_date="2026-07-01",
    )
    assert len(tab1_ws.appended_rows) == 1  # 失敗した1件目はスキップされ、2件目だけ反映
    assert "スキップ" in summary
```

- [ ] **Step 2: テストを実行して失敗することを確認**

Run: `python3 -m pytest tests/test_instagram.py -v -k sync_instagram_insights`
Expected: FAIL（`sync_instagram_insights` / `_open_worksheets` が未定義）

- [ ] **Step 3: 実装を追加**

`tools_instagram.py` に追記:

```python
TAB1_GID = 1526183674
TAB2_GID = 0
HEADER_ROW_IDX = 2  # シート内の実際の列見出し行（0-indexed）。実物で要確認。


def _open_worksheets(sheet_id: str, service_account_json_path: str):
    import gspread
    client = gspread.service_account(filename=service_account_json_path)
    spreadsheet = client.open_by_key(sheet_id)
    tab1 = spreadsheet.get_worksheet_by_id(TAB1_GID)
    tab2 = spreadsheet.get_worksheet_by_id(TAB2_GID)
    return tab1, tab2


def _build_tab1_entry(media: dict, insights: dict, rates: dict) -> dict:
    """タブ1は「フォロワー％」（構成比）、「フォロワー」「フォロワー外」（実数）の
    3列に分かれているため、reach_followerを実数列に、reach/reachの比率を％列に入れる。
    """
    date_str = to_jst_date_str(media["timestamp"])
    reach = insights["reach"] or 0
    follower_pct = round(insights["reach_follower"] / reach, 4) if reach else 0.0
    return {
        "match_value": media["permalink"],
        "updates": {
            "日付": date_str,
            "全体リーチ": insights["reach"],
            "フォロワー％": follower_pct,
            "フォロワー": insights["reach_follower"],
            "フォロワー外": insights["reach_nonfollower"],
            "再生数": insights["views"] if insights["views"] is not None else "",
            "平均再生時間": insights["avg_watch_time"] if insights["avg_watch_time"] is not None else "",
            "いいね率": rates["like_rate"],
            "保存率": rates["save_rate"],
            "プロアク率": rates["profile_activity_rate"],
            "リンクタップ率": rates["link_tap_rate"],
            "プロアク": insights["profile_activity"],
            "リンクタップ": insights["link_taps"],
            "いいね": insights["likes"],
            "保存": insights["saved"],
            "コメント": insights["comments"],
            "フォロー数": insights["follows"],
        },
        "new_row_defaults": {"日付": date_str, "投稿ＵＲＬ": media["permalink"]},
    }


def _build_tab2_entry(date_str: str, insights: dict) -> dict:
    return {
        "match_value": date_str,
        "updates": {
            "①リーチ": insights["reach"],
            "フォロワー": insights["reach_follower"],
            "フォロワー外": insights["reach_nonfollower"],
            "⑨いいね": insights["likes"],
            "⑩保存": insights["saved"],
            "⑪プロフアクセス": insights["profile_activity"],
            "リンククリック": insights["link_taps"],
            "⑫フォロー": insights["follows"],
        },
        "new_row_defaults": {"日付": date_str},
    }


def sync_instagram_insights(
    ig_user_id: str, access_token: str, sheet_id: str,
    service_account_json_path: str, since_date: str,
) -> str:
    """直近の投稿のInsightsを取得し、タブ1・2に自動入力する。戻り値はログサマリー文字列。"""
    try:
        media_items = fetch_recent_media(ig_user_id, access_token, since_date)
    except TokenExpiredError as e:
        return f"トークン期限切れです。.envのMETA_ACCESS_TOKENを再発行してください: {e}"
    except (RateLimitError, GraphAPIError) as e:
        return f"投稿一覧の取得に失敗しました: {e}"

    tab1_entries = []
    tab2_source = {}
    skipped = []

    for media in media_items:
        try:
            insights = fetch_media_insights(media["id"], media["media_product_type"], access_token)
        except TokenExpiredError as e:
            return f"トークン期限切れです。.envのMETA_ACCESS_TOKENを再発行してください: {e}"
        except (RateLimitError, GraphAPIError) as e:
            skipped.append(f"{media['permalink']} ({e})")
            continue

        rates = compute_rates(insights)
        tab1_entries.append(_build_tab1_entry(media, insights, rates))

        date_str = to_jst_date_str(media["timestamp"])
        if date_str not in tab2_source:
            tab2_source[date_str] = insights
        else:
            skipped.append(f"{media['permalink']} (同日{date_str}の2件目以降のためタブ2は手動確認)")

    tab1_ws, tab2_ws = _open_worksheets(sheet_id, service_account_json_path)
    tab1_logs = sync_to_sheet(tab1_ws, HEADER_ROW_IDX, "投稿ＵＲＬ", tab1_entries)

    tab2_entries = [_build_tab2_entry(date_str, insights) for date_str, insights in tab2_source.items()]
    tab2_logs = sync_to_sheet(tab2_ws, HEADER_ROW_IDX, "日付", tab2_entries)

    summary = f"タブ1: {len(tab1_logs)}件処理、タブ2: {len(tab2_logs)}件処理"
    if skipped:
        summary += f" / スキップ: {len(skipped)}件（{'; '.join(skipped)}）"
    return summary
```

- [ ] **Step 4: テストを実行して通過することを確認**

Run: `python3 -m pytest tests/test_instagram.py -v`
Expected: 23 passed

- [ ] **Step 5: CLIスクリプトを作成**

`scripts/sync_instagram_insights.py` を新規作成:

```python
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
```

- [ ] **Step 6: CLIの起動確認（環境変数未設定でもクラッシュしないことだけ確認）**

Run: `python3 scripts/sync_instagram_insights.py`
Expected: `❌ 必要な環境変数が未設定です: META_ACCESS_TOKEN, META_IG_USER_ID, GOOGLE_SERVICE_ACCOUNT_JSON, INSTAGRAM_SHEET_ID` が表示され、例外なく終了する

- [ ] **Step 7: コミット**

```bash
git add tools_instagram.py scripts/sync_instagram_insights.py tests/test_instagram.py
git commit -m "feat: Instagram Insights同期のオーケストレーション関数とCLIを実装"
```

---

## Task 8: runner.pyの週次スケジュールに組み込む

**Files:**
- Modify: `runner.py`
- Test: `tests/test_runner.py`

**Interfaces:**
- Consumes: `sync_instagram_insights`（Task 7）

- [ ] **Step 1: 失敗するテストを書く**

`tests/test_runner.py` の末尾に追記（既存のimport群に `instagram_insights_task` を追加する形）:

```python
from unittest.mock import patch
from runner import instagram_insights_task


@patch("runner.sync_instagram_insights")
def test_instagram_insights_task_calls_sync_and_does_not_raise(mock_sync):
    mock_sync.return_value = "タブ1: 1件処理、タブ2: 1件処理"
    instagram_insights_task()  # 例外を投げなければOK
    mock_sync.assert_called_once()


@patch("runner.sync_instagram_insights")
def test_instagram_insights_task_swallows_exceptions(mock_sync):
    mock_sync.side_effect = Exception("boom")
    instagram_insights_task()  # 例外が外に漏れないことを確認
```

- [ ] **Step 2: テストを実行して失敗することを確認**

Run: `python3 -m pytest tests/test_runner.py -v -k instagram_insights_task`
Expected: FAIL（`instagram_insights_task` が未定義）

- [ ] **Step 3: runner.pyに実装を追加**

`runner.py` の先頭付近、既存のimport群（`from tools_express import ...` の下）に追記:

```python
from tools_instagram import sync_instagram_insights
```

`runner.py` に新しい関数を追加（`wednesday_task` の直前が自然な配置）:

```python
def instagram_insights_task():
    try:
        access_token = os.environ.get("META_ACCESS_TOKEN")
        ig_user_id = os.environ.get("META_IG_USER_ID")
        service_account_json_path = os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON")
        sheet_id = os.environ.get("INSTAGRAM_SHEET_ID")
        if not all([access_token, ig_user_id, service_account_json_path, sheet_id]):
            print("  ⏭️ Instagram Insights同期: 環境変数未設定のためスキップ")
            return
        since_date = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
        summary = sync_instagram_insights(ig_user_id, access_token, sheet_id, service_account_json_path, since_date)
        print(f"  📊 Instagram Insights同期: {summary}")
    except Exception as e:
        print(f"  ❌ Instagram Insights同期 失敗: {e}")
```

`runner.py` の先頭のimportに `timedelta` を追加する（既存の `from datetime import datetime` を修正）:

```python
from datetime import datetime, timedelta
```

- [ ] **Step 4: テストを実行して通過することを確認**

Run: `python3 -m pytest tests/test_runner.py -v -k instagram_insights_task`
Expected: 2 passed

- [ ] **Step 5: 週次スケジュールに登録**

`runner.py` の `main()` 関数内、水曜のレビュー通知タスク登録の直前に追記:

```python
schedule.every().wednesday.at("08:45").do(instagram_insights_task)
```

`main()` 内の起動時ログ出力（`print("水09:00 レビュー通知 ...")` の行）に追記:

```python
print("水08:45 Instagram Insights同期 / 水09:00 レビュー通知 / 金09:00 SNS投稿文 / 日20:00 反応分析")
```

（既存の同一行の文字列を書き換える）

- [ ] **Step 6: 全体テストを実行して既存テストを壊していないことを確認**

Run: `python3 -m pytest tests/ -v`
Expected: 全件 passed（既存テスト含む）

- [ ] **Step 7: コミット**

```bash
git add runner.py tests/test_runner.py
git commit -m "feat: Instagram Insights同期を水曜08:45の週次タスクに追加"
```

---

## Task 9: オーナー向けセットアップ手順書

**Files:**
- Create: `docs/instagram_insights_setup.md`
- Modify: `CLAUDE.md`（環境変数一覧とマニュアルへのリンクを追記）

- [ ] **Step 1: セットアップ手順書を作成**

`docs/instagram_insights_setup.md` を新規作成:

```markdown
# Instagram Insights自動連携 セットアップマニュアル

Instagramの投稿分析（いいね・保存・リーチなど）を、毎週手動でコピーする代わりに
自動でスプレッドシートに反映する機能のセットアップ手順です。

この手順は最初の1回だけ、オーナーご自身で行っていただく必要があります。

---

## 1. Instagramをプロアカウントにする

1. Instagramアプリ → 設定 → アカウントの種類とツール
2. 「プロアカウントに切り替える」→ 「クリエイター」または「ビジネス」を選択

すでにプロアカウントになっている場合はこの手順は不要です。

## 2. Facebookページと連携する

1. プロアカウント設定の中の「ページ」または「アカウントセンター」から、
   連携するFacebookページを作成（または既存ページを選択）
2. 画面の案内に沿ってInstagramアカウントと連携する

## 3. Meta for Developersでアプリを作成する

1. https://developers.facebook.com/ にアクセスし、開発者登録
2. 「アプリを作成」→ 種類は「ビジネス」を選択
3. 作成したアプリに「Instagram」プロダクトを追加
4. アプリの設定画面から、連携したFacebookページ・Instagramアカウントを選択

## 4. 長期アクセストークンを発行する

1. Meta for Developersのツール「Graph APIエクスプローラー」を開く
2. 作成したアプリを選択し、`instagram_basic` `instagram_manage_insights` の
   権限にチェックを入れてトークンを生成
3. 生成された短期トークンを、長期トークン（約60日有効）に交換する
   （Graph APIエクスプローラーの案内、または以下のURLで交換）:
   ```
   https://graph.facebook.com/v21.0/oauth/access_token?grant_type=fb_exchange_token&client_id=アプリID&client_secret=アプリシークレット&fb_exchange_token=短期トークン
   ```
4. 発行された長期トークンを `.env` の `META_ACCESS_TOKEN` に設定する
5. InstagramビジネスアカウントのID（数字の羅列）を `.env` の `META_IG_USER_ID` に設定する
   （Graph APIエクスプローラーで `me/accounts` → 該当ページ → `instagram_business_account` から確認できる）

⚠️ このトークンは約60日で失効します。失効すると同期処理が
「トークン期限切れです」というメッセージを出して止まるので、そのタイミングで
このステップ4を再度行ってください。

## 5. Google Cloudサービスアカウントを作成する

1. https://console.cloud.google.com/ でプロジェクトを作成（または既存プロジェクトを使用）
2. 「APIとサービス」→ 「ライブラリ」で Google Sheets API を有効化
3. 「認証情報」→ 「認証情報を作成」→ 「サービスアカウント」を作成
4. 作成したサービスアカウントの「キー」タブから「鍵を追加」→ JSON形式でダウンロード
5. ダウンロードしたJSONファイルを分かりやすい場所に保存し、そのパスを
   `.env` の `GOOGLE_SERVICE_ACCOUNT_JSON` に設定する

## 6. スプレッドシートをサービスアカウントに共有する

1. ダウンロードしたJSONファイルの中の `client_email`（〇〇@〇〇.iam.gserviceaccount.com
   のようなメールアドレス）をコピー
2. 対象のスプレッドシートを開き、右上の「共有」からこのメールアドレスを
   **編集者**権限で追加

## 7. スプレッドシートIDを設定する

スプレッドシートのURL `https://docs.google.com/spreadsheets/d/【この部分】/edit...`
の【この部分】を `.env` の `INSTAGRAM_SHEET_ID` に設定する

---

## 動作確認

すべて設定したら、以下を実行して1回分だけ試してみてください。

```bash
python3 scripts/sync_instagram_insights.py
```

「✅ タブ1: N件処理、タブ2: N件処理」と表示されればOKです。
「❌」や「トークン期限切れ」と出た場合は、上記の手順を見直してください。

以降は毎週水曜08:45に `runner.py` から自動実行されます。
```

- [ ] **Step 2: CLAUDE.mdに環境変数とマニュアルへのリンクを追記**

`CLAUDE.md` の環境変数セクション（`.env`）に追記:

```
META_ACCESS_TOKEN=...        # 任意（Instagram Insights自動連携に必須）
META_IG_USER_ID=...          # 任意（同上）
GOOGLE_SERVICE_ACCOUNT_JSON=... # 任意（同上：Sheets書き込み用サービスアカウントキーのパス）
INSTAGRAM_SHEET_ID=...       # 任意（同上：対象スプレッドシートID）
```

`CLAUDE.md` の主要コマンドセクションに追記:

```
# Instagram Insightsをスプレッドシートに手動同期
python3 scripts/sync_instagram_insights.py
```

📖 セットアップ手順: `docs/instagram_insights_setup.md` へのリンクも追記する。

- [ ] **Step 3: コミット**

```bash
git add docs/instagram_insights_setup.md CLAUDE.md
git commit -m "docs: Instagram Insights自動連携のセットアップ手順書を追加"
```

---

## 完了確認

- [ ] `python3 -m pytest tests/ -v` が全件通過する
- [ ] `docs/instagram_insights_setup.md` の手順に沿ってオーナーが実際にセットアップできる
- [ ] `python3 scripts/sync_instagram_insights.py` を実アカウントで1回試し、タブ1・2に実データが反映されることを確認する（この最終確認だけは実際のMeta/Google認証情報が揃うまで実施できない）
