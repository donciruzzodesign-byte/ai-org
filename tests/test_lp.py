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


def test_generate_lp_returns_html():
    from tools_lp import generate_lp
    content = load_content()
    html = generate_lp(content)
    assert html.startswith("<!DOCTYPE html>")


def test_generate_lp_contains_all_sections():
    from tools_lp import generate_lp
    content = load_content()
    html = generate_lp(content)
    assert content["headline"]["catch"] in html
    assert content["headline"]["sub"] in html
    assert content["worries"][0] in html
    assert content["ideals"][0] in html
    assert content["gift"]["title"] in html
    assert content["cta_text"] in html
    assert content["meta"]["line_url"] in html
    assert content["profile"]["name"] in html
    assert content["story"][0]["title"] in html
    assert content["qa"][0]["q"] in html
    assert content["postscript"][:20] in html


def test_generate_lp_uses_correct_colors():
    from tools_lp import generate_lp
    content = load_content()
    html = generate_lp(content)
    assert "#F5F0E8" in html
    assert "#6B1A2A" in html
    assert "#C9A84C" in html


def test_generate_lp_has_google_fonts():
    from tools_lp import generate_lp
    content = load_content()
    html = generate_lp(content)
    assert "fonts.googleapis.com" in html
    assert "Cormorant+Garamond" in html
    assert "Noto+Sans+JP" in html


def test_generate_lp_is_responsive():
    from tools_lp import generate_lp
    content = load_content()
    html = generate_lp(content)
    assert "viewport" in html
    assert "max-width" in html


def test_generate_lp_no_cubocci_studio():
    from tools_lp import generate_lp
    content = load_content()
    html = generate_lp(content)
    assert "CUBOCCI STUDIO" not in html


def test_write_lp_outputs_file(tmp_path):
    from tools_lp import generate_lp, write_lp
    content = load_content()
    out_path = str(tmp_path / "index.html")
    write_lp(content, path=out_path)
    with open(out_path, encoding="utf-8") as f:
        text = f.read()
    assert "<!DOCTYPE html>" in text
    assert content["headline"]["catch"] in text
