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
    """合計値レスポンスを {メトリクス名: 値} に変換する。breakdownを指定しない場合、
    Graph APIは metric_type=total_value を指定しても素の values 形式で返してくる
    （total_value 形式はbreakdown指定時のみ）。両形式に対応する。
    """
    result = {}
    for item in payload.get("data", []):
        if "total_value" in item:
            result[item["name"]] = item["total_value"]["value"]
        else:
            result[item["name"]] = item["values"][0]["value"]
    return result


def _parse_breakdown(payload: dict) -> dict:
    """breakdown付きレスポンスを {"total": 合計値, "breakdown": {次元名: 値}} に変換する。
    内訳の合計が0件のときはbreakdownsを含まないvalues形式で返ってくるため、その場合は
    breakdownを空辞書として扱う。
    """
    entry = payload["data"][0]
    if "total_value" in entry:
        total = entry["total_value"]["value"]
        breakdown = {}
        for result in entry["total_value"].get("breakdowns", [{}])[0].get("results", []):
            dim = result["dimension_values"][0]
            breakdown[dim] = result["value"]
        return {"total": total, "breakdown": breakdown}
    return {"total": entry["values"][0]["value"], "breakdown": {}}


# profile_activity / follows はFEED・STORY投稿のみ対応。REELSでは
# 「The Media Insights API does not support the profile_activity metric
# for this media product type.」のようなエラーになるため取得自体をスキップする。
_PROFILE_METRICS_UNSUPPORTED_TYPES = {"REELS"}


def fetch_media_insights(media_id: str, media_product_type: str, access_token: str) -> dict:
    """1投稿分のInsightsを取得し、シートの自動入力列に対応する形へ正規化する。
    reachのfollow_typeブレークダウンは投稿単位のGraph APIでは提供されないため、
    全体リーチのみ取得する（フォロワー/フォロワー外の内訳はシート側で手動記入）。
    """
    metrics = "reach,likes,comments,saved"
    if media_product_type not in _PROFILE_METRICS_UNSUPPORTED_TYPES:
        metrics += ",follows"
    totals_payload = _graph_insights_get(media_id, metrics, access_token)
    totals = _parse_totals(totals_payload)

    result = {
        "reach": totals.get("reach", 0),
        "likes": totals.get("likes", 0),
        "comments": totals.get("comments", 0),
        "saved": totals.get("saved", 0),
        "follows": totals.get("follows", 0),
        "profile_activity": 0,
        "link_taps": 0,
        "views": None,
        "avg_watch_time": None,
    }

    if media_product_type not in _PROFILE_METRICS_UNSUPPORTED_TYPES:
        profile_payload = _graph_insights_get(media_id, "profile_activity", access_token, breakdown="action_type")
        profile_data = _parse_breakdown(profile_payload)
        result["profile_activity"] = profile_data["total"]
        result["link_taps"] = profile_data["breakdown"].get("BIO_LINK_CLICKED", 0)

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
    """フォロワー％／フォロワー／フォロワー外の内訳はGraph APIで取得できないため、
    自動入力の対象外（シート側で手動記入）とし、全体リーチのみ反映する。
    """
    date_str = to_jst_date_str(media["timestamp"])
    return {
        "match_value": media["permalink"],
        "updates": {
            "日付": date_str,
            "全体リーチ": insights["reach"],
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
    """フォロワー／フォロワー外はGraph APIで取得できないため自動入力の対象外。"""
    return {
        "match_value": date_str,
        "updates": {
            "①リーチ": insights["reach"],
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

    # group_media_by_date と同じ「早い投稿が先」の順序を保証するため、
    # タブ2の重複排除ループに入る前にタイムスタンプ昇順へ並べ替える。
    media_items = sorted(media_items, key=lambda m: m["timestamp"])

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
