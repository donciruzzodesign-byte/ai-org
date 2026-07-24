from unittest.mock import patch, MagicMock
import requests
from tools_instagram import to_jst_date_str, compute_rates, group_media_by_date, find_row_by_value, fetch_recent_media, fetch_media_insights, sync_to_sheet, TokenExpiredError, RateLimitError, GraphAPIError


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
        {"id": "2", "timestamp": "2026-07-20T14:00:00+0000"},
        {"id": "1", "timestamp": "2026-07-20T10:00:00+0000"},
        {"id": "3", "timestamp": "2026-07-21T09:00:00+0000"},
    ]
    grouped = group_media_by_date(media)
    assert list(grouped.keys()) == ["7/20", "7/21"]
    assert [m["id"] for m in grouped["7/20"]] == ["1", "2"]
    assert [m["id"] for m in grouped["7/21"]] == ["3"]


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
    # HEADER_ROW_IDX=2: 実シート同様、1〜2行目は結合されたグループ見出し行のダミー、
    # 3行目（0-indexedで2）が実際の列見出し行。
    tab1_ws = FakeWorksheet([
        [], [],
        ["日付", "投稿ＵＲＬ", "全体リーチ", "フォロワー％", "フォロワー", "フォロワー外", "いいね", "保存"],
    ])
    tab2_ws = FakeWorksheet([
        [], [],
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
    # HEADER_ROW_IDX=2 に合わせ、1〜2行目はダミーの空行としてパディングする。
    tab1_ws = FakeWorksheet([
        [], [],
        ["日付", "投稿ＵＲＬ", "全体リーチ", "フォロワー％", "フォロワー", "フォロワー外", "いいね", "保存"],
    ])
    tab2_ws = FakeWorksheet([
        [], [],
        ["日付", "①リーチ", "フォロワー", "フォロワー外", "⑨いいね", "⑩保存"],
    ])
    mock_open_ws.return_value = (tab1_ws, tab2_ws)

    summary = sync_instagram_insights(
        ig_user_id="IG_ID", access_token="TOKEN", sheet_id="SHEET_ID",
        service_account_json_path="/path/to/key.json", since_date="2026-07-01",
    )
    assert len(tab1_ws.appended_rows) == 1  # 失敗した1件目はスキップされ、2件目だけ反映
    assert "スキップ" in summary
