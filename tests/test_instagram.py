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
        {"id": "2", "timestamp": "2026-07-20T14:00:00+0000"},
        {"id": "1", "timestamp": "2026-07-20T10:00:00+0000"},
        {"id": "3", "timestamp": "2026-07-21T09:00:00+0000"},
    ]
    grouped = group_media_by_date(media)
    assert list(grouped.keys()) == ["7/20", "7/21"]
    assert [m["id"] for m in grouped["7/20"]] == ["1", "2"]
    assert [m["id"] for m in grouped["7/21"]] == ["3"]
