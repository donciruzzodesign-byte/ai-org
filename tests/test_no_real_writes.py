import runner


def test_report_failure_does_not_touch_real_notion_or_log(tmp_path):
    runner._report_failure("テスト用タスク", Exception("x"))  # 本物のNotion/ログに出ないこと(conftestで差し替え)
    assert runner.save_to_notion("t", "b") == "(テスト: Notion保存なし)"
