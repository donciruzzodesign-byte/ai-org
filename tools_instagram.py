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
