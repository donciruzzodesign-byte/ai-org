import os
import pytest
from tools_express import get_weekly_dir, TEMPLATES_DIR, WEEKLY_BASE_DIR


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
