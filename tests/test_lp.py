import json
import os
import sys
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

CONTENT_PATH = os.path.join(os.path.dirname(__file__), "..", "lp", "content.json")

REQUIRED_KEYS = [
    "meta", "headline", "worries", "ideals", "gift",
    "cta_text", "line_steps", "profile", "story",
    "why_free", "why_me", "qa", "postscript"
]


def load_content():
    with open(CONTENT_PATH, encoding="utf-8") as f:
        return json.load(f)


def test_content_json_exists():
    assert os.path.exists(CONTENT_PATH), "lp/content.json が存在しません"


def test_required_top_level_keys():
    content = load_content()
    for key in REQUIRED_KEYS:
        assert key in content, f"content.json に '{key}' がありません"


def test_meta_structure():
    content = load_content()
    assert "line_url" in content["meta"]
    assert "colors" in content["meta"]
    for key in ["bg", "text", "accent"]:
        assert key in content["meta"]["colors"], f"colors に '{key}' がありません"


def test_colors_are_correct():
    content = load_content()
    colors = content["meta"]["colors"]
    assert colors["bg"] == "#F5F0E8"
    assert colors["text"] == "#6B1A2A"
    assert colors["accent"] == "#C9A84C"


def test_worries_count():
    content = load_content()
    assert len(content["worries"]) >= 4


def test_ideals_count():
    content = load_content()
    assert len(content["ideals"]) >= 4


def test_story_structure():
    content = load_content()
    assert len(content["story"]) == 6
    for i, part in enumerate(content["story"]):
        assert "title" in part, f"story[{i}] に 'title' がありません"
        assert "body" in part, f"story[{i}] に 'body' がありません"


def test_qa_structure():
    content = load_content()
    assert len(content["qa"]) >= 1
    for i, item in enumerate(content["qa"]):
        assert "q" in item, f"qa[{i}] に 'q' がありません"
        assert "a" in item, f"qa[{i}] に 'a' がありません"


def test_gift_structure():
    content = load_content()
    gift = content["gift"]
    for key in ["title", "description", "items"]:
        assert key in gift, f"gift に '{key}' がありません"
    assert len(gift["items"]) >= 1


def test_profile_structure():
    content = load_content()
    assert "name" in content["profile"]
    assert "body" in content["profile"]
