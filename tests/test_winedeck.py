import os
import sys

WINEDECK_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "winedeck"
)
if WINEDECK_DIR not in sys.path:
    sys.path.insert(0, WINEDECK_DIR)

import winedeck as wd


def test_cover_returns_svg_with_correct_dimensions():
    svg = wd.cover("red", badge="赤ワイン", q=["長期熟成する", "偉大な赤は？"],
                    answer="ネッビオーロ", subtitle="バローロの主役", grape="nebbiolo")
    assert svg.startswith("<svg")
    assert 'width="1080"' in svg
    assert 'height="1350"' in svg
    assert "ネッビオーロ" in svg


def test_rows_slide_includes_all_rows_and_footer():
    svg = wd.rows_slide("red", "REGULATION", "バローロDOCG規定",
                         [("最低熟成", "38ヶ月（うち樽18ヶ月）"), ("品種", "ネッビオーロ100%")],
                         num=2, total=3, grape="nebbiolo")
    assert "最低熟成" in svg
    assert "38ヶ月（うち樽18ヶ月）" in svg
    assert "02 / 03" in svg


def test_summary_slide_includes_points_and_cta():
    svg = wd.summary_slide("red", "バローロ まとめ",
                            ["ネッビオーロ100%の長期熟成型", "最低38ヶ月（樽18ヶ月）熟成"],
                            cta="保存して一本選びに。", num=3, total=3)
    assert "バローロ まとめ" in svg
    assert "保存して一本選びに。" in svg


def test_unknown_wine_type_raises_keyerror():
    import pytest
    with pytest.raises(KeyError):
        wd.cover("nonexistent", badge="x", q=["a"], answer="b", subtitle="c")
