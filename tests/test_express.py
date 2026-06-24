import os
import pytest
from tools_express import (
    get_weekly_dir,
    TEMPLATES_DIR,
    WEEKLY_BASE_DIR,
    generate_brand_svgs,
    fill_svg_template,
    svg_to_png,
    generate_weekly_assets,
)


def test_get_weekly_dir_creates_directory(tmp_path):
    result = get_weekly_dir("2026-06-24", "wine", base_dir=str(tmp_path))
    assert os.path.isdir(result)
    assert result.endswith("2026-06-24-wine")


def test_get_weekly_dir_coffee(tmp_path):
    result = get_weekly_dir("2026-06-24", "coffee", base_dir=str(tmp_path))
    assert result.endswith("2026-06-24-coffee")


def test_templates_dir_is_under_desktop():
    assert "CUBOCCI_STUDIO" in TEMPLATES_DIR
    assert os.path.expanduser("~") in TEMPLATES_DIR


def test_generate_brand_svgs_creates_three_files(tmp_path):
    result = generate_brand_svgs(str(tmp_path))
    assert "youtube_thumbnail.svg" in result
    assert "reels_cover.svg" in result
    assert "title_card.svg" in result
    for path in result.values():
        assert os.path.exists(path)


def test_svgs_contain_brand_colors(tmp_path):
    generate_brand_svgs(str(tmp_path))
    for name in ["youtube_thumbnail.svg", "reels_cover.svg", "title_card.svg"]:
        with open(os.path.join(str(tmp_path), name), encoding="utf-8") as f:
            content = f.read()
        assert "#6B1A2A" in content
        assert "#C9A84C" in content
        assert "#F5F0E8" in content


def test_svgs_have_placeholder_fields(tmp_path):
    generate_brand_svgs(str(tmp_path))
    for name in ["youtube_thumbnail.svg", "reels_cover.svg", "title_card.svg"]:
        with open(os.path.join(str(tmp_path), name), encoding="utf-8") as f:
            content = f.read()
        assert "{{title}}" in content
        assert "{{subtitle}}" in content


def test_youtube_thumbnail_is_correct_size(tmp_path):
    generate_brand_svgs(str(tmp_path))
    with open(os.path.join(str(tmp_path), "youtube_thumbnail.svg"), encoding="utf-8") as f:
        content = f.read()
    assert 'width="1280"' in content
    assert 'height="720"' in content


def test_reels_cover_is_correct_size(tmp_path):
    generate_brand_svgs(str(tmp_path))
    with open(os.path.join(str(tmp_path), "reels_cover.svg"), encoding="utf-8") as f:
        content = f.read()
    assert 'width="1080"' in content
    assert 'height="1920"' in content


def test_title_card_is_correct_size(tmp_path):
    generate_brand_svgs(str(tmp_path))
    with open(os.path.join(str(tmp_path), "title_card.svg"), encoding="utf-8") as f:
        content = f.read()
    assert 'width="1920"' in content
    assert 'height="1080"' in content


def test_fill_svg_template_replaces_placeholders(tmp_path):
    tpl_dir = str(tmp_path / "tpl")
    generate_brand_svgs(tpl_dir)
    out = str(tmp_path / "out.svg")
    fill_svg_template(
        os.path.join(tpl_dir, "youtube_thumbnail.svg"),
        title="バローロの魅力",
        subtitle="王のワイン入門",
        output_path=out,
    )
    content = open(out, encoding="utf-8").read()
    assert "バローロの魅力" in content
    assert "王のワイン入門" in content
    assert "{{title}}" not in content
    assert "{{subtitle}}" not in content


def test_fill_svg_template_escapes_ampersand(tmp_path):
    tpl_dir = str(tmp_path / "tpl")
    generate_brand_svgs(tpl_dir)
    out = str(tmp_path / "out.svg")
    fill_svg_template(
        os.path.join(tpl_dir, "youtube_thumbnail.svg"),
        title="Wine & Food",
        subtitle="test",
        output_path=out,
    )
    content = open(out, encoding="utf-8").read()
    assert "&amp;" in content
    assert "Wine & Food" not in content


def test_svg_to_png_creates_file(tmp_path):
    tpl_dir = str(tmp_path / "tpl")
    generate_brand_svgs(tpl_dir)
    svg_path = os.path.join(tpl_dir, "youtube_thumbnail.svg")
    png_path = str(tmp_path / "thumb.png")
    result = svg_to_png(svg_path, png_path)
    assert os.path.exists(result)
    assert result.endswith(".png")


def test_generate_weekly_assets_creates_three_pngs(tmp_path):
    tpl_dir = str(tmp_path / "tpl")
    generate_brand_svgs(tpl_dir)
    results = generate_weekly_assets(
        title="バローロ入門",
        subtitle="ピエモンテの王様",
        date_str="2026-06-24",
        theme="wine",
        templates_dir=tpl_dir,
        base_dir=str(tmp_path / "weekly"),
    )
    weekly_dir = os.path.join(str(tmp_path / "weekly"), "2026-06-24-wine")
    assert os.path.exists(os.path.join(weekly_dir, "youtube_thumbnail.png"))
    assert os.path.exists(os.path.join(weekly_dir, "reels_cover.png"))
    assert os.path.exists(os.path.join(weekly_dir, "title_card.png"))
    assert len(results) == 3
