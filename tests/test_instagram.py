from unittest.mock import patch, MagicMock
import requests
from tools_instagram import to_jst_date_str, compute_rates, group_media_by_date, find_row_by_value, fetch_recent_media, fetch_media_insights, TokenExpiredError, RateLimitError, GraphAPIError


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
