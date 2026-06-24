import os
import pytest
from tools_express import get_weekly_dir, TEMPLATES_DIR, WEEKLY_BASE_DIR, generate_brand_svgs


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
