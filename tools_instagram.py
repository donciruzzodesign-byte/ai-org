from datetime import datetime, timedelta, timezone
import time
import requests

_JST = timezone(timedelta(hours=9))

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

    # Sort dictionary keys by date (M/D format)
    def date_key(date_str):
        month, day = map(int, date_str.split('/'))
        return (month, day)

    return {k: grouped[k] for k in sorted(grouped.keys(), key=date_key)}


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
